# Wellness CRUD API

FastAPI backend cho demo CRUD User, Food và Meal. Agent runtime dùng LangChain/LangGraph
được tách sang repository khác và chỉ tích hợp qua public OpenAPI.

## Chạy local

```bash
uv sync --all-groups
docker compose -f deploy/docker-compose.yml up -d postgres kafka
uv run alembic upgrade head
uv run python -m app.scripts.create_superuser admin@example.com
uv run uvicorn app.main:app --reload
```

API được phục vụ tại `/api/v1`; OpenAPI tại `/openapi.json` và `/docs`.

## Kiểm tra

```bash
uv run ruff check .
uv run pytest
```
