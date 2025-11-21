#!/bin/bash
# Validate .env file has all required variables

REQUIRED_VARS=(
    "DATABASE_URL"
    "REDIS_URL"
    "SECRET_KEY"
    "AWS_ACCESS_KEY_ID"
    "AWS_SECRET_ACCESS_KEY"
    "AWS_STORAGE_BUCKET_NAME"
)

if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    echo ""
    echo "Copy .env.example to .env and fill in your values:"
    echo "  cp .env.example .env"
    echo ""
    exit 1
fi

echo "Validating environment variables..."
echo ""

missing=0
for var in "${REQUIRED_VARS[@]}"; do
    if ! grep -q "^${var}=" .env; then
        echo "❌ Missing required variable: $var"
        missing=$((missing + 1))
    else
        echo "✅ Found: $var"
    fi
done

echo ""

if [ $missing -gt 0 ]; then
    echo "Please add $missing missing variable(s) to .env"
    exit 1
else
    echo "✅ All required environment variables present"
    echo ""
    echo "⚠️  Remember: Local development connects to PRODUCTION database"
    echo "   Use 'make test' to run tests in Docker"
fi
