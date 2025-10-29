# FeeFiFoFunds Architecture

## 📋 Table of Contents

- [System Overview](#system-overview)
- [Database Schema](#database-schema)
- [Application Layers](#application-layers)
- [Data Flow](#data-flow)
- [API Design](#api-design)
- [Performance Optimizations](#performance-optimizations)
- [Future Architecture](#future-architecture)

## 🏗️ System Overview

FeeFiFoFunds follows a classic Django layered architecture with additional service layers for business logic. The system is designed to be portable within the parent project while maintaining clear boundaries.

### Design Principles

1. **Portability** - All code self-contained in `feefifofunds/` directory
2. **Separation of Concerns** - Clear boundaries between layers
3. **Data Source Agnostic** - Pluggable data source implementations
4. **Performance First** - Caching, indexing, and TimescaleDB for time-series data
5. **Test-Driven** - Comprehensive test coverage for critical paths

### Technology Stack

- **Framework**: Django 5.0+
- **Database**: PostgreSQL 16+ with TimescaleDB extension
- **Cache**: Redis 7+
- **Task Queue**: Celery with Redis broker
- **Frontend**: Django templates + Vanilla JS (no framework dependency)
- **Monitoring**: Django Debug Toolbar (dev), Flower (Celery), CodeQL (security)

## 🗄️ Database Schema

### Core Models

#### Fund (feefifofunds_fund)
Primary entity representing an ETF or mutual fund.

**Key Fields**:
- `ticker` (CharField, unique, indexed) - Primary identifier
- `name` (CharField, indexed) - Full fund name
- `slug` (SlugField, unique) - URL-friendly identifier
- `fund_type` (CharField) - ETF, MUTUAL, INDEX, etc.
- `asset_class` (CharField) - EQUITY, BOND, MIXED, etc.
- `expense_ratio` (DecimalField) - Annual fee as percentage
- `current_price` (DecimalField) - Most recent NAV/price
- `aum` (DecimalField) - Assets Under Management (millions)
- `is_active` (BooleanField) - Soft delete flag

**Relationships**:
- One-to-Many with FundPerformance (historical prices)
- One-to-Many with FundHolding (portfolio holdings)
- One-to-Many with FundMetrics (calculated metrics)
- One-to-Many with DataSync (sync history)

**Indexes**:
```sql
CREATE INDEX idx_fund_ticker_active ON feefifofunds_fund(ticker, is_active);
CREATE INDEX idx_fund_type_class ON feefifofunds_fund(fund_type, asset_class);
CREATE INDEX idx_fund_expense ON feefifofunds_fund(expense_ratio);
```

#### FundPerformance (feefifofunds_performance)
Time-series OHLCV (Open, High, Low, Close, Volume) data.

**Key Fields**:
- `fund_id` (ForeignKey) - Related fund
- `date` (DateField, indexed) - Trading date
- `interval` (CharField) - 1D, 1W, 1M, etc.
- `close_price` (DecimalField) - Closing price/NAV
- `volume` (BigIntegerField) - Trading volume
- `daily_return` (DecimalField) - Calculated return

**TimescaleDB Integration**:
- Converted to hypertable partitioned by date
- Compression enabled for data older than 7 days
- Continuous aggregates for hourly/daily rollups

**Indexes**:
```sql
CREATE INDEX idx_perf_fund_date ON feefifofunds_performance(fund_id, date DESC);
CREATE INDEX idx_perf_date_fund ON feefifofunds_performance(date, fund_id);
CREATE INDEX idx_perf_interval ON feefifofunds_performance(interval, date DESC);
```

**Unique Constraint**:
```sql
UNIQUE(fund_id, date, interval)
```

#### FundHolding (feefifofunds_holding)
Portfolio holdings and allocations.

**Key Fields**:
- `fund_id` (ForeignKey) - Parent fund
- `ticker` (CharField) - Holding ticker
- `name` (CharField) - Holding name
- `weight` (DecimalField) - Portfolio weight as percentage
- `sector` (CharField, indexed) - Sector classification
- `as_of_date` (DateField, indexed) - Reporting date

**Indexes**:
```sql
CREATE INDEX idx_holding_fund_weight ON feefifofunds_holding(fund_id, weight DESC);
CREATE INDEX idx_holding_fund_date ON feefifofunds_holding(fund_id, as_of_date DESC);
CREATE INDEX idx_holding_sector ON feefifofunds_holding(sector, weight DESC);
```

**Unique Constraint**:
```sql
UNIQUE(fund_id, ticker, as_of_date)
```

#### FundMetrics (feefifofunds_metrics)
Pre-calculated financial metrics and ratios.

**Key Fields**:
- `fund_id` (ForeignKey) - Related fund
- `time_frame` (CharField) - 1M, 3M, 6M, YTD, 1Y, 3Y, 5Y, 10Y, ALL
- `calculation_date` (DateField, indexed) - When calculated
- `total_return` (DecimalField) - Total return percentage
- `annualized_return` (DecimalField) - Annualized return
- `volatility` (DecimalField) - Standard deviation
- `sharpe_ratio` (DecimalField) - Risk-adjusted return
- `max_drawdown` (DecimalField) - Maximum drawdown
- `overall_score` (IntegerField, indexed) - Composite score (0-100)

**Indexes**:
```sql
CREATE INDEX idx_metrics_fund_date ON feefifofunds_metrics(fund_id, calculation_date DESC);
CREATE INDEX idx_metrics_score ON feefifofunds_metrics(overall_score DESC);
CREATE INDEX idx_metrics_timeframe ON feefifofunds_metrics(time_frame, overall_score DESC);
```

**Unique Constraint**:
```sql
UNIQUE(fund_id, calculation_date, time_frame)
```

#### DataSource (feefifofunds_datasource)
External API provider configuration and monitoring.

**Key Fields**:
- `name` (CharField, unique) - Source identifier (e.g., "alpha_vantage")
- `display_name` (CharField) - Human-readable name
- `status` (CharField) - ACTIVE, INACTIVE, ERROR, RATE_LIMITED
- `rate_limit_requests` (IntegerField) - Max requests allowed
- `rate_limit_period_seconds` (IntegerField) - Time window
- `requests_today` (IntegerField) - Current request count
- `reliability_score` (DecimalField) - Success rate (0-100)
- `consecutive_failures` (IntegerField) - Failure counter

**Indexes**:
```sql
CREATE INDEX idx_source_priority_status ON feefifofunds_datasource(priority DESC, status);
CREATE INDEX idx_source_status_sync ON feefifofunds_datasource(status, last_successful_sync DESC);
```

#### DataSync (feefifofunds_datasync)
Synchronization history and audit trail.

**Key Fields**:
- `data_source_id` (ForeignKey) - Source used
- `fund_id` (ForeignKey, nullable) - Target fund
- `sync_type` (CharField) - FUND_INFO, PRICES, HOLDINGS, etc.
- `status` (CharField) - PENDING, IN_PROGRESS, SUCCESS, FAILED
- `started_at` (DateTimeField) - Start timestamp
- `completed_at` (DateTimeField) - Completion timestamp
- `records_created` (IntegerField) - New records created
- `records_updated` (IntegerField) - Existing records updated

**Indexes**:
```sql
CREATE INDEX idx_sync_started ON feefifofunds_datasync(started_at DESC);
CREATE INDEX idx_sync_source ON feefifofunds_datasync(data_source_id, started_at DESC);
CREATE INDEX idx_sync_fund ON feefifofunds_datasync(fund_id, started_at DESC);
```

### Abstract Base Classes

#### TimestampedModel
Provides automatic timestamp tracking for all models.

```python
created_at = DateTimeField(auto_now_add=True, indexed=True)
updated_at = DateTimeField(auto_now=True, indexed=True)
```

#### SoftDeleteModel
Enables soft deletion for audit trail purposes.

```python
is_active = BooleanField(default=True, indexed=True)
deleted_at = DateTimeField(null=True, blank=True)

def delete(soft=True):
    if soft:
        self.is_active = False
        self.deleted_at = timezone.now()
        self.save()
    else:
        super().delete()
```

## 🏛️ Application Layers

### 1. Models Layer (`feefifofunds/models/`)
- Django ORM models
- Business logic as model methods/properties
- Database constraints and indexes
- Soft delete and timestamp mixins

### 2. Services Layer (`feefifofunds/services/`)
- Business logic not tied to HTTP requests
- Reusable across views, management commands, and tasks
- Three main service types:
  - **Data Sources** - External API integrations
  - **Calculators** - Financial metrics computation
  - **Validators** - Data quality checks
  - **Comparison** - Fund comparison logic

### 3. Views Layer (`feefifofunds/views*.py`)
- HTTP request/response handling
- Three view modules:
  - `views.py` - HTML views for end users
  - `views_json.py` - JSON API endpoints
  - `views_comparison.py` - Comparison-specific views
- Thin views - delegate to services
- Session-based authentication (leverages parent project's auth)

### 4. Management Commands Layer (`feefifofunds/management/commands/`)
- CLI tools for batch operations
- Data fetching and synchronization
- Metrics calculation
- System health checks

### 5. Tasks Layer (`feefifofunds/tasks.py`) - PLANNED
- Celery background tasks
- Scheduled data updates
- Async processing for long-running operations

## 🔄 Data Flow

### 1. Data Ingestion Flow

```
External API (Alpha Vantage, Polygon.io, etc.)
       ↓
BaseDataSource (with rate limiting & caching)
       ↓
HTTP Request (with retry & timeout)
       ↓
Response JSON
       ↓
DTO (FundDataDTO, PerformanceDataDTO, etc.)
       ↓
DataValidator (sanity checks & normalization)
       ↓
Django Model (Fund, FundPerformance, etc.)
       ↓
PostgreSQL Database (with TimescaleDB for time-series)
       ↓
Cache (Redis) for frequently accessed data
```

### 2. Metrics Calculation Flow

```
FundPerformance Records (raw OHLCV data)
       ↓
MetricsCalculator Service
       ↓
Statistical Calculations (returns, volatility, ratios)
       ↓
FundMetrics Model (pre-calculated results)
       ↓
Database (with caching)
```

### 3. API Request Flow

```
HTTP Request
       ↓
URL Router (urls.py)
       ↓
View Function (views*.py)
       ↓
Cache Check (Redis)
       ├─ HIT → Return cached response
       └─ MISS ↓
Model Query (with select_related/prefetch_related)
       ↓
Serialization (to dict/JSON)
       ↓
Cache Write (Redis)
       ↓
HTTP Response (JSON or HTML)
```

### 4. Comparison Flow

```
User Request (compare 2-10 funds)
       ↓
ComparisonEngine Service
       ↓
Fetch Fund Models + Related Data
       ↓
Parallel Fetching of:
  - Latest Metrics (FundMetrics)
  - Performance Data (FundPerformance)
  - Holdings (FundHolding)
       ↓
Comparison Calculations:
  - Performance Comparison
  - Risk Comparison
  - Cost Comparison
  - Holdings Overlap Analysis
       ↓
Comparison Results (dict)
       ↓
Cache (Redis - 20 min TTL)
       ↓
JSON Response or HTML Template
```

## 🌐 API Design

### URL Structure

```
/feefifofunds/
├── (home page)
├── funds/
│   ├── (list view)
│   └── <slug>/
│       └── (detail view)
├── compare/
│   └── (comparison tool)
└── api/
    ├── funds/
    │   ├── (fund list JSON)
    │   └── <slug>/
    │       ├── (fund detail JSON)
    │       ├── performance/
    │       │   └── (OHLCV data JSON)
    │       └── holdings/
    │           └── (holdings data JSON)
    └── compare/
        └── (comparison JSON - POST or GET)
```

### Authentication

Currently uses session-based authentication from parent project (django-allauth):
- `@login_required` decorator for protected views
- No separate API authentication (uses Django sessions)
- Future: Consider API tokens for external integrations

### Response Format

**Success Response**:
```json
{
  "ticker": "SPY",
  "name": "SPDR S&P 500 ETF Trust",
  "current_price": 450.25,
  "expense_ratio": 0.0945,
  ...
}
```

**Error Response**:
```json
{
  "error": "Fund not found",
  "status": 404
}
```

**List Response with Pagination**:
```json
{
  "count": 1000,
  "next": 40,
  "previous": 0,
  "results": [...]
}
```

## ⚡ Performance Optimizations

### 1. Database Optimizations

**Indexes**:
- All foreign keys indexed
- Composite indexes for common query patterns
- Partial indexes for active records only

**Query Optimization**:
```python
# Bad: N+1 queries
funds = Fund.objects.all()
for fund in funds:
    metrics = fund.get_latest_metrics()  # Separate query each iteration

# Good: Prefetch related data
funds = Fund.objects.all().prefetch_related('metrics')
```

**TimescaleDB**:
- Hypertables for time-series data (FundPerformance)
- Automatic partitioning by date
- Compression for old data (7+ days)
- Continuous aggregates for rollups

### 2. Caching Strategy

**Cache Levels**:
1. **Application Cache** (Redis) - 20 min to 1 hour TTL
   - Fund info
   - Latest metrics
   - Comparison results

2. **Query Cache** (Django ORM) - Request lifetime
   - select_related for ForeignKeys
   - prefetch_related for reverse FKs
   - only() and defer() for field selection

3. **Template Fragment Cache** - PLANNED
   - Common UI components
   - Fund cards
   - Performance charts

**Cache Keys**:
```python
cache_key = f"feefifofunds:fund:{ticker}"
cache_key = f"feefifofunds:comparison:{'-'.join(sorted(tickers))}"
cache_key = f"feefifofunds:metrics:{fund_id}:{time_frame}"
```

### 3. Rate Limiting

**Redis-backed Rate Limiting**:
- Atomic increment operations
- Distributed across multiple workers
- Prevents race conditions

**Per-Source Limits**:
```python
# Alpha Vantage Free: 25 requests/day
rate_limit_requests = 2000
rate_limit_period = 3600

# Alpha Vantage Free: 5 requests/minute
rate_limit_requests = 5
rate_limit_period = 60
```

### 4. Data Compression

**TimescaleDB Compression**:
```sql
-- Enable compression on hypertable
ALTER TABLE feefifofunds_performance SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'fund_id',
    timescaledb.compress_orderby = 'date DESC'
);

-- Auto-compress data older than 7 days
SELECT add_compression_policy('feefifofunds_performance', INTERVAL '7 days');
```

**Redis Compression**:
- Gzip compression enabled in cache backend
- Automatic for values > 100 bytes
- Significant memory savings for large datasets

## 🚧 Future Architecture

### Planned Enhancements

#### 1. Microservices (Optional)
If load increases significantly:
- **Data Fetcher Service** - Dedicated service for external API calls
- **Metrics Calculator Service** - Heavy computation offloaded
- **API Gateway** - Unified entry point

#### 2. Real-time Updates
- **WebSocket Server** (Django Channels)
- **Redis Pub/Sub** for event broadcasting
- **Live price updates** for watched funds

#### 3. Machine Learning Pipeline
- **ML Service** - Separate Python service
- **Model Storage** - S3 or similar
- **Prediction API** - Performance forecasting
- **Recommendation Engine** - Personalized suggestions

#### 4. Advanced Caching
- **CDN** for static assets
- **Varnish** for HTTP caching
- **GraphQL** with DataLoader for query optimization

#### 5. Monitoring & Observability
- **Prometheus** for metrics collection
- **Grafana** for dashboards
- **Sentry** for error tracking
- **ELK Stack** for log aggregation

### Scalability Considerations

**Current Scale** (acceptable):
- 1,000-10,000 funds
- 100-1,000 daily active users
- Single server deployment

**Future Scale** (requires changes):
- 100,000+ funds
- 10,000+ concurrent users
- Multi-region deployment
- High-frequency data updates

**Scaling Strategy**:
1. **Vertical** first - Larger server, more RAM, faster disk
2. **Horizontal** next - Load balancer + multiple app servers
3. **Database** - Read replicas for queries, primary for writes
4. **Cache** - Redis cluster with replication
5. **Celery** - Dedicated worker pool per task type

## 📐 Design Decisions

### Why Django (not FastAPI)?
- Integrated admin interface
- ORM with migration support
- Built-in authentication
- Template system
- Portability within existing Django project

### Why TimescaleDB?
- Efficient time-series queries
- Automatic partitioning
- Compression for storage savings
- Compatible with PostgreSQL (no separate database)

### Why Redis?
- Fast in-memory cache
- Atomic operations for rate limiting
- Celery broker support
- Pub/Sub for future real-time features

### Why No DRF (Django REST Framework)?
- Simple JSON endpoints sufficient for current needs
- Avoid dependency for internal-use API
- Django's JsonResponse adequate
- Can add later if needed

### Why Separate Service Layer?
- Reusability across views, commands, and tasks
- Testability without HTTP overhead
- Clear separation of concerns
- Business logic in one place

## 📚 References

- [Django Documentation](https://docs.djangoproject.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [TimescaleDB Documentation](https://docs.timescale.com/)
- [Redis Documentation](https://redis.io/documentation)
- [Celery Documentation](https://docs.celeryproject.org/)
