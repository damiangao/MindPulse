from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=True)


def reset_db():
    """Reset the database state for testing."""
    from server.database.connection import _connection_cache, _get_db_path

    # Close all cached connections
    for conn in _connection_cache.values():
        conn.close()
    _connection_cache.clear()

    # Delete the database file and WAL files
    db_path = _get_db_path()
    for path in [db_path, Path(str(db_path) + "-wal"), Path(str(db_path) + "-shm")]:
        if path.exists():
            path.unlink()


# Reset DB once at session start
reset_db()
