from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.api.schemas import LoginRequest, TokenResponse, UserPublic
from src.auth.security import create_access_token_for_user, get_current_user, verify_password
from src.db.models import User
from src.db.session import get_db

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login",
    description="Login with email/password and receive a JWT access token.",
    operation_id="auth_login",
)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Authenticate a user using email/password and return a JWT token."""
    user = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if not user or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return TokenResponse(access_token=create_access_token_for_user(user))


@router.get(
    "/me",
    response_model=UserPublic,
    summary="Get current user",
    description="Return the authenticated user's profile.",
    operation_id="auth_me",
)
def me(user: User = Depends(get_current_user)) -> UserPublic:
    """Get currently authenticated user."""
    return UserPublic(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        is_active=user.is_active,
    )
