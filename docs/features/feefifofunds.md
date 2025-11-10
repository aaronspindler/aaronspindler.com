# FeeFiFoFunds - Multi-Asset Tracking System

## Overview

FeeFiFoFunds is an MVP Django application for tracking financial asset prices over time using a hybrid database architecture. It combines PostgreSQL for asset metadata with QuestDB for high-performance time-series data storage.

**Key Features:**
- Track multiple asset types: stocks, cryptocurrencies, commodities, currencies
- Store OHLCV (candle) data at multiple timeframes (1m, 5m, 15m, 60m, daily, etc.)
- Store individual trade (tick) data with microsecond precision
- Ingest data from multiple sources: Kraken CSV files, Massive.com API, Finnhub API
- High-performance ingestion: 50K-100K records/second with QuestDB ILP
- Tier-based asset classification for filtering and prioritization

## Architecture

### Hybrid Database Approach

FeeFiFoFunds uses two databases for optimal performance:

1. **PostgreSQL (default database)**
   - Stores Asset model with metadata (ticker, name, category, tier)
   - Django-managed with full ORM support and migrations
   - Relational queries and data integrity constraints

2. **QuestDB (time-series database)**
   - Stores AssetPrice and Trade models for time-series data
   - Optimized for high-throughput ingestion and fast queries
   - PARTITION BY DAY for efficient time-based queries
   - SYMBOL types for optimized string storage

### Why QuestDB?

QuestDB is purpose-built for time-series data and offers:
- **High ingestion speed**: 50K-100K records/second with ILP (Influx Line Protocol)
- **Efficient storage**: SYMBOL types compress repeated strings
- **Fast queries**: Sub-100ms aggregations on millions of records
- **Partitioning**: Daily partitions optimize time-range queries
- **PostgreSQL compatibility**: SQL queries work seamlessly
- **Designed timestamp**: Native time-series indexing

## Data Models

### Asset Model (PostgreSQL)

Universal model for all asset types stored in PostgreSQL.

**Fields:**
- `ticker` (CharField, unique): Primary ticker symbol (e.g., BTC, AAPL, GLD)
- `name` (CharField): Full asset name
- `category` (CharField): Asset category
  - STOCK: Stocks and ETFs
  - CRYPTO: Cryptocurrencies
  - COMMODITY: Commodities
  - CURRENCY: Fiat currencies
- `tier` (CharField): Asset tier classification
  - TIER1: Major/blue-chip assets (BTC, ETH, AAPL, SPY)
  - TIER2: Mid-cap/established assets (UNI, LINK, MSFT)
  - TIER3: Small-cap/emerging assets (BAT, ENJ, MANA)
  - TIER4: Micro-cap/speculative assets
  - UNCLASSIFIED: Not yet classified
- `description` (TextField): Optional asset description
- `active` (BooleanField): Whether asset is actively tracked
- `created_at`, `updated_at` (DateTimeField): Timestamps

**Indexes:**
- Primary key on `id`
- Unique index on `ticker`
- Index on `category`
- Index on `tier`
- Index on `active`

**Usage:**
```python
from feefifofunds.models import Asset

# Query by category
crypto_assets = Asset.objects.filter(category='CRYPTO')

# Query by tier
tier1_assets = Asset.objects.filter(tier='TIER1')

# Get specific asset
btc = Asset.objects.get(ticker='BTC')
```

---

### AssetPrice Model (QuestDB)

OHLCV (Open/High/Low/Close/Volume) price records stored in QuestDB for high-performance time-series queries.

**Fields:**
- `asset_id` (IntegerField): Reference to Asset.id in PostgreSQL
- `time` (DateTimeField): Timestamp (QuestDB designated timestamp)
- `open` (DecimalField): Opening price
- `high` (DecimalField): Highest price during interval
- `low` (DecimalField): Lowest price during interval
- `close` (DecimalField): Closing price
- `volume` (DecimalField): Trading volume
- `interval_minutes` (SmallIntegerField): Time interval in minutes
  - 1, 5, 15, 30, 60, 240, 720, 1440 (daily)
- `trade_count` (IntegerField): Number of trades during interval (for OHLCV data)
- `quote_currency` (CharField, SYMBOL): Currency for pricing (USD, EUR, BTC, etc.)
- `source` (CharField, SYMBOL): Data source (finnhub, massive, kraken)

**QuestDB Schema:**
```sql
CREATE TABLE assetprice (
    asset_id INT,
    time TIMESTAMP,
    open DOUBLE,
    high DOUBLE,
    low DOUBLE,
    close DOUBLE,
    volume DOUBLE,
    interval_minutes INT,
    trade_count INT,
    quote_currency SYMBOL CAPACITY 256 CACHE,
    source SYMBOL CAPACITY 256 CACHE
) timestamp(time) PARTITION BY DAY;
```

**Model Properties:**
- `managed = False`: Django doesn't manage this table
- `db_table = 'assetprice'`: QuestDB table name
- `asset` property: Lazy loads Asset from PostgreSQL

**Usage:**
```python
from feefifofunds.models import AssetPrice
from django.db import connections

# Query recent prices (use QuestDB connection)
with connections['questdb'].cursor() as cursor:
    cursor.execute("""
        SELECT asset_id, time, close, volume
        FROM assetprice
        WHERE asset_id = 1
        AND interval_minutes = 1440
        ORDER BY time DESC
        LIMIT 100
    """)
    rows = cursor.fetchall()
```

---

### Trade Model (QuestDB)

Individual trade (tick) records stored in QuestDB for high-performance time-series queries.

**Fields:**
- `asset_id` (IntegerField): Reference to Asset.id in PostgreSQL
- `time` (DateTimeField): Exact timestamp of trade (microsecond precision)
- `price` (DecimalField): Trade execution price
- `volume` (DecimalField): Trade volume/quantity
- `quote_currency` (CharField, SYMBOL): Currency for pricing
- `source` (CharField, SYMBOL): Data source (default: kraken)

**QuestDB Schema:**
```sql
CREATE TABLE trade (
    asset_id INT,
    time TIMESTAMP,
    price DOUBLE,
    volume DOUBLE,
    quote_currency SYMBOL CAPACITY 256 CACHE,
    source SYMBOL CAPACITY 256 CACHE
) timestamp(time) PARTITION BY DAY;
```

**Model Properties:**
- `managed = False`: Django doesn't manage this table
- `db_table = 'trade'`: QuestDB table name
- `asset` property: Lazy loads Asset from PostgreSQL

**Usage:**
```python
from feefifofunds.models import Trade
from django.db import connections

# Query recent trades (use QuestDB connection)
with connections['questdb'].cursor() as cursor:
    cursor.execute("""
        SELECT asset_id, time, price, volume
        FROM trade
        WHERE asset_id = 1
        AND time >= dateadd('d', -1, now())
        ORDER BY time DESC
        LIMIT 1000
    """)
    rows = cursor.fetchall()
```

## Management Commands

### Database Setup

#### setup_questdb_schema

Initialize QuestDB schema for AssetPrice and Trade tables.

```bash
# Initial setup
python manage.py setup_questdb_schema

# Drop and recreate (CAREFUL!)
python manage.py setup_questdb_schema --drop
```

**What it does:**
- Creates `assetprice` table with SYMBOL types, PARTITION BY DAY
- Creates `trade` table with SYMBOL types, PARTITION BY DAY
- Verifies tables were created successfully

**When to run:**
- Initial project setup
- After QuestDB instance reset

---

### Asset Management

#### create_asset

Manually create Asset records in PostgreSQL.

```bash
# Create Bitcoin
python manage.py create_asset --ticker BTC --name Bitcoin --category CRYPTO

# Create Apple stock
python manage.py create_asset --ticker AAPL --name "Apple Inc." --category STOCK

# With description
python manage.py create_asset \
  --ticker GLD \
  --name "SPDR Gold Trust" \
  --category COMMODITY \
  --description "Gold ETF tracking physical gold prices"
```

**Note:** Most assets are auto-created during ingestion. Use this for manual additions or testing.

---

### Data Ingestion

#### ingest_sequential (Recommended)

Fast sequential ingestion of Kraken OHLCV and trade data using QuestDB ILP.

**Key Features:**
- QuestDB ILP (Influx Line Protocol) for maximum speed (50K-100K records/sec)
- Filter by tier (TIER1-4), file type (ohlcv/trade), and intervals
- Auto-creates Asset records with tier classification
- Moves completed files to `ingested/` directory
- Idempotent: safe to re-run

**Examples:**

```bash
# Ingest TIER1 assets only (BTC, ETH, etc. - fastest)
python manage.py ingest_sequential --tier TIER1

# Ingest only OHLCV candle data
python manage.py ingest_sequential --file-type ohlcv

# Ingest only trade tick data
python manage.py ingest_sequential --file-type trade

# Ingest TIER1 OHLCV with specific intervals (1h and 1d only)
python manage.py ingest_sequential --tier TIER1 --file-type ohlcv --intervals 60,1440

# Automated run (skip confirmation)
python manage.py ingest_sequential --tier TIER1 --yes

# Stop on first error (for debugging)
python manage.py ingest_sequential --tier TIER1 --stop-on-error
```

**Tier Classification** (auto-assigned):
- **TIER1**: BTC, ETH, USDT, USDC, XRP, SOL, ADA, DOGE, BNB, TRX
- **TIER2**: UNI, AAVE, LINK, ALGO, ATOM, MATIC, DOT, FIL, ETC, LTC
- **TIER3**: BAT, ENJ, GALA, MANA, SAND, CRV, COMP, SNX, YFI, ZRX
- **TIER4**: All others

**Performance:**
- TIER1 OHLCV: ~10-15 seconds (major assets)
- TIER1 trade: ~30-60 seconds (major assets tick data)
- Full OHLCV: ~30-60 minutes (all tiers, all intervals)
- Full trade: ~2-4 hours (all tiers, all tick data)

---

#### load_prices

Load prices from external APIs (Massive.com or Finnhub).

**Examples:**

```bash
# Load 7 days of Apple stock from Massive.com
python manage.py load_prices --ticker AAPL --source massive --days 7

# Load 30 days of Bitcoin from Finnhub
python manage.py load_prices --ticker BTC --source finnhub --days 30

# Dry run
python manage.py load_prices --ticker AAPL --source massive --days 7 --dry-run
```

**Data Sources:**
- **Massive.com**: Stocks/ETFs (free: 730 days)
- **Finnhub**: Stocks/crypto/forex (free: ~365 days)

**Requirements:**
- Asset must exist in database
- API keys: `MASSIVE_API_KEY` or `FINNHUB_API_KEY`

---

#### backfill_prices

Backfill historical data with support for bulk operations.

**Examples:**

```bash
# Backfill single asset
python manage.py backfill_prices --ticker AAPL --source massive --days 730

# Backfill all active assets
python manage.py backfill_prices --source massive --days 365 --all

# Backfill only crypto
python manage.py backfill_prices --source massive --days 365 --all --category CRYPTO

# Backfill using grouped endpoint (MUCH faster!)
python manage.py backfill_prices --source massive --days 365 --all --grouped
```

**Grouped Mode** (Massive.com only):
- 1 API call per day instead of N calls (one per asset)
- Example: 365 days × 100 assets = 365 API calls (grouped) vs 36,500 calls (individual)
- Dramatically faster for bulk backfills

**Performance:**
- Individual: ~1 asset/second
- Grouped: ~100+ assets/second

## Usage Examples

### Query OHLCV Data

```python
from django.db import connections
from feefifofunds.models import Asset

# Get Bitcoin asset
btc = Asset.objects.get(ticker='BTC')

# Query daily prices for last 30 days
with connections['questdb'].cursor() as cursor:
    cursor.execute("""
        SELECT time, open, high, low, close, volume
        FROM assetprice
        WHERE asset_id = %s
        AND interval_minutes = 1440
        AND time >= dateadd('d', -30, now())
        ORDER BY time DESC
    """, [btc.id])

    for row in cursor.fetchall():
        time, open, high, low, close, volume = row
        print(f"{time}: O={open} H={high} L={low} C={close} V={volume}")
```

### Query Trade Data

```python
from django.db import connections
from feefifofunds.models import Asset

# Get Ethereum asset
eth = Asset.objects.get(ticker='ETH')

# Query trades for last hour
with connections['questdb'].cursor() as cursor:
    cursor.execute("""
        SELECT time, price, volume
        FROM trade
        WHERE asset_id = %s
        AND time >= dateadd('h', -1, now())
        ORDER BY time DESC
        LIMIT 1000
    """, [eth.id])

    for row in cursor.fetchall():
        time, price, volume = row
        print(f"{time}: ${price} Vol={volume}")
```

### Calculate VWAP (Volume Weighted Average Price)

```python
from django.db import connections
from feefifofunds.models import Asset

btc = Asset.objects.get(ticker='BTC')

with connections['questdb'].cursor() as cursor:
    cursor.execute("""
        SELECT
            time_bucket('1d', time) as day,
            sum(close * volume) / sum(volume) as vwap,
            sum(volume) as total_volume
        FROM assetprice
        WHERE asset_id = %s
        AND interval_minutes = 1440
        AND time >= dateadd('d', -30, now())
        GROUP BY day
        ORDER BY day DESC
    """, [btc.id])

    for row in cursor.fetchall():
        day, vwap, volume = row
        print(f"{day}: VWAP=${vwap:.2f} Vol={volume:,.0f}")
```

## Common Workflows

### Initial Setup

```bash
# 1. Run PostgreSQL migrations
python manage.py migrate feefifofunds

# 2. Initialize QuestDB schema
python manage.py setup_questdb_schema

# 3. Ingest Kraken data (TIER1 only for testing)
python manage.py ingest_sequential --tier TIER1 --yes

# 4. Verify data
python manage.py shell
>>> from feefifofunds.models import Asset
>>> Asset.objects.count()
```

### Full Kraken Data Ingestion

```bash
# Ingest all OHLCV data (all tiers, all intervals)
python manage.py ingest_sequential --file-type ohlcv --yes

# Ingest all trade data (all tiers)
python manage.py ingest_sequential --file-type trade --yes
```

### Incremental Updates

```bash
# Ingest only new TIER1 OHLCV data (daily interval)
python manage.py ingest_sequential --tier TIER1 --file-type ohlcv --intervals 1440 --yes

# Backfill recent data from Massive.com
python manage.py backfill_prices --source massive --days 7 --all --grouped
```

### Data Recovery

```bash
# Drop and recreate QuestDB tables
python manage.py setup_questdb_schema --drop

# Re-ingest all data
python manage.py ingest_sequential --yes
```

## Configuration

### Database Settings

**PostgreSQL (default database):**
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'your_db_name',
        'USER': 'your_db_user',
        'PASSWORD': 'your_db_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

**QuestDB (time-series database):**
```python
DATABASES['questdb'] = {
    'ENGINE': 'django.db.backends.postgresql',
    'NAME': 'qdb',
    'USER': 'admin',
    'PASSWORD': 'quest',
    'HOST': 'localhost',
    'PORT': '8812',  # QuestDB PostgreSQL wire protocol port
}
```

### Environment Variables

**Required for external APIs:**
```bash
# Massive.com (free tier: 730 days historical)
MASSIVE_API_KEY=your_massive_api_key

# Finnhub (free tier: ~365 days historical)
FINNHUB_API_KEY=your_finnhub_api_key
```

**QuestDB connection:**
```bash
QUESTDB_URL=postgresql://admin:quest@localhost:8812/qdb
```

## Performance Optimization

### QuestDB Tuning

**Partition pruning:**
- QuestDB automatically prunes partitions based on time ranges
- Use time filters in WHERE clauses for optimal performance
- Example: `WHERE time >= dateadd('d', -30, now())`

**Symbol caching:**
- SYMBOL types cache repeated strings in memory
- Significantly reduces memory usage for source/quote_currency
- Automatically optimized by QuestDB

**Index usage:**
- QuestDB automatically creates time-based indexes
- No manual index creation needed for time-series queries

### Ingestion Optimization

**Batch size:**
- QuestDB ILP batches records for optimal throughput
- Default batch size: 1000 records
- Adjust based on available memory

**Network tuning:**
- Use persistent ILP connection for entire batch
- Minimize round trips with batching
- Default: single connection per command run

**File organization:**
- Keep CSV files in separate directories by tier
- Use tier filtering to ingest incrementally
- Archive processed files to `ingested/` directory

## Troubleshooting

### QuestDB Connection Issues

**Error:** `django.db.utils.OperationalError: could not connect to server`

**Solution:**
```bash
# Check QuestDB is running
docker ps | grep questdb

# Test connection
psql -h localhost -p 8812 -U admin -d qdb -c "SELECT 1"

# Verify settings
python manage.py shell
>>> from django.db import connections
>>> connections['questdb'].ensure_connection()
```

### Ingestion Errors

**Error:** `No such table: assetprice`

**Solution:**
```bash
# Initialize QuestDB schema
python manage.py setup_questdb_schema
```

**Error:** `Asset with ticker 'BTC' already exists`

**Solution:**
- Normal during re-ingestion (assets auto-created)
- Command will continue with existing asset
- Use `--yes` flag to skip confirmation

### Performance Issues

**Slow queries:**
- Add time filters: `WHERE time >= dateadd('d', -30, now())`
- Use appropriate intervals: daily (1440) for long-term trends
- Check partition pruning: `EXPLAIN SELECT ... WHERE time >= ...`

**Slow ingestion:**
- Use tier filtering: `--tier TIER1` for testing
- Use file type filtering: `--file-type ohlcv` or `--file-type trade`
- Check network latency to QuestDB
- Monitor QuestDB logs for errors

## Related Documentation

- [Commands Reference](../commands.md#feefifofunds-data-management) - All management commands
- [Architecture](../architecture.md) - System design overview
- [CLAUDE.md](../../CLAUDE.md#feefifofunds-data-management) - Development guide
