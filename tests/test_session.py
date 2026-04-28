import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from server.session import Session


class TestSession:
    @patch("server.session.AgentSession")
    @patch("server.session.chat_store")
    def test_subscribe_unsubscribe(self, mock_chat_store, mock_agent_session_cls):
        mock_agent_session_cls.return_value = MagicMock()
        session = Session("chat-1")

        mock_ws = MagicMock()
        session.subscribe(mock_ws)
        assert session.has_subscribers() is True

        still_alive = session.unsubscribe(mock_ws)
        assert still_alive is False
        assert session.has_subscribers() is False

    @patch("server.session.AgentSession")
    @patch("server.session.chat_store")
    async def test_broadcast(self, mock_chat_store, mock_agent_session_cls):
        mock_agent_session_cls.return_value = MagicMock()
        session = Session("chat-1")

        mock_ws = AsyncMock()
        session.subscribe(mock_ws)

        await session._broadcast({"type": "test", "data": "hello"})

        mock_ws.send_json.assert_called_once_with({"type": "test", "data": "hello"})

    @patch("server.session.AgentSession")
    @patch("server.session.chat_store")
    async def test_broadcast_removes_dead_clients(self, mock_chat_store, mock_agent_session_cls):
        mock_agent_session_cls.return_value = MagicMock()
        session = Session("chat-1")

        mock_ws_alive = AsyncMock()
        mock_ws_dead = AsyncMock()
        mock_ws_dead.send_json.side_effect = Exception("Connection closed")

        session.subscribe(mock_ws_alive)
        session.subscribe(mock_ws_dead)

        await session._broadcast({"type": "test"})

        assert session.has_subscribers() is True
        assert mock_ws_alive in session._subscribers
        assert mock_ws_dead not in session._subscribers

    @patch("server.session.AgentSession")
    @patch("server.session.chat_store")
    async def test_send_message(self, mock_chat_store, mock_agent_session_cls):
        mock_agent_session = MagicMock()
        mock_agent_session_cls.return_value = mock_agent_session

        session = Session("chat-1")

        mock_ws = AsyncMock()
        session.subscribe(mock_ws)

        # Mock the agent response
        async def mock_send_message(content):
            from claude_agent_sdk import AssistantMessage, ResultMessage

            yield AssistantMessage(content="Hello!", model="deepseek-v4-pro")
            yield ResultMessage(subtype="success", total_cost_usd=0.01, duration_ms=100)

        mock_agent_session.send_message = mock_send_message

        await session.send_message("Hi there")

        # User message should be stored and broadcast
        mock_chat_store.add_message.assert_called_with("chat-1", "user", "Hi there")

        # Wait for background task to complete
        await asyncio.sleep(0.1)

        # Assistant message should be stored
        mock_chat_store.add_message.assert_called_with("chat-1", "assistant", "Hello!")

    @patch("server.session.AgentSession")
    @patch("server.session.chat_store")
    async def test_broadcast_error(self, mock_chat_store, mock_agent_session_cls):
        mock_agent_session_cls.return_value = MagicMock()
        session = Session("chat-1")

        mock_ws = AsyncMock()
        session.subscribe(mock_ws)

        await session._broadcast_error("Something went wrong")

        mock_ws.send_json.assert_called_once()
        call_args = mock_ws.send_json.call_args[0][0]
        assert call_args["type"] == "error"
        assert call_args["error"] == "Something went wrong"
