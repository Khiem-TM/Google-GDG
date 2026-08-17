from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class Schema(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class DataEnvelope(Schema, Generic[T]):
    data: T
    meta: dict[str, object] | None = None


class ErrorDetail(Schema):
    code: str
    message: str
    details: dict[str, object] | None = None
    request_id: str | None = None
