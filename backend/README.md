# Personal Finance Tracking Platform Backend

Backend service for the Personal Finance Tracking Platform.

This backend currently includes:

- Argon2id password hashing, JWT access and refresh tokens, and authentication
  middleware over every `/api/v1` path
- Accounts with archive-instead-of-delete, and transactions with fingerprint
  duplicate detection, an append-only audit trail and Decimal balance updates
  committed in the same transaction as the write
- SMS ingestion (`/ingest/sms`, `/ingest/sms/batch`, `/ingest/reprocess`)
  authenticated by per-user API keys, with a read-only queue at `/raw-events`
- A parser engine for ICICI, HDFC and SBI with a generic fallback, merchant
  normalization and category resolution
- Reporting, the balance engine, transfers, historical import and AI suggestions
- Structured JSON logging with redaction, request correlation, rate limiting,
  roles and admin APIs
- A read-only dashboard at `/dashboard`

Telegram and AI are off by default behind `ENABLE_TELEGRAM` and `ENABLE_AI`.
MFA is the one roadmap item left open. See `docs/` for the per-sprint notes.

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

Authentication endpoints:

```text
POST http://localhost:8000/api/v1/auth/register
POST http://localhost:8000/api/v1/auth/login
POST http://localhost:8000/api/v1/auth/refresh
GET  http://localhost:8000/api/v1/users/me
```

Protected API paths under `/api/v1` require an access token:

```text
Authorization: Bearer <access_token>
```

Public paths are limited to health, registration, login, and refresh-token exchange.

## Tests

```powershell
cd backend
uv run pytest
```

Authentication-focused tests:

```powershell
cd backend
uv run pytest tests\test_auth_middleware.py tests\test_auth_login_endpoint.py tests\test_auth_refresh_endpoint.py tests\test_current_user_endpoint.py
```

## Alembic

```powershell
cd backend
uv run alembic upgrade head
```

Authentication migrations currently create the `users` and `user_settings` tables.

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
