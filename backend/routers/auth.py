from fastapi import APIRouter, HTTPException
from models import LoginRequest, LoginResponse
import hashlib
import time
import secrets

router = APIRouter()

CREDENTIALS = {
    "admin": {"password": "admin123", "role": "admin"},
    "user": {"password": "user123", "role": "user"},
}


def generate_token(username: str, role: str) -> str:
    """Generate a unique auth token using secrets module for collision-free tokens."""
    raw = f"{username}:{role}:{time.time()}:{secrets.token_hex(16)}"
    return hashlib.sha256(raw.encode()).hexdigest()


ACTIVE_TOKENS = {}


def validate_token(token: str) -> dict | None:
    return ACTIVE_TOKENS.get(token)


def require_role(token: str, required_role: str):
    token_data = validate_token(token)
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    if token_data["role"] != required_role and required_role != "any":
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return token_data


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    user = CREDENTIALS.get(request.username)
    if not user or user["password"] != request.password:
        return LoginResponse(
            success=False,
            message="Invalid username or password",
        )

    token = generate_token(request.username, user["role"])
    ACTIVE_TOKENS[token] = {
        "username": request.username,
        "role": user["role"],
        "created_at": time.time(),
    }

    return LoginResponse(
        success=True,
        role=user["role"],
        token=token,
        message=f"Welcome, {request.username}!",
    )


@router.post("/logout")
async def logout(token: str = ""):
    """Logout by removing the token from active tokens.
    Token is passed as a query parameter: /api/logout?token=xxx
    """
    if token and token in ACTIVE_TOKENS:
        del ACTIVE_TOKENS[token]
    return {"success": True, "message": "Logged out"}
