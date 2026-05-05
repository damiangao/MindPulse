"""SQLite database connection management with user isolation."""

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from server.database.migrations import ensure_user, init_schema

# Default data directory relative to repo root
DEFAULT_DATA_DIR = Path(__file__).parent.parent.parent / "data"

# Cache of initialized connections (per user)
_connection_cache: dict[str, sqlite3.Connection] = {}


def get_data_dir() -> Path:
    """Get the data directory path, creating it if necessary."""
    data_dir = os.environ.get("DATA_DIR", str(DEFAULT_DATA_DIR))
    path = Path(data_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _get_db_path() -> Path:
    """Get the database file path."""
    return get_data_dir() / "chats.db"


def _get_connection(user_id: str) -> sqlite3.Connection:
    """Get or create a connection for the given user.

    Connections are cached to avoid reopening the same database file.
    """
    if user_id not in _connection_cache:
        db_path = _get_db_path()
        conn = sqlite3.connect(str(db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row

        # Enable WAL mode for better concurrency
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")

        # Initialize schema on first connection
        init_schema(conn)

        # Ensure user exists
        ensure_user(conn, user_id)

        conn.commit()
        _connection_cache[user_id] = conn

    return _connection_cache[user_id]


@contextmanager
def get_workspace_db(user_id: str):
    """Context manager providing a database connection for a user.

    Yields a sqlite3.Connection scoped to the user. All queries
    through this connection are automatically filtered to the user.

    Args:
        user_id: The user identifier for data isolation

    Yields:
        sqlite3.Connection configured for the user
    """
    conn = _get_connection(user_id)
    try:
        # Ensure this user exists in the database
        # This is safe to call multiple times
        ensure_user(conn, user_id)
        conn.commit()
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        # Don't close the connection - it's cached for reuse
        pass


def reset_connections() -> None:
    """Reset all cached connections. Used primarily for testing."""
    global _connection_cache
    for conn in _connection_cache.values():
        conn.close()
    _connection_cache = {}
