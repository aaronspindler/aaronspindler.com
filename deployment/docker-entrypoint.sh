#!/bin/bash
set -e

echo "Starting web container initialization..."

# Run migrations
echo "Running database migrations..."
python manage.py migrate --no-input || {
    echo "Warning: Migrations failed, but continuing..."
}

# CSS is built during Docker image build with templates available
# Collect static files (includes the pre-built CSS)
echo "Collecting static files..."
python manage.py collectstatic_optimize --no-input || {
    echo "Warning: Static file collection failed, but continuing..."
}

echo "Web container initialization complete!"

# Execute the main command
exec "$@"
