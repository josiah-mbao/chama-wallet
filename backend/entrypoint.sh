#!/bin/sh

# =========================
# Robust Entrypoint Script
# =========================

# Exit immediately if a command exits with a non-zero status
set -e

# Load environment variables from .env (ignore comments/empty lines)
if [ -f /app/.env ]; then
  export $(grep -v '^#' /app/.env | xargs)
fi

# Use the docker-compose service name for DB host
DB_HOST=db
DB_PORT=5432

echo "Waiting for PostgreSQL at $DB_HOST:$DB_PORT to be ready..."

# Retry for up to 60 seconds
TRIES=0
MAX_TRIES=60

until nc -z -v -w5 "$DB_HOST" "$DB_PORT"; do
    TRIES=$((TRIES+1))
    echo "PostgreSQL is unavailable - sleeping ($TRIES/$MAX_TRIES)"
    sleep 1
    if [ "$TRIES" -ge "$MAX_TRIES" ]; then
        echo "Error: PostgreSQL not available after $MAX_TRIES seconds"
        exit 1
    fi
done

echo "PostgreSQL is up and running. Applying migrations..."

# Run Alembic migrations
alembic upgrade head

echo "Starting FastAPI application..."
exec uvicorn main:app --host 0.0.0.0 --port 8000
