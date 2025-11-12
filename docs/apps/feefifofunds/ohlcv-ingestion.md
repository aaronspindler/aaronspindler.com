# Kraken OHLCV Data Ingestion

Comprehensive guide for ingesting historical OHLCV (Open, High, Low, Close, Volume) data from Kraken CSV files into QuestDB.

## Table of Contents

- [Overview](#overview)
- [Data Model](#data-model)
- [Setup](#setup)
- [Ingestion Process](#ingestion-process)
- [CSV Format](#csv-format)
- [Performance](#performance)
- [Troubleshooting](#troubleshooting)

## Overview

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

## Data Model

### AssetPrice Model

The OHLCV data is stored in the `assetprice` table in QuestDB:

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

**Key Fields:**
- `asset_id`: Foreign key to Asset (PostgreSQL)
- `time`: Designated timestamp column (partitioned by day)
- `open`, `high`, `low`, `close`: OHLC prices
- `volume`: Trading volume
- `interval_minutes`: Candlestick interval (1, 5, 15, 60, 240, 1440, etc.)
- `trade_count`: Number of trades in interval
- `quote_currency`: SYMBOL type for efficient storage (USD, EUR, etc.)
- `source`: SYMBOL type, always "kraken" for Kraken data

## Setup

### 1. QuestDB Schema

Create the QuestDB table:

```bash
python manage.py setup_questdb_schema
```

This creates the `assetprice` table with optimized schema.

### 2. Prepare Kraken Data

Download historical data from Kraken and place CSV files in:

```
feefifofunds/data/kraken/Kraken_OHLCVT/
```

**Expected Filename Format:**
```
{PAIR}_{INTERVAL}.csv

Examples:
XXBTZUSD_60.csv      # BTC/USD 1-hour candles
ETHUSD_1440.csv      # ETH/USD daily candles
SOLUSD_5.csv         # SOL/USD 5-minute candles
```

### 3. Verify PostgreSQL Assets

Ensure base Assets exist (or let ingestion auto-create them):

```bash
python manage.py shell
>>> from feefifofunds.models import Asset
>>> Asset.objects.filter(category=Asset.Category.CRYPTO).count()
```

## Ingestion Process

### Sequential Ingestion (Recommended)

The `ingest_sequential` command provides fast, reliable OHLCV import:

```bash
python manage.py ingest_sequential [OPTIONS]
```

**Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--tier` | Filter by tier (TIER1/2/3/4/ALL) | ALL |
| `--intervals` | Comma-separated intervals in minutes | All |
| `--yes`, `-y` | Skip confirmation prompts | False |
| `--database` | Database to use | questdb |
| `--data-dir` | Custom data directory | `feefifofunds/data/kraken` |
| `--stop-on-error` | Stop on first error | False (continue) |

### Usage Examples

**Ingest Tier 1 Assets (1-hour and daily candles):**
```bash
python manage.py ingest_sequential --tier TIER1 --intervals 60,1440 --yes
```

**Ingest All Intervals for All Tiers:**
```bash
python manage.py ingest_sequential --tier ALL --yes
```

**Test with Custom Data Directory:**
```bash
python manage.py ingest_sequential --data-dir /path/to/test/data --tier TIER1
```

### Ingestion Flow

1. **Discover Files**: Scan directory for CSV files matching filters
2. **Tier Breakdown**: Calculate and display asset tier distribution
3. **Confirmation**: Show summary and request confirmation (unless --yes)
4. **Asset Cache**: Load existing assets into memory
5. **ILP Connection**: Connect to QuestDB ILP endpoint
6. **Process Files**: Sequentially process each file with progress tracking
7. **Move Files**: Move completed files to `ingested/ohlcv/` directory
8. **Report**: Display final statistics and performance metrics

### File Processing

For each OHLCV file:

1. Parse filename to extract pair and interval
2. Use `KrakenPairParser` to extract base ticker and quote currency
3. Get or create Asset (auto-creates if missing, with tier classification)
4. Stream CSV records and send via QuestDB ILP
5. Move file to `ingested/ohlcv/` on success

### Progress Display

```
📊 FeeFiFoFunds Sequential Ingestion
════════════════════════════════════════════════════════════════
Tier:     TIER1
Database: questdb

📁 Files to process: 234
   File type: OHLCV
   Tier filter: TIER1
   Interval filter: 60, 1440 minutes

📊 Tier breakdown:
   TIER1: 234 files

[████████████████░░░░] 80% | 187/234 files | 18.5M records | ETA: 2m 15s
Current: SOLUSD_60.csv (125 KB) → 8,945 records
```

## CSV Format

### Kraken OHLCV CSV Format

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

## Performance

### Ingestion Speed

**Typical Performance (QuestDB ILP):**
- **Small files** (<1 MB): 10K-30K records/sec
- **Medium files** (1-10 MB): 50K-80K records/sec
- **Large files** (>10 MB): 80K-120K records/sec

**Example:**
```
Total completed: 234/234 files
Total records: 18,523,456
Average speed: 72,341 records/second
```

### Performance Factors

**Factors Affecting Speed:**
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

### Asset Tier Classification

Assets are automatically classified into tiers based on market cap/importance:

**TIER1** (Top 20 assets):
- BTC, ETH, USDT, USDC, BNB, XRP, ADA, DOGE, SOL, DOT, etc.

**TIER2** (Medium-cap, ~30 assets):
- UNI, XLM, ALGO, AAVE, FIL, NEAR, APT, GRT, etc.

**TIER3** (Small-cap, ~30 assets):
- 1INCH, CRV, BAT, ENJ, GALA, LRC, ZRX, etc.

**TIER4** (Default):
- All other cryptocurrencies

Classification is defined in `KrakenAssetCreator` class.

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

#### 2. QuestDB connection failed

**Error:**
```
❌ Error: could not connect to server
```

**Solution:**
- Verify `QUESTDB_URL` in `.env`: `postgresql://admin:password@host:8812/qdb`
- Check QuestDB is running: `docker ps | grep questdb`
- Test connection: `psql $QUESTDB_URL -c "SELECT 1"`

#### 3. Invalid filename format

**Error:**
```
Invalid OHLCV filename: BTCUSD.csv
```

**Solution:**
- Rename file to include interval: `BTCUSD_1440.csv`
- Ensure format: `{PAIR}_{INTERVAL}.csv`

#### 4. Files already processed

If files were moved to `ingested/` but need reprocessing:

```bash
# Move files back to source directory
mv feefifofunds/data/kraken/ingested/ohlcv/*.csv feefifofunds/data/kraken/Kraken_OHLCVT/

# Re-run ingestion
python manage.py ingest_sequential --tier TIER1 --yes
```

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

### Data Validation

**Verify ingestion:**

```bash
# Count records in QuestDB
python manage.py shell
>>> from django.db import connections
>>> with connections['questdb'].cursor() as c:
...     c.execute("SELECT COUNT(*) FROM assetprice WHERE source='kraken'")
...     print(c.fetchone()[0])
```

**Check specific asset:**

```python
from feefifofunds.models import Asset, AssetPrice

asset = Asset.objects.get(ticker='BTC')
count = AssetPrice.objects.using('questdb').filter(
    asset_id=asset.id,
    source='kraken'
).count()
print(f"BTC OHLCV records: {count:,}")
```

## Related Documentation

- [Commands Reference](commands.md) - All management commands
- [Development Guide](development.md) - Development workflows
- [Overview](overview.md) - Architecture and data models
- [README](README.md) - Main FeeFiFoFunds documentation
