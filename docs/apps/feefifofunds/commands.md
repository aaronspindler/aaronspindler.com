# FeeFiFoFunds Management Commands

Complete reference for all FeeFiFoFunds management commands including database setup, asset management, and data ingestion from multiple sources.

## Commands

### check_questdb_version

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

**Output Example**:
```
🔍 Checking QuestDB Version
────────────────────────────────────────────────────────────

📊 QuestDB Version: 7.4.3

📋 Feature Compatibility:
   ✅ DEDUP support: YES (7.3+ required)
   ✅ Ready for deduplication migrations

────────────────────────────────────────────────────────────

✅ QuestDB version is compatible!

Next steps:
  1. Fake-apply schema migration: python manage.py migrate feefifofunds 0003 --fake
  2. Apply DEDUP migration: python manage.py migrate feefifofunds
```

---

### QuestDB Migrations

QuestDB schema is managed through Django migrations (introduced in migration 0003+).

**Initial Setup** (for existing databases):
```bash
# 1. Check QuestDB version (must be >= 7.3)
python manage.py check_questdb_version

# 2. Fake-apply initial schema migration (table already exists)
python manage.py migrate feefifofunds 0003 --fake

# 3. Apply DEDUP migration (actually runs ALTER TABLE)
python manage.py migrate feefifofunds
```

**New Environments**:
```bash
# Run all migrations (creates table with DEDUP enabled)
python manage.py migrate feefifofunds
```

**Migrations**:
- **0003_create_questdb_assetprice_table**: Creates `assetprice` table schema
  - SYMBOL types for quote_currency and source
  - PARTITION BY DAY for optimal performance
  - Designated timestamp column
- **0004_enable_dedup_assetprice**: Enables deduplication with UPSERT KEYS
  - Keys: `(time, asset_id, interval_minutes, source)`
  - Ensures idempotent re-ingestion (safe to re-run ingestion)
  - Upsert behavior: newer data overwrites older on conflict

**Rollback**:
```bash
# Disable deduplication (rollback 0004)
python manage.py migrate feefifofunds 0003

# Remove table (rollback 0003 - DANGEROUS)
python manage.py migrate feefifofunds 0002
```

**Important Notes**:
- AssetPrice model uses `managed=False` in Django
- These migrations only apply to the `questdb` database connection
- Deduplication requires QuestDB 7.3+ (check with `check_questdb_version`)
- With DEDUP enabled, re-ingesting data is safe (no duplicates created)

---

### create_asset

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

### ingest_sequential

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
- **Idempotent**: QuestDB deduplication enabled (migration 0004) - safe to re-run, no duplicates
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

### load_prices

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

**What It Does**:
1. Validates asset exists in database
2. Fetches historical OHLCV data from API
3. Stores data in AssetPrice model (QuestDB)
4. Displays progress with created/updated counts

**When to Use**:
- Loading small amounts of recent data
- Testing API connectivity
- Quick data updates for specific assets

**Requirements**:
- Asset must exist in database (create with `create_asset` command first)
- API keys: `MASSIVE_API_KEY` or `FINNHUB_API_KEY` environment variables

---

### backfill_prices

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

**Progress Display**:
- Real-time progress with percentage and ETA
- Shows created/updated counts per asset
- Failed assets listed at end with error messages

**When to Use**:
- Initial historical data load for new assets
- Filling gaps in existing data
- Bulk backfills (use --grouped for Massive.com)
- Recovery after data loss

**Requirements**:
- Assets must exist in database (created automatically by ingest_sequential or manually with create_asset)
- API keys: `MASSIVE_API_KEY` or `FINNHUB_API_KEY` environment variables

---

### backfill_kraken_gaps

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
- Idempotent: QuestDB deduplication enabled (migration 0004) - safe to re-run, no duplicates
- Rate limiting: 1 second between API requests (conservative)

**Output Example**:
```
═══════════════════════════════════════════════════════════
Kraken Gap Detection Report
═══════════════════════════════════════════════════════════

Scanning 15 assets for gaps...

───────────────────────────────────────────────────────────
📊 API-FILLABLE GAPS (within 720-candle limit)
───────────────────────────────────────────────────────────

BTC (TIER1) - 1440 min interval:
  ✓ 2024-11-01 → 2024-11-03 (3 days, 3 candles)
    └─ 9 candles from today (limit: 720) ✓

ETH (TIER1) - 60 min interval:
  ✓ 2025-01-10 08:00 → 2025-01-10 14:00 (6 hours, 6 candles)
    └─ 50 candles from today (limit: 720) ✓

Summary: 23 fillable gaps, 1,245 total candles to fetch

───────────────────────────────────────────────────────────
❌ UNFILLABLE GAPS (beyond 720-candle limit)
───────────────────────────────────────────────────────────

SOL (TIER1) - 1440 min interval:
  ✗ 2022-03-01 → 2022-03-15 (15 days, 15 candles)
    └─ 1,076 candles from today (limit: 720) ✗
    └─ TOO OLD by 356 candles (356 days)
    → ACTION: Download CSV from Kraken for 2022-03-01 to 2022-03-15

Summary: 4 unfillable gaps
  → Requires CSV export or alternative data source
  → Kraken CSV export: https://www.kraken.com/features/api#ohlc-data

═══════════════════════════════════════════════════════════

Proceed with backfilling 23 API-available gaps? [y/N]:
```

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

**Requirements**:
- Assets must exist in PostgreSQL database
- Asset price data must exist in QuestDB (from previous ingestion)
- Kraken API accessible (no API key required for public OHLC endpoint)
- QuestDB ILP port (9009) accessible

**Error Handling**:
- Continues processing on errors by default
- Failed gaps listed at end with error messages
- Common errors:
  - Unknown asset pair (check ticker mapping)
  - Rate limit exceeded (automatic 1-second delay)
  - Network timeout (automatic retry with backoff)

**Performance**:
- Gap detection: ~1 second per 10 assets
- API fetching: 1 request/second (rate limited)
- QuestDB writes: 50K-100K records/second via ILP
- Example: 20 gaps × 30 candles each = ~20 seconds

**Data Quality**:
- Excludes Kraken's incomplete last candle
- Validates OHLC data format
- Handles missing volume/trade count gracefully
- Idempotent: QuestDB deduplication (migration 0004) prevents duplicates

**Related Commands**:
- `ingest_sequential`: For bulk CSV ingestion (preferred for historical data)
- `check_questdb_version`: Verify QuestDB version for DEDUP support
- `backfill_prices`: For external API sources (Massive.com, Finnhub)

---



## Related Documentation

- [FeeFiFoFunds Overview](overview.md) - Architecture and data models
- [Kraken OHLCV Ingestion](ohlcv-ingestion.md) - CSV data ingestion details
- [Data Sources](data-sources.md) - API integration framework
- [QuestDB Setup](questdb-setup.md) - Database configuration and tuning
- [Development Guide](development.md) - Local setup and testing
- [Commands Index](../../commands/README.md) - All management commands
