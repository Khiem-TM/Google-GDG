from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models.meal import Meal, MealRevision


def get_owned_active(session: Session, meal_id: UUID, subject_id: UUID, *, lock: bool = False) -> Meal | None:
    statement = select(Meal).where(Meal.id == meal_id, Meal.subject_id == subject_id, Meal.deleted_at.is_(None))
    if lock:
        statement = statement.with_for_update()
    return session.scalar(statement)


def get_current_revision(session: Session, meal: Meal) -> MealRevision | None:
    return session.scalar(
        select(MealRevision).where(MealRevision.meal_id == meal.id, MealRevision.revision_no == meal.current_revision_no)
    )


def list_owned_active(session: Session, subject_id: UUID, limit: int) -> list[tuple[Meal, MealRevision]]:
    return list(
        session.execute(
            select(Meal, MealRevision)
            .join(
                MealRevision,
                and_(MealRevision.meal_id == Meal.id, MealRevision.revision_no == Meal.current_revision_no),
            )
            .where(Meal.subject_id == subject_id, Meal.deleted_at.is_(None))
            .order_by(MealRevision.occurred_at.desc(), Meal.id.desc())
            .limit(limit)
        ).tuples()
    )
