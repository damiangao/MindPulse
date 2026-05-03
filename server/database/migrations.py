"""Database schema initialization and migrations."""

import sqlite3


def init_schema(conn: sqlite3.Connection) -> None:
    """Initialize database schema - creates tables and indexes.

    Creates: workspaces, chats, messages tables with appropriate indexes.
    """
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS workspaces (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            owner_id TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (owner_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS chats (
            id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            title TEXT NOT NULL DEFAULT 'New Chat',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (workspace_id) REFERENCES workspaces(id)
        );

        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            chat_id TEXT NOT NULL,
            workspace_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        CREATE INDEX IF NOT EXISTS idx_chats_workspace ON chats(workspace_id);
        CREATE INDEX IF NOT EXISTS idx_messages_chat ON messages(chat_id);
        CREATE INDEX IF NOT EXISTS idx_messages_workspace ON messages(workspace_id);
    """)


def ensure_workspace(
    conn: sqlite3.Connection, workspace_id: str, owner_id: str | None = None
) -> None:
    """Ensure a workspace record exists, creating if necessary.

    Args:
        conn: Database connection
        workspace_id: Unique workspace identifier
        owner_id: Optional owner user ID (for user-owned workspaces)
    """
    conn.execute(
        "INSERT OR IGNORE INTO workspaces (id, name, owner_id) VALUES (?, ?, ?)",
        (workspace_id, f"Workspace {workspace_id}", owner_id),
    )
