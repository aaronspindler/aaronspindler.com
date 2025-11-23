#!/bin/bash
set -e

echo "Starting Celery container..."

# Celery doesn't need migrations or collectstatic
# Just wait for database to be ready if needed
if [ -n "$DATABASE_URL" ]; then
    echo "Waiting for database..."
    python -c "
import sys
import psycopg2
import os
from urllib.parse import urlparse
import time

url = urlparse(os.environ['DATABASE_URL'])
max_retries = 30
for i in range(max_retries):
    try:
        conn = psycopg2.connect(
            host=url.hostname,
            port=url.port or 5432,
            user=url.username,
            password=url.password,
            database=url.path[1:],
            connect_timeout=3
        )
        conn.close()
        print('Database is ready!')
        sys.exit(0)
    except psycopg2.OperationalError:
        if i < max_retries - 1:
            time.sleep(2)
        else:
            print('Database not ready after 60 seconds')
            sys.exit(1)
" || echo "Database check skipped"
fi

echo "Celery container initialization complete!"

# Execute the main command
exec "$@"
