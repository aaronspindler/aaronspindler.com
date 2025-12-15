# CLAUDE.md

AI-optimized guidance for Claude Code when working with this repository.

## Project Overview

Django-based personal website (aaronspindler.com) featuring:
- Blog with knowledge graph visualization
- Photo management with EXIF extraction
- Full-text search (PostgreSQL)
- Performance monitoring (Lighthouse)
- Multi-domain support (omas.coffee)
- FeeFiFoFunds: Multi-asset tracking with PostgreSQL + QuestDB

## 📚 Documentation

**All documentation is in `docs/`** - Start at [docs/README.md](docs/README.md)

Key docs:
- [Architecture](docs/architecture.md) - System design and app structure
- [Commands](docs/commands.md) - All management commands
- [Testing](docs/testing.md) - Test guidelines and factories
- [Deployment](docs/deployment.md) - Production setup

## AI-Specific Guidelines

### Cursor Rules
See [.cursor/rules/](.cursor/rules/) for detailed AI guidance:
- **documentation.mdc**: Update docs/ for all changes
- **git-operations.mdc**: NEVER commit/push without permission
- **testing.mdc**: Do NOT write new tests unless requested
- **dependencies.mdc**: Use uv for dependency management

### Critical Rules

1. **Documentation**: Update `docs/` for all code changes
2. **Testing**: Do NOT write new tests unless requested (but DO update existing tests)
3. **Git**: NEVER commit/push without permission
4. **Dependencies**: Edit `.in` files, then regenerate `.txt` with uv
5. **Comments/Docstrings**: DO NOT add code comments or docstrings unless explicitly requested or the code is genuinely complex and non-obvious. Code should be self-documenting through clear naming and structure. Only add comments for complex algorithms, non-obvious business logic, or when requested by the user

### Quick Start

```bash
# Setup
source venv/bin/activate
pip install uv
uv pip install -r requirements/base.txt

# Database
python manage.py migrate
python manage.py createsuperuser

# Run
python manage.py runserver
```

### Common Commands

See [docs/commands.md](docs/commands.md) for complete reference.

Most used:
- `python manage.py rebuild_knowledge_graph`
- `python manage.py rebuild_search_index`
- `python manage.py clear_cache`
- `python manage.py ingest_sequential --tier TIER1 --yes`
- `make static`

## Technical Notes

### Databases
- **PostgreSQL**: Django models, search
- **QuestDB**: Time-series data (50K-100K records/sec)
- **Redis**: Caching and sessions

### Multi-Domain
- `aaronspindler.com` → `config.urls`
- `omas.coffee` → `omas.urls`

### Code Style
- Line length: 120 chars
- Python 3.13
- Ruff for linting/formatting
- Pre-commit hooks configured

## Quick Reference

| Need | See |
|------|-----|
| **All documentation** | [docs/README.md](docs/README.md) |
| **Commands** | [docs/commands.md](docs/commands.md) |
| **Architecture** | [docs/architecture.md](docs/architecture.md) |
| **App docs** | [docs/apps/](docs/apps/) |

---

**Remember**: This file is for AI quick reference only. For detailed information, consult `docs/`.
