FROM python:3.11-slim

WORKDIR /app

# Install netcat (part of busybox) for the wait script
# and install necessary build tools for psycopg2
RUN apt-get update && \
    apt-get install -y netcat-traditional gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Make the entrypoint script executable (you did this before, but keep it)
RUN chmod +x /app/entrypoint.sh

# Set the entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]
