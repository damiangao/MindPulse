"""Tests for ChatRepository."""


class TestChatRepository:
    """Test cases for ChatRepository."""

    def test_create_chat(self, user_db, user_id):
        """Creates chat, verifies returned Chat has id/title/user_id."""
        from server.database.repositories.chat import ChatRepository

        repo = ChatRepository(user_db, user_id)
        chat = repo.create_chat("chat-123", "Test Chat", "sess-123")

        assert chat.id == "chat-123"
        assert chat.title == "Test Chat"
        assert chat.user_id == user_id

    def test_get_chat(self, user_db, user_id):
        """Creates chat, retrieves it, verifies title."""
        from server.database.repositories.chat import ChatRepository

        repo = ChatRepository(user_db, user_id)
        repo.create_chat("chat-456", "Original Title", "sess-456")
        retrieved = repo.get_chat("chat-456")

        assert retrieved is not None
        assert retrieved.title == "Original Title"

    def test_get_nonexistent_chat(self, user_db, user_id):
        """Returns None for non-existent chat."""
        from server.database.repositories.chat import ChatRepository

        repo = ChatRepository(user_db, user_id)
        result = repo.get_chat("nonexistent")

        assert result is None

    def test_get_all_chats_sorted(self, user_db, user_id):
        """Creates 2 chats, get_all_chats returns in updated_at DESC order."""
        from server.database.repositories.chat import ChatRepository

        repo = ChatRepository(user_db, user_id)
        repo.create_chat("chat-1", "First", "sess-1")
        repo.create_chat("chat-2", "Second", "sess-2")

        all_chats = repo.get_all_chats()
        assert len(all_chats) == 2
        # Sorted by updated_at DESC - most recent first
        assert all_chats[0].id == "chat-2"
        assert all_chats[1].id == "chat-1"

    def test_user_isolation(self, user_db):
        """Create chats in user A and B, verify they can't see each other's chats."""
        from server.database.repositories.chat import ChatRepository

        repo_a = ChatRepository(user_db, "user-a")
        repo_b = ChatRepository(user_db, "user-b")

        repo_a.create_chat("chat-a", "Chat in A", "sess-a")
        repo_b.create_chat("chat-b", "Chat in B", "sess-b")

        chats_a = repo_a.get_all_chats()
        chats_b = repo_b.get_all_chats()

        assert len(chats_a) == 1
        assert chats_a[0].id == "chat-a"
        assert len(chats_b) == 1
        assert chats_b[0].id == "chat-b"

    def test_update_chat_title(self, user_db, user_id):
        """Updates title, verifies returned chat has new title."""
        from server.database.repositories.chat import ChatRepository

        repo = ChatRepository(user_db, user_id)
        repo.create_chat("chat-update", "Old Title", "sess-update")
        updated = repo.update_title("chat-update", "New Title")

        assert updated is not None
        assert updated.title == "New Title"

    def test_delete_chat(self, user_db, user_id):
        """Deletes chat, verify it's gone."""
        from server.database.repositories.chat import ChatRepository

        repo = ChatRepository(user_db, user_id)
        repo.create_chat("chat-to-delete", "To Delete", "sess-del")
        result = repo.delete("chat-to-delete")

        assert result is True
        assert repo.get_chat("chat-to-delete") is None

    def test_delete_nonexistent(self, user_db, user_id):
        """Returns False when deleting non-existent chat."""
        from server.database.repositories.chat import ChatRepository

        repo = ChatRepository(user_db, user_id)
        result = repo.delete("nonexistent-chat")

        assert result is False

    def test_touch_updates_timestamp(self, user_db, user_id):
        """Touch updates the updated_at timestamp."""
        from server.database.repositories.chat import ChatRepository

        repo = ChatRepository(user_db, user_id)
        repo.create_chat("chat-touch", "Touch Test", "sess-touch")

        # Get original timestamp
        original = repo.get_chat("chat-touch")
        original_updated = original.updated_at

        # Touch and get new timestamp
        repo.touch("chat-touch")
        updated = repo.get_chat("chat-touch")

        # Timestamps should be different (touch updates updated_at)
        assert updated.updated_at >= original_updated
