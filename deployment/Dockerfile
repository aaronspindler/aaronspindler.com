# syntax=docker/dockerfile:1.4
# Optimized for CI/CD with fastest possible build times
#
# Uses Microsoft's Playwright Python image (includes Python + Playwright + Chromium)
# BuildKit cache mounts for pip, npm, and apt packages
#
# Performance:
#   - First build: ~2-3 minutes (vs 8 minutes with slim base)
#   - Rebuild with code changes: ~30-60 seconds
#   - Rebuild with dependencies: ~1-2 minutes
#
# Trade-off: Larger base image (~1.5GB) but optimized for CI/CD speed
# See DOCKER_BUILD_OPTIMIZATION.md for details

FROM mcr.microsoft.com/playwright/python:v1.55.0-noble

# Set Python environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /code

# Install Node.js and npm (not included in Playwright image)
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    nodejs \
    npm

# Copy only requirements file first (changes less frequently)
COPY requirements/base.txt requirements.txt

# Install Python dependencies with pip cache mount
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy package files for NPM (changes less frequently than app code)
COPY package*.json .config/postcss.config.js .config/purgecss.config.js ./

# Install NPM dependencies with cache mount
RUN --mount=type=cache,target=/root/.npm \
    npm ci --prefer-offline --no-audit

# Copy entrypoint script (changes rarely)
COPY deployment/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Copy static files and build configuration (needed for JS build)
COPY static/ ./static/
COPY scripts/ ./scripts/

# Build and optimize JavaScript files
RUN npm run build:js

# Copy rest of application code (changes most frequently - keep last!)
COPY . /code/

# Expose port 80
EXPOSE 80

# Use entrypoint script to handle initialization
ENTRYPOINT ["/docker-entrypoint.sh"]

# Default command
CMD ["gunicorn", "--bind", ":80", "--workers", "8", "config.wsgi", "--log-level", "info", "--access-logfile", "-", "--error-logfile", "-"]
