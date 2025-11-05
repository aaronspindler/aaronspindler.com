# Massive.com Data Source Integration

## Overview

The Massive.com (formerly Polygon.io) data source integration enables the FeeFiFoFunds app to fetch historical and daily stock/ETF price data from Massive.com's free API. This provides comprehensive OHLCV (Open, High, Low, Close, Volume) data for up to 2 years of history.

## Features

- **Historical Data Backloading**: Fetch up to 730 days (2 years) of historical price data
- **Daily Updates**: Automated daily price updates for all active funds
- **Fund Auto-Creation**: Automatically create fund records when fetching data
- **Transaction Safety**: All database operations wrapped in atomic transactions
- **DataSync Tracking**: Comprehensive audit trail of all data fetches
- **Input Validation**: Ticker format and date range validation
- **Rate Limiting**: Built-in awareness of API rate limits (~100 req/sec)

## Free Tier Capabilities

Massive.com's free tier provides generous limits:

- **Rate Limit**: ~100 requests/second (soft limit, no hard daily cap)
- **Historical Data**: 2 years at minute-level granularity
- **Data Type**: End-of-day OHLCV data (no real-time on free tier)
- **Best For**: Historical data backloading and batch processing

**Note**: For real-time data, consider using Finnhub after initial backload with Massive.com.

## Architecture

### Components

1. **MassiveDataSource** (`feefifofunds/services/data_sources/massive.py`)
   - Data source adapter implementing `BaseDataSource` interface
   - Handles API communication and data transformation
   - Includes validation and error handling

2. **Management Commands** (`feefifofunds/management/commands/`)
   - `backload_massive`: Historical data backloading
   - `update_massive_daily`: Daily price updates
   - `massive_utils`: Shared utility functions

3. **Models**
   - `Fund`: Asset model (polymorphic base)
   - `FundPerformance`: Price/performance data
   - `DataSync`: API fetch tracking and audit trail

### Data Flow

```
Massive.com API
    ↓
MassiveDataSource (validation, transformation)
    ↓
Management Command (transaction handling)
    ↓
FundPerformance Model (database storage)
    ↓
Fund Model (current value update)
```

## Setup

### 1. Get API Key

1. Visit [massive.com](https://massive.com)
2. Sign up for free account
3. Generate API key from dashboard

### 2. Configure Environment

Add to `.env` file:

```bash
MASSIVE_API_KEY=your_api_key_here
```

Or set environment variable:

```bash
export MASSIVE_API_KEY=your_api_key_here
```

### 3. Verify Setup

```bash
# Test connection
python manage.py shell
>>> from feefifofunds.services.data_sources.massive import MassiveDataSource
>>> ds = MassiveDataSource()
>>> print(ds.display_name)
Massive.com
```

## Usage

### Initial Backload

For new funds or historical data recovery:

```bash
# Single fund with auto-creation
python manage.py backload_massive SPY --create-fund --days 730

# Multiple funds
python manage.py backload_massive SPY QQQ VOO VTI --create-fund --days 730

# All existing funds
python manage.py backload_massive --all --days 730
```

### Daily Updates

For ongoing price updates:

```bash
# Update all active funds
python manage.py update_massive_daily

# Update specific funds
python manage.py update_massive_daily SPY QQQ

# Catch up after weekend
python manage.py update_massive_daily --days 5
```

### Automation

#### Cron Example

Add to crontab for daily 6 PM updates (weekdays only):

```bash
0 18 * * 1-5 /path/to/venv/bin/python /path/to/manage.py update_massive_daily
```

#### Celery Beat Example

Add to `config/celery.py`:

```python
from celery.schedules import crontab

app.conf.beat_schedule = {
    'update-fund-prices-daily': {
        'task': 'feefifofunds.tasks.update_fund_prices',
        'schedule': crontab(hour=18, minute=0, day_of_week='1-5'),
    },
}
```

Create task in `feefifofunds/tasks.py`:

```python
from celery import shared_task
from django.core.management import call_command

@shared_task
def update_fund_prices():
    call_command('update_massive_daily')
```

## API Reference

### MassiveDataSource Methods

#### `fetch_fund_info(ticker: str) -> FundDataDTO`

Fetch basic fund information including name, exchange, and current price.

**Parameters**:
- `ticker`: Stock/ETF ticker symbol (e.g., 'SPY', 'AAPL')

**Returns**: `FundDataDTO` with fund metadata

**Example**:
```python
from feefifofunds.services.data_sources.massive import MassiveDataSource

ds = MassiveDataSource()
fund_data = ds.fetch_fund_info('SPY')
print(f"{fund_data.name}: ${fund_data.current_price}")
```

#### `fetch_historical_prices(ticker: str, start_date: date, end_date: date, interval: str = "1D") -> List[PerformanceDataDTO]`

Fetch historical OHLCV data for a date range.

**Parameters**:
- `ticker`: Ticker symbol
- `start_date`: Start date for historical data
- `end_date`: End date for historical data
- `interval`: Data interval ('1D', '1W', '1M')

**Returns**: List of `PerformanceDataDTO` objects

**Example**:
```python
from datetime import date, timedelta
from feefifofunds.services.data_sources.massive import MassiveDataSource

ds = MassiveDataSource()
end_date = date.today()
start_date = end_date - timedelta(days=30)

prices = ds.fetch_historical_prices('AAPL', start_date, end_date)
for price in prices:
    print(f"{price.date}: ${price.close_price}")
```

#### `fetch_recent_days(ticker: str, days: int = 730) -> List[PerformanceDataDTO]`

Convenience method to fetch recent historical data.

**Parameters**:
- `ticker`: Ticker symbol
- `days`: Number of days to fetch (max 730)

**Returns**: List of `PerformanceDataDTO` objects

## Data Models

### FundPerformance

Stores daily price and volume data:

```python
class FundPerformance(models.Model):
    asset = models.ForeignKey(Fund, on_delete=models.CASCADE)
    date = models.DateField()
    open_price = models.DecimalField(max_digits=15, decimal_places=6)
    high_price = models.DecimalField(max_digits=15, decimal_places=6)
    low_price = models.DecimalField(max_digits=15, decimal_places=6)
    close_price = models.DecimalField(max_digits=15, decimal_places=6)
    adjusted_close = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    volume = models.BigIntegerField(default=0)
    dividend = models.DecimalField(max_digits=10, decimal_places=6, null=True)
    split_ratio = models.DecimalField(max_digits=10, decimal_places=6, null=True)
```

### DataSync

Tracks all API fetch operations:

```python
class DataSync(models.Model):
    sync_type = models.CharField(max_length=50)  # e.g., 'PRICES', 'FUND_INFO'
    fund = models.ForeignKey(Fund, on_delete=models.CASCADE, null=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True)
    success = models.BooleanField(default=False)
    records_fetched = models.IntegerField(default=0)
    records_created = models.IntegerField(default=0)
    records_updated = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)
```

## Validation

### Ticker Validation

Tickers must match pattern: `^[A-Z0-9.^-]+$`

**Valid**:
- `SPY`
- `BRK.B`
- `^VIX`

**Invalid**:
- `spy` (lowercase)
- `S&P` (special characters)

### Date Range Validation

- Start date must be before end date
- Maximum range: 730 days (free tier limit)
- Automatic capping at 730 days if exceeded

## Error Handling

### Common Errors

1. **Missing API Key**
   ```
   Error: MASSIVE_API_KEY is required. Set in environment variables or settings.
   ```
   **Solution**: Set `MASSIVE_API_KEY` in environment or `.env` file

2. **Invalid Ticker**
   ```
   Error: Invalid ticker format: spy
   ```
   **Solution**: Use uppercase ticker symbols (e.g., `SPY` not `spy`)

3. **Date Range Exceeded**
   ```
   Error: Date range exceeds free tier limit of 730 days
   ```
   **Solution**: Reduce date range or split into multiple requests

4. **No Data Found**
   ```
   Error: No historical data found for ticker XYZ
   ```
   **Solution**: Verify ticker exists and is traded on US exchanges

## Performance Considerations

### Rate Limiting

- Free tier: ~100 requests/second
- No hard daily cap
- Commands automatically handle rate limits

### Batch Processing

For large fund lists:

```bash
# Process in chunks (example: 100 funds)
python manage.py backload_massive --all --days 365
# Command handles all funds automatically with proper error handling
```

### Database Performance

- All operations use `update_or_create` for efficiency
- Transactions prevent partial updates
- Bulk creates when possible

## Testing

### Manual Testing

```bash
# Test single fund backload
python manage.py backload_massive SPY --create-fund --days 30

# Test daily update
python manage.py update_massive_daily SPY

# Test validation
python manage.py backload_massive spy  # Should fail (lowercase)
```

### Django Shell Testing

```python
from feefifofunds.services.data_sources.massive import MassiveDataSource
from datetime import date, timedelta

# Test data source initialization
ds = MassiveDataSource()

# Test fund info fetch
fund_data = ds.fetch_fund_info('SPY')
print(fund_data)

# Test price fetch
end_date = date.today()
start_date = end_date - timedelta(days=7)
prices = ds.fetch_historical_prices('SPY', start_date, end_date)
print(f"Fetched {len(prices)} price records")
```

## Monitoring

### DataSync Records

Check fetch history:

```python
from feefifofunds.models import DataSync

# Recent syncs
recent = DataSync.objects.filter(
    sync_type='PRICES'
).order_by('-started_at')[:10]

for sync in recent:
    print(f"{sync.fund.ticker}: {sync.records_fetched} records")
    if not sync.success:
        print(f"  Error: {sync.error_message}")
```

### Command Output

Both commands provide detailed progress output:

```
📊 Backloading data for: SPY
📅 Fetching 730 days of historical data (up to 2 years on free tier)

============================================================
Processing SPY...
============================================================
📥 Fetching historical data from 2023-11-04 to 2025-11-04...
💾 Saving 504 records...
✅ SPY: 504 created, 0 updated, 0 skipped

============================================================
✅ Successfully processed: 1
============================================================
```

## Recommended Workflow

1. **Initial Setup**:
   - Get Massive.com API key
   - Configure environment variable
   - Test with single fund

2. **Historical Backload**:
   - Use `backload_massive` for 2-year data
   - Start with major funds (SPY, QQQ, etc.)
   - Expand to full portfolio

3. **Daily Updates**:
   - Configure cron or Celery Beat
   - Use `update_massive_daily` for all active funds
   - Monitor DataSync records

4. **Optional Real-Time**:
   - After backload, consider Finnhub for real-time data
   - Use Massive.com for historical fills

## Related Documentation

- [Commands Reference](../commands.md) - Full command documentation
- [Architecture](../architecture.md) - FeeFiFoFunds architecture
- [Testing](../testing.md) - Testing guidelines
