from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


def get_by_email(session: Session, email: str) -> User | None:
    return session.scalar(select(User).where(User.email == email))


def get_active_by_id(session: Session, user_id: UUID) -> User | None:
    return session.scalar(select(User).where(User.id == user_id, User.is_active.is_(True)))


def create(session: Session, user: User) -> User:
    session.add(user)
    session.flush()
    return user
