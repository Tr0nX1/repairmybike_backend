#!/bin/bash

# Determine HTTP port (Railway injects PORT_HTTP or PORT, default 8080)
HTTP_PORT="${PORT_HTTP:-${PORT:-8080}}"
echo "[STARTUP] Binding to port: $HTTP_PORT"

# Run migrations in background so server opens port immediately
(
    python manage.py migrate --no-input 2>&1 | while read -r line; do echo "[MIGRATE] $line"; done
) &

# Start Gunicorn server immediately so Railway port health check passes instantly
echo "[STARTUP] Launching Gunicorn on 0.0.0.0:$HTTP_PORT..."
exec gunicorn repairmybike.wsgi:application \
    --bind 0.0.0.0:$HTTP_PORT \
    --workers 2 \
    --timeout 120
