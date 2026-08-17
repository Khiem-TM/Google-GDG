from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import AppError, ConflictError
from app.core.security import create_access_token, hash_password, verify_password
from app.crud import crud_audit, crud_user
from app.models.user import User
from app.schemas.auth import AccessToken, LoginRequest, RegisterRequest


def register(session: Session, request: RegisterRequest, request_id: str | None = None) -> User:
    existing = crud_user.get_by_email(session, request.email)
    if existing is not None:
        raise ConflictError("EMAIL_ALREADY_EXISTS", "An account with this email already exists")
    user = crud_user.create(session, User(email=request.email, password_hash=hash_password(request.password)))
    crud_audit.record_mutation(
        session,
        event_type="user.registered",
        aggregate_type="user",
        aggregate_id=user.id,
        aggregate_version=user.version,
        subject_id=user.id,
        request_id=request_id,
    )
    return user


def login(session: Session, request: LoginRequest, settings: Settings) -> AccessToken:
    user = crud_user.get_by_email(session, request.email)
    if user is None or not user.is_active:
        raise AppError("AUTH_REQUIRED", "Invalid email or password", 401)
    if not verify_password(request.password, user.password_hash):
        raise AppError("AUTH_REQUIRED", "Invalid email or password", 401)
    return AccessToken(
        access_token=create_access_token(user.id, user.token_version, settings),
        expires_in=settings.access_token_minutes * 60,
    )
