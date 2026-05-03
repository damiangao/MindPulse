"""Tests for MessageRepository."""


class TestMessageRepository:
    """Test cases for MessageRepository."""

    def test_add_message(self, workspace_db, workspace_id):
        """Adds message, verifies returned ChatMessage has correct fields."""
        from server.database.repositories.message import MessageRepository

        repo = MessageRepository(workspace_db, workspace_id)
        msg = repo.add_message("chat-msg-1", "user", "Hello, world!")

        assert msg.chat_id == "chat-msg-1"
        assert msg.role == "user"
        assert msg.content == "Hello, world!"
        assert msg.workspace_id == workspace_id
        assert msg.id is not None

    def test_get_messages(self, workspace_db, workspace_id):
        """Adds multiple messages, verifies they're returned in timestamp ASC order."""
        from server.database.repositories.message import MessageRepository

        repo = MessageRepository(workspace_db, workspace_id)
        repo.add_message("chat-msgs", "user", "First")
        repo.add_message("chat-msgs", "assistant", "Second")
        repo.add_message("chat-msgs", "user", "Third")

        messages = repo.get_messages("chat-msgs")

        assert len(messages) == 3
        assert messages[0].content == "First"
        assert messages[1].content == "Second"
        assert messages[2].content == "Third"

    def test_workspace_isolation(self, workspace_db):
        """Messages in workspace A not visible in workspace B."""
        from server.database.repositories.message import MessageRepository

        repo_a = MessageRepository(workspace_db, "workspace-a")
        repo_b = MessageRepository(workspace_db, "workspace-b")

        repo_a.add_message("chat-cross", "user", "Message in A")
        repo_b.add_message("chat-cross", "user", "Message in B")

        msgs_a = repo_a.get_messages("chat-cross")
        msgs_b = repo_b.get_messages("chat-cross")

        assert len(msgs_a) == 1
        assert msgs_a[0].content == "Message in A"
        assert len(msgs_b) == 1
        assert msgs_b[0].content == "Message in B"

    def test_messages_ordered_by_timestamp(self, workspace_db, workspace_id):
        """Messages are returned in chronological order."""
        from server.database.repositories.message import MessageRepository

        repo = MessageRepository(workspace_db, workspace_id)
        repo.add_message("chat-ordered", "user", "Earliest")
        repo.add_message("chat-ordered", "assistant", "Middle")
        repo.add_message("chat-ordered", "user", "Latest")

        messages = repo.get_messages("chat-ordered")

        assert messages[0].content == "Earliest"
        assert messages[1].content == "Middle"
        assert messages[2].content == "Latest"
