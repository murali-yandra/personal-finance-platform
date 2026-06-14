# Personal Finance Tracking Platform Backend

Backend service for the Personal Finance Tracking Platform.

This backend currently includes:

- FastAPI application startup
- Health endpoint
- Environment configuration
- PostgreSQL/SQLModel session wiring
- Alembic migration scaffold
- Internal event dispatcher scaffold
- Argon2id password hashing
- JWT access and refresh token services
- User registration, login, refresh, and current-user endpoints
- Authentication middleware for protected API paths
- Security and financial calculation foundations
- Pytest setup

SMS ingestion, Telegram, AI, and financial business logic are not implemented yet.

## Local Development

The local runtime file is `.env`. It is ignored by git and has been populated for this workspace. If it ever needs to be recreated:

```powershell
cd E:\ledger-ai\backend
Copy-Item .env.example .env
```

Replace every placeholder value in `.env` with environment-specific secrets and connection values. `.env.example` is documentation only and must not be used as a runtime secrets file.

Install `uv` if the command is not available:

```powershell
python -m pip install --user uv
```

Install dependencies:

```powershell
python -m uv sync --extra dev
```

Apply migrations when PostgreSQL is running:

```powershell
python -m uv run alembic upgrade head
```

Start the backend:

```powershell
python -m uv run uvicorn app.main:app --reload
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

## Validated Authentication Example

With the backend running locally, this PowerShell flow registers a user, logs in,
calls the current-user endpoint with the access token, and refreshes the access
token with the refresh token.

```powershell
$baseUrl = "http://localhost:8000"
$email = "murali+$([guid]::NewGuid().ToString('N'))@example.com"
$password = "SecurePass1"

$registerBody = @{
    email = $email
    password = $password
    display_name = "Murali Yandra"
} | ConvertTo-Json

$register = Invoke-RestMethod `
    -Method Post `
    -Uri "$baseUrl/api/v1/auth/register" `
    -ContentType "application/json" `
    -Body $registerBody

$loginBody = @{
    email = $email
    password = $password
} | ConvertTo-Json

$login = Invoke-RestMethod `
    -Method Post `
    -Uri "$baseUrl/api/v1/auth/login" `
    -ContentType "application/json" `
    -Body $loginBody

$authHeaders = @{
    Authorization = "Bearer $($login.data.access_token)"
}

$currentUser = Invoke-RestMethod `
    -Method Get `
    -Uri "$baseUrl/api/v1/users/me" `
    -Headers $authHeaders

$refreshBody = @{
    refresh_token = $login.data.refresh_token
} | ConvertTo-Json

$refresh = Invoke-RestMethod `
    -Method Post `
    -Uri "$baseUrl/api/v1/auth/refresh" `
    -ContentType "application/json" `
    -Body $refreshBody

$register
$currentUser
$refresh
```

Expected behavior:

- Register returns `success = true` and a `user_id`.
- Login returns `access_token`, `refresh_token`, and `expires_in = 900`.
- Current user returns the authenticated user's profile.
- Refresh returns a new `access_token`.

## Tests

```powershell
cd backend
python -m uv run pytest
```

Authentication-focused tests:

```powershell
cd backend
python -m uv run pytest tests\test_auth_middleware.py tests\test_auth_login_endpoint.py tests\test_auth_refresh_endpoint.py tests\test_current_user_endpoint.py
```

## Alembic

```powershell
cd backend
python -m uv run alembic upgrade head
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
