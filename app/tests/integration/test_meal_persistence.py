import os
from collections.abc import Generator
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.security import hash_password
from app.crud import crud_meal
from app.db.seed import seed_demo_catalog
from app.models.food import Food
from app.models.meal import Meal, MealRevision
from app.models.user import User
from app.schemas.meal import MealItemInput, MealWrite
from app.services import meal_service

TEST_DATABASE_URL = os.getenv("WELLNESS_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="Set WELLNESS_TEST_DATABASE_URL after alembic upgrade to run PostgreSQL integration tests",
)


@pytest.fixture()
def session() -> Generator[Session, None, None]:
    if TEST_DATABASE_URL is None:
        pytest.skip("WELLNESS_TEST_DATABASE_URL is required")
    engine = create_engine(TEST_DATABASE_URL)
    with engine.begin() as connection:
        connection.execute(
            text("TRUNCATE TABLE audit.idempotency_record, audit.outbox_event, audit.audit_event, "
                 "nutrition.meal_item_nutrient_snapshot, nutrition.meal_nutrient_snapshot, nutrition.meal_item, "
                 "nutrition.meal_revision, nutrition.meal, nutrition.food_nutrient, nutrition.food_serving, "
                 "nutrition.food, nutrition.nutrient_definition, core.app_user RESTART IDENTITY CASCADE")
        )
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        yield db


def _create_user_and_food(session: Session) -> tuple[User, Food]:
    with session.begin():
        user = User(email="demo@example.com", password_hash=hash_password("demo-password-123"))
        session.add(user)
        session.flush()
        seed_demo_catalog(session)
        food = session.query(Food).filter(Food.canonical_name == "Bún chả demo").one()
    return user, food


def _payload(food: Food, quantity: str = "400") -> MealWrite:
    return MealWrite(
        meal_type="lunch",
        occurred_at=datetime.fromisoformat("2026-08-17T12:00:00+07:00"),
        timezone="Asia/Ho_Chi_Minh",
        items=[MealItemInput(food_id=food.id, quantity=Decimal(quantity), unit="g")],
    )


def test_BR_GEN_007_replays_same_meal_for_same_idempotency_key(session: Session) -> None:
    user, food = _create_user_and_food(session)
    key = str(uuid4())
    with session.begin():
        first = meal_service.create(session, user, _payload(food), key)
    with session.begin():
        replay = meal_service.create(session, user, _payload(food), key)
    assert replay.id == first.id
    assert replay.nutrition_totals["energy_kcal"] == Decimal("740.000")


def test_BR_MEAL_014_creates_new_immutable_revision(session: Session) -> None:
    user, food = _create_user_and_food(session)
    with session.begin():
        created = meal_service.create(session, user, _payload(food), str(uuid4()))
    with session.begin():
        revised = meal_service.replace(session, user, created.id, created.version, _payload(food, "200"), str(uuid4()))
    revisions = session.query(MealRevision).filter(MealRevision.meal_id == created.id).all()
    assert revised.revision_no == 2
    assert len(revisions) == 2
    assert created.nutrition_totals["energy_kcal"] == Decimal("740.000")
    assert revised.nutrition_totals["energy_kcal"] == Decimal("370.000")


def test_delete_marks_meal_inactive_and_preserves_revision_history(session: Session) -> None:
    user, food = _create_user_and_food(session)
    with session.begin():
        created = meal_service.create(session, user, _payload(food), str(uuid4()))
    with session.begin():
        meal_service.delete(session, user, created.id, created.version, str(uuid4()))

    meal = session.get(Meal, created.id)
    assert meal is not None
    assert meal.is_active is False
    assert crud_meal.get_owned_active(session, created.id, user.id) is None
    assert session.query(MealRevision).filter(MealRevision.meal_id == created.id).count() == 1
