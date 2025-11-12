# FeeFiFoFunds Management Commands

Complete reference for all FeeFiFoFunds management commands including database setup, asset management, and data ingestion from multiple sources.

## Commands

### setup_questdb_schema

Initialize QuestDB schema for AssetPrice time-series table.

**Usage**:
```bash
python manage.py setup_questdb_schema
```

**Options**:
- `--database`: Database to use (default: questdb)
- `--drop`: Drop existing table before creating (DANGEROUS)

**Examples**:
```bash
# Initialize schema (safe, uses IF NOT EXISTS)
python manage.py setup_questdb_schema

# Drop and recreate table (CAREFUL - deletes all data!)
python manage.py setup_questdb_schema --drop

# Use different database connection
python manage.py setup_questdb_schema --database custom_questdb
```

**What It Does**:
1. Creates `assetprice` table with optimized QuestDB schema
   - SYMBOL types for quote_currency and source
   - PARTITION BY DAY for optimal performance
   - Designated timestamp column
2. Verifies table was created successfully

**When to Run**:
- Initial project setup
- After QuestDB instance reset
- When switching to a new QuestDB instance

**Note**:
- AssetPrice model uses `managed=False` in Django
- Django migrations do NOT apply to this QuestDB table
- Schema must be created manually with this command

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
- **Idempotent**: QuestDB handles duplicate timestamps automatically, safe to re-run
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



## Related Documentation

- [FeeFiFoFunds Overview](overview.md) - Architecture and data models
- [Kraken OHLCV Ingestion](ohlcv-ingestion.md) - CSV data ingestion details
- [Data Sources](data-sources.md) - API integration framework
- [QuestDB Setup](questdb-setup.md) - Database configuration and tuning
- [Development Guide](development.md) - Local setup and testing
- [Commands Index](../../commands/README.md) - All management commands
