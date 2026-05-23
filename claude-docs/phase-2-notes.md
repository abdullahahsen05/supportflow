# Phase 2 — Notes & Decisions

## Port conflict: 5432 → 5433

A local Postgres installation (Windows service, PID 8516) was already occupying port 5432.
Docker container is remapped to **5433:5432** to avoid the conflict.

- `docker-compose.yml`: `"5433:5432"`
- `DATABASE_URL`: `postgresql+psycopg://supportflow:supportflow@localhost:5433/supportflow`
- `.env.example` and `backend/.env` both reflect port 5433.

If 5433 is also in use, change the host port in `docker-compose.yml` and update `DATABASE_URL` accordingly.

## Driver: psycopg3 (psycopg[binary])

Using psycopg3 (not psycopg2). URL prefix is `postgresql+psycopg://`.

## Schema decisions

- **Integer primary keys** throughout (simpler for demo data; order_number 1004 works as a separate unique string column).
- **String columns for status/role/priority** fields (not Postgres native ENUM) — most migration-friendly; application layer validates with Python enums.
- **Relationships not defined** on models yet — ForeignKey constraints only. ORM `relationship()` added when queries need it (later phases).
- **`onupdate=func.now()`** on `updated_at` columns — ORM-level; direct SQL updates won't trigger it (acceptable for demo).
- `metadata_json` used instead of `metadata` to avoid SQLAlchemy MetaData name collision.

## Alembic

- Commands run from `backend/` directory with `.venv` activated.
- `alembic/env.py` pulls `DATABASE_URL` from pydantic-settings; no hardcoded URL in `alembic.ini`.
- To regenerate after model changes: `alembic revision --autogenerate -m "description"` + `alembic upgrade head`.
