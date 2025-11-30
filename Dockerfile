# Use Python 3.11 slim image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Create and activate virtual environment
RUN python -m venv /opt/venv

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create and set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copy project files
COPY . /app

# Create startup script
RUN echo '#!/bin/bash\n\
HTTP_PORT="${PORT_HTTP:-8080}"\n\
python manage.py migrate --no-input\n\
python manage.py collectstatic --no-input\n\
gunicorn repairmybike.wsgi:application --bind 0.0.0.0:$HTTP_PORT --workers 2 --timeout 120' > start.sh && \
    chmod +x start.sh

# Run the application
CMD ["/bin/bash", "./start.sh"]
