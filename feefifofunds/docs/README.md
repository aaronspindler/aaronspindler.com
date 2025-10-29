# FeeFiFoFunds

> **Fund Analysis Platform for ETFs and Mutual Funds**

A Django-based platform for aggregating, tracking, comparing, and analyzing ETF and mutual fund data. Currently in active development with core infrastructure complete.

## 🚀 Quick Start

```bash
# Install dependencies
uv pip install -r requirements/base.txt

# Run migrations
python manage.py migrate

# Start development server
python manage.py runserver

# Access the app
open http://localhost:8000/feefifofunds/
```

For detailed setup instructions, see [DEVELOPMENT.md](DEVELOPMENT.md).

## 📊 Current Status

**Phase**: Foundation & Data Infrastructure (Phase 1 of 6)

### ✅ Implemented (Ready to Use)

- ✅ **Database Models** - Complete data models with proper relationships and indexes
- ✅ **TimescaleDB Integration** - Time-series optimization for performance data
- ✅ **Django Admin** - Full-featured admin interface for all models
- ✅ **Data Source Framework** - BaseDataSource with rate limiting, caching, and error handling
- ✅ **DTOs** - Standardized data transfer objects for external APIs
- ✅ **Comparison Engine** - Logic for comparing multiple funds across various metrics
- ✅ **Data Validation** - Comprehensive validation pipeline for external data
- ✅ **Basic Views** - HTML views (home, list, detail, compare)
- ✅ **JSON API Endpoints** - Fund data, performance, holdings, comparison
- ✅ **Management Commands** - CLI tools for data fetching and metrics calculation
- ✅ **Test Framework** - Comprehensive tests for data source infrastructure

### 🚧 In Progress

- 🚧 **Metrics Calculator** - Interface defined, algorithms need implementation
- 🚧 **Yahoo Finance Integration** - Code complete, needs integration testing
- 🚧 **Frontend Templates** - Basic structure exists, needs styling and interactivity

### 📋 Planned

- 📋 **Additional Data Sources** - Alpha Vantage, Finnhub, Polygon.io
- 📋 **Advanced Analytics** - Full suite of risk metrics and technical indicators
- 📋 **Machine Learning** - Fund similarity and performance prediction models
- 📋 **Real-time Updates** - WebSocket integration for live price data
- 📋 **Portfolio Tracking** - User portfolios and watchlists
- 📋 **Recommendation Engine** - Personalized fund recommendations

## 🏗️ Architecture

### Core Components

```
feefifofunds/
├── models/              # ✅ Database models (complete)
│   ├── fund.py
│   ├── performance.py
│   ├── holding.py
│   ├── metrics.py
│   └── data_source.py
│
├── services/            # 🚧 Business logic layer
│   ├── calculators.py   # 🚧 Metrics calculation (stub)
│   ├── comparison.py    # ✅ Fund comparison (complete)
│   ├── validators.py    # ✅ Data validation (complete)
│   └── data_sources/    # ✅ External API integrations
│       ├── base.py      # ✅ Abstract base (complete)
│       ├── dto.py       # ✅ Data transfer objects (complete)
│       └── yahoo_finance.py  # 🚧 Yahoo Finance (ready for testing)
│
├── views.py             # ✅ HTML views (basic)
├── views_json.py        # ✅ JSON API endpoints (complete)
├── views_comparison.py  # ✅ Comparison views (complete)
├── admin.py             # ✅ Django admin (complete)
└── urls.py              # ✅ URL routing (complete)
```

### Technology Stack

- **Backend**: Django 5.0+
- **Database**: PostgreSQL 16+ with TimescaleDB
- **Cache**: Redis 7+
- **Task Queue**: Celery (planned)
- **Frontend**: Django templates + Vanilla JS (no framework)

### Key Design Decisions

1. **Portability** - All code self-contained in `feefifofunds/` directory
2. **No DRF** - Simple JsonResponse for API endpoints (can add later if needed)
3. **Service Layer** - Business logic separated from views for reusability
4. **TimescaleDB** - Optimized time-series storage for performance data
5. **Redis Caching** - Aggressive caching with 20-min to 1-hour TTLs

## 📚 Documentation

- **[DEVELOPMENT.md](DEVELOPMENT.md)** - Setup, testing, and contribution guide
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Technical architecture and design decisions

## 🎯 Project Vision

### Short-term Goals (Next 3-6 Months)

1. Complete metrics calculation algorithms
2. Integrate and test Yahoo Finance data source
3. Build interactive frontend with charts
4. Add user authentication and watchlists
5. Implement basic recommendations

### Long-term Vision

Create a comprehensive fund analysis platform that:
1. **Aggregates** data from multiple premium and free sources
2. **Analyzes** performance, risk, costs, and holdings
3. **Compares** funds with detailed metrics and visualizations
4. **Predicts** future performance using machine learning
5. **Recommends** optimal funds based on user goals and risk tolerance

## 🔌 Available API Endpoints

### HTML Views
- `GET /feefifofunds/` - Home page
- `GET /feefifofunds/funds/` - Fund list with filters
- `GET /feefifofunds/funds/<slug>/` - Fund detail page
- `GET /feefifofunds/compare/` - Comparison tool

### JSON Endpoints
- `GET /feefifofunds/api/funds/` - Fund list (JSON)
- `GET /feefifofunds/api/funds/<slug>/` - Fund detail (JSON)
- `GET /feefifofunds/api/funds/<slug>/performance/` - Historical prices
- `GET /feefifofunds/api/funds/<slug>/holdings/` - Portfolio holdings
- `GET|POST /feefifofunds/api/compare/` - Fund comparison

## 🛠️ Management Commands

```bash
# Check TimescaleDB status
python manage.py check_timescaledb

# Fetch fund data from Yahoo Finance
python manage.py fetch_fund SPY --info --save
python manage.py fetch_fund SPY --historical --days 365 --save
python manage.py fetch_fund SPY --holdings --save

# Calculate metrics (stub - needs implementation)
python manage.py calculate_metrics SPY
python manage.py calculate_metrics --all --timeframe 1Y
```

## 🧪 Testing

```bash
# Run all tests
python manage.py test feefifofunds

# Run specific test
python manage.py test feefifofunds.tests.test_base_data_source

# With coverage
coverage run --source='feefifofunds' manage.py test feefifofunds
coverage report
```

## 📦 Portability

**IMPORTANT**: All FeeFiFoFunds functionality is self-contained within the `feefifofunds/` directory. This architectural decision ensures the app can be easily extracted and deployed as a standalone Django project when needed.

### What's Included
- All models, views, templates, and static files
- Management commands and Celery tasks
- Tests and fixtures
- Documentation

### What's NOT Included (From Parent Project)
- User authentication (uses django-allauth from parent)
- Static file serving configuration (uses parent's WhiteNoise setup)
- Database and cache configuration (inherits from parent settings)

To extract as standalone, see deployment documentation.

## 🤝 Contributing

1. Read [DEVELOPMENT.md](DEVELOPMENT.md) for setup and guidelines
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Make changes and add tests
4. Run tests: `python manage.py test feefifofunds`
5. Run pre-commit hooks: `pre-commit run --all-files`
6. Create pull request with clear description

### Code Style

- Follow PEP 8 (enforced by Ruff)
- Use type hints
- Write docstrings for public methods
- Keep functions small and focused
- Add tests for new features

## 📝 Current Limitations

**Data Sources**:
- Only Yahoo Finance implemented (free, no API key required)
- Historical data limited to what Yahoo Finance provides
- Real-time data not yet implemented

**Metrics**:
- Basic returns calculated by database properties
- Advanced metrics (Sharpe, Sortino, etc.) need implementation
- No backtesting or performance attribution

**Frontend**:
- Basic templates without styling
- No interactive charts yet
- No user authentication on frontend views

**Performance**:
- No load testing performed
- Optimized for <10,000 funds
- Single server deployment only

## 🗺️ Roadmap

### Phase 1: Foundation (Current)
- ✅ Database models and migrations
- ✅ Data source framework
- 🚧 Basic data fetching
- 🚧 Metrics calculation

### Phase 2: Data Pipeline (Next)
- Celery task queue setup
- Scheduled data updates
- Data quality monitoring
- Additional data sources

### Phase 3: Analytics
- Complete metrics calculations
- Risk analysis tools
- Performance attribution
- Portfolio analysis

### Phase 4: Frontend
- Interactive charts
- Responsive design
- Comparison tool enhancements
- Export functionality

### Phase 5: ML & Recommendations
- Fund similarity models
- Performance prediction
- Personalized recommendations
- Portfolio optimization

### Phase 6: Production
- Load testing and optimization
- Monitoring and alerting
- Documentation completion
- User acceptance testing

## 📄 License

This project is part of the aaronspindler.com codebase. All rights reserved.

## 🔗 Related Projects

- **Parent Project**: [aaronspindler.com](https://aaronspindler.com)
- **Blog**: Uses similar Django patterns for content management
- **Photos App**: Shared media storage patterns

## 📧 Contact

For questions or suggestions, please create a GitHub issue or contact the maintainers.
