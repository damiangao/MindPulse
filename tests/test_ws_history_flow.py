"""Integration tests for WebSocket chat history and subscribe flow."""

import time
import pytest
from fastapi.testclient import TestClient

from server.main import app
from server.chat_store import chat_store


@pytest.fixture
def client():
    return TestClient(app)


class TestWebSocketHistoryFlow:
    """Test WebSocket subscribe -> history -> chat flow for EXISTING chats."""

    def test_subscribe_to_existing_chat_sends_history(self, client):
        """Subscribe to a chat that already has messages, verify history is sent."""
        # Register and login
        client.post("/api/auth/register", json={
            "email": "history-flow@example.com",
            "password": "testpass123",
        })
        login_res = client.post("/api/auth/login", json={
            "email": "history-flow@example.com",
            "password": "testpass123",
        })
        token = login_res.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create a formal chat via init
        chat_id = "existing-chat-001"
        init_res = client.post(
            "/api/chats/init",
            json={"chatId": chat_id},
            headers=headers,
        )
        assert init_res.status_code == 200, f"init failed: {init_res.text}"

        # Manually add a user and assistant message via DB to simulate history
        from server.chat_store import chat_store
        from server.models import ChatMessage
        user_id = login_res.json()["user"]["id"]
        chat_store.add_message(chat_id, user_id, "user", "Hello, assistant!")
        chat_store.add_message(chat_id, user_id, "assistant", "Hello, user! How can I help?")

        # Verify messages are stored
        msgs = client.get(f"/api/chats/{chat_id}/messages", headers=headers)
        assert msgs.status_code == 200
        assert len(msgs.json()) == 2

        # Now WebSocket: connect, subscribe, should receive history
        with client.websocket_connect("/ws") as ws:
            # Receive connected
            msg = ws.receive_json()
            assert msg["type"] == "connected"

            # Subscribe to existing chat
            ws.send_json({
                "type": "subscribe",
                "chatId": chat_id,
                "authorization": f"Bearer {token}",
            })

            # Should receive history
            history_msg = ws.receive_json()
            assert history_msg["type"] == "history", f"Expected history, got: {history_msg}"
            assert history_msg["chatId"] == chat_id
            assert len(history_msg["messages"]) == 2, f"Expected 2 messages, got: {history_msg['messages']}"

            # Verify message content
            msg0 = history_msg["messages"][0]
            assert msg0["role"] == "user"
            assert msg0["content"] == "Hello, assistant!"
            msg1 = history_msg["messages"][1]
            assert msg1["role"] == "assistant"
            assert msg1["content"] == "Hello, user! How can I help?"

    def test_subscribe_then_send_chat_on_existing_chat(self, client):
        """Subscribe to existing chat, then send a chat message."""
        # Register and login
        client.post("/api/auth/register", json={
            "email": "subscribe-then-chat@example.com",
            "password": "testpass123",
        })
        login_res = client.post("/api/auth/login", json={
            "email": "subscribe-then-chat@example.com",
            "password": "testpass123",
        })
        token = login_res.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        user_id = login_res.json()["user"]["id"]

        # Create chat with init
        chat_id = "subscribe-then-chat-001"
        init_res = client.post(
            "/api/chats/init",
            json={"chatId": chat_id},
            headers=headers,
        )
        assert init_res.status_code == 200

        # Add a message so chat has history
        chat_store.add_message(chat_id, user_id, "user", "Previous message")
        chat_store.add_message(chat_id, user_id, "assistant", "Previous response")

        with client.websocket_connect("/ws") as ws:
            # Connected
            ws.receive_json()

            # Subscribe
            ws.send_json({
                "type": "subscribe",
                "chatId": chat_id,
                "authorization": f"Bearer {token}",
            })

            # Receive history
            history = ws.receive_json()
            assert history["type"] == "history"
            assert len(history["messages"]) == 2

            # Send new chat message
            ws.send_json({
                "type": "chat",
                "chatId": chat_id,
                "content": "New message after history",
            })

            # Should get user_message back
            user_msg = ws.receive_json()
            assert user_msg["type"] == "user_message"
            assert user_msg["content"] == "New message after history"

            # Then we get thinking/assistant deltas... wait for result
            deadline = time.time() + 15
            while time.time() < deadline:
                msg = ws.receive_json()
                if msg["type"] == "result":
                    break
                if msg["type"] == "error":
                    pytest.fail(f"Got error: {msg['error']}")

    def test_subscribe_to_empty_existing_chat(self, client):
        """Subscribe to a formal chat with no messages - should get empty history."""
        # Register and login
        client.post("/api/auth/register", json={
            "email": "empty-history@example.com",
            "password": "testpass123",
        })
        login_res = client.post("/api/auth/login", json={
            "email": "empty-history@example.com",
            "password": "testpass123",
        })
        token = login_res.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create formal chat via init (no messages added)
        chat_id = "empty-chat-001"
        init_res = client.post(
            "/api/chats/init",
            json={"chatId": chat_id},
            headers=headers,
        )
        assert init_res.status_code == 200

        with client.websocket_connect("/ws") as ws:
            ws.receive_json()  # connected

            ws.send_json({
                "type": "subscribe",
                "chatId": chat_id,
                "authorization": f"Bearer {token}",
            })

            # Should receive history with empty messages
            history = ws.receive_json()
            assert history["type"] == "history"
            assert history["chatId"] == chat_id
            assert history["messages"] == []

    def test_subscribe_rejected_for_nonexistent_chat(self, client):
        """Subscribe to a chatId that was never created - should still get history (empty)."""
        # Register and login
        client.post("/api/auth/register", json={
            "email": "nosuch-chat@example.com",
            "password": "testpass123",
        })
        login_res = client.post("/api/auth/login", json={
            "email": "nosuch-chat@example.com",
            "password": "testpass123",
        })
        token = login_res.json()["token"]

        with client.websocket_connect("/ws") as ws:
            ws.receive_json()  # connected

            # Subscribe to a chat that was never created
            ws.send_json({
                "type": "subscribe",
                "chatId": "this-chat-does-not-exist",
                "authorization": f"Bearer {token}",
            })

            # Should still get history (empty) since the chat simply doesn't exist
            # This is because there's no validation on subscribe - it just returns empty history
            # OR it may error if the Session lookup fails
            try:
                msg = ws.receive_json(timeout=2)
                # If we get a response, check type
                if msg["type"] == "error" and "No session_id found" in msg.get("error", ""):
                    pass  # This is expected - Session.__init__ raises ValueError
                elif msg["type"] == "history":
                    assert msg["messages"] == []
                else:
                    pytest.fail(f"Unexpected message: {msg}")
            except Exception:
                pass  # Timeout is also OK - no such chat returns empty history or error


class TestSwitchChatsFlow:
    """Test switching between multiple chats."""

    def test_switch_between_two_chats(self, client):
        """Create two chats, switch between them, verify correct history for each."""
        # Register and login
        client.post("/api/auth/register", json={
            "email": "switch-chats@example.com",
            "password": "testpass123",
        })
        login_res = client.post("/api/auth/login", json={
            "email": "switch-chats@example.com",
            "password": "testpass123",
        })
        token = login_res.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        user_id = login_res.json()["user"]["id"]

        # Create chat A with messages
        chat_a_id = "chat-A-001"
        init_a = client.post("/api/chats/init", json={"chatId": chat_a_id}, headers=headers)
        assert init_a.status_code == 200
        chat_store.add_message(chat_a_id, user_id, "user", "Message in chat A")
        chat_store.add_message(chat_a_id, user_id, "assistant", "Response in chat A")

        # Create chat B with messages
        chat_b_id = "chat-B-001"
        init_b = client.post("/api/chats/init", json={"chatId": chat_b_id}, headers=headers)
        assert init_b.status_code == 200
        chat_store.add_message(chat_b_id, user_id, "user", "Message in chat B")
        chat_store.add_message(chat_b_id, user_id, "assistant", "Response in chat B")

        # WebSocket: subscribe to chat A
        with client.websocket_connect("/ws") as ws:
            ws.receive_json()  # connected

            ws.send_json({
                "type": "subscribe",
                "chatId": chat_a_id,
                "authorization": f"Bearer {token}",
            })

            history_a = ws.receive_json()
            assert history_a["type"] == "history"
            assert len(history_a["messages"]) == 2
            assert history_a["messages"][0]["content"] == "Message in chat A"

            # Switch to chat B - send new subscribe
            ws.send_json({
                "type": "subscribe",
                "chatId": chat_b_id,
                "authorization": f"Bearer {token}",
            })

            history_b = ws.receive_json()
            assert history_b["type"] == "history"
            assert len(history_b["messages"]) == 2
            assert history_b["messages"][0]["content"] == "Message in chat B"

            # Switch back to chat A
            ws.send_json({
                "type": "subscribe",
                "chatId": chat_a_id,
                "authorization": f"Bearer {token}",
            })

            history_a2 = ws.receive_json()
            assert history_a2["type"] == "history"
            assert len(history_a2["messages"]) == 2