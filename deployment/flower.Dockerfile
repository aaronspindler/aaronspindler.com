FROM python:3.14.0-slim-bookworm

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

# Install Python dependencies
COPY requirements/base.txt /tmp/requirements.txt
RUN pip install --upgrade pip && \
    pip install -r /tmp/requirements.txt && \
    rm -rf /root/.cache/

# Copy project
COPY . /code/

# Expose Flower port
EXPOSE 5555

# Run Flower with basic authentication if provided
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
