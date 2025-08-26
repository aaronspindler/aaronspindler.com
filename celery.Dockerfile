FROM python:3.13.7-slim-bookworm

# Define build-time arguments
ARG DATABASE_URL
ARG REDIS_URL
ARG CELERY_BROKER_URL
ARG DEBUG
ARG SECRET_KEY

# Set environment variables
ENV DATABASE_URL=${DATABASE_URL}
ENV REDIS_URL=${REDIS_URL}
ENV CELERY_BROKER_URL=${CELERY_BROKER_URL}
ENV DEBUG=${DEBUG}
ENV SECRET_KEY=${SECRET_KEY}
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
COPY requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip && \
    pip install -r /tmp/requirements.txt && \
    rm -rf /root/.cache/

# Copy project
COPY . /code/

# Run Celery worker with gevent pool for better concurrency
CMD ["celery", "--app", "config.celery", "worker", "--loglevel", "info", "--concurrency", "200", "-P", "gevent"]