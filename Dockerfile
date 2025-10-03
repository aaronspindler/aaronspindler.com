# Multi-stage build for smaller final image
# Stage 1: Build dependencies
FROM python:3.13.7-slim-bookworm AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Stage 2: Playwright installation (separate for caching, only for web service)
FROM python:3.13.7-slim-bookworm AS playwright-installer

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Playwright and its dependencies
RUN playwright install --with-deps chromium

# Stage 3: Base runtime image (used for all services)
FROM python:3.13.7-slim-bookworm AS base

# Set Python environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Create and set work directory
WORKDIR /code

# Copy application code
COPY . /code/

# Stage 4: Web service (with Playwright and Node.js for frontend builds)
FROM base AS web

# Install Node.js for CSS and JS build pipeline
RUN apt-get update && apt-get install -y --no-install-recommends \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Copy Playwright installation from playwright stage
COPY --from=playwright-installer /root/.cache/ms-playwright /root/.cache/ms-playwright
COPY --from=playwright-installer /usr/lib /usr/lib
COPY --from=playwright-installer /usr/bin /usr/bin

# Copy package files for NPM installation
COPY package*.json postcss.config.js purgecss.config.js ./

# Install NPM dependencies and build assets
RUN npm ci || npm install
RUN npm run build:js

# Copy entrypoint script
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Expose port 80
EXPOSE 80

# Use entrypoint script
ENTRYPOINT ["/docker-entrypoint.sh"]

# Default command for web service
CMD ["gunicorn", "--bind", ":80", "--workers", "8", "config.wsgi", "--log-level", "info", "--access-logfile", "-", "--error-logfile", "-"]

# Stage 5: Celery worker (no Playwright or Node.js needed)
FROM base AS celery

CMD ["celery", "--app", "config.celery", "worker", "--loglevel", "info", "--concurrency", "200", "-P", "gevent"]

# Stage 6: Celery beat (no Playwright or Node.js needed)
FROM base AS celerybeat

CMD ["celery", "--app", "config.celery", "beat", "--loglevel", "info", "--scheduler", "django_celery_beat.schedulers:DatabaseScheduler"]

# Stage 7: Flower (no Playwright or Node.js needed)
FROM base AS flower

# Create data directory for Flower
RUN mkdir -p /data

# Expose Flower port
EXPOSE 5555

CMD if [ -n "$FLOWER_BASIC_AUTH" ]; then \
        celery --app=config.celery flower \
            --loglevel=info \
            --persistent=true \
            --db=/data/flower.db \
            --basic_auth="$FLOWER_BASIC_AUTH" \
            --port=5555; \
    else \
        celery --app=config.celery flower \
            --loglevel=info \
            --persistent=true \
            --db=/data/flower.db \
            --port=5555; \
    fi