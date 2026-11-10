#!/bin/bash
set -e

echo "=== [STARTUP] RepairMyBike Backend Initializing ==="

# Determine HTTP port (Railway injects $PORT)
PORT="${PORT:-${PORT_HTTP:-8080}}"
echo "[STARTUP] Binding to port: $PORT"

# 1. Wait for PostgreSQL to become available (up to 60 seconds)
echo "[STARTUP] Waiting for database connection..."
python manage.py wait_for_db --timeout 60

# 2. Apply database migrations
echo "[STARTUP] Running database migrations..."
python manage.py migrate --no-input

# 3. Collect static files
echo "[STARTUP] Collecting static files..."
python manage.py collectstatic --no-input

# 4. Start Gunicorn application server
echo "[STARTUP] Launching Gunicorn on 0.0.0.0:$PORT..."
exec gunicorn repairmybike.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers 2 \
    --timeout 120
