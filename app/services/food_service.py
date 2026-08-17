from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.crud import crud_audit, crud_food
from app.models.food import Food, FoodNutrient, FoodServing
from app.models.user import User
from app.schemas.food import FoodCreate, FoodRead, FoodUpdate, NutrientRead, ServingRead


def _to_read(session: Session, food: Food) -> FoodRead:
    servings = [ServingRead.model_validate(serving) for serving in crud_food.list_servings(session, food.id)]
    nutrients = [
        NutrientRead(
            code=definition.code,
            display_name=definition.display_name,
            canonical_unit=definition.canonical_unit,
            amount_per_basis=nutrient.amount_per_basis,
        )
        for nutrient, definition in crud_food.list_nutrients(session, food.id)
    ]
    return FoodRead(
        id=food.id,
        canonical_name=food.canonical_name,
        food_kind=food.food_kind,
        basis_amount=food.basis_amount,
        basis_unit=food.basis_unit,
        is_active=food.is_active,
        source_name=food.source_name,
        source_version=food.source_version,
        catalog_version=food.catalog_version,
        version=food.version,
        created_at=food.created_at,
        updated_at=food.updated_at,
        servings=servings,
        nutrients=nutrients,
    )


def get_active(session: Session, food_id: UUID) -> FoodRead:
    food = crud_food.get_active(session, food_id)
    if food is None:
        raise NotFoundError("Food not found")
    return _to_read(session, food)


def list_active(session: Session, limit: int) -> list[FoodRead]:
    return [_to_read(session, food) for food in crud_food.list_active(session, limit)]


def _definitions_or_error(session: Session, request: FoodCreate | FoodUpdate) -> dict[str, Any]:
    if request.nutrients is None:
        return {}
    definitions = crud_food.nutrient_definitions_by_code(session, {item.nutrient_code for item in request.nutrients})
    missing = sorted({item.nutrient_code for item in request.nutrients} - definitions.keys())
    if missing:
        raise AppError("INVALID_NUTRIENT", "One or more nutrient definitions are inactive or unknown", 422, {"codes": missing})
    return definitions


def create(session: Session, actor: User, request: FoodCreate, request_id: str | None = None) -> FoodRead:
    definitions = _definitions_or_error(session, request)
    food = Food(
        canonical_name=request.canonical_name.strip(),
        food_kind=request.food_kind,
        basis_amount=request.basis_amount,
        basis_unit=request.basis_unit.lower(),
        source_name=request.source_name,
        source_version=request.source_version,
    )
    session.add(food)
    session.flush()
    for serving in request.servings:
        session.add(
            FoodServing(
                food_id=food.id,
                code=serving.code,
                display_name=serving.display_name,
                canonical_amount=serving.canonical_amount,
                canonical_unit=serving.canonical_unit.lower(),
            )
        )
    for nutrient in request.nutrients:
        session.add(
            FoodNutrient(
                food_id=food.id,
                nutrient_definition_id=definitions[nutrient.nutrient_code].id,
                amount_per_basis=nutrient.amount_per_basis,
                basis_amount=request.basis_amount,
                basis_unit=request.basis_unit.lower(),
                source_version=request.source_version,
            )
        )
    session.flush()
    crud_audit.record_mutation(
        session,
        event_type="food.created",
        aggregate_type="food",
        aggregate_id=food.id,
        aggregate_version=food.version,
        subject_id=actor.id,
        request_id=request_id,
    )
    return _to_read(session, food)


def update(
    session: Session, actor: User, food_id: UUID, expected_version: int, request: FoodUpdate, request_id: str | None = None
) -> FoodRead:
    food = crud_food.get_any(session, food_id)
    if food is None:
        raise NotFoundError("Food not found")
    if food.version != expected_version:
        raise ConflictError("VERSION_CONFLICT", "Food version is stale")
    definitions = _definitions_or_error(session, request)
    for field in ("canonical_name", "food_kind", "basis_amount", "basis_unit"):
        value = getattr(request, field)
        if value is not None:
            setattr(food, field, value.lower() if field == "basis_unit" else value)
    if request.servings is not None:
        existing_servings = {
            serving.code: serving for serving in session.scalars(select(FoodServing).where(FoodServing.food_id == food.id))
        }
        requested_codes = {serving.code for serving in request.servings}
        for serving in request.servings:
            stored = existing_servings.get(serving.code)
            if stored is None:
                session.add(
                    FoodServing(
                        food_id=food.id,
                        code=serving.code,
                        display_name=serving.display_name,
                        canonical_amount=serving.canonical_amount,
                        canonical_unit=serving.canonical_unit.lower(),
                    )
                )
            else:
                stored.display_name = serving.display_name
                stored.canonical_amount = serving.canonical_amount
                stored.canonical_unit = serving.canonical_unit.lower()
                stored.is_active = True
                stored.version += 1
        for code, stored in existing_servings.items():
            if code not in requested_codes:
                stored.is_active = False
                stored.version += 1
    if request.nutrients is not None:
        existing_nutrients = {
            nutrient.nutrient_definition_id: nutrient
            for nutrient in session.scalars(select(FoodNutrient).where(FoodNutrient.food_id == food.id))
        }
        requested_definition_ids = set()
        for nutrient in request.nutrients:
            definition = definitions[nutrient.nutrient_code]
            requested_definition_ids.add(definition.id)
            stored = existing_nutrients.get(definition.id)
            if stored is None:
                session.add(
                    FoodNutrient(
                        food_id=food.id,
                        nutrient_definition_id=definition.id,
                        amount_per_basis=nutrient.amount_per_basis,
                        basis_amount=food.basis_amount,
                        basis_unit=food.basis_unit,
                        source_version=food.source_version,
                    )
                )
            else:
                stored.amount_per_basis = nutrient.amount_per_basis
                stored.basis_amount = food.basis_amount
                stored.basis_unit = food.basis_unit
                stored.source_version = food.source_version
                stored.is_active = True
        for definition_id, stored in existing_nutrients.items():
            if definition_id not in requested_definition_ids:
                stored.is_active = False
    food.version += 1
    food.catalog_version += 1
    session.flush()
    crud_audit.record_mutation(
        session,
        event_type="food.updated",
        aggregate_type="food",
        aggregate_id=food.id,
        aggregate_version=food.version,
        subject_id=actor.id,
        request_id=request_id,
    )
    return _to_read(session, food)


def deactivate(session: Session, actor: User, food_id: UUID, expected_version: int, request_id: str | None = None) -> None:
    food = crud_food.get_any(session, food_id)
    if food is None:
        raise NotFoundError("Food not found")
    if food.version != expected_version:
        raise ConflictError("VERSION_CONFLICT", "Food version is stale")
    food.is_active = False
    for serving in session.scalars(select(FoodServing).where(FoodServing.food_id == food.id)):
        serving.is_active = False
    for nutrient in session.scalars(select(FoodNutrient).where(FoodNutrient.food_id == food.id)):
        nutrient.is_active = False
    food.version += 1
    crud_audit.record_mutation(
        session,
        event_type="food.deactivated",
        aggregate_type="food",
        aggregate_id=food.id,
        aggregate_version=food.version,
        subject_id=actor.id,
        request_id=request_id,
    )
