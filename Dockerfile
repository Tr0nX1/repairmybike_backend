# Use Python 3.11 slim image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=repairmybike.settings

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Create directories
RUN mkdir -p /app/static /app/media

# Expose port
EXPOSE 8000

# Simple startup command
CMD python manage.py migrate && \
    python manage.py collectstatic --noinput && \
    gunicorn repairmybike.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 120