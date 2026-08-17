from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AuditEvent(Base):
    __tablename__ = "audit_event"
    __table_args__ = {"schema": "audit"}

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True)
    event_type: Mapped[str] = mapped_column(String(128))
    subject_id: Mapped[UUID | None] = mapped_column(ForeignKey("core.app_user.id", ondelete="RESTRICT"), nullable=True)
    aggregate_type: Mapped[str] = mapped_column(String(64))
    aggregate_id: Mapped[UUID] = mapped_column(Uuid)
    aggregate_version: Mapped[int | None] = mapped_column(nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metadata_redacted: Mapped[dict[str, object]] = mapped_column(JSON, default=dict, nullable=False)
    payload_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)


class OutboxEvent(Base):
    __tablename__ = "outbox_event"
    __table_args__ = {"schema": "audit"}

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    event_id: Mapped[UUID] = mapped_column(Uuid, default=uuid4, unique=True, index=True)
    event_type: Mapped[str] = mapped_column(String(128))
    aggregate_type: Mapped[str] = mapped_column(String(64))
    aggregate_id: Mapped[UUID] = mapped_column(Uuid)
    aggregate_version: Mapped[int] = mapped_column()
    subject_id: Mapped[UUID] = mapped_column(ForeignKey("core.app_user.id", ondelete="RESTRICT"), index=True)
    payload: Mapped[dict[str, object]] = mapped_column(JSON, default=dict, nullable=False)
    delivery_state: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, index=True)
    attempt_count: Mapped[int] = mapped_column(default=0, nullable=False)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
