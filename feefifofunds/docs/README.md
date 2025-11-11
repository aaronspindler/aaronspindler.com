# FeeFiFoFunds Documentation

> **Multi-Asset Price Tracking Platform (MVP)** - A Django-based platform for tracking and analyzing prices across stocks, cryptocurrencies, commodities, and currencies.

## 📚 Documentation Has Moved

All FeeFiFoFunds documentation has been consolidated to the main project `docs/` directory for better organization and easier maintenance.

### 🚀 Quick Links

**New to FeeFiFoFunds?**
- **[FeeFiFoFunds Overview](../../docs/features/feefifofunds.md)** - Start here! Complete guide with architecture, setup, and usage

**Developer Resources:**
- **[Development Guide](../../docs/apps/feefifofunds/development.md)** - Local setup, testing, debugging, contribution guidelines
- **[Commands Reference](../../docs/commands.md#feefifofunds-data-management)** - All management commands with examples

**Feature Guides:**
- **[Kraken Ingestion](../../docs/features/kraken-ingestion.md)** - Fast CSV data ingestion (50K-100K records/sec)
- **[Massive.com Integration](../../docs/features/massive-integration.md)** - Stock/ETF data from Massive.com API
- **[Data Sources Framework](../../docs/features/data-sources.md)** - External API integration patterns
- **[QuestDB Setup](../../docs/features/questdb-setup.md)** - Time-series database configuration

**Core Documentation:**
- **[Architecture Overview](../../docs/architecture.md)** - System design and Django apps
- **[Documentation Index](../../docs/README.md)** - Complete documentation map

## 🏃 Quick Start

```bash
# Install dependencies
uv pip install -r requirements/base.txt

# Run PostgreSQL migrations
python manage.py migrate

# Initialize QuestDB schema
python manage.py setup_questdb_schema

# Ingest Kraken data (TIER1 assets - fastest)
python manage.py ingest_sequential --tier TIER1 --yes

# Access Django admin
python manage.py createsuperuser
open http://localhost:8000/admin/
```

See the [FeeFiFoFunds Overview](../../docs/features/feefifofunds.md) for detailed setup instructions and architecture explanation.

## 📊 Current Status

**Phase**: MVP - Data Ingestion Infrastructure (Phase 1)

### ✅ Implemented
- Universal Asset Model (stocks, crypto, commodities, currencies)
- OHLCV & Trade data tracking with QuestDB (high performance)
- Django Admin interface
- Kraken CSV ingestion (50K-100K records/sec)
- Finnhub & Massive.com API integration
- Management commands for data operations

### 🚧 In Progress
- Frontend views
- API endpoints

### 📋 Planned
- Metrics calculation (returns, volatility, Sharpe ratio)
- Asset comparison
- Real-time updates
- Portfolio tracking

See [FeeFiFoFunds Overview](../../docs/features/feefifofunds.md#architecture) for complete architecture details and roadmap.

## 🤝 Contributing

See the [Development Guide](../../docs/apps/feefifofunds/development.md) for:
- Local development setup
- Running tests
- Code style guidelines
- Pull request process

---

**Note**: This directory previously contained detailed documentation files (ARCHITECTURE.md, DEVELOPMENT.md) which have been moved to the centralized documentation structure for easier maintenance and discoverability.
