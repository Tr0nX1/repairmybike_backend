#!/bin/bash

echo "=== [STARTUP] RepairMyBike Backend Initializing ==="

# Determine HTTP port (Railway injects $PORT)
PORT="${PORT:-${PORT_HTTP:-8080}}"
echo "[STARTUP] Binding to port: $PORT"

# 1. Attempt database connection wait (up to 20 seconds), but don't prevent server boot
echo "[STARTUP] Checking database connection..."
python manage.py wait_for_db --timeout 20 || echo "[WARNING] Database unavailable after 20s. Starting in degraded mode."

# 2. Apply database migrations if database is available
echo "[STARTUP] Running database migrations..."
python manage.py migrate --no-input || echo "[WARNING] Migrations skipped or failed. Server will start in degraded mode."

# 3. Collect static files
echo "[STARTUP] Collecting static files..."
python manage.py collectstatic --no-input

# 4. Start Gunicorn application server
echo "[STARTUP] Launching Gunicorn on 0.0.0.0:$PORT..."
exec gunicorn repairmybike.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers 2 \
    --timeout 120
