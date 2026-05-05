import os
import shutil
import tempfile
from unittest.mock import patch

import pytest

from server.chat_store import ChatStore


@pytest.fixture(autouse=True)
def fresh_store():
    """Reset database connections between tests to avoid ID collisions."""
    from server.database.connection import reset_connections

    # Use a temp directory for each test to avoid collision
    test_dir = tempfile.mkdtemp()
    with patch.dict(os.environ, {"DATA_DIR": test_dir}):
        reset_connections()
        yield
        reset_connections()
        shutil.rmtree(test_dir, ignore_errors=True)


class TestChatStore:
    def test_create_chat(self):
        store = ChatStore()
        chat = store.create_chat("chat-1", "user-1", session_id="sess-1")

        assert chat.id == "chat-1"
        assert chat.user_id == "user-1"
        assert chat.title == "New Chat"
        assert chat.created_at is not None
        assert chat.updated_at is not None

    def test_create_chat_default_title(self):
        store = ChatStore()
        chat = store.create_chat("chat-1", "user-1", session_id="sess-1")

        assert chat.title == "New Chat"
        assert chat.user_id == "user-1"

    def test_get_chat(self):
        store = ChatStore()
        store.create_chat("chat-1", "user-1", "Test", "sess-1")

        chat = store.get_chat("chat-1", "user-1")
        assert chat is not None
        assert chat.title == "Test"

        missing = store.get_chat("nonexistent", "user-1")
        assert missing is None

    def test_get_all_chats_sorted(self):
        store = ChatStore()
        store.create_chat("chat-1", "user-1", "First", "sess-1")
        store.create_chat("chat-2", "user-1", "Second", "sess-2")

        chats = store.get_all_chats("user-1")
        assert len(chats) == 2
        # Most recently created first
        assert chats[0].id == "chat-2"
        assert chats[1].id == "chat-1"

    def test_delete_chat(self):
        store = ChatStore()
        store.create_chat("chat-1", "user-1", session_id="sess-1")

        assert store.delete_chat("chat-1", "user-1") is True
        assert store.get_chat("chat-1", "user-1") is None
        assert store.delete_chat("chat-1", "user-1") is False

    def test_add_message(self):
        store = ChatStore()
        store.create_chat("chat-1", "user-1", session_id="sess-1")

        msg = store.add_message("chat-1", "user-1", "user", "Hello")

        assert msg.chat_id == "chat-1"
        assert msg.user_id == "user-1"
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.timestamp is not None

        messages = store.get_messages("chat-1", "user-1")
        assert len(messages) == 1
        assert messages[0].content == "Hello"

    def test_add_message_chat_not_found(self):
        store = ChatStore()

        with pytest.raises(ValueError, match="not found"):
            store.add_message("nonexistent", "user-1", "user", "Hello")

    def test_add_message_updates_chat_timestamp(self):
        store = ChatStore()
        chat = store.create_chat("chat-1", "user-1", session_id="sess-1")
        old_updated = chat.updated_at

        store.add_message("chat-1", "user-1", "user", "Hello")

        updated = store.get_chat("chat-1", "user-1")
        assert updated.updated_at > old_updated

    def test_add_message_auto_title(self):
        store = ChatStore()
        chat = store.create_chat("chat-1", "user-1", session_id="sess-1")
        assert chat.title == "New Chat"

        store.add_message("chat-1", "user-1", "user", "My first message")

        updated = store.get_chat("chat-1", "user-1")
        assert updated.title == "My first message"

    def test_add_message_auto_title_truncation(self):
        store = ChatStore()
        store.create_chat("chat-1", "user-1", session_id="sess-1")

        long_content = "a" * 100
        store.add_message("chat-1", "user-1", "user", long_content)

        updated = store.get_chat("chat-1", "user-1")
        assert updated.title == "a" * 50 + "..."
        assert len(updated.title) == 53

    def test_add_message_does_not_change_existing_title(self):
        store = ChatStore()
        store.create_chat("chat-1", "user-1", "Custom Title", "sess-1")

        store.add_message("chat-1", "user-1", "user", "Hello")

        chat = store.get_chat("chat-1", "user-1")
        assert chat.title == "Custom Title"

    def test_add_message_assistant_does_not_change_title(self):
        store = ChatStore()
        store.create_chat("chat-1", "user-1", session_id="sess-1")

        store.add_message("chat-1", "user-1", "assistant", "Hello")

        chat = store.get_chat("chat-1", "user-1")
        assert chat.title == "New Chat"

    def test_user_isolation(self):
        """Chats from one user are not visible in another."""
        store = ChatStore()

        store.create_chat("chat-A", "user-A", "Chat in A", "sess-A")
        store.create_chat("chat-B", "user-B", "Chat in B", "sess-B")

        assert store.get_chat("chat-A", "user-A") is not None
        assert store.get_chat("chat-A", "user-B") is None
        assert store.get_chat("chat-B", "user-B") is not None
        assert store.get_chat("chat-B", "user-A") is None

        chats_A = store.get_all_chats("user-A")
        assert len(chats_A) == 1
        assert chats_A[0].title == "Chat in A"

        chats_B = store.get_all_chats("user-B")
        assert len(chats_B) == 1
        assert chats_B[0].title == "Chat in B"
