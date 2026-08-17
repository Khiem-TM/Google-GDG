from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from app.schemas.common import Schema


class ServingInput(Schema):
    code: str = Field(min_length=1, max_length=64)
    display_name: str = Field(min_length=1, max_length=128)
    canonical_amount: Decimal = Field(gt=0, max_digits=18, decimal_places=6)
    canonical_unit: str = Field(default="g", min_length=1, max_length=16)


class NutrientInput(Schema):
    nutrient_code: str = Field(min_length=1, max_length=64)
    amount_per_basis: Decimal = Field(ge=0, max_digits=18, decimal_places=6)


class FoodCreate(Schema):
    canonical_name: str = Field(min_length=1, max_length=255)
    food_kind: str = Field(default="ingredient", min_length=1, max_length=32)
    basis_amount: Decimal = Field(default=Decimal("100"), gt=0, max_digits=18, decimal_places=6)
    basis_unit: str = Field(default="g", min_length=1, max_length=16)
    source_name: str = Field(default="demo_fixture", min_length=1, max_length=128)
    source_version: str = Field(default="v1", min_length=1, max_length=64)
    servings: list[ServingInput] = Field(default_factory=list)
    nutrients: list[NutrientInput] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_nested_codes(self) -> "FoodCreate":
        if len({item.code for item in self.servings}) != len(self.servings):
            raise ValueError("Serving codes must be unique within a food")
        if len({item.nutrient_code for item in self.nutrients}) != len(self.nutrients):
            raise ValueError("Nutrient codes must be unique within a food")
        return self


class FoodUpdate(Schema):
    canonical_name: str | None = Field(default=None, min_length=1, max_length=255)
    food_kind: str | None = Field(default=None, min_length=1, max_length=32)
    basis_amount: Decimal | None = Field(default=None, gt=0, max_digits=18, decimal_places=6)
    basis_unit: str | None = Field(default=None, min_length=1, max_length=16)
    servings: list[ServingInput] | None = None
    nutrients: list[NutrientInput] | None = None

    @model_validator(mode="after")
    def require_change(self) -> "FoodUpdate":
        if all(
            value is None
            for value in (
                self.canonical_name,
                self.food_kind,
                self.basis_amount,
                self.basis_unit,
                self.servings,
                self.nutrients,
            )
        ):
            raise ValueError("At least one field must be provided")
        return self

    @field_validator("servings", "nutrients")
    @classmethod
    def reject_empty_replacement(cls, value: list[object] | None) -> list[object] | None:
        if value is not None and not value:
            raise ValueError("Replacement collections cannot be empty")
        return value


class ServingRead(Schema):
    id: UUID
    code: str
    display_name: str
    canonical_amount: Decimal
    canonical_unit: str
    is_active: bool


class NutrientRead(Schema):
    code: str
    display_name: str
    canonical_unit: str
    amount_per_basis: Decimal


class FoodRead(Schema):
    id: UUID
    canonical_name: str
    food_kind: str
    basis_amount: Decimal
    basis_unit: str
    is_active: bool
    source_name: str
    source_version: str
    catalog_version: int
    version: int
    created_at: datetime
    updated_at: datetime
    servings: list[ServingRead]
    nutrients: list[NutrientRead]
