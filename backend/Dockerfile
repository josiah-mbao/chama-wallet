FROM python:3.11-slim

WORKDIR /app

# Install netcat (part of busybox) for the wait script
# and install necessary build tools for psycopg2
RUN apt-get update && \
    apt-get install -y netcat-traditional gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy entrypoint first and make it executable
COPY entrypoint.sh .
RUN chmod +x /app/entrypoint.sh

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
