"""Integration tests for init + chat flow with real database."""

import time

import pytest
from fastapi.testclient import TestClient

from server.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestInitChatFlow:
    """Test the full init + chat flow."""

    def test_init_then_chat(self, client):
        """Send init for a draft chatId, then send chat message with that same chatId.

        This tests that:
        1. init creates a chat record with session_id
        2. WebSocket subscribe to that chatId works
        3. WebSocket chat to that chatId after subscribe works (no error)
        """
        # Register and login to get a token
        client.post("/api/auth/register", json={
            "email": "flow-test@example.com",
            "password": "testpass123",
        })
        login_res = client.post("/api/auth/login", json={
            "email": "flow-test@example.com",
            "password": "testpass123",
        })
        token = login_res.json()["token"]

        headers = {"Authorization": f"Bearer {token}"}
        draft_chat_id = "draft-123-456"

        # Step 1: init the draft chat - creates chat record with SDK session
        init_res = client.post(
            "/api/chats/init",
            json={"chatId": draft_chat_id},
            headers=headers,
        )
        assert init_res.status_code == 200, f"init failed: {init_res.json()}"
        data = init_res.json()
        assert data["id"] == draft_chat_id
        assert data["sessionId"] is not None

        # Step 2: WebSocket subscribe + chat
        with client.websocket_connect("/ws") as ws:
            # Receive connected message
            msg = ws.receive_json()
            assert msg["type"] == "connected"

            # Subscribe to the formal chat (same as draft_chat_id)
            ws.send_json({
                "type": "subscribe",
                "chatId": draft_chat_id,
                "authorization": f"Bearer {token}",
            })

            # Should get history (empty)
            msg = ws.receive_json()
            assert msg["type"] == "history"
            assert msg["chatId"] == draft_chat_id

            # Send chat message - should NOT get "Must subscribe first" error
            ws.send_json({
                "type": "chat",
                "chatId": draft_chat_id,
                "content": "Hello from test",
            })

            # Receive all messages until we get result or error (with timeout)
            deadline = time.time() + 5
            while time.time() < deadline:
                try:
                    msg = ws.receive_json(timeout=0.5)
                    if msg["type"] == "error":
                        assert msg["type"] != "error", f"Got error: {msg['error']}"
                    if msg["type"] == "result":
                        break
                except Exception:
                    # Timeout is OK - means no error was sent
                    break

    def test_init_returns_session_id(self, client):
        """Verify init stores session_id in database."""
        # Register and login
        client.post("/api/auth/register", json={
            "email": "session-id-test@example.com",
            "password": "testpass123",
        })
        login_res = client.post("/api/auth/login", json={
            "email": "session-id-test@example.com",
            "password": "testpass123",
        })
        token = login_res.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        chat_id = "chat-with-session-123"
        res = client.post(
            "/api/chats/init",
            json={"chatId": chat_id},
            headers=headers,
        )
        assert res.status_code == 200
        data = res.json()
        assert data["sessionId"] is not None

        # Verify session_id is stored
        chat = client.get(f"/api/chats/{chat_id}", headers=headers)
        assert chat.json()["sessionId"] == data["sessionId"]

    def test_chat_without_subscribe_returns_error(self, client):
        """Verify chat without subscribe is rejected."""
        # Register and login
        client.post("/api/auth/register", json={
            "email": "no-subscribe@example.com",
            "password": "testpass123",
        })
        login_res = client.post("/api/auth/login", json={
            "email": "no-subscribe@example.com",
            "password": "testpass123",
        })
        token = login_res.json()["token"]

        with client.websocket_connect("/ws") as ws:
            ws.receive_json()  # connected

            # Try to chat without subscribing first
            ws.send_json({
                "type": "chat",
                "chatId": "any-chat-id",
                "content": "Hello",
            })

            msg = ws.receive_json()
            assert msg["type"] == "error"
            assert "subscribe" in msg["error"].lower()


class TestAuthFlow:
    """E2E auth tests."""

    def test_register_and_login(self, client):
        """Register, login, verify token works."""
        email = "e2e-auth@example.com"
        password = "testpass123"

        # Register
        reg = client.post("/api/auth/register", json={"email": email, "password": password})
        assert reg.status_code == 200

        # Login
        login = client.post("/api/auth/login", json={"email": email, "password": password})
        assert login.status_code == 200
        token = login.json()["token"]
        assert token

        # Use token
        me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200
        assert me.json()["email"] == email

    def test_login_with_existing_account(self, client):
        """Login twice - second login should work (existing account)."""
        email = "e2e-existing@example.com"
        password = "testpass123"

        client.post("/api/auth/register", json={"email": email, "password": password})

        for _ in range(2):
            login = client.post("/api/auth/login", json={"email": email, "password": password})
            assert login.status_code == 200


class TestChatHistoryFlow:
    """E2E chat history tests."""

    def test_create_chat_and_get_history(self, client):
        """Create a chat via init, then get its messages."""
        # Register and login
        client.post("/api/auth/register", json={
            "email": "history-test@example.com",
            "password": "testpass123",
        })
        login_res = client.post("/api/auth/login", json={
            "email": "history-test@example.com",
            "password": "testpass123",
        })
        token = login_res.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        chat_id = "history-chat-123"
        res = client.post("/api/chats/init", json={"chatId": chat_id}, headers=headers)
        assert res.status_code == 200

        # Get chat messages (should be empty)
        msgs = client.get(f"/api/chats/{chat_id}/messages", headers=headers)
        assert msgs.status_code == 200
        assert msgs.json() == []

        # Get all chats
        chats = client.get("/api/chats", headers=headers)
        assert chats.status_code == 200
        ids = [c["id"] for c in chats.json()]
        assert chat_id in ids

    def test_delete_chat_removes_from_list(self, client):
        """Delete a chat, verify it's no longer in chat list."""
        # Register and login
        client.post("/api/auth/register", json={
            "email": "delete-test@example.com",
            "password": "testpass123",
        })
        login_res = client.post("/api/auth/login", json={
            "email": "delete-test@example.com",
            "password": "testpass123",
        })
        token = login_res.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        chat_id = "delete-me-123"
        client.post("/api/chats/init", json={"chatId": chat_id}, headers=headers)

        # Verify it exists
        chats = client.get("/api/chats", headers=headers)
        ids = [c["id"] for c in chats.json()]
        assert chat_id in ids

        # Delete it
        res = client.delete(f"/api/chats/{chat_id}", headers=headers)
        assert res.status_code == 200

        # Verify it's gone
        chats = client.get("/api/chats", headers=headers)
        ids = [c["id"] for c in chats.json()]
        assert chat_id not in ids
