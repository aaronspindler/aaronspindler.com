#!/bin/bash
set -e

echo "Starting web container initialization..."

# Run migrations
echo "Running database migrations..."
python manage.py migrate --no-input || {
    echo "Warning: Migrations failed, but continuing..."
}

# Static files were collected during Docker image build
# Verify manifest file exists and is valid
echo "Verifying static files manifest..."
STATIC_ROOT=$(python -c "from django.conf import settings; print(settings.STATIC_ROOT)")
MANIFEST_PATH="${STATIC_ROOT}/staticfiles.json"

if [ ! -f "$MANIFEST_PATH" ]; then
    echo "ERROR: Manifest file not found at ${MANIFEST_PATH}"
    echo "Static file collection failed during Docker build."
    exit 1
fi

# Verify manifest is valid JSON
if ! python -c "import json; json.load(open('${MANIFEST_PATH}'))" 2>/dev/null; then
    echo "ERROR: Manifest file at ${MANIFEST_PATH} is not valid JSON"
    exit 1
fi

# Verify critical file exists in manifest
if ! python -c "import json, sys; manifest = json.load(open('${MANIFEST_PATH}')); sys.exit(0 if 'images/spindlers/logo.png' in manifest.get('paths', {}) else 1)" 2>/dev/null; then
    echo "ERROR: images/spindlers/logo.png not found in manifest"
    echo "Static file collection failed - critical files missing"
    exit 1
fi

echo "Static files manifest verified successfully!"

echo "Web container initialization complete!"

# Execute the main command
exec "$@"
