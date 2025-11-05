# FeeFiFoFunds Architecture

## 📋 Table of Contents

- [System Overview](#system-overview)
- [Database Schema](#database-schema)
- [Application Layers](#application-layers)
- [Data Flow](#data-flow)
- [Performance Optimizations](#performance-optimizations)
- [Future Architecture](#future-architecture)

## 🏗️ System Overview

FeeFiFoFunds is a simplified MVP for tracking asset prices across multiple categories (stocks, crypto, commodities, currencies). The system uses a straightforward Django architecture focused on data ingestion and storage.

### Design Principles

1. **Simplicity First** - MVP focuses on core data ingestion, not complex analytics
2. **Universal Model** - Single Asset table with category field instead of polymorphic inheritance
3. **Multi-source Support** - Track same asset from multiple data providers
4. **Timezone-aware** - All timestamps stored in UTC
5. **Decimal Precision** - Financial data uses Decimal fields for accuracy

### Technology Stack

- **Framework**: Django 5.0+
- **Database**: PostgreSQL 16+
- **Cache**: Redis 7+ (planned for future)
- **Frontend**: Django templates (planned)
- **Monitoring**: Django Debug Toolbar (dev), CodeQL (security)

## 🗄️ Database Schema

### Core Models

#### Asset (feefifofunds_asset)
Universal model representing any trackable asset across 4 categories.

**Key Fields**:
- `ticker` (CharField, unique, indexed) - Primary identifier (e.g., BTC, AAPL, GLD)
- `name` (CharField, indexed) - Full asset name
- `category` (CharField, indexed) - STOCK, CRYPTO, COMMODITY, CURRENCY
- `quote_currency` (CharField) - Pricing currency (USD, EUR, BTC, etc.)
- `description` (TextField) - Optional asset description
- `active` (BooleanField, indexed) - Whether actively tracked
- `created_at` (DateTimeField, indexed) - Auto-managed by TimestampedModel mixin
- `updated_at` (DateTimeField, indexed) - Auto-managed by TimestampedModel mixin

**Relationships**:
- One-to-Many with AssetPrice (historical prices)

**Indexes**:
```sql
CREATE INDEX idx_asset_ticker ON feefifofunds_asset(ticker);
CREATE INDEX idx_asset_category ON feefifofunds_asset(category);
CREATE INDEX idx_asset_active ON feefifofunds_asset(active);
CREATE INDEX idx_asset_created ON feefifofunds_asset(created_at);
CREATE INDEX idx_asset_updated ON feefifofunds_asset(updated_at);
```

**Design Decision**: Category field instead of polymorphic inheritance
- Simpler queries: `Asset.objects.filter(category='CRYPTO')`
- Easy to add new categories
- No complex model inheritance
- Better for MVP stage

#### AssetPrice (feefifofunds_assetprice)
Time-series OHLCV (Open, High, Low, Close, Volume) price data.

**Key Fields**:
- `asset` (ForeignKey) - Related Asset
- `timestamp` (DateTimeField, indexed) - Date/time of price record (UTC)
- `open` (DecimalField) - Opening price
- `high` (DecimalField) - Highest price during period
- `low` (DecimalField) - Lowest price during period
- `close` (DecimalField) - Closing price
- `volume` (DecimalField, nullable) - Trading volume
- `source` (CharField, indexed) - Data source identifier (finnhub, massive, etc.)
- `created_at` (DateTimeField) - When record was created

**Indexes**:
```sql
CREATE INDEX idx_price_asset_timestamp_source ON feefifofunds_assetprice(asset_id, timestamp, source);
CREATE INDEX idx_price_asset_source ON feefifofunds_assetprice(asset_id, source);
CREATE INDEX idx_price_timestamp ON feefifofunds_assetprice(timestamp);
CREATE INDEX idx_price_source ON feefifofunds_assetprice(source);
```

**Unique Constraint**:
```sql
UNIQUE(asset_id, timestamp, source)
```

**Design Decision**: Multi-source support via unique constraint
- Allows tracking same asset from multiple data providers
- Enables data quality comparison
- Example: Compare AAPL prices from Finnhub vs Massive.com
- Future: Merge/reconcile data from multiple sources

### Abstract Base Classes

#### TimestampedModel (utils.models.mixins)
Provides automatic timestamp tracking for all models.

```python
created_at = DateTimeField(
    default=timezone.now,
    editable=False,
    db_index=True
)
updated_at = DateTimeField(
    auto_now=True,
    db_index=True
)
```

**Usage**: `class Asset(TimestampedModel)`

**Location**: Shared across entire Django project in `utils/models/mixins.py`

#### SoftDeleteModel (utils.models.mixins)
Enables soft deletion for audit trail purposes.

```python
is_active = BooleanField(default=True, db_index=True)
deleted_at = DateTimeField(null=True, blank=True)

def delete(self, soft=True):
    if soft:
        self.is_active = False
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_active', 'deleted_at'])
    else:
        super().delete()
```

**Note**: Not currently used in FeeFiFoFunds models, but available for future use.

## 🏛️ Application Layers

### 1. Models Layer (`feefifofunds/models/`)
- Django ORM models: Asset, AssetPrice
- Uses TimestampedModel mixin from utils.models
- Database constraints and indexes defined in models
- Simple model methods (e.g., `__str__`)

### 2. Services Layer (`feefifofunds/services/`)
- Business logic not tied to HTTP requests
- Currently focused on data source integrations

**Data Sources** (`services/data_sources/`):
- `base.py` - Error classes (DataSourceError, DataNotFoundError)
- `finnhub.py` - Finnhub API integration (stocks + crypto)
- `massive.py` - Massive.com/Polygon.io integration (stocks only)

Each data source implements:
- `fetch_historical_prices(ticker, start_date, end_date)` → List[dict]
- Returns standardized format: ticker, timestamp, open, high, low, close, volume
- Handles API-specific transformations

### 3. Views Layer (`feefifofunds/views*.py`)
**Status**: Planned, not yet implemented

Will include:
- `views.py` - HTML views for end users
- `views_json.py` - JSON API endpoints

### 4. Management Commands Layer (`feefifofunds/management/commands/`)
CLI tools for data management:

- **create_asset.py** - Manually create assets
- **load_prices.py** - Load recent price data for a single ticker
- **backfill_prices.py** - Backfill historical prices (single or all assets)
- **populate_popular_assets.py** - Seed database with popular assets

### 5. Admin Interface (`feefifofunds/admin.py`)
Django admin configuration for managing data via web UI:
- Asset admin with list display, filters, search
- AssetPrice admin with list display, filters
- Proper field organization and help text

## 🔄 Data Flow

### 1. Data Ingestion Flow

```
User runs management command
       ↓
Management Command (load_prices or backfill_prices)
       ↓
DataSource Selection (Finnhub or Massive.com)
       ↓
External API Request (with rate limiting awareness)
       ↓
HTTP Response (JSON)
       ↓
Data Transformation (API-specific → standardized dict format)
       ↓
Database Write (AssetPrice.objects.update_or_create)
       ↓
PostgreSQL (with unique constraint enforcement)
```

**Key Points**:
- No automatic scheduling yet (manual commands only)
- `update_or_create` handles duplicates gracefully
- Unique constraint prevents duplicate (asset, timestamp, source) records
- Transactions used for bulk inserts

### 2. Data Source Flow

```
FinnhubDataSource or MassiveDataSource
       ↓
__init__ (load API key from settings)
       ↓
fetch_historical_prices(ticker, start_date, end_date)
       ↓
API Client (finnhub-python or polygon-python)
       ↓
HTTP Request to External API
       ↓
Response Validation (check for errors, no_data)
       ↓
_transform_results(data)
       ↓
List[dict] (standardized format)
```

**Error Handling**:
- `DataNotFoundError` - Ticker not found or no data available
- `DataSourceError` - API errors, network issues, invalid responses

### 3. Management Command Flow

```
User: python manage.py load_prices --ticker AAPL --source massive --days 30
       ↓
Command.handle() - Parse arguments
       ↓
Validate Asset exists (or raise error)
       ↓
Calculate date range (start_date, end_date)
       ↓
Check free tier limits (warn if exceeded)
       ↓
_fetch_price_data() - Call data source
       ↓
_save_prices() - Bulk insert/update with transaction
       ↓
Print summary (created count, updated count)
```

**Features**:
- Dry-run mode (`--dry-run`) - Preview without saving
- Batch processing (`--all`) - Process multiple assets
- Free tier warnings - Alert when exceeding data source limits

## ⚡ Performance Optimizations

### 1. Database Optimizations

**Indexes**:
- All foreign keys indexed automatically by Django
- Composite index on (asset, timestamp, source) for common queries
- Individual indexes on timestamp and source for filtering
- Indexes on Asset fields (ticker, category, active)

**Query Patterns**:
```python
# Efficient: Uses composite index
prices = AssetPrice.objects.filter(
    asset=asset,
    timestamp__gte=start_date,
    source='finnhub'
).order_by('-timestamp')

# Efficient: Uses ticker index
asset = Asset.objects.get(ticker='BTC')

# Efficient: Uses category index
crypto_assets = Asset.objects.filter(category='CRYPTO', active=True)
```

### 2. Bulk Operations

**Management Commands Use Transactions**:
```python
@transaction.atomic
def _save_prices(self, asset, price_data, source):
    for data in price_data:
        AssetPrice.objects.update_or_create(
            asset=asset,
            timestamp=data['timestamp'],
            source=source,
            defaults={...}
        )
```

**Benefits**:
- All-or-nothing: Rollback on error
- Faster than individual commits
- Consistent database state

### 3. Data Source Rate Limiting

**Awareness, Not Enforcement**:
- Commands display warnings when exceeding free tier limits
- User responsibility to stay within limits
- Future: Implement actual rate limiting with Redis

**Free Tier Limits**:
- Finnhub: 60 calls/minute, ~1 year historical
- Massive.com: ~100 requests/second, 2 years historical

## 🚧 Future Architecture

### Planned Enhancements

#### 1. Caching Layer (Phase 2)
```
Redis Cache
├── Asset metadata (1 hour TTL)
├── Latest prices (20 min TTL)
└── Price history (1 hour TTL)
```

**Cache Keys**:
```python
cache_key = f"feefifofunds:asset:{ticker}"
cache_key = f"feefifofunds:prices:{ticker}:{source}:{timeframe}"
```

#### 2. Metrics Calculation (Phase 2)
**New Model**: `AssetMetrics`
```python
class AssetMetrics(TimestampedModel):
    asset = ForeignKey(Asset)
    timeframe = CharField()  # 1D, 7D, 30D, 90D, 1Y, ALL
    calculation_date = DateField()
    total_return = DecimalField()
    volatility = DecimalField()
    sharpe_ratio = DecimalField()
    max_drawdown = DecimalField()
```

**Calculation Service**:
```python
class MetricsCalculator:
    def calculate_returns(prices) -> Decimal
    def calculate_volatility(prices) -> Decimal
    def calculate_sharpe_ratio(prices, risk_free_rate) -> Decimal
```

#### 3. API Endpoints (Phase 3)
```
/feefifofunds/api/assets/                    # List assets
/feefifofunds/api/assets/<ticker>/           # Asset detail
/feefifofunds/api/assets/<ticker>/prices/    # Price history
/feefifofunds/api/assets/<ticker>/metrics/   # Calculated metrics
```

#### 4. Real-time Updates (Phase 4)
- **WebSocket Server** (Django Channels)
- **Redis Pub/Sub** for event broadcasting
- **Celery Beat** for scheduled price updates

#### 5. Advanced Features (Phase 5+)
- Asset comparison engine
- Portfolio tracking
- User authentication
- Custom alerts
- Machine learning predictions

### Scalability Considerations

**Current Scale** (MVP):
- 100-1,000 assets
- Manual data updates
- Single server deployment
- Admin-only interface

**Future Scale**:
- 10,000+ assets
- Automated updates (hourly/daily)
- Multi-server deployment
- Public API + frontend

**Scaling Strategy**:
1. **Vertical** first - Larger database server
2. **Caching** next - Redis for frequently accessed data
3. **Read Replicas** - For price history queries
4. **Horizontal** - Multiple app servers with load balancer

## 📐 Design Decisions

### Why Universal Asset Model?
**Chosen**: Single table with category field
**Alternative**: Polymorphic inheritance (Stock, Crypto, Commodity models)

**Reasoning**:
- ✅ Simpler queries and relationships
- ✅ Easy to add new categories
- ✅ Better for MVP stage
- ✅ Less database tables
- ❌ Can't have category-specific fields (not needed for MVP)

### Why Multi-Source Support?
**Chosen**: Unique constraint on (asset, timestamp, source)
**Alternative**: Single source per asset

**Reasoning**:
- ✅ Compare data quality across sources
- ✅ Fallback if one source fails
- ✅ Verify accuracy with multiple providers
- ✅ Future: Merge/reconcile data
- ❌ More storage required (acceptable for MVP)

### Why Decimal for Prices?
**Chosen**: DecimalField(max_digits=20, decimal_places=8)
**Alternative**: FloatField

**Reasoning**:
- ✅ Exact precision for financial calculations
- ✅ No floating-point errors
- ✅ Industry standard for financial data
- ❌ Slightly slower than float (negligible for MVP)

### Why Django (not FastAPI)?
**Chosen**: Django
**Alternative**: FastAPI, Flask

**Reasoning**:
- ✅ Integrated admin interface (huge for MVP)
- ✅ ORM with migration support
- ✅ Part of existing Django project (portability)
- ✅ Built-in authentication
- ❌ Heavier than FastAPI (not a concern for MVP)

### Why PostgreSQL?
**Chosen**: PostgreSQL 16+
**Alternative**: MySQL, TimescaleDB

**Reasoning**:
- ✅ Time-series data support (native)
- ✅ Already used by parent project
- ✅ Excellent indexing for timestamps
- ✅ JSON fields for future flexibility
- ❌ TimescaleDB would be better for huge scale (overkill for MVP)

### Why Management Commands (not Celery)?
**Chosen**: Management commands for data loading
**Alternative**: Celery tasks with Beat scheduler

**Reasoning**:
- ✅ Simpler for MVP (no Celery setup required)
- ✅ Manual control over data ingestion
- ✅ Easy to debug and test
- ✅ Good for development phase
- ❌ Not suitable for production automation (will add Celery in Phase 2)

## 📚 References

- [Django Documentation](https://docs.djangoproject.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Finnhub API Documentation](https://finnhub.io/docs/api)
- [Polygon.io API Documentation](https://polygon.io/docs)
