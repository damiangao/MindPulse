import asyncio
import json
import os
from contextlib import asynccontextmanager

from claude_agent_sdk import ClaudeSDKClient, SystemMessage
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from server.ai_client import AgentSession
from server.chat_store import chat_store
from server.session import Session

load_dotenv(override=True)

PORT = int(os.getenv("PORT", "3001"))

# Session management
_sessions: dict[str, Session] = {}


def get_or_create_session(chat_id: str) -> Session:
    if chat_id not in _sessions:
        _sessions[chat_id] = Session(chat_id)
    return _sessions[chat_id]


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

# Serve static files from client directory
app.mount("/client", StaticFiles(directory="client"), name="client")


@app.get("/", response_class=HTMLResponse)
async def root():
    return FileResponse("client/index.html")


# REST API: Get all chats
@app.get("/api/chats")
async def get_chats():
    chats = chat_store.get_all_chats()
    return [
        {
            "id": c.id,
            "title": c.title,
            "createdAt": c.created_at,
            "updatedAt": c.updated_at,
        }
        for c in chats
    ]


# REST API: Create new chat (legacy, can still be used directly if needed)
@app.post("/api/chats")
async def create_chat(payload: dict | None = None):
    # Create an AgentSession to get the SDK's session_id as the chat ID
    agent_session = AgentSession()
    async with ClaudeSDKClient(options=agent_session._options) as client:
        await client.query("hi")
        session_id = None
        async for message in client.receive_response():
            if isinstance(message, SystemMessage) and message.subtype == "init":
                session_id = message.data.get("session_id")
                break

    if not session_id:
        return {"error": "Failed to create chat session"}, 500

    chat = chat_store.create_chat(session_id, payload.get("title") if payload else None)
    return {
        "id": chat.id,
        "title": chat.title,
        "createdAt": chat.created_at,
        "updatedAt": chat.updated_at,
    }


# REST API: Initialize a draft chat with SDK session
@app.post("/api/chats/init")
async def init_chat(payload: dict):
    temp_id = payload.get("tempId")
    if not temp_id:
        return {"error": "tempId is required"}, 400

    # Create an AgentSession to get the SDK's session_id
    agent_session = AgentSession()
    async with ClaudeSDKClient(options=agent_session._options) as client:
        await client.query("hi")
        session_id = None
        async for message in client.receive_response():
            if isinstance(message, SystemMessage) and message.subtype == "init":
                session_id = message.data.get("session_id")
                break

    if not session_id:
        return {"error": "Failed to create chat session"}, 500

    chat = chat_store.create_chat(session_id, payload.get("title") if payload else None)
    return {
        "id": chat.id,
        "title": chat.title,
        "createdAt": chat.created_at,
        "updatedAt": chat.updated_at,
    }


# REST API: Get single chat
@app.get("/api/chats/{chat_id}")
async def get_chat(chat_id: str):
    chat = chat_store.get_chat(chat_id)
    if not chat:
        return {"error": "Chat not found"}, 404
    return {
        "id": chat.id,
        "title": chat.title,
        "createdAt": chat.created_at,
        "updatedAt": chat.updated_at,
    }


# REST API: Delete chat
@app.delete("/api/chats/{chat_id}")
async def delete_chat(chat_id: str):
    deleted = chat_store.delete_chat(chat_id)
    if not deleted:
        return {"error": "Chat not found"}, 404
    session = _sessions.get(chat_id)
    if session:
        await session.close()
        del _sessions[chat_id]
    return {"success": True}


# REST API: Get chat messages
@app.get("/api/chats/{chat_id}/messages")
async def get_messages(chat_id: str):
    messages = chat_store.get_messages(chat_id)
    return [
        {
            "id": m.id,
            "chatId": m.chat_id,
            "role": m.role,
            "content": m.content,
            "timestamp": m.timestamp,
        }
        for m in messages
    ]


# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("WebSocket client connected")

    await websocket.send_json({
        "type": "connected",
        "message": "Connected to chat server",
    })

    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                msg_type = message.get("type")

                if msg_type == "subscribe":
                    chat_id = message["chatId"]
                    session = get_or_create_session(chat_id)
                    session.subscribe(websocket)
                    print(f"Client subscribed to chat {chat_id}")

                    # Send existing messages
                    messages = chat_store.get_messages(chat_id)
                    await websocket.send_json({
                        "type": "history",
                        "messages": [
                            {
                                "id": m.id,
                                "chatId": m.chat_id,
                                "role": m.role,
                                "content": m.content,
                                "timestamp": m.timestamp,
                            }
                            for m in messages
                        ],
                        "chatId": chat_id,
                    })

                elif msg_type == "chat":
                    chat_id = message["chatId"]
                    content = message["content"]
                    session = get_or_create_session(chat_id)
                    await session.send_message(content)

                else:
                    print(f"Unknown message type: {msg_type}")

            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "error": "Invalid message format",
                })
            except Exception as e:
                print(f"Error handling WebSocket message: {e}")
                await websocket.send_json({
                    "type": "error",
                    "error": str(e),
                })

    except WebSocketDisconnect:
        print("WebSocket client disconnected")
        # Unsubscribe from all sessions
        for session in _sessions.values():
            session.unsubscribe(websocket)


def main():
    import uvicorn

    print(f"Server running at http://localhost:{PORT}")
    print(f"WebSocket endpoint available at ws://localhost:{PORT}/ws")
    print(f"Visit http://localhost:{PORT} to view the chat interface")

    uvicorn.run(
        "server.main:app",
        host="0.0.0.0",
        port=PORT,
        reload=True,
        ws="websockets",
    )


if __name__ == "__main__":
    main()
