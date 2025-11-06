# AARONSPINDLER.COM
[![codecov](https://codecov.io/gh/aaronspindler/aaronspindler.com/graph/badge.svg?token=AO200M56SH)](https://codecov.io/gh/aaronspindler/aaronspindler.com)

## FEATURES

| Feature | Description | Documentation |
|---------|-------------|--------------|
| Interactive Knowledge Graph | D3.js-powered visualization mapping relationships between blog posts | [Knowledge Graph](docs/features/knowledge-graph.md) |
| Smart Photo Management | Automatic multi-resolution generation with EXIF extraction | [Photo Management](docs/features/photo-management.md) |
| Template-Based Blog | Blog posts as HTML templates with rich metadata | [Blog System](docs/features/blog-system.md) |
| Full-Text Search | PostgreSQL FTS with trigram similarity, sub-100ms autocomplete | [Search](docs/features/search.md) |
| Performance Monitoring | Automated Lighthouse audits with historical trends | [Performance Monitoring](docs/features/performance-monitoring.md) |
| Request Tracking | Privacy-focused analytics with IP geolocation | [Request Tracking](docs/features/request-tracking.md) |
| Financial Data Integration | Standardized framework for fund data from external APIs with rate limiting, caching, and monitoring | [Data Sources](docs/features/data-sources.md) |
| Kraken Data Ingestion | Historical OHLCV and trade data import system | [Kraken Ingestion](docs/features/kraken-ingestion.md) |
| Massive.com Integration | Historical stock/ETF data fetching (2 years free) | [Massive Integration](docs/features/massive-integration.md) |
| Omas Coffee Website | Multi-domain website serving omas.coffee | [Omas Coffee](docs/features/omas-coffee.md) |
| Optimized Assets | Static file compression, multi-stage Docker builds, intelligent caching | [Architecture](docs/architecture.md) |

## TECH STACK

| Category | Technologies | Documentation |
|----------|--------------|--------------|
| Backend | Django 5.2.5, Python 3.13, PostgreSQL 15+, Celery, Redis | [Architecture](docs/architecture.md) |
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
docker build -f deployment/Dockerfile -t aaronspindler.com .
docker run -p 80:80 --env-file .env.production aaronspindler.com
```

See [Deployment Guide](docs/deployment.md) for production setup.

## DOCUMENTATION

### Core Documentation

| Document | Description |
|----------|-------------|
| [Architecture & Project Structure](docs/architecture.md) | System design and Django apps overview |
| [Testing Guide](docs/testing.md) | Test framework, factories, and Docker test environment |
| [Management Commands](docs/commands.md) | Complete command reference |
| [API Reference](docs/api.md) | REST API endpoints |
| [Deployment Guide](docs/deployment.md) | Production deployment with Docker |
| [Maintenance Guide](docs/maintenance.md) | Monitoring, backups, and troubleshooting |

### Feature Documentation

| Document | Description |
|----------|-------------|
| [Blog System](docs/features/blog-system.md) | Template-based posts, comments, syntax highlighting |
| [Knowledge Graph](docs/features/knowledge-graph.md) | Visualization, screenshots, API |
| [Photo Management](docs/features/photo-management.md) | Multi-resolution, EXIF, albums |
| [Full-Text Search](docs/features/search.md) | PostgreSQL FTS, autocomplete, indexing |
| [Performance Monitoring](docs/features/performance-monitoring.md) | Lighthouse audits, badges |
| [Request Tracking](docs/features/request-tracking.md) | Fingerprinting, geolocation, security |
| [Data Sources](docs/features/data-sources.md) | External API integration framework for fund data |
| [Massive.com Integration](docs/features/massive-integration.md) | Historical stock/ETF data fetching (2 years free) |
| [Kraken Ingestion](docs/features/kraken-ingestion.md) | Historical OHLCV and trade data import |
| [Omas Coffee](docs/features/omas-coffee.md) | Multi-domain website implementation |

## COMMON COMMANDS

```bash
# Development
python manage.py runserver
python manage.py build_css --dev
make static  # Build all assets + pre-commit

# Blog management
# See Blog System documentation: docs/features/blog-system.md
# See Knowledge Graph documentation: docs/features/knowledge-graph.md
python manage.py create_blog_post --title "Post Title" --category tech
python manage.py rebuild_knowledge_graph
python manage.py rebuild_search_index

# Testing
# See Testing documentation: docs/testing.md
python manage.py test
make test  # Docker test environment
coverage run --source='.' manage.py test --no-input && coverage report

# Maintenance
# See Maintenance documentation: docs/maintenance.md
# See Performance Monitoring documentation: docs/features/performance-monitoring.md
# See Request Tracking documentation: docs/features/request-tracking.md
python manage.py clear_cache
python manage.py run_lighthouse_audit
python manage.py geolocate_fingerprints

# Financial data
# See Kraken Ingestion documentation: docs/features/kraken-ingestion.md
# See Data Sources documentation: docs/features/data-sources.md
# See Massive Integration documentation: docs/features/massive-integration.md
python manage.py ingest_kraken_ohlcv --intervals 1440
python manage.py ingest_kraken_trades
python manage.py backload_massive SPY --create-fund --days 730
python manage.py update_massive_daily
```

See [Management Commands](docs/commands.md) for complete reference.

## PROJECT STRUCTURE

```
aaronspindler.com/
├── accounts/           # User authentication
├── blog/              # Blog system & knowledge graph
├── pages/             # Core website pages
├── photos/            # Photo management
├── utils/             # Search, notifications, monitoring
├── feefifofunds/      # Financial data integration
├── config/            # Django configuration
├── deployment/        # Docker and deployment files
│   ├── Dockerfile
│   ├── docker-compose.test.yml
│   └── *.Dockerfile   # Service-specific images
├── .config/           # Tool configurations
│   ├── postcss.config.js
│   ├── purgecss.config.js
│   └── .prettierrc    # CSS formatter
├── requirements/      # Python dependencies
│   ├── base.txt       # Core dependencies
│   └── dev.txt        # Development dependencies
├── docs/              # Documentation
│   ├── features/      # Feature-specific guides
│   ├── architecture.md
│   ├── testing.md
│   ├── commands.md
│   ├── api.md
│   ├── deployment.md
│   └── maintenance.md
├── templates/         # Django templates
├── static/            # CSS, JS, images
├── scripts/           # Utility scripts
└── tests/             # Test factories
```

See [Architecture Guide](docs/architecture.md) for detailed structure. For Docker configuration, see [Deployment documentation](docs/deployment.md). For test structure, see [Testing documentation](docs/testing.md).

## DEVELOPMENT WORKFLOW

1. **Create feature branch**: `git checkout -b feature/amazing-feature`
2. **Make changes**: Edit code, write tests
3. **Run tests**: `make test` (see [Testing documentation](docs/testing.md) for test requirements)
4. **Pre-commit checks**: Automatic via git hooks (Ruff, Prettier, etc.)
5. **Commit**: `git commit -m 'feat: Add amazing feature'`
6. **Push**: `git push origin feature/amazing-feature`
7. **Open PR**: Create pull request on GitHub

For available management commands, see [Management Commands documentation](docs/commands.md). For project organization, see [Architecture documentation](docs/architecture.md).

### Code Quality

| Tool | Purpose |
|------|---------|
| Ruff | Python linting and formatting (Black-compatible) |
| Prettier | CSS formatting for source files |
| Pre-commit | Automatic checks on commit/push |
| Safety | Security vulnerability scanning |
| Coverage | Maintain 80%+ test coverage |

Run `pre-commit run --all-files` before pushing.

## CONTRIBUTING

Contributions welcome! Please:

1. Review [Testing Guide](docs/testing.md) for test requirements
2. Follow code standards (Ruff formatting, type hints, docstrings)
3. Write tests for new features (use factories from `tests/factories.py`)
4. Update documentation in `docs/` for significant changes
5. Follow [conventional commits](https://www.conventionalcommits.org/) format

For code organization, see [Architecture documentation](docs/architecture.md). For development commands, see [Management Commands documentation](docs/commands.md).

**Commit Conventions**: `feat:`, `fix:`, `docs:`, `style:`, `refactor:`, `test:`, `chore:`

## SECURITY

| Security Feature | Description | Documentation |
|-----------------|--------------|--------------|
| CodeQL Analysis | Automated security scanning on push, PR, and daily | - |
| GitHub Copilot Autofix | AI-powered fix suggestions for security alerts | - |
| Pre-commit Hooks | Local code quality enforcement | - |
| Dependency Scanning | Safety checks for vulnerabilities | - |
| Request Fingerprinting | Suspicious request detection | [Request Tracking](docs/features/request-tracking.md) |

For security monitoring procedures, see [Maintenance documentation](docs/maintenance.md).

Report security issues via GitHub Issues or directly to the maintainer.
