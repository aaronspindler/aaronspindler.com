# CLAUDE.md

This file provides AI-optimized guidance for Claude Code when working with this repository.

## Project Overview

This is a Django-based personal website and blog (aaronspindler.com) with advanced features including knowledge graph visualization, photo management, analytics tracking, and multi-asset price tracking (FeeFiFoFunds).

**Key Features:**
- Template-based blog system with knowledge graph visualization
- Photo management with multi-resolution images and EXIF extraction
- Full-text search with PostgreSQL and autocomplete
- Request fingerprinting and security tracking
- Lighthouse performance monitoring
- Multi-domain support (omas.coffee)
- FeeFiFoFunds: Multi-asset tracking with PostgreSQL + QuestDB hybrid architecture

## 📚 Documentation

**All detailed documentation is in `docs/` - Start at [docs/README.md](docs/README.md)**

- **Core**: architecture.md, commands.md, testing.md, api.md, deployment.md, maintenance.md
- **Apps**: blog/, photos/, feefifofunds/, omas/
- **Features**: search.md, performance-monitoring.md, request-tracking.md

## Directory Organization

- **`deployment/`**: Docker and deployment files (Dockerfiles, docker-compose, env files)
- **`.config/`**: Tool configs (PostCSS, PurgeCSS, Prettier, .dockerignore, .python-version)
- **`requirements/`**: Python dependencies with **uv lockfiles**
  - `.in` files: Direct dependencies (edit these)
  - `.txt` files: Generated lockfiles (never edit directly)
- **`docs/`**: Centralized documentation (architecture, features, commands, etc.)
- **Root**: Essential files only (manage.py, Makefile, package.json)

## Cursor Rules

See [.cursor/rules/](.cursor/rules/) for AI-specific guidance. Key rules:
- **documentation.mdc**: Update docs/ for all changes
- **git-operations.mdc**: NEVER commit/push without permission
- **testing.mdc**: Do NOT write new tests unless requested
- **dependencies.mdc**, **comments.mdc**, **ai-context.mdc**

## Common Development Commands

**See [docs/commands.md](docs/commands.md) for complete command reference with all options and examples.**

### Local Development

```bash
# Setup
source venv/bin/activate
pip install uv
uv pip install -r requirements/base.txt

# Database
python manage.py migrate
python manage.py createsuperuser

# Run server
python manage.py runserver
```

### Dependency Management

```bash
# Add dependency: Edit requirements/base.in, then regenerate
uv pip compile requirements/base.in -o requirements/base.txt --generate-hashes

# Install from lockfile
uv pip install -r requirements/base.txt
```

**See** [.cursor/rules/dependencies.mdc](.cursor/rules/dependencies.mdc) **for complete workflow.**

### Static Files

```bash
make static  # Build and optimize all static assets
```

**See** [docs/commands.md](docs/commands.md) **for CSS, JS, and optimization commands.**

### Testing

```bash
python manage.py test
make test
```

**IMPORTANT**: Do NOT write new tests unless requested. DO update existing tests when modifying code.

**See** [docs/testing.md](docs/testing.md) **and** [.cursor/rules/testing.mdc](.cursor/rules/testing.mdc)

### Common Tasks

```bash
# Blog & Knowledge Graph
python manage.py rebuild_knowledge_graph
python manage.py generate_knowledge_graph_screenshot

# Search
python manage.py rebuild_search_index

# Cache
python manage.py clear_cache

# Performance
python manage.py run_lighthouse_audit

# Request Tracking
python manage.py geolocate_fingerprints
python manage.py remove_local_fingerprints

# FeeFiFoFunds
python manage.py ingest_sequential --tier TIER1 --yes
```

**See** [docs/commands.md](docs/commands.md) **for all commands with detailed options and examples.**

## Key Architecture Notes

**For complete architecture details, see** [docs/architecture.md](docs/architecture.md)

### Multi-Domain Support

Domain routing middleware serves multiple sites:
- `aaronspindler.com` → `config.urls`
- `omas.coffee` → `omas.urls`

**See** [docs/apps/omas/](docs/apps/omas/)

### Database Architecture

- **PostgreSQL**: Django models, search, Asset metadata
- **QuestDB**: FeeFiFoFunds time-series data (50K-100K records/sec)
- **Redis**: Caching and sessions

**See** [docs/apps/feefifofunds/](docs/apps/feefifofunds/)

### Storage

- **Static files** (CSS, JS, fonts): WhiteNoise (served from container)
- **Media files** (photos, uploads): AWS S3 via django-storages

### Key Features by App

- **Blog**: Template-based posts with knowledge graph ([docs/apps/blog/](docs/apps/blog/))
- **Photos**: Multi-resolution images with EXIF extraction ([docs/apps/photos/](docs/apps/photos/))
- **FeeFiFoFunds**: Multi-asset tracking with PostgreSQL + QuestDB ([docs/apps/feefifofunds/](docs/apps/feefifofunds/))
- **Omas Coffee**: Multi-domain German coffee cart website ([docs/apps/omas/](docs/apps/omas/))
- **Search**: PostgreSQL FTS + trigram similarity ([docs/features/search.md](docs/features/search.md))
- **Performance Monitoring**: Lighthouse audits ([docs/features/performance-monitoring.md](docs/features/performance-monitoring.md))
- **Request Tracking**: IP geolocation and security ([docs/features/request-tracking.md](docs/features/request-tracking.md))

## Code Style & Quality

**See** [docs/architecture.md](docs/architecture.md) **for complete code style configuration.**

### Pre-commit Hooks

```bash
pre-commit install
pre-commit run --all-files
```

Hooks include:
- Ruff (linting and formatting)
- Prettier (CSS formatting)
- File quality checks
- CSS format checker (prevents minified CSS in git)

### Code Style (pyproject.toml)

- Line length: 120 characters
- Target: Python 3.13
- Linter: Ruff (replaces flake8, isort)
- Formatter: Ruff (Black-compatible)

### Security

- **CodeQL Analysis**: Automated security scanning (daily + on PR)
- **GitHub Copilot Autofix**: AI-powered fix suggestions for new alerts in PRs

## Critical Guidelines

1. **Documentation**: Update `docs/` for all code changes - see [.cursor/rules/documentation.mdc](.cursor/rules/documentation.mdc)
2. **Testing**: Do NOT write new tests unless requested - see [.cursor/rules/testing.mdc](.cursor/rules/testing.mdc)
3. **Git**: NEVER commit/push without permission - see [.cursor/rules/git-operations.mdc](.cursor/rules/git-operations.mdc)
4. **Dependencies**: Only add direct dependencies - see [.cursor/rules/dependencies.mdc](.cursor/rules/dependencies.mdc)

## Quick Reference

| Need | See |
|------|-----|
| **Documentation index** | [docs/README.md](docs/README.md) |
| **Architecture overview** | [docs/architecture.md](docs/architecture.md) |
| **All commands** | [docs/commands.md](docs/commands.md) |
| **Testing guide** | [docs/testing.md](docs/testing.md) |
| **Deployment** | [docs/deployment.md](docs/deployment.md) |
| **API reference** | [docs/api.md](docs/api.md) |
| **Blog app** | [docs/apps/blog/](docs/apps/blog/) |
| **Photos app** | [docs/apps/photos/](docs/apps/photos/) |
| **FeeFiFoFunds app** | [docs/apps/feefifofunds/](docs/apps/feefifofunds/) |
| **Omas Coffee app** | [docs/apps/omas/](docs/apps/omas/) |
| **Cross-cutting features** | [docs/features/](docs/features/) |

---

**Remember**: This file provides AI-specific guidance and quick reference. For detailed information, **always consult the centralized documentation in `docs/`**.
