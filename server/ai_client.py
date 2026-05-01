#!/usr/bin/env python3
"""AI client for managing agent sessions with interruptible streaming input."""

import asyncio
import os
from dataclasses import replace

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, ResultMessage, SystemMessage

from server._logging import setup_logger

SYSTEM_PROMPT = (
    "You are a helpful AI assistant. You can help users with a wide variety"
    " of tasks including: answering questions, writing and editing text,"
    " coding and debugging, analysis and research, and creative tasks."
    " Be concise but thorough in your responses."
)

_INIT_SUBTYPE = "init"

# Project root for loading skills and CLAUDE.md via setting_sources
PROJECT_ROOT = os.environ.get("AGENT_PROJECT_ROOT", ".")

# Default model and thinking configuration
DEFAULT_MODEL = os.environ.get("MODEL", "MiniMax-M2.7")
DEFAULT_THINKING = {"type": "enabled", "budget_tokens": 8000}

_logger = setup_logger("ai_client")


class AgentSession:
    """Manages a single agent conversation session with persistent connection.

    Uses a long-lived ClaudeSDKClient connection with an asyncio.Queue for
    streaming input. This allows interrupting the assistant mid-response and
    sending follow-up messages without reconnecting.
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
        self._client: ClaudeSDKClient | None = None
        self._message_queue: asyncio.Queue[dict] = asyncio.Queue()
        self._response_queue: asyncio.Queue = asyncio.Queue()
        self._connected = False
        self._closed = False
        self._receive_task: asyncio.Task | None = None

    def _build_options(self) -> ClaudeAgentOptions:
        """Build ClaudeAgentOptions, including resume if session_id is set."""
        if self.session_id:
            return replace(self._options, resume=self.session_id)
        return self._options

    def _try_capture_session_id(self, message: SystemMessage) -> None:
        """Capture session_id from an init SystemMessage if not already set."""
        if not self.session_id and message.subtype == _INIT_SUBTYPE:
            self.session_id = message.data.get("session_id")

    async def _message_generator(self):
        """Async generator that yields messages from the queue for streaming input."""
        while not self._closed:
            try:
                message = await asyncio.wait_for(
                    self._message_queue.get(), timeout=1.0
                )
                yield message
            except asyncio.TimeoutError:
                continue

    async def _receive_messages(self):
        """Background task: receive messages from the SDK and put into response queue."""
        if not self._client:
            return
        try:
            async for message in self._client.receive_messages():
                if isinstance(message, SystemMessage):
                    self._try_capture_session_id(message)
                await self._response_queue.put(message)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            _logger.error(f"Error receiving messages: {e}")

    async def connect(self) -> None:
        """Establish a persistent connection to the SDK."""
        if self._connected or self._closed:
            return

        options = self._build_options()
        self._client = ClaudeSDKClient(options=options)
        await self._client.connect(prompt=self._message_generator())
        self._connected = True

        # Start background task to receive messages
        self._receive_task = asyncio.create_task(self._receive_messages())

    async def init(self) -> str | None:
        """Initialize a new session and return its session_id.

        Sends a dummy query to trigger the SDK's init handshake.
        """
        if self.session_id:
            return self.session_id

        await self.connect()

        # Send a dummy message to trigger init
        await self._message_queue.put({
            "type": "user",
            "message": {"role": "user", "content": "hi"},
        })

        # Wait for init message
        while not self.session_id and not self._closed:
            try:
                msg = await asyncio.wait_for(self._response_queue.get(), timeout=0.1)
                if isinstance(msg, SystemMessage) and msg.subtype == _INIT_SUBTYPE:
                    self._try_capture_session_id(msg)
            except asyncio.TimeoutError:
                continue

        return self.session_id

    async def send_message(self, content: str):
        """Send a message via the persistent connection.

        Yields all response messages for this turn. Must be called sequentially
        (not concurrently) per session.
        """
        if not self._connected:
            await self.connect()

        # Clear any stale messages that may have arrived after interrupt
        # cleanup or from a previous turn. This prevents old responses from
        # being returned for new messages.
        stale_count = 0
        while not self._response_queue.empty():
            try:
                self._response_queue.get_nowait()
                stale_count += 1
            except asyncio.QueueEmpty:
                break
        if stale_count:
            _logger.debug(f"[AgentSession] Cleared {stale_count} stale messages before sending")

        _logger.debug(f"[AgentSession] send_message starting, content={content[:30]}...")

        # Send the user message
        await self._message_queue.put({
            "type": "user",
            "message": {"role": "user", "content": content},
        })
        _logger.debug("[AgentSession] Message queued")

        # Yield messages until we see a ResultMessage
        msg_count = 0
        while True:
            try:
                message = await asyncio.wait_for(
                    self._response_queue.get(), timeout=0.1
                )
            except asyncio.TimeoutError:
                if self._closed:
                    _logger.debug("[AgentSession] Closed, exiting")
                    break
                continue

            msg_count += 1
            msg_type = type(message).__name__
            _logger.debug(f"[AgentSession] Got message #{msg_count}: {msg_type}")

            yield message
            if isinstance(message, ResultMessage):
                _logger.debug("[AgentSession] Got ResultMessage, breaking")
                break

    async def _drain_queues(self) -> None:
        """Remove all pending messages from both queues."""
        drained_msg = 0
        while not self._message_queue.empty():
            try:
                self._message_queue.get_nowait()
                drained_msg += 1
            except asyncio.QueueEmpty:
                break
        drained_resp = 0
        while not self._response_queue.empty():
            try:
                self._response_queue.get_nowait()
                drained_resp += 1
            except asyncio.QueueEmpty:
                break
        _logger.debug(f"[AgentSession] Drained queues: message_queue={drained_msg}, response_queue={drained_resp}")

    async def interrupt(self) -> None:
        """Interrupt the current assistant response (streaming mode only).

        Calls client.interrupt() to send a stop signal to the SDK, then
        drains the response queue until the ResultMessage for the interrupted
        turn is consumed. This follows the SDK documentation which states that
        after interrupt(), receive_response() must be called to drain messages.
        """
        _logger.debug(f"[AgentSession] interrupt called, client exists={self._client is not None}")
        if self._client:
            await self._client.interrupt()
            _logger.debug("[AgentSession] SDK interrupt() called")

        # Drain response queue until we see ResultMessage or queue is empty
        # for a sustained period. This consumes the interrupted turn's
        # remaining messages as required by the SDK.
        # Use a longer wait (up to 2s) because _receive_messages may still be
        # pushing messages after the interrupt signal is processed.
        drained_count = 0
        empty_streak = 0
        while empty_streak < 40:
            try:
                message = self._response_queue.get_nowait()
                drained_count += 1
                empty_streak = 0
                if isinstance(message, ResultMessage):
                    _logger.debug(f"[AgentSession] Drained ResultMessage (subtype={message.subtype}), interrupt cleanup done")
                    break
            except asyncio.QueueEmpty:
                empty_streak += 1
                await asyncio.sleep(0.05)

        # Also drain any pending messages in the message queue
        msg_drained = 0
        while not self._message_queue.empty():
            try:
                self._message_queue.get_nowait()
                msg_drained += 1
            except asyncio.QueueEmpty:
                break

        _logger.debug(f"[AgentSession] Interrupt cleanup done: response_queue drained={drained_count}, message_queue drained={msg_drained}")

    async def close(self) -> None:
        """Close the persistent connection."""
        self._closed = True
        if self._receive_task and not self._receive_task.done():
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
        if self._client:
            await self._client.disconnect()
            self._client = None
        self._connected = False
