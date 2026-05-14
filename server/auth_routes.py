"""Authentication routes: register and login."""

from datetime import datetime, timezone

from fastapi import APIRouter, Header, HTTPException

import os

from server.auth import create_token, decode_token, generate_user_id, hash_password, verify_password
from server.database.connection import get_workspace_db
from server.models import User

AGENT_PROJECT_ROOT = os.environ.get("AGENT_PROJECT_ROOT", ".")

router = APIRouter(prefix="/api/auth", tags=["auth"])


def get_user_by_email(email: str) -> User | None:
    """Find user by email."""
    with get_workspace_db("system") as conn:
        row = conn.execute(
            "SELECT id, email, password_hash, created_at FROM users WHERE email = ?",
            (email,),
        ).fetchone()
        if not row:
            return None
        return User(
            id=row["id"],
            email=row["email"],
            password_hash=row["password_hash"],
            created_at=row["created_at"],
        )


def create_user(email: str, password: str) -> User:
    """Create a new user with hashed password."""
    user_id = generate_user_id()
    password_hash = hash_password(password)
    now = datetime.now(timezone.utc).isoformat()

    with get_workspace_db("system") as conn:
        conn.execute(
            "INSERT INTO users (id, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
            (user_id, email, password_hash, now),
        )
        conn.commit()

    # Create workspace directory immediately after user creation
    workspace_root = os.path.join(AGENT_PROJECT_ROOT, user_id)
    os.makedirs(workspace_root, exist_ok=True)

    return User(
        id=user_id,
        email=email,
        password_hash=password_hash,
        created_at=now,
    )


@router.post("/register")
async def register(payload: dict):
    """Register a new user account."""
    email = payload.get("email", "").strip().lower()
    password = payload.get("password", "")

    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Valid email is required")

    if not password or len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    # Check if user already exists
    existing = get_user_by_email(email)
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = create_user(email, password)
    token = create_token(user.id, user.email)

    return {
        "token": token,
        "user": user.to_dict(),
    }


@router.post("/login")
async def login(payload: dict):
    """Login and get a JWT token."""
    email = payload.get("email", "").strip().lower()
    password = payload.get("password", "")

    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password are required")

    user = get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_token(user.id, user.email)

    return {
        "token": token,
        "user": user.to_dict(),
    }


@router.get("/me")
async def me(authorization: str = Header(...)):
    """Get current user info from Bearer token in Authorization header."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization[7:]  # Remove "Bearer " prefix
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = get_user_by_email(payload["email"])
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user.to_dict()
