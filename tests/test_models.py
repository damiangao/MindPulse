from server.models import Chat, ChatMessage, WSChatMessage, WSSubscribeMessage


class TestChat:
    def test_chat_creation(self):
        chat = Chat(
            id="chat-1",
            title="Test",
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
        )
        assert chat.id == "chat-1"
        assert chat.title == "Test"


class TestChatMessage:
    def test_message_creation(self):
        msg = ChatMessage(
            id="msg-1",
            chat_id="chat-1",
            role="user",
            content="Hello",
            timestamp="2024-01-01T00:00:00Z",
        )
        assert msg.role == "user"
        assert msg.content == "Hello"


class TestWSMessages:
    def test_chat_message(self):
        msg = WSChatMessage(type="chat", content="Hello", chat_id="chat-1")
        assert msg.type == "chat"

    def test_subscribe_message(self):
        msg = WSSubscribeMessage(type="subscribe", chat_id="chat-1")
        assert msg.type == "subscribe"
