from fastapi import APIRouter, Request, Response, status

from app.api.dependencies import CurrentUser, DbSession, get_request_id
from app.schemas.common import DataEnvelope
from app.schemas.user import UserRead, UserUpdate
from app.services import user_service

router = APIRouter()


@router.get("/me", response_model=DataEnvelope[UserRead])
def get_me(current_user: CurrentUser) -> DataEnvelope[UserRead]:
    return DataEnvelope(data=user_service.to_read(current_user))


@router.patch("/me", response_model=DataEnvelope[UserRead])
def update_me(
    payload: UserUpdate, http_request: Request, current_user: CurrentUser, db: DbSession
) -> DataEnvelope[UserRead]:
    with db.begin():
        user = user_service.update(db, current_user, payload, get_request_id(http_request))
        result = user_service.to_read(user)
    return DataEnvelope(data=result)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_me(http_request: Request, current_user: CurrentUser, db: DbSession) -> Response:
    with db.begin():
        user_service.disable(db, current_user, get_request_id(http_request))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
