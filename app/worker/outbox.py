import json
import logging
import time
from datetime import UTC, datetime, timedelta

from kafka import KafkaProducer

from app.core.config import get_settings
from app.crud.crud_outbox import claim_pending
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


def publish_once(batch_size: int = 50) -> int:
    settings = get_settings()
    with SessionLocal.begin() as session:
        events = claim_pending(session, batch_size)
        event_ids = [event.id for event in events]
    if not event_ids:
        return 0

    producer = KafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        value_serializer=lambda value: json.dumps(value, separators=(",", ":")).encode("utf-8"),
    )
    published = 0
    for event_id in event_ids:
        with SessionLocal.begin() as session:
            from app.models.audit import OutboxEvent

            event = session.get(OutboxEvent, event_id)
            if event is None or event.delivery_state != "publishing":
                continue
            try:
                producer.send(
                    settings.kafka_topic,
                    key=str(event.event_id).encode("utf-8"),
                    value={"event_id": str(event.event_id), "event_type": event.event_type, "payload": event.payload},
                ).get(timeout=10)
            except Exception:
                event.delivery_state = "failed"
                event.available_at = datetime.now(UTC) + timedelta(seconds=min(event.attempt_count * 5, 300))
                logger.exception("outbox publish failed", extra={"event_id": str(event.event_id)})
            else:
                event.delivery_state = "published"
                event.published_at = datetime.now(UTC)
                published += 1
    producer.flush()
    producer.close()
    return published


def run_forever() -> None:
    while True:
        count = publish_once()
        time.sleep(0.1 if count else 2)


if __name__ == "__main__":
    run_forever()
