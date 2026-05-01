# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A chat web application with a Python FastAPI backend and a React frontend. AI conversations are powered by the `claude-agent-sdk` Python package via WebSocket.

## Development Commands

All commands run from the repository root.

```bash
# Start both frontend (Vite) and backend (FastAPI) in dev mode
npm run dev

# Start backend only
npm run dev:server

# Start frontend only
npm run dev:client

# Install Python dependencies
uv sync

# Run tests
uv run pytest

# Run a single test file
uv run pytest tests/test_chat_store.py

# Run a single test
uv run pytest tests/test_chat_store.py::TestChatStore::test_create_chat -v

# Lint and format Python
uv run ruff check .
uv run ruff format .

# Type check Python
uv run pyright

# Run the backend directly (for testing)
PYTHONPATH=. uv run python -m server.main
```

**Environment variables:** The backend reads `.env` via `load_dotenv()` in `server/main.py`. Any code using `claude-agent-sdk` directly (tests, scripts) must call `load_dotenv()` before importing the SDK — it reads `ANTHROPIC_API_KEY` from the environment at initialization time.

## Architecture

### Backend (Python / FastAPI)

- **`server/main.py`** — FastAPI app with REST API and WebSocket endpoint (`/ws`). Maintains a `_sessions` dict of `Session` objects. On WebSocket disconnect, unsubscribes the client and cleans up sessions with no remaining subscribers.
- **`server/session.py`** — `Session` class manages one chat session. It wraps `AgentSession`, stores messages via `chat_store`, and broadcasts responses to WebSocket subscribers. Uses `StreamEvent` from the SDK for streaming output, with a `_DELTA_BUFFER_SIZE` of 20 chars to batch small deltas before broadcasting. Supports interruption: calling `send_message()` while a response is in-flight cancels the old task and calls `interrupt()` on the agent.
- **`server/ai_client.py`** — `AgentSession` wraps `ClaudeSDKClient` from `claude-agent-sdk`. Uses a long-lived connection with an `asyncio.Queue` for streaming input, allowing interruption without reconnecting. Yields SDK messages until `ResultMessage`. Extracts `session_id` from `SystemMessage(subtype="init")`. Configured with `include_partial_messages=True`, `thinking={"type": "enabled", "budget_tokens": 8000}`, and `setting_sources=["project"]` to load skills from `AGENT_PROJECT_ROOT`.
- **`server/chat_store.py`** — In-memory `ChatStore` singleton. `create_chat()` takes an external ID (the SDK's `session_id`). `add_message()` auto-updates the chat title from the first user message.
- **`server/models.py`** — Dataclasses: `Chat`, `ChatMessage`.

**Key patterns:**
- Chat IDs are SDK `session_id`s, not server-generated UUIDs. The `session_id` is captured from the first `SystemMessage(subtype="init")` and used everywhere.
- WebSocket messages are filtered by `chat_id` on both frontend and backend to prevent cross-chat leakage.
- The backend does not persist data to disk; restarting the server loses all chat history.
- `AgentSession.send_message()` clears stale messages from its response queue before each send to prevent old responses from being returned for new messages.
- On interruption, `Session._process_response()` catches `asyncio.CancelledError`, broadcasts an `interrupted` event, and does NOT persist partial output.

### Frontend (React / Vite)

- **`client/App.jsx`** — Root component. Manages chat list state, draft chat pattern, WebSocket connection, and message handling. Uses `selectedChatIdRef` in WebSocket callbacks to avoid stale closures.
- **`client/components/ChatList.jsx`** — Sidebar showing formal chats only.
- **`client/components/ChatWindow.jsx`** — Main chat area. Renders `MessageBubble`, `ThinkingBlock`, and `ToolUseBlock`. Auto-scrolls only when the user is near the bottom. Empty content bubbles are not rendered.

**Key patterns:**
- **Draft chat pattern:** Clicking "New Chat" creates a local temporary chat (not sent to backend). The backend SDK session is only initialized when the user sends their first message via `initDraftChat()`, which calls `POST /api/chats/init` to get a real `session_id`. This makes "New Chat" instant.
- The sidebar only shows "formal" chats (`chats` state). Draft chats are not shown.
- Thinking content is displayed outside the message bubble, collapsed to the last 2 lines by default.
- Tool use blocks are inserted immediately after the streaming assistant message that triggered them.
- When a response is interrupted, the frontend clears the `thinking` field on the streaming message so the old thinking block disappears.

### WebSocket Protocol

Messages are JSON with a `type` field:

| Type | Direction | Description |
|------|-----------|-------------|
| `subscribe` | Client → Server | Subscribe to a chat's messages |
| `chat` | Client → Server | Send a user message |
| `stop` | Client → Server | Stop the current assistant response |
| `connected` | Server → Client | Connection established |
| `history` | Server → Client | Existing messages for subscribed chat |
| `user_message` | Server → Client | User message echoed back |
| `assistant_delta` | Server → Client | Streaming text chunk (batched) |
| `thinking_delta` | Server → Client | Streaming thinking chunk (batched) |
| `tool_use` | Server → Client | Tool use block (displayed in UI) |
| `result` | Server → Client | Query completed |
| `interrupted` | Server → Client | Response was cancelled/interrupted |
| `assistant_message` | Server → Client | Legacy complete message (fallback) |
| `error` | Server → Client | Error occurred |

### Environment Variables

The backend reads these from `.env`:
- `ANTHROPIC_API_KEY` — Required for `claude-agent-sdk`
- `ANTHROPIC_BASE_URL` — Optional API base URL
- `MODEL` — Optional model override (default: `MiniMax-M2.7`)
- `PORT` — Backend port (default: `3001`)
- `AGENT_PROJECT_ROOT` — Working directory for agent file operations and skill loading (default: `.`)

## Important Notes

- The `claude-agent-sdk` package is installed from a local wheel (`wheels/claude_agent_sdk-0.1.0-py3-none-any.whl`). Do not try to upgrade it from PyPI.
- Frontend runs on port `5173` (Vite dev server) with a proxy to backend `3001`. Access the app at `http://localhost:5173`, not `3001`.
- Python package is managed with `uv`. Dependencies are in `pyproject.toml`.
- `server/__init__.py` is required for `PYTHONPATH=.` imports to work.
- Python style rules are in `.claude/rules/python-style.md` (binary operator spacing, shebang, docstring requirements).
