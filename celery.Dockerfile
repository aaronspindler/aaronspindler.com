FROM mcr.microsoft.com/playwright/python:v1.48.0-noble

# Set Python environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create and set work directory
WORKDIR /code

# Install Node.js and npm (not included in Playwright image)
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    nodejs \
    npm \
    libpq5

# Copy only requirements file first (changes less frequently)
COPY requirements.txt .

# Install Python dependencies with pip cache mount
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy package files for NPM (changes less frequently than app code)
COPY package*.json ./

# Install NPM dependencies (including @lhci/cli for Lighthouse audits) with cache mount
RUN --mount=type=cache,target=/root/.npm \
    npm ci --prefer-offline --no-audit

# Copy project
COPY . /code/

# Run Celery worker with gevent pool for better concurrency
CMD ["celery", "--app", "config.celery", "worker", "--loglevel", "info", "--concurrency", "200", "-P", "gevent"]
