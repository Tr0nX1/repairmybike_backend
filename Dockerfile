# Use Python 3.12 slim image
FROM python:3.12-slim-bullseye

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/opt/venv/bin:$PATH"

# Create virtual environment
RUN python -m venv /opt/venv

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    libjpeg-dev \
    libcairo2 \
    gcc \
    build-essential \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /code

# Install Python dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r /tmp/requirements.txt

# Copy project
COPY . /code/

# Create necessary directories with proper permissions
RUN mkdir -p /code/staticfiles /code/media /code/logs && \
    chmod 755 /code/staticfiles /code/media /code/logs

# Collect static files
RUN python manage.py collectstatic --noinput

# Create startup script with proper error handling
RUN printf "#!/bin/bash\n" > /code/start.sh && \
    printf "set -e\n\n" >> /code/start.sh && \
    printf "echo 'Starting Django application...'\n\n" >> /code/start.sh && \
    printf "# Wait for database\n" >> /code/start.sh && \
    printf "echo 'Waiting for database...'\n" >> /code/start.sh && \
    printf "python manage.py wait_for_db --timeout 60\n\n" >> /code/start.sh && \
    printf "# Run migrations\n" >> /code/start.sh && \
    printf "echo 'Running migrations...'\n" >> /code/start.sh && \
    printf "python manage.py migrate --no-input\n\n" >> /code/start.sh && \
    printf "# Collect static files\n" >> /code/start.sh && \
    printf "echo 'Collecting static files...'\n" >> /code/start.sh && \
    printf "python manage.py collectstatic --noinput\n\n" >> /code/start.sh && \
    printf "# Start Gunicorn\n" >> /code/start.sh && \
    printf "echo 'Starting Gunicorn server...'\n" >> /code/start.sh && \
    printf "exec gunicorn repairmybike.wsgi:application \\\\\n" >> /code/start.sh && \
    printf "    --bind 0.0.0.0:\${PORT:-8000} \\\\\n" >> /code/start.sh && \
    printf "    --workers 2 \\\\\n" >> /code/start.sh && \
    printf "    --timeout 120 \\\\\n" >> /code/start.sh && \
    printf "    --keep-alive 2 \\\\\n" >> /code/start.sh && \
    printf "    --max-requests 1000 \\\\\n" >> /code/start.sh && \
    printf "    --max-requests-jitter 50 \\\\\n" >> /code/start.sh && \
    printf "    --preload \\\\\n" >> /code/start.sh && \
    printf "    --access-logfile - \\\\\n" >> /code/start.sh && \
    printf "    --error-logfile -\n" >> /code/start.sh && \
    chmod +x /code/start.sh

# Create non-root user and set permissions
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /code

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health/ || exit 1

# Run the application
CMD ["/code/start.sh"]