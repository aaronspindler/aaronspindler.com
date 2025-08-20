#!/bin/bash
set -e

echo "Starting temporary Django server for screenshot generation..."

# Start Django development server in the background
python manage.py runserver 127.0.0.1:8000 &
SERVER_PID=$!

# Function to cleanup on exit
cleanup() {
    echo "Stopping Django server..."
    kill $SERVER_PID 2>/dev/null || true
    wait $SERVER_PID 2>/dev/null || true
}
trap cleanup EXIT

# Wait for server to be ready (max 30 seconds)
echo "Waiting for Django server to be ready..."
for i in {1..30}; do
    if curl -s http://127.0.0.1:8000/ > /dev/null 2>&1; then
        echo "Django server is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "ERROR: Django server failed to start in 30 seconds"
        exit 1
    fi
    sleep 1
done

# Generate the screenshot
echo "Generating knowledge graph screenshot..."
python manage.py generate_knowledge_graph_screenshot

echo "Screenshot generation complete!"
