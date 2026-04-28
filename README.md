# Simple Chat App (Python)

A minimal chat application demonstrating the Claude Agent SDK Python version.

## Architecture

- **Frontend**: React + Vite + Tailwind CSS (JSX version, same as original)
- **Backend**: Python + FastAPI + WebSocket (websockets)
- **Agent**: Claude Agent SDK Python integrated directly on the server
- **Package Manager**: UV (Python), npm (frontend dev server)
- **Config**: pyproject.toml, package.json

## Prerequisites

- Python 3.10+
- [UV](https://docs.astral.sh/uv/) package manager
- Node.js + npm
- Anthropic API key

## Running the App

```bash
# 1. Copy environment variables
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# 2. Install Python dependencies
uv sync

# 3. Install Node dependencies (for Vite dev server)
npm install

# 4. Kill any existing processes on the ports (macOS/Linux)
lsof -ti:3001 | xargs kill -9 2>/dev/null
lsof -ti:5173 | xargs kill -9 2>/dev/null

# 5. Start both backend and frontend
npm run dev
```

This starts:
- Backend server on http://localhost:3001
- Vite dev server on http://localhost:5173

Visit http://localhost:5173 to view the chat interface.


## Project Structure

```
├── server/                    # Python backend
│   ├── main.py               # FastAPI server (REST + WebSocket)
│   ├── ai_client.py          # Claude Agent SDK wrapper
│   ├── session.py            # Chat session management
│   ├── chat_store.py         # In-memory chat storage
│   └── models.py             # Python dataclasses
├── client/                    # React frontend (JSX)
│   ├── App.jsx               # Main app component
│   ├── index.jsx             # Entry point
│   ├── index.html            # HTML template
│   └── components/
│       ├── ChatList.jsx      # Left sidebar with chat list
│       └── ChatWindow.jsx    # Main chat interface
├── pyproject.toml            # UV project config
├── package.json              # npm scripts and frontend deps
├── vite.config.js            # Vite configuration
├── .env.example              # Environment template
└── .gitignore
```

## Available Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start both backend and frontend (uses concurrently) |
| `npm run dev:server` | Start only the FastAPI backend |
| `npm run dev:client` | Start only the Vite dev server |
| `npm run build` | Build frontend for production |

## API Endpoints

### REST API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/chats` | List all chats |
| POST | `/api/chats` | Create new chat |
| GET | `/api/chats/{id}` | Get chat details |
| DELETE | `/api/chats/{id}` | Delete chat |
| GET | `/api/chats/{id}/messages` | Get chat messages |

### WebSocket (`ws://localhost:3001/ws`)

**Client -> Server:**
- `{ type: "subscribe", chatId: string }` - Subscribe to a chat
- `{ type: "chat", chatId: string, content: string }` - Send message

**Server -> Client:**
- `{ type: "connected" }` - Connection established
- `{ type: "history", messages: [...] }` - Chat history
- `{ type: "assistant_message", content: string }` - AI response
- `{ type: "tool_use", toolName: string, toolInput: {...} }` - Tool being used
- `{ type: "result", success: boolean }` - Query complete
- `{ type: "error", error: string }` - Error occurred

## Notes

- In-memory storage (data lost on restart)
- Agent has access to: Bash, Read, Write, Edit, Glob, Grep, WebSearch, WebFetch
- Uses `ClaudeSDKClient` for multi-turn conversations with the Python SDK
- FastAPI handles both REST API and WebSocket in a single server
