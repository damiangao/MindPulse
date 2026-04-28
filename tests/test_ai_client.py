from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from server.ai_client import AgentSession, SYSTEM_PROMPT


class TestAgentSession:
    @patch("server.ai_client.ClaudeSDKClient")
    async def test_init_creates_new_session(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        from claude_agent_sdk import SystemMessage

        async def mock_receive():
            yield SystemMessage(subtype="init", data={"session_id": "sess-123"})

        mock_client.receive_response = mock_receive

        session = AgentSession()
        session_id = await session.init()

        assert session_id == "sess-123"
        assert session.session_id == "sess-123"
        mock_client.query.assert_awaited_once_with("hi")

    @patch("server.ai_client.ClaudeSDKClient")
    async def test_init_returns_existing_session_id(self, mock_client_cls):
        session = AgentSession(session_id="existing-sess")
        session_id = await session.init()

        assert session_id == "existing-sess"
        mock_client_cls.assert_not_called()

    @patch("server.ai_client.ClaudeSDKClient")
    async def test_send_message_with_new_session(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        from claude_agent_sdk import AssistantMessage, SystemMessage

        async def mock_receive():
            yield SystemMessage(subtype="init", data={"session_id": "sess-456"})
            yield AssistantMessage(content="Hello!", model="deepseek-v4-pro")

        mock_client.receive_response = mock_receive

        session = AgentSession()
        messages = []
        async for msg in session.send_message("Hi"):
            messages.append(msg)

        assert session.session_id == "sess-456"
        assert len(messages) == 2
        mock_client.query.assert_awaited_once_with("Hi")

    @patch("server.ai_client.ClaudeSDKClient")
    async def test_send_message_with_existing_session(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        from claude_agent_sdk import AssistantMessage

        async def mock_receive():
            yield AssistantMessage(content="Resumed!", model="deepseek-v4-pro")

        mock_client.receive_response = mock_receive

        session = AgentSession(session_id="sess-789")
        messages = []
        async for msg in session.send_message("Hi"):
            messages.append(msg)

        assert len(messages) == 1
        # Should use resume option
        call_kwargs = mock_client_cls.call_args[1]
        assert "options" in call_kwargs
        options = call_kwargs["options"]
        assert options.resume == "sess-789"

    def test_build_options_returns_base_when_no_session_id(self):
        session = AgentSession()
        options = session._build_options()

        assert options.system_prompt == SYSTEM_PROMPT
        assert options.max_turns == 100
        assert options.model == "deepseek-v4-pro"
        assert "Bash" in options.allowed_tools
        assert options.resume is None

    def test_build_options_includes_resume(self):
        session = AgentSession(session_id="sess-abc")
        options = session._build_options()

        assert options.resume == "sess-abc"
