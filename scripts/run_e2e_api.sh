#!/usr/bin/env bash
set -euo pipefail

: "${E2E_BASE_URL:?Set E2E_BASE_URL to an isolated API instance, for example http://api:8000}"
: "${E2E_DATABASE_URL:?Set E2E_DATABASE_URL to the isolated PostgreSQL database}"

uv run pytest app/tests/e2e -v
