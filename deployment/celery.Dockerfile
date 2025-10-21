# syntax=docker/dockerfile:1.4
# Celery worker Dockerfile - Optimized with pyppeteer for screenshot generation

FROM python:3.14-slim

# Set Python environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Path to Chromium for Lighthouse
    CHROME_PATH=/usr/bin/chromium \
    # Pyppeteer configuration
    PYPPETEER_CHROMIUM_REVISION=1056772 \
    PYPPETEER_HOME=/opt/pyppeteer

# Create and set work directory
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
    # Chromium and dependencies for screenshot generation
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
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list \
    && apt-get update && apt-get install -y --no-install-recommends nodejs \
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
COPY package*.json ./

# Install NPM dependencies (including @lhci/cli for Lighthouse audits) with cache mount
RUN --mount=type=cache,target=/root/.npm \
    npm ci --prefer-offline --no-audit

# Copy project
COPY . /code/

# Run Celery worker with gevent pool for better concurrency
CMD ["celery", "--app", "config.celery", "worker", "--loglevel", "info", "--concurrency", "200", "-P", "gevent"]
