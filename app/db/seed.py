from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.food import Food, FoodNutrient, NutrientDefinition

DEMO_NUTRIENTS = (
    ("energy_kcal", "Energy", "kcal"),
    ("protein_g", "Protein", "g"),
    ("carbohydrate_g", "Carbohydrate", "g"),
    ("fat_g", "Fat", "g"),
)


def seed_demo_catalog(session: Session) -> None:
    """Create a small, explicitly demo-only catalog without overwriting existing rows."""
    definitions: dict[str, NutrientDefinition] = {}
    for code, name, unit in DEMO_NUTRIENTS:
        definition = session.scalar(select(NutrientDefinition).where(NutrientDefinition.code == code))
        if definition is None:
            definition = NutrientDefinition(code=code, display_name=name, canonical_unit=unit)
            session.add(definition)
            session.flush()
        else:
            definition.is_active = True
        definitions[code] = definition

    food = session.scalar(select(Food).where(Food.canonical_name == "Bún chả demo"))
    if food is not None:
        food.is_active = True
        return

    food = Food(
        canonical_name="Bún chả demo",
        food_kind="prepared_dish",
        basis_amount=Decimal("100"),
        basis_unit="g",
        source_name="demo_fixture",
        source_version="2026-08-17",
    )
    session.add(food)
    session.flush()
    for code, amount in {
        "energy_kcal": Decimal("185"),
        "protein_g": Decimal("8.5"),
        "carbohydrate_g": Decimal("21.0"),
        "fat_g": Decimal("7.2"),
    }.items():
        session.add(
            FoodNutrient(
                food_id=food.id,
                nutrient_definition_id=definitions[code].id,
                amount_per_basis=amount,
                basis_amount=Decimal("100"),
                basis_unit="g",
                source_version="2026-08-17",
            )
        )
