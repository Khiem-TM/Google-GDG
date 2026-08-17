"""Black-box HTTP checks against an isolated running API instance.

Set E2E_BASE_URL and E2E_DATABASE_URL. The database is used only to seed the
catalog and provision an admin because those capabilities have no public API.
"""

import os
from collections.abc import Callable, Generator
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import Session

from app.db.seed import seed_demo_catalog
from app.models.food import Food
from app.models.user import User

E2E_BASE_URL = os.getenv("E2E_BASE_URL")
E2E_DATABASE_URL = os.getenv("E2E_DATABASE_URL")
PASSWORD = "e2e-password-123"


def _email(label: str) -> str:
    return f"{label}-{uuid4().hex}@example.test"


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _error(response: httpx.Response, status_code: int, code: str) -> None:
    assert response.status_code == status_code, response.text
    body = response.json()
    assert body["error"]["code"] == code
    assert body["error"]["request_id"]


@pytest.fixture(scope="session")
def database_url() -> str:
    if not E2E_DATABASE_URL:
        pytest.skip("Set E2E_DATABASE_URL to run E2E tests against an isolated database")
    return E2E_DATABASE_URL


@pytest.fixture(scope="session", autouse=True)
def seed_catalog(database_url: str) -> None:
    engine = create_engine(database_url)
    with Session(engine) as session, session.begin():
        seed_demo_catalog(session)


@pytest.fixture()
def client() -> Generator[httpx.Client, None, None]:
    if not E2E_BASE_URL:
        pytest.skip("Set E2E_BASE_URL to run E2E tests against a running API")
    with httpx.Client(base_url=E2E_BASE_URL, timeout=10.0) as http_client:
        yield http_client


@pytest.fixture()
def create_account(client: httpx.Client) -> Callable[[bool], tuple[str, str, str]]:
    def create(is_admin: bool = False) -> tuple[str, str, str]:
        email = _email("admin" if is_admin else "member")
        response = client.post("/api/v1/auth/register", json={"email": email, "password": PASSWORD})
        assert response.status_code == 201, response.text
        user_id = response.json()["data"]["id"]
        if is_admin:
            assert E2E_DATABASE_URL
            engine = create_engine(E2E_DATABASE_URL)
            with Session(engine) as session, session.begin():
                session.execute(update(User).where(User.id == user_id).values(is_superuser=True))
        login = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
        assert login.status_code == 200, login.text
        return email, user_id, login.json()["data"]["access_token"]

    return create


def _demo_food_id(database_url: str) -> str:
    engine = create_engine(database_url)
    with Session(engine) as session:
        food = session.scalar(
            select(Food).where(Food.canonical_name == "Bún chả demo", Food.is_active.is_(True))
        )
    assert food is not None
    return str(food.id)


def _meal_payload(food_id: str, quantity: str = "200") -> dict[str, object]:
    return {
        "meal_type": "lunch",
        "occurred_at": "2026-08-17T12:00:00+07:00",
        "timezone": "Asia/Ho_Chi_Minh",
        "items": [{"food_id": food_id, "quantity": quantity, "unit": "g"}],
    }


def _food_payload(name: str) -> dict[str, object]:
    return {
        "canonical_name": name,
        "food_kind": "ingredient",
        "basis_amount": "100",
        "basis_unit": "g",
        "source_name": "e2e_fixture",
        "source_version": "v1",
        "servings": [
            {
                "code": "portion",
                "display_name": "one portion",
                "canonical_amount": "50",
                "canonical_unit": "g",
            }
        ],
        "nutrients": [{"nutrient_code": "energy_kcal", "amount_per_basis": "90"}],
    }


def test_health_endpoints_and_request_id(client: httpx.Client) -> None:
    live = client.get("/api/v1/health/live", headers={"X-Request-Id": "e2e-live-request"})
    assert live.status_code == 200
    assert live.json() == {"data": {"status": "live"}}
    assert live.headers["X-Request-Id"] == "e2e-live-request"

    ready = client.get("/api/v1/health/ready")
    assert ready.status_code == 200
    assert ready.json() == {"data": {"status": "ready"}}


def test_auth_and_validation(client: httpx.Client, create_account: Callable[[bool], tuple[str, str, str]]) -> None:
    email, _, token = create_account(False)
    assert token

    duplicate = client.post("/api/v1/auth/register", json={"email": email, "password": PASSWORD})
    _error(duplicate, 409, "EMAIL_ALREADY_EXISTS")

    invalid_login = client.post("/api/v1/auth/login", json={"email": email, "password": "wrong-password-123"})
    _error(invalid_login, 401, "AUTH_REQUIRED")

    malformed = client.post(
        "/api/v1/auth/register",
        headers={"X-Request-Id": "e2e-validation-request"},
        json={"email": _email("invalid"), "password": PASSWORD, "unexpected": True},
    )
    _error(malformed, 422, "VALIDATION_FAILED")
    assert malformed.headers["X-Request-Id"] == "e2e-validation-request"


def test_user_lifecycle(client: httpx.Client, create_account: Callable[[bool], tuple[str, str, str]]) -> None:
    email, user_id, token = create_account(False)
    current = client.get("/api/v1/users/me", headers=_headers(token))
    assert current.status_code == 200
    assert current.json()["data"]["id"] == user_id
    assert current.json()["data"]["is_active"] is True

    updated_email = _email("renamed")
    update_email = client.patch("/api/v1/users/me", headers=_headers(token), json={"email": updated_email})
    assert update_email.status_code == 200
    assert update_email.json()["data"]["email"] == updated_email

    change_password = client.patch(
        "/api/v1/users/me",
        headers=_headers(token),
        json={"current_password": PASSWORD, "new_password": "e2e-new-password-456"},
    )
    assert change_password.status_code == 200
    _error(client.get("/api/v1/users/me", headers=_headers(token)), 401, "AUTH_REQUIRED")

    refreshed = client.post(
        "/api/v1/auth/login", json={"email": updated_email, "password": "e2e-new-password-456"}
    )
    assert refreshed.status_code == 200
    refreshed_token = refreshed.json()["data"]["access_token"]
    deleted = client.delete("/api/v1/users/me", headers=_headers(refreshed_token))
    assert deleted.status_code == 204
    _error(client.get("/api/v1/users/me", headers=_headers(refreshed_token)), 401, "AUTH_REQUIRED")


def test_food_crud_and_permissions(
    client: httpx.Client, create_account: Callable[[bool], tuple[str, str, str]]
) -> None:
    _, _, member_token = create_account(False)
    _, _, admin_token = create_account(True)
    _error(client.get("/api/v1/foods"), 401, "AUTH_REQUIRED")
    assert client.get("/api/v1/foods", headers=_headers(member_token)).status_code == 200

    payload = _food_payload(f"E2E food {uuid4().hex}")
    _error(client.post("/api/v1/foods", headers=_headers(member_token), json=payload), 403, "OWNERSHIP_DENIED")
    created = client.post("/api/v1/foods", headers=_headers(admin_token), json=payload)
    assert created.status_code == 201, created.text
    food = created.json()["data"]
    food_id = food["id"]
    version = food["version"]
    assert food["is_active"] is True

    assert client.get(f"/api/v1/foods/{food_id}", headers=_headers(member_token)).status_code == 200
    _error(client.patch(f"/api/v1/foods/{food_id}", headers=_headers(admin_token), json={"food_kind": "dish"}), 400, "VALIDATION_FAILED")
    _error(
        client.patch(
            f"/api/v1/foods/{food_id}",
            headers={**_headers(admin_token), "If-Match": '"999"'},
            json={"food_kind": "dish"},
        ),
        409,
        "VERSION_CONFLICT",
    )
    updated = client.patch(
        f"/api/v1/foods/{food_id}",
        headers={**_headers(admin_token), "If-Match": f'"{version}"'},
        json={"food_kind": "dish"},
    )
    assert updated.status_code == 200, updated.text
    updated_version = updated.json()["data"]["version"]
    assert updated_version == version + 1

    deleted = client.delete(
        f"/api/v1/foods/{food_id}",
        headers={**_headers(admin_token), "If-Match": f'"{updated_version}"'},
    )
    assert deleted.status_code == 204
    _error(client.get(f"/api/v1/foods/{food_id}", headers=_headers(member_token)), 404, "RESOURCE_NOT_FOUND")


def test_meal_crud_idempotency_and_ownership(
    client: httpx.Client,
    create_account: Callable[[bool], tuple[str, str, str]],
    database_url: str,
) -> None:
    _, _, owner_token = create_account(False)
    _, _, other_token = create_account(False)
    food_id = _demo_food_id(database_url)
    payload = _meal_payload(food_id)

    _error(client.get("/api/v1/meals"), 401, "AUTH_REQUIRED")
    _error(client.post("/api/v1/meals", headers=_headers(owner_token), json=payload), 400, "VALIDATION_FAILED")

    create_key = str(uuid4())
    created = client.post(
        "/api/v1/meals",
        headers={**_headers(owner_token), "Idempotency-Key": create_key},
        json=payload,
    )
    assert created.status_code == 201, created.text
    meal = created.json()["data"]
    meal_id = meal["id"]
    version = meal["version"]
    assert meal["revision_no"] == 1

    replay = client.post(
        "/api/v1/meals",
        headers={**_headers(owner_token), "Idempotency-Key": create_key},
        json=payload,
    )
    assert replay.status_code == 201
    assert replay.json()["data"]["id"] == meal_id
    _error(
        client.post(
            "/api/v1/meals",
            headers={**_headers(owner_token), "Idempotency-Key": create_key},
            json=_meal_payload(food_id, "250"),
        ),
        409,
        "IDEMPOTENCY_CONFLICT",
    )

    assert client.get("/api/v1/meals", headers=_headers(owner_token)).status_code == 200
    assert client.get(f"/api/v1/meals/{meal_id}", headers=_headers(owner_token)).status_code == 200
    _error(client.get(f"/api/v1/meals/{meal_id}", headers=_headers(other_token)), 404, "RESOURCE_NOT_FOUND")

    replace_key = str(uuid4())
    replaced = client.put(
        f"/api/v1/meals/{meal_id}",
        headers={**_headers(owner_token), "If-Match": f'"{version}"', "Idempotency-Key": replace_key},
        json=_meal_payload(food_id, "100"),
    )
    assert replaced.status_code == 200, replaced.text
    replacement = replaced.json()["data"]
    assert replacement["revision_no"] == 2
    assert replacement["version"] == version + 1
    _error(
        client.put(
            f"/api/v1/meals/{meal_id}",
            headers={**_headers(owner_token), "If-Match": f'"{version}"', "Idempotency-Key": str(uuid4())},
            json=payload,
        ),
        409,
        "VERSION_CONFLICT",
    )

    delete_key = str(uuid4())
    deleted = client.delete(
        f"/api/v1/meals/{meal_id}",
        headers={
            **_headers(owner_token),
            "If-Match": f'"{replacement["version"]}"',
            "Idempotency-Key": delete_key,
        },
    )
    assert deleted.status_code == 204
    replay_delete = client.delete(
        f"/api/v1/meals/{meal_id}",
        headers={
            **_headers(owner_token),
            "If-Match": f'"{replacement["version"]}"',
            "Idempotency-Key": delete_key,
        },
    )
    assert replay_delete.status_code == 204
    _error(client.get(f"/api/v1/meals/{meal_id}", headers=_headers(owner_token)), 404, "RESOURCE_NOT_FOUND")
