from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.core.idempotency import idempotency_conflict
from app.models.idempotency import IdempotencyRecord


def reserve_or_replay(
    session: Session, *, subject_id: UUID, operation: str, key: str, request_hash: str
) -> IdempotencyRecord:
    statement = (
        insert(IdempotencyRecord)
        .values(subject_id=subject_id, operation=operation, idempotency_key=key, request_hash=request_hash)
        .on_conflict_do_nothing(index_elements=["subject_id", "operation", "idempotency_key"])
    )
    result = cast(CursorResult[Any], session.execute(statement))
    record = session.scalar(
        select(IdempotencyRecord)
        .where(
            IdempotencyRecord.subject_id == subject_id,
            IdempotencyRecord.operation == operation,
            IdempotencyRecord.idempotency_key == key,
        )
        .with_for_update()
    )
    if record is None:
        raise RuntimeError("Unable to reserve idempotency record")
    if record.request_hash != request_hash:
        raise idempotency_conflict()
    if result.rowcount == 0 and record.response_data is None:
        raise AppError("ACTION_IN_PROGRESS", "A matching write is still being processed", 423)
    return record


def complete(record: IdempotencyRecord, response_data: dict[str, object], status_code: int = 200) -> None:
    record.response_data = response_data
    record.status_code = status_code
    record.completed_at = datetime.now(UTC)
