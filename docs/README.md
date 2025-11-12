# Documentation Index

Welcome to the comprehensive documentation for aaronspindler.com. This index helps you find the right documentation for your needs.

## Quick Navigation by Audience

### 🌐 External Users & Visitors
Start here if you're new to the project or want to understand what it does:
- **[Project README](../README.md)** - Project overview, features, quick start guide
- **[Architecture](architecture.md)** - System design and technical overview
- **[API Reference](api.md)** - REST API endpoints and usage

### 🤖 AI Assistants (Claude Code, GitHub Copilot)
Essential context for AI tools working with this codebase:
- **[CLAUDE.md](../CLAUDE.md)** - AI-optimized project context and guidelines
- **[Cursor Rules](../.cursor/rules/)** - Specific guidance for different tasks
  - `ai-context.mdc` - Context document maintenance
  - `documentation.mdc` - Documentation requirements
  - `comments.mdc` - Comment guidelines
  - `git-operations.mdc` - Git workflow
  - `dependencies.mdc` - Dependency management
  - `testing.mdc` - Testing guidelines

### 👨‍💻 Developers
Comprehensive guides for contributing to the codebase:
- **[Architecture](architecture.md)** - System design, Django apps, data flow
- **[Testing](testing.md)** - Test framework, factories, running tests
- **[Commands](commands.md)** - Management commands reference
- **[Feature Documentation](features/)** - Detailed feature guides
- **[App-Specific Documentation](apps/)** - Individual Django app docs

### 🚀 DevOps & System Administrators
Deployment and operations guides:
- **[Deployment](deployment.md)** - Production deployment guide
- **[Maintenance](maintenance.md)** - Ongoing operations and monitoring
- **[Commands](commands.md)** - Operational commands

### 📡 API Consumers & Frontend Developers
API integration guides:
- **[API Reference](api.md)** - Complete REST API documentation
- **[Project README](../README.md)** - Quick API overview

## Complete Documentation Reference

### Core Documentation

| Document | Description | Audience | Lines |
|----------|-------------|----------|-------|
| [architecture.md](architecture.md) | System design, Django apps, design patterns, tech stack | Developers, Architects | 586 |
| [testing.md](testing.md) | Test framework, factories, Docker test environment, best practices | Developers | 690 |
| [commands.md](commands.md) | Complete management commands reference | Developers, DevOps | 1,021 |
| [api.md](api.md) | REST API endpoints with request/response examples | API Consumers | 819 |
| [deployment.md](deployment.md) | Production deployment, environment config, Docker setup | DevOps | 752 |
| [maintenance.md](maintenance.md) | Daily/weekly/monthly tasks, monitoring, troubleshooting | DevOps, SysAdmins | 676 |

### Cross-Cutting Features

These features are used across multiple Django apps:

| Document | Description | Used By |
|----------|-------------|---------|
| [features/search.md](features/search.md) | PostgreSQL FTS with autocomplete | Blog, Photos |
| [features/performance-monitoring.md](features/performance-monitoring.md) | Lighthouse audit system | All apps |
| [features/request-tracking.md](features/request-tracking.md) | Request fingerprinting and security | All apps |

### App-Specific Documentation

Documentation organized by Django app:

| App | Description | Documentation |
|-----|-------------|---------------|
| **Blog** | Template-based blog with knowledge graph | [docs/apps/blog/](apps/blog/) |
| **Photos** | Multi-resolution photo management | [docs/apps/photos/](apps/photos/) |
| **FeeFiFoFunds** | Multi-asset price tracking (PostgreSQL + QuestDB) | [docs/apps/feefifofunds/](apps/feefifofunds/) |
| **Omas Coffee** | German coffee cart website (multi-domain) | [docs/apps/omas/](apps/omas/) |

See [apps/README.md](apps/README.md) for more information about app-specific documentation.

## Documentation by Topic

### Getting Started
- [Project README](../README.md) - Quick start guide
- [Architecture](architecture.md) - System overview
- [Testing](testing.md) - Running tests locally

### Development Workflow
- [Commands](commands.md) - Common development commands
- [Testing](testing.md) - Writing and running tests
- [CLAUDE.md](../CLAUDE.md) - Quick reference for AI assistants

### Blog & Content
- [Blog App Documentation](apps/blog/) - Complete blog system guide
  - [Blog System](apps/blog/blog-system.md) - Template-based posts, categories
  - [Knowledge Graph](apps/blog/knowledge-graph.md) - Interactive D3.js visualization

### Photos & Media
- [Photos App Documentation](apps/photos/) - Complete photo management guide
  - [Photo Management](apps/photos/photo-management.md) - Multi-resolution images, EXIF, albums

### Financial Data (FeeFiFoFunds)
- [FeeFiFoFunds App Documentation](apps/feefifofunds/) - Complete multi-asset tracking guide
  - [Overview](apps/feefifofunds/overview.md) - Architecture and data models
  - [Kraken OHLCV Ingestion](apps/feefifofunds/ohlcv-ingestion.md) - CSV data ingestion
  - [Massive Integration](apps/feefifofunds/massive-integration.md) - Stock/ETF API
  - [Data Sources](apps/feefifofunds/data-sources.md) - API integration framework
  - [QuestDB Setup](apps/feefifofunds/questdb-setup.md) - Time-series database
  - [Development Guide](apps/feefifofunds/development.md) - Local setup and testing

### Multi-Domain & Branding
- [Omas Coffee App Documentation](apps/omas/) - Complete German coffee cart website guide
  - [Technical Setup](apps/omas/technical-setup.md) - Domain routing and deployment
  - [Brand Documentation](apps/omas/) - Complete brand guidelines (6 docs)

### Cross-Cutting Features
- [Search System](features/search.md) - Full-text search with autocomplete
- [Performance Monitoring](features/performance-monitoring.md) - Lighthouse audits
- [Request Tracking](features/request-tracking.md) - Security and analytics

### Operations & Deployment
- [Deployment Guide](deployment.md) - Production setup
- [Maintenance Guide](maintenance.md) - Ongoing operations
- [Commands Reference](commands.md) - Operational commands

### API Integration
- [API Reference](api.md) - All REST endpoints
- [Data Sources](apps/feefifofunds/data-sources.md) - External API patterns

## Documentation Standards

All documentation follows these standards:

- **Clear and Concise**: Simple language, avoid unnecessary jargon
- **Examples**: Practical code examples for all features
- **Commands**: Copy/paste ready commands
- **Cross-References**: Links to related documentation
- **Professional Tone**: Technical but approachable

### Writing Documentation

When contributing to documentation:

1. **Update existing docs** when modifying features
2. **Create feature docs** for major new features (in `features/`)
3. **Update commands.md** when adding management commands
4. **Update API docs** when adding/modifying endpoints
5. **Update architecture.md** for architectural changes
6. **Keep CLAUDE.md synchronized** with project changes

### Documentation Templates

**Use standardized templates** for consistency:

- **[Feature Template](templates/feature-template.md)** - Template for new feature documentation
- **[Command Template](templates/command-template.md)** - Template for management commands
- **[API Endpoint Template](templates/api-endpoint-template.md)** - Template for API endpoints
- **[Templates Guide](templates/README.md)** - How to use the templates

See [../.cursor/rules/documentation.mdc](../.cursor/rules/documentation.mdc) for complete documentation guidelines.

## Getting Help

- **Documentation Issues**: Check this index or search within specific docs
- **Setup Problems**: Start with [Project README](../README.md)
- **Development Questions**: See [Architecture](architecture.md) or [Testing](testing.md)
- **Deployment Issues**: See [Deployment](deployment.md) or [Maintenance](maintenance.md)
- **API Questions**: See [API Reference](api.md)
- **Feature-Specific**: Check relevant doc in [features/](features/)

## Contributing to Documentation

Documentation is a critical part of this project. Code changes without documentation updates will be rejected. See [../.cursor/rules/documentation.mdc](../.cursor/rules/documentation.mdc) for:

- When to update documentation
- Documentation templates
- Writing standards
- Review checklist

---

**Last Updated**: 2025-01-10
**Total Documentation**: 6 core docs + 12 feature docs + app-specific docs = 10,500+ lines
