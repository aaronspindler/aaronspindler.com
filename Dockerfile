# Pull base image
FROM python:3.13.7-slim-bookworm

# Set Python environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Create and set work directory called `app`
RUN mkdir -p /code
WORKDIR /code

# Install minimal system dependencies first
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt /tmp/requirements.txt

RUN set -ex && \
    pip install --upgrade pip && \
    pip install -r /tmp/requirements.txt && \
    rm -rf /root/.cache/

# Install Playwright dependencies and chromium browser
# This command automatically installs all necessary system dependencies for chromium
RUN playwright install --with-deps chromium

# Copy local project
COPY . /code/

# Expose port 80
EXPOSE 80

# Add healthcheck for zero downtime deployments
# This checks if the Django application is responding properly
# The start-period gives the container 40 seconds to start up before health checks begin
HEALTHCHECK --interval=30s --timeout=30s --start-period=40s --retries=3 \
    CMD curl -f http://127.0.0.1:80/ || exit 1

RUN python manage.py collectstatic_optimize
RUN python manage.py migrate --no-input

# Generate knowledge graph screenshot for caching (optional)
# This attempts to pre-generate the screenshot during build, but if it fails,
# the screenshot will be generated on first request at runtime instead
RUN ./generate_screenshot.sh || echo "INFO: Screenshot pre-generation skipped, will generate on first request"

# Use gunicorn on port 80
CMD ["gunicorn", "--bind", ":80", "--workers", "8", "config.wsgi", "--log-level", "info", "--access-logfile", "-", "--error-logfile", "-"]
