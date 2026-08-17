from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, Response, status

from app.api.dependencies import CurrentUser, DbSession, get_request_id, parse_if_match
from app.core.idempotency import validate_idempotency_key
from app.schemas.common import DataEnvelope
from app.schemas.meal import MealRead, MealWrite
from app.services import meal_service

router = APIRouter()


@router.get("", response_model=DataEnvelope[list[MealRead]])
def list_meals(current_user: CurrentUser, db: DbSession, limit: int = Query(default=20, ge=1, le=100)) -> DataEnvelope[list[MealRead]]:
    return DataEnvelope(data=meal_service.list_owned(db, current_user.id, limit), meta={"limit": limit})


@router.get("/{meal_id}", response_model=DataEnvelope[MealRead])
def get_meal(meal_id: UUID, current_user: CurrentUser, db: DbSession) -> DataEnvelope[MealRead]:
    return DataEnvelope(data=meal_service.get_owned(db, current_user.id, meal_id))


@router.post("", response_model=DataEnvelope[MealRead], status_code=status.HTTP_201_CREATED)
def create_meal(
    payload: MealWrite,
    http_request: Request,
    current_user: CurrentUser,
    db: DbSession,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> DataEnvelope[MealRead]:
    with db.begin():
        result = meal_service.create(
            db,
            current_user,
            payload,
            validate_idempotency_key(idempotency_key),
            get_request_id(http_request),
        )
    return DataEnvelope(data=result)


@router.put("/{meal_id}", response_model=DataEnvelope[MealRead])
def replace_meal(
    meal_id: UUID,
    payload: MealWrite,
    http_request: Request,
    current_user: CurrentUser,
    db: DbSession,
    expected_version: int = Depends(parse_if_match),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> DataEnvelope[MealRead]:
    with db.begin():
        result = meal_service.replace(
            db,
            current_user,
            meal_id,
            expected_version,
            payload,
            validate_idempotency_key(idempotency_key),
            get_request_id(http_request),
        )
    return DataEnvelope(data=result)


@router.delete("/{meal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_meal(
    meal_id: UUID,
    http_request: Request,
    current_user: CurrentUser,
    db: DbSession,
    expected_version: int = Depends(parse_if_match),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> Response:
    with db.begin():
        meal_service.delete(
            db,
            current_user,
            meal_id,
            expected_version,
            validate_idempotency_key(idempotency_key),
            get_request_id(http_request),
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
