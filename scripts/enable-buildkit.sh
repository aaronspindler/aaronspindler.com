#!/bin/bash
# Docker BuildKit information and status check
# BuildKit is enabled by default in modern Docker (20.10+) and GitHub Actions
# This script just verifies your setup

set -e

echo "🚀 Docker BuildKit Status"
echo ""

# Check Docker version
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker first."
    exit 1
fi

DOCKER_VERSION=$(docker --version | grep -oE '[0-9]+\.[0-9]+' | head -1)
echo "✓ Docker version: $DOCKER_VERSION"

# Check if BuildKit is enabled
if [ "${DOCKER_BUILDKIT:-0}" = "1" ]; then
    echo "✓ BuildKit is enabled in this session"
elif command -v docker buildx version &> /dev/null; then
    echo "✓ BuildKit available via docker buildx"
else
    echo "○ BuildKit not explicitly enabled"
fi

echo ""
echo "ℹ️  BuildKit Status:"
echo ""
echo "  • BuildKit is enabled by default in Docker 20.10+ and GitHub Actions"
echo "  • Your Dockerfile already uses BuildKit features (cache mounts)"
echo "  • No additional setup needed for CI/CD"
echo ""
echo "  Performance with current Dockerfile:"
echo "    - First build: ~2-3 minutes (Playwright base image)"
echo "    - Code changes: ~30-60 seconds (cache mounts)"
echo "    - Dependencies: ~1-2 minutes (cache mounts)"
echo ""

# Check if user wants to enable explicitly (optional)
echo "Optional: Enable BuildKit explicitly for local builds"
echo ""
read -p "Enable BuildKit environment variables? (y/N) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Detect shell
    if [ -n "$BASH_VERSION" ]; then
        SHELL_RC="$HOME/.bashrc"
    elif [ -n "$ZSH_VERSION" ]; then
        SHELL_RC="$HOME/.zshrc"
    else
        SHELL_RC="$HOME/.profile"
    fi

    if ! grep -q "DOCKER_BUILDKIT" "$SHELL_RC" 2>/dev/null; then
        echo "export DOCKER_BUILDKIT=1" >> "$SHELL_RC"
        echo "export COMPOSE_DOCKER_CLI_BUILD=1" >> "$SHELL_RC"
        echo "✅ BuildKit enabled in $SHELL_RC"
        echo "   Run: source $SHELL_RC (or restart your terminal)"
    else
        echo "✓ BuildKit already configured in $SHELL_RC"
    fi

    export DOCKER_BUILDKIT=1
    export COMPOSE_DOCKER_CLI_BUILD=1
    echo "✓ BuildKit enabled for this session"
else
    echo "Skipped. BuildKit will still work in most cases."
fi

echo ""
echo "Build the image:"
echo "  docker build -t aaronspindler.com ."
echo ""
echo "See DOCKER_BUILD_OPTIMIZATION.md for details"
