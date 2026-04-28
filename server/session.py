from __future__ import annotations

import asyncio
import json

from claude_agent_sdk import AssistantMessage, ResultMessage, SystemMessage
from claude_agent_sdk.types import StreamEvent
from fastapi import WebSocket

from server.ai_client import AgentSession
from server.chat_store import chat_store


class Session:
    # Minimum accumulated characters before broadcasting a delta
    _DELTA_BUFFER_SIZE = 20

    def __init__(self, chat_id: str):
        self.chat_id = chat_id
        self._subscribers: set[WebSocket] = set()
        self._agent_session = AgentSession(session_id=chat_id)
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
        self._reset_state()
        try:
            async for message in self._agent_session.send_message(content):
                await self._handle_sdk_message(message)
            # Flush any remaining pending deltas
            await self._flush_pending_deltas()
        except Exception as e:
            print(f"Error in session {self.chat_id}: {e}")
            await self._broadcast_error(str(e))
        finally:
            # Persist the complete assistant message
            if self._current_response_text:
                chat_store.add_message(
                    self.chat_id, "assistant", self._current_response_text
                )
            self._reset_state()

    async def _flush_pending_deltas(self):
        """Broadcast any accumulated pending deltas."""
        await self._maybe_broadcast_delta("_pending_text_delta", "assistant_delta")
        await self._maybe_broadcast_delta("_pending_thinking_delta", "thinking_delta")

    async def _maybe_broadcast_delta(self, attr: str, msg_type: str) -> None:
        """Broadcast pending delta if it exists, then clear it."""
        delta = getattr(self, attr)
        if delta:
            await self._broadcast({
                "type": msg_type,
                "delta": delta,
                "chat_id": self.chat_id,
            })
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
            await self._broadcast({
                "type": msg_type,
                "delta": new_pending,
                "chat_id": self.chat_id,
            })
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
                    await self._broadcast({
                        "type": "tool_use",
                        "tool_name": self._current_tool_name,
                        "tool_input": tool_input,
                        "chat_id": self.chat_id,
                    })
                    self._current_tool_name = None
                    self._current_tool_input = ""

        elif isinstance(message, AssistantMessage):
            # Complete assistant message - used as fallback or for final state
            pass

        elif isinstance(message, ResultMessage):
            await self._flush_pending_deltas()
            await self._broadcast({
                "type": "result",
                "success": message.subtype == "success",
                "chat_id": self.chat_id,
                "cost": message.total_cost_usd,
                "duration": message.duration_ms,
            })

        elif isinstance(message, SystemMessage):
            # System messages include retry info, errors, and init messages
            # We log them but don't broadcast to frontend unless it's an error
            if message.subtype == "retry":
                print(f"SDK retry in session {self.chat_id}: {message}")
            elif message.subtype == "error":
                error_msg = str(message)
                print(f"SDK error in session {self.chat_id}: {error_msg}")
                await self._broadcast({
                    "type": "error",
                    "error": error_msg,
                    "chat_id": self.chat_id,
                })
            else:
                print(f"SDK system message in session {self.chat_id}: {message}")

    async def send_message(self, content: str):
        # Store user message
        chat_store.add_message(self.chat_id, "user", content)

        # Broadcast user message
        await self._broadcast({
            "type": "user_message",
            "content": content,
            "chat_id": self.chat_id,
        })

        # Send to agent and process response
        asyncio.create_task(self._process_response(content))

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
                print(f"Error broadcasting to client: {e}")
                dead_clients.add(client)
        self._subscribers -= dead_clients

    async def _broadcast_error(self, error: str):
        await self._broadcast({
            "type": "error",
            "error": error,
            "chat_id": self.chat_id,
        })

    async def close(self):
        # AgentSession uses async with internally, no explicit cleanup needed
        pass
