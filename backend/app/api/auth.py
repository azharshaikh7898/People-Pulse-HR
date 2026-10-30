from datetime import datetime, timezone

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_token_payload
from app.database import get_db
from app.models.user import User
from app.schemas.auth import PasswordChange, TokenOut, UserOut
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenOut, summary="Sign in with email (as 'username') and password")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user, token, expires = auth_service.authenticate(db, form.username, form.password)
    return {"access_token": token, "expires_at": expires, "user": user}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Invalidate the current token")
def logout(payload: dict = Depends(get_token_payload), db: Session = Depends(get_db)):
    expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    auth_service.revoke_token(db, payload["jti"], expires_at)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.put("/me/password", status_code=status.HTTP_204_NO_CONTENT, summary="Change your own password")
def change_password(body: PasswordChange, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    auth_service.change_password(db, user, body.current_password, body.new_password)
