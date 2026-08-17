from app.main import app


def test_openapi_exposes_crud_contract_without_agent_routes() -> None:
    paths = app.openapi()["paths"]
    assert "/api/v1/auth/register" in paths
    assert "/api/v1/foods/{food_id}" in paths
    assert "/api/v1/meals/{meal_id}" in paths
    assert not any("internal" in path or "agent" in path for path in paths)
