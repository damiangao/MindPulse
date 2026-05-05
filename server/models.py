from dataclasses import dataclass
from typing import Literal


@dataclass
class User:
    id: str
    email: str
    password_hash: str
    created_at: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "email": self.email,
            "createdAt": self.created_at,
        }


@dataclass
class Chat:
    id: str
    session_id: str | None
    user_id: str
    title: str
    created_at: str
    updated_at: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "sessionId": self.session_id,
            "userId": self.user_id,
            "title": self.title,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
        }


@dataclass
class ChatMessage:
    id: str
    chat_id: str
    user_id: str
    role: Literal["user", "assistant"]
    content: str
    timestamp: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "chatId": self.chat_id,
            "userId": self.user_id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
        }


@dataclass
class WSChatMessage:
    type: Literal["chat"]
    content: str
    chat_id: str


@dataclass
class WSSubscribeMessage:
    type: Literal["subscribe"]
    chat_id: str
    user_id: str


IncomingWSMessage = WSChatMessage | WSSubscribeMessage
