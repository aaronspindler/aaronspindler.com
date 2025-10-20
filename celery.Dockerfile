FROM mcr.microsoft.com/playwright/python:v1.55.0-noble

# Set Python environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create and set work directory
WORKDIR /code

# Install Node.js 20.x from NodeSource (required for Lighthouse @lhci/cli compatibility)
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    gnupg \
    libpq5 && \
    mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg && \
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list && \
    apt-get update && apt-get install -y --no-install-recommends nodejs

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
