#!/bin/bash
# Test database connectivity without making changes

set -e

# Load environment
if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    exit 1
fi

export $(grep -v '^#' .env | grep DATABASE_URL | xargs)

DB_INFO=$(python3 << 'PYTHON_SCRIPT'
import os
from urllib.parse import urlparse
url = urlparse(os.environ['DATABASE_URL'])
print(f"{url.username}|{url.password}|{url.hostname}|{url.port or 5432}|{url.path.lstrip('/')}")
PYTHON_SCRIPT
)

IFS='|' read -r DB_USER DB_PASSWORD DB_HOST DB_PORT DB_NAME <<< "$DB_INFO"

export PGPASSWORD="$DB_PASSWORD"

echo "Testing connection to:"
echo "  Host: $DB_HOST:$DB_PORT"
echo "  Database: $DB_NAME"
echo "  User: $DB_USER"
echo ""

if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT version();" > /dev/null 2>&1; then
    echo "✅ Database connection successful!"
    echo ""
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT version();"
    echo ""
    echo "⚠️  This is the PRODUCTION database - be careful!"
else
    echo "❌ Database connection failed!"
    exit 1
fi

unset PGPASSWORD
