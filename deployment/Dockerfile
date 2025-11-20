# syntax=docker/dockerfile:1.4
# Optimized for CI/CD with lightweight pyppeteer for screenshot generation
#
# Uses Python slim base image with minimal Chromium installation
# BuildKit cache mounts for pip, npm, and apt packages
#
# Build args:
#   - SKIP_JS_BUILD=1: Skip JavaScript build for test environments (saves ~10-20s)
#
# Performance:
#   - Image size: ~800MB optimized for production
#   - First build: ~2-3 minutes
#   - Rebuild with code changes: ~30-60 seconds
#   - Rebuild with dependencies: ~1-2 minutes
#   - Test build (SKIP_JS_BUILD=1): ~20-40s faster

FROM python:3.13-slim

# Set Python environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Path to Chromium for Lighthouse
    CHROME_PATH=/usr/bin/chromium \
    # Pyppeteer configuration
    PYPPETEER_CHROMIUM_REVISION=1056772 \
    PYPPETEER_HOME=/opt/pyppeteer

WORKDIR /code

# Install system dependencies including Chromium and Node.js
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    # Build essentials
    curl \
    ca-certificates \
    gnupg \
    # PostgreSQL client library
    libpq5 \
    # Chromium and dependencies
    chromium \
    chromium-driver \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libx11-6 \
    libxcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    # Node.js and npm from Debian repositories (more reliable than NodeSource)
    nodejs \
    npm \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create pyppeteer directory for Chromium download
RUN mkdir -p $PYPPETEER_HOME && chmod -R 755 $PYPPETEER_HOME

# Install uv for fast dependency installation
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip uv

# Copy only requirements lockfile first (changes less frequently)
COPY requirements/base.txt requirements.txt

# Install Python dependencies with uv (10-100x faster than pip)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system --no-cache -r requirements.txt

# Pre-download Chromium for pyppeteer
RUN python -c "from pyppeteer import chromium_downloader; chromium_downloader.download_chromium()"

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
COPY omas/static/ ./omas/static/

# Build and optimize JavaScript files (skip during test builds with --build-arg SKIP_JS_BUILD=1)
ARG SKIP_JS_BUILD=0
RUN if [ "$SKIP_JS_BUILD" = "0" ]; then npm run build:js; else echo "Skipping JS build for tests"; fi

# Copy rest of application code (changes most frequently - keep last!)
COPY . /code/

# Build CSS with all templates now available
# PurgeCSS will scan all templates to determine which CSS to keep
RUN python manage.py build_css

# Collect static files and create WhiteNoise manifest
# Must run during build (not entrypoint) for CompressedManifestStaticFilesStorage
RUN python manage.py collectstatic_optimize --no-input

# Expose port 80
EXPOSE 80

# Health check for zero-downtime deployments
# CapRover will wait for new container to pass health check before routing traffic
# HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
#     CMD curl -f http://127.0.0.1:80/health/ || exit 1

# Use entrypoint script to handle initialization
ENTRYPOINT ["/docker-entrypoint.sh"]

# Default command
CMD ["gunicorn", "--bind", ":80", "--workers", "8", "config.wsgi", "--log-level", "info", "--access-logfile", "-", "--error-logfile", "-"]
