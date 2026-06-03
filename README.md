# Ledger AI / Personal Finance Tracking Platform

Sprint 0 backend foundation for the Personal Finance Tracking Platform.

This project currently includes infrastructure only: FastAPI startup, health checks, environment configuration, SQLModel/PostgreSQL wiring, Alembic scaffold, Docker setup, event scaffolding, security placeholder, financial calculator placeholder, and tests.

No authentication, SMS ingestion, Telegram, AI, or financial business logic is implemented in Sprint 0.

## 1. Prerequisites

Run these commands in PowerShell.

Required tools:

- Python 3.12
- uv
- Docker Desktop
- Git, optional but recommended

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

Expected result:

```text
4 passed, 1 skipped
```

The skipped test is the PostgreSQL smoke test. It only runs when explicitly enabled.

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

There are no business tables or migrations yet, but the Alembic scaffold can be checked:

```powershell
cd E:\ledger-ai\backend
uv run alembic heads
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



