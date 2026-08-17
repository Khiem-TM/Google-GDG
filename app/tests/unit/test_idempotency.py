from uuid import uuid4

import pytest

from app.core.exceptions import AppError
from app.core.idempotency import canonical_payload_hash, validate_idempotency_key


def test_BR_GEN_013_hash_is_stable_for_key_order() -> None:
    assert canonical_payload_hash({"b": 2, "a": 1}) == canonical_payload_hash({"a": 1, "b": 2})


def test_BR_GEN_007_rejects_non_uuid_idempotency_key() -> None:
    with pytest.raises(AppError, match="Idempotency-Key"):
        validate_idempotency_key("not-a-uuid")


def test_idempotency_accepts_uuid() -> None:
    key = str(uuid4())
    assert validate_idempotency_key(key) == key
