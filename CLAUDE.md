# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A chat web application with a Python FastAPI backend and a React frontend. AI conversations are powered by the `claude-agent-sdk` Python package via WebSocket. Features SQLite persistence with per-account workspace isolation, and JWT-based authentication.

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

# Install frontend dependencies
cd client && npm install

# Run all tests (backend + frontend)
uv run pytest        # Python tests (91 tests)
npm test            # Frontend tests (20 tests)

# Run backend tests only
uv run pytest

# Run frontend tests only
npm test -- --coverage  # with coverage

# Run a single test file
uv run pytest tests/test_chat_store.py

# Lint and format Python
uv run ruff check .
uv run ruff format .

# Type check Python
uv run pyright

# Run the backend directly
PYTHONPATH=. uv run python -m server.main
```

**Environment variables:** The backend reads `.env` via `load_dotenv()` in `server/main.py`. Any code using `claude-agent-sdk` directly (tests, scripts) must call `load_dotenv()` before importing the SDK — it reads `ANTHROPIC_API_KEY` from the environment at initialization time.

## Architecture

### Backend (Python / FastAPI)

- **`server/main.py`** — FastAPI app with REST API and WebSocket endpoint (`/ws`). Maintains a `_sessions` dict of `Session` objects. On WebSocket disconnect, unsubscribes the client and cleans up sessions with no remaining subscribers.
- **`server/session.py`** — `Session` class manages one chat session. It wraps `AgentSession`, stores messages via `chat_store`, and broadcasts responses to WebSocket subscribers. Uses `StreamEvent` from the SDK for streaming output, with a `_DELTA_BUFFER_SIZE` of 20 chars to batch small deltas before broadcasting. Supports interruption: calling `send_message()` while a response is in-flight cancels the old task and calls `interrupt()` on the agent.
- **`server/ai_client.py`** — `AgentSession` wraps `ClaudeSDKClient` from `claude-agent-sdk`. Uses a long-lived connection with an `asyncio.Queue` for streaming input, allowing interruption without reconnecting. Yields SDK messages until `ResultMessage`. Extracts `session_id` from `SystemMessage(subtype="init")`. Per-user workspace is `{AGENT_PROJECT_ROOT}/{user_id}/`.
- **`server/chat_store.py`** — SQLite-backed `ChatStore`. Uses per-user `get_workspace_db()` connections with WAL mode. `create_chat()` takes an external ID (the SDK's `session_id`). `add_message()` auto-updates the chat title from the first user message.
- **`server/models.py`** — Dataclasses: `User`, `Chat`, `ChatMessage`.
- **`server/auth.py`** — JWT auth utilities: `create_token()`, `decode_token()`, `hash_password()`, `verify_password()`.
- **`server/auth_routes.py`** — Auth endpoints: `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`.
- **`server/file_storage.py`** — File upload/download utility. Files stored at `{AGENT_PROJECT_ROOT}/{user_id}/{chat_id}/{filename}`.
- **`server/database/connection.py`** — SQLite connections at `data/chats.db` with WAL mode. Caches connections by user.
- **`server/database/repositories/chat.py`** — `ChatRepository` with `create_chat()`, `get_chat()`, `get_all_chats()`, `update_title()`, `delete()`.
- **`server/database/repositories/message.py`** — `MessageRepository` with `add_message()`, `get_messages()`.
- **`server/_logging.py`** — Shared logging setup with file + console handlers.

**Key patterns:**
- **Simplified chat creation:** "New Chat" creates a local temp chat (UUID not in sidebar). First message sent via WebSocket auto-creates the chat and session in the backend. Chat appears in sidebar after `result` event triggers `fetchChats()`.
- Chat IDs are SDK `session_id`s. The `session_id` is captured from the first `SystemMessage(subtype="init")` and stored in the `chats` table.
- WebSocket messages are filtered by `chat_id` on both frontend and backend to prevent cross-chat leakage.
- SQLite persistence: single database at `data/chats.db` with `user_id` column for multi-tenant isolation.
- On interruption, `Session._process_response()` catches `asyncio.CancelledError`, broadcasts an `interrupted` event, and does NOT persist partial output.
- **user_id = workspace dir name**: The JWT `sub` claim is used directly as the workspace directory name.
- Message grouping: `tool_use` is inserted after the streaming assistant that triggered it. `assistant_delta` and `thinking_delta` after `tool_use` create a NEW assistant message (grouped with that tool_use's turn).

### Frontend (React / Vite + Vitest)

- **`client/App.jsx`** — Root component with `ChatApp` sub-component. Manages chat list state, WebSocket connection, and message handling. Uses `selectedChatIdRef` to avoid stale closures in WebSocket callbacks. `connectingRef` prevents duplicate WS connections.
- **`client/components/ChatList.jsx`** — Left sidebar showing chat list.
- **`client/components/ChatWindow.jsx`** — Main chat area. Renders `MessageBubble`, `ThinkingBlock`, and `ToolUseBlock`. Auto-scrolls only when user is near bottom. Leading newlines stripped from message content.
- **`client/components/FileUpload.jsx`** — File upload button with paperclip icon. Requires `token` prop.

**Key patterns:**
- **No draft chat state:** "New Chat" creates a temp chat locally, but does NOT add it to the chats list. First message triggers backend auto-creation.
- History messages: `history` type from WebSocket loads stored messages for the subscribed chat.
- `tool_use` is inserted after the streaming assistant that triggered it. `assistant_delta` and `thinking_delta` arriving after `tool_use` create a NEW assistant message (grouped with that tool_use's turn).
- WebSocket `connectWebSocket` guarded by `connectingRef` to prevent duplicate connections in StrictMode dev.

### WebSocket Protocol

| Type | Direction | Description |
|------|-----------|-------------|
| `subscribe` | Client → Server | Subscribe to a chat (requires `authorization` Bearer token) |
| `chat` | Client → Server | Send a user message |
| `stop` | Client → Server | Stop current assistant response |
| `connected` | Server → Client | Connection established |
| `history` | Server → Client | Existing messages for subscribed chat |
| `user_message` | Server → Client | User message echoed back |
| `assistant_delta` | Server → Client | Streaming text chunk (batched) |
| `thinking_delta` | Server → Client | Streaming thinking chunk (batched) |
| `tool_use` | Server → Client | Tool use block |
| `result` | Server → Client | Query completed |
| `interrupted` | Server → Client | Response was cancelled |
| `error` | Server → Client | Error occurred |

### Environment Variables

The backend reads these from `.env`:
- `ANTHROPIC_API_KEY` — Required for `claude-agent-sdk`
- `ANTHROPIC_BASE_URL` — Optional API base URL
- `MODEL` — Optional model override (default: `MiniMax-M2.7`)
- `PORT` — Backend port (default: `3001`)
- `AGENT_PROJECT_ROOT` — Base directory for per-user workspaces. Each user's files go under `{AGENT_PROJECT_ROOT}/{user_id}/`. Defaults to `.` (project root).
- `JWT_SECRET` — Secret key for JWT signing (min 32 bytes)
- `JWT_EXPIRE_HOURS` — Token expiry in hours (default: 24)

## Testing

**Minimum coverage: 80%** for functions, branches, lines, and statements.

**Python tests:** 91 tests, run with `uv run pytest`. Key test files:
- `tests/test_init_flow.py` — Init + chat flow integration tests
- `tests/test_ws_history_flow.py` — WebSocket history and chat switching
- `tests/test_chat_store.py` — Chat store unit tests
- `tests/test_session.py` — Session broadcast and interrupt tests

**Frontend tests:** 20 tests, run with `npm test`. Uses Vitest + React Testing Library.
- `client/tests/ChatList.test.jsx` — 6 tests
- `client/tests/ChatWindow.test.jsx` — 14 tests

## Important Notes

- The `claude-agent-sdk` package is installed from a local wheel. Do not upgrade from PyPI.
- Frontend runs on port `5173` with proxy to backend `3001`. Access app at `http://localhost:5173`.
- Python package managed with `uv`. Dependencies in `pyproject.toml`.
- `server/__init__.py` required for `PYTHONPATH=.` imports.
- All protected endpoints require `Authorization: Bearer <token>` header.
- Workspace data stored in `data/workspaces/{user_id}/` (gitignored).
- Database: `data/chats.db` (gitignored), shared SQLite with `user_id` column for isolation.