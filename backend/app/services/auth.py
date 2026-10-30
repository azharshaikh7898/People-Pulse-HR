"""Login, logout (token revocation) and password change."""
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, joinedload

from app.core.errors import AppError, bad_request
from app.core.security import DUMMY_HASH, create_access_token, hash_password, verify_password
from app.models.user import RevokedToken, User


def authenticate(db: Session, email: str, password: str) -> tuple[User, str, datetime]:
    user = db.scalar(select(User).options(joinedload(User.employee)).where(User.email == email.strip().lower()))
    # Always run one bcrypt comparison so response time does not reveal whether the email exists.
    password_ok = verify_password(password, user.hashed_password if user else DUMMY_HASH)
    if not user or not password_ok:
        raise AppError(401, "Incorrect email or password")
    if not user.is_active:
        raise AppError(403, "This account has been deactivated. Please contact HR")
    token, expires = create_access_token(user.id, user.role)
    return user, token, expires


def revoke_token(db: Session, jti: str, expires_at: datetime) -> None:
    now = datetime.now(timezone.utc)
    db.execute(delete(RevokedToken).where(RevokedToken.expires_at < now))  # tidy up expired entries
    if not db.get(RevokedToken, jti):
        db.add(RevokedToken(jti=jti, expires_at=expires_at))
    db.commit()


def is_revoked(db: Session, jti: str) -> bool:
    return db.get(RevokedToken, jti) is not None


def change_password(db: Session, user: User, current: str, new: str) -> None:
    if not verify_password(current, user.hashed_password):
        raise bad_request("Current password is incorrect")
    if verify_password(new, user.hashed_password):
        raise bad_request("New password must be different from the current password")
    user.hashed_password = hash_password(new)
    db.commit()
