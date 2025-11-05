# FeeFiFoFunds Development Guide

## 📋 Table of Contents

- [Project Overview](#project-overview)
- [Current Implementation Status](#current-implementation-status)
- [Development Setup](#development-setup)
- [Architecture](#architecture)
- [Testing](#testing)
- [Contribution Guidelines](#contribution-guidelines)

## 🎯 Project Overview

FeeFiFoFunds is a Django-based fund analysis platform for tracking, comparing, and analyzing ETFs and mutual funds. The project is currently in active development with core infrastructure in place and data source integrations in progress.

### Goals

- **Primary**: Provide comprehensive fund data aggregation from multiple sources
- **Secondary**: Enable detailed fund comparison and analysis
- **Future**: AI-powered recommendations and portfolio optimization

## ✅ Current Implementation Status

### Completed Components

#### 🗄️ Database Models (100%)
- **Fund** - Complete with all fields, properties, and methods
- **FundPerformance** - OHLCV data with optimized indexing
- **FundHolding** - Portfolio holdings tracking
- **FundMetrics** - Calculated financial metrics
- **DataSource** - External API provider tracking
- **DataSync** - Synchronization history and monitoring

#### 🔌 Data Source Infrastructure (90%)
- **BaseDataSource** - Abstract base class with rate limiting, caching, and error handling
- **DTOs** - FundDataDTO, PerformanceDataDTO, HoldingDataDTO
- **DataValidator** - Comprehensive validation pipeline

#### 📊 Services (60%)
- **ComparisonEngine** - Fund comparison logic (COMPLETE)
- **DataValidator** - Data quality checks (COMPLETE)
- **MetricsCalculator** - STUB (needs implementation)

#### 🌐 Views & URLs (80%)
- HTML views: home, list, detail, compare
- JSON endpoints: fund data, performance, holdings, comparison
- URL routing configured

#### 🎨 Admin Interface (100%)
- All models registered with custom displays
- Colored status indicators
- Proper fieldsets and filters

### In Progress

- **Metrics Calculation** - Stub exists, needs algorithm implementation
- **Data Source Testing** - Infrastructure ready, needs integration tests
- **Frontend Templates** - Basic structure exists, needs styling and interactivity

### Planned

- **Additional Data Sources** - Alpha Vantage, Finnhub, massive.com
- **Advanced Analytics** - Risk metrics, technical indicators
- **ML Recommendations** - Fund similarity, performance prediction
- **Real-time Updates** - WebSocket integration

## 🚀 Development Setup

### Prerequisites

- Python 3.11+
- PostgreSQL 16+
- Redis 7+
- Node.js 18+ (for frontend assets)
- uv (for fast dependency management)

### Installation

1. **Clone the repository**

```bash
cd /path/to/aaronspindler.com
```

2. **Set up virtual environment**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install uv (fast Python package installer)**

```bash
pip install uv
```

4. **Install dependencies**

```bash
# Install from lockfile (10-100x faster than pip)
uv pip install -r requirements/base.txt
uv pip install -r requirements/dev.txt
```

5. **Set up environment variables**

Create `.env` file in project root:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/aaronspindler

# Redis
REDIS_URL=redis://localhost:6379/0
USE_DEV_CACHE_PREFIX=True

# Django
DEBUG=True
SECRET_KEY=your-secret-key-here

# Optional: Data Source API Keys (when implemented)
ALPHA_VANTAGE_API_KEY=
FINNHUB_API_KEY=
POLYGON_API_KEY=
```

6. **Set up database**

```bash
# Run migrations
python manage.py migrate

# Create superuser for admin access
python manage.py createsuperuser
```

7. **Install frontend dependencies** (if working on frontend)

```bash
npm install
```

8. **Run development server**

```bash
python manage.py runserver
```

Access the app at `http://localhost:8000/feefifofunds/`

### Quick Start with Docker (Alternative)

```bash
# Build and start all services
make test-build
make test-up

# Run migrations
docker-compose -f deployment/docker-compose.test.yml exec web python manage.py migrate

# Access shell
make test-shell
```

## 📁 Project Structure

```
feefifofunds/
├── __init__.py
├── apps.py
├── models/               # Database models
│   ├── __init__.py
│   ├── base.py          # Base abstract classes
│   ├── fund.py          # Fund model
│   ├── performance.py   # FundPerformance model
│   ├── holding.py       # FundHolding model
│   ├── metrics.py       # FundMetrics model
│   └── data_source.py   # DataSource & DataSync models
│
├── services/            # Business logic
│   ├── __init__.py
│   ├── calculators.py   # Metrics calculation (STUB)
│   ├── comparison.py    # Fund comparison engine
│   ├── validators.py    # Data validation
│   └── data_sources/    # External API integrations
│       ├── __init__.py
│       ├── base.py      # Abstract base class
│       ├── dto.py       # Data transfer objects
│       └── example_source.py  # Placeholder for future implementations
│
├── management/commands/ # Django management commands
│   ├── calculate_metrics.py
│   └── fetch_fund.py
│
├── migrations/          # Database migrations
├── templates/           # HTML templates
│   └── feefifofunds/
│       ├── base.html
│       ├── home.html
│       ├── fund_list.html
│       ├── fund_detail.html
│       └── compare.html
│
├── static/              # Static files (CSS, JS, images)
│   └── feefifofunds/
│
├── tests/               # Test suite
│   ├── __init__.py
│   └── test_base_data_source.py
│
├── admin.py             # Django admin configuration
├── views.py             # HTML views
├── views_json.py        # JSON API endpoints
├── views_comparison.py  # Comparison views
└── urls.py              # URL routing
```

## 🧪 Testing

### Running Tests

```bash
# Run all tests (locally, no parallel)
python manage.py test feefifofunds

# Run specific test file
python manage.py test feefifofunds.tests.test_base_data_source

# Run with coverage
coverage run --source='feefifofunds' manage.py test feefifofunds --no-input
coverage report
coverage html  # Generate HTML report
```

### Docker Testing

```bash
# Full test suite in Docker
make test

# Test specific app
make test-run-app APP=feefifofunds

# Interactive shell for debugging
make test-shell
```

### Writing Tests

- Place tests in `feefifofunds/tests/`
- Use Django's TestCase for database tests
- Mock external API calls to avoid rate limits
- Follow existing test patterns (see `test_base_data_source.py`)

## 🔧 Common Development Tasks

### Adding a New Data Source

1. Create new file in `services/data_sources/`:

```python
# services/data_sources/example_source.py
from .base import BaseDataSource, DataSourceError
from .dto import FundDataDTO, PerformanceDataDTO, HoldingDataDTO

class ExampleSource(BaseDataSource):
    name = "example_source"
    display_name = "Example Data Source"
    base_url = "https://api.example.com"
    requires_api_key = True
    rate_limit_requests = 60
    rate_limit_period = 60

    def fetch_fund_info(self, ticker: str) -> FundDataDTO:
        # Implementation here
        pass

    def fetch_historical_prices(self, ticker: str, start_date, end_date, interval="1D"):
        # Implementation here
        pass

    def fetch_holdings(self, ticker: str):
        # Implementation here
        pass
```

2. Add to `services/data_sources/__init__.py`
3. Create tests in `tests/test_example_source.py`
4. Update documentation

### Creating a Management Command

```bash
python manage.py startcommand command_name feefifofunds
```

Edit `feefifofunds/management/commands/command_name.py`:

```python
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Description of command'

    def add_arguments(self, parser):
        parser.add_argument('--option', type=str, help='Option description')

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Command executed successfully!'))
```

### Adding a Model Field

1. Edit the model in `feefifofunds/models/`
2. Create migration:

```bash
python manage.py makemigrations feefifofunds
```

3. Review the migration file
4. Apply migration:

```bash
python manage.py migrate feefifofunds
```

5. Update admin.py if field should be displayed
6. Update serializers/DTOs if needed

### Adding a New Metric Calculation

Edit `services/calculators.py`:

```python
def calculate_sharpe_ratio(self, performance_data: list, risk_free_rate: Decimal) -> Optional[Decimal]:
    """
    Calculate Sharpe ratio.

    Args:
        performance_data: List of FundPerformance instances
        risk_free_rate: Risk-free rate as decimal

    Returns:
        Sharpe ratio or None if insufficient data
    """
    # Implementation here
    pass
```

Update `calculate_all_metrics()` to call your new calculation.

## 🎨 Frontend Development

### Building CSS

```bash
# Build and minify CSS
npm run build:css

# Development mode (unminified)
python manage.py build_css --dev

# Watch mode (auto-rebuild on changes)
npm run watch:css
```

### Building JavaScript

```bash
# Build and minify JS
npm run build:js

# Watch mode
npm run watch:js
```

### Build All Assets

```bash
# Build everything and collect static files
make static
```

## 📚 Key Concepts

### Data Flow

```
External API → BaseDataSource → DTO → Validator → Model → Database
                    ↓
              Rate Limiter
                    ↓
              Cache (Redis)
```

### Metrics Calculation Flow

```
FundPerformance (raw data) → MetricsCalculator → FundMetrics (calculated)
                                     ↓
                                Validators
                                     ↓
                                  Cache
```

### Comparison Flow

```
Multiple Fund objects → ComparisonEngine → Comparison Results → JSON/HTML
                            ↓
                    Metrics Calculation
                            ↓
                     Holdings Analysis
```

## 🐛 Debugging

### Enable Debug Logging

```python
# In settings.py or .env
DEBUG=True
LOG_LEVEL=DEBUG
```

### Django Debug Toolbar

```python
# Already configured in dev settings
# Access at http://localhost:8000/__debug__/
```

### Database Queries

```python
from django.db import connection
from django.test.utils import override_settings

# Log all queries
with override_settings(DEBUG=True):
    # Your code here
    print(connection.queries)
```

### Redis Cache Inspection

```bash
redis-cli
> KEYS feefifofunds:*
> GET feefifofunds:fund:SPY
> FLUSHALL  # Clear all cache (use with caution!)
```

## 🤝 Contribution Guidelines

### Code Style

- Follow PEP 8 (enforced by Ruff)
- Use type hints for function parameters and return values
- Write docstrings for all public methods
- Keep functions focused and small (<50 lines ideal)

### Pre-commit Hooks

```bash
# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

Hooks include:
- Ruff (linting and formatting)
- Prettier (CSS formatting)
- File quality checks
- Django checks

### Commit Messages

Follow conventional commits format:

```
feat: Add Alpha Vantage data source integration
fix: Correct expense ratio calculation in Fund model
docs: Update development setup instructions
test: Add tests for ComparisonEngine
refactor: Simplify rate limiting logic
```

### Pull Request Process

1. Create feature branch: `git checkout -b feature/your-feature-name`
2. Make changes and test thoroughly
3. Run pre-commit hooks: `pre-commit run --all-files`
4. Run full test suite: `python manage.py test feefifofunds`
5. Update documentation if needed
6. Commit changes with descriptive messages
7. Push branch and create PR
8. Request review from maintainers

### Branch Naming

- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation only
- `refactor/` - Code refactoring
- `test/` - Test additions/improvements

## 📖 Additional Resources

- [Django Documentation](https://docs.djangoproject.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Alpha Vantage Documentation](https://www.alphavantage.co/documentation/)
- [Project README](../README.md)
- [Architecture Documentation](ARCHITECTURE.md)

## 🆘 Getting Help

- Check existing documentation
- Search GitHub issues
- Ask in project Slack/Discord (if applicable)
- Create a GitHub issue with details

## 📝 Notes

- **Never commit API keys** - Use environment variables
- **Run tests before committing** - Ensures code quality
- **Update docs with code changes** - Keep documentation in sync
- **Use branches for features** - Never commit directly to main
- **Ask questions early** - Better to clarify than assume
