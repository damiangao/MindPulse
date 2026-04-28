import os
from dataclasses import replace

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, SystemMessage

SYSTEM_PROMPT = """You are a helpful AI assistant. You can help users with a wide variety of tasks including:
- Answering questions
- Writing and editing text
- Coding and debugging
- Analysis and research
- Creative tasks

Be concise but thorough in your responses."""

_INIT_SUBTYPE = "init"

# Project root for loading skills and CLAUDE.md via setting_sources
PROJECT_ROOT = os.environ.get("AGENT_PROJECT_ROOT", ".")

# Default model and thinking configuration
DEFAULT_MODEL = os.environ.get("MODEL", "glm-5.1")
DEFAULT_THINKING = {"type": "enabled", "budget_tokens": 8000}


class AgentSession:
    """Manages a single agent conversation session.

    If session_id is provided, resumes an existing session.
    If not, creates a new session and captures the session_id.
    """

    def __init__(self, session_id: str | None = None):
        self.session_id = session_id
        self._options = ClaudeAgentOptions(
            cwd=PROJECT_ROOT,
            system_prompt=SYSTEM_PROMPT,
            max_turns=100,
            model=DEFAULT_MODEL,
            thinking=DEFAULT_THINKING,
            include_partial_messages=True,
            setting_sources=["project"],
            allowed_tools=[
                "Bash",
                "Skill",
                "Read",
                "Write",
                "Edit",
                "Glob",
                "Grep",
                "WebSearch",
                "WebFetch",
            ],
        )

    def _build_options(self) -> ClaudeAgentOptions:
        """Build ClaudeAgentOptions, including resume if session_id is set."""
        if self.session_id:
            return replace(self._options, resume=self.session_id)
        return self._options

    def _try_capture_session_id(self, message: SystemMessage) -> None:
        """Capture session_id from an init SystemMessage if not already set."""
        if not self.session_id and message.subtype == _INIT_SUBTYPE:
            self.session_id = message.data.get("session_id")

    async def init(self) -> str | None:
        """Initialize a new session and return its session_id.

        Sends a dummy query to trigger the SDK's init handshake.
        """
        if self.session_id:
            return self.session_id

        async with ClaudeSDKClient(options=self._options) as client:
            await client.query("hi")
            async for message in client.receive_response():
                if isinstance(message, SystemMessage):
                    self._try_capture_session_id(message)
                    if self.session_id:
                        break
        return self.session_id

    async def send_message(self, content: str):
        """Send a message and yield responses."""
        options = self._build_options()
        async with ClaudeSDKClient(options=options) as client:
            await client.query(content)
            async for message in client.receive_response():
                if isinstance(message, SystemMessage):
                    self._try_capture_session_id(message)
                yield message
