from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class NutrientDefinition(Base):
    __tablename__ = "nutrient_definition"
    __table_args__ = {"schema": "nutrition"}

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(128))
    canonical_unit: Mapped[str] = mapped_column(String(16))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )


class Food(Base):
    __tablename__ = "food"
    __table_args__ = (
        CheckConstraint("basis_amount > 0", name="food_positive_basis_amount"),
        {"schema": "nutrition"},
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    canonical_name: Mapped[str] = mapped_column(String(255), index=True)
    food_kind: Mapped[str] = mapped_column(String(32), default="ingredient", nullable=False)
    basis_amount: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=Decimal("100"), nullable=False)
    basis_unit: Mapped[str] = mapped_column(String(16), default="g", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    source_name: Mapped[str] = mapped_column(String(128), default="demo_fixture", nullable=False)
    source_version: Mapped[str] = mapped_column(String(64), default="v1", nullable=False)
    catalog_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )


class FoodServing(Base):
    __tablename__ = "food_serving"
    __table_args__ = (
        UniqueConstraint("food_id", "code", name="uq_food_serving_food_code"),
        CheckConstraint("canonical_amount > 0", name="food_serving_positive_amount"),
        {"schema": "nutrition"},
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    food_id: Mapped[UUID] = mapped_column(ForeignKey("nutrition.food.id", ondelete="RESTRICT"), index=True)
    code: Mapped[str] = mapped_column(String(64))
    display_name: Mapped[str] = mapped_column(String(128))
    canonical_amount: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    canonical_unit: Mapped[str] = mapped_column(String(16), default="g")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class FoodNutrient(Base):
    __tablename__ = "food_nutrient"
    __table_args__ = (
        UniqueConstraint("food_id", "nutrient_definition_id", name="uq_food_nutrient_food_definition"),
        CheckConstraint("amount_per_basis >= 0", name="food_nutrient_non_negative_amount"),
        {"schema": "nutrition"},
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    food_id: Mapped[UUID] = mapped_column(ForeignKey("nutrition.food.id", ondelete="RESTRICT"), index=True)
    nutrient_definition_id: Mapped[UUID] = mapped_column(
        ForeignKey("nutrition.nutrient_definition.id", ondelete="RESTRICT"), index=True
    )
    amount_per_basis: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    basis_amount: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=Decimal("100"), nullable=False)
    basis_unit: Mapped[str] = mapped_column(String(16), default="g", nullable=False)
    source_version: Mapped[str] = mapped_column(String(64), default="v1", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
