#!/bin/bash

echo "=== Starting Knowledge Graph Screenshot Generation ==="

# Don't exit on error immediately, we want to handle errors gracefully
set +e

# Check if we're in Docker or local environment
if [ -f /.dockerenv ]; then
    echo "Running in Docker container"
    IS_DOCKER=true
else
    echo "Running in local environment"
    IS_DOCKER=false
fi

echo "Starting temporary Django server for screenshot generation..."

# Set environment variables for local development
export DJANGO_SETTINGS_MODULE=config.settings
export DEBUG=True

# Start Django development server in the background with more verbose output
echo "Starting server on localhost:8000..."
python manage.py runserver localhost:8000 --noreload --insecure > /tmp/django_server.log 2>&1 &
SERVER_PID=$!

# Function to cleanup on exit
cleanup() {
    echo "Cleaning up..."
    if [ -n "$SERVER_PID" ]; then
        echo "Stopping Django server (PID: $SERVER_PID)..."
        kill $SERVER_PID 2>/dev/null || true
        wait $SERVER_PID 2>/dev/null || true
    fi
    
    # Show server logs for debugging
    if [ -f /tmp/django_server.log ]; then
        echo "=== Django Server Logs ==="
        tail -50 /tmp/django_server.log
        echo "=========================="
    fi
}
trap cleanup EXIT

# Check if server process started
sleep 2
if ! kill -0 $SERVER_PID 2>/dev/null; then
    echo "ERROR: Django server process failed to start"
    exit 1
fi

echo "Server process started with PID: $SERVER_PID"

# Wait for server to be ready (max 60 seconds)
echo "Waiting for Django server to be ready..."
MAX_ATTEMPTS=60
for i in $(seq 1 $MAX_ATTEMPTS); do
    # Try to connect to the server
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/ | grep -q "200\|301\|302"; then
        echo "Django server is ready! (attempt $i/$MAX_ATTEMPTS)"
        
        # Give it a bit more time to fully initialize
        echo "Waiting 5 more seconds for full initialization..."
        sleep 5
        break
    fi
    
    if [ $i -eq $MAX_ATTEMPTS ]; then
        echo "ERROR: Django server failed to become ready in $MAX_ATTEMPTS seconds"
        echo "Checking server process..."
        ps aux | grep -v grep | grep "runserver" || echo "Server process not found"
        
        echo "Checking if port 8000 is listening..."
        netstat -tuln | grep :8000 || echo "Port 8000 not listening"
        
        echo "Last 20 lines of server log:"
        tail -20 /tmp/django_server.log
        
        exit 1
    fi
    
    # Show progress every 10 attempts
    if [ $((i % 10)) -eq 0 ]; then
        echo "Still waiting... (attempt $i/$MAX_ATTEMPTS)"
    fi
    
    sleep 1
done

# Verify the server is actually responding
echo "Verifying server is responding correctly..."
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/)
echo "Server returned HTTP status: $HTTP_STATUS"

if [ "$HTTP_STATUS" != "200" ] && [ "$HTTP_STATUS" != "301" ] && [ "$HTTP_STATUS" != "302" ]; then
    echo "WARNING: Server returned unexpected status code: $HTTP_STATUS"
fi

# Generate the screenshot
echo "Generating knowledge graph screenshot..."
python manage.py generate_knowledge_graph_screenshot --wait-time 10000 || {
    EXIT_CODE=$?
    echo "WARNING: Screenshot generation failed with exit code $EXIT_CODE"
    echo "This is non-fatal, continuing build..."
    # Don't exit with error, just warn
}

echo "=== Screenshot generation process complete ===""
