from datetime import datetime
from uuid import UUID

from pydantic import Field, model_validator

from app.schemas.common import Schema


class UserUpdate(Schema):
    email: str | None = Field(default=None, min_length=3, max_length=320)
    current_password: str | None = Field(default=None, min_length=12, max_length=256)
    new_password: str | None = Field(default=None, min_length=12, max_length=256)

    @model_validator(mode="after")
    def validate_password_change(self) -> "UserUpdate":
        if (self.current_password is None) != (self.new_password is None):
            raise ValueError("current_password and new_password must be provided together")
        if self.email is None and self.new_password is None:
            raise ValueError("At least one field must be provided")
        if self.email is not None:
            self.email = self.email.strip().lower()
            if "@" not in self.email:
                raise ValueError("A valid email address is required")
        return self


class UserRead(Schema):
    id: UUID
    email: str
    is_superuser: bool
    is_active: bool
    version: int
    created_at: datetime
    updated_at: datetime
