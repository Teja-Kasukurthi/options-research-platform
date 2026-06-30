from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import APIRouter, HTTPException, status
from jose import jwt
from pydantic import BaseModel

from app.core.config import settings

router = APIRouter()

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE = timedelta(hours=24)
REFRESH_TOKEN_EXPIRE = timedelta(days=30)


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


def _create_token(data: dict, expires_delta: timedelta) -> str:
    expire = datetime.now(timezone.utc) + expires_delta
    return jwt.encode({**data, "exp": expire}, settings.secret_key, algorithm=ALGORITHM)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest) -> TokenResponse:
    if body.email != settings.admin_email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not bcrypt.checkpw(body.password.encode(), settings.admin_password_hash.encode()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    payload = {"sub": body.email}
    return TokenResponse(
        access_token=_create_token(payload, ACCESS_TOKEN_EXPIRE),
        refresh_token=_create_token({**payload, "refresh": True}, REFRESH_TOKEN_EXPIRE),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: dict) -> TokenResponse:
    from jose import JWTError
    try:
        payload = jwt.decode(body.get("refresh_token", ""), settings.secret_key, algorithms=[ALGORITHM])
        if not payload.get("refresh"):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not a refresh token")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    new_payload = {"sub": payload["sub"]}
    return TokenResponse(
        access_token=_create_token(new_payload, ACCESS_TOKEN_EXPIRE),
        refresh_token=_create_token({**new_payload, "refresh": True}, REFRESH_TOKEN_EXPIRE),
    )


@router.post("/logout", status_code=204)
async def logout() -> None:
    # Stateless JWT — client drops the token
    pass
