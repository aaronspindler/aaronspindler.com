#!/bin/bash
#
# Database backup script for aaronspindler.com
#
# Usage: ./scripts/backup_database.sh [output_file]
#
# This script:
# 1. Reads DATABASE_URL from .env file
# 2. Extracts connection parameters
# 3. Creates a timestamped backup using pg_dump
# 4. Optionally compresses the backup with gzip
#

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Change to project root
cd "$PROJECT_ROOT"

echo -e "${BLUE}=== Database Backup Script ===${NC}"

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${RED}Error: .env file not found in project root${NC}"
    echo "Please ensure .env file exists with DATABASE_URL configured"
    exit 1
fi

# Load DATABASE_URL from .env
export $(grep -v '^#' .env | grep DATABASE_URL | xargs)

if [ -z "$DATABASE_URL" ]; then
    echo -e "${RED}Error: DATABASE_URL not found in .env file${NC}"
    exit 1
fi

echo -e "${GREEN}✓ DATABASE_URL loaded from .env${NC}"

# Parse DATABASE_URL using Python (more reliable than bash regex)
DB_INFO=$(python3 << 'PYTHON_SCRIPT'
import os
import sys
from urllib.parse import urlparse

try:
    url = urlparse(os.environ['DATABASE_URL'])

    # Extract components
    scheme = url.scheme
    user = url.username or 'postgres'
    password = url.password or ''
    host = url.hostname or 'localhost'
    port = url.port or 5432
    database = url.path.lstrip('/') or 'postgres'

    # Print in format: user|password|host|port|database
    print(f"{user}|{password}|{host}|{port}|{database}")
except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
PYTHON_SCRIPT
)

# Check if parsing succeeded
if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Failed to parse DATABASE_URL${NC}"
    exit 1
fi

# Split the parsed info
IFS='|' read -r DB_USER DB_PASSWORD DB_HOST DB_PORT DB_NAME <<< "$DB_INFO"

echo -e "${GREEN}✓ Connection details parsed:${NC}"
echo -e "  Host:     ${DB_HOST}:${DB_PORT}"
echo -e "  Database: ${DB_NAME}"
echo -e "  User:     ${DB_USER}"

# Generate backup filename
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="${PROJECT_ROOT}/backups"
DEFAULT_BACKUP_FILE="${BACKUP_DIR}/backup_${DB_NAME}_${TIMESTAMP}.sql"

# Use provided filename or default
BACKUP_FILE="${1:-$DEFAULT_BACKUP_FILE}"

# Create backups directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

echo -e "${BLUE}Starting backup...${NC}"
echo -e "  Output: ${BACKUP_FILE}"

# Set PGPASSWORD environment variable for pg_dump
export PGPASSWORD="$DB_PASSWORD"

# Run pg_dump
if pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --verbose \
    --no-owner \
    --no-acl \
    -f "$BACKUP_FILE" 2>&1 | grep -E "processing|completed|dumping"; then

    # Get file size
    FILE_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)

    echo -e "${GREEN}✅ Backup completed successfully!${NC}"
    echo -e "  File: ${BACKUP_FILE}"
    echo -e "  Size: ${FILE_SIZE}"

    # Offer to compress
    echo -e "${YELLOW}Compress backup with gzip? (saves ~70% space)${NC}"
    read -p "Compress? [y/N]: " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}Compressing...${NC}"
        gzip "$BACKUP_FILE"
        COMPRESSED_SIZE=$(du -h "${BACKUP_FILE}.gz" | cut -f1)
        echo -e "${GREEN}✅ Compressed: ${BACKUP_FILE}.gz (${COMPRESSED_SIZE})${NC}"
    fi

    echo -e "${GREEN}🎉 Backup complete!${NC}"

    # Show how to restore
    echo ""
    echo -e "${BLUE}To restore this backup later:${NC}"
    if [ -f "${BACKUP_FILE}.gz" ]; then
        echo -e "  gunzip ${BACKUP_FILE}.gz"
        echo -e "  psql -h \$DB_HOST -p \$DB_PORT -U \$DB_USER -d \$DB_NAME -f ${BACKUP_FILE}"
    else
        echo -e "  psql -h \$DB_HOST -p \$DB_PORT -U \$DB_USER -d \$DB_NAME -f ${BACKUP_FILE}"
    fi

else
    echo -e "${RED}❌ Backup failed!${NC}"
    exit 1
fi

# Unset password
unset PGPASSWORD
