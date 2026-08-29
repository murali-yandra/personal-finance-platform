# Personal Finance Tracking Platform Backend

Sprint 0 foundation for the Personal Finance Tracking Platform.

This backend currently includes only infrastructure skeletons:

- FastAPI application startup
- Health endpoint
- Environment configuration
- PostgreSQL/SQLModel session wiring
- Alembic migration scaffold
- Internal event dispatcher scaffold
- Security and financial calculation placeholders
- Pytest setup

No authentication, SMS ingestion, Telegram, AI, or financial business logic is implemented in Sprint 0.

## Local Development

The local runtime file is `.env`. It is ignored by git and has been populated for this workspace. If it ever needs to be recreated:

```powershell
Copy-Item .env.example .env
```

Replace every placeholder value in `.env` with environment-specific secrets and connection values. `.env.example` is documentation only and must not be used as a runtime secrets file.

```powershell
cd backend
python -m uv sync --extra dev
uv run uvicorn app.main:app --reload
```

Health check:

```text
GET http://localhost:8000/health
```

## Tests

```powershell
cd backend
uv run pytest
```

## Alembic

```powershell
cd backend
uv run alembic upgrade head
```

There are no business tables or migrations yet.

## Docker

Run this from the repository root:

```powershell
cd ..
docker compose --env-file backend\.env up --build
```

The backend is available at:

```text
http://localhost:8000/health
```
