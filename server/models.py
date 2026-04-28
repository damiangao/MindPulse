from dataclasses import dataclass, field
from typing import Literal


@dataclass
class Chat:
    id: str
    title: str
    created_at: str
    updated_at: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
        }


@dataclass
class ChatMessage:
    id: str
    chat_id: str
    role: Literal["user", "assistant"]
    content: str
    timestamp: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "chatId": self.chat_id,
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


IncomingWSMessage = WSChatMessage | WSSubscribeMessage
