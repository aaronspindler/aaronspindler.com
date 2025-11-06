# Kraken Historical Data Ingestion

Comprehensive system for ingesting Kraken historical trading data into the FeeFiFoFunds database.

## Overview

The Kraken data ingestion system supports importing two types of historical data:
- **OHLCVT Data** (candles): Aggregated open/high/low/close/volume/trades data at various time intervals
- **Trading History** (ticks): Individual trade records with timestamp, price, and volume

## Data Models

### AssetPrice (Enhanced)

Enhanced to support multiple timeframes and trade counts:

```python
class AssetPrice(models.Model):
    asset = ForeignKey(Asset)
    timestamp = DateTimeField()  # UTC
    open = DecimalField(max_digits=20, decimal_places=8)
    high = DecimalField(max_digits=20, decimal_places=8)
    low = DecimalField(max_digits=20, decimal_places=8)
    close = DecimalField(max_digits=20, decimal_places=8)
    volume = DecimalField(max_digits=20, decimal_places=2, null=True)
    interval_minutes = SmallIntegerField(null=True, db_index=True)  # NEW
    trade_count = IntegerField(null=True)  # NEW
    source = CharField(max_length=50)

    # Unique constraint: (asset, timestamp, source, interval_minutes)
```

**New Fields:**
- `interval_minutes`: Time interval in minutes (1, 5, 15, 30, 60, 240, 720, 1440)
- `trade_count`: Number of trades during the interval (from Kraken OHLCVT data)

### Trade (New Model)

Individual trade records:

```python
class Trade(models.Model):
    asset = ForeignKey(Asset)
    timestamp = DateTimeField(db_index=True)  # UTC, exact trade time
    price = DecimalField(max_digits=20, decimal_places=8)
    volume = DecimalField(max_digits=20, decimal_places=8)
    source = CharField(max_length=50, default="kraken")

    # Unique constraint: (asset, timestamp, source)
```

## Management Commands

### ingest_kraken_ohlcv

Import Kraken OHLCV (candle) data from CSV files.

**Basic Usage:**
```bash
# Import daily data only
python manage.py ingest_kraken_ohlcv --intervals 1440

# Import hourly and daily
python manage.py ingest_kraken_ohlcv --intervals 60,1440

# Import all intervals
python manage.py ingest_kraken_ohlcv --intervals 1,5,15,30,60,240,720,1440

# Import specific pair
python manage.py ingest_kraken_ohlcv --pair BTCUSD --intervals 1440
```

**Options:**
- `--intervals`: Comma-separated list (1,5,15,30,60,240,720,1440). Default: all
- `--pair`: Import specific trading pair only (e.g., BTCUSD)
- `--directory`: Custom data directory path
- `--batch-size`: Records per batch (default: 25,000)
- `--dry-run`: Preview without saving to database
- `--skip-existing`: Skip files where asset already has data for this interval
- `--drop-indexes`: Drop indexes before import, recreate after (faster for large imports)

**Performance Tips:**
- Use `--intervals 1440` for daily-only (fastest, most space-efficient)
- Use `--skip-existing` to avoid re-importing existing data
- Use `--drop-indexes` for initial large imports (significantly faster)
- Smaller intervals (1, 5 minutes) have the most data and take longest

**Example Output:**
```
📂 Found 8656 files to process
⚙️  Intervals: 1440 minutes
📦 Batch size: 25,000 records
✓ [1/8656] BTCUSD      1440m - +  1,800 | 0.0% | ⏱️  1.2s | ETA 2h 45m
✓ [2/8656] ETHUSD      1440m - +  1,600 | 0.0% | ⏱️  2.5s | ETA 2h 42m
...
✅ Complete: 8656/8656 files | +2,456,789 records created | ⊘ 0 skipped | ⏱️  2h 38m
```

### ingest_kraken_trades

Import Kraken trade history (tick data) from CSV files.

**Basic Usage:**
```bash
# Import all trading pairs
python manage.py ingest_kraken_trades

# Import specific pair
python manage.py ingest_kraken_trades --pair BTCUSD

# Test with limited records per file
python manage.py ingest_kraken_trades --pair BTCUSD --limit-per-file 10000
```

**Options:**
- `--pair`: Import specific trading pair only (e.g., BTCUSD)
- `--directory`: Custom data directory path
- `--batch-size`: Records per batch (default: 50,000, larger than OHLCV due to simpler records)
- `--dry-run`: Preview without saving to database
- `--skip-existing`: Skip files where asset already has trade data
- `--drop-indexes`: Drop indexes before import, recreate after (faster for large imports)
- `--limit-per-file`: Max records per file (useful for testing)

**Performance Tips:**
- Trades have higher volume (~200M records) than OHLCV (~millions)
- Always use `--drop-indexes` for full imports (major speed improvement)
- Consider importing trades only for specific pairs you need
- Use `--limit-per-file` for testing before full import

**Example Output:**
```
📂 Found 1119 files to process
📦 Batch size: 50,000 records
✓ [1/1119] BTCUSD      - +  245,678 | 0.1% | ⏱️  15.3s | ETA 4h 45m
✓ [2/1119] ETHUSD      - +  198,432 | 0.2% | ⏱️  28.1s | ETA 4h 32m
...
✅ Complete: 1119/1119 files | +203,456,789 records created | ⊘ 0 skipped | ⏱️  4h 28m
```

## Data Source

### Kraken CSV Format

**OHLCVT Files** (`feefifofunds/data/kraken/Kraken_OHLCVT/`):
- Filename format: `{PAIR}_{INTERVAL}.csv` (e.g., `BTCUSD_1440.csv`)
- Intervals: 1, 5, 15, 30, 60, 240, 720, 1440 minutes
- Columns: `timestamp,open,high,low,close,volume,trade_count`
- Timestamp: Unix epoch (seconds)
- 8,656 total files

**Trading History Files** (`feefifofunds/data/kraken/Kraken_Trading_History/`):
- Filename format: `{PAIR}.csv` (e.g., `BTCUSD.csv`)
- Columns: `timestamp,price,volume`
- Timestamp: Unix epoch (seconds)
- 1,119 total files
- ~182k trades per file average

### Supported Trading Pairs

- **Base assets**: 1,100+ cryptocurrencies (BTC, ETH, AAVE, ADA, etc.)
- **Quote currencies**: USD, EUR, GBP, JPY, CAD, CHF, AUD, AED, XBT, ETH, DAI, DOT, POL

**Kraken Ticker Mappings:**
- `XBT` → `BTC` (Kraken uses XBT for Bitcoin)
- `ZEUR` → `EUR`
- `ZUSD` → `USD`
- Similar Z-prefix mappings for other fiat currencies

## Implementation Details

### Pair Parsing

`KrakenPairParser` extracts base asset and quote currency:

```python
from feefifofunds.services.kraken import KrakenPairParser

base, quote = KrakenPairParser.parse_pair("BTCUSD")  # ("BTC", "USD")
base, quote = KrakenPairParser.parse_pair("AAVEXBT")  # ("AAVE", "XBT")
base, quote = KrakenPairParser.parse_pair("1INCHEUR")  # ("1INCH", "EUR")
```

### Asset Auto-Creation

Assets are automatically created during import:

```python
from feefifofunds.services.kraken import KrakenAssetCreator

creator = KrakenAssetCreator()
asset = creator.get_or_create_asset("BTC", "USD")
# Creates Asset(ticker="BTC", name="BTC", category=CRYPTO, quote_currency="USD")
```

**Caching:** Asset lookups are cached in memory during import for performance.

### CSV Parsing

Memory-efficient streaming parsers:

```python
from feefifofunds.services.kraken import parse_ohlcv_csv, parse_trade_csv

# Stream OHLCV data
for record in parse_ohlcv_csv("path/to/BTCUSD_1440.csv", interval_minutes=1440):
    # record = {timestamp, open, high, low, close, volume, trade_count, interval_minutes}
    pass

# Stream trade data
for record in parse_trade_csv("path/to/BTCUSD.csv"):
    # record = {timestamp, price, volume}
    pass
```

### Bulk Insertion

Optimized batch operations:

```python
from feefifofunds.services.kraken import BulkInsertHelper

# Batch insert prices (25k batch size)
BulkInsertHelper.bulk_create_prices(price_objects, batch_size=25000)

# Batch insert trades (50k batch size)
BulkInsertHelper.bulk_create_trades(trade_objects, batch_size=50000)
```

## Database Optimizations

### Indexes

**AssetPrice:**
- `(asset_id, timestamp, interval_minutes)` - Primary query index
- `(asset_id, interval_minutes)` - Interval filtering
- `timestamp` - Time-based queries
- `source` - Source filtering
- `interval_minutes` - Interval filtering

**Trade:**
- `(asset_id, timestamp)` - Primary query index
- `timestamp` - Time-based queries
- `asset_id` - Asset filtering
- `source` - Source filtering

### Index Management

**Drop Before Import:**
```bash
python manage.py ingest_kraken_ohlcv --intervals 1440 --drop-indexes
```

This drops indexes before import and recreates them after, providing significant speed improvements for large imports.

**Manual Index Operations:**
```sql
-- Drop indexes
DROP INDEX IF EXISTS feefifofund_asset_i_b862eb_idx;
DROP INDEX IF EXISTS feefifofund_asset_i_48d942_idx;
-- (etc.)

-- Recreate indexes
CREATE INDEX feefifofund_asset_i_b862eb_idx ON feefifofunds_assetprice (asset_id, timestamp, interval_minutes);
-- (etc.)
```

### Unique Constraints

**AssetPrice:**
- `(asset, timestamp, source, interval_minutes)` - Prevents duplicate records across intervals

**Trade:**
- `(asset, timestamp, source)` - Prevents duplicate trade records

Both use `ignore_conflicts=True` in bulk_create for idempotent imports.

## Performance Benchmarks

Approximate ingestion speeds (on M1 Mac, PostgreSQL):

**OHLCV Data:**
- Without `--drop-indexes`: ~10,000-20,000 records/second
- With `--drop-indexes`: ~50,000-100,000 records/second
- Daily data only (1440m): ~1-2 hours for full dataset
- All intervals: ~8-12 hours for full dataset

**Trade Data:**
- Without `--drop-indexes`: ~15,000-25,000 records/second
- With `--drop-indexes`: ~100,000-150,000 records/second
- Full dataset: ~4-6 hours with index dropping
- Specific pairs: Minutes to hours depending on trade volume

**Database Size:**
- OHLCV (all intervals): ~5-10 GB
- OHLCV (daily only): ~500 MB - 1 GB
- Trades (all): ~50-100 GB
- Total with all data: ~100-150 GB

## Querying Examples

### Get Daily Prices for Asset

```python
from feefifofunds.models import Asset, AssetPrice

asset = Asset.objects.get(ticker="BTC")
daily_prices = AssetPrice.objects.filter(
    asset=asset,
    interval_minutes=1440,
    source="kraken"
).order_by("timestamp")

for price in daily_prices:
    print(f"{price.timestamp.date()}: ${price.close}")
```

### Get Intraday Prices

```python
from datetime import datetime, timedelta

asset = Asset.objects.get(ticker="ETH")
start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
end_date = start_date + timedelta(days=1)

hourly_prices = AssetPrice.objects.filter(
    asset=asset,
    interval_minutes=60,
    timestamp__gte=start_date,
    timestamp__lt=end_date,
    source="kraken"
).order_by("timestamp")
```

### Get Trades for Time Range

```python
from feefifofunds.models import Trade

asset = Asset.objects.get(ticker="BTC")
start_time = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
end_time = datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc)

trades = Trade.objects.filter(
    asset=asset,
    timestamp__gte=start_time,
    timestamp__lt=end_time,
    source="kraken"
).order_by("timestamp")

for trade in trades:
    print(f"{trade.timestamp}: ${trade.price} x {trade.volume}")
```

### Calculate VWAP from Trades

```python
from django.db.models import Sum, F

trades = Trade.objects.filter(
    asset=asset,
    timestamp__gte=start_time,
    timestamp__lt=end_time
)

total_volume = trades.aggregate(total=Sum("volume"))["total"]
vwap = trades.aggregate(
    vwap=Sum(F("price") * F("volume")) / total_volume
)["vwap"]
```

## Troubleshooting

### Import Failures

**Symptom:** Files failing to import with parse errors

**Solution:**
- Check CSV file format matches expected columns
- Verify file encoding is UTF-8
- Check for corrupted files (try opening in text editor)

### Slow Import Speed

**Symptom:** Import taking much longer than benchmarks

**Solution:**
- Use `--drop-indexes` flag for initial large imports
- Increase `--batch-size` (test with 50k or 100k)
- Check database is not under heavy load
- Verify sufficient disk space for database growth

### Duplicate Key Errors

**Symptom:** `IntegrityError` on unique constraint

**Solution:**
- The commands use `ignore_conflicts=True`, so this shouldn't occur
- If it does, check that unique constraints are correctly defined
- Verify AssetPrice has `(asset, timestamp, source, interval_minutes)` constraint

### Out of Memory

**Symptom:** Process killed or OOM errors

**Solution:**
- Reduce `--batch-size` to process smaller batches
- Import one pair at a time with `--pair` flag
- Use `--limit-per-file` for testing
- Close other applications to free memory

### Missing Assets

**Symptom:** Assets not being created during import

**Solution:**
- Assets are auto-created, so this should not occur
- Check KrakenPairParser can parse the pair name
- Verify ticker mapping is correct for unusual pairs

## Maintenance

### Post-Import Optimization

After large imports, optimize database:

```sql
-- Analyze tables for query planner
ANALYZE feefifofunds_assetprice;
ANALYZE feefifofunds_trade;

-- Vacuum to reclaim space
VACUUM ANALYZE feefifofunds_assetprice;
VACUUM ANALYZE feefifofunds_trade;
```

### Checking Import Status

```python
from feefifofunds.models import Asset, AssetPrice, Trade

# Check total records
print(f"Assets: {Asset.objects.count()}")
print(f"OHLCV records: {AssetPrice.objects.count()}")
print(f"Trade records: {Trade.objects.count()}")

# Check by source
print(f"Kraken OHLCV: {AssetPrice.objects.filter(source='kraken').count()}")
print(f"Kraken trades: {Trade.objects.filter(source='kraken').count()}")

# Check intervals
from django.db.models import Count
intervals = AssetPrice.objects.values("interval_minutes").annotate(count=Count("id"))
for interval in intervals:
    print(f"  {interval['interval_minutes']}m: {interval['count']:,} records")
```

### Re-importing Data

To re-import data (e.g., after receiving updated files):

1. Use `--skip-existing` to only import new pairs/intervals
2. Or delete existing data first:
   ```python
   AssetPrice.objects.filter(source="kraken").delete()
   Trade.objects.filter(source="kraken").delete()
   ```
3. Then run import commands without `--skip-existing`
