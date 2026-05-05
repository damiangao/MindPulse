"""DB-backed chat store with user isolation."""

from server.database.connection import get_workspace_db
from server.database.repositories.chat import ChatRepository
from server.database.repositories.message import MessageRepository
from server.models import Chat, ChatMessage


class ChatStore:
    """DB-backed chat store using SQLite.

    All operations are scoped to a user_id which must be
    passed to each method.
    """

    def create_chat(self, chat_id: str, user_id: str, title: str | None = None, session_id: str | None = None) -> "Chat":
        """Create a new chat for the user."""
        with get_workspace_db(user_id) as conn:
            repo = ChatRepository(conn, user_id)
            return repo.create_chat(chat_id, title, session_id)

    def get_chat(self, chat_id: str, user_id: str) -> "Chat | None":
        """Get a chat by ID for the user."""
        with get_workspace_db(user_id) as conn:
            repo = ChatRepository(conn, user_id)
            return repo.get_chat(chat_id)

    def get_all_chats(self, user_id: str) -> list["Chat"]:
        """Get all chats for the user, sorted by updated_at DESC."""
        with get_workspace_db(user_id) as conn:
            repo = ChatRepository(conn, user_id)
            return repo.get_all_chats()

    def update_chat_title(self, chat_id: str, user_id: str, title: str) -> "Chat | None":
        """Update a chat's title."""
        with get_workspace_db(user_id) as conn:
            repo = ChatRepository(conn, user_id)
            return repo.update_title(chat_id, title)

    def delete_chat(self, chat_id: str, user_id: str) -> bool:
        """Delete a chat."""
        with get_workspace_db(user_id) as conn:
            repo = ChatRepository(conn, user_id)
            return repo.delete(chat_id)

    def add_message(
        self,
        chat_id: str,
        user_id: str,
        role: str,
        content: str,
    ) -> "ChatMessage":
        """Add a message to a chat. Also updates chat's updated_at and auto-titles.

        Raises:
            ValueError: If the chat does not exist for the user
            TypeError: If role is not 'user' or 'assistant'
        """
        if role not in ("user", "assistant"):
            raise TypeError(f"Invalid role: {role}")
        with get_workspace_db(user_id) as conn:
            chat_repo = ChatRepository(conn, user_id)
            chat = chat_repo.get_chat(chat_id)
            if chat is None:
                raise ValueError(f"Chat {chat_id} not found for user {user_id}")

            msg_repo = MessageRepository(conn, user_id)
            msg = msg_repo.add_message(chat_id, role, content)

            # Auto-title from first user message; otherwise just update timestamp
            if chat.title == "New Chat" and role == "user":
                title = content[:50] + ("..." if len(content) > 50 else "")
                chat_repo.update_title(chat_id, title)
            else:
                chat_repo.touch(chat_id)

            return msg

    def get_messages(self, chat_id: str, user_id: str) -> list["ChatMessage"]:
        """Get all messages for a chat."""
        with get_workspace_db(user_id) as conn:
            repo = MessageRepository(conn, user_id)
            return repo.get_messages(chat_id)


# Singleton instance
chat_store = ChatStore()
