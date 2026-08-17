"""SQLAlchemy models imported by Alembic metadata discovery."""

from app.models.audit import AuditEvent, OutboxEvent
from app.models.food import Food, FoodNutrient, FoodServing, NutrientDefinition
from app.models.idempotency import IdempotencyRecord
from app.models.meal import Meal, MealItem, MealItemNutrientSnapshot, MealNutrientSnapshot, MealRevision
from app.models.user import User

__all__ = [
    "AuditEvent",
    "Food",
    "FoodNutrient",
    "FoodServing",
    "IdempotencyRecord",
    "Meal",
    "MealItem",
    "MealItemNutrientSnapshot",
    "MealNutrientSnapshot",
    "MealRevision",
    "NutrientDefinition",
    "OutboxEvent",
    "User",
]
