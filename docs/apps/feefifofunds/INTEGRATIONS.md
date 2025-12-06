# FeeFiFoFunds - Data Source Integrations

Complete guide for integrating external financial data APIs and managing data models.

## Table of Contents

1. [Overview](#overview)
2. [Available Data Sources](#available-data-sources)
3. [Data Models](#data-models)
4. [Data Transfer Objects (DTOs)](#data-transfer-objects-dtos)
5. [Creating a Data Source](#creating-a-data-source)
6. [Massive.com Integration](#massivecom-integration)
7. [Rate Limiting](#rate-limiting)
8. [Error Handling](#error-handling)
9. [Caching](#caching)
10. [Monitoring](#monitoring)
11. [Best Practices](#best-practices)
12. [Troubleshooting](#troubleshooting)

---

## Overview

The Data Sources system provides a standardized framework for integrating external financial data APIs (Yahoo Finance, Alpha Vantage, Finnhub, Massive.com, etc.) into the FeeFiFoFunds application. It includes rate limiting, error handling, caching, monitoring, and data validation to ensure reliable and cost-effective data acquisition.

### Features

- **Standardized Interface**: Abstract base class ensures consistent integration across all data sources
- **Rate Limiting**: Automatic rate limit enforcement to prevent API overages and account suspension
- **Error Handling**: Comprehensive exception hierarchy for different failure modes
- **Caching**: Redis-backed caching reduces API calls and improves performance
- **Monitoring**: Tracks request success/failure, reliability scores, and consecutive failures
- **Data Validation**: DTOs with automatic type conversion and validation
- **Auto-Recovery**: Automatic disable after 5 consecutive failures, prevents cascading issues
- **Audit Trail**: Complete DataSync records for compliance and debugging

---

## Available Data Sources

| Source | Free Tier | Historical Data | Real-Time | Best For |
|--------|-----------|-----------------|-----------|----------|
| **Massive.com** | 100 req/sec | 2 years | No | Historical backloads |
| Yahoo Finance | Unlimited | Years | 15-min delay | General purpose |
| Finnhub | 60 calls/min | Limited | Yes | Real-time updates |
| Alpha Vantage | 5 calls/min | 20+ years | Yes | Research/analysis |

---

## Data Models

FeeFiFoFunds uses a hybrid database architecture for optimal performance:

### PostgreSQL Models (Metadata)

#### Asset Model
Universal model for all asset types stored in PostgreSQL.

**Fields:**
```python
ticker = CharField(max_length=20, unique=True)  # BTC, AAPL, GLD
name = CharField(max_length=255)  # Full asset name
category = CharField(max_length=20, choices=[STOCK, CRYPTO, COMMODITY, CURRENCY])
tier = CharField(max_length=20, choices=[TIER1, TIER2, TIER3, TIER4, UNCLASSIFIED])
description = TextField(blank=True)
active = BooleanField(default=True)
created_at, updated_at = DateTimeField()
```

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

### QuestDB Models (Time-Series)

#### AssetPrice Model
OHLCV (Open/High/Low/Close/Volume) price records stored in QuestDB for high-performance time-series queries.

**Fields:**
```python
asset_id = IntegerField()  # Reference to Asset.id in PostgreSQL
time = DateTimeField()  # QuestDB designated timestamp
open = DecimalField(max_digits=20, decimal_places=8)
high = DecimalField(max_digits=20, decimal_places=8)
low = DecimalField(max_digits=20, decimal_places=8)
close = DecimalField(max_digits=20, decimal_places=8)
volume = DecimalField(max_digits=20, decimal_places=8)
interval_minutes = SmallIntegerField()  # 1, 5, 15, 30, 60, 240, 1440
trade_count = IntegerField(null=True)
quote_currency = CharField(max_length=10)  # SYMBOL type in QuestDB
source = CharField(max_length=50)  # SYMBOL type in QuestDB
```

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
) TIMESTAMP(time) PARTITION BY DAY
DEDUP UPSERT KEYS(time, asset_id, interval_minutes, source, quote_currency);
```

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

## Data Transfer Objects (DTOs)

### FundDataDTO

Standardizes fund information from various APIs.

**Required Fields**:
```python
ticker: str              # Fund ticker symbol (e.g., "VTI")
name: str               # Full fund name
```

**Fund Classification**:
```python
fund_type: Optional[str]       # ETF, MUTUAL, INDEX, BOND, MM, TARGET, OTHER
asset_class: Optional[str]     # EQUITY, BOND, MIXED, MM, COMMODITY, REIT, ALT
category: Optional[str]        # Morningstar category
```

**Costs & Fees**:
```python
expense_ratio: Optional[Decimal]    # Annual expense ratio (e.g., 0.03 for 0.03%)
management_fee: Optional[Decimal]   # Management fee percentage
front_load: Optional[Decimal]       # Front-end load fee
back_load: Optional[Decimal]        # Back-end load fee
```

**Current State**:
```python
current_price: Optional[Decimal]    # Current NAV or price
previous_close: Optional[Decimal]   # Previous closing price
currency: str = "USD"               # Currency code (ISO 4217)
```

**Fund Size**:
```python
aum: Optional[Decimal]              # Assets Under Management (millions)
avg_volume: Optional[int]           # Average daily trading volume
```

**Metadata**:
```python
exchange: Optional[str]             # Primary exchange
website: Optional[str]              # Official fund website
isin: Optional[str]                 # International Securities ID
cusip: Optional[str]                # CUSIP number
source: str                         # Data source identifier
fetched_at: datetime                # Timestamp of fetch
```

---

### PerformanceDataDTO

Standardizes OHLCV price data.

**Required Fields**:
```python
ticker: str                 # Fund ticker symbol
date: date                  # Data date
close_price: Decimal        # Closing price
```

**OHLCV Data**:
```python
open_price: Optional[Decimal]      # Opening price
high_price: Optional[Decimal]      # High price for the period
low_price: Optional[Decimal]       # Low price for the period
adjusted_close: Optional[Decimal]  # Adjusted closing price
volume: Optional[int]              # Trading volume (shares)
```

**Distributions**:
```python
dividend: Optional[Decimal]        # Dividend amount
split_ratio: Optional[Decimal]     # Stock split ratio
```

**Metadata**:
```python
interval: str = "1D"               # Data interval (1D, 1W, 1M, 1Q, 1Y)
source: str                        # Data source identifier
fetched_at: datetime               # Timestamp of fetch
```

---

### HoldingDataDTO

Standardizes fund holdings data.

**Required Fields**:
```python
ticker: str                 # Holding ticker symbol
name: str                   # Holding name
weight: Decimal             # Portfolio weight percentage
```

**Position Details**:
```python
shares: Optional[Decimal]          # Number of shares held
market_value: Optional[Decimal]    # Current market value
```

**Classification**:
```python
holding_type: str = "EQUITY"       # EQUITY, BOND, CASH, OPTION, FUTURE, COMMODITY, REIT, OTHER
sector: Optional[str]              # GICS sector
industry: Optional[str]            # Industry classification
country: Optional[str]             # Country of domicile
```

**Identifiers**:
```python
cusip: Optional[str]               # CUSIP number
isin: Optional[str]                # ISIN number
```

**Metadata**:
```python
as_of_date: Optional[date]         # Data as-of date
source: str                        # Data source identifier
fetched_at: datetime               # Timestamp of fetch
```

---

## Creating a Data Source

### Step 1: Create Implementation Class

```python
# feefifofunds/services/data_sources/yahoo_finance.py
from datetime import date
from typing import List
from decimal import Decimal

from feefifofunds.services.data_sources import (
    BaseDataSource,
    FundDataDTO,
    PerformanceDataDTO,
    HoldingDataDTO,
    DataNotFoundError,
)

class YahooFinanceDataSource(BaseDataSource):
    """Yahoo Finance data source implementation."""

    # Required class attributes
    name = "yahoo_finance"
    display_name = "Yahoo Finance"
    base_url = "https://query1.finance.yahoo.com"
    requires_api_key = False
    rate_limit_requests = 2000
    rate_limit_period = 3600  # per hour

    def fetch_fund_info(self, ticker: str) -> FundDataDTO:
        """Fetch basic fund information."""
        # Check rate limit
        if not self.can_make_request():
            self.wait_for_rate_limit()

        # Build request
        url = f"{self.base_url}/v8/finance/quote"
        params = {"symbols": ticker}

        # Make request (handles errors, rate limiting, recording)
        data = self._make_request(url, params)

        # Check for data
        if not data or "quoteResponse" not in data:
            raise DataNotFoundError(f"No data found for ticker: {ticker}")

        results = data["quoteResponse"]["result"]
        if not results:
            raise DataNotFoundError(f"Ticker not found: {ticker}")

        quote = results[0]

        # Transform to DTO
        return FundDataDTO(
            ticker=ticker.upper(),
            name=quote.get("longName", quote.get("shortName", ticker)),
            fund_type="ETF" if quote.get("quoteType") == "ETF" else "OTHER",
            current_price=Decimal(str(quote["regularMarketPrice"])) if "regularMarketPrice" in quote else None,
            previous_close=Decimal(str(quote["previousClose"])) if "previousClose" in quote else None,
            currency=quote.get("currency", "USD"),
            exchange=quote.get("fullExchangeName"),
            source=self.name,
        )

    def fetch_historical_prices(
        self, ticker: str, start_date: date, end_date: date, interval: str = "1D"
    ) -> List[PerformanceDataDTO]:
        """Fetch historical price data."""
        # Implementation details...
        pass

    def fetch_holdings(self, ticker: str) -> List[HoldingDataDTO]:
        """Fetch fund holdings."""
        # Yahoo Finance doesn't provide holdings
        raise NotImplementedError("Yahoo Finance does not provide holdings data")
```

---

### Step 2: Register Data Source

```python
# feefifofunds/services/data_sources/__init__.py
from .yahoo_finance import YahooFinanceDataSource

# Data source registry
DATA_SOURCES = {
    "yahoo_finance": YahooFinanceDataSource,
    # Add more sources...
}

def get_data_source(name: str, api_key: str = None):
    """Get data source instance by name."""
    if name not in DATA_SOURCES:
        raise ValueError(f"Unknown data source: {name}")
    return DATA_SOURCES[name](api_key=api_key)
```

---

### Step 3: Use Data Source

```python
from feefifofunds.services.data_sources import get_data_source

# Initialize data source
yahoo = get_data_source("yahoo_finance")

# Fetch fund information
try:
    fund_data = yahoo.fetch_fund_info("VTI")
    print(f"Fund: {fund_data.name}")
    print(f"Price: ${fund_data.current_price}")
    print(f"Expense Ratio: {fund_data.expense_ratio}%")
except DataNotFoundError:
    print("Fund not found")
except RateLimitError:
    print("Rate limit exceeded")
```

---

## Massive.com Integration

The Massive.com (formerly Polygon.io) data source integration enables the FeeFiFoFunds app to fetch historical and daily stock/ETF price data from Massive.com's free API. This provides comprehensive OHLCV data for up to 2 years of history.

### Features

- **Historical Data Backloading**: Fetch up to 730 days (2 years) of historical price data
- **Daily Updates**: Automated daily price updates for all active funds
- **Fund Auto-Creation**: Automatically create fund records when fetching data
- **Transaction Safety**: All database operations wrapped in atomic transactions
- **DataSync Tracking**: Comprehensive audit trail of all data fetches
- **Input Validation**: Ticker format and date range validation
- **Rate Limiting**: Built-in awareness of API rate limits (~100 req/sec)

### Free Tier Capabilities

Massive.com's free tier provides generous limits:

- **Rate Limit**: ~100 requests/second (soft limit, no hard daily cap)
- **Historical Data**: 2 years at minute-level granularity
- **Data Type**: End-of-day OHLCV data (no real-time on free tier)
- **Best For**: Historical data backloading and batch processing

**Note**: For real-time data, consider using Finnhub after initial backload with Massive.com.

### Setup

#### 1. Get API Key

1. Visit [massive.com](https://massive.com)
2. Sign up for free account
3. Generate API key from dashboard

#### 2. Configure Environment

Add to `.env` file:

```bash
MASSIVE_API_KEY=your_api_key_here
```

Or set environment variable:

```bash
export MASSIVE_API_KEY=your_api_key_here
```

#### 3. Verify Setup

```bash
# Test connection
python manage.py shell
>>> from feefifofunds.services.data_sources.massive import MassiveDataSource
>>> ds = MassiveDataSource()
>>> print(ds.display_name)
Massive.com
```

### Usage

#### Initial Backload

For new funds or historical data recovery:

```bash
# Single fund with auto-creation
python manage.py backload_massive SPY --create-fund --days 730

# Multiple funds
python manage.py backload_massive SPY QQQ VOO VTI --create-fund --days 730

# All existing funds
python manage.py backload_massive --all --days 730
```

#### Daily Updates

For ongoing price updates:

```bash
# Update all active funds
python manage.py update_massive_daily

# Update specific funds
python manage.py update_massive_daily SPY QQQ

# Catch up after weekend
python manage.py update_massive_daily --days 5
```

### API Reference

#### MassiveDataSource Methods

**`fetch_fund_info(ticker: str) -> FundDataDTO`**

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

---

**`fetch_historical_prices(ticker: str, start_date: date, end_date: date, interval: str = "1D") -> List[PerformanceDataDTO]`**

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

---

**`fetch_recent_days(ticker: str, days: int = 730) -> List[PerformanceDataDTO]`**

Convenience method to fetch recent historical data.

**Parameters**:
- `ticker`: Ticker symbol
- `days`: Number of days to fetch (max 730)

**Returns**: List of `PerformanceDataDTO` objects

---

## Rate Limiting

### How It Works

1. **Track Requests**: Every API call is recorded in `DataSource.requests_today`
2. **Check Limit**: `can_make_request()` checks if limit would be exceeded
3. **Auto-Wait**: `wait_for_rate_limit()` pauses execution if needed
4. **Reset Daily**: `requests_today` resets at midnight UTC

### Configuration

```python
class YourDataSource(BaseDataSource):
    rate_limit_requests = 100      # Max requests
    rate_limit_period = 60         # Time period in seconds
```

### Manual Rate Limiting

```python
# Check before making request
if not data_source.can_make_request():
    print("Rate limit would be exceeded")
    data_source.wait_for_rate_limit()

# Make request
result = data_source.fetch_fund_info("VTI")
```

### Distributed Rate Limiting

For production with multiple workers, use Redis-backed rate limiting:

```python
from django_ratelimit.core import is_ratelimited

def can_make_request(self) -> bool:
    """Check rate limit with Redis backend."""
    key = f'datasource:{self.name}'
    return not is_ratelimited(
        key=key,
        rate=f'{self.rate_limit_requests}/{self.rate_limit_period}s',
        increment=True
    )
```

---

## Error Handling

### Exception Hierarchy

```python
DataSourceError              # Base exception
├── RateLimitError          # Rate limit exceeded (429)
└── DataNotFoundError       # Data not found (404)
```

### Handling Errors

```python
from feefifofunds.services.data_sources import (
    DataSourceError,
    RateLimitError,
    DataNotFoundError,
)

try:
    fund_data = data_source.fetch_fund_info("VTI")
except DataNotFoundError as e:
    # Ticker doesn't exist or no data available
    logger.warning(f"Fund not found: {e}")
except RateLimitError as e:
    # Rate limit exceeded, retry later
    logger.error(f"Rate limit: {e}")
    # Schedule retry in Celery
except DataSourceError as e:
    # Generic API error
    logger.error(f"Data source error: {e}")
```

### Automatic Error Recording

All errors are automatically recorded in the `DataSource` model:
- `last_error`: Error message
- `last_error_time`: Timestamp
- `consecutive_failures`: Counter (auto-disables at 5)
- `reliability_score`: Exponential moving average

### Auto-Disable on Failures

After 5 consecutive failures, the data source automatically:
1. Sets `status = "ERROR"`
2. Stops making requests (`can_make_request()` returns `False`)
3. Requires manual re-enable in Django admin

---

## Caching

### Automatic Caching

Use the built-in cache helper:

```python
def fetch_fund_info(self, ticker: str) -> FundDataDTO:
    cache_key = f"fund_info:{ticker}"

    def fetch():
        # Actual API call
        return self._fetch_from_api(ticker)

    # Cache for 1 hour (3600 seconds)
    return self._get_cached_or_fetch(cache_key, fetch, cache_timeout=3600)
```

### Cache Keys Convention

```python
# Fund information: fund_info:{ticker}
f"fund_info:{ticker}"

# Historical prices: prices:{ticker}:{start}:{end}:{interval}
f"prices:{ticker}:{start_date}:{end_date}:{interval}"

# Holdings: holdings:{ticker}
f"holdings:{ticker}"
```

### Cache Invalidation

```python
from django.core.cache import cache

# Clear specific fund
cache.delete(f"fund_info:VTI")

# Clear all fund data
cache.delete_pattern("fund_info:*")

# Clear all data for a ticker
cache.delete_pattern(f"*:VTI")
```

---

## Monitoring

### DataSource Model Fields

**Health Metrics**:
- `requests_today`: Request count for current day
- `last_request_time`: Timestamp of last request
- `last_successful_sync`: Timestamp of last successful sync
- `consecutive_failures`: Number of consecutive failures
- `reliability_score`: Score from 0-100 (exponential moving average)

**Status**:
- `ACTIVE`: Operational
- `INACTIVE`: Manually disabled
- `ERROR`: Auto-disabled due to failures
- `RATE_LIMITED`: Temporarily rate limited
- `MAINTENANCE`: Under maintenance

### Viewing Metrics in Admin

Navigate to `/admin/feefifofunds/datasource/` to view:
- Current status with color coding
- Reliability scores
- Request counts
- Last sync times
- Error messages

### Querying Metrics

```python
from feefifofunds.models import DataSource

# Get data source
ds = DataSource.objects.get(name="yahoo_finance")

# Check health
print(f"Status: {ds.get_status_display()}")
print(f"Reliability: {ds.reliability_score}%")
print(f"Requests today: {ds.requests_today}")
print(f"Last success: {ds.last_successful_sync}")

# Check if operational
if ds.status == DataSource.Status.ACTIVE and ds.reliability_score > 80:
    print("Data source is healthy")
```

### DataSync Audit Trail

Every data fetch creates a `DataSync` record:

```python
from feefifofunds.models import DataSync

# Get recent syncs
recent_syncs = DataSync.objects.filter(
    data_source__name="yahoo_finance"
).order_by('-started_at')[:10]

for sync in recent_syncs:
    print(f"{sync.sync_type}: {sync.get_status_display()}")
    print(f"  Duration: {sync.duration_seconds}s")
    print(f"  Records: {sync.records_created} created, {sync.records_updated} updated")
    if sync.status == DataSync.Status.FAILED:
        print(f"  Error: {sync.error_message}")
```

---

## Best Practices

### 1. Use DTOs for All Data Transfer

**Do**:
```python
def fetch_fund_info(self, ticker: str) -> FundDataDTO:
    data = self._make_request(url)
    return FundDataDTO(
        ticker=ticker,
        name=data["name"],
        current_price=Decimal(str(data["price"])),
        source=self.name,
    )
```

**Don't**:
```python
def fetch_fund_info(self, ticker: str) -> dict:
    return self._make_request(url)  # Raw dict, no validation
```

---

### 2. Always Use Decimal for Money

**Do**:
```python
price = Decimal(str(api_response["price"]))  # Precise
```

**Don't**:
```python
price = float(api_response["price"])  # Loses precision
```

---

### 3. Handle Missing Data Gracefully

**Do**:
```python
expense_ratio = None
if "expenseRatio" in data:
    expense_ratio = Decimal(str(data["expenseRatio"]))
```

**Don't**:
```python
expense_ratio = Decimal(str(data["expenseRatio"]))  # KeyError if missing
```

---

### 4. Use Caching for Expensive Operations

**Do**:
```python
return self._get_cached_or_fetch(cache_key, fetch_func, 3600)
```

**Don't**:
```python
return fetch_func()  # Always hits API
```

---

### 5. Create Sync Records for Audit

**Do**:
```python
sync = self.create_sync_record(
    sync_type=DataSync.SyncType.FUND_INFO,
    fund=fund,
    request_params={"ticker": ticker}
)
try:
    result = self.fetch_fund_info(ticker)
    sync.mark_success(records_fetched=1)
except Exception as e:
    sync.mark_failed(str(e))
    raise
```

---

## Troubleshooting

### Rate Limit Exceeded

**Symptoms**: `RateLimitError` exceptions, API returning 429 status

**Solutions**:
1. Check requests_today in Django admin
2. Reduce rate_limit_requests if too aggressive
3. Implement distributed rate limiting with Redis
4. Use caching to reduce API calls
5. Schedule data fetches during off-peak hours

---

### Data Source Auto-Disabled

**Symptoms**: `status = ERROR`, requests failing with "Source is disabled"

**Solutions**:
1. Check `last_error` field in Django admin
2. Fix underlying issue (API key, network, etc.)
3. Reset `consecutive_failures` to 0
4. Change `status` back to ACTIVE
5. Test with single request before batch operations

---

### DTO Validation Errors

**Symptoms**: `ValueError` during DTO creation

**Solutions**:
1. Check required fields are present (ticker, name, etc.)
2. Verify Decimal conversion for prices
3. Check date format (YYYY-MM-DD)
4. Validate currency codes (ISO 4217)
5. Review API response format changes

---

### Caching Issues

**Symptoms**: Stale data, cache misses

**Solutions**:
1. Check Redis is running: `redis-cli PING`
2. Verify REDIS_URL in environment
3. Check cache key format (consistent naming)
4. Clear cache: `python manage.py clear_cache`
5. Adjust cache_timeout for your use case

---

### Missing API Data

**Symptoms**: `DataNotFoundError`, incomplete fund information

**Solutions**:
1. Verify ticker symbol is correct
2. Check data source supports requested data type
3. Try alternative data source
4. Handle missing data with Optional fields
5. Log missing data for investigation

---

## Related Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture and design
- [OPERATIONS.md](OPERATIONS.md) - Commands and workflows
- [SETUP.md](SETUP.md) - Development environment setup
- [README.md](README.md) - Overview and quick start
