# Use Python 3.12 slim image
FROM python:3.12-slim-bullseye

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=repairmybike.settings \
    PATH="/opt/venv/bin:$PATH"

# Create a virtual environment
RUN python -m venv /opt/venv

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    libjpeg-dev \
    libcairo2 \
    gcc \
    build-essential \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /code

# Copy requirements and install Python dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r /tmp/requirements.txt

# Copy project files
COPY . /code/

# Create necessary directories
RUN mkdir -p /code/staticfiles /code/media /code/logs

# Collect static files
RUN python manage.py collectstatic --noinput

# Create a non-root user for security
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /code
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python manage.py check --deploy || exit 1

# Create and use the startup script
RUN printf "#!/bin/bash\n" > /code/start.sh && \
    printf "set -e\n\n" >> /code/start.sh && \
    printf "echo 'Starting Django application...'\n" >> /code/start.sh && \
    printf "python manage.py wait_for_db --timeout 60\n" >> /code/start.sh && \
    printf "python manage.py migrate --no-input\n" >> /code/start.sh && \
    printf "python manage.py collectstatic --noinput\n" >> /code/start.sh && \
    printf "exec gunicorn repairmybike.wsgi:application --bind 0.0.0.0:\${PORT:-8000} --workers 3 --timeout 120\n" >> /code/start.sh && \
    chmod +x /code/start.sh

# Run the application
CMD ["/bin/bash", "/code/start.sh"]