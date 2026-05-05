"""Chat repository for database operations with user isolation."""

import sqlite3
from datetime import datetime, timezone

from server.database.migrations import ensure_user
from server.models import Chat


class ChatRepository:
    """Repository for chat operations, scoped to a user."""

    def __init__(self, conn: sqlite3.Connection, user_id: str) -> None:
        """Initialize repository with connection and user ID.

        Args:
            conn: SQLite database connection
            user_id: User identifier for data isolation
        """
        self._conn = conn
        self._user_id = user_id

    def _ensure_user(self) -> None:
        """Ensure the user exists before database operations.

        This is called before insert/update operations to guarantee
        the user record exists (since we share connections).
        """
        ensure_user(self._conn, self._user_id)
        self._conn.commit()

    def create_chat(self, chat_id: str, title: str | None = None, session_id: str | None = None) -> Chat:
        """Create a new chat for the user.

        Args:
            chat_id: Unique chat identifier
            title: Optional chat title (defaults to 'New Chat')
            session_id: Optional SDK session ID (set after SDK init)

        Returns:
            Chat object representing the created chat
        """
        if title is None:
            title = "New Chat"

        self._ensure_user()

        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            """
            INSERT INTO chats (id, session_id, user_id, title, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (chat_id, session_id, self._user_id, title, now, now),
        )
        self._conn.commit()

        return Chat(
            id=chat_id,
            session_id=session_id,
            user_id=self._user_id,
            title=title,
            created_at=now,
            updated_at=now,
        )

    def get_chat(self, chat_id: str) -> Chat | None:
        """Retrieve a chat by ID within the user's data.

        Args:
            chat_id: Chat identifier

        Returns:
            Chat object if found, None otherwise
        """
        row = self._conn.execute(
            """
            SELECT id, session_id, title, created_at, updated_at
            FROM chats
            WHERE id = ? AND user_id = ?
            """,
            (chat_id, self._user_id),
        ).fetchone()

        if row is None:
            return None

        return Chat(
            id=row["id"],
            session_id=row["session_id"],
            user_id=self._user_id,
            title=row["title"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def get_all_chats(self) -> list[Chat]:
        """Retrieve all chats for the user, ordered by updated_at DESC.

        Returns:
            List of Chat objects sorted by most recently updated
        """
        rows = self._conn.execute(
            """
            SELECT id, session_id, title, created_at, updated_at
            FROM chats
            WHERE user_id = ?
            ORDER BY updated_at DESC
            """,
            (self._user_id,),
        ).fetchall()

        return [
            Chat(
                id=row["id"],
                session_id=row["session_id"],
                user_id=self._user_id,
                title=row["title"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]

    def set_session_id(self, chat_id: str, session_id: str) -> None:
        """Set the SDK session_id for a chat."""
        self._conn.execute(
            "UPDATE chats SET session_id = ? WHERE id = ? AND user_id = ?",
            (session_id, chat_id, self._user_id),
        )
        self._conn.commit()

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
            WHERE id = ? AND user_id = ?
            """,
            (title, now, chat_id, self._user_id),
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
            WHERE id = ? AND user_id = ?
            """,
            (now, chat_id, self._user_id),
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
            WHERE id = ? AND user_id = ?
            """,
            (chat_id, self._user_id),
        )
        self._conn.commit()
        return cursor.rowcount > 0
