# aaronspindler.com

> A Django-powered personal website featuring interactive knowledge graphs, smart photo management, and a template-based blog system

[![Django](https://img.shields.io/badge/Django-5.2.5-green?style=for-the-badge&logo=django)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.13-blue?style=for-the-badge&logo=python)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue?style=for-the-badge&logo=postgresql)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue?style=for-the-badge&logo=docker)](https://www.docker.com/)

## Features

- **📊 Interactive Knowledge Graph** - D3.js-powered visualization mapping relationships between blog posts • [📚 Docs](docs/features/knowledge-graph.md)
- **📸 Smart Photo Management** - Automatic multi-resolution generation with EXIF extraction • [📚 Docs](docs/features/photo-management.md)
- **📝 Template-Based Blog** - Blog posts as HTML templates with rich metadata • [📚 Docs](docs/features/blog-system.md)
- **🔍 Full-Text Search** - PostgreSQL FTS with trigram similarity, sub-100ms autocomplete • [📚 Docs](docs/features/search.md)
- **⚡ Performance Monitoring** - Automated Lighthouse audits with historical trends • [📚 Docs](docs/features/performance-monitoring.md)
- **🔒 Request Tracking** - Privacy-focused analytics with IP geolocation • [📚 Docs](docs/features/request-tracking.md)
- **🎨 Optimized Assets** - Static file compression, multi-stage Docker builds, intelligent caching

## Tech Stack

**Backend**: Django 5.2.5, Python 3.13, PostgreSQL 15+, Celery, Redis
**Frontend**: D3.js, Vanilla JavaScript, PostCSS, Prism.js
**Infrastructure**: Docker, Gunicorn, WhiteNoise (static), AWS S3 (media)
**Search**: PostgreSQL FTS with pg_trgm for typo tolerance
**Monitoring**: Lighthouse, Pyppeteer, Flower

## Quick Start

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

### Docker Setup

```bash
docker build -f deployment/Dockerfile -t aaronspindler.com .
docker run -p 80:80 --env-file .env.production aaronspindler.com
```

See [Deployment Guide](docs/deployment.md) for production setup.

## Documentation

### 📘 Core Documentation

- [Architecture & Project Structure](docs/architecture.md) - System design and Django apps overview
- [Testing Guide](docs/testing.md) - Test framework, factories, and Docker test environment
- [Management Commands](docs/commands.md) - Complete command reference
- [API Reference](docs/api.md) - REST API endpoints
- [Deployment Guide](docs/deployment.md) - Production deployment with Docker
- [Maintenance Guide](docs/maintenance.md) - Monitoring, backups, and troubleshooting

### 🎯 Feature Documentation

- [Blog System](docs/features/blog-system.md) - Template-based posts, comments, syntax highlighting
- [Knowledge Graph](docs/features/knowledge-graph.md) - Visualization, screenshots, API
- [Photo Management](docs/features/photo-management.md) - Multi-resolution, EXIF, albums
- [Full-Text Search](docs/features/search.md) - PostgreSQL FTS, autocomplete, indexing
- [Performance Monitoring](docs/features/performance-monitoring.md) - Lighthouse audits, badges
- [Request Tracking](docs/features/request-tracking.md) - Fingerprinting, geolocation, security

## Common Commands

```bash
# Development
python manage.py runserver
python manage.py build_css --dev
make static  # Build all assets + pre-commit

# Blog management
python manage.py create_blog_post --title "Post Title" --category tech
python manage.py rebuild_knowledge_graph
python manage.py rebuild_search_index

# Testing
python manage.py test
make test  # Docker test environment
coverage run --source='.' manage.py test --no-input && coverage report

# Maintenance
python manage.py clear_cache
python manage.py run_lighthouse_audit
python manage.py geolocate_fingerprints
```

See [Management Commands](docs/commands.md) for complete reference.

## Project Structure

```
aaronspindler.com/
├── accounts/           # User authentication
├── blog/              # Blog system & knowledge graph
├── pages/             # Core website pages
├── photos/            # Photo management
├── utils/             # Search, notifications, monitoring
├── config/            # Django configuration
├── deployment/        # 🐳 Docker and deployment files
│   ├── Dockerfile
│   ├── docker-compose.test.yml
│   └── *.Dockerfile   # Service-specific images
├── .config/           # 🔧 Tool configurations
│   ├── postcss.config.js
│   ├── purgecss.config.js
│   └── .prettierrc    # CSS formatter
├── requirements/      # 📦 Python dependencies
│   ├── base.txt       # Core dependencies
│   └── dev.txt        # Development dependencies
├── docs/              # 📚 Documentation
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

See [Architecture Guide](docs/architecture.md) for detailed structure.

## Development Workflow

1. **Create feature branch**: `git checkout -b feature/amazing-feature`
2. **Make changes**: Edit code, write tests
3. **Run tests**: `make test`
4. **Pre-commit checks**: Automatic via git hooks (Ruff, Prettier, etc.)
5. **Commit**: `git commit -m 'feat: Add amazing feature'`
6. **Push**: `git push origin feature/amazing-feature`
7. **Open PR**: Create pull request on GitHub

### Code Quality

- **Ruff**: Python linting and formatting (Black-compatible)
- **Prettier**: CSS formatting for source files
- **Pre-commit**: Automatic checks on commit/push
- **Safety**: Security vulnerability scanning
- **Coverage**: Maintain 80%+ test coverage

Run `pre-commit run --all-files` before pushing.

## Contributing

Contributions welcome! Please:

1. Review [Testing Guide](docs/testing.md) for test requirements
2. Follow code standards (Ruff formatting, type hints, docstrings)
3. Write tests for new features (use factories from `tests/factories.py`)
4. Update documentation in `docs/` for significant changes
5. Follow [conventional commits](https://www.conventionalcommits.org/) format

**Commit Conventions**: `feat:`, `fix:`, `docs:`, `style:`, `refactor:`, `test:`, `chore:`

## Security

- **CodeQL Analysis**: Automated security scanning on push, PR, and daily
- **GitHub Copilot Autofix**: AI-powered fix suggestions for security alerts
- **Pre-commit Hooks**: Local code quality enforcement
- **Dependency Scanning**: Safety checks for vulnerabilities
- **Request Fingerprinting**: Suspicious request detection

Report security issues via GitHub Issues or directly to the maintainer.
