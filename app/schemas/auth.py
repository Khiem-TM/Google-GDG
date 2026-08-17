from pydantic import Field, field_validator

from app.schemas.common import Schema


class RegisterRequest(Schema):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=12, max_length=256)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if "@" not in value or value.startswith("@") or value.endswith("@"):
            raise ValueError("A valid email address is required")
        return value


class LoginRequest(RegisterRequest):
    pass


class AccessToken(Schema):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
