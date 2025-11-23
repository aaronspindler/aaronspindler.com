#!/bin/bash
set -e

echo "Starting Celery container..."

echo "Celery container initialization complete!"

# Execute the main command
exec "$@"
