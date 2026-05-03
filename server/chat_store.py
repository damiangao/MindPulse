"""DB-backed chat store with workspace isolation."""

from server.database.connection import get_workspace_db
from server.database.repositories.chat import ChatRepository
from server.database.repositories.message import MessageRepository
from server.models import Chat, ChatMessage


class ChatStore:
    """DB-backed chat store using SQLite.

    All operations are scoped to a workspace_id which must be
    passed to each method.
    """

    def create_chat(self, chat_id: str, workspace_id: str, title: str | None = None) -> "Chat":
        """Create a new chat in the workspace."""
        with get_workspace_db(workspace_id) as conn:
            repo = ChatRepository(conn, workspace_id)
            return repo.create_chat(chat_id, title)

    def get_chat(self, chat_id: str, workspace_id: str) -> "Chat | None":
        """Get a chat by ID in the workspace."""
        with get_workspace_db(workspace_id) as conn:
            repo = ChatRepository(conn, workspace_id)
            return repo.get_chat(chat_id)

    def get_all_chats(self, workspace_id: str) -> list["Chat"]:
        """Get all chats in the workspace, sorted by updated_at DESC."""
        with get_workspace_db(workspace_id) as conn:
            repo = ChatRepository(conn, workspace_id)
            return repo.get_all_chats()

    def update_chat_title(self, chat_id: str, workspace_id: str, title: str) -> "Chat | None":
        """Update a chat's title."""
        with get_workspace_db(workspace_id) as conn:
            repo = ChatRepository(conn, workspace_id)
            return repo.update_title(chat_id, title)

    def delete_chat(self, chat_id: str, workspace_id: str) -> bool:
        """Delete a chat."""
        with get_workspace_db(workspace_id) as conn:
            repo = ChatRepository(conn, workspace_id)
            return repo.delete(chat_id)

    def add_message(
        self,
        chat_id: str,
        workspace_id: str,
        role: str,
        content: str,
    ) -> "ChatMessage":
        """Add a message to a chat. Also updates chat's updated_at and auto-titles.

        Raises:
            ValueError: If the chat does not exist in the workspace
        """
        with get_workspace_db(workspace_id) as conn:
            chat_repo = ChatRepository(conn, workspace_id)
            # Check that the chat exists
            chat = chat_repo.get_chat(chat_id)
            if chat is None:
                raise ValueError(f"Chat {chat_id} not found in workspace {workspace_id}")

            msg_repo = MessageRepository(conn, workspace_id)
            msg = msg_repo.add_message(chat_id, role, content)

            # Update chat's updated_at and auto-generate title from first user message
            chat_repo = ChatRepository(conn, workspace_id)
            chat = chat_repo.get_chat(chat_id)
            if chat and chat.title == "New Chat" and role == "user":
                title = content[:50] + ("..." if len(content) > 50 else "")
                chat_repo.update_title(chat_id, title)
            elif chat:
                chat_repo.touch(chat_id)

            return msg

    def get_messages(self, chat_id: str, workspace_id: str) -> list["ChatMessage"]:
        """Get all messages for a chat."""
        with get_workspace_db(workspace_id) as conn:
            repo = MessageRepository(conn, workspace_id)
            return repo.get_messages(chat_id)


# Backwards-compatible singleton instance (workspace_id must be passed to each method)
chat_store = ChatStore()
