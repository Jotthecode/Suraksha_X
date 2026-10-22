import base64
import datetime as dt
import hashlib
import hmac
import secrets

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session

from . import config
from .db import get_db
from .models import User

_PBKDF2_ROUNDS = 260_000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ROUNDS)
    return "pbkdf2_sha256${}${}${}".format(
        _PBKDF2_ROUNDS, base64.b64encode(salt).decode(), base64.b64encode(digest).decode()
    )


def verify_password(password: str, stored: str) -> bool:
    try:
        _, rounds, salt, digest = stored.split("$")
        expected = base64.b64decode(digest)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), base64.b64decode(salt), int(rounds))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def create_token(user_id: str) -> str:
    now = dt.datetime.now(dt.timezone.utc)
    payload = {"sub": user_id, "iat": now, "exp": now + dt.timedelta(days=config.TOKEN_TTL_DAYS)}
    return jwt.encode(payload, config.JWT_SECRET, algorithm="HS256")


def _token_from(request: Request) -> str:
    header = request.headers.get("Authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip()
    return ""


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = _token_from(request)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Login required")
    try:
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired session, please log in again")
    user = db.get(User, payload.get("sub"))
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Account not found, please log in again")
    return user


_basic = HTTPBasic(auto_error=False)


def require_admin(credentials: HTTPBasicCredentials | None = Depends(_basic)):
    if not config.ADMIN_PASSWORD:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Dashboard disabled: set ADMIN_PASSWORD on the server")
    ok = credentials is not None and hmac.compare_digest(
        credentials.username.encode(), config.ADMIN_USERNAME.encode()
    ) and hmac.compare_digest(credentials.password.encode(), config.ADMIN_PASSWORD.encode())
    if not ok:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Admin login required", headers={"WWW-Authenticate": 'Basic realm="SurakshaX"'}
        )
