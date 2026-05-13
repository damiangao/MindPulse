# Simple Chat App (Python)

A chat web application with a Python FastAPI backend and React frontend. AI conversations are powered by the `claude-agent-sdk` Python package via WebSocket, with SQLite persistence and per-account workspace isolation.

## Prerequisites

- Python 3.10+ with [UV](https://docs.astral.sh/uv/)
- Node.js + npm
- Anthropic API key

## Quick Start

```bash
# 1. Copy and edit environment variables
cp .env.example .env
# Edit .env: add ANTHROPIC_API_KEY

# 2. Install dependencies
uv sync
npm install

# 3. Start both backend and frontend
npm run dev
```

Visit http://localhost:5173 to use the app.

## Architecture

- **Frontend:** React + Vite (port 5173)
- **Backend:** Python + FastAPI (port 3001) with WebSocket support
- **Database:** SQLite at `data/chats.db` with WAL mode, per-account data isolation via `user_id` column
- **Auth:** JWT-based with bcrypt password hashing
- **Agent:** `claude-agent-sdk` Python with streaming via `StreamEvent`

## Project Structure

```
├── server/                  # Python backend
│   ├── main.py              # FastAPI app (REST + WebSocket)
│   ├── session.py           # Per-chat Session (broadcast, interrupt)
│   ├── ai_client.py         # AgentSession wrapper for SDK
│   ├── chat_store.py        # SQLite-backed chat persistence
│   ├── auth.py              # JWT utilities
│   ├── auth_routes.py       # /api/auth/* endpoints
│   ├── file_storage.py      # File upload/download
│   └── database/            # SQLite connection + repositories
├── client/                  # React frontend
│   ├── App.jsx              # Root + ChatApp component
│   ├── components/          # ChatList, ChatWindow, FileUpload
│   └── tests/               # Vitest tests
├── deploy/                  # Deployment configs
│   ├── docker-compose.yml   # Production Docker Compose
│   ├── docker-compose.dev.yml  # Development Docker Compose
│   ├── Dockerfile.server    # Backend image
│   ├── Dockerfile.client    # Frontend image (Nginx)
│   ├── nginx.conf          # Nginx config
│   └── k8s/               # Kubernetes configs
├── data/                    # Workspace data (gitignored)
│   └── workspaces/          # Per-user workspace dirs
│       └── {user_id}/      # Agent files + uploaded files
├── docs/                    # Documentation
├── pyproject.toml          # UV config
├── package.json             # npm scripts
├── vite.config.js           # Vite + Vitest config
└── CLAUDE.md               # Developer guidance
```

## Commands

```bash
npm run dev          # Start both backend + frontend
npm run dev:server   # Backend only
npm run dev:client   # Frontend only
npm test             # Frontend tests (Vitest)
uv run pytest        # Backend tests (pytest)
```

## API Overview

**REST:** `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/chats`, `POST /api/chats/init`, `POST /api/files/upload`, `GET /api/files/download`

**WebSocket `/ws`:** Send `subscribe` (with Bearer token), `chat`, `stop`. Receive `connected`, `history`, `assistant_delta`, `thinking_delta`, `tool_use`, `result`, `interrupted`, `error`.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | (required) | API key for claude-agent-sdk |
| `ANTHROPIC_BASE_URL` | `https://api.minimaxi.com/anthropic` | API base URL |
| `MODEL` | `MiniMax-M2.7` | Model override |
| `PORT` | `3001` | Backend port |
| `AGENT_PROJECT_ROOT` | `.` | Base dir for per-user workspaces |
| `JWT_SECRET` | (insecure default) | JWT signing key |
| `JWT_EXPIRE_HOURS` | `24` | Token expiry |