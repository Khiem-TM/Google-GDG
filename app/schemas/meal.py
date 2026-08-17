from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo

from pydantic import Field, field_validator

from app.schemas.common import Schema

MealType = Literal["breakfast", "lunch", "dinner", "snack", "other"]


class MealItemInput(Schema):
    food_id: UUID
    food_serving_id: UUID | None = None
    quantity: Decimal = Field(gt=0, max_digits=18, decimal_places=6)
    unit: str = Field(default="g", min_length=1, max_length=16)
    estimated: bool = False


class MealWrite(Schema):
    meal_type: MealType
    occurred_at: datetime
    timezone: str = Field(min_length=1, max_length=64)
    estimated: bool = False
    items: list[MealItemInput] = Field(min_length=1, max_length=50)

    @field_validator("occurred_at")
    @classmethod
    def require_timezone_aware_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("occurred_at must include a timezone offset")
        return value

    @field_validator("timezone")
    @classmethod
    def require_iana_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except Exception as exc:
            raise ValueError("timezone must be a valid IANA timezone") from exc
        return value


class MealItemRead(Schema):
    id: UUID
    food_id: UUID
    food_serving_id: UUID | None
    display_name: str
    quantity_canonical: Decimal
    canonical_unit: str
    original_quantity: Decimal
    original_unit: str
    estimated: bool
    nutrients: dict[str, Decimal]


class MealRead(Schema):
    id: UUID
    version: int
    revision_no: int
    meal_type: MealType
    occurred_at: datetime
    timezone: str
    estimated: bool
    deleted: bool
    items: list[MealItemRead]
    nutrition_totals: dict[str, Decimal]
