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

## Architecture

### Backend (Python / FastAPI)

- **`server/main.py`** — FastAPI app with REST API and WebSocket endpoint (`/ws`).
- **`server/session.py`** — `Session` class manages one chat session. It wraps `AgentSession`, stores messages via `chat_store`, and broadcasts responses to WebSocket subscribers.
- **`server/ai_client.py`** — `AgentSession` wraps `ClaudeSDKClient` from `claude-agent-sdk`. It yields SDK messages and extracts `session_id` from `SystemMessage(subtype="init")`.
- **`server/chat_store.py`** — In-memory `ChatStore` singleton. `create_chat()` takes an external ID (the SDK's `session_id`). `add_message()` auto-updates the chat title from the first user message.
- **`server/models.py`** — Dataclasses: `Chat`, `ChatMessage`.

**Key patterns:**
- Chat IDs are SDK `session_id`s, not server-generated UUIDs. The `session_id` is captured from the first `SystemMessage(subtype="init")` and used everywhere.
- WebSocket messages are filtered by `chat_id` on both frontend and backend to prevent cross-chat leakage.
- The backend does not persist data to disk; restarting the server loses all chat history.

### Frontend (React / Vite)

- **`client/App.jsx`** — Root component. Manages chat list state, draft chat pattern, WebSocket connection, and message handling.
- **`client/components/ChatList.jsx`** — Sidebar showing formal chats only.
- **`client/components/ChatWindow.jsx`** — Main chat area.

**Key patterns:**
- **Draft chat pattern:** Clicking "New Chat" creates a local temporary chat (not sent to backend). The backend SDK session is only initialized when the user sends their first message. This makes "New Chat" instant.
- `selectedChatIdRef` is used in WebSocket callbacks to avoid stale closures.
- The sidebar only shows "formal" chats (`chats` state). Draft chats are not shown.

### WebSocket Protocol

Messages are JSON with a `type` field:

| Type | Direction | Description |
|------|-----------|-------------|
| `subscribe` | Client → Server | Subscribe to a chat's messages |
| `chat` | Client → Server | Send a user message |
| `connected` | Server → Client | Connection established |
| `history` | Server → Client | Existing messages for subscribed chat |
| `user_message` | Server → Client | User message echoed back |
| `assistant_message` | Server → Client | AI response text |
| `tool_use` | Server → Client | Tool use block (displayed in UI) |
| `result` | Server → Client | Query completed |
| `error` | Server → Client | Error occurred |

### Environment Variables

The backend reads these from `.env`:
- `ANTHROPIC_API_KEY` — Required for `claude-agent-sdk`
- `ANTHROPIC_BASE_URL` — Optional API base URL
- `MODEL` — Optional model override (default: `deepseek-v4-pro`)
- `PORT` — Backend port (default: `3001`)

## Important Notes

- The `claude-agent-sdk` package is installed from a local wheel (`wheels/claude_agent_sdk-0.1.0-py3-none-any.whl`). Do not try to upgrade it from PyPI.
- Frontend runs on port `5173` (Vite dev server) with a proxy to backend `3001`. Access the app at `http://localhost:5173`, not `3001`.
- Python package is managed with `uv`. Dependencies are in `pyproject.toml`.
- `server/__init__.py` is required for `PYTHONPATH=.` imports to work.
