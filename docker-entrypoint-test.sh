#!/bin/bash
set -e

echo "Starting test container initialization..."

# Function to wait for a service
wait_for_service() {
    local host=$1
    local port=$2
    local service_name=$3

    echo "Waiting for $service_name to be ready..."
    while ! nc -z "$host" "$port" 2>/dev/null; do
        echo "  $service_name is not ready yet. Retrying in 2 seconds..."
        sleep 2
    done
    echo "  $service_name is ready!"
}

# Wait for required services
wait_for_service "postgres" "5432" "PostgreSQL"
wait_for_service "redis" "6379" "Redis"

# Give services a moment to fully initialize
sleep 1

# Run database migrations
echo "Running database migrations..."
python manage.py migrate --no-input --settings=config.settings_test || {
    echo "Warning: Migrations failed, but continuing..."
}

# Create test database if needed
echo "Preparing test database..."
python manage.py migrate --run-syncdb --no-input --settings=config.settings_test || {
    echo "  Test database preparation completed or already exists"
}

# Build CSS files (optional for tests, but ensures consistency)
echo "Building CSS files..."
python manage.py build_css --settings=config.settings_test 2>/dev/null || {
    echo "  CSS build skipped (not critical for tests)"
}

# Collect static files (uses FileSystemStorage in tests)
if [ "$COLLECT_STATIC" = "true" ]; then
    echo "Collecting static files..."
    python manage.py collectstatic --no-input --settings=config.settings_test || {
        echo "  Static file collection skipped or failed (not critical for tests)"
    }
fi

echo "Test container initialization complete!"

# Execute the main command
exec "$@"
