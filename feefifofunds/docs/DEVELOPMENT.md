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
- **Asset** - Universal model for all asset types (4 categories)
- **AssetPrice** - OHLCV price data with multi-source support
- Uses TimestampedModel mixin from `utils/models/mixins.py`

#### 🔌 Data Sources (100%)
- **FinnhubDataSource** - Stocks and crypto (~1 year historical on free tier)
- **MassiveDataSource** - Stocks via Polygon.io (2 years historical on free tier)
- Standardized data transformation pipeline
- Error handling (DataSourceError, DataNotFoundError)

#### 🛠️ Management Commands (100%)
- **create_asset** - Create assets manually
- **load_prices** - Load recent price data
- **backfill_prices** - Backfill historical prices (single or all assets)
- **populate_popular_assets** - Seed popular assets
- Dry-run mode support
- Free tier warnings

#### 🎨 Admin Interface (100%)
- Asset admin with filters and search
- AssetPrice admin with list display
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

6. **Set up database**

```bash
# Run migrations
python manage.py migrate

# Create superuser for admin access
python manage.py createsuperuser
```

7. **Seed data (optional)**

```bash
# Populate popular assets
python manage.py populate_popular_assets

# Load price data for specific assets
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
│   ├── asset.py          # Universal Asset model
│   └── price.py          # AssetPrice model
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
│   ├── create_asset.py
│   ├── load_prices.py
│   ├── backfill_prices.py
│   └── populate_popular_assets.py
│
├── migrations/           # Database migrations
├── docs/                 # Documentation
│   ├── README.md
│   ├── ARCHITECTURE.md
│   └── DEVELOPMENT.md
│
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
python manage.py create_asset --ticker AAPL --name "Apple Inc" --category STOCK

# Create a commodity
python manage.py create_asset --ticker GLD --name "Gold ETF" --category COMMODITY --quote-currency USD

# Populate popular assets (stocks, crypto, commodities, currencies)
python manage.py populate_popular_assets
```

### Price Data Loading

```bash
# Load recent prices (default: 7 days)
python manage.py load_prices --ticker AAPL --source massive --days 7

# Load 30 days of data
python manage.py load_prices --ticker BTC --source finnhub --days 30

# Backfill historical data
python manage.py backfill_prices --ticker AAPL --source massive --days 365

# Backfill all active assets
python manage.py backfill_prices --source massive --days 730 --all

# Dry-run mode (preview without saving)
python manage.py load_prices --ticker AAPL --source massive --days 7 --dry-run
```

**Data Source Considerations**:
- Finnhub free tier: ~1 year historical, 60 calls/minute, supports stocks + crypto
- Massive.com free tier: 2 years historical, ~100 requests/second, stocks only
- Commands warn when exceeding free tier limits

### Database Migrations

When modifying models:

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

**Important**: Never manually edit or drop migrations after they're committed. Use new migrations for all model changes.

### Django Admin

```bash
# Create superuser
python manage.py createsuperuser

# Access admin interface
open http://localhost:8000/admin/

# Available admin interfaces:
# - Assets: Browse, filter, search, create assets
# - Asset Prices: View price history with filters
```

### Django Shell

```bash
# Open Django shell
python manage.py shell

# Example queries:
>>> from feefifofunds.models import Asset, AssetPrice
>>>
>>> # Get all crypto assets
>>> Asset.objects.filter(category='CRYPTO')
>>>
>>> # Get price history for BTC
>>> btc = Asset.objects.get(ticker='BTC')
>>> btc.prices.order_by('-timestamp')[:10]
>>>
>>> # Compare sources
>>> AssetPrice.objects.filter(asset=btc, source='finnhub')
>>> AssetPrice.objects.filter(asset=btc, source='massive')
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
from feefifofunds.models import Asset, AssetPrice

class AssetModelTest(TestCase):
    def test_asset_creation(self):
        asset = Asset.objects.create(
            ticker='TEST',
            name='Test Asset',
            category='STOCK'
        )
        self.assertEqual(asset.ticker, 'TEST')
        self.assertTrue(asset.active)
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
- [Finnhub API Documentation](https://finnhub.io/docs/api)
- [Polygon.io API Documentation](https://polygon.io/docs)

### Project Documentation

- [README.md](README.md) - Project overview and quick start
- [ARCHITECTURE.md](ARCHITECTURE.md) - Technical architecture details

## 🆘 Getting Help

- Check existing documentation
- Search GitHub issues
- Review error messages and stack traces
- Use Django shell for debugging queries
- Create a GitHub issue with:
  - Clear description of problem
  - Steps to reproduce
  - Error messages and stack traces
  - Environment details (Python version, OS, etc.)

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

- Always use migrations for schema changes
- Never manually edit the database
- Use `update_or_create` for upserts
- Wrap bulk operations in `@transaction.atomic`
- Index fields used in filters and joins

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
- **Main CLAUDE.md**: Development guidelines and commands
- **Utils Models**: Shared model mixins in `utils/models/mixins.py`
