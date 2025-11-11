# App-Specific Documentation

This directory contains documentation specific to individual Django apps within the project. App-specific documentation includes development guides, internal architecture notes, brand guidelines, and other materials that are tightly coupled to a specific app.

## Directory Structure

```
docs/apps/
├── README.md (this file)
├── blog/
│   ├── README.md           # Blog app index
│   ├── blog-system.md      # Template-based blog architecture
│   └── knowledge-graph.md  # Knowledge graph visualization
├── photos/
│   ├── README.md           # Photos app index
│   └── photo-management.md # Multi-resolution photo management
├── feefifofunds/
│   ├── README.md           # FeeFiFoFunds app index
│   ├── overview.md         # Architecture and data models
│   ├── development.md      # Development guide
│   ├── kraken-ingestion.md # Kraken CSV ingestion
│   ├── data-sources.md     # API integration framework
│   ├── massive-integration.md # Massive.com API
│   └── questdb-setup.md    # QuestDB configuration
└── omas/
    ├── README.md           # Omas Coffee app index
    ├── technical-setup.md  # Django implementation and deployment
    ├── brand-foundation.md # Mission, values, brand personality
    ├── brand-standards.md  # Logo, colors, typography guidelines
    ├── design-guidelines.md # Design principles
    ├── digital-design.md   # Website/digital presence guidelines
    ├── physical-design.md  # Coffee cart physical design
    └── DESIGN_BRIEF.md     # Complete design specification
```

## When to Use App-Specific Documentation

### Use docs/apps/ For:

- **Development Guides**: Setup, testing, debugging specific to an app
- **Internal Architecture**: App-specific design decisions and patterns
- **Brand Guidelines**: Visual identity, design systems, brand standards
- **Contribution Guidelines**: App-specific contribution requirements
- **Internal Processes**: Workflows specific to an app's development

### Use docs/features/ Instead For:

- **User-Facing Features**: Functionality that users interact with
- **Feature Guides**: How to use a feature
- **API Documentation**: Public APIs exposed by the app
- **Integration Guides**: How features integrate with other parts of the system

## Current App Documentation

### Blog

**Location**: [docs/apps/blog/](blog/)

Template-based blog system with knowledge graph visualization.

**Documentation**:
- **[README.md](blog/README.md)** - Blog app index and quick start
- **[blog-system.md](blog/blog-system.md)** - Complete blog architecture
  - Template-based post structure
  - Creating and managing blog posts
  - Categories and organization
  - Comment system with voting
  - Syntax highlighting with Prism.js
  - View tracking
- **[knowledge-graph.md](blog/knowledge-graph.md)** - Interactive visualization system
  - Graph architecture and components
  - Link extraction and categorization
  - D3.js visualization
  - Server-side screenshot generation
  - API endpoints
  - Performance optimizations

### Photos

**Location**: [docs/apps/photos/](photos/)

Smart photo management with automatic multi-resolution generation and EXIF extraction.

**Documentation**:
- **[README.md](photos/README.md)** - Photos app index and quick start
- **[photo-management.md](photos/photo-management.md)** - Complete photo system
  - Multi-resolution image architecture
  - EXIF metadata extraction
  - AWS S3 storage configuration
  - Album management
  - Zip generation and downloads
  - WebP conversion
  - Search integration

### FeeFiFoFunds

**Location**: [docs/apps/feefifofunds/](feefifofunds/)

Multi-asset price tracking system with PostgreSQL + QuestDB hybrid architecture.

**Documentation**:
- **[README.md](feefifofunds/README.md)** - FeeFiFoFunds app index and quick start
- **[overview.md](feefifofunds/overview.md)** - Architecture and data models
  - Hybrid database approach (PostgreSQL + QuestDB)
  - Asset, AssetPrice, Trade models
  - Management commands
  - Usage examples and workflows
- **[development.md](feefifofunds/development.md)** - Development guide
  - Local setup and prerequisites
  - Testing and debugging
  - Contribution guidelines
- **[kraken-ingestion.md](feefifofunds/kraken-ingestion.md)** - Fast CSV data ingestion
  - QuestDB ILP ingestion (50K-100K records/sec)
  - Tier-based filtering
  - Performance optimization
- **[data-sources.md](feefifofunds/data-sources.md)** - API integration framework
  - BaseDataSource pattern
  - Finnhub and Massive.com integrations
  - DTOs and transformations
- **[massive-integration.md](feefifofunds/massive-integration.md)** - Massive.com API
  - Historical stock/ETF data
  - Grouped endpoint optimization
- **[questdb-setup.md](feefifofunds/questdb-setup.md)** - Time-series database
  - Installation and configuration
  - Schema initialization
  - Performance tuning

### Omas Coffee

**Location**: [docs/apps/omas/](omas/)

German coffee cart website served via multi-domain routing with comprehensive brand guidelines.

**Documentation**:
- **[README.md](omas/README.md)** - Omas Coffee app index and quick start
- **[technical-setup.md](omas/technical-setup.md)** - Django implementation
  - Domain routing middleware
  - Multi-domain configuration
  - Local development and deployment
  - German translations
- **Brand Documentation**:
  - **[brand-foundation.md](omas/brand-foundation.md)** - Mission, values, brand personality
  - **[brand-standards.md](omas/brand-standards.md)** - Logo, colors, typography
  - **[design-guidelines.md](omas/design-guidelines.md)** - Design principles
  - **[digital-design.md](omas/digital-design.md)** - Website guidelines
  - **[physical-design.md](omas/physical-design.md)** - Coffee cart design
  - **[DESIGN_BRIEF.md](omas/DESIGN_BRIEF.md)** - Complete design spec

## Guidelines for App Maintainers

### Adding New App Documentation

1. **Create app directory**: `docs/apps/[app_name]/`
2. **Add README.md**: Brief overview with links to all docs
3. **Create documentation**: development.md, brand guidelines, etc.
4. **Update this file**: Add app to "Current App Documentation" section
5. **Update docs/README.md**: Add to app-specific documentation table
6. **Link from app**: Create `[app]/docs/README.md` pointing to centralized docs

### Organizing App Documentation

**Keep in docs/apps/**:
- Development setup and workflows
- Internal architecture decisions
- Brand and design systems
- App-specific contribution guidelines

**Move to docs/features/**:
- User-facing feature documentation
- Public API documentation
- Integration and usage guides
- Feature architecture (when relevant to users)

### Cross-Referencing

Always provide clear links between:
- App-specific docs ↔ Feature docs
- App-specific docs ↔ Core docs (architecture.md, commands.md)
- App README in source ↔ Centralized app docs

## Integration with Main Documentation

App-specific documentation is part of the centralized documentation structure:

```
Root Documentation
├── README.md (project landing page)
├── CLAUDE.md (AI-optimized quick reference)
└── docs/
    ├── README.md (documentation index) ← **Start here**
    ├── Core docs (architecture, commands, testing, etc.)
    ├── features/ (user-facing features)
    └── apps/ (app-specific internal docs) ← **You are here**
```

**For the complete documentation map**, see [docs/README.md](../README.md).

## Contributing

When contributing to an app:

1. **Read the app-specific development guide** in `docs/apps/[app_name]/`
2. **Follow app-specific guidelines** for code style, testing, etc.
3. **Update app documentation** when making significant changes
4. **Update feature docs** if user-facing behavior changes
5. **See** [../.cursor/rules/documentation.mdc](../../.cursor/rules/documentation.mdc) **for comprehensive documentation guidelines**

---

**Questions?** Check [docs/README.md](../README.md) for the complete documentation index, or create a GitHub issue.
