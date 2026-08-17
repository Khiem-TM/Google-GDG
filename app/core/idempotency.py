import hashlib
import json
from collections.abc import Mapping
from decimal import Decimal
from typing import Any

from app.core.exceptions import ConflictError


def _json_default(value: object) -> str:
    if isinstance(value, Decimal):
        return format(value, "f")
    raise TypeError(f"Unsupported canonical JSON value: {type(value)!r}")


def canonical_payload_hash(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, default=_json_default, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def validate_idempotency_key(value: str | None) -> str:
    if not value or len(value) > 255:
        raise AppError("VALIDATION_FAILED", "Idempotency-Key header is required", 400)
    return value


def idempotency_conflict() -> ConflictError:
    return ConflictError("IDEMPOTENCY_CONFLICT", "Idempotency key was already used with a different payload")
