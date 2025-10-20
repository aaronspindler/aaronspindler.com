#!/bin/bash
set -e

# Initialize TimescaleDB extension
# This script runs when the PostgreSQL container is first created

echo "🚀 Initializing TimescaleDB extension..."

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Enable TimescaleDB extension
    CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

    -- Enable other useful extensions for financial data
    CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- Trigram for text search
    CREATE EXTENSION IF NOT EXISTS btree_gin;  -- GIN indexes for btree
    CREATE EXTENSION IF NOT EXISTS btree_gist;  -- GIST indexes for btree

    -- Grant privileges
    GRANT ALL PRIVILEGES ON DATABASE $POSTGRES_DB TO $POSTGRES_USER;

    -- Show installed extensions
    SELECT extname, extversion FROM pg_extension WHERE extname LIKE 'timescaledb%' OR extname IN ('pg_trgm', 'btree_gin', 'btree_gist');
EOSQL

echo "✅ TimescaleDB and extensions enabled successfully!"
