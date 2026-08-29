# Personal Finance Tracking Platform

A production-grade personal finance platform designed to track accounts, transactions, credit cards, balances, transfers, and financial insights.

Ledger AI is the current project folder and Docker resource name for the backend.

## Tech Stack

- FastAPI
- PostgreSQL
- SQLModel
- Alembic
- Docker
- Python 3.12
- GitHub Actions
- Ollama, future
- Telegram Bot, future

## Architecture

- Modular Monolith
- Event-Driven Internal Workflows
- UUID-based Entities
- Decimal Financial Calculations
- Soft Delete Support
- Audit Logging
- Merchant Pattern Learning, future
- Account Balance Reconciliation, future

## Status

All sprints 0-15 of `architecture/14-sprint_roadmap.md` are implemented.

| Sprint | Scope |
| --- | --- |
| 0-1 | Foundation, authentication |
| 2-4 | Accounts, transactions, audit trail, SMS ingestion |
| 5-7 | Parsing engine, merchant normalization, categories |
| 8-10 | Telegram, reporting, balance engine, transfers |
| 11-13 | Historical import, AI suggestions, learning engine |
| 14-15 | Structured logging, backups, rate limiting, per-user API keys, roles, admin APIs |

MVP scope (through Sprint 10) is feature-complete. Telegram and AI ship behind
`ENABLE_TELEGRAM` and `ENABLE_AI`, off by default until credentials are supplied.
MFA is the one roadmap item deliberately left open; see
`backend/docs/sprint-14-15-hardening-saas.md`.

A read-only dashboard is served at `/dashboard`: net worth, account balances,
the month's income and expenses, spending by category, and recent transactions.
It is a single static page with no build step, and it is not part of the sprint
roadmap, which defers a UI in favour of Telegram.

Per-sprint notes are in `backend/docs/`.

## Verify A Deployment

```powershell
$env:BASE_URL = "https://<your-service>.onrender.com"
$env:INGEST_API_KEY = "<your key>"
bash backend/scripts/smoke_mvp.sh
```

This walks register, login, account creation, SMS ingestion, and asserts the
transaction reaches the ledger, the balance, the reports and the audit trail,
and that a replayed message does not double-count.

## 1. Prerequisites

Run these commands in PowerShell.

Required tools:

- Python 3.12
- uv
- Docker Desktop
- Git

Check installed versions:

```powershell
python --version
uv --version
docker --version
docker compose version
```

If `uv` is not recognized, install it with the official Windows installer:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Close PowerShell, open a new PowerShell window, then verify:

```powershell
uv --version
```

If `uv` is still not recognized in the new window, run this once in that PowerShell session and verify again:

```powershell
$env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
uv --version
```

Python 3.14 is okay to have installed globally, but this project itself must run on Python `3.12.x`.

## 2. Go To The Project

```powershell
cd E:\ledger-ai
```

## 3. Environment File

Your local runtime file is:

```text
backend\.env
```

It has already been populated for this workspace and is ignored by git.

If you ever need to recreate it:

```powershell
Copy-Item backend\.env.example backend\.env
```

Then replace every placeholder in `backend\.env` before running the app or Docker Compose.

Check that the local file exists:

```powershell
Test-Path backend\.env
```

Check that no placeholders remain:

```powershell
Select-String -Path backend\.env -Pattern '<|replace-with|db-user|db-password|db-name'
```

This command should print nothing.

## 4. Install Backend Dependencies

This project requires Python 3.12. If your system Python is newer, such as Python 3.14, install and use Python 3.12 through uv:

```powershell
cd E:\ledger-ai\backend
uv python install 3.12
uv sync --python 3.12 --extra dev
```

Use this command for future dependency syncs too:

```powershell
cd E:\ledger-ai\backend
uv sync --python 3.12 --extra dev
```

## 5. Run Tests

```powershell
cd E:\ledger-ai\backend
uv run pytest
```

The suite runs against in-memory SQLite, so it needs no database service.

Skipped tests are the PostgreSQL-backed ones. They run only when explicitly
enabled via `RUN_DB_SMOKE_TEST=1` or `RUN_INTEGRATION_TESTS=1`.

## 6. Run Code Quality Checks

```powershell
cd E:\ledger-ai\backend
uv run ruff check .
uv run black --check .
uv run isort --check-only .
```

## 7. Run The App Locally Without Docker

This runs FastAPI directly on your machine.

```powershell
cd E:\ledger-ai\backend
uv run uvicorn app.main:app --reload
```

Open another PowerShell window and test the health endpoint:

```powershell
Invoke-RestMethod http://localhost:8000/health
```

Expected response:

```powershell
status
------
healthy
```

Stop the local server with `Ctrl+C`.

## 8. Run With Docker

Run this from the repository root:

```powershell
cd E:\ledger-ai
docker compose --env-file backend\.env up --build
```

The backend will be available at:

```text
http://localhost:8000/health
```

In another PowerShell window, verify it:

```powershell
Invoke-RestMethod http://localhost:8000/health
```

Expected response:

```powershell
status
------
healthy
```

Stop Docker containers with:

```powershell
docker compose --env-file backend\.env down
```

## 9. Run The PostgreSQL Smoke Test

The main Docker Compose file intentionally does not expose PostgreSQL on a host port. For the DB smoke test, start a temporary PostgreSQL 15 container with a local-only port:

```powershell
cd E:\ledger-ai
docker run --rm --name ledger-ai-db-smoke `
  -e POSTGRES_DB=finance `
  -e POSTGRES_USER=finance_app `
  -e POSTGRES_PASSWORD=finance_app_smoke_password `
  -p 127.0.0.1:55432:5432 `
  -d postgres:15
```

Wait until PostgreSQL is ready:

```powershell
docker exec ledger-ai-db-smoke pg_isready -U finance_app -d finance
```

When it returns `accepting connections`, run the smoke test:

```powershell
cd E:\ledger-ai\backend
$env:RUN_DB_SMOKE_TEST = '1'
$env:DATABASE_URL = 'postgresql+psycopg://finance_app:finance_app_smoke_password@localhost:55432/finance?connect_timeout=5'
uv run pytest tests\test_db_session.py
```

After the smoke test, clear the temporary environment variables:

```powershell
Remove-Item Env:\RUN_DB_SMOKE_TEST
Remove-Item Env:\DATABASE_URL
```

Stop the temporary PostgreSQL container:

```powershell
docker stop ledger-ai-db-smoke
```

## 10. Validate Docker Compose

```powershell
cd E:\ledger-ai
docker compose --env-file backend\.env config --quiet
```

This should complete without output.

## 11. Build Docker Image Only

```powershell
cd E:\ledger-ai
docker compose --env-file backend\.env build backend
```

## 12. Alembic Check

```powershell
cd E:\ledger-ai\backend
uv run alembic heads
uv run alembic current
```

## 13. Clean Generated Local Files

Use this if you want to remove local caches and virtual environments:

```powershell
cd E:\ledger-ai\backend
Remove-Item -Recurse -Force .venv*, .pytest_cache, .ruff_cache -ErrorAction SilentlyContinue
Get-ChildItem -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force
```

## 14. Common Issues

### Docker password mismatch

If Docker was previously started with a different PostgreSQL password, the old password may still exist inside the Docker volume.

Reset local Docker state with:

```powershell
cd E:\ledger-ai
docker compose --env-file backend\.env down -v
docker compose --env-file backend\.env up --build
```

This deletes the local PostgreSQL Docker volume. Use it only for local Sprint 0 development.

### Port 8000 already in use

Find the process:

```powershell
netstat -ano | findstr :8000
```

Stop the process using the PID from the last column:

```powershell
Stop-Process -Id <PID>
```

### Docker Desktop not running

Start Docker Desktop, wait until it says Docker is running, then rerun:

```powershell
docker compose version
```

## 15. Deploy To Render

The repository ships a Render Blueprint at `render.yaml`. It provisions a free
PostgreSQL instance and a Docker web service, and redeploys on every push.

### First deploy

1. Sign in at [render.com](https://render.com) and choose **New -> Blueprint**.
2. Select this repository. Render reads `render.yaml` and shows the plan: one
   database (`ledger-ai-db`) and one web service (`ledger-ai-backend`).
3. Render prompts for the two values that are deliberately not in the repository.
   Generate them first:

   ```powershell
   # JWT_SECRET - must be at least 32 bytes
   python -c "import secrets; print(secrets.token_urlsafe(48))"

   # INGEST_API_KEY - the key MacroDroid sends as the X-API-KEY header
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

4. Click **Apply**. The first build takes a few minutes.

`DATABASE_URL` is wired automatically from the managed database. The container
runs `backend/scripts/start.sh`, which applies `alembic upgrade head` before
starting the API, so schema changes ship with the code.

### Verify the deploy

```powershell
Invoke-RestMethod https://<your-service>.onrender.com/health
Invoke-RestMethod https://<your-service>.onrender.com/api/v1/health/ready
```

`/health` is dependency-free and is what Render polls. `/api/v1/health/ready`
additionally reports database connectivity.

### Environment variables

| Variable | Source | Notes |
| --- | --- | --- |
| `DATABASE_URL` | Managed database | Auto-wired. `postgres://` URLs are normalized to the psycopg driver at startup. |
| `JWT_SECRET` | You, in the dashboard | Minimum 32 bytes. |
| `INGEST_API_KEY` | You, in the dashboard | Shared key for the SMS ingestion endpoint. |
| `INGEST_USER_EMAIL` | You, in the dashboard | Email of the user that owns ingested SMS messages. |
| `CORS_ORIGINS` | Blueprint | Comma-separated browser origins. Empty disables CORS. |
| `ENABLE_AI`, `ENABLE_TELEGRAM` | Blueprint | Off by default until credentials are supplied. |

Never commit secrets. `.env` files are git-ignored per
`architecture/10-security_standards.md` section 10.

### Point MacroDroid at the deployment

#### 1. Create the account that owns the messages

The deployed instance starts with an empty database. Register yourself, then mint
an API key for the phone:

```powershell
$base = "https://<your-service>.onrender.com/api/v1"

Invoke-RestMethod "$base/auth/register" -Method Post -ContentType application/json `
  -Body '{"email":"you@example.com","password":"<your password>","display_name":"You"}'

$login = Invoke-RestMethod "$base/auth/login" -Method Post -ContentType application/json `
  -Body '{"email":"you@example.com","password":"<your password>"}'

$key = Invoke-RestMethod "$base/api-keys" -Method Post `
  -Headers @{ Authorization = "Bearer $($login.data.access_token)" } `
  -ContentType application/json -Body '{"name":"macrodroid"}'

$key.data.api_key   # shown once - copy it into MacroDroid now
```

A per-user key (`pfp_...`) identifies its owner by itself, so `INGEST_USER_EMAIL`
is not needed. Use the shared `INGEST_API_KEY` only if you skip this step, and
then `INGEST_USER_EMAIL` must name a registered, active user or every ingest call
returns `503 SERVICE_UNAVAILABLE`.

#### 2. Build the macro

Trigger: **SMS Received**, restricted to your bank senders. Action: **HTTP
Request**.

```text
POST https://<your-service>.onrender.com/api/v1/ingest/sms
X-API-KEY: <the pfp_... key from step 1>
Content-Type: application/json
```

Body:

```json
{
  "sender": "[sms_sender]",
  "message_text": "[sms_message]",
  "received_at": "[sms_received_date, yyyy-MM-dd'T'HH:mm:ss]"
}
```

Three details cost an evening each if missed:

- The field is **`message_text`**, not `message`. A wrong name is a `400`.
- **Send `sender`.** It is optional in the schema, but the bank parsers route on
  it. Without it the message body is used for routing instead and the parsed
  `bank_name` is empty, so an account is matched on last four digits alone.
- **`received_at` must be ISO-8601** (`2026-08-29T14:32:05`). MacroDroid's native
  SMS timestamp is epoch milliseconds or a locale string; format it explicitly or
  the request fails validation.

#### 3. Confirm messages are arriving

```powershell
$auth = @{ Authorization = "Bearer $($login.data.access_token)" }

# Everything captured, newest first
Invoke-RestMethod "$base/raw-events" -Headers $auth

# Only the messages no parser could read
Invoke-RestMethod "$base/raw-events?processing_status=UNKNOWN_FORMAT" -Headers $auth
```

`PROCESSED` became a transaction. `NEEDS_REVIEW` did too, but against an account
that was auto-created or archived. `IGNORED` is an OTP or promotional message the
pipeline correctly declined, not a gap. Only `UNKNOWN_FORMAT` and `FAILED` mean a
parser is missing.

Nothing is lost in the meantime: raw events are stored before parsing and are
never deleted, so once a parser is added, replay them with

```powershell
Invoke-RestMethod "$base/ingest/reprocess" -Method Post `
  -Headers @{ "X-API-KEY" = $key.data.api_key } `
  -ContentType application/json -Body '{}'
```

Bulk backfill of old messages should go to `POST /api/v1/ingest/sms/batch` (up to
1000 per request) rather than many single posts, which would exhaust the 100
requests per minute budget.

#### 4. Look at your data

Open `https://<your-service>.onrender.com/dashboard` and sign in with the account
from step 1.

### Free tier caveat

Render's free web services sleep after inactivity, so the first request after an
idle period takes a few seconds. Free PostgreSQL instances expire after 30 days.
Upgrade both to a paid plan before relying on this for real financial data, or
move to the VPS path in `architecture/11-deployment_standards.md` section 4.
