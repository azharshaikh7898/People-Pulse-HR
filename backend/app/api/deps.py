"""Reusable dependencies: current user, role checks."""
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.constants import Role
from app.core.errors import forbidden
from app.core.security import decode_access_token
from app.database import get_db
from app.models.user import User
from app.services import auth as auth_service

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

_CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials. Please sign in again",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_token_payload(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> dict:
    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError:
        raise _CREDENTIALS_ERROR
    jti = payload.get("jti")
    if not jti or auth_service.is_revoked(db, jti):
        raise _CREDENTIALS_ERROR
    return payload


def get_current_user(payload: dict = Depends(get_token_payload), db: Session = Depends(get_db)) -> User:
    try:
        user_id = int(payload["sub"])
    except (KeyError, ValueError):
        raise _CREDENTIALS_ERROR
    user = db.scalar(select(User).options(joinedload(User.employee)).where(User.id == user_id))
    if not user or not user.is_active:
        raise _CREDENTIALS_ERROR
    return user


def require_hr(user: User = Depends(get_current_user)) -> User:
    if user.role != Role.HR_ADMIN.value:
        raise forbidden("This action is restricted to HR administrators")
    return user


def is_hr(user: User) -> bool:
    return user.role == Role.HR_ADMIN.value
