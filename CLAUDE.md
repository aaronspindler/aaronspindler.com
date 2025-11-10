# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Django-based personal website and blog (aaronspindler.com) with advanced features including knowledge graph visualization, photo management, and analytics tracking.

## Directory Organization

The project root has been organized for clarity:

- **`deployment/`**: All Docker and deployment-related files (Dockerfiles, docker-compose, env files)
- **`.config/`**: Tool configuration files (PostCSS, PurgeCSS, Prettier, .dockerignore, .python-version)
- **`requirements/`**: Python dependencies using **uv lockfiles**:
  - **Source files** (`.in`): Direct dependencies only - edit these files
  - **Lockfiles** (`.txt`): Auto-generated with all dependencies pinned - never edit directly
  - `base.in` / `base.txt`: Production dependencies
  - `dev.in` / `dev.txt`: Development dependencies
- **Root directory**: Kept minimal with only essential files (manage.py, Makefile, package.json, captain-definition files)

**Important**: When referencing files in commands or documentation:
- Requirements: Install from `.txt` lockfiles, edit `.in` source files, regenerate with `uv pip compile`
- Docker: Use `deployment/Dockerfile` and `deployment/docker-compose.test.yml`
- Configs: PostCSS/PurgeCSS automatically find configs in `.config/` via explicit paths in build commands

## Cursor Rules

This project includes AI context rules in `.cursor/rules/` to guide development. These rules have YAML frontmatter that controls when they apply:

### Core Rules (Always Apply)

These rules are always active and must be followed:

- **ai-context.mdc**: Guidelines for maintaining CLAUDE.md and README.md
  - Update these files when making architectural or feature changes
  - Keep documentation synchronized with code

- **comments.mdc**: Clean comment guidelines
  - Focus comments on current implementation
  - Avoid references to replaced technologies or previous approaches
  - Explain WHY, not just WHAT

- **documentation.mdc**: Documentation maintenance requirements
  - Update `docs/` directory for all code changes
  - Create feature docs in `docs/features/` for major features
  - Update `docs/commands.md` for new management commands
  - Code changes without documentation updates will be rejected

- **git-operations.mdc**: Git commit/push guidelines
  - **NEVER** commit or push without explicit user permission
  - Always show what will be committed before asking
  - Even when user says "push", confirm what will be pushed

### Conditional Rules (Apply When Relevant)

These rules apply to specific tasks or file types:

- **dependencies.mdc**: Dependency management (when modifying requirements files)
  - Only add direct dependencies that are explicitly imported
  - Never add transitive dependencies
  - Always regenerate lockfiles after editing `.in` files

- **testing.mdc**: Testing guidelines (when writing or running tests)
  - **Do NOT write new tests** unless explicitly requested
  - **Do NOT run tests** unless explicitly requested
  - **DO update existing tests** when modifying code with test coverage
  - Use named variables in test assertions for clarity

**IMPORTANT**: All cursor rules are properly formatted with YAML frontmatter. Always reference these rules along with CLAUDE.md when working on this codebase.

## Development Guidelines

### Management Command Output

When writing Django management commands, ensure output is:
- **Readable**: Use clear formatting with emojis, progress indicators, and visual separators
- **Helpful**: Include progress tracking (percentage, ETA), status indicators (✓, ✗, ⊘), and summary reports
- **Concise**: Balance detail with brevity - don't overwhelm with unnecessary information

**Good Examples:**
```
📂 Found 8656 files to process
⚙️  Intervals: 1440 minutes
✓ [1/8656] BTCUSD    1440m - +1,800 | 0.0% | ⏱️  1.2s | ETA 2h 45m
────────────────────────────────────────────────────────────────────────────────
✅ Complete: 8656/8656 files | +2,456,789 records | ⏱️  2h 38m
```

**Key Elements:**
- 📊 Summary statistics at start (files found, configuration)
- ⏱️ Real-time progress with percentage and ETA
- ✓/✗/⊘ Status indicators for success/failure/skip
- ─── Visual separators for sections
- 📈 Final summary with totals and elapsed time
- 🎯 Aligned columns for easy scanning

**Avoid:**
- Walls of text without structure
- Missing progress indication for long-running operations
- Unclear success/failure states
- Excessive verbosity that obscures important information

## Common Development Commands

### Local Development
```bash
# Activate virtual environment
source venv/bin/activate

# Install uv (first time only)
pip install uv

# Install dependencies from lockfile (10-100x faster than pip)
uv pip install -r requirements/base.txt

# Run migrations
python manage.py migrate

# Collect static files (with optimization)
python manage.py collectstatic_optimize

# Run development server
python manage.py runserver

# Create superuser for admin access
python manage.py createsuperuser
```

### Dependency Management with uv

```bash
# Add a new dependency
# 1. Edit requirements/base.in (add package with version)
# 2. Regenerate lockfile
uv pip compile requirements/base.in -o requirements/base.txt --generate-hashes

# Update all dependencies to latest compatible versions
uv pip compile --upgrade requirements/base.in -o requirements/base.txt --generate-hashes

# Update specific package
uv pip compile --upgrade-package django requirements/base.in -o requirements/base.txt --generate-hashes

# Install from lockfile (fast!)
uv pip install -r requirements/base.txt
```

**IMPORTANT**:
- Only edit `.in` source files, never `.txt` lockfiles
- Always regenerate lockfiles after modifying `.in` files
- Commit both `.in` and `.txt` files together
- **Dependabot PRs**: Lockfiles are automatically regenerated by the `dependabot-lockfile-regen.yml` workflow
- See `.cursor/rules/dependencies.mdc` for complete workflow

### Testing

**CRITICAL**: Do not write new tests for code in this repository unless explicitly requested by the user.

**When to Update Existing Tests:**
- DO update existing tests when modifying code that has test coverage
- DO update tests when changing function signatures or behavior
- DO update tests when fixing bugs that have test cases
- DO update tests when refactoring code with existing tests

**Running Tests:**
```bash
# Run tests locally (without parallel execution)
python manage.py test

# Run tests with coverage locally (without parallel execution)
coverage run --source='.' manage.py test --no-input
coverage report

# Run tests in CI/CD with parallel execution
# Note: Only use --parallel flag in CI/CD environments, not locally
python manage.py test --parallel

# Security check
safety check
```

**Test Assertion Guidelines:**

Prefer named variables for each parameter in assertions:

```python
# DON'T DO THIS:
self.assertEqual(test_result.get_count(), 10, "Expecting 10")

# DO THIS:
actual = test_result.get_count()
expected = 10
message = f"Found {actual} expected {expected}"
self.assertEqual(actual, expected, message)
```

See `.cursor/rules/testing.mdc` for complete testing guidelines.

### Makefile Commands

The project includes a Makefile for common development tasks:

```bash
# Static file management (default target)
make static         # Build CSS, optimize JS, collect/optimize static files, run pre-commit hooks
make css            # Build CSS only
make js             # Build and optimize JavaScript only
make collect        # Collect static files only
make clean          # Remove generated static files

# Docker testing commands
make test           # Run full test suite (build, run, cleanup)
make test-build     # Build Docker test images
make test-up        # Start test environment in background
make test-run       # Run all tests in Docker
make test-run-app APP=<app>    # Run tests for specific app
make test-shell     # Open shell in test container
make test-down      # Stop test environment
make test-clean     # Stop and remove test volumes
make test-coverage  # Run tests with coverage report

# Examples
make test-run-app APP=blog
make test-run-specific TEST=blog.tests.test_models
```

**Note**: The `make static` command can be used to manually rebuild and optimize static assets during development. WhiteNoise automatically handles versioning and serving of static files in production.

### CSS and JavaScript Build
```bash
# Build and optimize CSS
npm run build:css

# Build CSS in development mode (unminified)
python manage.py build_css --dev

# Build critical CSS
npm run build:css:critical

# Build and minify JavaScript
npm run build:js

# Build all assets
npm run build:all
```

**Note**: CSS and JS files are automatically served by WhiteNoise with content-based cache busting. During development, you can run `make static` to manually rebuild and optimize assets if needed.

**CSS Build Process and Workflow**:
- **Source files** in `static/css/` (like `base.css`, `blog.css`, etc.) are **developer-friendly and formatted** in git
  - These files have proper line breaks, indentation, and whitespace for easy editing
  - Never commit minified/single-line CSS source files to git
  - Pre-commit hooks automatically format CSS with Prettier and prevent minified sources
- **Build process** (`python manage.py build_css`):
  - Combines all source CSS files in load order → creates `combined.css`
  - Runs PostCSS with cssnano for minification → creates `combined.processed.css`
  - Runs PurgeCSS to remove unused CSS → creates `combined.purged.css` (skipped in dev mode with `--dev`)
  - Creates final `combined.min.css` with Gzip and Brotli compressed versions
  - Temporary files (`combined.css`, `combined.processed.css`, etc.) are auto-cleaned and gitignored
- **Versioning and serving**:
  - WhiteNoise's `CompressedManifestStaticFilesStorage` handles versioning during `collectstatic`
  - Automatically creates content-hashed filenames (e.g., `combined.min.263d67867382.css`)
  - Serves pre-compressed Brotli/Gzip versions when supported by browser
  - Cache headers set to 1 year with `immutable` directive for optimal performance
- **Important**: Source CSS files are **never modified** by the build process - they stay formatted in git

### Knowledge Graph Commands
```bash
# Rebuild knowledge graph cache
python manage.py rebuild_knowledge_graph

# Generate knowledge graph screenshot (high-quality, 2400x1600 at 2x DPI)
# For local development (Django server running on localhost:8000)
python manage.py generate_knowledge_graph_screenshot

# For production (screenshot the live site)
python manage.py generate_knowledge_graph_screenshot --url https://aaronspindler.com

# Custom URL (e.g., staging environment)
python manage.py generate_knowledge_graph_screenshot --url https://staging.example.com
```

**Note**: The screenshot generation command:
- Uses Pyppeteer/Chromium to take high-quality screenshots (2400x1600, 2x device scale factor)
- Runs automatically via Celery Beat daily at 4 AM UTC (screenshots production site)
- Stores screenshots in the database with hash-based caching to avoid duplicates
- Defaults to `http://localhost:8000` for local development

### Lighthouse Performance Monitoring
```bash
# Run Lighthouse audit and store results
python manage.py run_lighthouse_audit

# Run audit for a specific URL
python manage.py run_lighthouse_audit --url https://example.com

# Setup daily automated audits (Celery Beat)
python manage.py setup_periodic_tasks
```

### Cache Management
```bash
# Clear all caches
python manage.py clear_cache

# Setup periodic tasks (for Celery)
python manage.py setup_periodic_tasks
```

### Search Index Management
```bash
# Rebuild full-text search index for all content
python manage.py rebuild_search_index

# Rebuild only blog posts
python manage.py rebuild_search_index --content-type blog

# Rebuild only photos
python manage.py rebuild_search_index --content-type photos

# Rebuild only photo albums
python manage.py rebuild_search_index --content-type albums

# Clear and rebuild entire index
python manage.py rebuild_search_index --clear

# Example: Clear and rebuild only blog posts
python manage.py rebuild_search_index --clear --content-type blog
```

**Note**: The search index should be rebuilt whenever:
- New blog posts are added
- Blog post content is significantly modified
- New photos or albums are added
- Project or book data changes

### Security & Request Tracking
```bash
# Geolocate IP addresses for RequestFingerprint records
python manage.py geolocate_fingerprints

# Limit number of records to process
python manage.py geolocate_fingerprints --limit 100

# Re-geolocate all records (including those with existing geo data)
python manage.py geolocate_fingerprints --force

# Custom batch size (default: 100 IPs per batch)
python manage.py geolocate_fingerprints --batch-size 50

# Skip confirmation prompt (for automated runs via cron/Celery)
python manage.py geolocate_fingerprints --yes

# Remove local/private IP request fingerprints
python manage.py remove_local_fingerprints

# Preview which records would be deleted (dry-run mode)
python manage.py remove_local_fingerprints --dry-run

# Limit number of records to delete
python manage.py remove_local_fingerprints --limit 100
```

**Note**: The `geolocate_fingerprints` command uses ip-api.com free tier:
- Single endpoint: 45 requests/minute
- Batch endpoint: 15 requests/minute (100 IPs per batch)
- IP addresses are automatically filtered to exclude local/private IPs
- Geolocation data includes: city, country, coordinates, timezone, ISP, etc.
- Shows statistics before processing (total records vs unique IPs)
- Waits for Enter key confirmation before proceeding (skip with --yes)
- Run periodically (e.g., via cron or Celery Beat) to batch process new records
- Geolocation is NOT performed during request processing to avoid latency

**Note**: The `remove_local_fingerprints` command removes historical local/private IP records:
- Local IPs: 127.0.0.1, ::1, localhost
- Private ranges: 10.x.x.x, 192.168.x.x, 172.16-31.x.x
- Middleware now automatically skips tracking local requests
- Use `--dry-run` to preview deletions before committing
- Useful for one-time cleanup after deploying local IP filtering

### FeeFiFoFunds Data Management

#### Database Migration Commands
```bash
# IMPORTANT: FeeFiFoFunds uses hybrid database approach
# - Asset model: PostgreSQL (default database)
# - AssetPrice and Trade models: QuestDB (questdb database, managed=False)

# Create new migrations for feefifofunds (Asset model only)
python manage.py makemigrations feefifofunds

# Apply migrations to PostgreSQL (Asset model)
python manage.py migrate feefifofunds

# Initialize QuestDB schema (AssetPrice and Trade tables)
python manage.py setup_questdb_schema

# Drop and recreate QuestDB tables (CAREFUL!)
python manage.py setup_questdb_schema --drop

# Note: AssetPrice and Trade use managed=False and are created manually in QuestDB
# Django migrations do NOT apply to QuestDB tables
```

#### Asset Management Commands
```bash
# Create a new asset manually
python manage.py create_asset --ticker BTC --name Bitcoin --category CRYPTO

# Specify quote currency (default: USD)
python manage.py create_asset --ticker ETHUSD --name Ethereum --category CRYPTO --quote-currency USD

# Add description
python manage.py create_asset --ticker AAPL --name "Apple Inc." --category STOCK --description "Technology company"
```

#### Data Ingestion Commands

**Sequential Ingestion (Recommended):**
```bash
# Ingest Kraken OHLCV and trade data - fast sequential processing
python manage.py ingest_sequential --tier TIER1 --file-type both

# Ingest only OHLCV (candle) data for TIER1 assets
python manage.py ingest_sequential --tier TIER1 --file-type ohlcv

# Ingest only trade (tick) data for TIER1 assets
python manage.py ingest_sequential --tier TIER1 --file-type trade

# Filter by specific intervals (OHLCV only)
python manage.py ingest_sequential --tier TIER1 --file-type ohlcv --intervals 60,1440

# Ingest all assets and all file types (default)
python manage.py ingest_sequential

# Skip confirmation prompt for automated runs
python manage.py ingest_sequential --tier TIER1 --yes

# Stop on first error (default: continue)
python manage.py ingest_sequential --tier TIER1 --stop-on-error
```

**Load Prices from External Sources:**
```bash
# Load prices from Massive.com (stocks/ETFs, 2 years free)
python manage.py load_prices --ticker AAPL --source massive --days 7

# Load prices from Finnhub (stocks, crypto, forex)
python manage.py load_prices --ticker AAPL --source finnhub --days 30

# Dry run to preview data
python manage.py load_prices --ticker BTC --source finnhub --days 7 --dry-run
```

**Backfill Historical Prices:**
```bash
# Backfill single asset
python manage.py backfill_prices --ticker AAPL --source massive --days 730

# Backfill all active assets
python manage.py backfill_prices --source massive --days 365 --all

# Backfill specific category
python manage.py backfill_prices --source massive --days 365 --all --category STOCK

# Backfill using grouped endpoint (MUCH faster - 1 API call per day instead of N)
python manage.py backfill_prices --source massive --days 365 --all --grouped

# Backfill crypto only with grouped endpoint
python manage.py backfill_prices --source massive --days 365 --all --grouped --category CRYPTO

# Specify date range
python manage.py backfill_prices --ticker AAPL --source massive --start 2024-01-01 --end 2024-12-31

# Dry run
python manage.py backfill_prices --ticker AAPL --source massive --days 30 --dry-run
```

**Note**: See `docs/features/feefifofunds.md` for comprehensive documentation
- **QuestDB ILP ingestion**: Direct QuestDB Influx Line Protocol for maximum speed
- **Tier-based filtering**: TIER1 (major), TIER2 (established), TIER3 (emerging), TIER4 (speculative)
- **File type filtering**: OHLCV (candles), trade (ticks), or both
- **Interval filtering**: Filter OHLCV data by specific intervals (1, 5, 15, 30, 60, 240, 720, 1440 minutes)
- **Auto-asset creation**: Automatically creates Asset records with tier classification
- **Idempotent operations**: Uses ON CONFLICT DO NOTHING, safe to re-run
- **Progress tracking**: Real-time stats with ETA calculation
- **File management**: Moves completed files to ingested/ directory
- **Performance**: ~50K-100K records/second with QuestDB ILP

## Architecture Overview

### Django Apps Structure
- **config/**: Main Django configuration
  - `settings.py`: Environment-based settings using django-environ
  - `urls.py`: Main URL routing
  - `storage_backends.py`: S3 storage configuration for media files (photos)
  - `celery.py`: Celery configuration for async tasks

- **pages/**: Core website functionality
  - Page visit tracking with geo-location data
  - Custom decorators for visit tracking
  - Context processors for resume settings
  - Management commands for CSS/JS optimization

- **blog/**: Blog system with unique features
  - Template-based blog posts stored in `templates/blog/`
  - Knowledge graph visualization system
  - API endpoints for graph data and screenshots
  - Posts organized by category (personal, projects, reviews, tech)

- **photos/**: Photo management system
  - Photo model with automatic image optimization (multiple sizes)
  - EXIF metadata extraction
  - Album management with zip generation
  - Private/public album support

- **utils/**: Utility features and performance monitoring
  - Notification system (email and SMS)
  - Request fingerprinting and security tracking:
    - RequestFingerprint model for tracking all requests
    - Automatic filtering of local/private IP requests
    - IP-based geolocation with batch processing support
    - User agent parsing (browser, OS, device detection)
    - Suspicious request detection
    - Management commands: `geolocate_fingerprints`, `remove_local_fingerprints`
  - Lighthouse performance monitoring:
    - Automated audits tracking 4 key metrics (Performance, Accessibility, Best Practices, SEO)
    - Historical data storage with 30-day visualization
    - Badge endpoint for shields.io integration
    - Celery Beat task for nightly audits at 2 AM UTC

- **accounts/**: User authentication via django-allauth
  - Custom user model
  - Registration disabled by default (NoSignupAccountAdapter)

- **feefifofunds/**: Multi-asset tracking and analysis (FeeFiFoFunds project - MVP)
  - **Hybrid database architecture**: PostgreSQL for Asset metadata, QuestDB for time-series data
  - **Universal Asset model**: Single model with category (STOCK, CRYPTO, COMMODITY, CURRENCY) and tier (TIER1-4) fields
  - **QuestDB time-series models**: AssetPrice and Trade models for high-performance OHLCV and tick data
  - **Multi-interval OHLCV**: Track prices at different timeframes (1m, 5m, 15m, 60m, daily, etc.)
  - **Trade tick data**: Individual trade records with microsecond precision
  - **Multiple data sources**: Kraken CSV ingestion, Massive.com API, Finnhub API
  - **QuestDB ILP ingestion**: Fast sequential ingestion via Influx Line Protocol (50K-100K records/sec)
  - **Tier-based filtering**: Filter ingestion by asset importance (TIER1-4)
  - Django admin interfaces for Asset management

- **omas/**: Omas Coffee website (omas.coffee)
  - Separate website served via domain routing middleware
  - Independent URL routing and templates
  - Coffee-themed design and branding
  - Homepage with feature showcase

### FeeFiFoFunds MVP Architecture

The **feefifofunds** app provides a simplified MVP for tracking financial asset prices over time using a hybrid database approach (PostgreSQL + QuestDB).

**Database Architecture:**
- **PostgreSQL (default database)**: Asset model with metadata (ticker, name, category, tier)
- **QuestDB (time-series database)**: AssetPrice and Trade models for high-performance OHLCV and trade data storage

**Model Structure:**

```
Asset (PostgreSQL)        ← Universal model for all asset types
├── ticker               ← Unique identifier (e.g., "BTC", "AAPL", "GLD")
├── name                 ← Full asset name
├── category             ← STOCK, CRYPTO, COMMODITY, or CURRENCY
├── tier                 ← TIER1-4 or UNCLASSIFIED (market cap/importance)
├── description          ← Optional details
└── active               ← Whether actively tracked

AssetPrice (QuestDB)     ← OHLCV price records (candles)
├── asset_id             ← Integer ID reference to Asset
├── time                 ← Timestamp (QuestDB designated timestamp)
├── open                 ← Opening price
├── high                 ← Highest price
├── low                  ← Lowest price
├── close                ← Closing price
├── volume               ← Trading volume (optional)
├── interval_minutes     ← Time interval in minutes (1, 5, 15, 60, 1440, etc.)
├── trade_count          ← Number of trades during interval (for OHLCV data)
├── quote_currency       ← Currency for pricing (USD, EUR, BTC, etc.)
└── source               ← Data source (e.g., 'finnhub', 'massive', 'kraken')
    PARTITION BY DAY

Trade (QuestDB)          ← Individual trade records (tick data)
├── asset_id             ← Integer ID reference to Asset
├── time                 ← Exact timestamp (QuestDB designated timestamp)
├── price                ← Trade execution price
├── volume               ← Trade volume/quantity
├── quote_currency       ← Currency for pricing
└── source               ← Data source (default: 'kraken')
    PARTITION BY DAY
```

**Key Features:**
- **Hybrid database approach**: PostgreSQL for metadata, QuestDB for time-series data
- **Tier classification**: TIER1 (major), TIER2 (established), TIER3 (emerging), TIER4 (speculative)
- **Multi-interval support**: Store OHLCV data at different timeframes (1m, 5m, 15m, 60m, daily, etc.)
- **Tick data support**: Trade model for individual trade records with microsecond precision
- **Multi-source support**: Track prices from multiple data sources (Kraken, Finnhub, Massive.com)
- **QuestDB optimizations**: SYMBOL types, PARTITION BY DAY, designated timestamps
- **Simple queries**: `Asset.objects.filter(category='CRYPTO', tier='TIER1')`
- **Time-series performance**: Sub-second queries on millions of records with QuestDB
- **Auto-asset creation**: Commands automatically create Asset records during ingestion
- **Extensible**: Easy to add new fields, categories, tiers, or data sources
- **Admin-ready**: Full Django admin interfaces for Asset management

**Data Ingestion:**
- **ingest_sequential**: Fast sequential QuestDB ILP ingestion for Kraken CSV files
- **load_prices**: Load prices from external APIs (Massive.com, Finnhub)
- **backfill_prices**: Backfill historical data with grouped API mode for efficiency
- **create_asset**: Manually create Asset records
- **setup_questdb_schema**: Initialize QuestDB tables

**Performance:**
- **QuestDB ILP**: 50K-100K records/second ingestion via Influx Line Protocol
- **Partitioning**: Daily partitions for optimal query performance
- **Symbols**: Optimized storage for repeated strings (source, quote_currency)
- **Time-series queries**: Sub-100ms for complex aggregations

**Design Philosophy:**
- Start simple with MVP, add complexity only when needed
- Use category and tier fields instead of complex inheritance
- Leverage QuestDB for time-series performance at scale
- Focus on core functionality: storing asset prices over time at multiple timeframes

### Multi-Domain Support

The application uses custom middleware (`config/domain_routing.py`) to serve multiple websites from a single Django project:

**How It Works**:
- `DomainRoutingMiddleware` inspects the request hostname
- Maps specific domains to their corresponding URL configurations
- Falls back to `config.urls` (main site) for unmapped domains

**Configuration** (`config/domain_routing.py`):
```python
domain_mapping = {
    "omas.coffee": "omas.urls",
    "www.omas.coffee": "omas.urls",
}
```

**Settings** (`config/settings.py`):
- Middleware: `DomainRoutingMiddleware` must be first in the middleware stack
- `ALLOWED_HOSTS`: Must include all domains to be served
- `CSRF_TRUSTED_ORIGINS`: Must include all trusted domain origins

**Adding New Domains**:
1. Create a new Django app for the domain
2. Add app to `INSTALLED_APPS` in settings.py
3. Add domain mapping to `config/domain_routing.py`
4. Add domain to `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` in settings.py
5. Create URL configuration (`urls.py`) and views for the new domain
6. Create templates for the new domain
7. Deploy and configure DNS to point to the application

**Local Development**:
- Use `/etc/hosts` to map domains to localhost for testing
- Example: Add `127.0.0.1 omas.coffee` to `/etc/hosts` to test omas.coffee locally
- Access via `http://omas.coffee:8000` when running `python manage.py runserver`

### Key Technical Features

1. **Knowledge Graph System** (`blog/knowledge_graph.py`)
   - Builds interactive graph from blog post metadata
   - Uses Pyppeteer for server-side screenshot generation
   - Caching system for performance
   - LinkParser class for extracting internal/external links
   - GraphBuilder for constructing graph structures
   - **Visualization Enhancements** (October 2024):
     - Adaptive force simulation parameters based on node count
     - Velocity limiting to prevent jitter (max velocity: 10)
     - Improved collision detection with 1.0x radius for blog posts
     - Golden angle distribution for category positioning
     - Grid layout for large category groups (8+ nodes)
     - Stabilization phase when alpha < 0.1
     - Maximum iteration limit (500 ticks) to prevent infinite running

2. **Static File Optimization**
   - Custom `collectstatic_optimize` command with image compression
   - CSS build pipeline with PostCSS, PurgeCSS, and critical CSS extraction
   - JavaScript minification with Terser
   - Brotli compression for static assets
   - WhiteNoise for serving static files (CSS, JS, fonts) from container

3. **Blog Post System**
   - HTML templates as blog posts
   - Metadata extraction from templates
   - View count tracking per post
   - Category-based organization
   - Template normalization for consistency
   - **Important**: When modifying blog post templates in `templates/blog/*/*.html`, utilize existing stylesheets and maintain consistency with other posts

4. **Full-Text Search System** (`utils/search.py`, `utils/models/search.py`)
   - PostgreSQL-powered full-text search with trigram similarity for typo tolerance
   - SearchableContent model (in utils app) stores indexed content from blog posts, projects, and books
   - Photo and PhotoAlbum models have search_vector fields with GIN indexes
   - Search features:
     - Full-text search using SearchVector, SearchQuery, and SearchRank
     - Trigram similarity (pg_trgm extension) for typo-tolerant matching
     - Combined scoring: 70% FTS rank + 30% trigram similarity
     - Relevance thresholds: rank > 0.01 OR similarity > 0.2
     - Weighted fields: title (A), description (B), content (C)
   - Frontend autocomplete already implemented:
     - Vanilla JavaScript in `/static/js/search-autocomplete.js`
     - Triggers after 2 characters typed
     - Keyboard navigation (arrow keys, enter, escape)
     - API endpoint: `/api/search/autocomplete/`
   - Management command: `rebuild_search_index` (in utils app) to populate/update search index
   - **Performance**: Sub-100ms response time for autocomplete queries

### Deployment Configuration
- **Docker**: Optimized build with Pyppeteer for screenshot generation (~800MB image size)
- **Database**: PostgreSQL with psycopg3
- **Storage**:
  - Static files (CSS, JS, fonts): WhiteNoise (served from container)
  - Media files (photos, uploads): AWS S3 via django-storages
- **Server**: Gunicorn with 8 workers
- **Cache**: Redis for caching and sessions
- **Task Queue**: Celery with Redis broker

### Environment Variables
Required environment variables (use django-environ):
- `DATABASE_URL`: PostgreSQL connection string
- `SECRET_KEY`: Django secret key
- `DEBUG`: Debug mode flag
- AWS credentials (required for production media storage; optional for local development):
  - `AWS_ACCESS_KEY_ID`
  - `AWS_SECRET_ACCESS_KEY`
  - `AWS_STORAGE_BUCKET_NAME`
  - `AWS_S3_REGION_NAME` (optional, defaults to us-east-1)
- `REDIS_URL`: Redis connection URL (for caching)
- `USE_DEV_CACHE_PREFIX`: Prefix cache keys with 'dev_' for local development (optional, defaults to False)
- `CELERY_BROKER_URL`: Celery broker URL (defaults to REDIS_URL)
- `RESUME_ENABLED`: Enable resume download feature
- `RESUME_FILENAME`: Resume file name

### Blog Post Template Structure
Blog posts are HTML templates in `templates/blog/<category>/<filename>.html` with metadata:
```html
{% block meta_description %}Post description{% endblock %}
{% block meta_title %}Post Title{% endblock %}
{% block meta_publish_date %}YYYY-MM-DD{% endblock %}
{% block meta_post_type %}Category{% endblock %}
{% block meta_reading_time %}X{% endblock %}
```

### Code Block Formatting in Blog Posts

**IMPORTANT**: Blog posts use Prism.js for syntax highlighting. Always format code blocks as follows:

#### Multi-line Code Blocks
```html
<pre><code class="language-python">
def hello_world():
    print("Hello, World!")
</code></pre>
```

#### Supported Languages
Common language classes (use `language-{name}` format):
- `language-python` - Python code
- `language-bash` - Bash/shell commands
- `language-javascript` or `language-js` - JavaScript
- `language-html` - HTML markup
- `language-css` - CSS styles
- `language-sql` - SQL queries
- `language-json` - JSON data
- `language-text` - Plain text output

#### Inline Code
For inline code within paragraphs, use simple `<code>` tags:
```html
<p>Use the <code>manage.py</code> command to run migrations.</p>
```

#### Technical Notes
- Prism.js automatically adds syntax highlighting with line numbers
- Copy-to-clipboard button appears on hover
- The site's CSS overrides Prism colors to match the theme
- **DO NOT** add custom borders, backgrounds, or margins to code elements - let Prism handle the layout

### Testing Approach
- Django's built-in test framework
- Parallel test execution supported (CI/CD only, not for local development)
- Test files organized in app-specific `tests/` directories
- Coverage reporting with coverage.py
- CI/CD via GitHub Actions with PostgreSQL service container

#### Docker Test Environment
The project includes a comprehensive Docker-based test environment (`docker-compose.test.yml`):
- **Services**: Web, PostgreSQL, Redis, Celery, Flower, Localstack (S3 emulation)
- **Configuration**: `env.test` for test-specific environment variables
- **Test runner**: Dedicated container for running tests with `config.settings_test`
- **Benefits**: Isolated test environment matching production setup
- **Usage**: Use `make test` commands (see Makefile Commands section above)
- **Note**: Test environment uses Localstack for S3 testing (no AWS credentials needed)

### Security and Code Quality
- **CodeQL Analysis**: Automated security scanning runs on:
  - Every push to main
  - All pull requests
  - Daily scheduled scans at 5:30 AM UTC
  - Scans both Python and JavaScript code
  - Uses `security-and-quality` query suite (comprehensive security + code quality checks)

- **GitHub Copilot Autofix**: Provides AI-powered fix suggestions for CodeQL alerts
  - Available for public repositories (free with GitHub Advanced Security)
  - **How it works**:
    - CodeQL runs on pull requests and detects security/quality issues in the PR's code changes
    - Copilot Autofix automatically analyzes new alerts and suggests fixes as PR comments
    - Developers can review and apply suggested fixes with one click
  - **Important**: Copilot Autofix only works for **new alerts detected in PR code changes**, not existing alerts on main branch
  - **Manual fix generation**: For existing alerts on main branch:
    1. Go to repository Security tab → Code scanning alerts
    2. Click on an alert to view details
    3. Click "Generate fix" button to get AI-powered fix suggestions
    4. Review and apply the suggested fix manually
  - Requires GitHub Advanced Security enabled (automatic for public repos)

- **Pre-commit Hooks**: Local code quality enforcement (`.pre-commit-config.yaml`)
  - **Ruff**: Fast Python linter and formatter
    - `ruff` hook: Linting with auto-fixing for Python code (replaces flake8, isort)
    - `ruff-format` hook: Code formatting (Black-compatible)
    - Configuration in `pyproject.toml`
  - **Prettier**: CSS formatting for source files only
    - Formats developer-friendly CSS files in `static/css/`
    - Excludes generated/optimized CSS files (`.opt.css`, `combined.*.css`, etc.)
  - **CSS Format Checker**: Custom script to prevent minified CSS from being committed
    - Script: `scripts/check-css-format.sh`
    - Ensures source CSS files remain developer-friendly
  - **File Quality Checks**: Standard pre-commit hooks
    - Trailing whitespace removal
    - End-of-file fixer
    - YAML validation
    - Large file checker (max 1MB)
    - Merge conflict checker
  - **Setup**: Run `pre-commit install` after cloning the repository
  - **Usage**: Automatically runs on `git commit`, or run manually with `pre-commit run --all-files`
  - **Note**: The `make static` command automatically runs pre-commit hooks at the end

### Code Style Configuration (`pyproject.toml`)

The project uses Ruff for linting and formatting, configured in `pyproject.toml`:

**General Settings**:
- Line length: 120 characters
- Target Python version: 3.13
- Excludes: migrations, venv, staticfiles, node_modules, third-party projects

**Linting Rules**:
- Enabled: pycodestyle (E/W), pyflakes (F), isort (I)
- Ignored: E501 (line too long, handled by formatter)

**Formatting**:
- Black-compatible formatter
- Double quotes for strings
- Space indentation
- Auto line-ending detection

**Per-File Ignores**:
- Test files: Allow star imports (F403, F405), unused variables (F841)
- `__init__.py`: Allow unused imports (F401)
- Admin files: Allow bare except clauses (E722) for display methods
- Build commands: Allow unused subprocess results (F841)
- Settings/utils: Allow module-level imports not at top (E402)

**Import Sorting**:
- First-party packages: accounts, blog, pages, photos, utils, config
- Order: future → standard-library → third-party → first-party → local-folder

### Prettier Configuration (`.prettierrc`)

CSS formatting is managed by Prettier with the following settings:
- Print width: 120 characters
- Tab width: 2 spaces
- Semi-colons: Required
- Quotes: Double quotes
- Trailing commas: ES5 style
- Line endings: LF (Unix-style)

**Note**: Only source CSS files in `static/css/` are formatted by Prettier. Generated/optimized CSS files (`.opt.css`, `combined.*.css`, etc.) are excluded via `.prettierignore`.

### Performance Optimizations
- Graph data caching with 20-minute timeout
- File modification time tracking for cache invalidation
- Multi-resolution image generation (thumbnail, small, medium, large)
- Static file compression and optimization
- Database query optimization with select/prefetch related
- PostgreSQL full-text search with GIN indexes
- Trigram indexes for typo-tolerant search

## Documentation Requirements

**CRITICAL**: This project maintains comprehensive documentation in the `docs/` directory. All code changes MUST be accompanied by corresponding documentation updates.

### Documentation Structure

```
docs/
├── architecture.md          # System design and Django apps
├── testing.md              # Test framework and factories
├── commands.md             # Management commands reference
├── api.md                  # REST API endpoints
├── deployment.md           # Production deployment
├── maintenance.md          # Monitoring and troubleshooting
└── features/               # Feature-specific documentation
    ├── blog-system.md
    ├── knowledge-graph.md
    ├── photo-management.md
    ├── search.md
    ├── performance-monitoring.md
    └── request-tracking.md
```

### When to Update Documentation

**ALWAYS update documentation when**:

1. **Adding New Features**:
   - Create new file in `docs/features/` for major features
   - Update existing feature docs for enhancements
   - Add to README.md features list with doc link
   - Update `docs/architecture.md` if new Django app or architectural change

2. **Adding Management Commands**:
   - Add command to `docs/commands.md` with full reference (usage, options, examples, when to run)
   - Update README.md common commands if frequently used

3. **Modifying APIs**:
   - Update `docs/api.md` with new/modified endpoints
   - Include request/response examples
   - Document new query parameters or body fields

4. **Changing Configuration**:
   - Update relevant docs with new environment variables
   - Document in `docs/deployment.md`
   - Update `.env.example` if needed

5. **Deployment Changes**:
   - Update `docs/deployment.md` for infrastructure changes
   - Document new services, containers, or dependencies

6. **Breaking Changes**:
   - Clearly document in all relevant docs
   - Add migration guide if needed
   - Update README.md if affects quick start

### Documentation Standards

- **Clear and Concise**: Use simple language, avoid jargon
- **Examples**: Include practical code examples for all features
- **Commands**: Show actual commands users can copy/paste
- **Cross-References**: Link to related documentation
- **Professional Tone**: Technical but approachable

See `.cursor/rules/documentation.mdc` for complete documentation guidelines, templates, and standards.

### Verification Before PR

Before completing ANY pull request, verify:

- [ ] README.md updated if new feature or breaking change
- [ ] Feature-specific doc created/updated in `docs/features/`
- [ ] `docs/commands.md` updated if new management command added
- [ ] `docs/api.md` updated if API endpoints added/modified
- [ ] `docs/architecture.md` updated if new app or architectural change
- [ ] `docs/deployment.md` updated if deployment process changes
- [ ] Examples tested and working
- [ ] Cross-references checked and valid
- [ ] No broken links in documentation

**IMPORTANT**: Code changes without documentation updates will be rejected. Documentation is not optional—it's a core part of every feature.

## Final Notes

### Always Follow These Guidelines

1. **Cursor Rules**: Always reference the cursor rules in `.cursor/rules/` when working on this codebase
   - **ai-context.mdc**: Keep CLAUDE.md and README.md synchronized with code changes
   - **documentation.mdc**: Update `docs/` directory whenever code changes
   - **comments.mdc**: Write clean, forward-looking comments without references to replaced implementations
   - **dependencies.mdc**: Only add direct dependencies that are explicitly imported/used
   - **git-operations.mdc**: Always ask before committing or pushing changes
   - **testing.mdc**: Do not write new tests unless explicitly requested; do update existing tests when modifying code

2. **Testing**:
   - **Do NOT run tests** unless explicitly requested by the user
   - **Do NOT write new tests** unless explicitly requested by the user
   - **DO update existing tests** when modifying code that has test coverage

3. **Code Quality**:
   - Run `pre-commit run --all-files` before pushing (or use graphite which auto-runs hooks)
   - Follow the code style configuration in `pyproject.toml`
   - Use Ruff for linting and formatting

4. **Documentation**:
   - Code changes without documentation updates will be rejected
   - Documentation is not optional—it's a core part of every feature
   - See `.cursor/rules/documentation.mdc` for complete guidelines

5. **Git Operations**:
   - **Never commit or push without explicit user permission**
   - Always show what will be committed before asking for permission
   - See `.cursor/rules/git-operations.mdc` for complete workflow
