FROM python:3.14.0-slim-bookworm

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

# Install Python dependencies
COPY requirements/base.txt requirements/celery.txt /tmp/requirements/
RUN pip install --upgrade pip && \
    pip install \
        -r /tmp/requirements/base.txt \
        -r /tmp/requirements/celery.txt && \
    rm -rf /root/.cache/

# Copy project
COPY . /code/

# Run Celery beat scheduler
CMD ["celery", "--app", "config.celery", "beat", "--loglevel", "info", "--scheduler", "django_celery_beat.schedulers:DatabaseScheduler"]
