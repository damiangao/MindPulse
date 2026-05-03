"""Auth test utilities."""

from server.auth import create_token


def make_test_token(user_id: str = "test-user-123", email: str = "test@example.com") -> str:
    """Create a valid JWT token for testing."""
    return create_token(user_id, email)


def auth_header(user_id: str = "test-user-123", email: str = "test@example.com") -> dict:
    """Return Authorization header dict for testing."""
    token = make_test_token(user_id, email)
    return {"Authorization": f"Bearer {token}"}
