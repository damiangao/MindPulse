import os

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, SystemMessage
from dotenv import load_dotenv

load_dotenv(override=True)

SYSTEM_PROMPT = """You are a helpful AI assistant. You can help users with a wide variety of tasks including:
- Answering questions
- Writing and editing text
- Coding and debugging
- Analysis and research
- Creative tasks

Be concise but thorough in your responses."""


class AgentSession:
    """Manages a single agent conversation session.

    If session_id is provided, resumes an existing session.
    If not, creates a new session and captures the session_id.
    """

    def __init__(self, session_id: str | None = None):
        self.session_id = session_id
        self._options = ClaudeAgentOptions(
            system_prompt=SYSTEM_PROMPT,
            max_turns=100,
            model="deepseek-v4-pro",
            allowed_tools=[
                "Bash",
                "Read",
                "Write",
                "Edit",
                "Glob",
                "Grep",
                "WebSearch",
                "WebFetch",
            ],
        )

    async def send_message(self, content: str):
        """Send a message and yield responses."""
        if self.session_id:
            # Resume existing session
            options = ClaudeAgentOptions(
                system_prompt=SYSTEM_PROMPT,
                max_turns=100,
                model="deepseek-v4-pro",
                allowed_tools=[
                    "Bash",
                    "Read",
                    "Write",
                    "Edit",
                    "Glob",
                    "Grep",
                    "WebSearch",
                    "WebFetch",
                ],
                resume=self.session_id,
            )
            async with ClaudeSDKClient(options=options) as client:
                await client.query(content)
                async for message in client.receive_response():
                    yield message
        else:
            # Create new session and capture session_id
            async with ClaudeSDKClient(options=self._options) as client:
                await client.query(content)
                async for message in client.receive_response():
                    if isinstance(message, SystemMessage) and message.subtype == "init":
                        self.session_id = message.data.get("session_id")
                    yield message
