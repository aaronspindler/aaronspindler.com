# Multi-stage build for smaller final image
# Stage 1: Build dependencies
FROM python:3.13.7-slim-bookworm as builder

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

# Stage 2: Playwright installation (separate for caching)
FROM python:3.13.7-slim-bookworm as playwright-installer

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Playwright and its dependencies
RUN playwright install --with-deps chromium

# Stage 3: Final runtime image
FROM python:3.13.7-slim-bookworm

# Set Python environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Install runtime dependencies and Node.js for CSS minification
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy Playwright installation from playwright stage
COPY --from=playwright-installer /root/.cache/ms-playwright /root/.cache/ms-playwright
COPY --from=playwright-installer /usr/lib /usr/lib
COPY --from=playwright-installer /usr/bin /usr/bin

# Create and set work directory
WORKDIR /code

# Copy entrypoint script first (rarely changes)
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Copy package files for NPM installation
COPY package*.json postcss.config.js purgecss.config.js ./

# Install NPM dependencies for CSS and JS build pipeline (including dev dependencies needed for build)
RUN npm ci || npm install

# Copy application code last (changes frequently)
COPY . /code/

# Build and optimize JavaScript files
RUN npm run build:js

# Expose port 80
EXPOSE 80

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -fL http://127.0.0.1:80/health || exit 1

# Use entrypoint script to handle initialization
ENTRYPOINT ["/docker-entrypoint.sh"]

# Default command
CMD ["gunicorn", "--bind", ":80", "--workers", "2", "config.wsgi", "--log-level", "info", "--access-logfile", "-", "--error-logfile", "-"]