import uuid
from datetime import datetime, timezone

from server.models import Chat, ChatMessage


class ChatStore:
    def __init__(self):
        self._chats: dict[str, Chat] = {}
        self._messages: dict[str, list[ChatMessage]] = {}

    def create_chat(self, chat_id: str, title: str | None = None) -> Chat:
        now = datetime.now(timezone.utc).isoformat()
        chat = Chat(
            id=chat_id,
            title=title or "New Chat",
            created_at=now,
            updated_at=now,
        )
        self._chats[chat_id] = chat
        self._messages[chat_id] = []
        return chat

    def get_chat(self, chat_id: str) -> Chat | None:
        return self._chats.get(chat_id)

    def get_all_chats(self) -> list[Chat]:
        return sorted(
            self._chats.values(),
            key=lambda c: c.updated_at,
            reverse=True,
        )

    def update_chat_title(self, chat_id: str, title: str) -> Chat | None:
        chat = self._chats.get(chat_id)
        if chat:
            chat.title = title
            chat.updated_at = datetime.now(timezone.utc).isoformat()
        return chat

    def delete_chat(self, chat_id: str) -> bool:
        self._messages.pop(chat_id, None)
        return self._chats.pop(chat_id, None) is not None

    def add_message(
        self,
        chat_id: str,
        role: str,
        content: str,
    ) -> ChatMessage:
        messages = self._messages.get(chat_id)
        if messages is None:
            raise ValueError(f"Chat {chat_id} not found")

        now = datetime.now(timezone.utc).isoformat()
        message = ChatMessage(
            id=str(uuid.uuid4()),
            chat_id=chat_id,
            role=role,  # type: ignore[arg-type]
            content=content,
            timestamp=now,
        )
        messages.append(message)

        # Update chat's updated_at
        chat = self._chats.get(chat_id)
        if chat:
            chat.updated_at = now
            # Auto-generate title from first user message
            if chat.title == "New Chat" and role == "user":
                chat.title = content[:50] + ("..." if len(content) > 50 else "")

        return message

    def get_messages(self, chat_id: str) -> list[ChatMessage]:
        return list(self._messages.get(chat_id, []))


chat_store = ChatStore()
