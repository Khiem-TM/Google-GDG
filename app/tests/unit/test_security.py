from uuid import uuid4

import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.core.exceptions import AppError
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hash_never_equals_input() -> None:
    value = "correct-horse-battery-staple"
    password_hash = hash_password(value)
    assert password_hash != value
    assert verify_password(value, password_hash)
    assert not verify_password("wrong-password", password_hash)


def test_jwt_round_trip_preserves_subject_and_token_version() -> None:
    settings = Settings(jwt_secret=SecretStr("test-secret-must-be-at-least-32-bytes"))
    subject_id = uuid4()
    token = create_access_token(subject_id, 2, settings)
    assert decode_access_token(token, settings) == (subject_id, 2)


def test_BR_SEC_001_rejects_invalid_jwt() -> None:
    settings = Settings(jwt_secret=SecretStr("test-secret-must-be-at-least-32-bytes"))
    with pytest.raises(AppError, match="Invalid or expired"):
        decode_access_token("not-a-token", settings)
