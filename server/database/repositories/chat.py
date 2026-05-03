"""Chat repository for database operations with workspace isolation."""

import sqlite3
from datetime import datetime, timezone

from server.database.migrations import ensure_workspace
from server.models import Chat


class ChatRepository:
    """Repository for chat operations, scoped to a workspace."""

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

        This is called before insert/update operations to guarantee
        the workspace record exists (since we share connections).
        """
        ensure_workspace(self._conn, self._workspace_id)
        self._conn.commit()

    def create_chat(self, chat_id: str, title: str | None = None) -> Chat:
        """Create a new chat in the workspace.

        Args:
            chat_id: Unique chat identifier
            title: Optional chat title (defaults to 'New Chat')

        Returns:
            Chat object representing the created chat
        """
        if title is None:
            title = "New Chat"

        self._ensure_workspace()

        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            """
            INSERT INTO chats (id, workspace_id, title, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (chat_id, self._workspace_id, title, now, now),
        )
        self._conn.commit()

        return Chat(
            id=chat_id,
            title=title,
            created_at=now,
            updated_at=now,
            workspace_id=self._workspace_id,
        )

    def get_chat(self, chat_id: str) -> Chat | None:
        """Retrieve a chat by ID within the workspace.

        Args:
            chat_id: Chat identifier

        Returns:
            Chat object if found, None otherwise
        """
        row = self._conn.execute(
            """
            SELECT id, title, created_at, updated_at
            FROM chats
            WHERE id = ? AND workspace_id = ?
            """,
            (chat_id, self._workspace_id),
        ).fetchone()

        if row is None:
            return None

        return Chat(
            id=row["id"],
            title=row["title"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            workspace_id=self._workspace_id,
        )

    def get_all_chats(self) -> list[Chat]:
        """Retrieve all chats in the workspace, ordered by updated_at DESC.

        Returns:
            List of Chat objects sorted by most recently updated
        """
        rows = self._conn.execute(
            """
            SELECT id, title, created_at, updated_at
            FROM chats
            WHERE workspace_id = ?
            ORDER BY updated_at DESC
            """,
            (self._workspace_id,),
        ).fetchall()

        return [
            Chat(
                id=row["id"],
                title=row["title"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                workspace_id=self._workspace_id,
            )
            for row in rows
        ]

    def update_title(self, chat_id: str, title: str) -> Chat | None:
        """Update a chat's title.

        Args:
            chat_id: Chat identifier
            title: New title

        Returns:
            Updated Chat object if found, None otherwise
        """
        now = datetime.now(timezone.utc).isoformat()
        cursor = self._conn.execute(
            """
            UPDATE chats
            SET title = ?, updated_at = ?
            WHERE id = ? AND workspace_id = ?
            """,
            (title, now, chat_id, self._workspace_id),
        )
        self._conn.commit()

        if cursor.rowcount == 0:
            return None

        return self.get_chat(chat_id)

    def touch(self, chat_id: str) -> None:
        """Update the updated_at timestamp of a chat.

        Args:
            chat_id: Chat identifier
        """
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            """
            UPDATE chats
            SET updated_at = ?
            WHERE id = ? AND workspace_id = ?
            """,
            (now, chat_id, self._workspace_id),
        )
        self._conn.commit()

    def delete(self, chat_id: str) -> bool:
        """Delete a chat by ID.

        Args:
            chat_id: Chat identifier

        Returns:
            True if chat was deleted, False if not found
        """
        cursor = self._conn.execute(
            """
            DELETE FROM chats
            WHERE id = ? AND workspace_id = ?
            """,
            (chat_id, self._workspace_id),
        )
        self._conn.commit()
        return cursor.rowcount > 0
