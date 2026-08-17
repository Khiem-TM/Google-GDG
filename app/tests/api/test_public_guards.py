from fastapi.testclient import TestClient

from app.main import app


def test_health_live_does_not_need_database() -> None:
    response = TestClient(app).get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "live"


def test_BR_SEC_001_blocks_anonymous_catalog_and_meal_reads() -> None:
    client = TestClient(app)
    assert client.get("/api/v1/foods").status_code == 401
    assert client.get("/api/v1/meals").status_code == 401
