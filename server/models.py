from dataclasses import dataclass, field
from typing import Literal


@dataclass
class Chat:
    id: str
    title: str
    created_at: str
    updated_at: str


@dataclass
class ChatMessage:
    id: str
    chat_id: str
    role: Literal["user", "assistant"]
    content: str
    timestamp: str


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
