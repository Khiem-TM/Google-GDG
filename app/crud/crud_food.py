from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.food import Food, FoodNutrient, FoodServing, NutrientDefinition


def get_active(session: Session, food_id: UUID) -> Food | None:
    return session.scalar(select(Food).where(Food.id == food_id, Food.is_active.is_(True)))


def get_any(session: Session, food_id: UUID) -> Food | None:
    return session.scalar(select(Food).where(Food.id == food_id, Food.is_active.is_(True)))


def list_active(session: Session, limit: int) -> list[Food]:
    return list(
        session.scalars(
            select(Food)
            .where(Food.is_active.is_(True))
            .order_by(Food.canonical_name.asc(), Food.id.asc())
            .limit(limit)
        )
    )


def list_servings(session: Session, food_id: UUID) -> list[FoodServing]:
    return list(
        session.scalars(
            select(FoodServing)
            .where(FoodServing.food_id == food_id, FoodServing.is_active.is_(True))
            .order_by(FoodServing.code.asc())
        )
    )


def list_nutrients(session: Session, food_id: UUID) -> list[tuple[FoodNutrient, NutrientDefinition]]:
    return list(
        session.execute(
            select(FoodNutrient, NutrientDefinition)
            .join(NutrientDefinition, NutrientDefinition.id == FoodNutrient.nutrient_definition_id)
            .where(
                FoodNutrient.food_id == food_id,
                FoodNutrient.is_active.is_(True),
                NutrientDefinition.is_active.is_(True),
            )
            .order_by(NutrientDefinition.code.asc())
        ).tuples()
    )


def get_serving_for_food(session: Session, food_id: UUID, serving_id: UUID) -> FoodServing | None:
    return session.scalar(
        select(FoodServing).where(
            FoodServing.id == serving_id, FoodServing.food_id == food_id, FoodServing.is_active.is_(True)
        )
    )


def nutrient_definitions_by_code(session: Session, codes: set[str]) -> dict[str, NutrientDefinition]:
    if not codes:
        return {}
    definitions = session.scalars(
        select(NutrientDefinition).where(NutrientDefinition.code.in_(codes), NutrientDefinition.is_active.is_(True))
    )
    return {definition.code: definition for definition in definitions}
