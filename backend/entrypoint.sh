#!/bin/sh

# The DB_HOST is "db" as defined in docker-compose.yml
DB_HOST="db"
DB_PORT=5432

echo "Waiting for PostgreSQL at $DB_HOST:$DB_PORT to be ready..."

# Loop until the connection succeeds
# Note: The 'nc' tool was installed in the Dockerfile for this check.
until nc -z -v -w30 "$DB_HOST" "$DB_PORT"
do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 1
done

echo "PostgreSQL is up and running. Applying migrations."

# Apply database migrations
# Alembic reads DATABASE_URL from the environment set by docker-compose.yml
alembic upgrade head

# Start the application
echo "Starting application..."
exec uvicorn main:app --host 0.0.0.0 --port 8000
