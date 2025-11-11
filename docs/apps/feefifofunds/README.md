# FeeFiFoFunds App Documentation

> **Multi-asset price tracking** with PostgreSQL + QuestDB hybrid architecture for high-performance time-series data.

## Overview

FeeFiFoFunds is a Django application for tracking financial asset prices over time across multiple categories (stocks, cryptocurrencies, commodities, currencies). It uses a hybrid database approach combining PostgreSQL for metadata with QuestDB for high-performance time-series data storage.

**Key Features:**
- Track multiple asset types: stocks, crypto, commodities, currencies
- Store OHLCV (candle) data at multiple timeframes (1m, 5m, 15m, 60m, daily, etc.)
- Store individual trade (tick) data with microsecond precision
- Ingest data from multiple sources: Kraken CSV, Massive.com API, Finnhub API
- High-performance ingestion: 50K-100K records/second with QuestDB ILP
- Tier-based asset classification for filtering and prioritization
- Hybrid database architecture: PostgreSQL + QuestDB

## Documentation

### Core Documentation

- **[Overview](overview.md)** - Complete system architecture and feature guide
  - Hybrid database approach (PostgreSQL + QuestDB)
  - Data models (Asset, AssetPrice, Trade)
  - Management commands
  - Usage examples
  - Configuration
  - Troubleshooting

- **[Development Guide](development.md)** - Local setup and contribution guidelines
  - Development setup and prerequisites
  - Project structure
  - Common development tasks
  - Testing guide
  - Debugging tips
  - Contribution guidelines

### Data Ingestion

- **[Kraken Ingestion](kraken-ingestion.md)** - Fast CSV data ingestion (50K-100K records/sec)
  - QuestDB ILP ingestion
  - OHLCV and trade data
  - Tier-based filtering
  - File management
  - Performance optimization

- **[Massive.com Integration](massive-integration.md)** - Stock/ETF data from Massive.com API
  - Historical stock/ETF data (2 years free)
  - Grouped endpoint optimization
  - Backfill commands
  - Rate limiting

- **[Data Sources Framework](data-sources.md)** - External API integration patterns
  - BaseDataSource pattern
  - Finnhub integration
  - Massive.com integration
  - DTOs and transformations

### Database

- **[QuestDB Setup](questdb-setup.md)** - Time-series database configuration
  - Installation and setup
  - Schema initialization
  - PARTITION BY DAY
  - SYMBOL types
  - Performance tuning

### Related Documentation

**Core Docs:**
- [Architecture](../../architecture.md) - FeeFiFoFunds in Django apps section
- [Commands](../../commands.md#feefifofunds-data-management) - All management commands
- [API Reference](../../api.md) - Future API endpoints
- [Deployment](../../deployment.md) - QuestDB deployment requirements

**Related Features:**
- [Request Tracking](../../../docs/features/request-tracking.md) - Similar analytics patterns

## Quick Start

### Initial Setup

```bash
# 1. Run PostgreSQL migrations
python manage.py migrate feefifofunds

# 2. Initialize QuestDB schema
python manage.py setup_questdb_schema

# 3. Ingest Kraken data (TIER1 only for quick testing)
python manage.py ingest_sequential --tier TIER1 --yes

# 4. Verify data
python manage.py shell
>>> from feefifofunds.models import Asset
>>> Asset.objects.count()
```

**See [Overview](overview.md) for complete setup guide.**

### Full Kraken Data Ingestion

```bash
# Ingest all OHLCV data (all tiers, all intervals)
python manage.py ingest_sequential --file-type ohlcv --yes

# Ingest all trade data (all tiers)
python manage.py ingest_sequential --file-type trade --yes
```

**See [Kraken Ingestion](kraken-ingestion.md) for detailed guide.**

### API Data Sources

```bash
# Load from Massive.com (stocks/ETFs)
python manage.py load_prices --ticker AAPL --source massive --days 7

# Backfill with grouped endpoint (MUCH faster!)
python manage.py backfill_prices --source massive --days 365 --all --grouped

# Load from Finnhub (stocks/crypto)
python manage.py backfill_prices --ticker BTC --source finnhub --days 365
```

**See [Massive Integration](massive-integration.md) and [Data Sources](data-sources.md) for details.**

## Architecture

### Hybrid Database Approach

**PostgreSQL (default database)**:
- Stores Asset model with metadata
- Django-managed with ORM support
- Relational queries and constraints

**QuestDB (time-series database)**:
- Stores AssetPrice and Trade models
- 50K-100K records/second ingestion
- PARTITION BY DAY for optimal queries
- SYMBOL types for repeated strings

**See [Overview](overview.md#architecture) for complete architecture details.**

### Data Models

**Asset (PostgreSQL)**:
- Universal model for all asset types
- Category: STOCK, CRYPTO, COMMODITY, CURRENCY
- Tier: TIER1-4, UNCLASSIFIED
- Fields: ticker, name, description, active

**AssetPrice (QuestDB)**:
- OHLCV price records (candles)
- Multiple intervals: 1m, 5m, 15m, 60m, 1440m (daily), etc.
- Fields: asset_id, time, open, high, low, close, volume, interval_minutes

**Trade (QuestDB)**:
- Individual trade records (ticks)
- Microsecond precision timestamps
- Fields: asset_id, time, price, volume

**See [Overview](overview.md#data-models) for complete model documentation.**

## Project Structure

```
feefifofunds/
├── __init__.py
├── apps.py
├── models/               # Database models
│   ├── __init__.py
│   ├── asset.py          # Asset model (PostgreSQL)
│   ├── price.py          # AssetPrice model (QuestDB)
│   └── trade.py          # Trade model (QuestDB)
│
├── services/             # Business logic
│   ├── __init__.py
│   ├── calculators.py    # Metrics calculation (future)
│   └── data_sources/     # External API integrations
│       ├── __init__.py
│       ├── base.py       # Base classes and errors
│       ├── finnhub.py    # Finnhub implementation
│       └── massive.py    # Massive.com implementation
│
├── management/commands/  # Django management commands
│   ├── setup_questdb_schema.py
│   ├── create_asset.py
│   ├── ingest_sequential.py
│   ├── load_prices.py
│   └── backfill_prices.py
│
├── migrations/           # Database migrations (PostgreSQL only)
├── admin.py              # Django admin configuration
└── urls.py               # URL routing (minimal)
```

## Common Commands

```bash
# Setup
python manage.py migrate feefifofunds
python manage.py setup_questdb_schema

# Ingest data
python manage.py ingest_sequential --tier TIER1 --yes
```

**See [Commands Reference](../../commands.md#feefifofunds-data-management) for complete command documentation with all options and examples.**

## Configuration

### Environment Variables

```bash
# Database connections
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
QUESTDB_URL=postgresql://admin:quest@localhost:8812/qdb

# External API keys
MASSIVE_API_KEY=your_massive_api_key
FINNHUB_API_KEY=your_finnhub_api_key
```

**See [Overview](overview.md#configuration) and [Deployment](../../deployment.md) for complete configuration.**

## Performance

### Ingestion Speed
- **QuestDB ILP**: 50K-100K records/second
- **Tier filtering**: Process only relevant assets
- **Batch processing**: Efficient bulk operations

### Query Performance
- **Partition pruning**: Daily partitions optimize time-range queries
- **Symbol caching**: Repeated strings cached in memory
- **Time-series indexes**: Automatic optimization

**See [QuestDB Setup](questdb-setup.md) for tuning details.**

## Future Enhancements

### Planned Features

**Phase 2: Basic Analytics**
- Metrics calculation (returns, volatility, Sharpe ratio)
- AssetMetrics model
- Pre-computed metrics for common timeframes

**Phase 3: Frontend & API**
- Django template views
- JSON API endpoints
- Chart visualization

**Phase 4: Advanced Features**
- Additional data sources (Alpha Vantage, CoinGecko)
- Real-time updates via WebSocket
- Portfolio tracking
- User authentication
- Custom alerts

**Phase 5+: Machine Learning**
- Price prediction models
- Asset similarity analysis
- Trend detection
- Anomaly detection

**See [Overview](overview.md#future-architecture) for complete roadmap.**

## Contributing

When contributing to FeeFiFoFunds:

1. **Follow development guide**: See [Development Guide](development.md)
2. **Test with QuestDB**: Ensure QuestDB connection works
3. **Test ingestion**: Verify data ingestion with sample files
4. **Document changes**: Update relevant docs in this directory
5. **Update commands.md**: If adding new management commands

**See [Development Guide](development.md) for complete contribution guidelines.**

## Troubleshooting

### Common Issues

**QuestDB connection errors**:
- Check QuestDB is running: `docker ps | grep questdb`
- Test connection: `psql -h localhost -p 8812 -U admin -d qdb -c "SELECT 1"`

**Ingestion errors**:
- Run `setup_questdb_schema` to initialize tables
- Check file paths and permissions
- Monitor QuestDB logs for errors

**See [Overview](overview.md#troubleshooting) for complete troubleshooting guide.**

---

**Questions?** Check the [Documentation Index](../../README.md) or create a GitHub issue.
