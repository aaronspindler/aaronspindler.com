# QuestDB Setup Guide

Complete guide for setting up and using QuestDB with the FeeFiFoFunds application.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Setup Instructions](#setup-instructions)
- [Schema Management](#schema-management)
- [Common Operations](#common-operations)
- [Querying Data](#querying-data)
- [Troubleshooting](#troubleshooting)

---

## Overview

QuestDB is a high-performance time-series database optimized for financial data. The FeeFiFoFunds application uses a hybrid database approach:

- **PostgreSQL (default database)**: Asset model (relational data)
- **QuestDB (questdb database)**: AssetPrice model (time-series data)

### Why QuestDB?

- **10-100x faster** queries for time-series data
- **Better compression** (2-5x vs PostgreSQL)
- **Lower resource usage** (512MB+ vs 2GB+ for TimescaleDB)
- **Built for financial data** with `SAMPLE BY` for OHLCV aggregations
- **Simple operations** - easier than TimescaleDB

---

## Architecture

### Database Routing

Django's database router (`config/db_routers.py`) automatically routes models to the correct database:

```python
# Routes to PostgreSQL (default)
Asset.objects.all()  # → default database

# Routes to QuestDB
AssetPrice.objects.all()  # → questdb database
```

### Model Configuration

**Asset Model (PostgreSQL)**:
- Managed by Django (`managed=True`)
- Uses Django migrations
- Has ForeignKey relationships

**AssetPrice Model (QuestDB)**:
- Not managed by Django (`managed=False`)
- Schema created manually via `setup_questdb_schema` command
- Uses `asset_id` integer field instead of ForeignKey
- Includes `@property` method to lazy-load asset from PostgreSQL

---

## Setup Instructions

### 1. CapRover Setup (Already Done)

You've already set up QuestDB on CapRover. Verify it's running:

```bash
# Check QuestDB web console
https://questdb.yourdomain.com

# Or test connection from Django container
./venv/bin/python manage.py shell
>>> from django.db import connections
>>> connections['questdb'].cursor()
```

### 2. Configure Environment Variables

Add to your `.env` file:

```bash
# QuestDB Connection
QUESTDB_URL=postgresql://admin:your-password@srv-captain--questdb:8812/qdb
```

**Connection string format**:
```
postgresql://[user]:[password]@[host]:[port]/[database]
```

**For CapRover internal DNS**:
- Host: `srv-captain--questdb` (CapRover internal DNS)
- Port: `8812` (PostgreSQL wire protocol port)
- Database: `qdb` (default QuestDB database)

### 3. Create QuestDB Tables

Run the schema initialization command:

```bash
./venv/bin/python manage.py setup_questdb_schema

# Options:
--database questdb  # Specify database (default: questdb)
--drop              # Drop existing tables first (DANGEROUS)
```

**What this does**:
- Creates `assetprice` table with optimized QuestDB schema
- Uses QuestDB-specific features: `SYMBOL` types, `PARTITION BY DAY`, designated timestamps

### 4. Run Django Migrations

Migrate the Asset model to PostgreSQL:

```bash
./venv/bin/python manage.py migrate
```

This creates the `Asset` table in the default (PostgreSQL) database. AssetPrice is NOT migrated (it's `managed=False`).

### 5. Verify Setup

```bash
# Check PostgreSQL (Asset table)
./venv/bin/python manage.py dbshell
\dt feefifofunds_*

# Check QuestDB (assetprice table)
# Access web console at https://questdb.yourdomain.com
SELECT * FROM tables() WHERE table_name = 'assetprice';
```

---

## Schema Management

### QuestDB Schema Details

**AssetPrice Table**:
```sql
CREATE TABLE assetprice (
    asset_id INT,
    time TIMESTAMP,              -- Designated timestamp
    open DOUBLE,
    high DOUBLE,
    low DOUBLE,
    close DOUBLE,
    volume DOUBLE,
    interval_minutes INT,
    trade_count INT,
    quote_currency SYMBOL CAPACITY 256 CACHE,  -- Optimized for repeated values
    source SYMBOL CAPACITY 256 CACHE,
    created_at TIMESTAMP
) timestamp(time) PARTITION BY DAY;
```

### Key Features

- **SYMBOL type**: Optimized storage for repeated string values (currencies, sources)
- **timestamp(time)**: Designated timestamp column for time-series operations
- **PARTITION BY DAY**: Data partitioned by day for efficient queries
- **No indexes needed**: QuestDB automatically optimizes timestamp queries

### Updating Schema

If you need to modify the QuestDB schema:

1. **Backup your data** (if any exists)
2. Drop and recreate tables:
   ```bash
   ./venv/bin/python manage.py setup_questdb_schema --drop
   ```
3. Re-ingest data if needed

**Note**: QuestDB has limited DDL support. You cannot:
- Add columns to existing tables
- Rename columns
- Change column types

For schema changes, you must drop and recreate tables.

---

## Common Operations

### Ingesting Data

```bash
# Ingest Tier 1 assets, daily interval
./venv/bin/python manage.py ingest_sequential --tier TIER1 --intervals 1440

# Ingest multiple intervals
./venv/bin/python manage.py ingest_sequential --intervals 60,1440

# Ingest all tiers, all file types
./venv/bin/python manage.py ingest_sequential --tier ALL --file-type both
```

### Clearing Data

```bash
# Clear all data
./venv/bin/python manage.py clear_asset_data --yes

# Clear only prices/trades (keeps assets)
./venv/bin/python manage.py clear_asset_data --tables prices --yes

# Dry run (preview)
./venv/bin/python manage.py clear_asset_data --dry-run
```

### Querying from Django

```python
from feefifofunds.models import Asset, AssetPrice

# Get asset from PostgreSQL
asset = Asset.objects.get(ticker="BTC")

# Get prices from QuestDB (automatically routed)
prices = AssetPrice.objects.filter(
    asset_id=asset.id,
    interval_minutes=1440,
    time__gte='2024-01-01'
).order_by('-time')[:30]

# Access asset via property (lazy loads from PostgreSQL)
for price in prices:
    print(f"{price.asset.ticker}: ${price.close}")  # Loads asset on first access
```

---

## Querying Data

### Using Django ORM

```python
# Simple filter
recent_prices = AssetPrice.objects.filter(
    asset_id=1,
    interval_minutes=1440
).order_by('-time')[:100]

# Aggregations
from django.db.models import Avg, Max, Min
stats = AssetPrice.objects.filter(asset_id=1).aggregate(
    avg_close=Avg('close'),
    max_high=Max('high'),
    min_low=Min('low')
)
```

### Using Raw SQL (QuestDB SAMPLE BY)

For advanced time-series queries, use raw SQL with QuestDB's `SAMPLE BY`:

```python
from django.db import connections

with connections['questdb'].cursor() as cursor:
    # Resample to weekly OHLCV
    cursor.execute("""
        SELECT
            time,
            first(open) as open,
            max(high) as high,
            min(low) as low,
            last(close) as close,
            sum(volume) as volume
        FROM assetprice
        WHERE asset_id = %s
        AND interval_minutes = 1440
        SAMPLE BY 1w
    """, [asset_id])

    results = cursor.fetchall()
```

### Useful QuestDB Queries

**Get latest prices per asset**:
```sql
SELECT asset_id, last(close) as latest_close
FROM assetprice
WHERE interval_minutes = 1440
LATEST ON time PARTITION BY asset_id;
```

**Calculate moving averages**:
```sql
SELECT
    time,
    close,
    avg(close) OVER (ORDER BY time ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) as sma_7
FROM assetprice
WHERE asset_id = 1
AND interval_minutes = 1440;
```

**Count records by source**:
```sql
SELECT source, count() FROM assetprice;
```

---

## Troubleshooting

### Connection Issues

**Problem**: `django.db.utils.OperationalError: could not connect to server`

**Solutions**:
1. Verify QuestDB is running:
   ```bash
   # Check CapRover dashboard
   # Or curl the health endpoint
   curl http://srv-captain--questdb:9003/status
   ```

2. Check `QUESTDB_URL` in `.env`:
   ```bash
   # Correct format for CapRover
   QUESTDB_URL=postgresql://admin:password@srv-captain--questdb:8812/qdb
   ```

3. Test connection:
   ```bash
   ./venv/bin/python manage.py shell
   >>> from django.db import connections
   >>> connections['questdb'].cursor().execute("SELECT 1")
   ```

### Schema Issues

**Problem**: "Table 'assetprice' does not exist"

**Solution**: Run schema setup:
```bash
./venv/bin/python manage.py setup_questdb_schema
```

**Problem**: "Column X does not exist"

**Cause**: Schema mismatch between Django model and QuestDB table

**Solution**: Drop and recreate tables (WARNING: deletes data):
```bash
./venv/bin/python manage.py setup_questdb_schema --drop
```

### Performance Issues

**Problem**: Queries are slow

**Checks**:
1. Ensure you're querying on `time` column (indexed)
2. Use `SAMPLE BY` for aggregations
3. Check QuestDB memory usage via web console
4. Consider partitioning settings

**Optimization**:
```sql
-- Good: Uses designated timestamp
SELECT * FROM assetprice WHERE time > '2024-01-01';

-- Bad: Scans all data
SELECT * FROM assetprice WHERE asset_id = 1 AND interval_minutes = 1440;
```

### Data Ingestion Issues

**Problem**: Ingestion is slow

**Solutions**:
1. Use `--drop-indexes` flag (if supported)
2. Increase batch size in ingestor
3. Check QuestDB disk space
4. Monitor resource usage

**Problem**: Duplicate key errors

**Cause**: Attempting to insert duplicate records

**Solution**: QuestDB uses `ON CONFLICT DO NOTHING` automatically via the ingestor's COPY operations.

---

## Additional Resources

- **QuestDB Documentation**: https://questdb.io/docs/
- **QuestDB SQL Reference**: https://questdb.io/docs/reference/sql/
- **PostgreSQL Wire Protocol**: https://questdb.io/docs/reference/api/postgres/
- **FeeFiFoFunds Architecture**: `/docs/architecture.md`

---

## Next Steps

1. ✅ QuestDB is running on CapRover
2. ✅ Environment variables configured
3. ✅ Schema initialized
4. ✅ Django migrations applied
5. ➡️ **Start ingesting data**: `python manage.py ingest_sequential --tier TIER1 --intervals 1440`

For questions or issues, refer to the troubleshooting section above or check the QuestDB logs in CapRover.
