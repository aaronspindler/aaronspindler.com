# Data Sources System

## Overview

The Data Sources system provides a standardized framework for integrating external financial data APIs (Yahoo Finance, Alpha Vantage, Finnhub, Massive.com, etc.) into the FeeFiFoFunds application. It includes rate limiting, error handling, caching, monitoring, and data validation to ensure reliable and cost-effective data acquisition.

## Available Data Sources

| Source | Free Tier | Historical Data | Real-Time | Best For |
|--------|-----------|-----------------|-----------|----------|
| **Massive.com** | 100 req/sec | 2 years | No | Historical backloads |
| Yahoo Finance | Unlimited | Years | 15-min delay | General purpose |
| Finnhub | 60 calls/min | Limited | Yes | Real-time updates |
| Alpha Vantage | 5 calls/min | 20+ years | Yes | Research/analysis |

See [Massive.com Integration](massive-integration.md) for detailed documentation on the Massive.com data source.

## Features

- **Standardized Interface**: Abstract base class ensures consistent integration across all data sources
- **Rate Limiting**: Automatic rate limit enforcement to prevent API overages and account suspension
- **Error Handling**: Comprehensive exception hierarchy for different failure modes
- **Caching**: Redis-backed caching reduces API calls and improves performance
- **Monitoring**: Tracks request success/failure, reliability scores, and consecutive failures
- **Data Validation**: DTOs with automatic type conversion and validation
- **Auto-Recovery**: Automatic disable after 5 consecutive failures, prevents cascading issues
- **Audit Trail**: Complete DataSync records for compliance and debugging

## Architecture

### Components

```
feefifofunds/services/data_sources/
├── __init__.py          # Package exports
├── base.py              # BaseDataSource abstract class (289 lines)
├── dto.py               # Data Transfer Objects (178 lines)
└── implementations/     # Concrete implementations (Yahoo, Alpha Vantage, etc.)
```

### Data Flow

```
External API → BaseDataSource → DTO Validation → Database Model
                    ↓
              Rate Limiting
              Error Handling
              Caching
              Monitoring
```

### Database Models

**DataSource Model**: Tracks data source configuration and health
- Configuration: base_url, rate limits, API key requirements
- Monitoring: requests_today, last_request_time, reliability_score
- Status: ACTIVE, INACTIVE, ERROR, RATE_LIMITED, MAINTENANCE

**DataSync Model**: Audit trail for all synchronization operations
- Tracks: sync_type, status, timing, records processed
- Stores: request_params, response_metadata, error_details

## Data Transfer Objects (DTOs)

### FundDataDTO

Standardizes fund information from various APIs.

**Required Fields**:
```python
ticker: str              # Fund ticker symbol (e.g., "VTI")
name: str               # Full fund name (e.g., "Vanguard Total Stock Market ETF")
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

### PerformanceDataDTO

Standardizes OHLCV (Open, High, Low, Close, Volume) price data.

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

## Creating a Data Source

### Step 1: Create Implementation Class

```python
# feefifofunds/services/data_sources/implementations/yahoo_finance.py
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

### Step 2: Register Data Source

```python
# feefifofunds/services/data_sources/__init__.py
from .implementations.yahoo_finance import YahooFinanceDataSource

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

## Configuration

### Environment Variables

```bash
# Data source API keys
YAHOO_FINANCE_API_KEY=your-key-here
ALPHA_VANTAGE_API_KEY=your-key-here
FINNHUB_API_KEY=your-key-here

# Rate limiting (optional, overrides defaults)
YAHOO_FINANCE_RATE_LIMIT=2000
YAHOO_FINANCE_RATE_PERIOD=3600

# Caching
CACHE_BACKEND=redis
REDIS_URL=redis://localhost:6379/0
```

### Django Settings

```python
# settings.py

# Data source configuration
DATA_SOURCE_SETTINGS = {
    "yahoo_finance": {
        "api_key": env("YAHOO_FINANCE_API_KEY", default=None),
        "rate_limit_requests": env.int("YAHOO_FINANCE_RATE_LIMIT", default=2000),
        "rate_limit_period": env.int("YAHOO_FINANCE_RATE_PERIOD", default=3600),
        "cache_timeout": 3600,  # 1 hour
    },
    "alpha_vantage": {
        "api_key": env("ALPHA_VANTAGE_API_KEY"),
        "rate_limit_requests": env.int("ALPHA_VANTAGE_RATE_LIMIT", default=5),
        "rate_limit_period": env.int("ALPHA_VANTAGE_RATE_PERIOD", default=60),
        "cache_timeout": 7200,  # 2 hours
    },
}
```

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

### 2. Always Use Decimal for Money

**Do**:
```python
price = Decimal(str(api_response["price"]))  # Precise
```

**Don't**:
```python
price = float(api_response["price"])  # Loses precision
```

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

### 4. Use Caching for Expensive Operations

**Do**:
```python
return self._get_cached_or_fetch(cache_key, fetch_func, 3600)
```

**Don't**:
```python
return fetch_func()  # Always hits API
```

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

## Troubleshooting

### Rate Limit Exceeded

**Symptoms**: `RateLimitError` exceptions, API returning 429 status

**Solutions**:
1. Check requests_today in Django admin
2. Reduce rate_limit_requests if too aggressive
3. Implement distributed rate limiting with Redis
4. Use caching to reduce API calls
5. Schedule data fetches during off-peak hours

### Data Source Auto-Disabled

**Symptoms**: `status = ERROR`, requests failing with "Source is disabled"

**Solutions**:
1. Check `last_error` field in Django admin
2. Fix underlying issue (API key, network, etc.)
3. Reset `consecutive_failures` to 0
4. Change `status` back to ACTIVE
5. Test with single request before batch operations

### DTO Validation Errors

**Symptoms**: `ValueError` during DTO creation

**Solutions**:
1. Check required fields are present (ticker, name, etc.)
2. Verify Decimal conversion for prices
3. Check date format (YYYY-MM-DD)
4. Validate currency codes (ISO 4217)
5. Review API response format changes

### Caching Issues

**Symptoms**: Stale data, cache misses

**Solutions**:
1. Check Redis is running: `redis-cli PING`
2. Verify REDIS_URL in environment
3. Check cache key format (consistent naming)
4. Clear cache: `python manage.py clear_cache`
5. Adjust cache_timeout for your use case

### Missing API Data

**Symptoms**: `DataNotFoundError`, incomplete fund information

**Solutions**:
1. Verify ticker symbol is correct
2. Check data source supports requested data type
3. Try alternative data source
4. Handle missing data with Optional fields
5. Log missing data for investigation

## Related Documentation

- [Architecture](../architecture.md) - System design and data flow
- [API Reference](../api.md) - API endpoints for data sources
- [Commands](../commands.md) - Management commands for data syncing
- [Testing](../testing.md) - Testing data source integrations
- [Deployment](../deployment.md) - Production configuration for data sources
