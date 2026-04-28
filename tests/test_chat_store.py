import os
from unittest.mock import patch

import pytest

from server.chat_store import ChatStore


class TestChatStore:
    def test_create_chat(self):
        store = ChatStore()
        chat = store.create_chat("chat-1", "Test Chat")

        assert chat.id == "chat-1"
        assert chat.title == "Test Chat"
        assert chat.created_at is not None
        assert chat.updated_at is not None

    def test_create_chat_default_title(self):
        store = ChatStore()
        chat = store.create_chat("chat-1")

        assert chat.title == "New Chat"

    def test_get_chat(self):
        store = ChatStore()
        store.create_chat("chat-1", "Test")

        chat = store.get_chat("chat-1")
        assert chat is not None
        assert chat.title == "Test"

        missing = store.get_chat("nonexistent")
        assert missing is None

    def test_get_all_chats_sorted(self):
        store = ChatStore()
        store.create_chat("chat-1", "First")
        store.create_chat("chat-2", "Second")

        chats = store.get_all_chats()
        assert len(chats) == 2
        # Most recently created first
        assert chats[0].id == "chat-2"
        assert chats[1].id == "chat-1"

    def test_delete_chat(self):
        store = ChatStore()
        store.create_chat("chat-1")

        assert store.delete_chat("chat-1") is True
        assert store.get_chat("chat-1") is None
        assert store.delete_chat("chat-1") is False

    def test_add_message(self):
        store = ChatStore()
        store.create_chat("chat-1")

        msg = store.add_message("chat-1", "user", "Hello")

        assert msg.chat_id == "chat-1"
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.timestamp is not None

        messages = store.get_messages("chat-1")
        assert len(messages) == 1
        assert messages[0].content == "Hello"

    def test_add_message_chat_not_found(self):
        store = ChatStore()

        with pytest.raises(ValueError, match="Chat nonexistent not found"):
            store.add_message("nonexistent", "user", "Hello")

    def test_add_message_updates_chat_timestamp(self):
        store = ChatStore()
        chat = store.create_chat("chat-1")
        old_updated = chat.updated_at

        store.add_message("chat-1", "user", "Hello")

        assert chat.updated_at > old_updated

    def test_add_message_auto_title(self):
        store = ChatStore()
        chat = store.create_chat("chat-1")
        assert chat.title == "New Chat"

        store.add_message("chat-1", "user", "My first message")

        assert chat.title == "My first message"

    def test_add_message_auto_title_truncation(self):
        store = ChatStore()
        chat = store.create_chat("chat-1")

        long_content = "a" * 100
        store.add_message("chat-1", "user", long_content)

        assert chat.title == "a" * 50 + "..."
        assert len(chat.title) == 53

    def test_add_message_does_not_change_existing_title(self):
        store = ChatStore()
        store.create_chat("chat-1", "Custom Title")

        store.add_message("chat-1", "user", "Hello")

        chat = store.get_chat("chat-1")
        assert chat.title == "Custom Title"

    def test_add_message_assistant_does_not_change_title(self):
        store = ChatStore()
        store.create_chat("chat-1")

        store.add_message("chat-1", "assistant", "Hello")

        chat = store.get_chat("chat-1")
        assert chat.title == "New Chat"

    def test_message_limit(self):
        store = ChatStore()
        store.create_chat("chat-1")

        for i in range(1005):
            store.add_message("chat-1", "user", f"msg-{i}")

        messages = store.get_messages("chat-1")
        assert len(messages) == 1000
        # Oldest messages should be dropped
        assert messages[0].content == "msg-5"
        assert messages[-1].content == "msg-1004"

    @patch.dict(os.environ, {"MAX_MESSAGES_PER_CHAT": "5"})
    def test_message_limit_from_env(self):
        # Need to reimport to pick up the env var
        import importlib
        from server import chat_store as cs

        importlib.reload(cs)
        store = cs.ChatStore()
        store.create_chat("chat-1")

        for i in range(10):
            store.add_message("chat-1", "user", f"msg-{i}")

        messages = store.get_messages("chat-1")
        assert len(messages) == 5
        assert messages[0].content == "msg-5"
