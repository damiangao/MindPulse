#!/usr/bin/env python3
"""Session management for WebSocket chat connections."""

from __future__ import annotations

import asyncio
import json

from claude_agent_sdk import AssistantMessage, ResultMessage, SystemMessage, TextBlock, ThinkingBlock
from claude_agent_sdk.types import StreamEvent
from fastapi import WebSocket

from server._logging import setup_logger
from server.ai_client import AgentSession
from server.chat_store import chat_store

_logger = setup_logger("session")


class Session:
    # Minimum accumulated characters before broadcasting a delta
    _DELTA_BUFFER_SIZE = 20

    def __init__(self, chat_id: str, workspace_id: str):
        self.chat_id = chat_id
        self.workspace_id = workspace_id
        self._subscribers: set[WebSocket] = set()
        self._agent_session = AgentSession(session_id=chat_id)
        self._response_task: asyncio.Task | None = None
        self._reset_state()

    def _reset_state(self) -> None:
        """Reset per-response state variables."""
        self._current_response_text: str = ""
        self._current_response_thinking: str = ""
        self._current_tool_name: str | None = None
        self._current_tool_input: str = ""
        self._pending_text_delta: str = ""
        self._pending_thinking_delta: str = ""

    async def _process_response(self, content: str):
        """Send message to agent and broadcast responses."""
        _logger.debug(f"[Session {self.chat_id}] _process_response started for: {content[:50]}...")
        self._reset_state()
        try:
            msg_count = 0
            async for message in self._agent_session.send_message(content):
                msg_count += 1
                msg_type = type(message).__name__
                _logger.debug(f"[Session {self.chat_id}] Processing SDK message #{msg_count}: {msg_type}")
                await self._handle_sdk_message(message)
            _logger.debug(f"[Session {self.chat_id}] Finished iterating SDK messages, total={msg_count}")
            # Flush any remaining pending deltas
            await self._flush_pending_deltas()
        except asyncio.CancelledError:
            _logger.debug(f"[Session {self.chat_id}] _process_response cancelled (interrupted)")
            # Task was cancelled (interrupted by new user message or stop button)
            # Do NOT persist partial output - discard it per UX convention
            await self._broadcast(
                {
                    "type": "interrupted",
                    "chat_id": self.chat_id,
                }
            )
            raise
        except Exception as e:
            _logger.debug(f"[Session {self.chat_id}] Error in _process_response: {e}")
            await self._broadcast_error(str(e))
        finally:
            _logger.debug(f"[Session {self.chat_id}] _process_response finally block, current_response_text length={len(self._current_response_text)}")
            # Only persist complete assistant messages (not when cancelled)
            if self._current_response_text:
                chat_store.add_message(self.chat_id, self.workspace_id, "assistant", self._current_response_text)
                _logger.debug(f"[Session {self.chat_id}] Persisted assistant message, length={len(self._current_response_text)}")
            else:
                _logger.debug(f"[Session {self.chat_id}] No assistant text to persist")
            self._reset_state()
            self._response_task = None
            _logger.debug(f"[Session {self.chat_id}] _process_response ended")

    async def _flush_pending_deltas(self):
        """Broadcast any accumulated pending deltas."""
        await self._maybe_broadcast_delta("_pending_text_delta", "assistant_delta")
        await self._maybe_broadcast_delta("_pending_thinking_delta", "thinking_delta")

    async def _maybe_broadcast_delta(self, attr: str, msg_type: str) -> None:
        """Broadcast pending delta if it exists, then clear it."""
        delta = getattr(self, attr)
        if delta:
            await self._broadcast(
                {
                    "type": msg_type,
                    "delta": delta,
                    "chat_id": self.chat_id,
                }
            )
            setattr(self, attr, "")

    async def _accumulate_and_maybe_broadcast(
        self, text: str, accumulator_attr: str, pending_attr: str, msg_type: str
    ) -> None:
        """Add text to accumulator and pending, broadcast if buffer is full."""
        accumulator = getattr(self, accumulator_attr)
        setattr(self, accumulator_attr, accumulator + text)
        pending = getattr(self, pending_attr)
        new_pending = pending + text
        setattr(self, pending_attr, new_pending)
        if len(new_pending) >= self._DELTA_BUFFER_SIZE:
            await self._broadcast(
                {
                    "type": msg_type,
                    "delta": new_pending,
                    "chat_id": self.chat_id,
                }
            )
            setattr(self, pending_attr, "")

    async def _handle_sdk_message(
        self, message: AssistantMessage | ResultMessage | SystemMessage | StreamEvent
    ):
        if isinstance(message, StreamEvent):
            event = message.event
            event_type = event.get("type")

            if event_type == "content_block_delta":
                delta = event.get("delta", {})
                delta_type = delta.get("type")

                if delta_type == "text_delta":
                    await self._accumulate_and_maybe_broadcast(
                        delta.get("text", ""),
                        "_current_response_text",
                        "_pending_text_delta",
                        "assistant_delta",
                    )

                elif delta_type == "thinking_delta":
                    await self._accumulate_and_maybe_broadcast(
                        delta.get("thinking", ""),
                        "_current_response_thinking",
                        "_pending_thinking_delta",
                        "thinking_delta",
                    )

                elif delta_type == "input_json_delta":
                    self._current_tool_input += delta.get("partial_json", "")

            elif event_type == "content_block_start":
                # Flush any pending deltas before starting a new block
                await self._flush_pending_deltas()
                content_block = event.get("content_block", {})
                block_type = content_block.get("type")

                if block_type == "tool_use":
                    self._current_tool_name = content_block.get("name")
                    self._current_tool_input = ""

            elif event_type == "content_block_stop":
                # Flush any pending deltas before stopping a block
                await self._flush_pending_deltas()
                if self._current_tool_name is not None:
                    try:
                        if self._current_tool_input:
                            tool_input = json.loads(self._current_tool_input)
                        else:
                            tool_input = {}
                    except json.JSONDecodeError:
                        tool_input = {}
                    await self._broadcast(
                        {
                            "type": "tool_use",
                            "tool_name": self._current_tool_name,
                            "tool_input": tool_input,
                            "chat_id": self.chat_id,
                        }
                    )
                    self._current_tool_name = None
                    self._current_tool_input = ""

        elif isinstance(message, AssistantMessage):
            _logger.debug(f"[Session {self.chat_id}] AssistantMessage received: content={message.content!r}, model={message.model}")
            for block in message.content:
                if isinstance(block, TextBlock) and block.text:
                    _logger.debug(f"[Session {self.chat_id}]   TextBlock.text = {block.text!r}")
                    await self._accumulate_and_maybe_broadcast(
                        block.text, "_current_response_text", "_pending_text_delta", "assistant_delta",
                    )
                elif isinstance(block, ThinkingBlock) and block.thinking:
                    _logger.debug(f"[Session {self.chat_id}]   ThinkingBlock.thinking = {block.thinking!r}")
                    await self._accumulate_and_maybe_broadcast(
                        block.thinking, "_current_response_thinking", "_pending_thinking_delta", "thinking_delta",
                    )

        elif isinstance(message, ResultMessage):
            await self._flush_pending_deltas()
            await self._broadcast(
                {
                    "type": "result",
                    "success": message.subtype == "success",
                    "chat_id": self.chat_id,
                    "cost": message.total_cost_usd,
                    "duration": message.duration_ms,
                }
            )

        elif isinstance(message, SystemMessage):
            # System messages include retry info, errors, and init messages
            # We log them but don't broadcast to frontend unless it's an error
            if message.subtype == "retry":
                _logger.debug(f"SDK retry in session {self.chat_id}: {message}")
            elif message.subtype == "error":
                error_msg = str(message)
                _logger.error(f"SDK error in session {self.chat_id}: {error_msg}")
                await self._broadcast(
                    {
                        "type": "error",
                        "error": error_msg,
                        "chat_id": self.chat_id,
                    }
                )
            else:
                _logger.debug(f"SDK system message in session {self.chat_id}: {message}")

    async def send_message(self, content: str):
        _logger.debug(f"[Session {self.chat_id}] send_message called with: {content[:50]}...")
        # If there's an in-flight response, interrupt it first.
        if self._response_task and not self._response_task.done():
            _logger.debug(
                f"[Session {self.chat_id}] Interrupting in-flight response "
                f"for new message: {content[:30]}..."
            )
            # Cancel the old response task so it stops consuming messages
            self._response_task.cancel()
            try:
                await self._response_task
            except asyncio.CancelledError:
                pass
            # Send interrupt signal and drain remaining messages from the
            # interrupted turn (including its ResultMessage).
            await self._agent_session.interrupt()
            _logger.debug(f"[Session {self.chat_id}] Old task cancelled and drained")

        # Store user message
        chat_store.add_message(self.chat_id, self.workspace_id, "user", content)

        # Broadcast user message
        await self._broadcast(
            {
                "type": "user_message",
                "content": content,
                "chat_id": self.chat_id,
            }
        )

        # Send to agent and process response
        _logger.debug(f"[Session {self.chat_id}] Starting new response task for: {content[:50]}...")
        self._response_task = asyncio.create_task(self._process_response(content))
        _logger.debug(f"[Session {self.chat_id}] Response task created, task_id={id(self._response_task)}")

    def subscribe(self, client: WebSocket):
        self._subscribers.add(client)

    def unsubscribe(self, client: WebSocket) -> bool:
        """Unsubscribe a client. Returns True if session still has subscribers."""
        self._subscribers.discard(client)
        return self.has_subscribers()

    def has_subscribers(self) -> bool:
        return len(self._subscribers) > 0

    async def _broadcast(self, message: dict):
        dead_clients = set()
        for client in self._subscribers:
            try:
                await client.send_json(message)
            except Exception as e:
                _logger.warning(f"Error broadcasting to client: {e}")
                dead_clients.add(client)
        self._subscribers -= dead_clients

    async def _broadcast_error(self, error: str):
        await self._broadcast(
            {
                "type": "error",
                "error": error,
                "chat_id": self.chat_id,
            }
        )

    async def stop_response(self):
        """Stop the current assistant response without sending a new message."""
        _logger.debug(f"[Session {self.chat_id}] stop_response called")
        if self._response_task and not self._response_task.done():
            _logger.debug(f"[Session {self.chat_id}] Stopping in-flight response task")
            # Cancel the response task first so it stops consuming messages
            self._response_task.cancel()
            try:
                await self._response_task
            except asyncio.CancelledError:
                _logger.debug(f"[Session {self.chat_id}] Response task cancelled successfully")
                pass
            # Send interrupt signal and drain remaining messages
            await self._agent_session.interrupt()
            _logger.debug(f"[Session {self.chat_id}] Finished stop_response")
        else:
            _logger.debug(f"[Session {self.chat_id}] No in-flight response to stop")

    async def close(self):
        if self._response_task and not self._response_task.done():
            self._response_task.cancel()
            try:
                await self._response_task
            except asyncio.CancelledError:
                pass
        await self._agent_session.close()
