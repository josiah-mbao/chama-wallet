#!/bin/sh
set -e

# Ensure Python sees /app as the root for imports
export PYTHONPATH=/app

DB_HOST="db"
DB_PORT=5432

echo "Waiting for PostgreSQL at $DB_HOST:$DB_PORT to be ready..."

until nc -z -v -w30 "$DB_HOST" "$DB_PORT"
do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 1
 done

echo "PostgreSQL is up and running. Applying migrations."

# Apply database migrations with Alembic
alembic upgrade head

# Start the FastAPI application
exec uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
