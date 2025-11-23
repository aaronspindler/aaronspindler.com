# AARONSPINDLER.COM
[![codecov](https://codecov.io/gh/aaronspindler/aaronspindler.com/graph/badge.svg?token=AO200M56SH)](https://codecov.io/gh/aaronspindler/aaronspindler.com)

## FEATURES

| Feature | Description | Documentation |
|---------|-------------|--------------|
| Interactive Knowledge Graph | D3.js-powered visualization mapping relationships between blog posts | [Blog App](docs/apps/blog/) |
| Smart Photo Management | Automatic multi-resolution generation with EXIF extraction | [Photos App](docs/apps/photos/) |
| Template-Based Blog | Blog posts as HTML templates with rich metadata | [Blog App](docs/apps/blog/) |
| Full-Text Search | PostgreSQL FTS with trigram similarity, sub-100ms autocomplete | [Search](docs/features/search.md) |
| Performance Monitoring | Automated Lighthouse audits with historical trends | [Performance](docs/features/performance-monitoring.md) |
| Request Tracking | Privacy-focused analytics with IP geolocation | [Request Tracking](docs/features/request-tracking.md) |
| FeeFiFoFunds | Multi-asset tracking with PostgreSQL + QuestDB hybrid architecture | [FeeFiFoFunds App](docs/apps/feefifofunds/) |
| Financial Data Integration | Standardized framework for asset price data from external APIs | [FeeFiFoFunds App](docs/apps/feefifofunds/) |
| Kraken Data Ingestion | High-speed OHLCV and trade data import (50K-100K records/sec) | [FeeFiFoFunds App](docs/apps/feefifofunds/) |
| Massive.com Integration | Historical stock/ETF data fetching (2 years free) | [FeeFiFoFunds App](docs/apps/feefifofunds/) |
| Omas Coffee Website | Multi-domain website serving omas.coffee | [Omas Coffee App](docs/apps/omas/) |
| Optimized Assets | Static file compression, multi-stage Docker builds, intelligent caching | [Architecture](docs/architecture.md) |

## TECH STACK

| Category | Technologies | Documentation |
|----------|--------------|--------------|
| Backend | Django 5.2.8, Python 3.13, PostgreSQL 15+, Celery, Redis | [Architecture](docs/architecture.md) |
| Frontend | D3.js, Vanilla JavaScript, PostCSS, Prism.js | - |
| Infrastructure | Docker, Gunicorn, WhiteNoise (static), AWS S3 (media) | [Deployment](docs/deployment.md) |
| Search | PostgreSQL FTS with pg_trgm for typo tolerance | [Search](docs/features/search.md) |
| Monitoring | Lighthouse, Pyppeteer, Flower | [Performance Monitoring](docs/features/performance-monitoring.md) |
| Testing | Django test framework with factory-based test data | [Testing](docs/testing.md) |

## QUICK START

```bash
# Clone and setup
git clone https://github.com/aaronspindler/aaronspindler.com.git
cd aaronspindler.com
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements/base.txt
pip install -r requirements/dev.txt
# Pyppeteer will auto-download Chromium on first run

# Configure environment
cp .env.example .env  # Edit with your settings

# Setup database
python manage.py migrate
python manage.py createsuperuser

# Setup git hooks
./scripts/setup-git-hooks.sh

# Initialize data
python manage.py collectstatic_optimize
python manage.py rebuild_search_index

# Run server
python manage.py runserver
```

Visit `http://localhost:8000`

For Docker setup, see [Deployment documentation](docs/deployment.md). For project structure details, see [Architecture documentation](docs/architecture.md). For available management commands, see [Management Commands documentation](docs/commands.md).

### Docker Setup

```bash
docker build -f deployment/Dockerfile.multistage -t aaronspindler.com .
docker run -p 80:80 --env-file .env.production aaronspindler.com
```

See [Deployment Guide](docs/deployment.md) for production setup.

## DOCUMENTATION

**📚 [Documentation Index](docs/README.md)** - Complete documentation map with audience-based navigation

### Core Documentation

| Document | Description |
|----------|-------------|
| [Architecture & Project Structure](docs/architecture.md) | System design and Django apps overview |
| [Testing Guide](docs/testing.md) | Test framework, factories, and Docker test environment |
| [Management Commands](docs/commands.md) | Complete command reference |
| [API Reference](docs/api.md) | REST API endpoints |
| [Deployment Guide](docs/deployment.md) | Production deployment with Docker |
| [Maintenance Guide](docs/maintenance.md) | Monitoring, backups, and troubleshooting |

### Django App Documentation

| App | Description | Documentation |
|-----|-------------|---------------|
| [Blog](docs/apps/blog/) | Template-based blog with knowledge graph visualization | [Blog System](docs/apps/blog/blog-system.md), [Knowledge Graph](docs/apps/blog/knowledge-graph.md) |
| [Photos](docs/apps/photos/) | Multi-resolution photo management with EXIF | [Photo Management](docs/apps/photos/photo-management.md) |
| [FeeFiFoFunds](docs/apps/feefifofunds/) | Multi-asset price tracking (PostgreSQL + QuestDB) | [Overview](docs/apps/feefifofunds/overview.md), [5 more docs](docs/apps/feefifofunds/) |
| [Omas Coffee](docs/apps/omas/) | German coffee cart website (multi-domain) | [Technical Setup](docs/apps/omas/technical-setup.md), [Brand Docs](docs/apps/omas/) |

### Cross-Cutting Features

| Feature | Description |
|---------|-------------|
| [Full-Text Search](docs/features/search.md) | PostgreSQL FTS with autocomplete (used by blog, photos) |
| [Performance Monitoring](docs/features/performance-monitoring.md) | Lighthouse audits and historical tracking |
| [Request Tracking](docs/features/request-tracking.md) | Request fingerprinting, geolocation, security |

## COMMON COMMANDS

```bash
# Development
python manage.py runserver
python manage.py build_css --dev
make static  # Build all assets + pre-commit

# Blog & search
python manage.py rebuild_knowledge_graph
python manage.py rebuild_search_index

# Testing
python manage.py test
make test

# Maintenance
python manage.py clear_cache
python manage.py run_lighthouse_audit

# Financial data
# See FeeFiFoFunds documentation: docs/apps/feefifofunds/
python manage.py ingest_sequential --tier TIER1
```

See [Management Commands](docs/commands.md) for complete command reference.

## PROJECT STRUCTURE

**Django Apps**: accounts, blog, pages, photos, utils, feefifofunds, omas
**Config**: deployment/, .config/, requirements/, docs/, templates/, static/

See [Architecture Guide](docs/architecture.md) for complete project structure.

## DEVELOPMENT

**Workflow**: Branch → Code → Test → Pre-commit → Commit → PR
**Code Quality**: Ruff (linting/formatting), Prettier (CSS), Pre-commit hooks, 80%+ coverage

See [Testing Guide](docs/testing.md) and [Architecture Guide](docs/architecture.md) for details.

## CONTRIBUTING

1. Follow [Testing Guide](docs/testing.md) - write tests, use factories
2. Follow code standards - Ruff formatting, type hints
3. Update `docs/` for all changes - see [Documentation Guide](.cursor/rules/documentation.mdc)
4. Use conventional commits: `feat:`, `fix:`, `docs:`, etc.

## SECURITY

**Automated**: CodeQL Analysis, GitHub Copilot Autofix, Pre-commit Hooks, Dependency Scanning
**Manual**: Request fingerprinting - see [Request Tracking](docs/features/request-tracking.md)

For security monitoring procedures, see [Maintenance documentation](docs/maintenance.md).

Report security issues via GitHub Issues or directly to the maintainer.
