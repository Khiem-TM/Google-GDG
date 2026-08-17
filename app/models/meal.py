from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Numeric, SmallInteger, String, Uuid, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Meal(Base):
    __tablename__ = "meal"
    __table_args__ = {"schema": "nutrition"}

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    subject_id: Mapped[UUID] = mapped_column(ForeignKey("core.app_user.id", ondelete="RESTRICT"), index=True)
    current_revision_no: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MealRevision(Base):
    __tablename__ = "meal_revision"
    __table_args__ = (
        UniqueConstraint("meal_id", "revision_no", name="uq_meal_revision_meal_revision"),
        {"schema": "nutrition"},
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    meal_id: Mapped[UUID] = mapped_column(ForeignKey("nutrition.meal.id", ondelete="RESTRICT"), index=True)
    revision_no: Mapped[int] = mapped_column(Integer)
    meal_type: Mapped[str] = mapped_column(String(32))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    timezone: Mapped[str] = mapped_column(String(64))
    estimated: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class MealItem(Base):
    __tablename__ = "meal_item"
    __table_args__ = (
        UniqueConstraint("meal_revision_id", "ordinal", name="uq_meal_item_revision_ordinal"),
        CheckConstraint("quantity_canonical > 0", name="meal_item_positive_quantity"),
        {"schema": "nutrition"},
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    meal_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("nutrition.meal_revision.id", ondelete="RESTRICT"), index=True
    )
    food_id: Mapped[UUID] = mapped_column(ForeignKey("nutrition.food.id", ondelete="RESTRICT"), index=True)
    food_serving_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("nutrition.food_serving.id", ondelete="RESTRICT"), nullable=True
    )
    ordinal: Mapped[int] = mapped_column(SmallInteger)
    display_name_snapshot: Mapped[str] = mapped_column(String(255))
    quantity_canonical: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    canonical_unit: Mapped[str] = mapped_column(String(16), default="g")
    original_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    original_unit: Mapped[str] = mapped_column(String(16))
    catalog_version: Mapped[int] = mapped_column(Integer)
    estimated: Mapped[bool] = mapped_column(default=False, nullable=False)


class MealItemNutrientSnapshot(Base):
    __tablename__ = "meal_item_nutrient_snapshot"
    __table_args__ = (
        UniqueConstraint("meal_item_id", "nutrient_definition_id", name="uq_item_snapshot_item_nutrient"),
        {"schema": "nutrition"},
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    meal_item_id: Mapped[UUID] = mapped_column(ForeignKey("nutrition.meal_item.id", ondelete="RESTRICT"), index=True)
    nutrient_definition_id: Mapped[UUID] = mapped_column(
        ForeignKey("nutrition.nutrient_definition.id", ondelete="RESTRICT"), index=True
    )
    amount_canonical: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    canonical_unit: Mapped[str] = mapped_column(String(16))
    food_catalog_version: Mapped[int] = mapped_column(Integer)
    calculation_version: Mapped[str] = mapped_column(String(32), default="meal_snapshot_v1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class MealNutrientSnapshot(Base):
    __tablename__ = "meal_nutrient_snapshot"
    __table_args__ = (
        UniqueConstraint("meal_revision_id", "nutrient_definition_id", name="uq_meal_snapshot_revision_nutrient"),
        {"schema": "nutrition"},
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    meal_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("nutrition.meal_revision.id", ondelete="RESTRICT"), index=True
    )
    nutrient_definition_id: Mapped[UUID] = mapped_column(
        ForeignKey("nutrition.nutrient_definition.id", ondelete="RESTRICT"), index=True
    )
    amount_canonical: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    canonical_unit: Mapped[str] = mapped_column(String(16))
    calculation_version: Mapped[str] = mapped_column(String(32), default="meal_snapshot_v1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
