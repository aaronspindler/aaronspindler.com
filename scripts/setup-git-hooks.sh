#!/bin/bash

# Setup Git hooks for the project using pre-commit
# Run this script after cloning the repository: ./scripts/setup-git-hooks.sh

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}Setting up Git hooks with pre-commit...${NC}"
echo ""

# Get the project root directory
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
cd "$PROJECT_ROOT"

# Check if pre-commit is installed
if ! command -v pre-commit &> /dev/null; then
    echo -e "${YELLOW}⚠️  pre-commit not found, installing...${NC}"

    # Check if we're in a virtual environment
    if [ -d "venv" ]; then
        source venv/bin/activate
        pip install pre-commit
    elif [ -d ".venv" ]; then
        source .venv/bin/activate
        pip install pre-commit
    else
        echo -e "${RED}✗ No virtual environment found!${NC}"
        echo "Please create and activate a virtual environment first:"
        echo "  python -m venv venv"
        echo "  source venv/bin/activate"
        echo "  pip install pre-commit"
        exit 1
    fi
fi

# Install pre-commit hooks
echo -e "${BLUE}Installing pre-commit hooks...${NC}"
pre-commit install

echo ""
echo -e "${GREEN}✓ Pre-commit hooks installed${NC}"
echo ""
echo -e "${BLUE}What runs on commit:${NC}"
echo "  • Ruff linter (auto-fix)"
echo "  • Ruff formatter (Black-compatible)"
echo "  • Ruff import sorting"
echo "  • File checks (whitespace, end-of-file, YAML)"
echo ""
echo -e "${BLUE}Useful commands:${NC}"
echo "  • Run all hooks manually: ${GREEN}pre-commit run --all-files${NC}"
echo "  • Run specific hook: ${GREEN}pre-commit run ruff${NC}"
echo "  • Update hooks: ${GREEN}pre-commit autoupdate${NC}"
echo "  • Skip hooks: ${GREEN}git commit --no-verify${NC}"
echo ""
echo -e "${GREEN}✅ Git hooks setup complete!${NC}"
echo ""
echo "Note: Heavier checks (MyPy, Django) only run in CI/CD to keep commits fast."
