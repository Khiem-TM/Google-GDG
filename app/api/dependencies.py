from typing import Annotated

from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.exceptions import AppError, ConflictError, ForbiddenError
from app.core.security import decode_access_token
from app.crud.crud_user import get_active_by_id
from app.db.session import get_db
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)
DbSession = Annotated[Session, Depends(get_db)]


def get_request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AppError("AUTH_REQUIRED", "Bearer authentication is required", 401)
    subject_id, token_version = decode_access_token(credentials.credentials, settings)
    user = get_active_by_id(db, subject_id)
    if user is None or user.token_version != token_version:
        raise AppError("AUTH_REQUIRED", "Access token is no longer valid", 401)
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_superuser(current_user: CurrentUser) -> User:
    if not current_user.is_superuser:
        raise ForbiddenError("Admin permission is required")
    return current_user


AdminUser = Annotated[User, Depends(require_superuser)]


def parse_if_match(value: Annotated[str | None, Header(alias="If-Match")]) -> int:
    if value is None:
        raise AppError("VALIDATION_FAILED", "If-Match header is required", 400)
    try:
        version = int(value.strip().strip('"'))
    except ValueError as exc:
        raise AppError("VALIDATION_FAILED", "If-Match must be an integer version", 400) from exc
    if version < 1:
        raise ConflictError("VERSION_CONFLICT", "If-Match version must be positive")
    return version
