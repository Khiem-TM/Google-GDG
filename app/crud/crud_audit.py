from uuid import UUID

from sqlalchemy.orm import Session

from app.models.audit import AuditEvent, OutboxEvent


def record_mutation(
    session: Session,
    *,
    event_type: str,
    aggregate_type: str,
    aggregate_id: UUID,
    aggregate_version: int,
    subject_id: UUID,
    request_id: str | None,
    payload_hash: str | None = None,
) -> None:
    session.add(
        AuditEvent(
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            aggregate_version=aggregate_version,
            subject_id=subject_id,
            request_id=request_id,
            payload_hash=payload_hash,
            metadata_redacted={"actor_type": "user"},
        )
    )
    session.add(
        OutboxEvent(
            event_type=f"{event_type}.v1",
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            aggregate_version=aggregate_version,
            subject_id=subject_id,
            payload={"aggregate_id": str(aggregate_id), "aggregate_version": aggregate_version},
        )
    )
