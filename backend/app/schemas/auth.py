from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.core.constants import Role
from app.core.security import MAX_PASSWORD_BYTES


def validate_new_password(v: str) -> str:
    if len(v) < 8:
        raise ValueError("Password must be at least 8 characters")
    if len(v.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise ValueError("Password is too long (max 72 bytes)")
    if not any(c.isalpha() for c in v) or not any(c.isdigit() for c in v):
        raise ValueError("Password must contain at least one letter and one number")
    return v


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    role: Role
    employee_id: int | None
    display_name: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user: UserOut


class PasswordChange(BaseModel):
    current_password: str
    new_password: str

    _check = field_validator("new_password")(validate_new_password)
