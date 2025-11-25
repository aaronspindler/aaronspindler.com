# FeeFiFoFunds - Setup & Development Guide

Complete guide for setting up and developing the FeeFiFoFunds application.

## Table of Contents

1. [Project Overview](#project-overview)
2. [Prerequisites](#prerequisites)
3. [Installation](#installation)
4. [Database Setup](#database-setup)
5. [QuestDB Configuration](#questdb-configuration)
6. [Development Workflows](#development-workflows)
7. [Testing](#testing)
8. [Debugging](#debugging)
9. [Contribution Guidelines](#contribution-guidelines)

---

## Project Overview

FeeFiFoFunds is a Django-based multi-asset price tracking platform. The project is in production with focus on data ingestion infrastructure for stocks, cryptocurrencies, commodities, and currencies.

### Goals

- **Primary**: Build reliable data ingestion pipeline for multi-asset price tracking
- **Secondary**: Enable asset comparison and basic analytics
- **Future**: Advanced analytics and machine learning predictions

### Current Status

**Completed Components:**

#### 🗄️ Database Models (100%)
- **Asset** - Universal model for all asset types (4 categories) stored in PostgreSQL
- **AssetPrice** - OHLCV price data stored in QuestDB for time-series performance
- Uses TimestampedModel mixin from `utils/models/mixins.py`

#### 🔌 Data Sources (100%)
- **Kraken CSV Ingestion** - Fast QuestDB ILP ingestion (50K-100K records/sec)
- **FinnhubDataSource** - Stocks and crypto (~1 year historical on free tier)
- **MassiveDataSource** - Stocks via Polygon.io (2 years historical on free tier)
- Standardized data transformation pipeline
- Error handling (DataSourceError, DataNotFoundError)

#### 🛠️ Management Commands (100%)
- **setup_questdb_schema** - Initialize QuestDB tables
- **create_asset** - Create assets manually
- **ingest_sequential** - Fast QuestDB ILP ingestion from Kraken CSV
- **load_prices** - Load recent price data from APIs
- **backfill_prices** - Backfill historical prices (single or all assets)
- Dry-run mode support
- Free tier warnings

#### 🎨 Admin Interface (100%)
- Asset admin with filters and search (PostgreSQL)
- AssetPrice data managed via raw SQL (QuestDB)
- Proper field organization and help text

---

## Prerequisites

### Required Software

- **Python 3.13+**
- **PostgreSQL 16+**
- **QuestDB 8.2.0+** (requires 7.3+ for DEDUP support)
- **Redis 7+** (optional, for caching)
- **uv** (for fast dependency management)

### System Requirements

- **OS**: macOS, Linux, or Windows (WSL2 recommended)
- **RAM**: 4GB minimum, 8GB recommended
- **Disk**: 10GB free space (more for large datasets)
- **Network**: Stable internet connection for API access

---

## Installation

### 1. Clone and Navigate

```bash
cd /path/to/aaronspindler.com
```

### 2. Set Up Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install uv

```bash
pip install uv
```

### 4. Install Dependencies

```bash
# Install from lockfiles (10-100x faster than pip)
uv pip install -r requirements/base.txt
uv pip install -r requirements/dev.txt
```

### 5. Set Up Environment Variables

Create `.env` file in project root:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/aaronspindler

# Django
DEBUG=True
SECRET_KEY=your-secret-key-here

# QuestDB
QUESTDB_URL=postgresql://admin:quest@localhost:8812/qdb

# Data Source API Keys
FINNHUB_API_KEY=your-finnhub-key
MASSIVE_API_KEY=your-polygon-key

# Optional: Redis (for caching)
REDIS_URL=redis://localhost:6379/0
USE_DEV_CACHE_PREFIX=True
```

**Get API Keys**:
- Finnhub: https://finnhub.io/register (free tier: 60 calls/min)
- Massive.com/Polygon.io: https://polygon.io/dashboard/signup (free tier: 2 years historical)

### 6. Run Migrations

```bash
# Run PostgreSQL migrations
python manage.py migrate

# Create superuser for admin access
python manage.py createsuperuser
```

### 7. Seed Data (Optional)

```bash
# Ingest Kraken data (TIER1 only for quick testing)
python manage.py ingest_sequential --tier TIER1 --yes

# Or load price data from external APIs
python manage.py backfill_prices --ticker AAPL --source massive --days 365
python manage.py backfill_prices --ticker BTC --source finnhub --days 365
```

### 8. Run Development Server

```bash
python manage.py runserver
```

Access Django admin at `http://localhost:8000/admin/`

---

## Database Setup

### PostgreSQL Setup

FeeFiFoFunds uses PostgreSQL for relational data (Asset model).

**Configuration** (already in settings.py):
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('DB_NAME'),
        'USER': env('DB_USER'),
        'PASSWORD': env('DB_PASSWORD'),
        'HOST': env('DB_HOST', default='localhost'),
        'PORT': env('DB_PORT', default='5432'),
    }
}
```

**Running Migrations**:
```bash
# Create migrations after model changes
python manage.py makemigrations feefifofunds

# Review migration file
cat feefifofunds/migrations/000X_description.py

# Apply migrations
python manage.py migrate feefifofunds

# Show migration status
python manage.py showmigrations feefifofunds
```

**Important**:
- Django migrations only apply to PostgreSQL models (Asset)
- QuestDB model (AssetPrice) uses `managed=False` and is created via `setup_questdb_schema`
- Never manually edit or drop migrations after they're committed

---

## QuestDB Configuration

### Why QuestDB?

QuestDB is a high-performance time-series database optimized for financial data. FeeFiFoFunds uses a hybrid database approach:

- **PostgreSQL (default database)**: Asset model (relational data)
- **QuestDB (questdb database)**: AssetPrice model (time-series data)

**Benefits:**
- **10-100x faster** queries for time-series data
- **Better compression** (2-5x vs PostgreSQL)
- **Lower resource usage** (512MB+ vs 2GB+ for TimescaleDB)
- **Built for financial data** with `SAMPLE BY` for OHLCV aggregations
- **Simple operations** - easier than TimescaleDB

### Architecture

#### Database Routing

Django's database router (`config/db_routers.py`) automatically routes models to the correct database:

```python
# Routes to PostgreSQL (default)
Asset.objects.all()  # → default database

# Routes to QuestDB
AssetPrice.objects.all()  # → questdb database
```

#### Model Configuration

**Asset Model (PostgreSQL)**:
- Managed by Django (`managed=True`)
- Uses Django migrations
- Has ForeignKey relationships

**AssetPrice Model (QuestDB)**:
- Not managed by Django (`managed=False`)
- Schema created manually via `setup_questdb_schema` command
- Uses `asset_id` integer field instead of ForeignKey
- Includes `@property` method to lazy-load asset from PostgreSQL

### Setup Instructions

#### 1. CapRover Setup (Production)

If you're using CapRover, verify it's running:

```bash
# Check QuestDB web console
https://questdb.yourdomain.com

# Or test connection from Django container
./venv/bin/python manage.py shell
>>> from django.db import connections
>>> connections['questdb'].cursor()
```

#### 2. Local Docker Setup (Development)

```bash
# Run QuestDB via Docker
docker run -d \
  --name questdb \
  -p 9000:9000 \
  -p 9009:9009 \
  -p 8812:8812 \
  questdb/questdb:latest

# Access web console at http://localhost:9000
```

#### 3. Configure Environment Variables

Add to your `.env` file:

```bash
# QuestDB Connection
QUESTDB_URL=postgresql://admin:your-password@localhost:8812/qdb
```

**Connection string format**:
```
postgresql://[user]:[password]@[host]:[port]/[database]
```

**For CapRover internal DNS**:
- Host: `srv-captain--questdb` (CapRover internal DNS)
- Port: `8812` (PostgreSQL wire protocol port)
- Database: `qdb` (default QuestDB database)

**For Local Development**:
- Host: `localhost`
- Port: `8812`
- Database: `qdb`

#### 4. Create QuestDB Tables

Run the schema initialization command:

```bash
python manage.py setup_questdb_schema

# Options:
--database questdb  # Specify database (default: questdb)
--drop              # Drop existing tables first (DANGEROUS)
```

**What this does**:
- Creates `assetprice` table with optimized QuestDB schema
- Uses QuestDB-specific features: `SYMBOL` types, `PARTITION BY DAY`, designated timestamps
- Enables DEDUP (QuestDB 7.3+ required)

#### 5. Verify Setup

```bash
# Check PostgreSQL (Asset table)
python manage.py dbshell
\dt feefifofunds_*

# Check QuestDB (assetprice table)
# Access web console at http://localhost:9000 or https://questdb.yourdomain.com
SELECT * FROM tables() WHERE table_name = 'assetprice';
```

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
) TIMESTAMP(time) PARTITION BY DAY
DEDUP UPSERT KEYS(time, asset_id, interval_minutes, source, quote_currency);
```

**Key Features**:
- **SYMBOL type**: Optimized storage for repeated string values (currencies, sources)
- **timestamp(time)**: Designated timestamp column for time-series operations
- **PARTITION BY DAY**: Data partitioned by day for efficient queries
- **DEDUP**: Ensures idempotent re-ingestion (safe to re-run, no duplicates)
- **No indexes needed**: QuestDB automatically optimizes timestamp queries

### Updating Schema

If you need to modify the QuestDB schema:

1. **Backup your data** (if any exists)
2. Drop and recreate tables:
   ```bash
   python manage.py setup_questdb_schema --drop
   ```
3. Re-ingest data if needed

**Note**: QuestDB has limited DDL support. You cannot:
- Add columns to existing tables
- Rename columns
- Change column types

For schema changes, you must drop and recreate tables.

### Common Operations

#### Ingesting Data

```bash
# Ingest Tier 1 assets, daily interval
python manage.py ingest_sequential --tier TIER1 --intervals 1440

# Ingest multiple intervals
python manage.py ingest_sequential --intervals 60,1440

# Ingest all tiers
python manage.py ingest_sequential --tier ALL
```

#### Clearing Data

```bash
# Clear all data
python manage.py clear_asset_data --yes

# Clear only prices (keeps assets)
python manage.py clear_asset_data --tables prices --yes

# Dry run (preview)
python manage.py clear_asset_data --dry-run
```

#### Querying from Django

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

### Querying Data

#### Using Django ORM

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

#### Using Raw SQL (QuestDB SAMPLE BY)

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

#### Useful QuestDB Queries

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

## Development Workflows

### Asset Management

```bash
# Create a single asset
python manage.py create_asset --ticker BTC --name Bitcoin --category CRYPTO

# Create a stock
python manage.py create_asset --ticker AAPL --name "Apple Inc." --category STOCK

# Create a commodity
python manage.py create_asset --ticker GLD --name "Gold ETF" --category COMMODITY
```

**Note**: Most assets are auto-created during Kraken ingestion with automatic tier classification.

### Price Data Loading

```bash
# Ingest Kraken CSV data (recommended - fastest)
python manage.py ingest_sequential --tier TIER1 --yes

# Load recent prices from APIs
python manage.py load_prices --ticker AAPL --source massive --days 7

# Load 30 days of data
python manage.py load_prices --ticker BTC --source finnhub --days 30

# Backfill historical data
python manage.py backfill_prices --ticker AAPL --source massive --days 365

# Backfill all active assets using grouped endpoint (MUCH faster!)
python manage.py backfill_prices --source massive --days 730 --all --grouped

# Dry-run mode (preview without saving)
python manage.py load_prices --ticker AAPL --source massive --days 7 --dry-run
```

**Data Source Considerations**:
- **Kraken**: Best for crypto, 50K-100K records/sec ingestion via QuestDB ILP
- **Finnhub**: ~1 year historical, 60 calls/minute, supports stocks + crypto
- **Massive.com**: 2 years historical, ~100 requests/second, stocks only

### Django Admin

```bash
# Create superuser
python manage.py createsuperuser

# Access admin interface
open http://localhost:8000/admin/

# Available admin interfaces:
# - Assets: Browse, filter, search, create assets (PostgreSQL)
# - AssetPrice: Query via Django shell or QuestDB console (managed=False)
```

### Django Shell

```bash
# Open Django shell
python manage.py shell

# Example queries:
>>> from feefifofunds.models import Asset
>>> from django.db import connections
>>>
>>> # Get all crypto assets
>>> Asset.objects.filter(category='CRYPTO')
>>>
>>> # Query QuestDB for price history
>>> btc = Asset.objects.get(ticker='BTC')
>>> with connections['questdb'].cursor() as cursor:
...     cursor.execute("""
...         SELECT time, close, volume
...         FROM assetprice
...         WHERE asset_id = %s
...         AND interval_minutes = 1440
...         ORDER BY time DESC
...         LIMIT 10
...     """, [btc.id])
...     rows = cursor.fetchall()
```

---

## Testing

### Running Tests

```bash
# Run all feefifofunds tests
python manage.py test feefifofunds

# Run with verbose output
python manage.py test feefifofunds --verbosity=2

# Run with coverage
coverage run --source='feefifofunds' manage.py test feefifofunds --no-input
coverage report
coverage html  # Generate HTML report in htmlcov/
```

### Docker Testing

```bash
# Build test environment
make test-build

# Run tests in Docker
make test-run-app APP=feefifofunds

# Interactive shell for debugging
make test-shell
```

### Writing Tests

**Test Structure**:
```python
from django.test import TestCase
from feefifofunds.models import Asset

class AssetModelTest(TestCase):
    def test_asset_creation(self):
        asset = Asset.objects.create(
            ticker='TEST',
            name='Test Asset',
            category='STOCK'
        )
        actual_ticker = asset.ticker
        expected_ticker = 'TEST'
        message = f"Expected ticker {expected_ticker}, got {actual_ticker}"
        self.assertEqual(actual_ticker, expected_ticker, message)

        self.assertTrue(asset.active, "Asset should be active by default")
```

---

## Debugging

### Enable Debug Logging

```python
# In settings.py
DEBUG = True

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'feefifofunds': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}
```

### Django Debug Toolbar

Already configured in dev settings. Access at `/__debug__/` when DEBUG=True.

### Database Query Debugging

```python
from django.db import connection

# Enable query logging
from django.conf import settings
settings.DEBUG = True

# Run your code
asset = Asset.objects.get(ticker='BTC')

# View queries
for query in connection.queries:
    print(query['sql'])
```

### Data Source Debugging

```bash
# Use dry-run mode to preview API calls
python manage.py load_prices --ticker AAPL --source massive --days 7 --dry-run

# Check API keys
python manage.py shell
>>> from django.conf import settings
>>> settings.FINNHUB_API_KEY
>>> settings.MASSIVE_API_KEY
```

### QuestDB Debugging

```bash
# Test QuestDB connection
psql -h localhost -p 8812 -U admin -d qdb -c "SELECT 1"

# Check table exists
psql -h localhost -p 8812 -U admin -d qdb -c "SELECT COUNT(*) FROM assetprice"

# Verify data ingestion
psql -h localhost -p 8812 -U admin -d qdb -c "SELECT COUNT(*) FROM assetprice WHERE asset_id = 1"
```

---

## Contribution Guidelines

### Code Style

- Follow PEP 8 (enforced by Ruff)
- Use type hints for function parameters and return values
- Write docstrings for public methods
- Keep functions small and focused (<50 lines ideal)

### Pre-commit Hooks

```bash
# Install hooks
pre-commit install

# Run manually on all files
pre-commit run --all-files

# Run on staged files only
git add .
pre-commit
```

Hooks include:
- Ruff (linting and formatting)
- File quality checks (trailing whitespace, end-of-file, etc.)
- Django system checks

### Commit Messages

Follow conventional commits format:

```
feat: Add CoinGecko data source integration
fix: Correct timestamp timezone handling in Finnhub source
docs: Update setup instructions with API key steps
test: Add tests for Asset model
refactor: Simplify price data transformation
```

### Pull Request Process

1. Create feature branch: `git checkout -b feature/your-feature-name`
2. Make changes and test thoroughly
3. Run pre-commit hooks: `pre-commit run --all-files`
4. Update documentation if needed
5. Commit changes with descriptive messages
6. Push branch and create PR
7. Request review from maintainers

### Branch Naming

- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation only
- `refactor/` - Code refactoring
- `test/` - Test additions/improvements

---

## Development Notes

### API Rate Limits

Be mindful of free tier limits when developing:

**Finnhub**:
- 60 API calls per minute
- ~1 year historical data
- Supports stocks and crypto

**Massive.com (Polygon.io)**:
- ~100 requests per second (soft limit)
- 2 years historical data
- Stocks only

### Environment Variables

Never commit:
- API keys
- Secret keys
- Database passwords
- Debug settings (DEBUG=True)

Always use `.env` file and django-environ.

### Database Best Practices

**PostgreSQL (Asset model)**:
- Always use migrations for schema changes
- Never manually edit the database
- Index fields used in filters and joins

**QuestDB (AssetPrice model)**:
- Use raw SQL for queries (`connections['questdb'].cursor()`)
- Leverage PARTITION BY DAY for time-range queries
- Use SYMBOL types for repeated strings
- Batch inserts with ILP for maximum performance

### Data Quality

When loading price data:
- Verify timestamps are in UTC
- Check for missing or null values
- Compare data from multiple sources when available
- Use dry-run mode to preview before saving

---

## Troubleshooting

### Connection Issues

**Problem**: `django.db.utils.OperationalError: could not connect to server`

**Solutions**:
1. Verify QuestDB is running:
   ```bash
   # Check Docker container
   docker ps | grep questdb

   # Or check health endpoint
   curl http://localhost:9003/status
   ```

2. Check `QUESTDB_URL` in `.env`:
   ```bash
   # Correct format for local
   QUESTDB_URL=postgresql://admin:quest@localhost:8812/qdb

   # Correct format for CapRover
   QUESTDB_URL=postgresql://admin:password@srv-captain--questdb:8812/qdb
   ```

3. Test connection:
   ```bash
   python manage.py shell
   >>> from django.db import connections
   >>> connections['questdb'].cursor().execute("SELECT 1")
   ```

---

### Schema Issues

**Problem**: "Table 'assetprice' does not exist"

**Solution**: Run schema setup:
```bash
python manage.py setup_questdb_schema
```

**Problem**: "Column X does not exist"

**Cause**: Schema mismatch between Django model and QuestDB table

**Solution**: Drop and recreate tables (WARNING: deletes data):
```bash
python manage.py setup_questdb_schema --drop
```

---

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

---

## Related Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture and design
- [OPERATIONS.md](OPERATIONS.md) - Commands and workflows
- [INTEGRATIONS.md](INTEGRATIONS.md) - Data source integrations
- [README.md](README.md) - Overview and quick start

---

## Getting Help

- Check [centralized documentation](../../) for comprehensive guides
- Search GitHub issues
- Review error messages and stack traces
- Use Django shell for debugging queries
- Create a GitHub issue with:
  - Clear description of problem
  - Steps to reproduce
  - Error messages and stack traces
  - Environment details (Python version, OS, databases, etc.)
