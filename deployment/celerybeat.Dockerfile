FROM python:3.14-slim

# Set Python environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create and set work directory
RUN mkdir -p /code
WORKDIR /code

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    curl \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency installation
RUN pip install --upgrade pip uv

# Install Python dependencies with uv lockfile
COPY requirements/base.txt /tmp/requirements.txt
RUN uv pip install --system --no-cache -r /tmp/requirements.txt

# Copy project
COPY . /code/

# Run Celery beat scheduler
CMD ["celery", "--app", "config.celery", "beat", "--loglevel", "info", "--scheduler", "django_celery_beat.schedulers:DatabaseScheduler"]
