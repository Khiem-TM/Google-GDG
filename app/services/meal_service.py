from datetime import UTC
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.core.idempotency import canonical_payload_hash
from app.crud import crud_audit, crud_food, crud_idempotency, crud_meal
from app.domain.nutrition import calculate_amount_per_basis, normalize_mass
from app.models.food import FoodNutrient, NutrientDefinition
from app.models.meal import (
    Meal,
    MealItem,
    MealItemNutrientSnapshot,
    MealNutrientSnapshot,
    MealRevision,
)
from app.models.user import User
from app.schemas.meal import MealItemRead, MealRead, MealType, MealWrite


def _snapshot_values(session: Session, revision_id: UUID) -> tuple[list[MealItemRead], dict[str, Decimal]]:
    items = list(
        session.scalars(select(MealItem).where(MealItem.meal_revision_id == revision_id).order_by(MealItem.ordinal))
    )
    item_reads: list[MealItemRead] = []
    for item in items:
        nutrients = {
            definition.code: snapshot.amount_canonical
            for snapshot, definition in session.execute(
                select(MealItemNutrientSnapshot, NutrientDefinition)
                .join(NutrientDefinition, NutrientDefinition.id == MealItemNutrientSnapshot.nutrient_definition_id)
                .where(MealItemNutrientSnapshot.meal_item_id == item.id)
            ).tuples()
        }
        item_reads.append(
            MealItemRead(
                id=item.id,
                food_id=item.food_id,
                food_serving_id=item.food_serving_id,
                display_name=item.display_name_snapshot,
                quantity_canonical=item.quantity_canonical,
                canonical_unit=item.canonical_unit,
                original_quantity=item.original_quantity,
                original_unit=item.original_unit,
                estimated=item.estimated,
                nutrients=nutrients,
            )
        )
    totals = {
        definition.code: snapshot.amount_canonical
        for snapshot, definition in session.execute(
            select(MealNutrientSnapshot, NutrientDefinition)
            .join(NutrientDefinition, NutrientDefinition.id == MealNutrientSnapshot.nutrient_definition_id)
            .where(MealNutrientSnapshot.meal_revision_id == revision_id)
        ).tuples()
    }
    return item_reads, totals


def to_read(session: Session, meal: Meal) -> MealRead:
    revision = crud_meal.get_current_revision(session, meal)
    if revision is None:
        raise RuntimeError("Meal has no current revision")
    items, totals = _snapshot_values(session, revision.id)
    return MealRead(
        id=meal.id,
        version=meal.version,
        revision_no=revision.revision_no,
        meal_type=cast(MealType, revision.meal_type),
        occurred_at=revision.occurred_at,
        timezone=revision.timezone,
        estimated=revision.estimated,
        deleted=not meal.is_active,
        items=items,
        nutrition_totals=totals,
    )


def get_owned(session: Session, subject_id: UUID, meal_id: UUID) -> MealRead:
    meal = crud_meal.get_owned_active(session, meal_id, subject_id)
    if meal is None:
        raise NotFoundError("Meal not found")
    return to_read(session, meal)


def list_owned(session: Session, subject_id: UUID, limit: int) -> list[MealRead]:
    return [to_read(session, meal) for meal, _ in crud_meal.list_owned_active(session, subject_id, limit)]


def _populate_revision(session: Session, meal: Meal, revision: MealRevision, request: MealWrite) -> None:
    total_by_definition: dict[UUID, tuple[str, Decimal]] = {}
    for ordinal, input_item in enumerate(request.items, start=1):
        food = crud_food.get_active(session, input_item.food_id)
        if food is None:
            raise AppError("FOOD_NOT_FOUND", "Selected food is inactive or unknown", 422)
        if food.basis_unit != "g":
            raise AppError("INVALID_UNIT", "Only gram-based foods are supported in this demo", 422)
        if input_item.food_serving_id is not None and crud_food.get_serving_for_food(
            session, food.id, input_item.food_serving_id
        ) is None:
            raise AppError("INVALID_SERVING", "Serving does not belong to the selected food", 422)
        try:
            quantity_g = normalize_mass(input_item.quantity, input_item.unit)
        except ValueError as exc:
            raise AppError("INVALID_UNIT", str(exc), 422) from exc
        item = MealItem(
            meal_revision_id=revision.id,
            food_id=food.id,
            food_serving_id=input_item.food_serving_id,
            ordinal=ordinal,
            display_name_snapshot=food.canonical_name,
            quantity_canonical=quantity_g,
            canonical_unit="g",
            original_quantity=input_item.quantity,
            original_unit=input_item.unit.lower(),
            catalog_version=food.catalog_version,
            estimated=input_item.estimated,
        )
        session.add(item)
        session.flush()
        nutrient_rows = list(
            session.execute(
                select(FoodNutrient, NutrientDefinition)
                .join(NutrientDefinition, NutrientDefinition.id == FoodNutrient.nutrient_definition_id)
                .where(
                    FoodNutrient.food_id == food.id,
                    FoodNutrient.is_active.is_(True),
                    NutrientDefinition.is_active.is_(True),
                )
            ).tuples()
        )
        if not nutrient_rows:
            raise AppError("INVALID_NUTRIENT", "Food has no active nutrient values", 422)
        for nutrient, definition in nutrient_rows:
            if nutrient.basis_unit != "g":
                raise AppError("INVALID_NUTRIENT", "Food nutrient has an incompatible basis unit", 422)
            amount = calculate_amount_per_basis(nutrient.amount_per_basis, quantity_g, nutrient.basis_amount)
            session.add(
                MealItemNutrientSnapshot(
                    meal_item_id=item.id,
                    nutrient_definition_id=definition.id,
                    amount_canonical=amount,
                    canonical_unit=definition.canonical_unit,
                    food_catalog_version=food.catalog_version,
                )
            )
            previous = total_by_definition.get(definition.id)
            total_by_definition[definition.id] = (
                definition.canonical_unit,
                (previous[1] if previous else Decimal("0")) + amount,
            )
    for definition_id, (unit, total) in total_by_definition.items():
        session.add(
            MealNutrientSnapshot(
                meal_revision_id=revision.id,
                nutrient_definition_id=definition_id,
                amount_canonical=total,
                canonical_unit=unit,
            )
        )


def _payload_data(request: MealWrite) -> dict[str, Any]:
    return request.model_dump(mode="json")


def create(
    session: Session, user: User, request: MealWrite, idempotency_key: str, request_id: str | None = None
) -> MealRead:
    payload = _payload_data(request)
    request_hash = canonical_payload_hash(payload)
    record = crud_idempotency.reserve_or_replay(
        session,
        subject_id=user.id,
        operation="meal.create",
        key=idempotency_key,
        request_hash=request_hash,
    )
    if record.response_data is not None:
        return MealRead.model_validate(record.response_data)
    meal = Meal(subject_id=user.id)
    session.add(meal)
    session.flush()
    revision = MealRevision(
        meal_id=meal.id,
        revision_no=1,
        meal_type=request.meal_type,
        occurred_at=request.occurred_at.astimezone(UTC),
        timezone=request.timezone,
        estimated=request.estimated,
    )
    session.add(revision)
    session.flush()
    _populate_revision(session, meal, revision, request)
    session.flush()
    result = to_read(session, meal)
    crud_audit.record_mutation(
        session,
        event_type="meal.created",
        aggregate_type="meal",
        aggregate_id=meal.id,
        aggregate_version=meal.version,
        subject_id=user.id,
        request_id=request_id,
        payload_hash=request_hash,
    )
    crud_idempotency.complete(record, result.model_dump(mode="json"), status_code=201)
    return result


def replace(
    session: Session,
    user: User,
    meal_id: UUID,
    expected_version: int,
    request: MealWrite,
    idempotency_key: str,
    request_id: str | None = None,
) -> MealRead:
    payload = _payload_data(request)
    request_hash = canonical_payload_hash(payload)
    record = crud_idempotency.reserve_or_replay(
        session,
        subject_id=user.id,
        operation=f"meal.replace:{meal_id}",
        key=idempotency_key,
        request_hash=request_hash,
    )
    if record.response_data is not None:
        return MealRead.model_validate(record.response_data)
    meal = crud_meal.get_owned_active(session, meal_id, user.id, lock=True)
    if meal is None:
        raise NotFoundError("Meal not found")
    if meal.version != expected_version:
        raise ConflictError("VERSION_CONFLICT", "Meal version is stale")
    meal.current_revision_no += 1
    meal.version += 1
    revision = MealRevision(
        meal_id=meal.id,
        revision_no=meal.current_revision_no,
        meal_type=request.meal_type,
        occurred_at=request.occurred_at.astimezone(UTC),
        timezone=request.timezone,
        estimated=request.estimated,
    )
    session.add(revision)
    session.flush()
    _populate_revision(session, meal, revision, request)
    session.flush()
    result = to_read(session, meal)
    crud_audit.record_mutation(
        session,
        event_type="meal.revised",
        aggregate_type="meal",
        aggregate_id=meal.id,
        aggregate_version=meal.version,
        subject_id=user.id,
        request_id=request_id,
        payload_hash=request_hash,
    )
    crud_idempotency.complete(record, result.model_dump(mode="json"))
    return result


def delete(
    session: Session,
    user: User,
    meal_id: UUID,
    expected_version: int,
    idempotency_key: str,
    request_id: str | None = None,
) -> None:
    request_hash = canonical_payload_hash({"meal_id": str(meal_id), "expected_version": expected_version})
    record = crud_idempotency.reserve_or_replay(
        session,
        subject_id=user.id,
        operation=f"meal.delete:{meal_id}",
        key=idempotency_key,
        request_hash=request_hash,
    )
    if record.response_data is not None:
        return
    meal = crud_meal.get_owned_active(session, meal_id, user.id, lock=True)
    if meal is None:
        raise NotFoundError("Meal not found")
    if meal.version != expected_version:
        raise ConflictError("VERSION_CONFLICT", "Meal version is stale")
    meal.is_active = False
    meal.version += 1
    crud_audit.record_mutation(
        session,
        event_type="meal.deleted",
        aggregate_type="meal",
        aggregate_id=meal.id,
        aggregate_version=meal.version,
        subject_id=user.id,
        request_id=request_id,
        payload_hash=request_hash,
    )
    crud_idempotency.complete(record, {"id": str(meal.id), "deleted": True, "version": meal.version}, status_code=204)
