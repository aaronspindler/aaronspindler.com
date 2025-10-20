# Fee Fi Fo Funds

The goal of Fee Fi Fo Funds is to gather a base of data, have an interface that is interactive and easy to use to compare ETFs and Mutual Funds, and eventually be able to utilize data from the sources to make recommendations.

## 🎯 Project Overview

FeeFiFoFunds is a comprehensive fund analysis platform that aggregates data from multiple financial APIs to provide investors with detailed comparisons, performance analytics, and AI-powered recommendations for ETFs and Mutual Funds.

### 📦 Portability & Architecture Note

**IMPORTANT:** All functionality for FeeFiFoFunds must be contained within the `feefifofunds/` Django app directory. This includes:
- All models, views, and templates
- Static files and media
- Management commands
- API endpoints and serializers
- Celery tasks
- Custom middleware or context processors
- Tests and fixtures

This architectural decision ensures the app remains portable and can be easily extracted to run as a standalone Django deployment when needed. Avoid creating dependencies on other apps in the parent project, and keep all feature-specific code self-contained within the `feefifofunds/` directory structure.

### 📁 Recommended Directory Structure

```
feefifofunds/
├── __init__.py
├── apps.py
├── models.py              # All models defined here
├── admin.py              # Django admin configuration
├── views.py              # View logic
├── urls.py               # URL routing (included in main urls.py)
├── serializers.py        # DRF serializers
├── forms.py              # Django forms
├── tasks.py              # Celery tasks
├──
├── api/                  # API endpoints
│   ├── __init__.py
│   ├── v1/
│   │   ├── views.py
│   │   ├── serializers.py
│   │   └── urls.py
│   └── utils.py
├──
├── data_sources/         # Data provider integrations
│   ├── __init__.py
│   ├── base.py          # Abstract base classes
│   ├── dto.py           # Data transfer objects
│   ├── yahoo_finance.py
│   ├── alpha_vantage.py
│   ├── finnhub.py
│   └── polygon.py
├──
├── analytics/            # Analysis engines
│   ├── __init__.py
│   ├── metrics.py       # Financial calculations
│   ├── scoring.py       # Scoring algorithms
│   ├── comparison.py    # Comparison logic
│   └── ml_models.py     # Machine learning models
├──
├── management/
│   └── commands/        # Management commands
│       ├── fetch_fund.py
│       ├── sync_all_funds.py
│       ├── calculate_scores.py
│       └── import_fund_list.py
├──
├── migrations/          # Database migrations
├──
├── static/
│   └── feefifofunds/    # Static files (CSS, JS, images)
│       ├── css/
│       ├── js/
│       └── img/
├──
├── templates/
│   └── feefifofunds/    # HTML templates
│       ├── base.html
│       ├── fund_list.html
│       ├── fund_detail.html
│       └── comparison.html
├──
├── tests/               # Test suite
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_views.py
│   ├── test_data_sources.py
│   └── test_analytics.py
├──
├── fixtures/            # Test data
│   └── sample_funds.json
├──
└── utils/              # Utility functions
    ├── __init__.py
    ├── cache.py
    ├── validators.py
    └── helpers.py
```

## 📊 System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           User Interface Layer                          │
├─────────────────────────────────────────────────────────────────────────┤
│  Web Interface │ API Gateway │ Real-time Updates │ Analytics Dashboard │
└────────────────┬────────────────────────────────────┬───────────────────┘
                 │                                    │
┌────────────────▼────────────────────────────────────▼───────────────────┐
│                         Application Layer                               │
├──────────────────────────────────────────────────────────────────────────┤
│  Fund Comparison │ Portfolio Analysis │ Recommendations │ Alerts        │
└────────────────┬─────────────────────────────────────┬──────────────────┘
                 │                                     │
┌────────────────▼─────────────────────────────────────▼──────────────────┐
│                          Data Processing Layer                          │
├──────────────────────────────────────────────────────────────────────────┤
│  Data Pipeline │ ETL Jobs │ Scoring Engine │ ML Models │ Cache (Redis)  │
└────────────────┬─────────────────────────────────────┬──────────────────┘
                 │                                     │
┌────────────────▼─────────────────────────────────────▼──────────────────┐
│                           Data Storage Layer                            │
├──────────────────────────────────────────────────────────────────────────┤
│        PostgreSQL Database        │        Time Series Database         │
│  ┌──────────────────────────────┐ │  ┌──────────────────────────────┐ │
│  │ • Fund Master Data           │ │  │ • Price History              │ │
│  │ • Holdings & Allocations     │ │  │ • Performance Metrics        │ │
│  │ • Fund Metrics & Ratios      │ │  │ • Volume Data                │ │
│  │ • User Data & Watchlists     │ │  │ • Technical Indicators       │ │
│  └──────────────────────────────┘ │  └──────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
                                     │
┌────────────────────────────────────▼────────────────────────────────────┐
│                          Data Source Layer                              │
├──────────────────────────────────────────────────────────────────────────┤
│  Yahoo Finance │ Alpha Vantage │ Finnhub │ Polygon.io │ SEC EDGAR      │
└──────────────────────────────────────────────────────────────────────────┘
```

## 🗃️ Data Model Structure

### Core Models

#### 1. Fund Model
```python
class Fund(models.Model):
    """Master fund information model"""

    # Identifiers
    ticker = models.CharField(max_length=10, unique=True, db_index=True)
    cusip = models.CharField(max_length=9, blank=True, null=True)
    isin = models.CharField(max_length=12, blank=True, null=True)

    # Basic Information
    name = models.CharField(max_length=255)
    fund_type = models.CharField(max_length=20, choices=[
        ('ETF', 'Exchange Traded Fund'),
        ('MUTUAL', 'Mutual Fund'),
        ('INDEX', 'Index Fund'),
        ('CLOSED', 'Closed-End Fund'),
    ])
    category = models.CharField(max_length=100)  # e.g., "Large Cap Growth"
    fund_family = models.CharField(max_length=100)  # e.g., "Vanguard"

    # Key Attributes
    inception_date = models.DateField(blank=True, null=True)
    total_assets = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    expense_ratio = models.DecimalField(max_digits=5, decimal_places=4, null=True)
    management_fee = models.DecimalField(max_digits=5, decimal_places=4, null=True)
    twelve_b1_fee = models.DecimalField(max_digits=5, decimal_places=4, null=True)

    # Investment Strategy
    investment_strategy = models.TextField(blank=True)
    benchmark_index = models.CharField(max_length=100, blank=True)

    # Trading Information
    exchange = models.CharField(max_length=20, blank=True)
    min_investment = models.DecimalField(max_digits=10, decimal_places=2, null=True)

    # Metadata
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=['fund_type', 'category']),
            models.Index(fields=['expense_ratio']),
        ]
```

#### 2. FundPerformance Model
```python
class FundPerformance(models.Model):
    """Historical performance and price data"""

    fund = models.ForeignKey(Fund, on_delete=models.CASCADE, related_name='performance')
    date = models.DateField(db_index=True)

    # Price Data
    nav = models.DecimalField(max_digits=10, decimal_places=4)  # Net Asset Value
    open_price = models.DecimalField(max_digits=10, decimal_places=4, null=True)
    high_price = models.DecimalField(max_digits=10, decimal_places=4, null=True)
    low_price = models.DecimalField(max_digits=10, decimal_places=4, null=True)
    close_price = models.DecimalField(max_digits=10, decimal_places=4, null=True)
    adjusted_close = models.DecimalField(max_digits=10, decimal_places=4, null=True)

    # Volume
    volume = models.BigIntegerField(null=True)

    # Returns (calculated daily)
    daily_return = models.DecimalField(max_digits=8, decimal_places=5, null=True)

    class Meta:
        unique_together = ['fund', 'date']
        indexes = [
            models.Index(fields=['fund', '-date']),
        ]
```

#### 3. FundHolding Model
```python
class FundHolding(models.Model):
    """Fund portfolio holdings"""

    fund = models.ForeignKey(Fund, on_delete=models.CASCADE, related_name='holdings')
    as_of_date = models.DateField()

    # Security Information
    security_name = models.CharField(max_length=255)
    security_ticker = models.CharField(max_length=10, blank=True)
    security_type = models.CharField(max_length=50)  # Stock, Bond, Cash, etc.
    sector = models.CharField(max_length=100, blank=True)

    # Position Data
    shares_held = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    market_value = models.DecimalField(max_digits=15, decimal_places=2)
    weight_percentage = models.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        unique_together = ['fund', 'as_of_date', 'security_name']
        indexes = [
            models.Index(fields=['fund', '-as_of_date']),
        ]
```

#### 4. FundMetrics Model
```python
class FundMetrics(models.Model):
    """Calculated financial metrics and ratios"""

    fund = models.OneToOneField(Fund, on_delete=models.CASCADE, related_name='metrics')

    # Risk Metrics
    beta = models.DecimalField(max_digits=6, decimal_places=3, null=True)
    alpha = models.DecimalField(max_digits=6, decimal_places=3, null=True)
    sharpe_ratio = models.DecimalField(max_digits=6, decimal_places=3, null=True)
    sortino_ratio = models.DecimalField(max_digits=6, decimal_places=3, null=True)
    standard_deviation = models.DecimalField(max_digits=6, decimal_places=3, null=True)
    r_squared = models.DecimalField(max_digits=6, decimal_places=3, null=True)

    # Returns (Annualized)
    return_1y = models.DecimalField(max_digits=8, decimal_places=4, null=True)
    return_3y = models.DecimalField(max_digits=8, decimal_places=4, null=True)
    return_5y = models.DecimalField(max_digits=8, decimal_places=4, null=True)
    return_10y = models.DecimalField(max_digits=8, decimal_places=4, null=True)
    return_ytd = models.DecimalField(max_digits=8, decimal_places=4, null=True)

    # Dividend Information
    dividend_yield = models.DecimalField(max_digits=6, decimal_places=4, null=True)
    dividend_frequency = models.CharField(max_length=20, blank=True)

    # Turnover and Efficiency
    turnover_ratio = models.DecimalField(max_digits=6, decimal_places=2, null=True)

    # Morningstar Ratings
    morningstar_rating = models.IntegerField(null=True)  # 1-5 stars
    morningstar_category = models.CharField(max_length=100, blank=True)

    last_updated = models.DateTimeField(auto_now=True)
```

### Data Source Models

#### 5. DataSource Model
```python
class DataSource(models.Model):
    """Track data provider information and API limits"""

    name = models.CharField(max_length=50, unique=True)
    api_key = models.CharField(max_length=255, blank=True)
    base_url = models.URLField()

    # Rate Limiting
    requests_per_minute = models.IntegerField(default=60)
    requests_per_day = models.IntegerField(null=True)
    last_request_time = models.DateTimeField(null=True)

    # Status
    is_active = models.BooleanField(default=True)
    last_error = models.TextField(blank=True)
    last_error_time = models.DateTimeField(null=True)
```

#### 6. DataSync Model
```python
class DataSync(models.Model):
    """Track data synchronization history"""

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('PARTIAL', 'Partial Success'),
    ]

    fund = models.ForeignKey(Fund, on_delete=models.CASCADE, related_name='sync_history')
    data_source = models.ForeignKey(DataSource, on_delete=models.CASCADE)
    sync_type = models.CharField(max_length=50)  # 'full', 'incremental', 'holdings', etc.
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)

    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True)
    records_processed = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['fund', '-started_at']),
            models.Index(fields=['status', '-started_at']),
        ]
```

### Analysis Models

#### 7. FundComparison Model
```python
class FundComparison(models.Model):
    """Store fund comparison results"""

    funds = models.ManyToManyField(Fund, related_name='comparisons')
    comparison_date = models.DateTimeField(auto_now_add=True)

    # Comparison Metadata
    comparison_type = models.CharField(max_length=50)  # 'performance', 'risk', 'cost', etc.
    time_period = models.CharField(max_length=20)  # '1Y', '3Y', '5Y', etc.

    # Results (stored as JSON for flexibility)
    comparison_data = models.JSONField()
    winner = models.ForeignKey(Fund, on_delete=models.SET_NULL, null=True, related_name='wins')

    # User tracking (optional)
    created_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True)
```

#### 8. FundScore Model
```python
class FundScore(models.Model):
    """Proprietary scoring system"""

    fund = models.OneToOneField(Fund, on_delete=models.CASCADE, related_name='score')

    # Component Scores (0-100)
    performance_score = models.IntegerField()
    risk_score = models.IntegerField()
    cost_score = models.IntegerField()
    consistency_score = models.IntegerField()

    # Overall Score
    overall_score = models.IntegerField()
    score_percentile = models.IntegerField()  # Percentile rank among peers

    # Scoring Metadata
    scoring_date = models.DateTimeField(auto_now=True)
    scoring_version = models.CharField(max_length=10, default='1.0')
```

## 📊 Data Flow Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           Data Collection Flow                           │
└──────────────────────────────────────────────────────────────────────────┘

[External APIs] ─────► [Rate Limiter] ─────► [Data Fetcher]
                              │                     │
                              ▼                     ▼
                       [Redis Cache]         [Data Validator]
                                                   │
                                                   ▼
                                           [Data Normalizer]
                                                   │
                                                   ▼
                                            [PostgreSQL DB]
                                                   │
                                                   ▼
                                          [Analysis Engine]
                                                   │
                         ┌─────────────────────────┴──────────────────────┐
                         ▼                         ▼                      ▼
                  [Scoring Engine]         [ML Models]          [Alert System]
                         │                         │                      │
                         └─────────────────────────┴──────────────────────┘
                                                   │
                                                   ▼
                                              [API Layer]
                                                   │
                                                   ▼
                                           [User Interface]
```

## 📉 Market Data Granularity & Storage

### Data Granularity Levels Supported

The system is designed to handle multiple levels of market data granularity, with appropriate storage strategies for each:

#### 1. **Tick-Level Data** (Highest Granularity)
```python
class FundTick(models.Model):
    """Store individual trade/quote ticks"""
    fund = models.ForeignKey(Fund, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(db_index=True)  # Microsecond precision
    tick_type = models.CharField(max_length=10)  # 'TRADE', 'BID', 'ASK'
    price = models.DecimalField(max_digits=10, decimal_places=4)
    volume = models.BigIntegerField(null=True)
    exchange = models.CharField(max_length=10, blank=True)

    class Meta:
        # Partition by day for performance
        indexes = [
            models.Index(fields=['fund', 'timestamp']),
        ]
```

**Storage Strategy:**
- TimescaleDB hypertables with automatic partitioning
- Retention policy: 30 days for tick data, then aggregate to minute bars
- Compression: Automatic compression after 7 days

#### 2. **Minute-Level Data** (High Frequency)
```python
class FundMinuteBar(models.Model):
    """1-minute OHLCV bars"""
    fund = models.ForeignKey(Fund, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(db_index=True)
    open = models.DecimalField(max_digits=10, decimal_places=4)
    high = models.DecimalField(max_digits=10, decimal_places=4)
    low = models.DecimalField(max_digits=10, decimal_places=4)
    close = models.DecimalField(max_digits=10, decimal_places=4)
    volume = models.BigIntegerField()
    vwap = models.DecimalField(max_digits=10, decimal_places=4, null=True)
    trade_count = models.IntegerField(null=True)

    class Meta:
        unique_together = ['fund', 'timestamp']
```

**Storage Strategy:**
- Keep 6 months of minute data
- Older data aggregated to hourly bars
- ~390 bars per trading day per fund

#### 3. **Hourly Data** (Medium Frequency)
```python
class FundHourlyBar(models.Model):
    """Hourly aggregated data"""
    fund = models.ForeignKey(Fund, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(db_index=True)
    # OHLCV fields...

    # Additional metrics calculated at this level
    volatility = models.DecimalField(max_digits=8, decimal_places=4, null=True)
    rsi = models.DecimalField(max_digits=5, decimal_places=2, null=True)
```

**Storage Strategy:**
- Keep 2 years of hourly data
- ~7 bars per trading day

#### 4. **Daily Data** (Standard Frequency)
Already defined in `FundPerformance` model - this is the primary storage level for long-term analysis.

### Data Volume Estimates

| Granularity | Records/Day/Fund | Storage/Year/Fund | 1000 Funds/Year |
|-------------|------------------|-------------------|-----------------|
| Tick-level  | ~50,000         | ~500 MB          | ~500 GB        |
| Minute bars | 390             | ~1 MB            | ~1 GB          |
| Hourly bars | 7               | ~20 KB           | ~20 MB         |
| Daily bars  | 1               | ~3 KB            | ~3 MB          |

### TimescaleDB Configuration

```sql
-- Create hypertable for tick data
SELECT create_hypertable('fundtick', 'timestamp',
    chunk_time_interval => INTERVAL '1 day');

-- Add compression policy
ALTER TABLE fundtick SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'fund_id',
    timescaledb.compress_orderby = 'timestamp DESC'
);

-- Automatic compression after 7 days
SELECT add_compression_policy('fundtick', INTERVAL '7 days');

-- Continuous aggregates for minute bars
CREATE MATERIALIZED VIEW fund_minute_bars
WITH (timescaledb.continuous) AS
SELECT
    fund_id,
    time_bucket('1 minute', timestamp) AS minute,
    first(price, timestamp) AS open,
    max(price) AS high,
    min(price) AS low,
    last(price, timestamp) AS close,
    sum(volume) AS volume,
    count(*) AS tick_count
FROM fundtick
GROUP BY fund_id, minute;

-- Retention policies
SELECT add_retention_policy('fundtick', INTERVAL '30 days');
SELECT add_retention_policy('fundminutebar', INTERVAL '6 months');
```

### Real-time Data Streaming

```python
# WebSocket support for real-time tick data
class TickConsumer(AsyncWebsocketConsumer):
    """Stream real-time ticks to connected clients"""

    async def connect(self):
        self.fund_ticker = self.scope['url_route']['kwargs']['ticker']
        await self.channel_layer.group_add(
            f'ticks_{self.fund_ticker}',
            self.channel_name
        )
        await self.accept()

    async def receive_tick(self, event):
        """Send tick data to WebSocket client"""
        await self.send(text_data=json.dumps({
            'type': 'tick',
            'timestamp': event['timestamp'],
            'price': event['price'],
            'volume': event['volume']
        }))
```

### Data Source Capabilities by Granularity

| Data Source    | Tick | 1-min | 5-min | 15-min | Hourly | Daily |
|----------------|------|-------|-------|--------|--------|-------|
| Yahoo Finance  | ❌   | ✅*   | ✅    | ✅     | ✅     | ✅    |
| Alpha Vantage  | ❌   | ✅    | ✅    | ✅     | ✅     | ✅    |
| Finnhub       | ✅** | ✅    | ✅    | ✅     | ✅     | ✅    |
| Polygon.io    | ✅   | ✅    | ✅    | ✅     | ✅     | ✅    |

*Limited to recent data (7-60 days depending on interval)
**Premium subscription required for real-time tick data

## 🔌 Data Source Integration

### Base Data Source Class
```python
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class FundDataDTO:
    """Data Transfer Object for standardized fund data"""
    ticker: str
    name: str
    nav: float
    expense_ratio: Optional[float]
    total_assets: Optional[float]
    performance_data: Dict
    holdings: List[Dict]
    metrics: Dict
    last_updated: datetime

class BaseDataSource(ABC):
    """Abstract base class for all data sources"""

    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.rate_limiter = RateLimiter()

    @abstractmethod
    def fetch_fund_info(self, ticker: str) -> FundDataDTO:
        """Fetch basic fund information"""
        pass

    @abstractmethod
    def fetch_historical_prices(self, ticker: str, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Fetch historical price data"""
        pass

    @abstractmethod
    def fetch_holdings(self, ticker: str) -> List[Dict]:
        """Fetch current holdings"""
        pass

    def validate_data(self, data: Dict) -> bool:
        """Validate fetched data meets quality standards"""
        # Implementation for data validation
        pass
```

### Data Sources

#### Yahoo Finance
**Docs:** https://ranaroussi.github.io/yfinance/
- **Purpose:** Primary source for real-time quotes, historical prices, and basic fund info
- **Data Available:**
  - Historical prices (OHLCV)
  - Fund profile and description
  - Expense ratios and fees
  - Top holdings
  - Sector weightings
- **Rate Limits:** No official limit (be respectful)
- **Implementation Priority:** HIGH

#### Alpha Vantage
**Docs:** https://www.alphavantage.co/documentation/
- **Purpose:** Technical indicators and advanced analytics
- **Data Available:**
  - Time series data
  - Technical indicators (SMA, EMA, RSI, MACD, etc.)
  - Fundamental data
  - Economic indicators
- **Rate Limits:** 5 API calls/minute (free), 75 calls/minute (premium)
- **Implementation Priority:** MEDIUM

#### Finnhub
**Docs:** https://finnhub.io/docs/api
- **Purpose:** Real-time data and news sentiment
- **Data Available:**
  - Real-time quotes
  - ETF holdings and exposures
  - News sentiment scores
  - Peer comparison data
- **Rate Limits:** 60 calls/minute (free), 300+ (paid)
- **Implementation Priority:** MEDIUM

#### Polygon.io
**Docs:** https://polygon.io/docs
- **Purpose:** Comprehensive market data and aggregates
- **Data Available:**
  - Tick-level data
  - Aggregated bars (minute, hour, day)
  - Snapshots
  - Technical indicators
- **Rate Limits:** 5 calls/minute (free), unlimited (paid)
- **Implementation Priority:** LOW

## 🔄 Data Pipeline

### Celery Tasks Structure
```python
# feefifofunds/tasks.py

from celery import shared_task
from celery.schedules import crontab

@shared_task
def fetch_daily_prices():
    """Fetch daily price updates for all active funds"""
    pass

@shared_task
def update_fund_holdings():
    """Update holdings data (monthly)"""
    pass

@shared_task
def calculate_metrics():
    """Calculate risk metrics and scores"""
    pass

@shared_task
def generate_recommendations():
    """Run ML models for recommendations"""
    pass

# Celery Beat Schedule
CELERY_BEAT_SCHEDULE = {
    'fetch-daily-prices': {
        'task': 'feefifofunds.tasks.fetch_daily_prices',
        'schedule': crontab(hour=18, minute=0),  # 6 PM daily
    },
    'update-holdings': {
        'task': 'feefifofunds.tasks.update_fund_holdings',
        'schedule': crontab(day_of_month=1, hour=2, minute=0),  # Monthly
    },
    'calculate-metrics': {
        'task': 'feefifofunds.tasks.calculate_metrics',
        'schedule': crontab(hour=19, minute=0),  # 7 PM daily
    },
}
```

## 🛠️ Management Commands

### 1. Fetch Fund Data
```bash
python manage.py fetch_fund --ticker SPY --source yahoo --full
```

### 2. Sync All Funds
```bash
python manage.py sync_all_funds --source all --parallel
```

### 3. Calculate Scores
```bash
python manage.py calculate_scores --category "large-cap" --force
```

### 4. Import Fund List
```bash
python manage.py import_fund_list --file etf_list.csv
```

## 🌐 API Endpoints

### RESTful API Structure
```
/api/v1/
├── funds/
│   ├── GET    /                    # List all funds
│   ├── GET    /{ticker}/           # Get fund details
│   ├── GET    /{ticker}/performance/  # Historical performance
│   ├── GET    /{ticker}/holdings/     # Current holdings
│   └── GET    /{ticker}/metrics/      # Risk metrics
│
├── compare/
│   ├── POST   /                    # Compare multiple funds
│   ├── GET    /saved/              # Get saved comparisons
│   └── GET    /{id}/               # Get specific comparison
│
├── search/
│   ├── GET    /                    # Search funds
│   └── GET    /autocomplete/       # Autocomplete suggestions
│
├── recommendations/
│   ├── GET    /                    # Get recommendations
│   └── POST   /preferences/        # Update preferences
│
└── analytics/
    ├── GET    /market-overview/    # Market overview
    ├── GET    /top-performers/     # Top performing funds
    └── GET    /sector-analysis/    # Sector performance
```

## 💻 Frontend Components

### Interactive Comparison Interface
```
┌──────────────────────────────────────────────────────────────┐
│                    Fund Comparison Tool                      │
├──────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Fund A    │  │   Fund B    │  │   Fund C    │  [+ Add]│
│  └─────────────┘  └─────────────┘  └─────────────┘         │
├──────────────────────────────────────────────────────────────┤
│  Performance Chart                                           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │     📈 Interactive Line Chart with Zoom/Pan           │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  Key Metrics Comparison Table                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Metric          │ Fund A  │ Fund B  │ Fund C         │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │ Expense Ratio   │ 0.03%   │ 0.09%   │ 0.20%         │   │
│  │ 5Y Return       │ 15.2%   │ 14.8%   │ 13.5%         │   │
│  │ Sharpe Ratio    │ 1.45    │ 1.32    │ 1.18          │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  Holdings Overlap Analysis                                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │     🔵 Venn Diagram showing holding overlaps          │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

## 📈 Analytics Features

### 1. Performance Analytics
- Cumulative returns over multiple periods
- Rolling returns and volatility
- Drawdown analysis
- Risk-adjusted returns

### 2. Portfolio Analysis
- Holdings concentration analysis
- Sector/geographic allocation
- Style box analysis
- Overlap detection

### 3. Cost Analysis
- Total cost of ownership calculation
- Fee impact on long-term returns
- Tax efficiency metrics

### 4. Risk Analysis
- Value at Risk (VaR)
- Maximum drawdown
- Beta across different market conditions
- Correlation matrices

## 🤖 Machine Learning Components

### Recommendation Engine
```python
class FundRecommendationEngine:
    """ML-based fund recommendation system"""

    def __init__(self):
        self.similarity_model = self.load_similarity_model()
        self.performance_predictor = self.load_performance_model()
        self.risk_assessor = self.load_risk_model()

    def get_recommendations(self, user_preferences: Dict) -> List[Fund]:
        """
        Generate personalized fund recommendations based on:
        - User risk tolerance
        - Investment goals
        - Time horizon
        - Current portfolio
        - Historical preferences
        """
        pass

    def find_similar_funds(self, fund: Fund, n: int = 10) -> List[Fund]:
        """Find similar funds based on characteristics"""
        pass

    def predict_performance(self, fund: Fund, horizon: str) -> Dict:
        """Predict future performance using ML models"""
        pass
```

## 🚀 Implementation Phases

### Phase 1: Foundation (Weeks 1-2)
- [x] Create Django app structure
- [ ] Implement core models (Fund, FundPerformance, FundHolding)
- [ ] Set up Yahoo Finance integration
- [ ] Create basic import commands
- [ ] Build initial database schema

### Phase 2: Data Pipeline (Weeks 3-4)
- [ ] Implement Celery task queue
- [ ] Add data validation layer
- [ ] Create sync mechanisms
- [ ] Set up Redis caching
- [ ] Add error handling and retry logic

### Phase 3: Analytics Engine (Weeks 5-6)
- [ ] Calculate financial metrics
- [ ] Implement scoring system
- [ ] Build comparison engine
- [ ] Add portfolio analysis tools

### Phase 4: API Development (Weeks 7-8)
- [ ] Design RESTful API
- [ ] Implement authentication
- [ ] Add rate limiting
- [ ] Create API documentation
- [ ] Build WebSocket support for real-time data

### Phase 5: Frontend (Weeks 9-10)
- [ ] Create comparison interface
- [ ] Build interactive charts
- [ ] Implement search and filters
- [ ] Add user dashboard
- [ ] Create mobile-responsive design

### Phase 6: ML & Recommendations (Weeks 11-12)
- [ ] Train similarity models
- [ ] Build recommendation engine
- [ ] Implement backtesting
- [ ] Add performance prediction
- [ ] Create A/B testing framework

## 🔧 Technical Requirements

### Infrastructure
- **Database:** PostgreSQL 14+ with TimescaleDB extension
- **Cache:** Redis 6+
- **Queue:** Celery with Redis broker
- **Search:** PostgreSQL full-text search or Elasticsearch
- **Storage:** AWS S3 for data backups

### Python Dependencies
```requirements
# Core
Django==5.0+
psycopg3==3.1+
redis==5.0+
celery==5.3+

# Data Sources
yfinance==0.2+
alpha-vantage==2.3+
finnhub-python==2.4+
polygon-api-client==1.12+

# Analytics
pandas==2.0+
numpy==1.24+
scipy==1.11+
scikit-learn==1.3+

# API
djangorestframework==3.14+
django-cors-headers==4.2+
channels==4.0+

# Utilities
python-dotenv==1.0+
requests==2.31+
beautifulsoup4==4.12+
```

## 📊 Database Optimization

### Indexes
```sql
-- Performance queries
CREATE INDEX idx_performance_fund_date ON fundperformance(fund_id, date DESC);
CREATE INDEX idx_performance_date ON fundperformance(date);

-- Holdings queries
CREATE INDEX idx_holdings_fund_date ON fundholding(fund_id, as_of_date DESC);
CREATE INDEX idx_holdings_sector ON fundholding(sector);

-- Search optimization
CREATE INDEX idx_fund_name_gin ON fund USING gin(name gin_trgm_ops);
CREATE INDEX idx_fund_category ON fund(category);
```

### Partitioning Strategy
```sql
-- Partition performance data by year
CREATE TABLE fundperformance_2024 PARTITION OF fundperformance
    FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
```

## 🔒 Security Considerations

1. **API Key Management**
   - Store keys in environment variables
   - Rotate keys regularly
   - Use separate keys for dev/staging/production

2. **Data Privacy**
   - Encrypt sensitive user data
   - Implement GDPR compliance
   - Regular security audits

3. **Rate Limiting**
   - Implement per-user rate limits
   - Add DDoS protection
   - Monitor for unusual activity

## 📈 Monitoring & Observability

1. **Application Metrics**
   - API response times
   - Data sync success rates
   - Cache hit ratios
   - Error rates by endpoint

2. **Business Metrics**
   - Most compared funds
   - Popular search queries
   - User engagement metrics
   - Recommendation accuracy

3. **Infrastructure Monitoring**
   - Database performance
   - Redis memory usage
   - Celery queue lengths
   - External API availability

## 🧪 Testing Strategy

### Unit Tests
```python
# tests/test_models.py
class FundModelTests(TestCase):
    def test_fund_creation(self):
        """Test fund instance creation"""
        pass

    def test_performance_calculation(self):
        """Test return calculations"""
        pass
```

### Integration Tests
```python
# tests/test_data_sources.py
class DataSourceTests(TestCase):
    def test_yahoo_finance_integration(self):
        """Test Yahoo Finance API integration"""
        pass

    def test_data_normalization(self):
        """Test data normalization process"""
        pass
```

### Performance Tests
```python
# tests/test_performance.py
class PerformanceTests(TestCase):
    def test_bulk_import_performance(self):
        """Test large dataset import performance"""
        pass

    def test_comparison_query_performance(self):
        """Test complex comparison queries"""
        pass
```

## 📝 Future Enhancements

1. **Advanced Features**
   - Options strategy analyzer
   - Tax-loss harvesting suggestions
   - Rebalancing recommendations
   - Custom index creation

2. **Data Expansion**
   - Add bond funds
   - Include international funds
   - Crypto ETFs
   - Alternative investments

3. **AI/ML Improvements**
   - Natural language queries
   - Sentiment analysis from news
   - Predictive analytics
   - Anomaly detection

4. **User Features**
   - Portfolio tracking
   - Custom alerts
   - Social features (follow other investors)
   - Educational content

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines and code standards.

## 🚢 Deployment & Extraction Guide

### Extracting to Standalone Django Project

When FeeFiFoFunds is ready to be deployed as a standalone service, follow these steps:

1. **Create New Django Project**
```bash
django-admin startproject feefifofunds_standalone
cd feefifofunds_standalone
```

2. **Copy the App**
```bash
cp -r /path/to/feefifofunds ./
```

3. **Update Settings**
```python
# settings.py
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'feefifofunds',  # Add the app
    'rest_framework',
    'corsheaders',
    'channels',
]
```

4. **Configure URLs**
```python
# urls.py
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('feefifofunds.urls')),  # Mount at root
    # or
    path('funds/', include('feefifofunds.urls')),  # Mount at /funds/
]
```

5. **Environment Variables**
Create `.env` file with all required API keys:
```env
# Data Source API Keys
YAHOO_FINANCE_API_KEY=xxx
ALPHA_VANTAGE_API_KEY=xxx
FINNHUB_API_KEY=xxx
POLYGON_API_KEY=xxx

# Redis Configuration
REDIS_URL=redis://localhost:6379

# Database
DATABASE_URL=postgresql://user:pass@localhost/feefifofunds
```

6. **Run Migrations**
```bash
python manage.py migrate
python manage.py collectstatic
```

### Docker Deployment

A Dockerfile for standalone deployment:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy app
COPY feefifofunds/ ./feefifofunds/
COPY manage.py .
COPY config/ ./config/

# Run migrations and start server
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
```

## 📄 License

This project is proprietary software. All rights reserved.
