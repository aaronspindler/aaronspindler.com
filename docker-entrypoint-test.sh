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
wait_for_service "localstack" "4566" "LocalStack"

# Give services a moment to fully initialize
sleep 2

# Create S3 bucket in LocalStack
echo "Setting up LocalStack S3 bucket..."
aws --endpoint-url=http://localstack:4566 s3 mb s3://test-bucket 2>/dev/null || {
    echo "  Bucket already exists or creation failed (may be okay)"
}

# Set CORS configuration for the bucket
echo "Setting CORS configuration for S3 bucket..."
if [ -f "/code/test-cors.json" ]; then
    aws --endpoint-url=http://localstack:4566 s3api put-bucket-cors \
        --bucket test-bucket \
        --cors-configuration file:///code/test-cors.json 2>/dev/null || {
        echo "  CORS configuration failed (may be okay)"
    }
fi

# Set bucket ACL to public-read
echo "Setting bucket ACL..."
aws --endpoint-url=http://localstack:4566 s3api put-bucket-acl \
    --bucket test-bucket \
    --acl public-read 2>/dev/null || {
    echo "  Bucket ACL setting failed (may be okay)"
}

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

# Collect static files to S3 (LocalStack)
if [ "$COLLECT_STATIC" = "true" ]; then
    echo "Collecting static files to LocalStack S3..."
    python manage.py collectstatic --no-input --settings=config.settings_test || {
        echo "  Static file collection skipped or failed (not critical for tests)"
    }
fi

echo "Test container initialization complete!"

# Execute the main command
exec "$@"
