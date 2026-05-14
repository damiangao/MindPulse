# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A chat web application with a Python FastAPI backend and React frontend. AI conversations are powered by the `claude-agent-sdk` Python package via WebSocket. Features SQLite persistence with per-account workspace isolation, and JWT-based authentication.

## Development Commands

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

# Run all tests
PYTHONPATH=. .venv/bin/python -m pytest tests/ -x  # 92 Python tests
npm test                                               # 22 frontend tests (Vitest)
npm test -- --coverage                                # with coverage

# Run a single test file
PYTHONPATH=. .venv/bin/python -m pytest tests/test_chat_store.py

# Lint and format Python
uv run ruff check .
uv run ruff format .

# Type check Python
uv run pyright

# Run the backend directly
PYTHONPATH=. uv run python -m server.main
```

The backend reads `.env` via `load_dotenv()` in `server/main.py`. Any code using `claude-agent-sdk` directly (tests, scripts) must call `load_dotenv()` before importing the SDK.

## Architecture

### Backend (Python / FastAPI)

- **`server/main.py`** — FastAPI app with REST API and WebSocket endpoint (`/ws`). Maintains a `_sessions` dict of `Session` objects. On WebSocket disconnect, unsubscribes the client and cleans up sessions with no remaining subscribers.
- **`server/session.py`** — `Session` class manages one chat session. It wraps `AgentSession`, stores messages via `chat_store`, and broadcasts responses to WebSocket subscribers. Uses `StreamEvent` from the SDK for streaming output, with a `_DELTA_BUFFER_SIZE` of 20 chars to batch small deltas before broadcasting. Supports interruption: calling `send_message()` while a response is in-flight cancels the old task and calls `interrupt()` on the agent.
- **`server/ai_client.py`** — `AgentSession` wraps `ClaudeSDKClient` from `claude-agent-sdk`. Uses a long-lived connection with an `asyncio.Queue` for streaming input, allowing interruption without reconnecting. Yields SDK messages until `ResultMessage`. Extracts `session_id` from `SystemMessage(subtype="init")`. Per-user workspace is `{AGENT_PROJECT_ROOT}/{user_id}/`.
- **`server/chat_store.py`** — SQLite-backed `ChatStore`. Uses per-user `get_workspace_db()` connections with WAL mode. `create_chat()` takes an external ID (the SDK's `session_id`). `add_message()` auto-updates the chat title from the first user message.
- **`server/models.py`** — Dataclasses: `User`, `Chat`, `ChatMessage`.
- **`server/auth.py`** — JWT auth utilities: `create_token()`, `decode_token()`, `hash_password()`, `verify_password()`.
- **`server/auth_routes.py`** — Auth endpoints: `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`.
- **`server/file_storage.py`** — File CRUD utility. Files stored at `{AGENT_PROJECT_ROOT}/{user_id}/{filename}`. Supports list, upload, download, delete, rename, mkdir operations.
- **`server/database/connection.py`** — SQLite connections at `data/chats.db` with WAL mode. Caches connections by user.
- **`server/database/repositories/chat.py`** — `ChatRepository` with `create_chat()`, `get_chat()`, `get_all_chats()`, `update_title()`, `delete()`.
- **`server/database/repositories/message.py`** — `MessageRepository` with `add_message()`, `get_messages()`.
- **`server/_logging.py`** — Shared logging setup with file + console handlers.

### Frontend (React / Vite + Vitest)

- **`client/App.jsx`** — Root component with `ChatApp` sub-component. Manages chat list state, WebSocket connection, message handling, and config fetch. Uses `selectedChatIdRef` to avoid stale closures. `connectingRef` prevents duplicate WS connections.
- **`client/components/ChatList.jsx`** — Left sidebar showing chat list.
- **`client/components/ChatWindow.jsx`** — Main chat area. Renders `MessageBubble`, `ThinkingBlock`, and `ToolUseBlock`. Auto-scrolls only when user is near bottom. Leading newlines stripped from message content.
- **`client/components/FileBrowser/`** — File browser with VSCode-style tree view, right-click context menu, and drag-drop upload. Tab-switchable with chat list.
  - `FileTree.jsx` — Tree root with refresh button
  - `FileTreeNode.jsx` — Single node with expand/collapse
  - `ContextMenu.jsx` — Right-click menu: Add to chat, Download, Rename, Delete, New folder
  - `UploadZone.jsx` — Drag-drop upload zone

## Key Patterns

**Simplified chat creation:** "New Chat" creates a local temp chat (UUID not in sidebar). First message sent via WebSocket auto-creates the chat and session in the backend. Chat appears in sidebar after `result` event triggers `fetchChats()`.

**Chat IDs are SDK `session_id`s.** The `session_id` is captured from `SystemMessage(subtype="init")` and stored in the `chats` table.

**Workspace isolation:** The JWT `sub` claim is used directly as the workspace directory name. All file operations are scoped to `{user_id}/` paths.

**Message grouping:** `tool_use` is inserted after the streaming assistant that triggered it. `assistant_delta` and `thinking_delta` after `tool_use` create a NEW assistant message (grouped with that tool_use's turn).

**On interruption:** `Session._process_response()` catches `asyncio.CancelledError`, broadcasts an `interrupted` event, and does NOT persist partial output.

## WebSocket Protocol

| Type | Direction | Description |
|------|-----------|-------------|
| `subscribe` | Client → Server | Subscribe to a chat (requires `authorization` Bearer token) |
| `chat` | Client → Server | Send a user message |
| `stop` | Client → Server | Stop current assistant response |
| `connected` | Server → Client | Connection established |
| `history` | Server → Client | Existing messages for subscribed chat |
| `assistant_delta` | Server → Client | Streaming text chunk (batched) |
| `thinking_delta` | Server → Client | Streaming thinking chunk (batched) |
| `tool_use` | Server → Client | Tool use block |
| `result` | Server → Client | Query completed |
| `interrupted` | Server → Client | Response was cancelled |
| `error` | Server → Client | Error occurred |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | (required) | API key for `claude-agent-sdk` |
| `ANTHROPIC_BASE_URL` | (optional) | API base URL override |
| `MODEL` | `MiniMax-M2.7` | Model override |
| `PORT` | `3001` | Backend port |
| `AGENT_PROJECT_ROOT` | `.` | Base dir for per-user workspaces. Each user's files go under `{AGENT_PROJECT_ROOT}/{user_id}/`. |
| `JWT_SECRET` | (required) | Secret key for JWT signing (min 32 bytes) |
| `JWT_EXPIRE_HOURS` | `24` | Token expiry in hours |

## Testing

**Minimum coverage: 80%** for functions, branches, lines, and statements.

**Python tests:** 92 tests, run with `PYTHONPATH=. .venv/bin/python -m pytest tests/ -x`.
- `tests/test_init_flow.py` — Init + chat flow integration tests
- `tests/test_ws_history_flow.py` — WebSocket history and chat switching
- `tests/test_chat_store.py` — Chat store unit tests
- `tests/test_session.py` — Session broadcast and interrupt tests
- `tests/test_file_storage.py` — File storage utility tests

**Frontend tests:** 22 tests, run with `npm test`. Uses Vitest + React Testing Library.
- `client/tests/ChatList.test.jsx` — 6 tests
- `client/tests/ChatWindow.test.jsx` — 14 tests

**E2E tests:** Run with `npx playwright test`. Playwright config at `playwright.config.js`.

E2E tests must verify **end-to-end outcomes**, not just UI presence:
- ✅ "Upload a file, then verify it appears in the file tree"
- ✅ "Right-click a file, select 'Add to chat', then verify the path is in the input"
- ✅ "Delete a file, then verify it's gone from the list after refresh"
- ❌ NOT: "Click upload button and verify it exists"

Key E2E test files:
- `e2e/file-browser.spec.js` — File browser tab switch, tree load, upload, right-click menu, path insertion
- `e2e/session-resume.spec.js` — Chat history resume
- `e2e/full-flow.spec.js` — Register → login → create chat → send message

## Important Notes

- The `claude-agent-sdk` package is installed from a local wheel. Do not upgrade from PyPI.
- Frontend runs on port `5173` with proxy to backend `3001`. Access app at `http://localhost:5173`.
- Python package managed with `uv`. Dependencies in `pyproject.toml`.
- `server/__init__.py` required for `PYTHONPATH=.` imports.
- All protected endpoints require `Authorization: Bearer <token>` header.
- Workspace files stored in `{AGENT_PROJECT_ROOT}/{user_id}/` (gitignored).
- Database: `data/chats.db` (gitignored), shared SQLite with `user_id` column for isolation.
- File download: `GET /api/files/download?path=...` requires `Authorization` header (uses `fetch` + blob, not `window.location.href`).
- `/api/config` returns `{"workspace_root": get_project_root()}` — used by FileBrowser to construct correct absolute paths for "Add to chat".

## Documentation

- **`docs/ARCHITECTURE.md`** — System architecture, data models, and communication protocol (in Chinese)
- **`docs/claude_agent_sdk.md`** — Claude Agent SDK 完整文档，包含 API 参考和使用示例