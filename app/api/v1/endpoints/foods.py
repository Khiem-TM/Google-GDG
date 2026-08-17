from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status

from app.api.dependencies import AdminUser, CurrentUser, DbSession, get_request_id, parse_if_match
from app.schemas.common import DataEnvelope
from app.schemas.food import FoodCreate, FoodRead, FoodUpdate
from app.services import food_service

router = APIRouter()


@router.get("", response_model=DataEnvelope[list[FoodRead]])
def list_foods(
    current_user: CurrentUser, db: DbSession, limit: int = Query(default=20, ge=1, le=100)
) -> DataEnvelope[list[FoodRead]]:
    return DataEnvelope(data=food_service.list_active(db, limit), meta={"limit": limit})


@router.get("/{food_id}", response_model=DataEnvelope[FoodRead])
def get_food(food_id: UUID, current_user: CurrentUser, db: DbSession) -> DataEnvelope[FoodRead]:
    return DataEnvelope(data=food_service.get_active(db, food_id))


@router.post("", response_model=DataEnvelope[FoodRead], status_code=status.HTTP_201_CREATED)
def create_food(payload: FoodCreate, http_request: Request, admin: AdminUser, db: DbSession) -> DataEnvelope[FoodRead]:
    with db.begin():
        result = food_service.create(db, admin, payload, get_request_id(http_request))
    return DataEnvelope(data=result)


@router.patch("/{food_id}", response_model=DataEnvelope[FoodRead])
def update_food(
    food_id: UUID,
    payload: FoodUpdate,
    http_request: Request,
    admin: AdminUser,
    db: DbSession,
    expected_version: int = Depends(parse_if_match),
) -> DataEnvelope[FoodRead]:
    with db.begin():
        result = food_service.update(db, admin, food_id, expected_version, payload, get_request_id(http_request))
    return DataEnvelope(data=result)


@router.delete("/{food_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_food(
    food_id: UUID,
    http_request: Request,
    admin: AdminUser,
    db: DbSession,
    expected_version: int = Depends(parse_if_match),
) -> Response:
    with db.begin():
        food_service.deactivate(db, admin, food_id, expected_version, get_request_id(http_request))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
