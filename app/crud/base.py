from datetime import UTC, datetime
from typing import Protocol


class SoftDeletable(Protocol):
    deleted_at: datetime | None


def soft_delete(model: SoftDeletable) -> None:
    model.deleted_at = datetime.now(UTC)
