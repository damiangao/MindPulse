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
        self._current_response_text: str = ""
        self._current_response_thinking: str = ""
        self._current_tool_name: str | None = None
        self._current_tool_input: str = ""
        self._pending_text_delta: str = ""
        self._pending_thinking_delta: str = ""

    async def _process_response(self, content: str):
        """Send message to agent and broadcast responses."""
        self._current_response_text = ""
        self._current_response_thinking = ""
        self._current_tool_name = None
        self._current_tool_input = ""
        self._pending_text_delta = ""
        self._pending_thinking_delta = ""
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
            self._current_response_text = ""
            self._current_response_thinking = ""
            self._current_tool_name = None
            self._current_tool_input = ""
            self._pending_text_delta = ""
            self._pending_thinking_delta = ""

    async def _flush_pending_deltas(self):
        """Broadcast any accumulated pending deltas."""
        if self._pending_text_delta:
            await self._broadcast({
                "type": "assistant_delta",
                "delta": self._pending_text_delta,
                "chat_id": self.chat_id,
            })
            self._pending_text_delta = ""
        if self._pending_thinking_delta:
            await self._broadcast({
                "type": "thinking_delta",
                "delta": self._pending_thinking_delta,
                "chat_id": self.chat_id,
            })
            self._pending_thinking_delta = ""

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
                    text = delta.get("text", "")
                    self._current_response_text += text
                    self._pending_text_delta += text
                    if len(self._pending_text_delta) >= self._DELTA_BUFFER_SIZE:
                        await self._broadcast({
                            "type": "assistant_delta",
                            "delta": self._pending_text_delta,
                            "chat_id": self.chat_id,
                        })
                        self._pending_text_delta = ""

                elif delta_type == "thinking_delta":
                    thinking = delta.get("thinking", "")
                    self._current_response_thinking += thinking
                    self._pending_thinking_delta += thinking
                    if len(self._pending_thinking_delta) >= self._DELTA_BUFFER_SIZE:
                        await self._broadcast({
                            "type": "thinking_delta",
                            "delta": self._pending_thinking_delta,
                            "chat_id": self.chat_id,
                        })
                        self._pending_thinking_delta = ""

                elif delta_type == "input_json_delta":
                    partial_json = delta.get("partial_json", "")
                    self._current_tool_input += partial_json

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
