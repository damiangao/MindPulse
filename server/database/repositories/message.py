"""Message repository for database operations with workspace isolation."""

import sqlite3
import uuid
from datetime import datetime, timezone

from server.database.migrations import ensure_workspace
from server.models import ChatMessage


class MessageRepository:
    """Repository for message operations, scoped to a workspace."""

    def __init__(self, conn: sqlite3.Connection, workspace_id: str) -> None:
        """Initialize repository with connection and workspace ID.

        Args:
            conn: SQLite database connection
            workspace_id: Workspace identifier for data isolation
        """
        self._conn = conn
        self._workspace_id = workspace_id

    def _ensure_workspace(self) -> None:
        """Ensure the workspace exists before database operations.

        This is called before insert operations to guarantee
        the workspace record exists (since we share connections).
        """
        ensure_workspace(self._conn, self._workspace_id)
        self._conn.commit()

    def add_message(
        self, chat_id: str, role: str, content: str
    ) -> ChatMessage:
        """Add a message to a chat.

        Args:
            chat_id: Chat identifier
            role: Message role ('user' or 'assistant')
            content: Message content

        Returns:
            ChatMessage object representing the created message
        """
        self._ensure_workspace()

        msg_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        self._conn.execute(
            """
            INSERT INTO messages (id, chat_id, workspace_id, role, content, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (msg_id, chat_id, self._workspace_id, role, content, now),
        )
        self._conn.commit()

        return ChatMessage(
            id=msg_id,
            chat_id=chat_id,
            role=role,  # type: ignore
            content=content,
            timestamp=now,
            workspace_id=self._workspace_id,
        )

    def get_messages(self, chat_id: str) -> list[ChatMessage]:
        """Retrieve all messages for a chat, ordered by timestamp ASC.

        Args:
            chat_id: Chat identifier

        Returns:
            List of ChatMessage objects in chronological order
        """
        rows = self._conn.execute(
            """
            SELECT id, role, content, timestamp
            FROM messages
            WHERE chat_id = ? AND workspace_id = ?
            ORDER BY timestamp ASC
            """,
            (chat_id, self._workspace_id),
        ).fetchall()

        return [
            ChatMessage(
                id=row["id"],
                chat_id=chat_id,
                role=row["role"],  # type: ignore
                content=row["content"],
                timestamp=row["timestamp"],
                workspace_id=self._workspace_id,
            )
            for row in rows
        ]
