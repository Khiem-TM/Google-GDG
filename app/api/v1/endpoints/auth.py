from fastapi import APIRouter, Request, status

from app.api.dependencies import DbSession, get_request_id
from app.core.config import get_settings
from app.schemas.auth import AccessToken, LoginRequest, RegisterRequest
from app.schemas.common import DataEnvelope
from app.schemas.user import UserRead
from app.services import auth_service, user_service

router = APIRouter()


@router.post("/register", response_model=DataEnvelope[UserRead], status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest, http_request: Request, db: DbSession) -> DataEnvelope[UserRead]:
    with db.begin():
        user = auth_service.register(db, request, get_request_id(http_request))
        payload = user_service.to_read(user)
    return DataEnvelope(data=payload)


@router.post("/login", response_model=DataEnvelope[AccessToken])
def login(request: LoginRequest, db: DbSession) -> DataEnvelope[AccessToken]:
    return DataEnvelope(data=auth_service.login(db, request, get_settings()))
