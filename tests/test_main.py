from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from server.main import app

    return TestClient(app)


@pytest.fixture
def workspace_header():
    return {"X-Workspace-ID": "test-workspace-123"}


class TestRoot:
    def test_root(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


class TestChatsAPI:
    @patch("server.main.chat_store")
    def test_get_chats(self, mock_chat_store, client, workspace_header):
        from server.models import Chat

        mock_chat_store.get_all_chats.return_value = [
            Chat(id="chat-1", workspace_id="test-workspace-123", title="First", created_at="2024-01-01", updated_at="2024-01-02"),
            Chat(id="chat-2", workspace_id="test-workspace-123", title="Second", created_at="2024-01-03", updated_at="2024-01-04"),
        ]

        response = client.get("/api/chats", headers=workspace_header)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["id"] == "chat-1"
        assert data[0]["title"] == "First"

    @patch("server.main._create_sdk_chat")
    def test_create_chat(self, mock_create, client, workspace_header):
        mock_create.return_value = {
            "id": "chat-1",
            "workspaceId": "test-workspace-123",
            "title": "New Chat",
            "createdAt": "2024-01-01",
            "updatedAt": "2024-01-01",
        }

        response = client.post("/api/chats", json={"title": "Test"}, headers=workspace_header)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "chat-1"
        mock_create.assert_awaited_once_with("test-workspace-123", "Test")

    @patch("server.main._create_sdk_chat")
    def test_init_chat(self, mock_create, client, workspace_header):
        mock_create.return_value = {
            "id": "chat-1",
            "workspaceId": "test-workspace-123",
            "title": "New Chat",
            "createdAt": "2024-01-01",
            "updatedAt": "2024-01-01",
        }

        response = client.post("/api/chats/init", json={"tempId": "temp-123"}, headers=workspace_header)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "chat-1"
        mock_create.assert_awaited_once_with("test-workspace-123", None)

    @patch("server.main._create_sdk_chat")
    def test_init_chat_missing_temp_id(self, mock_create, client, workspace_header):
        response = client.post("/api/chats/init", json={}, headers=workspace_header)

        assert response.status_code == 400
        data = response.json()
        assert "tempId is required" in data["detail"]
        mock_create.assert_not_called()

    @patch("server.main.chat_store")
    def test_get_chat(self, mock_chat_store, client, workspace_header):
        from server.models import Chat

        mock_chat_store.get_chat.return_value = Chat(
            id="chat-1", workspace_id="test-workspace-123", title="Test", created_at="2024-01-01", updated_at="2024-01-01"
        )

        response = client.get("/api/chats/chat-1", headers=workspace_header)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "chat-1"
        assert data["title"] == "Test"

    @patch("server.main.chat_store")
    def test_get_chat_not_found(self, mock_chat_store, client, workspace_header):
        mock_chat_store.get_chat.return_value = None

        response = client.get("/api/chats/nonexistent", headers=workspace_header)

        assert response.status_code == 404
        assert "Chat not found" in response.json()["detail"]

    @patch("server.main.chat_store")
    @patch("server.main._sessions", {})
    def test_delete_chat(self, mock_chat_store, client, workspace_header):
        mock_chat_store.delete_chat.return_value = True

        response = client.delete("/api/chats/chat-1", headers=workspace_header)

        assert response.status_code == 200
        assert response.json()["success"] is True

    @patch("server.main.chat_store")
    def test_delete_chat_not_found(self, mock_chat_store, client, workspace_header):
        mock_chat_store.delete_chat.return_value = False

        response = client.delete("/api/chats/nonexistent", headers=workspace_header)

        assert response.status_code == 404
        assert "Chat not found" in response.json()["detail"]

    @patch("server.main.chat_store")
    def test_get_messages(self, mock_chat_store, client, workspace_header):
        from server.models import ChatMessage

        mock_chat_store.get_messages.return_value = [
            ChatMessage(
                id="msg-1",
                chat_id="chat-1",
                workspace_id="test-workspace-123",
                role="user",
                content="Hello",
                timestamp="2024-01-01",
            ),
            ChatMessage(
                id="msg-2",
                chat_id="chat-1",
                workspace_id="test-workspace-123",
                role="assistant",
                content="Hi there",
                timestamp="2024-01-02",
            ),
        ]

        response = client.get("/api/chats/chat-1/messages", headers=workspace_header)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["role"] == "user"
        assert data[1]["role"] == "assistant"


class TestWebSocket:
    @patch("server.main.chat_store")
    @patch("server.main.get_or_create_session")
    def test_websocket_subscribe(self, mock_get_session, mock_chat_store, client):
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        mock_chat_store.get_messages.return_value = []

        with client.websocket_connect("/ws") as ws:
            # Receive connected message
            msg = ws.receive_json()
            assert msg["type"] == "connected"

            # Subscribe to a chat with workspaceId
            ws.send_json({"type": "subscribe", "chatId": "chat-1", "workspaceId": "ws-1"})

            # Receive history
            msg = ws.receive_json()
            assert msg["type"] == "history"
            assert msg["chatId"] == "chat-1"

            mock_session.subscribe.assert_called_once()
            mock_get_session.assert_called_once_with("chat-1", "ws-1")

    @patch("server.main.get_or_create_session")
    def test_websocket_chat(self, mock_get_session, client):
        mock_session = MagicMock()
        mock_session.send_message = AsyncMock()
        mock_get_session.return_value = mock_session

        with client.websocket_connect("/ws") as ws:
            # Receive connected message
            msg = ws.receive_json()
            assert msg["type"] == "connected"

            # Subscribe first
            ws.send_json({"type": "subscribe", "chatId": "chat-1", "workspaceId": "ws-1"})
            ws.receive_json()  # history

            # Send a chat message
            ws.send_json({"type": "chat", "chatId": "chat-1", "content": "Hello"})

            # Wait a bit for async processing
            import asyncio

            asyncio.run(asyncio.sleep(0.1))

            mock_session.send_message.assert_called_once_with("Hello")

    def test_websocket_invalid_json(self, client):
        with client.websocket_connect("/ws") as ws:
            # Receive connected message
            msg = ws.receive_json()
            assert msg["type"] == "connected"

            # Send invalid JSON
            ws.send_text("not json")

            msg = ws.receive_json()
            assert msg["type"] == "error"
            assert "Invalid message format" in msg["error"]