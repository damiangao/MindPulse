from __future__ import annotations

import asyncio

from fastapi import WebSocket

from claude_agent_sdk import AssistantMessage, ResultMessage, SystemMessage, TextBlock, ToolUseBlock

from server.ai_client import AgentSession
from server.chat_store import chat_store


class Session:
    def __init__(self, chat_id: str):
        self.chat_id = chat_id
        self._subscribers: set[WebSocket] = set()
        self._agent_session = AgentSession(session_id=chat_id)

    async def _process_response(self, content: str):
        """Send message to agent and broadcast responses."""
        try:
            async for message in self._agent_session.send_message(content):
                self._handle_sdk_message(message)
        except Exception as e:
            print(f"Error in session {self.chat_id}: {e}")
            await self._broadcast_error(str(e))

    def _handle_sdk_message(self, message: AssistantMessage | ResultMessage | SystemMessage):
        if isinstance(message, AssistantMessage):
            content = message.content

            if isinstance(content, str):
                chat_store.add_message(self.chat_id, "assistant", content)
                asyncio.create_task(
                    self._broadcast({
                        "type": "assistant_message",
                        "content": content,
                        "chat_id": self.chat_id,
                    })
                )
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, TextBlock):
                        chat_store.add_message(self.chat_id, "assistant", block.text)
                        asyncio.create_task(
                            self._broadcast({
                                "type": "assistant_message",
                                "content": block.text,
                                "chat_id": self.chat_id,
                            })
                        )
                    elif isinstance(block, ToolUseBlock):
                        asyncio.create_task(
                            self._broadcast({
                                "type": "tool_use",
                                "tool_name": block.name,
                                "tool_id": block.id,
                                "tool_input": block.input,
                                "chat_id": self.chat_id,
                            })
                        )
        elif isinstance(message, ResultMessage):
            asyncio.create_task(
                self._broadcast({
                    "type": "result",
                    "success": message.subtype == "success",
                    "chat_id": self.chat_id,
                    "cost": message.total_cost_usd,
                    "duration": message.duration_ms,
                })
            )
        elif isinstance(message, SystemMessage):
            # System messages include retry info, errors, and init messages
            # We log them but don't broadcast to frontend unless it's an error
            if message.subtype == "retry":
                print(f"SDK retry in session {self.chat_id}: {message}")
            elif message.subtype == "error":
                error_msg = str(message)
                print(f"SDK error in session {self.chat_id}: {error_msg}")
                asyncio.create_task(
                    self._broadcast({
                        "type": "error",
                        "error": error_msg,
                        "chat_id": self.chat_id,
                    })
                )
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

    def unsubscribe(self, client: WebSocket):
        self._subscribers.discard(client)

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
