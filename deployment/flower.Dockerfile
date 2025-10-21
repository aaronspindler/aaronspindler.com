FROM python:3.14-slim

# Set Python environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create and set work directory
RUN mkdir -p /code /data
WORKDIR /code

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    curl \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency installation
RUN pip install --upgrade pip uv

# Install Python dependencies with uv lockfile
COPY requirements/base.txt /tmp/requirements.txt
RUN uv pip install --system --no-cache -r /tmp/requirements.txt

# Copy project
COPY . /code/

# Expose Flower port
EXPOSE 5555

# Run Flower with basic authentication if provided
# Configuration options:
#   --persistent=true: Save state across restarts
#   --db: Database file for persistence
#   --max_tasks: Maximum number of tasks to keep in memory (default: 10000)
#   --loglevel: Logging level
#   --state_save_interval: How often to save state (ms, default: 5000)
CMD if [ -n "$FLOWER_BASIC_AUTH" ]; then \
        celery --app=config.celery flower \
            --loglevel=info \
            --persistent=true \
            --db=/data/flower.db \
            --max_tasks=50000 \
            --state_save_interval=10000 \
            --basic_auth="$FLOWER_BASIC_AUTH" \
            --port=5555; \
    else \
        celery --app=config.celery flower \
            --loglevel=info \
            --persistent=true \
            --db=/data/flower.db \
            --max_tasks=50000 \
            --state_save_interval=10000 \
            --port=5555; \
    fi
