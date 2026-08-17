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

## API demo

- `POST /auth/register`, `POST /auth/login`
- `GET/PATCH/DELETE /users/me`
- `GET /foods`, `GET /foods/{id}`; Food mutation yêu cầu JWT admin và `If-Match` khi sửa/xóa.
- `POST/GET /meals`, `GET/PUT/DELETE /meals/{id}`; mọi mutation Meal cần `Idempotency-Key`, còn update/delete cần `If-Match`.

Food fixture chỉ dùng cho local/test. Tạo tài khoản admin sau migration, sau đó chạy
`uv run python -m app.scripts.seed_demo_catalog` nếu cần dữ liệu demo.

## Kiểm tra

```bash
uv run ruff check .
uv run pytest
```
