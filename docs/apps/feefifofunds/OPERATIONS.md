# FeeFiFoFunds - Operations Guide

Complete reference for all operational commands, automated tasks, and ingestion workflows.

## Table of Contents

1. [Management Commands](#management-commands)
2. [Kraken OHLCV Ingestion](#kraken-ohlcv-ingestion)
3. [Celery Automated Tasks](#celery-automated-tasks)
4. [Common Workflows](#common-workflows)
5. [Troubleshooting](#troubleshooting)

---

## Management Commands

### Database Setup Commands

#### check_questdb_version

Check QuestDB version to verify DEDUP support (requires 7.3+).

**Usage**:
```bash
python manage.py check_questdb_version
```

**Options**:
- `--database`: Database to check (default: questdb)

**Examples**:
```bash
# Check default QuestDB instance
python manage.py check_questdb_version

# Check custom database connection
python manage.py check_questdb_version --database custom_questdb
```

**What It Does**:
1. Queries QuestDB version using `SELECT version()`
2. Verifies version is >= 7.3 (required for DEDUP feature)
3. Displays compatibility status for deduplication support
4. Provides migration instructions if version is compatible

**When to Run**:
- Before applying QuestDB migrations
- After upgrading QuestDB instance
- When troubleshooting deduplication issues

---

#### QuestDB Migrations

QuestDB schema is managed through Django migrations (introduced in migration 0003+).

**New Environments**:
```bash
# Run all migrations (creates table with DEDUP enabled)
python manage.py migrate feefifofunds
```

**Migrations**:
- **0003_create_questdb_assetprice_with_dedup**: Creates `assetprice` table with DEDUP enabled
  - SYMBOL types for quote_currency and source
  - PARTITION BY DAY for optimal performance
  - Designated timestamp column
  - DEDUP UPSERT KEYS: `(time, asset_id, interval_minutes, source, quote_currency)`
  - Ensures idempotent re-ingestion (safe to re-run ingestion)
  - Upsert behavior: newer data overwrites older on conflict

**Rollback**:
```bash
# Remove table (rollback 0003 - DANGEROUS)
python manage.py migrate feefifofunds 0002
```

**Important Notes**:
- AssetPrice model uses `managed=False` in Django
- These migrations only apply to the `questdb` database connection
- Deduplication requires QuestDB 7.3+ (check with `check_questdb_version`)
- DEDUP is enabled by default in migration 0003 (no separate migration needed)
- With DEDUP enabled, re-ingesting data is safe (no duplicates created)

---

### Asset Management Commands

#### create_asset

Create a new asset record in the PostgreSQL database.

**Usage**:
```bash
python manage.py create_asset --ticker SYMBOL --name "Asset Name" --category TYPE
```

**Options**:
- `--ticker` (required): Asset ticker symbol (e.g., BTC, AAPL, GLD)
- `--name` (required): Full asset name
- `--category` (required): Asset category (STOCK/CRYPTO/COMMODITY/CURRENCY)
- `--quote-currency`: Currency for pricing (default: USD)
- `--description`: Optional asset description

**Examples**:
```bash
# Create Bitcoin asset
python manage.py create_asset --ticker BTC --name Bitcoin --category CRYPTO

# Create Apple stock with custom quote currency
python manage.py create_asset --ticker AAPL --name "Apple Inc." --category STOCK --quote-currency USD

# Create asset with description
python manage.py create_asset --ticker GLD --name "SPDR Gold Trust" --category COMMODITY --description "Gold ETF tracking physical gold prices"
```

**What It Does**:
1. Validates ticker doesn't already exist
2. Creates Asset record in PostgreSQL
3. Sets asset as active by default
4. Displays confirmation with asset details

**When to Use**:
- Manually adding assets not auto-created during ingestion
- Adding assets for external API data sources
- Testing asset management functionality

---

### Data Ingestion Commands

#### ingest_sequential

**Fast sequential ingestion of Kraken OHLCV data files using QuestDB ILP (Influx Line Protocol).**

**Usage**:
```bash
python manage.py ingest_sequential [--tier TIER] [--intervals INTERVALS]
```

**Options**:
- `--tier`: Asset tier to ingest (TIER1/TIER2/TIER3/TIER4/ALL). Default: ALL
- `--intervals`: Comma-separated intervals in minutes (e.g., '60,1440' for 1h and 1d)
- `--yes`, `-y`: Skip confirmation prompts
- `--database`: Database to use (default: questdb)
- `--data-dir`: Custom data directory (for testing)
- `--stop-on-error`: Stop processing on first error (default: continue)

**Examples**:
```bash
# Ingest only TIER1 assets (BTC, ETH, etc. - fastest)
python manage.py ingest_sequential --tier TIER1

# Ingest TIER1 data with specific intervals (1h and 1d only)
python manage.py ingest_sequential --tier TIER1 --intervals 60,1440

# Ingest all assets (default)
python manage.py ingest_sequential

# Automated run (skip prompts)
python manage.py ingest_sequential --tier TIER1 --yes

# Stop on first error
python manage.py ingest_sequential --stop-on-error
```

**Key Features**:
- **QuestDB ILP ingestion**: Direct Influx Line Protocol for maximum speed (50K-100K records/sec)
- **Flexible filtering**: Filter by asset tier (TIER1-4) and/or intervals
- **Idempotent**: QuestDB deduplication enabled (migration 0003) - safe to re-run, no duplicates
- **Auto file management**: Moves completed files to `ingested/ohlcv/` directory
- **Empty file cleanup**: Deletes invalid/empty files automatically
- **Rich progress display**: Real-time stats with file size, records, and ETA
- **Auto-asset creation**: Creates Asset records with tier classification if they don't exist
- **Persistent ILP connection**: Single connection for entire batch for better performance

**Asset Tier Classification** (auto-assigned during ingestion):
- **TIER1**: Major cryptos (BTC, ETH, USDT, USDC, XRP, SOL, ADA, DOGE, BNB, etc.)
- **TIER2**: Established projects (UNI, AAVE, LINK, ALGO, ATOM, MATIC, DOT, etc.)
- **TIER3**: Emerging projects (BAT, ENJ, GALA, MANA, SAND, etc.)
- **TIER4**: Small/speculative (all others)

**Performance**:
- TIER1 OHLCV: ~10-15 seconds (major assets only)
- Full OHLCV dataset: ~30-60 minutes (all tiers, all intervals)
- Speed: 50K-100K records/second with QuestDB ILP

**Error Handling**:
```bash
# By default, continues processing on errors
python manage.py ingest_sequential

# To stop on first error (useful for debugging)
python manage.py ingest_sequential --stop-on-error
```

**File Discovery**:
- Automatically discovers OHLCV files in `data/` directory
- Filters by tier and intervals
- Displays file breakdown and tier statistics before processing
- Waits for user confirmation (unless --yes specified)

**When to Use**:
- **Preferred method** for Kraken OHLCV data ingestion
- Fast, reliable sequential processing with QuestDB ILP
- Ideal for both initial bulk loads and incremental updates

---

#### load_prices

Load asset price data from external sources (Massive.com or Finnhub).

**Usage**:
```bash
python manage.py load_prices --ticker SYMBOL --source SOURCE --days N
```

**Options**:
- `--ticker` (required): Asset ticker symbol (e.g., AAPL, MSFT)
- `--source` (required): Data source (massive/finnhub)
- `--days`: Number of days to fetch (default: 7)
- `--dry-run`: Preview data without saving to database

**Examples**:
```bash
# Load 7 days of Apple stock data from Massive.com
python manage.py load_prices --ticker AAPL --source massive --days 7

# Load 30 days of Bitcoin data from Finnhub
python manage.py load_prices --ticker BTC --source finnhub --days 30

# Dry run to preview data
python manage.py load_prices --ticker AAPL --source massive --days 7 --dry-run
```

**Data Sources**:
- **Massive.com**: Stocks and ETFs (free tier: 730 days historical)
- **Finnhub**: Stocks, crypto, forex (free tier: ~365 days estimated)

**Requirements**:
- Asset must exist in database (create with `create_asset` command first)
- API keys: `MASSIVE_API_KEY` or `FINNHUB_API_KEY` environment variables

---

#### backfill_prices

Backfill historical asset price data from external sources with support for bulk operations.

**Usage**:
```bash
python manage.py backfill_prices --source SOURCE [--ticker SYMBOL | --all] --days N
```

**Options**:
- `--source` (required): Data source (massive/finnhub)
- `--ticker`: Single asset ticker symbol
- `--all`: Backfill all active assets
- `--days`: Number of days to backfill from today
- `--start`: Start date (YYYY-MM-DD format)
- `--end`: End date (YYYY-MM-DD format, defaults to today)
- `--category`: Filter by category (only with --all)
- `--grouped`: Use grouped daily endpoint (massive only, requires --all, MUCH faster)
- `--dry-run`: Preview without saving

**Examples**:
```bash
# Backfill single asset for 2 years
python manage.py backfill_prices --ticker AAPL --source massive --days 730

# Backfill all active assets for 1 year
python manage.py backfill_prices --source massive --days 365 --all

# Backfill only crypto assets
python manage.py backfill_prices --source massive --days 365 --all --category CRYPTO

# Backfill using grouped endpoint (1 API call per day instead of N - MUCH faster!)
python manage.py backfill_prices --source massive --days 365 --all --grouped

# Backfill specific date range
python manage.py backfill_prices --ticker AAPL --source massive --start 2024-01-01 --end 2024-12-31

# Dry run to preview
python manage.py backfill_prices --ticker AAPL --source massive --days 30 --dry-run
```

**Grouped Mode** (Massive.com only):
- Uses `/grouped/daily/{date}` endpoint
- **1 API call per day** instead of N calls (one per asset)
- **Dramatically faster** for bulk backfills
- Returns data for ALL available assets in a single response
- Filters to match your active assets
- Example: 365 days × 100 assets = 365 API calls (grouped) vs 36,500 calls (individual)

**Performance**:
- Individual mode: ~1 asset/second (API rate limited)
- Grouped mode: ~100+ assets/second (1 call returns all assets)
- Free tier limits:
  - Massive.com: 730 days max, ~100 requests/second
  - Finnhub: ~365 days estimated

---

#### backfill_kraken_gaps

**Detect and backfill gaps in Kraken asset price data using the Kraken REST API.**

Identifies both missing days and missing intervals within days, classifies gaps based on Kraken's 720-candle API limitation, and provides interactive backfilling with detailed reporting.

**Usage**:
```bash
python manage.py backfill_kraken_gaps [--tier TIER] [--asset TICKER] [--interval N]
```

**Options**:
- `--tier`: Filter by asset tier (TIER1/TIER2/TIER3/TIER4/ALL)
- `--asset`: Filter by specific asset ticker (e.g., BTC, ETH)
- `--interval`: Filter by specific interval in minutes (e.g., 60, 1440)
- `--yes`, `-y`: Auto-confirm all backfills without prompting
- `--dry-run`: Only detect gaps, don't backfill
- `--show-unfillable-only`: Only show gaps beyond 720-candle limit
- `--export-unfillable`: Export unfillable gaps to CSV file

**Examples**:
```bash
# Detect all gaps for TIER1 assets
python manage.py backfill_kraken_gaps --tier TIER1

# Detect and auto-backfill gaps for specific interval
python manage.py backfill_kraken_gaps --tier TIER1 --interval 1440 --yes

# Dry run to see what gaps exist
python manage.py backfill_kraken_gaps --tier TIER1 --dry-run

# Backfill specific asset
python manage.py backfill_kraken_gaps --asset BTC --interval 60

# Show only gaps that can't be filled by API
python manage.py backfill_kraken_gaps --tier TIER1 --show-unfillable-only

# Export unfillable gaps to CSV for manual handling
python manage.py backfill_kraken_gaps --tier TIER1 --export-unfillable gaps.csv
```

**Key Features**:

**Gap Detection**:
- **Missing Days**: Identifies days with no data in continuous sequence
- **Missing Intervals**: Detects incomplete data within days (e.g., missing hours)
- **Comprehensive Scanning**: Checks all asset/interval combinations in QuestDB

**720-Candle API Limitation**:
Kraken's REST API only returns the last 720 candles, which means:
- **Daily (1440 min)**: ~2 years from today
- **Hourly (60 min)**: 30 days from today
- **5-minute**: ~2.5 days from today

Gaps older than these limits **cannot** be filled via API and require CSV export from Kraken.

**Gap Classification**:
- **API-Fillable**: Gaps within 720-candle limit (can backfill now)
- **Unfillable**: Gaps beyond 720-candle limit (require CSV or alternative source)

**Interactive Mode**:
- Displays two separate reports: fillable vs unfillable gaps
- Shows gap summary: start date, end date, missing candle count, days from today
- Prompts for confirmation before backfilling (unless `--yes` flag used)
- Tracks success/failure per gap with error messages

**High-Performance Ingestion**:
- Uses QuestDB ILP (Influx Line Protocol) for fast writes
- Idempotent: QuestDB deduplication enabled (migration 0003) - safe to re-run, no duplicates
- Rate limiting: 1 second between API requests (conservative)

**CSV Export Format** (when using `--export-unfillable`):
```csv
asset_ticker,tier,interval_minutes,gap_start,gap_end,missing_candles,candles_from_today,overflow_candles
SOL,TIER1,1440,2022-03-01,2022-03-15,15,1076,356
XRP,TIER1,60,2024-10-05,2024-10-10,144,912,192
```

**Common Use Cases**:

1. **Regular Gap Checks**:
   ```bash
   # Weekly check for TIER1 assets
   python manage.py backfill_kraken_gaps --tier TIER1
   ```

2. **After Bulk Ingestion**:
   ```bash
   # Check for any missed data after bulk CSV ingestion
   python manage.py backfill_kraken_gaps --tier TIER1 --tier TIER2
   ```

3. **Specific Asset Maintenance**:
   ```bash
   # Check and fill gaps for specific asset
   python manage.py backfill_kraken_gaps --asset BTC --yes
   ```

4. **Gap Analysis**:
   ```bash
   # Generate report of all gaps
   python manage.py backfill_kraken_gaps --dry-run --export-unfillable analysis.csv
   ```

5. **Old Data Identification**:
   ```bash
   # Find gaps that need CSV export
   python manage.py backfill_kraken_gaps --show-unfillable-only
   ```

**When to Use**:
- After initial CSV bulk ingestion to fill recent gaps
- Regular maintenance to catch missed data
- Recovery from data collection outages
- Identifying data that needs CSV export

**When NOT to Use**:
- For gaps older than 720 candles (use CSV export instead)
- Initial bulk historical load (use `ingest_sequential` with CSV files)
- Real-time data streaming (use WebSocket or scheduled polling)

---

## Kraken OHLCV Ingestion

Comprehensive guide for ingesting historical OHLCV (Open, High, Low, Close, Volume) data from Kraken CSV files into QuestDB.

### Overview

The Kraken OHLCV ingestion system provides fast, efficient import of historical candlestick data from Kraken's CSV exports into QuestDB for time-series analysis.

### Key Features

- **High Performance**: QuestDB ILP (InfluxDB Line Protocol) ingestion at 50K-100K records/sec
- **Tier Filtering**: Process only specific asset tiers (TIER1-4)
- **Interval Filtering**: Filter by time intervals (e.g., 1h, 1d)
- **Automatic Asset Creation**: Assets auto-created with tier classification
- **Progress Tracking**: Real-time progress with ETA
- **Error Handling**: Continue processing on errors, move completed files

### Architecture

```
Kraken CSV Files → SequentialIngestor → QuestDB ILP → assetprice table
                   ↓
              Asset Creation (PostgreSQL)
```

### CSV Format

#### Kraken OHLCV CSV Format

**Columns (in order):**

| Index | Field | Type | Description |
|-------|-------|------|-------------|
| 0 | timestamp | Unix timestamp | Candle open time |
| 1 | open | Decimal | Opening price |
| 2 | high | Decimal | Highest price |
| 3 | low | Decimal | Lowest price |
| 4 | close | Decimal | Closing price |
| 5 | volume | Decimal | Trading volume |
| 6 | trade_count | Integer | Number of trades (optional) |

**Example CSV:**
```csv
1609459200,29000.5,29500.0,28900.0,29200.0,125.5,1523
1609462800,29200.0,29800.0,29100.0,29750.0,210.3,2105
1609466400,29750.0,30100.0,29700.0,30000.0,305.8,2891
```

**Notes:**
- No header row expected (automatically detected and skipped if present)
- Timestamps are Unix epoch seconds (UTC)
- Empty values allowed for volume and trade_count

### File Organization

**Expected Directory Structure:**
```
feefifofunds/data/kraken/Kraken_OHLCVT/
├── XXBTZUSD_60.csv      # BTC/USD 1-hour candles
├── ETHUSD_1440.csv      # ETH/USD daily candles
├── SOLUSD_5.csv         # SOL/USD 5-minute candles
└── ...
```

**Filename Format:** `{PAIR}_{INTERVAL}.csv`

**After Ingestion (Moved Automatically):**
```
feefifofunds/data/kraken/ingested/ohlcv/
├── XXBTZUSD_60.csv
├── ETHUSD_1440.csv
└── ...
```

### Performance

**Ingestion Speed:**
- **Small files** (<1 MB): 10K-30K records/sec
- **Medium files** (1-10 MB): 50K-80K records/sec
- **Large files** (>10 MB): 80K-120K records/sec

**Example:**
```
Total completed: 234/234 files
Total records: 18,523,456
Average speed: 72,341 records/second
```

**Performance Factors:**
- Network latency to QuestDB
- QuestDB server configuration (commit intervals, WAL settings)
- File size (larger files have better throughput)
- Concurrent writes (run one ingestion at a time for best performance)

**QuestDB Configuration:**
Optimal settings in `server.conf`:
```properties
# Commit interval for ILP
line.tcp.commit.interval.default=2000

# Maintenance job interval
line.tcp.maintenance.job.interval=5000
```

---

## Celery Automated Tasks

Automated tasks for maintaining Kraken OHLCV data using Celery and Celery Beat. These tasks keep your data current by automatically backfilling gaps and monitoring data quality.

### Available Tasks

#### 1. Incremental Gap Backfill (`backfill_gaps_incremental`)

**Purpose:** Automatically backfill gaps from the last saved data point to now for all assets in a tier.

**How it works:**
1. Finds the last data point for each asset/interval
2. Calculates gap from last data point to now
3. Backfills via Kraken API (if within 720-candle limit)
4. Creates `GapRecord` entries for tracking
5. Logs unfillable gaps (>720 candles) for manual CSV download

**Parameters:**
- `tier` (str): Asset tier to process - `TIER1`, `TIER2`, `TIER3`, `TIER4`, or `ALL` (default: `TIER1`)
- `intervals` (List[int]): Interval minutes to process (default: `[60, 1440]`)
- `lookback_days` (int): Only process assets with data within last N days (default: `7`)
- `max_gaps_per_asset` (int): Maximum gaps to fill per asset (default: `10`)

**Returns:** Summary dict with statistics:
```python
{
    "task_id": "abc-123",
    "tier": "TIER1",
    "intervals": [60, 1440],
    "assets_processed": 20,
    "gaps_detected": 5,
    "gaps_filled": 4,
    "gaps_unfillable": 1,
    "gaps_failed": 0,
    "total_candles_filled": 240,
    "errors": []
}
```

**Example Usage:**
```python
# Trigger manually via Django shell
from feefifofunds.tasks import backfill_gaps_incremental
result = backfill_gaps_incremental.delay(tier='TIER1', intervals=[60, 1440])

# Check result
print(result.get())
```

---

#### 2. Cleanup Old Gap Records (`cleanup_old_gap_records`)

**Purpose:** Clean up old resolved gap records to prevent database bloat.

**How it works:**
- Deletes `FILLED` gaps older than N days
- Deletes `FAILED` gaps older than N days (gives time for retry)
- Keeps `UNFILLABLE` gaps indefinitely (documentation of missing CSV files)

**Parameters:**
- `days` (int): Delete filled/failed gaps older than this many days (default: `90`)

**Returns:**
```python
{
    "filled_deleted": 123,
    "failed_deleted": 5
}
```

---

#### 3. Data Completeness Report (`report_data_completeness`)

**Purpose:** Generate and log data completeness metrics for monitoring.

**How it works:**
- Counts gaps by status (fillable vs unfillable)
- Calculates completeness percentage
- Logs summary to application logs

**Parameters:**
- `tier` (str): Asset tier to report on (default: `TIER1`)
- `intervals` (List[int]): Intervals to report on (default: `[60, 1440]`)

**Returns:**
```python
{
    "tier": "TIER1",
    "total_assets": 20,
    "assets_with_gaps": 2,
    "completeness_pct": 90.0,
    "intervals": {
        60: {
            "fillable_gaps": 3,
            "unfillable_gaps": 1,
            "total_gaps": 4
        },
        1440: {
            "fillable_gaps": 0,
            "unfillable_gaps": 0,
            "total_gaps": 0
        }
    }
}
```

---

#### 4. Validate Recent Data (`validate_recent_data`)

**Purpose:** Alert if critical assets are missing recent data (monitoring/alerting).

**How it works:**
- Checks TIER1 and TIER2 assets for recent data
- Identifies assets with stale data (older than N hours)
- Logs warnings for investigation

**Parameters:**
- `hours` (int): Alert if no data within last N hours (default: `24`)

**Returns:**
```python
{
    "assets_checked": 50,
    "interval_minutes": 1440,
    "assets_missing_data": [
        {
            "ticker": "XBTUSD",
            "tier": "TIER1",
            "last_timestamp": "2024-12-30T00:00:00",
            "hours_behind": 48
        }
    ]
}
```

---

### Complete Celery Beat Configuration

Add this to your `config/settings.py` or `config/celery.py`:

```python
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    # Daily incremental backfill for TIER1 (most critical)
    'backfill-tier1-daily': {
        'task': 'feefifofunds.backfill_gaps_incremental',
        'schedule': crontab(hour=2, minute=0),  # 2 AM daily
        'kwargs': {
            'tier': 'TIER1',
            'intervals': [60, 1440],  # Hourly and daily
            'lookback_days': 7,
            'max_gaps_per_asset': 10
        }
    },

    # Daily incremental backfill for TIER2
    'backfill-tier2-daily': {
        'task': 'feefifofunds.backfill_gaps_incremental',
        'schedule': crontab(hour=3, minute=0),  # 3 AM daily
        'kwargs': {
            'tier': 'TIER2',
            'intervals': [1440],  # Daily only
            'lookback_days': 7
        }
    },

    # Weekly cleanup of old gap records
    'cleanup-gap-records-weekly': {
        'task': 'feefifofunds.cleanup_old_gap_records',
        'schedule': crontab(day_of_week='sunday', hour=4, minute=0),
        'kwargs': {'days': 90}
    },

    # Daily completeness report
    'completeness-report-daily': {
        'task': 'feefifofunds.report_data_completeness',
        'schedule': crontab(hour=8, minute=0),  # 8 AM daily
        'kwargs': {'tier': 'TIER1', 'intervals': [60, 1440]}
    },

    # Hourly validation (monitoring)
    'validate-data-hourly': {
        'task': 'feefifofunds.validate_recent_data',
        'schedule': crontab(minute=0),  # Every hour
        'kwargs': {'hours': 24}
    },
}
```

---

### Manual Task Execution

#### Via Django Shell

```python
# Start Django shell
python manage.py shell

# Import tasks
from feefifofunds.tasks import (
    backfill_gaps_incremental,
    cleanup_old_gap_records,
    report_data_completeness,
    validate_recent_data
)

# Execute task asynchronously (returns AsyncResult)
result = backfill_gaps_incremental.delay(tier='TIER1', intervals=[60, 1440])

# Get task ID
print(f"Task ID: {result.id}")

# Wait for result (blocking)
summary = result.get(timeout=3600)  # 1 hour timeout
print(summary)

# Check task status
print(f"Status: {result.status}")  # PENDING, STARTED, SUCCESS, FAILURE
print(f"Ready: {result.ready()}")  # True if completed
```

---

#### Via Celery CLI

```bash
# Trigger task via CLI
celery -A config call feefifofunds.backfill_gaps_incremental \
    --kwargs='{"tier": "TIER1", "intervals": [60, 1440]}'

# Inspect scheduled tasks
celery -A config inspect scheduled

# Inspect active tasks
celery -A config inspect active

# Purge all tasks
celery -A config purge
```

---

### Production Deployment

#### Celery Worker Configuration

```bash
# Start Celery worker
celery -A config worker \
    --loglevel=info \
    --logfile=logs/celery.log \
    --concurrency=2 \
    --max-tasks-per-child=100

# Start Celery Beat (scheduler)
celery -A config beat \
    --loglevel=info \
    --logfile=logs/celery-beat.log \
    --pidfile=celery-beat.pid

# Or combined (development only)
celery -A config worker --beat --loglevel=info
```

---

#### Systemd Service (Production)

```ini
# /etc/systemd/system/celery-feefifofunds.service
[Unit]
Description=Celery Worker - FeeFiFoFunds
After=network.target redis.target

[Service]
Type=forking
User=www-data
Group=www-data
WorkingDirectory=/app
ExecStart=/app/venv/bin/celery -A config worker \
    --loglevel=info \
    --logfile=/app/logs/celery.log \
    --pidfile=/app/run/celery.pid \
    --concurrency=2
ExecStop=/app/venv/bin/celery -A config control shutdown
Restart=always

[Install]
WantedBy=multi-user.target
```

```ini
# /etc/systemd/system/celerybeat-feefifofunds.service
[Unit]
Description=Celery Beat - FeeFiFoFunds Scheduler
After=network.target redis.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/app
ExecStart=/app/venv/bin/celery -A config beat \
    --loglevel=info \
    --logfile=/app/logs/celery-beat.log \
    --pidfile=/app/run/celery-beat.pid
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start services
sudo systemctl daemon-reload
sudo systemctl enable celery-feefifofunds
sudo systemctl enable celerybeat-feefifofunds
sudo systemctl start celery-feefifofunds
sudo systemctl start celerybeat-feefifofunds

# Check status
sudo systemctl status celery-feefifofunds
sudo systemctl status celerybeat-feefifofunds
```

---

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

---

### Full Kraken OHLCV Ingestion

```bash
# Ingest all OHLCV data (all tiers, all intervals)
python manage.py ingest_sequential --yes

# Ingest specific intervals only
python manage.py ingest_sequential --intervals 60,1440 --yes
```

---

### Incremental Updates

```bash
# Ingest only new TIER1 OHLCV data (daily interval)
python manage.py ingest_sequential --tier TIER1 --intervals 1440 --yes

# Backfill recent data from Massive.com
python manage.py backfill_prices --source massive --days 7 --all --grouped
```

---

### Data Recovery

```bash
# Drop and recreate QuestDB tables
python manage.py setup_questdb_schema --drop

# Re-ingest all data
python manage.py ingest_sequential --yes
```

---

## Troubleshooting

### Common Issues

#### 1. No files found
**Error:**
```
⚠️  No OHLCV files found matching filters (tier=TIER1)
```

**Solution:**
- Verify CSV files exist in `feefifofunds/data/kraken/Kraken_OHLCVT/`
- Check filename format: `{PAIR}_{INTERVAL}.csv`
- Verify tier filter matches assets (use `--tier ALL` to test)

---

#### 2. QuestDB connection failed
**Error:**
```
❌ Error: could not connect to server
```

**Solution:**
- Verify `QUESTDB_URL` in `.env`: `postgresql://admin:password@host:8812/qdb`
- Check QuestDB is running: `docker ps | grep questdb`
- Test connection: `psql $QUESTDB_URL -c "SELECT 1"`

---

#### 3. Invalid filename format
**Error:**
```
Invalid OHLCV filename: BTCUSD.csv
```

**Solution:**
- Rename file to include interval: `BTCUSD_1440.csv`
- Ensure format: `{PAIR}_{INTERVAL}.csv`

---

#### 4. Files already processed

If files were moved to `ingested/` but need reprocessing:

```bash
# Move files back to source directory
mv feefifofunds/data/kraken/ingested/ohlcv/*.csv feefifofunds/data/kraken/Kraken_OHLCVT/

# Re-run ingestion
python manage.py ingest_sequential --tier TIER1 --yes
```

---

#### 5. Task Not Running

```bash
# 1. Check Celery worker is running
ps aux | grep celery

# 2. Check Celery Beat is running
ps aux | grep "celery beat"

# 3. Check task is registered
celery -A config inspect registered | grep feefifofunds

# 4. Check Beat schedule
celery -A config inspect scheduled
```

---

#### 6. Task Running But No Results

```python
# Check task in Django logs
tail -f logs/django.log | grep feefifofunds

# Check GapRecords are being created
from feefifofunds.models import GapRecord
recent = GapRecord.objects.filter(
    detected_at__gte=datetime.now() - timedelta(hours=24)
)
print(f"Recent gaps: {recent.count()}")
```

---

### Performance Optimization

**Slow ingestion speed:**

1. **Check QuestDB server load:**
   ```bash
   docker stats questdb
   ```

2. **Verify network latency:**
   ```bash
   ping <questdb-host>
   ```

3. **Run one ingestion at a time** (avoid concurrent writes)

4. **Use interval filtering** to process smaller batches:
   ```bash
   # Process daily candles first (fewer records)
   python manage.py ingest_sequential --intervals 1440 --yes

   # Then process 1-hour candles
   python manage.py ingest_sequential --intervals 60 --yes
   ```

---

## Related Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture and design
- [INTEGRATIONS.md](INTEGRATIONS.md) - Data source integrations
- [SETUP.md](SETUP.md) - Development environment setup
- [README.md](README.md) - Overview and quick start
