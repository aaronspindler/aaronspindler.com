# FeeFiFoFunds Development Guide

## 📋 Table of Contents

- [Project Overview](#project-overview)
- [Current Implementation Status](#current-implementation-status)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Common Development Tasks](#common-development-tasks)
- [Testing](#testing)
- [Debugging](#debugging)
- [Contribution Guidelines](#contribution-guidelines)

## 🎯 Project Overview

FeeFiFoFunds is a Django-based multi-asset price tracking platform. The project is currently in MVP stage with focus on data ingestion infrastructure for stocks, cryptocurrencies, commodities, and currencies.

### Goals

- **Primary**: Build reliable data ingestion pipeline for multi-asset price tracking
- **Secondary**: Enable asset comparison and basic analytics
- **Future**: Advanced analytics and machine learning predictions

## ✅ Current Implementation Status

### Completed Components (MVP Phase 1)

#### 🗄️ Database Models (100%)
- **Asset** - Universal model for all asset types (4 categories) stored in PostgreSQL
- **AssetPrice** - OHLCV price data stored in QuestDB for time-series performance
- Uses TimestampedModel mixin from `utils/models/mixins.py`

#### 🔌 Data Sources (100%)
- **Kraken CSV Ingestion** - Fast QuestDB ILP ingestion (50K-100K records/sec)
- **FinnhubDataSource** - Stocks and crypto (~1 year historical on free tier)
- **MassiveDataSource** - Stocks via Polygon.io (2 years historical on free tier)
- Standardized data transformation pipeline
- Error handling (DataSourceError, DataNotFoundError)

#### 🛠️ Management Commands (100%)
- **setup_questdb_schema** - Initialize QuestDB tables
- **create_asset** - Create assets manually
- **ingest_sequential** - Fast QuestDB ILP ingestion from Kraken CSV
- **load_prices** - Load recent price data from APIs
- **backfill_prices** - Backfill historical prices (single or all assets)
- Dry-run mode support
- Free tier warnings

#### 🎨 Admin Interface (100%)
- Asset admin with filters and search (PostgreSQL)
- AssetPrice data managed via raw SQL (QuestDB)
- Proper field organization and help text

### In Progress

- **Frontend Views** - Template structure needs implementation
- **API Endpoints** - JSON endpoints planned

### Planned (Future Phases)

- **Metrics Calculation** - Returns, volatility, Sharpe ratio
- **Asset Comparison** - Side-by-side comparisons
- **Additional Data Sources** - Alpha Vantage, CoinGecko, Yahoo Finance
- **Real-time Updates** - WebSocket integration
- **Portfolio Tracking** - User portfolios and watchlists

## 🚀 Development Setup

### Prerequisites

- Python 3.13+
- PostgreSQL 16+
- QuestDB 8.2.0+
- Redis 7+ (optional, for future caching)
- uv (for fast dependency management)

### Installation

1. **Clone and navigate to project**

```bash
cd /path/to/aaronspindler.com
```

2. **Set up virtual environment**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install uv**

```bash
pip install uv
```

4. **Install dependencies**

```bash
# Install from lockfiles (10-100x faster than pip)
uv pip install -r requirements/base.txt
uv pip install -r requirements/dev.txt
```

5. **Set up environment variables**

Create `.env` file in project root:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/aaronspindler

# Django
DEBUG=True
SECRET_KEY=your-secret-key-here

# QuestDB
QUESTDB_URL=postgresql://admin:quest@localhost:8812/qdb

# Data Source API Keys
FINNHUB_API_KEY=your-finnhub-key
MASSIVE_API_KEY=your-polygon-key

# Optional: Redis (for future caching)
REDIS_URL=redis://localhost:6379/0
USE_DEV_CACHE_PREFIX=True
```

**Get API Keys**:
- Finnhub: https://finnhub.io/register (free tier: 60 calls/min)
- Massive.com/Polygon.io: https://polygon.io/dashboard/signup (free tier: 2 years historical)

6. **Set up databases**

```bash
# Run PostgreSQL migrations
python manage.py migrate

# Initialize QuestDB schema
python manage.py setup_questdb_schema

# Create superuser for admin access
python manage.py createsuperuser
```

7. **Seed data (optional)**

```bash
# Ingest Kraken data (TIER1 only for quick testing)
python manage.py ingest_sequential --tier TIER1 --yes

# Or load price data from external APIs
python manage.py backfill_prices --ticker AAPL --source massive --days 365
python manage.py backfill_prices --ticker BTC --source finnhub --days 365
```

8. **Run development server**

```bash
python manage.py runserver
```

Access Django admin at `http://localhost:8000/admin/`

## 📁 Project Structure

```
feefifofunds/
├── __init__.py
├── apps.py
├── models/               # Database models
│   ├── __init__.py
│   ├── asset.py          # Universal Asset model (PostgreSQL)
│   └── price.py          # AssetPrice model (QuestDB)
│
├── services/             # Business logic
│   ├── __init__.py
│   ├── calculators.py    # Metrics calculation (stub for Phase 2)
│   └── data_sources/     # External API integrations
│       ├── __init__.py
│       ├── base.py       # Error classes
│       ├── dto.py        # Data transfer objects (deprecated, not used)
│       ├── finnhub.py    # Finnhub implementation
│       └── massive.py    # Massive.com/Polygon.io implementation
│
├── management/commands/  # Django management commands
│   ├── __init__.py
│   ├── setup_questdb_schema.py
│   ├── create_asset.py
│   ├── ingest_sequential.py
│   ├── load_prices.py
│   └── backfill_prices.py
│
├── migrations/           # Database migrations (PostgreSQL only)
├── admin.py              # Django admin configuration
├── urls.py               # URL routing (minimal, admin only)
└── tests/                # Test suite (to be added)
```

## 🔧 Common Development Tasks

### Asset Management

```bash
# Create a single asset
python manage.py create_asset --ticker BTC --name Bitcoin --category CRYPTO

# Create a stock
python manage.py create_asset --ticker AAPL --name "Apple Inc." --category STOCK

# Create a commodity
python manage.py create_asset --ticker GLD --name "Gold ETF" --category COMMODITY
```

**Note**: Most assets are auto-created during Kraken ingestion with automatic tier classification.

### Price Data Loading

```bash
# Ingest Kraken CSV data (recommended - fastest)
python manage.py ingest_sequential --tier TIER1 --yes

# Load recent prices from APIs
python manage.py load_prices --ticker AAPL --source massive --days 7

# Load 30 days of data
python manage.py load_prices --ticker BTC --source finnhub --days 30

# Backfill historical data
python manage.py backfill_prices --ticker AAPL --source massive --days 365

# Backfill all active assets using grouped endpoint (MUCH faster!)
python manage.py backfill_prices --source massive --days 730 --all --grouped

# Dry-run mode (preview without saving)
python manage.py load_prices --ticker AAPL --source massive --days 7 --dry-run
```

**Data Source Considerations**:
- **Kraken**: Best for crypto, 50K-100K records/sec ingestion via QuestDB ILP
- **Finnhub**: ~1 year historical, 60 calls/minute, supports stocks + crypto
- **Massive.com**: 2 years historical, ~100 requests/second, stocks only

### Database Migrations

When modifying Asset model (PostgreSQL):

```bash
# Create migration for feefifofunds app
python manage.py makemigrations feefifofunds

# Review migration file
cat feefifofunds/migrations/000X_description.py

# Apply migrations
python manage.py migrate feefifofunds

# Show migration status
python manage.py showmigrations feefifofunds
```

**Important**:
- Django migrations only apply to PostgreSQL models (Asset)
- QuestDB model (AssetPrice) uses `managed=False` and is created via `setup_questdb_schema`
- Never manually edit or drop migrations after they're committed

### Django Admin

```bash
# Create superuser
python manage.py createsuperuser

# Access admin interface
open http://localhost:8000/admin/

# Available admin interfaces:
# - Assets: Browse, filter, search, create assets (PostgreSQL)
# - AssetPrice: Query via Django shell or QuestDB console (managed=False)
```

### Django Shell

```bash
# Open Django shell
python manage.py shell

# Example queries:
>>> from feefifofunds.models import Asset
>>> from django.db import connections
>>>
>>> # Get all crypto assets
>>> Asset.objects.filter(category='CRYPTO')
>>>
>>> # Query QuestDB for price history
>>> btc = Asset.objects.get(ticker='BTC')
>>> with connections['questdb'].cursor() as cursor:
...     cursor.execute("""
...         SELECT time, close, volume
...         FROM assetprice
...         WHERE asset_id = %s
...         AND interval_minutes = 1440
...         ORDER BY time DESC
...         LIMIT 10
...     """, [btc.id])
...     rows = cursor.fetchall()
```

## 🧪 Testing

### Running Tests

```bash
# Run all feefifofunds tests
python manage.py test feefifofunds

# Run with verbose output
python manage.py test feefifofunds --verbosity=2

# Run with coverage
coverage run --source='feefifofunds' manage.py test feefifofunds --no-input
coverage report
coverage html  # Generate HTML report in htmlcov/
```

### Docker Testing

```bash
# Build test environment
make test-build

# Run tests in Docker
make test-run-app APP=feefifofunds

# Interactive shell for debugging
make test-shell
```

### Writing Tests

**Test Structure** (to be implemented):
```python
from django.test import TestCase
from feefifofunds.models import Asset

class AssetModelTest(TestCase):
    def test_asset_creation(self):
        asset = Asset.objects.create(
            ticker='TEST',
            name='Test Asset',
            category='STOCK'
        )
        actual_ticker = asset.ticker
        expected_ticker = 'TEST'
        message = f"Expected ticker {expected_ticker}, got {actual_ticker}"
        self.assertEqual(actual_ticker, expected_ticker, message)

        self.assertTrue(asset.active, "Asset should be active by default")
```

## 🐛 Debugging

### Enable Debug Logging

```python
# In settings.py
DEBUG = True

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'feefifofunds': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}
```

### Django Debug Toolbar

Already configured in dev settings. Access at `/__debug__/` when DEBUG=True.

### Database Query Debugging

```python
from django.db import connection

# Enable query logging
from django.conf import settings
settings.DEBUG = True

# Run your code
asset = Asset.objects.get(ticker='BTC')

# View queries
for query in connection.queries:
    print(query['sql'])
```

### Data Source Debugging

```bash
# Use dry-run mode to preview API calls
python manage.py load_prices --ticker AAPL --source massive --days 7 --dry-run

# Check API keys
python manage.py shell
>>> from django.conf import settings
>>> settings.FINNHUB_API_KEY
>>> settings.MASSIVE_API_KEY
```

### QuestDB Debugging

```bash
# Test QuestDB connection
psql -h localhost -p 8812 -U admin -d qdb -c "SELECT 1"

# Check table exists
psql -h localhost -p 8812 -U admin -d qdb -c "SELECT COUNT(*) FROM assetprice"

# Verify data ingestion
psql -h localhost -p 8812 -U admin -d qdb -c "SELECT COUNT(*) FROM assetprice WHERE asset_id = 1"
```

## 🤝 Contribution Guidelines

### Code Style

- Follow PEP 8 (enforced by Ruff)
- Use type hints for function parameters and return values
- Write docstrings for public methods
- Keep functions small and focused (<50 lines ideal)

### Pre-commit Hooks

```bash
# Install hooks
pre-commit install

# Run manually on all files
pre-commit run --all-files

# Run on staged files only
git add .
pre-commit
```

Hooks include:
- Ruff (linting and formatting)
- File quality checks (trailing whitespace, end-of-file, etc.)
- Django system checks

### Commit Messages

Follow conventional commits format:

```
feat: Add CoinGecko data source integration
fix: Correct timestamp timezone handling in Finnhub source
docs: Update setup instructions with API key steps
test: Add tests for Asset model
refactor: Simplify price data transformation
```

### Pull Request Process

1. Create feature branch: `git checkout -b feature/your-feature-name`
2. Make changes and test thoroughly
3. Run pre-commit hooks: `pre-commit run --all-files`
4. Update documentation if needed
5. Commit changes with descriptive messages
6. Push branch and create PR
7. Request review from maintainers

### Branch Naming

- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation only
- `refactor/` - Code refactoring
- `test/` - Test additions/improvements

## 📖 Additional Resources

### External Documentation

- [Django Documentation](https://docs.djangoproject.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [QuestDB Documentation](https://questdb.io/docs/)
- [Finnhub API Documentation](https://finnhub.io/docs/api)
- [Polygon.io API Documentation](https://polygon.io/docs)

### Project Documentation

- [Feature Overview](overview.md) - Complete feature documentation
- [Kraken OHLCV Ingestion Guide](ohlcv-ingestion.md) - CSV data ingestion details
- [Massive.com Integration](massive-integration.md) - API integration guide
- [QuestDB Setup Guide](questdb-setup.md) - Database setup and optimization
- [Data Sources Framework](data-sources.md) - External API integration patterns
- [Commands Reference](../../commands.md#feefifofunds-data-management) - All management commands
- [Architecture Overview](../../architecture.md) - System design

## 🆘 Getting Help

- Check [centralized documentation](../../) for comprehensive guides
- Search GitHub issues
- Review error messages and stack traces
- Use Django shell for debugging queries
- Create a GitHub issue with:
  - Clear description of problem
  - Steps to reproduce
  - Error messages and stack traces
  - Environment details (Python version, OS, databases, etc.)

## 📝 Development Notes

### API Rate Limits

Be mindful of free tier limits when developing:

**Finnhub**:
- 60 API calls per minute
- ~1 year historical data
- Supports stocks and crypto

**Massive.com (Polygon.io)**:
- ~100 requests per second (soft limit)
- 2 years historical data
- Stocks only

### Environment Variables

Never commit:
- API keys
- Secret keys
- Database passwords
- Debug settings (DEBUG=True)

Always use `.env` file and django-environ.

### Database Best Practices

**PostgreSQL (Asset model)**:
- Always use migrations for schema changes
- Never manually edit the database
- Index fields used in filters and joins

**QuestDB (AssetPrice model)**:
- Use raw SQL for queries (`connections['questdb'].cursor()`)
- Leverage PARTITION BY DAY for time-range queries
- Use SYMBOL types for repeated strings
- Batch inserts with ILP for maximum performance

### Data Quality

When loading price data:
- Verify timestamps are in UTC
- Check for missing or null values
- Compare data from multiple sources when available
- Use dry-run mode to preview before saving

### Future Phases

**Phase 2**: Basic Analytics
- Implement MetricsCalculator service
- Add metrics calculation management command
- Create AssetMetrics model

**Phase 3**: Frontend & API
- Build Django template views
- Implement JSON API endpoints
- Add chart visualization

**Phase 4**: Advanced Features
- Add more data sources
- Implement Celery for scheduled updates
- Add user authentication
- Build portfolio tracking

## 🔗 Related Resources

- **Parent Project**: [aaronspindler.com](https://aaronspindler.com)
- **Main Documentation**: [docs/](../../) - Comprehensive project documentation
- **Main CLAUDE.md**: [../../CLAUDE.md](../../CLAUDE.md) - AI context and quick reference
- **Utils Models**: Shared model mixins in `utils/models/mixins.py`
