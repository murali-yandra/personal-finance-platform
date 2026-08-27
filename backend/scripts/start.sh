#!/usr/bin/env sh
# Container entrypoint: apply database migrations, then serve the API.
#
# Hosting platforms assign the listening port through $PORT; local Docker Compose
# does not set it, so 8000 is the fallback.
set -eu

echo "Applying database migrations..."
alembic upgrade head

echo "Starting API server on port ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
