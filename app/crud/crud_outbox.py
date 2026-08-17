from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import OutboxEvent


def claim_pending(session: Session, limit: int) -> list[OutboxEvent]:
    events = list(
        session.scalars(
            select(OutboxEvent)
            .where(OutboxEvent.delivery_state.in_(("pending", "failed")), OutboxEvent.available_at <= datetime.now(UTC))
            .order_by(OutboxEvent.available_at, OutboxEvent.id)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
    )
    for event in events:
        event.delivery_state = "publishing"
        event.attempt_count += 1
    return events
