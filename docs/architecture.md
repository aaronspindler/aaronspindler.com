# Architecture & Project Structure

## Overview

This Django-based personal website is organized into modular apps, each handling specific functionality. The architecture emphasizes separation of concerns, performance optimization, and maintainability.

## Project Structure

```
aaronspindler.com/
├── config/              # Main Django configuration
│   ├── settings.py     # Environment-based settings
│   ├── urls.py         # Main URL routing
│   ├── storage_backends.py  # S3 storage for media files
│   └── celery.py       # Celery async task configuration
├── accounts/           # User authentication
│   ├── models.py       # Custom user model
│   └── adapters.py     # django-allauth customization
├── blog/              # Blog system and knowledge graph
│   ├── models.py       # Blog comments, votes, screenshots
│   ├── views.py        # Blog rendering, comments, voting
│   ├── knowledge_graph.py  # Graph building and visualization
│   ├── utils.py        # Blog template utilities
│   ├── forms.py        # Comment forms
│   └── templates/blog/ # Blog post templates by category
├── omas/              # Omas Coffee website (omas.coffee)
│   ├── urls.py         # Domain-specific routing
│   ├── views.py        # Homepage and content pages
│   ├── static/omas/    # CSS, JS, and images
│   └── templates/omas/ # Domain-specific templates
├── pages/             # Core website pages
│   ├── views.py        # Home, health check, resume
│   ├── utils.py        # Books and projects data
│   └── management/     # CSS/JS optimization commands
├── photos/            # Photo management
│   ├── models.py       # Photo and PhotoAlbum models
│   ├── image_utils.py  # EXIF extraction, optimization
│   └── tasks.py        # Album zip generation (Celery)
├── utils/             # Cross-cutting utilities
│   ├── models/         # Utility models (search, notifications, security)
│   ├── search.py       # Full-text search functions
│   ├── middleware.py   # Request fingerprinting
│   ├── tasks.py        # Notification tasks
│   └── management/     # Search index, cache commands
├── feefifofunds/      # Multi-asset tracking system
│   ├── models/         # Modular model organization
│   │   ├── asset.py    # Asset model (PostgreSQL)
│   │   ├── price.py    # AssetPrice model (QuestDB)
│   │   └── trade.py    # Trade model (QuestDB)
│   ├── admin.py        # Django admin configuration
│   ├── services/       # Data source integrations
│   │   └── data_sources/
│   │       ├── base.py  # BaseDataSource abstract class
│   │       ├── dto.py   # Data Transfer Objects
│   │       ├── finnhub.py  # Finnhub API integration
│   │       └── massive.py  # Massive.com API integration
│   └── tests/          # Test suite
├── projects/          # Third-party projects (not Django apps)
│   └── ActionsUptime/ # GitHub Actions monitoring service
├── templates/         # Project-wide templates
├── static/           # Static assets (CSS, JS, images)
└── tests/            # Test data factories
```

### Note on Projects Directory

The `projects/` directory contains third-party projects that are not part of the main Django application:

- **ActionsUptime**: A separate Django project for monitoring GitHub Actions workflows and web endpoints
  - Not integrated with the main aaronspindler.com codebase
  - Included for reference or development purposes
  - Has its own Django settings, apps, and deployment configuration
  - Should not be imported or referenced by the main application

These projects are independent and should not be confused with Django apps in the main application.

## Django Apps

### config/ - Main Configuration

**Purpose**: Central configuration for the Django project.

**Key Components**:
- **settings.py**: Environment-based settings using django-environ
  - Database configuration (PostgreSQL)
  - Cache configuration (Redis)
  - Storage backends (WhiteNoise for static, S3 for media)
  - Security settings (CORS, CSRF, session management)
  - Static file configuration

- **urls.py**: Main URL routing
  - App-level URL includes
  - API endpoints
  - Admin interface

- **domain_routing.py**: Multi-domain support
  - Maps domains to specific URL configurations
  - DomainRoutingMiddleware for request routing
  - Supports omas.coffee for separate website

- **storage_backends.py**: S3 storage for media files
  - PublicMediaStorage for photos and uploads
  - CloudFront CDN integration for media delivery

- **celery.py**: Celery configuration
  - Task queue setup
  - Periodic task scheduling (Celery Beat)

### accounts/ - User Authentication

**Purpose**: User authentication and account management.

**Key Components**:
- **Custom User Model**: Extends Django's AbstractUser
- **NoSignupAccountAdapter**: Disables public registration by default
- **Integration**: django-allauth for flexible authentication options

**Features**:
- Custom user fields
- Password reset functionality
- Email verification support
- Social authentication ready (configured but not enabled)

### blog/ - Blog System & Knowledge Graph

**Purpose**: Template-based blog system with interactive knowledge graph visualization.

**Key Components**:

**Models** (`models.py`):
- **BlogComment**: User comments on blog posts with moderation
- **CommentVote**: Upvote/downvote system for comments
- **KnowledgeGraphScreenshot**: Cached graph screenshots

**Views** (`views.py`):
- Blog post rendering from templates
- Comment submission and moderation
- Voting endpoints
- Category and post list views

**Knowledge Graph** (`knowledge_graph.py`):
- **LinkParser**: Extracts internal/external links from blog posts
- **GraphBuilder**: Constructs node/edge graph structures
- **Screenshot Generation**: Pyppeteer-powered server-side rendering
- **Caching System**: 20-minute cache with smart invalidation

**Template System**:
- Blog posts stored as HTML templates in `blog/templates/blog/<category>/`
- Metadata extracted from template blocks
- Categories: hobbies, personal, projects, reviews, tech
- Automatic numbering system (e.g., `0001_Post_Title.html`)

### omas/ - Omas Coffee Website

**Purpose**: Separate website (omas.coffee) served from the same Django application using multi-domain routing.

**Key Components**:

**Multi-Domain Routing**:
- **DomainRoutingMiddleware** (`config/domain_routing.py`):
  - Inspects request hostname and routes to appropriate URL configuration
  - Maps `omas.coffee` and `www.omas.coffee` to `omas.urls`
  - Must be first in middleware stack for proper routing

**German Translation System**:
- **Interactive Hover Tooltips** (`static/omas/js/german-translations.js`):
  - Automatic detection of German terms in page content
  - Elegant tooltips with German flag emoji and translations
  - Mobile touch support with auto-dismiss
  - Smart positioning based on viewport space
- **Visual Design**: Rich walnut and antique gold color palette
- **Typography**: UnifrakturMaguntia font for Gothic brand styling

**Features**:
- Coffee cart website honoring German Kaffeezeit tradition
- Memorial tribute to owner's grandmother
- Spring 2025 opening announcement
- Newsletter signup integration

**Related Documentation**: [Omas Coffee App Documentation](apps/omas/)

### pages/ - Core Website

**Purpose**: Main website pages and global functionality.

**Key Components**:

**Views** (`views.py`):
- **Home Page**: Aggregates blog posts, projects, books, albums
- **Health Check**: Application health monitoring endpoint
- **Resume Download**: Conditional resume serving

**Context Processors**:
- Global template variables
- Resume settings
- Site-wide configuration

**Management Commands** (`management/`):
- **collectstatic_optimize**: Static file collection with image optimization
- **build_css**: CSS compilation and minification with PostCSS/PurgeCSS
- **optimize_js**: JavaScript minification with Terser

**Visit Tracking**:
- Page visit tracking with request fingerprinting
- Privacy-respecting analytics
- Custom decorators for tracking specific pages

### photos/ - Photo Management

**Purpose**: Comprehensive photo and album management system.

**Key Components**:

**Models** (`models.py`):
- **Photo**:
  - Auto-generated multiple image sizes (thumbnail, small, medium, large, original)
  - EXIF metadata storage
  - WebP format support
  - Duplicate detection via perceptual hashing
  - Full-text search integration

- **PhotoAlbum**:
  - Collection of photos
  - Private/public visibility
  - Downloadable album zips
  - Cover photo selection
  - Full-text search integration

**Image Processing** (`image_utils.py`):
- EXIF data extraction (camera, lens, GPS, settings)
- Multi-resolution image generation
- WebP conversion
- Automatic optimization

**Celery Tasks** (`tasks.py`):
- Asynchronous album zip generation
- Background image processing
- Scheduled optimization tasks

### utils/ - Shared Utilities

**Purpose**: Cross-cutting functionality used across multiple apps.

**Key Components**:

**Search System** (`search.py`, `models/search.py`):
- **SearchableContent Model**: Centralized search index for blog posts, projects, books
- PostgreSQL full-text search with GIN indexes
- Trigram similarity for typo tolerance
- Weighted search fields (title: A, description: B, content: C)
- Autocomplete API with sub-100ms response time

**Notifications** (`models/notifications.py`, `tasks.py`):
- Email notification system
- SMS notifications (Twilio integration)
- Template-based notification content
- Async task processing

**Request Fingerprinting** (`models/security.py`, `middleware.py`):
- **RequestFingerprint Model**: Tracks all HTTP requests
- IP address tracking with geolocation
- User agent parsing (browser, OS, device detection)
- Suspicious request detection
- Privacy-focused (skips local/private IPs)

**Performance Monitoring** (`models/lighthouse.py`):
- **LighthouseResult Model**: Stores audit results
- Tracks 4 key metrics (Performance, Accessibility, Best Practices, SEO)
- Historical data storage with 30-day visualization
- Badge endpoint for shields.io integration
- Nightly audits via Celery Beat

**Management Commands** (`management/`):
- **rebuild_search_index**: Rebuild full-text search index
- **clear_cache**: Clear Redis cache
- **geolocate_fingerprints**: Batch IP geolocation
- **remove_local_fingerprints**: Clean up local IP records
- **run_lighthouse_audit**: Manual performance audit
- **setup_periodic_tasks**: Configure Celery Beat tasks

### feefifofunds/ - Financial Data Integration

**Purpose**: Multi-asset tracking and analysis system using a hybrid database architecture for high-performance time-series data storage.

**Key Components**:

**Models** (`models/` subdirectory - modular organization):
- **Asset** (`asset.py` in PostgreSQL): Universal model for all asset types (stocks, crypto, commodities, currencies)
  - Ticker, name, category (STOCK/CRYPTO/COMMODITY/CURRENCY)
  - Tier classification (TIER1-4 based on market cap/importance)
  - Active tracking status
- **AssetPrice** (`price.py` in QuestDB): OHLCV price records with multi-interval support
  - Open, high, low, close, volume data
  - Multiple timeframes (1m, 5m, 15m, 60m, 1440m/daily, etc.)
  - Quote currency and data source tracking
  - Trade count for each candle
  - Partitioned by day for optimal query performance

**Data Sources** (`services/data_sources/`):
- **BaseDataSource** (`base.py`): Abstract base class for all data source integrations
- **DTOs** (`dto.py`): Data Transfer Objects for standardized data handling
- **Finnhub** (`finnhub.py`): Real-time and historical data for stocks, crypto, forex
- **Massive** (`massive.py`): Historical stock/ETF data with 2-year free tier

**Ingestion System**:
- **QuestDB ILP**: High-speed ingestion via Influx Line Protocol (50K-100K records/sec)
- **Tier-based filtering**: Process data by asset importance (TIER1-4)
- **File type filtering**: OHLCV candles, trade ticks, or both
- **Auto-asset creation**: Automatically creates Asset records during ingestion
- **Idempotent operations**: Safe to re-run with ON CONFLICT DO NOTHING

**Hybrid Database Architecture**:
- **PostgreSQL**: Asset metadata, Django ORM support, relational queries
- **QuestDB**: Time-series data, optimized for high-throughput ingestion and fast aggregations
- **Benefits**: Combines Django's ORM convenience with QuestDB's time-series performance

## Design Patterns

### Template-Based Blog System

Unlike traditional CMS systems that store content in databases, this project uses HTML templates for blog posts. This approach offers several advantages:

**Benefits**:
- Version control for content (Git history)
- No database overhead for content storage
- Easy backup and migration
- Rich HTML formatting without WYSIWYG editor limitations
- Developer-friendly editing workflow

**Implementation**:
- Posts stored in `templates/blog/<category>/####_Post_Name.html`
- Metadata extracted from template blocks (title, date, description, etc.)
- Automatic discovery and parsing
- Knowledge graph builds relationships from internal links

### Knowledge Graph Visualization

The knowledge graph system automatically maps relationships between blog posts:

**Components**:
1. **Link Extraction**: Parses blog post templates to find internal links
2. **Graph Building**: Constructs nodes (posts, categories) and edges (relationships)
3. **Visualization**: D3.js force-directed graph with adaptive parameters
4. **Screenshot Generation**: Pyppeteer captures high-quality images for social sharing

**Performance Optimizations**:
- Caching with file modification tracking
- Adaptive force simulation parameters based on node count
- Velocity limiting to prevent jitter
- Grid layout for large category groups
- Maximum iteration limit (500 ticks)

### Multi-Resolution Image System

Photos automatically generate 5 optimized versions:

1. **Thumbnail**: 150x150px (square crop)
2. **Small**: 400px width
3. **Medium**: 800px width
4. **Large**: 1200px width
5. **Original**: Preserved as uploaded

**Benefits**:
- Responsive image delivery
- Bandwidth optimization
- Automatic WebP conversion
- S3 storage integration
- CDN-friendly structure

### Model Organization Patterns

This project uses two approaches for organizing Django models:

**Single File Pattern** (`models.py`):
- Used in: `accounts`, `blog`, `photos` apps
- Best for: Apps with few models (1-5) that are closely related
- Benefits: Simple, easy to navigate, Django default pattern
- Example: `blog/models.py` contains BlogComment, CommentVote, KnowledgeGraphScreenshot

**Modular Pattern** (`models/` directory):
- Used in: `feefifofunds`, `utils` apps
- Best for: Apps with many models or clear domain boundaries
- Benefits: Better organization, easier to maintain, reduces merge conflicts
- Structure:
  ```
  models/
  ├── __init__.py     # Import all models for Django discovery
  ├── asset.py        # Asset model
  ├── price.py        # AssetPrice model
  └── trade.py        # Trade model
  ```
- Important: `__init__.py` must import all models for Django to discover them

**When to Use Which Pattern**:
- Start with single file for simplicity
- Migrate to modular when:
  - Models exceed 500-1000 lines
  - Clear domain boundaries emerge
  - Multiple developers work on models
  - Models have distinct responsibilities

**Migration Process**:
1. Create `models/` directory
2. Move models to separate files by domain
3. Import all models in `__init__.py`
4. Update any direct imports in other files
5. Run tests to ensure models are discovered

## Technology Stack

### Backend
- **Django 5.2.8**: Web framework
- **Python 3.13**: Programming language
- **PostgreSQL 15+**: Database with full-text search extensions
- **Celery**: Async task queue
- **Redis**: Caching and message broker

### Frontend
- **D3.js**: Knowledge graph visualization
- **Vanilla JavaScript**: Lightweight interactions
- **PostCSS**: CSS processing and optimization
- **Prism.js**: Syntax highlighting for code blocks

### Infrastructure
- **Docker**: Containerization
- **Gunicorn**: WSGI server
- **WhiteNoise**: Static file serving (CSS, JS, fonts) from container
- **AWS S3**: Media storage (photos, uploads)
- **CloudFront**: Optional CDN for media files
- **GitHub Actions**: CI/CD pipeline for testing and deployment
- **GitHub Container Registry**: Docker image distribution
- **CodeQL**: Security vulnerability scanning

### Development Tools
- **Pyppeteer**: Browser automation for screenshots
- **Ruff**: Python linting and formatting
- **Prettier**: CSS formatting
- **pre-commit**: Git hooks for code quality
- **coverage.py**: Test coverage reporting

## Data Flow

### Request Lifecycle

1. **Request Arrival**:
   - Gunicorn receives HTTP request
   - Django processes through middleware stack
   - RequestFingerprintMiddleware tracks request details

2. **View Processing**:
   - URL routing to appropriate view
   - Database queries (optimized with select_related/prefetch_related)
   - Cache lookups for expensive operations

3. **Template Rendering**:
   - Context processors add global data
   - Template rendered with context
   - Static files served via WhiteNoise from container

4. **Response**:
   - HTML returned to client
   - Request fingerprint saved asynchronously
   - Page visit tracked if applicable

### Background Task Flow

1. **Task Triggering**:
   - Periodic tasks via Celery Beat
   - Manual tasks via management commands
   - Event-driven tasks from user actions

2. **Celery Processing**:
   - Task picked up by Celery worker
   - Redis message broker coordinates
   - Task executes (e.g., generate album zip)

3. **Result Storage**:
   - Task result stored in Redis
   - Database updated if needed
   - Cache invalidated if applicable

4. **Monitoring**:
   - Flower dashboard for task monitoring
   - Logging for debugging
   - Health checks for system status

## CI/CD Pipeline

### Continuous Integration
The project uses GitHub Actions for automated testing and quality assurance:

1. **Build Phase**:
   - Docker images built with multi-stage Dockerfile
   - Dependencies cached for faster builds
   - Images pushed to GitHub Container Registry

2. **Test Phase** (6 parallel jobs):
   - Django test suite split across parallel workers
   - PostgreSQL, Redis, and QuestDB services for each test job
   - Dynamic test balancing based on historical timing data

3. **Quality Checks**:
   - **Linting**: Ruff for Python code style and formatting
   - **Type Checking**: MyPy for static type analysis
   - **Security**: CodeQL scanning for vulnerability detection
   - **Pre-commit**: Hooks for consistent code quality

### Continuous Deployment
- **Image Distribution**: GitHub Container Registry for production images
- **Tagging Strategy**: Images tagged with commit SHA and 'latest' for main branch
- **Fallback Mechanism**: Artifact-based distribution for fork PRs

### Performance Optimizations
The CI/CD pipeline has been optimized for speed and cost efficiency:
- **44% runtime reduction**: From ~45 minutes to ~25-30 minutes
- **Parallel execution**: 6 concurrent test jobs
- **Smart caching**: BuildKit cache mounts and inline caching
- **Annual savings**: $1,200 in compute costs

For detailed CI/CD documentation, see [CI/CD Pipeline](features/ci-cd.md).

## Security Considerations

### Authentication & Authorization
- Custom user model with flexible authentication
- Registration disabled by default
- django-allauth for social auth support
- Session-based authentication
- CSRF protection enabled

### Request Security
- Request fingerprinting for suspicious activity detection
- IP-based rate limiting (to be implemented)
- User agent validation
- Automatic bot detection

### Data Protection
- Environment-based configuration (no secrets in code)
- HTTPS enforced in production
- Secure cookie settings
- SQL injection protection (Django ORM)
- XSS protection (template auto-escaping)

### Content Security
- CSP headers configured
- HSTS enabled
- Clickjacking protection
- Secure static file serving

## Performance Optimizations

### Database
- Connection pooling
- Query optimization with ORM methods
- GIN indexes for full-text search
- Trigram indexes for similarity matching
- Selective field loading

### Caching Strategy
- Redis-backed caching
- Multi-level cache (template, view, query)
- Cache invalidation on updates
- CDN caching for static assets

**Cache Timeouts**:
- Graph data: 20 minutes
- Blog posts: 1 hour
- Projects/books: 24 hours
- Search results: 5 minutes

### Static Files
- Brotli and gzip compression
- Hashed filenames for cache busting
- CSS/JS minification
- Image optimization
- CDN distribution

### Async Processing
- Celery for long-running tasks
- Background image processing
- Periodic task scheduling
- Non-blocking operations

## Deployment Architecture

### Production Setup

```
[User] → [CloudFront CDN] → [Load Balancer]
                                    ↓
                          [Docker Container: Web]
                          [Gunicorn + Django]
                                    ↓
        ┌──────────────────────────┼──────────────────────────┐
        ↓                          ↓                          ↓
  [PostgreSQL]                [Redis]                    [S3 Bucket]
   (Database)              (Cache/Queue)              (Media/Static)
        ↓
  [Celery Workers]
   (Background Tasks)
```

### Health Monitoring
- Health check endpoint (`/health/`)
- Database connectivity check
- Cache connectivity check (non-critical)
- Uptime monitoring integration

### Scaling Considerations
- Stateless application (session in Redis)
- Horizontal scaling ready
- Database read replicas possible
- CDN for static content distribution
- Celery workers can scale independently

## Related Documentation

### Core Documentation
- [Testing Guide](testing.md) - Test framework, factories, Docker test environment
- [Deployment Guide](deployment.md) - Production deployment with Docker
- [Management Commands](commands.md) - Complete command reference
- [API Reference](api.md) - REST API endpoints
- [Maintenance Guide](maintenance.md) - Operations, monitoring, troubleshooting

### Cross-Cutting Features
- [CI/CD Pipeline](features/ci-cd.md) - Continuous integration and deployment
- [Search System](features/search.md) - PostgreSQL FTS architecture (used by blog, photos)
- [Performance Monitoring](features/performance-monitoring.md) - Lighthouse audit system
- [Request Tracking](features/request-tracking.md) - Security and analytics

### App-Specific Documentation
- [Blog App](apps/blog/) - Template-based blog system with knowledge graph
- [Photos App](apps/photos/) - Photo management with multi-resolution images
- [FeeFiFoFunds App](apps/feefifofunds/) - Multi-asset tracking with hybrid database
- [Omas Coffee App](apps/omas/) - German coffee cart website with brand guidelines

### Documentation Index
- [Documentation Index](README.md) - Complete documentation map
