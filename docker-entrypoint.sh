#!/bin/bash
set -e

echo "Starting container initialization..."

# Wait for database to be ready (optional, but recommended)
if [ -n "$DATABASE_URL" ]; then
    echo "Waiting for database..."
    python << END
import sys
import time
import psycopg
from urllib.parse import urlparse

url = urlparse("$DATABASE_URL")
max_retries = 30
retry_count = 0

while retry_count < max_retries:
    try:
        conn = psycopg.connect(
            host=url.hostname,
            port=url.port or 5432,
            dbname=url.path[1:],
            user=url.username,
            password=url.password
        )
        conn.close()
        print("Database is ready!")
        break
    except Exception as e:
        retry_count += 1
        print(f"Database not ready yet... ({retry_count}/{max_retries})")
        time.sleep(2)
else:
    print("Database connection timeout. Proceeding anyway...")
END
fi

# Run migrations only if this is the web service (not celery workers)
if [ "$RUN_MIGRATIONS" = "true" ]; then
    echo "Running database migrations..."
    python manage.py migrate --no-input || {
        echo "Warning: Migrations failed, but continuing..."
    }
fi

# Collect static files only for web service
if [ "$COLLECT_STATIC" = "true" ]; then
    echo "Collecting static files..."
    python manage.py collectstatic_optimize --no-input || {
        echo "Warning: Static file collection failed, but continuing..."
    }
fi

# Run any custom initialization commands
if [ -n "$INIT_COMMANDS" ]; then
    echo "Running custom initialization commands..."
    eval "$INIT_COMMANDS"
fi

echo "Container initialization complete!"

# Execute the main command
exec "$@"