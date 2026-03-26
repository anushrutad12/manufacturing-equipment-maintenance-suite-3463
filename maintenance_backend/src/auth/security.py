from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.settings import get_settings
from src.db.models import User
from src.db.session import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# PUBLIC_INTERFACE
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a stored hash."""
    return pwd_context.verify(plain_password, hashed_password)


# PUBLIC_INTERFACE
def hash_password(password: str) -> str:
    """Hash a password for storage."""
    return pwd_context.hash(password)


def _create_access_token(subject: str, expires_delta: timedelta) -> str:
    s = get_settings()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode: Dict[str, Any] = {"sub": subject, "exp": expire}
    return jwt.encode(to_encode, s.jwt_secret_key, algorithm=s.jwt_algorithm)


# PUBLIC_INTERFACE
def create_access_token_for_user(user: User) -> str:
    """Create JWT access token for the given user."""
    s = get_settings()
    return _create_access_token(subject=str(user.id), expires_delta=timedelta(minutes=s.access_token_exp_minutes))


# PUBLIC_INTERFACE
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Get current authenticated user from JWT.

    Raises:
        HTTPException: 401 if invalid token or user not found/inactive.
    """
    s = get_settings()
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, s.jwt_secret_key, algorithms=[s.jwt_algorithm])
        user_id: Optional[str] = payload.get("sub")
        if not user_id:
            raise credentials_exception
    except JWTError as e:
        raise credentials_exception from e

    user = db.execute(select(User).where(User.id == int(user_id))).scalar_one_or_none()
    if not user or not user.is_active:
        raise credentials_exception
    return user


# PUBLIC_INTERFACE
def require_roles(*roles: str):
    """Dependency factory enforcing that current user has one of the given roles."""

    def _dep(user: User = Depends(get_current_user)) -> User:
        if user.role.value not in set(roles):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return _dep
