"""Pytest fixtures for database tests."""

import os
import shutil
import tempfile

import pytest

# Set up test data directory before importing database modules
TEST_DATA_DIR = tempfile.mkdtemp()


@pytest.fixture
def workspace_id():
    """Generate a unique workspace ID for each test."""
    return f"test-workspace-{os.urandom(8).hex()}"


@pytest.fixture
def workspace_db(workspace_id):
    """Provide a database connection scoped to a test workspace."""
    from server.database.connection import get_workspace_db, reset_connections

    # Override the data directory for testing
    os.environ["DATA_DIR"] = TEST_DATA_DIR

    # Reset connections to ensure fresh state for this workspace
    reset_connections()

    with get_workspace_db(workspace_id) as conn:
        yield conn

    # Reset connections after test to clean up
    reset_connections()


@pytest.fixture(autouse=True)
def cleanup_test_data():
    """Clean up test data directory after each test."""
    yield
    if os.path.exists(TEST_DATA_DIR):
        shutil.rmtree(TEST_DATA_DIR, ignore_errors=True)
