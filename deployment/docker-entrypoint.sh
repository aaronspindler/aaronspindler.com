#!/bin/bash
set -e

echo "Starting web container initialization..."

# Run migrations
echo "Running database migrations..."
python manage.py migrate --no-input || {
    echo "Warning: Migrations failed, but continuing..."
}

# Run collectstatic
echo "Running collectstatic..."
python manage.py collectstatic --no-input


echo "Web container initialization complete!"

# Execute the main command
exec "$@"
