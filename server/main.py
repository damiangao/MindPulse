import json
import logging
import os
import sys
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from server._logging import setup_logger
from server.ai_client import AgentSession
from server.auth import decode_token
from server.auth_routes import router as auth_router
from server.chat_store import chat_store
from server.session import Session

load_dotenv(override=True)

PORT = int(os.getenv("PORT", "3001"))

# Configure uvicorn/fastapi logging to include date+time
LOG_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"
for _uvlogger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
    _uvlog = logging.getLogger(_uvlogger_name)
    _uvlog.handlers.clear()
    _uvconsole = logging.StreamHandler(sys.stderr)
    _uvconsole.setFormatter(logging.Formatter(
        f"%(asctime)s [%(process)d] %(levelname)s: %(message)s",
        datefmt=LOG_TIMESTAMP_FORMAT,
    ))
    _uvlog.addHandler(_uvconsole)
    _uvlog.setLevel(logging.INFO)

_logger = setup_logger("main")

# Session management: (chat_id, workspace_id) -> Session
_sessions: dict[tuple[str, str], Session] = {}


def get_or_create_session(chat_id: str, workspace_id: str) -> Session:
    key = (chat_id, workspace_id)
    if key not in _sessions:
        _sessions[key] = Session(chat_id, workspace_id)
    return _sessions[key]


def get_current_user(authorization: str = ""):
    """Extract and verify JWT from Authorization Bearer header. Returns (user_id, workspace_id)."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization[7:]
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # Use user_id as workspace_id for account-level isolation
    return payload["sub"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    # Cleanup on shutdown
    for session in _sessions.values():
        await session.close()
    _sessions.clear()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth routes (no auth required)
app.include_router(auth_router)

# Serve static files from client directory
app.mount("/client", StaticFiles(directory="client"), name="client")


@app.get("/", response_class=HTMLResponse)
async def root():
    return FileResponse("client/index.html")


# REST API: Get all chats (auth required)
@app.get("/api/chats")
async def get_chats(user_id: str = Depends(get_current_user)):
    chats = chat_store.get_all_chats(user_id)
    return [c.to_dict() for c in chats]


async def _create_sdk_chat(workspace_id: str, title: str | None = None) -> dict:
    """Create a new chat by initializing an AgentSession and extracting session_id."""
    agent_session = AgentSession()
    session_id = await agent_session.init()

    if not session_id:
        raise HTTPException(status_code=500, detail="Failed to create chat session")

    chat = chat_store.create_chat(session_id, workspace_id, title)
    return chat.to_dict()


# REST API: Create new chat (auth required)
@app.post("/api/chats")
async def create_chat(payload: dict | None = None, user_id: str = Depends(get_current_user)):
    return await _create_sdk_chat(user_id, payload.get("title") if payload else None)


# REST API: Initialize a draft chat with SDK session (auth required)
@app.post("/api/chats/init")
async def init_chat(payload: dict, user_id: str = Depends(get_current_user)):
    temp_id = payload.get("tempId")
    if not temp_id:
        raise HTTPException(status_code=400, detail="tempId is required")

    return await _create_sdk_chat(user_id, payload.get("title") if payload else None)


# REST API: Get single chat (auth required)
@app.get("/api/chats/{chat_id}")
async def get_chat(chat_id: str, user_id: str = Depends(get_current_user)):
    chat = chat_store.get_chat(chat_id, user_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat.to_dict()


# REST API: Delete chat (auth required)
@app.delete("/api/chats/{chat_id}")
async def delete_chat(chat_id: str, user_id: str = Depends(get_current_user)):
    deleted = chat_store.delete_chat(chat_id, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Chat not found")
    session = _sessions.get((chat_id, user_id))
    if session:
        await session.close()
        del _sessions[(chat_id, user_id)]
    return {"success": True}


# REST API: Get chat messages (auth required)
@app.get("/api/chats/{chat_id}/messages")
async def get_messages(chat_id: str, user_id: str = Depends(get_current_user)):
    messages = chat_store.get_messages(chat_id, user_id)
    return [m.to_dict() for m in messages]


# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    _logger.info("WebSocket client connected")

    await websocket.send_json({
        "type": "connected",
        "message": "Connected to chat server",
    })

    # State for this connection
    chat_id: str | None = None
    user_id: str | None = None

    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                msg_type = message.get("type")

                if msg_type == "subscribe":
                    auth_header = message.get("authorization", "")
                    if not auth_header.startswith("Bearer "):
                        await websocket.send_json({
                            "type": "error",
                            "error": "Missing or invalid Authorization header",
                        })
                        continue

                    token = auth_header[7:]
                    payload = decode_token(token)
                    if not payload:
                        await websocket.send_json({
                            "type": "error",
                            "error": "Invalid or expired token",
                        })
                        continue

                    user_id = payload["sub"]
                    chat_id = message.get("chatId")

                    if not chat_id:
                        await websocket.send_json({
                            "type": "error",
                            "error": "chatId is required",
                        })
                        continue

                    session = get_or_create_session(chat_id, user_id)
                    session.subscribe(websocket)
                    _logger.debug(f"Client subscribed to chat {chat_id} as user {user_id}")

                    # Send existing messages
                    messages = chat_store.get_messages(chat_id, user_id)
                    await websocket.send_json({
                        "type": "history",
                        "messages": [m.to_dict() for m in messages],
                        "chatId": chat_id,
                    })

                elif msg_type == "chat":
                    if not chat_id or not user_id:
                        await websocket.send_json({
                            "type": "error",
                            "error": "Must subscribe first",
                        })
                        continue
                    content = message["content"]
                    _logger.debug(f"[WebSocket] Received chat message for chat_id={chat_id}, content={content[:50]}...")
                    session = get_or_create_session(chat_id, user_id)
                    await session.send_message(content)
                    _logger.debug(f"[WebSocket] Finished processing chat message for chat_id={chat_id}")

                elif msg_type == "stop":
                    if not chat_id or not user_id:
                        await websocket.send_json({
                            "type": "error",
                            "error": "Must subscribe first",
                        })
                        continue
                    _logger.debug(f"[WebSocket] Received stop request for chat_id={chat_id}")
                    session = get_or_create_session(chat_id, user_id)
                    await session.stop_response()
                    _logger.debug(f"[WebSocket] Finished processing stop request for chat_id={chat_id}")

                else:
                    _logger.warning(f"Unknown message type: {msg_type}")

            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "error": "Invalid message format",
                })
            except Exception as e:
                _logger.error(f"Error handling WebSocket message: {e}")
                await websocket.send_json({
                    "type": "error",
                    "error": str(e),
                })

    except WebSocketDisconnect:
        _logger.info("WebSocket client disconnected")
        # Unsubscribe from all sessions and clean up empty ones
        if chat_id and user_id:
            key = (chat_id, user_id)
            session = _sessions.get(key)
            if session:
                still_alive = session.unsubscribe(websocket)
                if not still_alive:
                    _sessions.pop(key, None)
                    _logger.info(f"Cleaned up session {chat_id}")


def main():
    import uvicorn

    _logger.info(f"Server running at http://localhost:{PORT}")
    _logger.info(f"WebSocket endpoint available at ws://localhost:{PORT}/ws")
    _logger.info(f"Visit http://localhost:{PORT} to view the chat interface")

    uvicorn.run(
        "server.main:app",
        host="0.0.0.0",
        port=PORT,
        reload=True,
        ws="websockets",
    )


if __name__ == "__main__":
    main()