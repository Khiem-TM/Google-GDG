from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.exceptions import AppError, ConflictError
from app.core.security import verify_password
from app.crud import crud_audit, crud_user
from app.models.user import User
from app.schemas.user import UserRead, UserUpdate


def to_read(user: User) -> UserRead:
    return UserRead.model_validate(user)


def update(session: Session, user: User, request: UserUpdate, request_id: str | None = None) -> User:
    if request.email is not None and request.email != user.email:
        existing = crud_user.get_by_email(session, request.email)
        if existing is not None:
            raise ConflictError("EMAIL_ALREADY_EXISTS", "An account with this email already exists")
        user.email = request.email
    if request.new_password is not None:
        if request.current_password is None or not verify_password(request.current_password, user.password_hash):
            raise AppError("AUTH_REQUIRED", "Current password is invalid", 401)
        from app.core.security import hash_password

        user.password_hash = hash_password(request.new_password)
        user.token_version += 1
    user.version += 1
    crud_audit.record_mutation(
        session,
        event_type="user.updated",
        aggregate_type="user",
        aggregate_id=user.id,
        aggregate_version=user.version,
        subject_id=user.id,
        request_id=request_id,
    )
    return user


def disable(session: Session, user: User, request_id: str | None = None) -> None:
    user.status = "disabled"
    user.deleted_at = datetime.now(UTC)
    user.token_version += 1
    user.version += 1
    crud_audit.record_mutation(
        session,
        event_type="user.disabled",
        aggregate_type="user",
        aggregate_id=user.id,
        aggregate_version=user.version,
        subject_id=user.id,
        request_id=request_id,
    )
