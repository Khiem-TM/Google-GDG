from fastapi import APIRouter
from sqlalchemy import text

from app.api.dependencies import DbSession
from app.core.exceptions import AppError

router = APIRouter()


@router.get("/health/live")
def live() -> dict[str, object]:
    return {"data": {"status": "live"}}


@router.get("/health/ready")
def ready(db: DbSession) -> dict[str, object]:
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        raise AppError("SERVICE_UNAVAILABLE", "Database is unavailable", 503) from exc
    return {"data": {"status": "ready"}}
