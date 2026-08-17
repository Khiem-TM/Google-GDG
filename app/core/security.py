from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from app.core.config import Settings
from app.core.exceptions import AppError

_password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except (InvalidHashError, VerifyMismatchError):
        return False


def create_access_token(subject_id: UUID, token_version: int, settings: Settings) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(subject_id),
        "tv": token_version,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret.get_secret_value(), algorithm=settings.jwt_algorithm)


def decode_access_token(token: str, settings: Settings) -> tuple[UUID, int]:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "exp", "tv"]},
        )
        return UUID(str(payload["sub"])), int(payload["tv"])
    except (jwt.PyJWTError, ValueError, TypeError) as exc:
        raise AppError("AUTH_REQUIRED", "Invalid or expired access token", 401) from exc
