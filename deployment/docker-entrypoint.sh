#!/bin/bash
set -e

echo "Starting web container initialization..."

# Run migrations
echo "Running database migrations..."
python manage.py migrate --no-input || {
    echo "Warning: Migrations failed, but continuing..."
}

# Build CSS files
echo "Building combined CSS..."
python manage.py build_css || {
    echo "Warning: CSS build failed, but continuing..."
}

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --no-input || {
    echo "Warning: Static file collection failed, but continuing..."
}

echo "Web container initialization complete!"

# Execute the main command
exec "$@"
