#!/usr/bin/env python3
"""Tests for the AI client module."""

from unittest.mock import AsyncMock, patch

from server.ai_client import DEFAULT_MODEL, SYSTEM_PROMPT, AgentSession


class TestAgentSession:
    def test_build_options_returns_base_when_no_session_id(self):
        session = AgentSession()
        options = session._build_options()

        assert options.system_prompt == SYSTEM_PROMPT
        assert options.max_turns == 100
        assert options.model == DEFAULT_MODEL
        assert "Bash" in options.allowed_tools
        assert options.resume is None

    def test_build_options_includes_resume(self):
        session = AgentSession(session_id="sess-abc")
        options = session._build_options()

        assert options.resume == "sess-abc"

    def test_try_capture_session_id_from_init(self):
        from claude_agent_sdk import SystemMessage

        session = AgentSession()
        msg = SystemMessage(subtype="init", data={"session_id": "sess-123"})
        session._try_capture_session_id(msg)

        assert session.session_id == "sess-123"

    def test_try_capture_session_id_ignores_non_init(self):
        from claude_agent_sdk import SystemMessage

        session = AgentSession()
        msg = SystemMessage(subtype="retry", data={})
        session._try_capture_session_id(msg)

        assert session.session_id is None

    def test_try_capture_session_id_does_not_override(self):
        from claude_agent_sdk import SystemMessage

        session = AgentSession(session_id="existing")
        msg = SystemMessage(subtype="init", data={"session_id": "new-sess"})
        session._try_capture_session_id(msg)

        assert session.session_id == "existing"

    @patch("server.ai_client.ClaudeSDKClient")
    async def test_connect_creates_client_and_starts_receiver(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_client_cls.return_value = mock_client

        session = AgentSession()
        await session.connect()

        assert session._connected is True
        mock_client.connect.assert_awaited_once()
        assert session._receive_task is not None

    @patch("server.ai_client.ClaudeSDKClient")
    async def test_init_sends_dummy_and_returns_session_id(self, mock_client_cls):
        from claude_agent_sdk import SystemMessage

        mock_client = AsyncMock()
        mock_client_cls.return_value = mock_client

        session = AgentSession()

        # Simulate init message in response queue
        async def mock_receive():
            yield SystemMessage(subtype="init", data={"session_id": "sess-123"})

        mock_client.receive_messages = mock_receive

        session_id = await session.init()

        assert session_id == "sess-123"
        assert session.session_id == "sess-123"

    @patch("server.ai_client.ClaudeSDKClient")
    async def test_init_returns_existing_session_id(self, mock_client_cls):
        session = AgentSession(session_id="existing-sess")
        session_id = await session.init()

        assert session_id == "existing-sess"
        mock_client_cls.assert_not_called()

    @patch("server.ai_client.ClaudeSDKClient")
    async def test_send_message_yields_messages_until_result(self, mock_client_cls):
        from claude_agent_sdk import ResultMessage

        mock_client = AsyncMock()
        mock_client_cls.return_value = mock_client

        async def mock_receive():
            yield ResultMessage(
                subtype="success",
                duration_ms=100,
                duration_api_ms=80,
                is_error=False,
                num_turns=1,
                session_id="sess-456",
                total_cost_usd=0.01,
            )

        mock_client.receive_messages = mock_receive

        session = AgentSession()
        await session.connect()

        messages = []
        async for msg in session.send_message("Hi"):
            messages.append(msg)

        assert len(messages) == 1
        assert isinstance(messages[0], ResultMessage)

    @patch("server.ai_client.ClaudeSDKClient")
    async def test_interrupt_calls_client_interrupt(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_client_cls.return_value = mock_client

        session = AgentSession()
        await session.connect()

        await session.interrupt()

        mock_client.interrupt.assert_awaited_once()

    @patch("server.ai_client.ClaudeSDKClient")
    async def test_interrupt_drains_queues(self, mock_client_cls):
        """When interrupted, both message queues should be drained."""
        from claude_agent_sdk import ResultMessage

        mock_client = AsyncMock()
        mock_client_cls.return_value = mock_client

        async def mock_receive():
            yield ResultMessage(
                subtype="success",
                duration_ms=100,
                duration_api_ms=80,
                is_error=False,
                num_turns=1,
                session_id="sess-456",
                total_cost_usd=0.01,
            )

        mock_client.receive_messages = mock_receive

        session = AgentSession()
        await session.connect()

        # Put some stale messages in queues
        await session._message_queue.put(
            {"type": "user", "message": {"role": "user", "content": "stale"}}
        )
        await session._response_queue.put("stale")

        await session.interrupt()

        assert session._message_queue.empty()
        assert session._response_queue.empty()

    @patch("server.ai_client.ClaudeSDKClient")
    async def test_close_disconnects_client(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_client_cls.return_value = mock_client

        session = AgentSession()
        await session.connect()
        await session.close()

        assert session._closed is True
        assert session._connected is False
        mock_client.disconnect.assert_awaited_once()
