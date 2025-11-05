# FeeFiFoFunds

> **Multi-Asset Price Tracking Platform (MVP)**

A Django-based platform for tracking and analyzing prices across multiple asset classes: stocks, cryptocurrencies, commodities, and currencies. Currently in MVP stage with core data ingestion infrastructure complete.

## 🚀 Quick Start

```bash
# Install dependencies
uv pip install -r requirements/base.txt

# Run migrations
python manage.py migrate

# Create an asset
python manage.py create_asset --ticker BTC --name Bitcoin --category CRYPTO

# Load price data
python manage.py load_prices --ticker BTC --source finnhub --days 30

# Access Django admin
python manage.py createsuperuser
open http://localhost:8000/admin/
```

For detailed setup instructions, see [DEVELOPMENT.md](DEVELOPMENT.md).

## 📊 Current Status

**Phase**: MVP - Data Ingestion Infrastructure (Phase 1 of 6)

### ✅ Implemented (Ready to Use)

- ✅ **Universal Asset Model** - Single model supporting stocks, crypto, commodities, and currencies
- ✅ **OHLCV Price Tracking** - Time-series price data with multi-source support
- ✅ **Django Admin** - Full-featured admin interface for assets and prices
- ✅ **Data Source Framework** - Pluggable data source implementations
- ✅ **Finnhub Integration** - Stocks and crypto data (~1 year historical on free tier)
- ✅ **Massive.com Integration** - Stock data via Polygon.io (2 years historical on free tier)
- ✅ **Management Commands** - CLI tools for creating assets and loading prices
- ✅ **Timestamp-aware Storage** - UTC timestamps with proper timezone handling
- ✅ **Multi-source Tracking** - Compare data from multiple sources for the same asset

### 🚧 In Progress

- 🚧 **Frontend Views** - Basic structure exists, needs implementation
- 🚧 **API Endpoints** - JSON API for accessing asset data

### 📋 Planned

- 📋 **Metrics Calculation** - Returns, volatility, Sharpe ratio, etc.
- 📋 **Asset Comparison** - Compare multiple assets side-by-side
- 📋 **Additional Data Sources** - Alpha Vantage, CoinGecko, Yahoo Finance
- 📋 **Advanced Analytics** - Technical indicators, trend analysis
- 📋 **Real-time Updates** - WebSocket integration for live prices
- 📋 **Portfolio Tracking** - User portfolios and watchlists

## 🏗️ Architecture

### Core Components

```
feefifofunds/
├── models/              # ✅ Database models (complete)
│   ├── asset.py         # Universal Asset model (4 categories)
│   └── price.py         # AssetPrice model (OHLCV data)
│
├── services/            # 🚧 Business logic layer
│   └── data_sources/    # ✅ External API integrations (complete)
│       ├── base.py      # Error classes
│       ├── finnhub.py   # Finnhub implementation (stocks + crypto)
│       └── massive.py   # Massive.com/Polygon.io (stocks only)
│
├── management/          # ✅ CLI commands (complete)
│   └── commands/
│       ├── create_asset.py          # Create assets manually
│       ├── load_prices.py           # Load recent price data
│       ├── backfill_prices.py       # Backfill historical prices
│       └── populate_popular_assets.py  # Seed popular assets
│
├── admin.py             # ✅ Django admin (complete)
└── urls.py              # 📋 URL routing (planned)
```

### Technology Stack

- **Backend**: Django 5.0+
- **Database**: PostgreSQL 16+
- **Cache**: Redis 7+ (planned)
- **Frontend**: Django templates (planned)

### Key Design Decisions

1. **Simplicity** - MVP focuses on core data ingestion, not complex analysis
2. **Universal Model** - Single Asset table with category field (not polymorphic)
3. **Multi-source Support** - Unique constraint on (asset, timestamp, source) allows comparing data sources
4. **Timezone-aware** - All timestamps stored in UTC
5. **Decimal Precision** - Financial data uses Decimal fields (not float)

## 📚 Documentation

- **[DEVELOPMENT.md](DEVELOPMENT.md)** - Setup, testing, and contribution guide
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Technical architecture and design decisions

## 🎯 Project Vision

### Short-term Goals (MVP Phase)

1. ✅ Implement universal asset model
2. ✅ Build data ingestion pipeline
3. ✅ Integrate 2+ data sources
4. 🚧 Create basic frontend views
5. 📋 Add metrics calculation

### Long-term Vision

Evolve into a comprehensive multi-asset analysis platform that:
1. **Aggregates** data from multiple free and premium sources
2. **Analyzes** price trends, volatility, and correlations
3. **Compares** assets across different classes
4. **Predicts** future performance using machine learning
5. **Recommends** optimal assets based on user goals

## 🛠️ Management Commands

### Asset Management

```bash
# Create a new asset
python manage.py create_asset --ticker BTC --name Bitcoin --category CRYPTO
python manage.py create_asset --ticker AAPL --name "Apple Inc" --category STOCK

# Populate popular assets (stocks, crypto, commodities, currencies)
python manage.py populate_popular_assets
```

### Price Data Loading

```bash
# Load recent prices (default: 7 days)
python manage.py load_prices --ticker AAPL --source massive --days 30

# Backfill historical prices
python manage.py backfill_prices --ticker BTC --source finnhub --days 365

# Backfill all active assets
python manage.py backfill_prices --source massive --days 730 --all

# Dry-run mode (preview without saving)
python manage.py load_prices --ticker AAPL --source massive --days 7 --dry-run
```

### Data Source Limits (Free Tier)

- **Finnhub**: ~1 year historical, 60 calls/minute
- **Massive.com (Polygon.io)**: 2 years historical, ~100 requests/second

## 🧪 Testing

```bash
# Run all tests
python manage.py test feefifofunds

# Run with coverage
coverage run --source='feefifofunds' manage.py test feefifofunds
coverage report
```

## 📦 Database Schema

### Asset Model

Universal model supporting 4 asset categories:

| Field | Type | Description |
|-------|------|-------------|
| ticker | CharField | Unique ticker symbol (e.g., BTC, AAPL, GLD) |
| name | CharField | Full asset name |
| category | CharField | STOCK, CRYPTO, COMMODITY, CURRENCY |
| quote_currency | CharField | Pricing currency (USD, EUR, BTC, etc.) |
| description | TextField | Optional description |
| active | BooleanField | Whether actively tracked |
| created_at | DateTimeField | Auto-managed by TimestampedModel |
| updated_at | DateTimeField | Auto-managed by TimestampedModel |

### AssetPrice Model

OHLCV price data with multi-source support:

| Field | Type | Description |
|-------|------|-------------|
| asset | ForeignKey | Related Asset |
| timestamp | DateTimeField | Date/time of price record (UTC) |
| open | DecimalField | Opening price |
| high | DecimalField | Highest price during period |
| low | DecimalField | Lowest price during period |
| close | DecimalField | Closing price |
| volume | DecimalField | Trading volume (optional) |
| source | CharField | Data source (finnhub, massive, etc.) |
| created_at | DateTimeField | When record was created |

**Unique Constraint**: `(asset, timestamp, source)` - Allows comparing data from multiple sources

**Indexes**:
- Composite: (asset, timestamp, source)
- Composite: (asset, source)
- Single: timestamp, source

## 🤝 Contributing

1. Read [DEVELOPMENT.md](DEVELOPMENT.md) for setup and guidelines
2. Create a feature branch
3. Make changes and add tests
4. Run pre-commit hooks: `pre-commit run --all-files`
5. Create pull request with clear description

### Code Style

- Follow PEP 8 (enforced by Ruff)
- Use type hints
- Write docstrings for public methods
- Keep functions small and focused
- Add tests for new features

## 📝 Current Limitations

**MVP Scope**:
- No frontend views yet (admin only)
- No API endpoints
- No metrics calculation
- No asset comparison
- No portfolio tracking
- No real-time updates

**Data Sources**:
- Limited to Finnhub and Massive.com
- Free tier restrictions apply
- No automated scheduled updates (manual commands only)

## 🗺️ Roadmap

### Phase 1: MVP - Data Ingestion (Current)
- ✅ Universal asset model
- ✅ OHLCV price tracking
- ✅ Multi-source data ingestion
- ✅ Management commands

### Phase 2: Basic Analytics
- Metrics calculation (returns, volatility)
- Simple comparisons
- Basic visualizations

### Phase 3: Frontend & API
- Django templates for viewing assets
- JSON API endpoints
- Chart integration

### Phase 4: Advanced Features
- Additional data sources
- Real-time updates
- Portfolio tracking
- User authentication

### Phase 5: Machine Learning
- Price prediction models
- Asset similarity
- Trend detection

### Phase 6: Production
- Load testing
- Monitoring
- Documentation
- User acceptance testing

## 📄 License

This project is part of the aaronspindler.com codebase. All rights reserved.

## 🔗 Related Projects

- **Parent Project**: [aaronspindler.com](https://aaronspindler.com)
- **Blog**: Similar Django patterns for content management
- **Photos App**: Shared Django admin patterns

## 📧 Contact

For questions or suggestions, please create a GitHub issue or contact the maintainers.
