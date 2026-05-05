from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from tests.test_auth import auth_header


@pytest.fixture
def client():
    from server.main import app

    return TestClient(app)


class TestRoot:
    def test_root(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


class TestChatsAPI:
    @patch("server.main.chat_store")
    def test_get_chats(self, mock_chat_store, client):
        from server.models import Chat

        mock_chat_store.get_all_chats.return_value = [
            Chat(
                id="chat-1",
                session_id="sess-1",
                user_id="test-user-123",
                title="First",
                created_at="2024-01-01",
                updated_at="2024-01-02",
            ),
            Chat(
                id="chat-2",
                session_id="sess-2",
                user_id="test-user-123",
                title="Second",
                created_at="2024-01-03",
                updated_at="2024-01-04",
            ),
        ]

        response = client.get("/api/chats", headers=auth_header())

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["id"] == "chat-1"
        assert data[0]["title"] == "First"

    @patch("server.main._create_sdk_chat")
    def test_create_chat(self, mock_create, client):
        mock_create.return_value = {
            "id": "chat-1",
            "title": "New Chat",
            "createdAt": "2024-01-01",
            "updatedAt": "2024-01-01",
        }

        response = client.post("/api/chats", json={"title": "Test"}, headers=auth_header())

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "chat-1"
        mock_create.assert_awaited_once()

    @patch("server.main._create_sdk_chat")
    def test_init_chat(self, mock_create, client):
        mock_create.return_value = {
            "id": "chat-1",
            "title": "New Chat",
            "createdAt": "2024-01-01",
            "updatedAt": "2024-01-01",
        }

        response = client.post(
            "/api/chats/init", json={"chatId": "temp-123"}, headers=auth_header()
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "chat-1"
        mock_create.assert_awaited_once()

    @patch("server.main._create_sdk_chat")
    def test_init_chat_missing_temp_id(self, mock_create, client):
        response = client.post("/api/chats/init", json={}, headers=auth_header())

        assert response.status_code == 400
        data = response.json()
        assert "chatId is required" in data["detail"]
        mock_create.assert_not_called()

    @patch("server.main.chat_store")
    def test_get_chat(self, mock_chat_store, client):
        from server.models import Chat

        mock_chat_store.get_chat.return_value = Chat(
            id="chat-1",
            session_id="sess-1",
            user_id="test-user-123",
            title="Test",
            created_at="2024-01-01",
            updated_at="2024-01-01",
        )

        response = client.get("/api/chats/chat-1", headers=auth_header())

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "chat-1"
        assert data["title"] == "Test"

    @patch("server.main.chat_store")
    def test_get_chat_not_found(self, mock_chat_store, client):
        mock_chat_store.get_chat.return_value = None

        response = client.get("/api/chats/nonexistent", headers=auth_header())

        assert response.status_code == 404
        assert "Chat not found" in response.json()["detail"]

    @patch("server.main.chat_store")
    @patch("server.main._sessions", {})
    def test_delete_chat(self, mock_chat_store, client):
        mock_chat_store.delete_chat.return_value = True

        response = client.delete("/api/chats/chat-1", headers=auth_header())

        assert response.status_code == 200
        assert response.json()["success"] is True

    @patch("server.main.chat_store")
    def test_delete_chat_not_found(self, mock_chat_store, client):
        mock_chat_store.delete_chat.return_value = False

        response = client.delete("/api/chats/nonexistent", headers=auth_header())

        assert response.status_code == 404
        assert "Chat not found" in response.json()["detail"]

    @patch("server.main.chat_store")
    def test_get_messages(self, mock_chat_store, client):
        from server.models import ChatMessage

        mock_chat_store.get_messages.return_value = [
            ChatMessage(
                id="msg-1",
                chat_id="chat-1",
                user_id="test-user-123",
                role="user",
                content="Hello",
                timestamp="2024-01-01",
            ),
            ChatMessage(
                id="msg-2",
                chat_id="chat-1",
                user_id="test-user-123",
                role="assistant",
                content="Hi there",
                timestamp="2024-01-02",
            ),
        ]

        response = client.get("/api/chats/chat-1/messages", headers=auth_header())

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["role"] == "user"
        assert data[1]["role"] == "assistant"

    def test_get_chats_unauthorized(self, client):
        response = client.get("/api/chats")
        assert response.status_code in (401, 422)


class TestWebSocket:
    @patch("server.main.chat_store")
    @patch("server.main.get_or_create_session")
    def test_websocket_subscribe(self, mock_get_session, mock_chat_store, client):
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        mock_chat_store.get_messages.return_value = []

        with client.websocket_connect("/ws") as ws:
            msg = ws.receive_json()
            assert msg["type"] == "connected"

            from tests.test_auth import make_test_token

            token = make_test_token()
            ws.send_json(
                {
                    "type": "subscribe",
                    "chatId": "chat-1",
                    "authorization": f"Bearer {token}",
                }
            )

            msg = ws.receive_json()
            assert msg["type"] == "history"
            assert msg["chatId"] == "chat-1"

            mock_session.subscribe.assert_called_once()
            mock_get_session.assert_called_once_with("chat-1", "test-user-123")

    @patch("server.main.chat_store")
    @patch("server.main.get_or_create_session")
    def test_websocket_chat(self, mock_get_session, mock_chat_store, client):
        mock_session = MagicMock()
        mock_session.send_message = AsyncMock()
        mock_get_session.return_value = mock_session
        mock_chat_store.get_chat.return_value = MagicMock(session_id="existing-session")

        with client.websocket_connect("/ws") as ws:
            msg = ws.receive_json()
            assert msg["type"] == "connected"

            from tests.test_auth import make_test_token

            token = make_test_token()
            ws.send_json(
                {
                    "type": "subscribe",
                    "chatId": "chat-1",
                    "authorization": f"Bearer {token}",
                }
            )
            ws.receive_json()  # history

            ws.send_json({"type": "chat", "chatId": "chat-1", "content": "Hello"})

            import asyncio

            asyncio.run(asyncio.sleep(0.1))

            mock_session.send_message.assert_called_once_with("Hello")

    @patch("server.main.chat_store")
    @patch("server.main.AgentSession")
    @patch("server.main.get_or_create_session")
    def test_chat_auto_creates_chat_and_session(
        self, mock_get_session, mock_agent_session_cls, mock_chat_store, client
    ):
        """When chat message received for non-existent chat, chat and session are auto-created."""
        temp_chat_id = str(uuid4())
        user_id = "testuser"

        # Simulate chat not existing
        mock_chat_store.get_chat.return_value = None

        # Mock AgentSession instance and init
        mock_agent_session = MagicMock()
        mock_agent_session.init = AsyncMock(return_value="new-session-id")
        mock_agent_session_cls.return_value = mock_agent_session

        # Mock get_or_create_session to return a mock session
        mock_session = MagicMock()
        mock_session.send_message = AsyncMock()
        mock_get_session.return_value = mock_session

        with client.websocket_connect("/ws") as ws:
            msg = ws.receive_json()
            assert msg["type"] == "connected"

            from tests.test_auth import make_test_token

            token = make_test_token(user_id=user_id)
            ws.send_json(
                {
                    "type": "subscribe",
                    "chatId": temp_chat_id,
                    "authorization": f"Bearer {token}",
                }
            )
            ws.receive_json()  # history

            ws.send_json({"type": "chat", "chatId": temp_chat_id, "content": "Hello"})

            import asyncio

            asyncio.run(asyncio.sleep(0.1))

            # Verify AgentSession was created and initialized
            mock_agent_session_cls.assert_called_once_with(user_id=user_id)
            mock_agent_session.init.assert_awaited_once()

            # Verify chat was created in store
            mock_chat_store.create_chat.assert_called_once_with(
                temp_chat_id, user_id, None, "new-session-id"
            )

            # Verify session was used to send message
            mock_session.send_message.assert_called_once_with("Hello")

    def test_websocket_invalid_json(self, client):
        with client.websocket_connect("/ws") as ws:
            msg = ws.receive_json()
            assert msg["type"] == "connected"

            ws.send_text("not json")

            msg = ws.receive_json()
            assert msg["type"] == "error"
            assert "Invalid message format" in msg["error"]

    def test_websocket_subscribe_without_auth(self, client):
        with client.websocket_connect("/ws") as ws:
            msg = ws.receive_json()
            assert msg["type"] == "connected"

            ws.send_json({"type": "subscribe", "chatId": "chat-1"})

            msg = ws.receive_json()
            assert msg["type"] == "error"
            assert "Authorization" in msg["error"]


class TestAuth:
    def test_register_success(self, client):
        response = client.post(
            "/api/auth/register",
            json={
                "email": "new@example.com",
                "password": "password123",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == "new@example.com"

    def test_register_duplicate_email(self, client):
        # First register
        client.post(
            "/api/auth/register",
            json={
                "email": "dup@example.com",
                "password": "password123",
            },
        )

        # Try again with same email
        response = client.post(
            "/api/auth/register",
            json={
                "email": "dup@example.com",
                "password": "password456",
            },
        )

        assert response.status_code == 409
        assert "already registered" in response.json()["detail"]

    def test_register_invalid_email(self, client):
        response = client.post(
            "/api/auth/register",
            json={
                "email": "not-an-email",
                "password": "password123",
            },
        )

        assert response.status_code == 400
        assert "email" in response.json()["detail"]

    def test_register_short_password(self, client):
        response = client.post(
            "/api/auth/register",
            json={
                "email": "test@example.com",
                "password": "12345",
            },
        )

        assert response.status_code == 400
        assert "Password" in response.json()["detail"]

    def test_login_success(self, client):
        # Register first
        client.post(
            "/api/auth/register",
            json={
                "email": "login@example.com",
                "password": "password123",
            },
        )

        # Login
        response = client.post(
            "/api/auth/login",
            json={
                "email": "login@example.com",
                "password": "password123",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["email"] == "login@example.com"

    def test_login_wrong_password(self, client):
        # Register first
        client.post(
            "/api/auth/register",
            json={
                "email": "wrong@example.com",
                "password": "password123",
            },
        )

        # Login with wrong password
        response = client.post(
            "/api/auth/login",
            json={
                "email": "wrong@example.com",
                "password": "wrongpassword",
            },
        )

        assert response.status_code == 401
        assert "Invalid email or password" in response.json()["detail"]

    def test_login_nonexistent_user(self, client):
        response = client.post(
            "/api/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "password123",
            },
        )

        assert response.status_code == 401
        assert "Invalid email or password" in response.json()["detail"]

    def test_me_success(self, client):
        # Register and get token
        reg_response = client.post(
            "/api/auth/register",
            json={
                "email": "me@example.com",
                "password": "password123",
            },
        )
        token = reg_response.json()["token"]

        # Get current user
        response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 200
        assert response.json()["email"] == "me@example.com"

    def test_me_invalid_token(self, client):
        response = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid-token"})

        assert response.status_code == 401


class TestFileUploadAPI:
    @patch("server.main.get_project_root")
    def test_upload_file(self, mock_root, client, tmp_path):
        mock_root.return_value = str(tmp_path)
        from io import BytesIO

        from tests.test_auth import auth_header

        file_content = b"test file content"
        file = ("test.txt", BytesIO(file_content), "text/plain")
        response = client.post(
            "/api/files/upload",
            files={"file": file},
            data={"chatId": "chat-123"},
            headers=auth_header(),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["path"] == "test-user-123/chat-123/test.txt"
        assert (tmp_path / "test-user-123" / "chat-123" / "test.txt").read_bytes() == file_content

    def test_upload_file_missing_chat_id(self, client):
        from io import BytesIO

        from tests.test_auth import auth_header

        file = ("test.txt", BytesIO(b"content"), "text/plain")
        response = client.post("/api/files/upload", files={"file": file}, headers=auth_header())
        assert response.status_code == 422  # FastAPI validation error

    @patch("server.main.get_project_root")
    def test_download_file(self, mock_root, client, tmp_path):
        mock_root.return_value = str(tmp_path)
        file_path = tmp_path / "test-user-123" / "chat-123" / "test.txt"
        file_path.parent.mkdir(parents=True)
        file_path.write_bytes(b"file content")
        from tests.test_auth import auth_header

        response = client.get(
            "/api/files/download?path=test-user-123%2Fchat-123%2Ftest.txt", headers=auth_header()
        )
        assert response.status_code == 200
        assert response.content == b"file content"

    @patch("server.main.get_project_root")
    def test_download_file_not_found(self, mock_root, client, tmp_path):
        mock_root.return_value = str(tmp_path)
        from tests.test_auth import auth_header

        response = client.get(
            "/api/files/download?path=test-user-123%2Fnonexistent%2Ffile.txt", headers=auth_header()
        )
        assert response.status_code == 404
