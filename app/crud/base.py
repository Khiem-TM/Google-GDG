from typing import Protocol


class SoftDeletable(Protocol):
    is_active: bool


def soft_delete(model: SoftDeletable) -> None:
    model.is_active = False
