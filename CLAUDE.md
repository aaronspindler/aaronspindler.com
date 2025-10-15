# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Django-based personal website and blog (aaronspindler.com) with advanced features including knowledge graph visualization, photo management, and analytics tracking.

## Common Development Commands

### Local Development
```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Collect static files (with optimization)
python manage.py collectstatic_optimize

# Run development server
python manage.py runserver

# Create superuser for admin access
python manage.py createsuperuser
```

### Testing
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

**IMPORTANT**: Do not write new tests for code in this repository unless explicitly requested.

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

**IMPORTANT**: Whenever CSS or JS files are modified, you MUST run `make static` to rebuild and apply the changes. This command handles all necessary build steps to optimize and deploy static assets.

**CSS Build Process and Workflow**:
- **Source files** in `static/css/` (like `base.css`, `blog.css`, etc.) are **developer-friendly and formatted** in git
  - These files have proper line breaks, indentation, and whitespace for easy editing
  - Never commit minified/single-line CSS source files to git
  - Pre-commit hooks automatically format CSS with Prettier and prevent minified sources
- **Build process** (`python manage.py build_css`):
  - Phase 1: Optimizes each source file → creates temporary `.opt.css` versions
    - In dev mode (`--dev`): `.opt.css` files are just copies (no optimization)
    - In production: `.opt.css` files are fully optimized and minified
  - Phase 2: Combines all `.opt.css` files → runs PostCSS/PurgeCSS → creates `combined.min.css`
  - Final file is pushed to S3 via `collectstatic_optimize`
  - Temporary files (`.opt.css`, `combined.css`, etc.) are auto-cleaned and gitignored
- **Important**: Source CSS files are **never modified** by the build process - they stay formatted in git

### Knowledge Graph Commands
```bash
# Rebuild knowledge graph cache
python manage.py rebuild_knowledge_graph

# Generate knowledge graph screenshot (high-quality)
python manage.py generate_knowledge_graph_screenshot --width 2400 --height 1600 --device-scale-factor 2.0 --quality 100 --transparent
```

### Photo Management
```bash
# Generate photo album zips
python manage.py generate_album_zips
```

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
- Run periodically (e.g., via cron or Celery Beat) to batch process new records
- Geolocation is NOT performed during request processing to avoid latency

**Note**: The `remove_local_fingerprints` command removes historical local/private IP records:
- Local IPs: 127.0.0.1, ::1, localhost
- Private ranges: 10.x.x.x, 192.168.x.x, 172.16-31.x.x
- Middleware now automatically skips tracking local requests
- Use `--dry-run` to preview deletions before committing
- Useful for one-time cleanup after deploying local IP filtering

## Architecture Overview

### Django Apps Structure
- **config/**: Main Django configuration
  - `settings.py`: Environment-based settings using django-environ
  - `urls.py`: Main URL routing
  - `storage_backends.py`: S3 storage configuration
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

### Key Technical Features

1. **Knowledge Graph System** (`blog/knowledge_graph.py`)
   - Builds interactive graph from blog post metadata
   - Uses Playwright for server-side screenshot generation
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
   - WhiteNoise for serving in production

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
- **Docker**: Multi-stage build with Playwright for screenshot generation
- **Database**: PostgreSQL with psycopg3
- **Storage**: AWS S3 support via django-storages
- **Server**: Gunicorn with 8 workers
- **Cache**: Redis for caching and sessions
- **Task Queue**: Celery with Redis broker

### Environment Variables
Required environment variables (use django-environ):
- `DATABASE_URL`: PostgreSQL connection string
- `SECRET_KEY`: Django secret key
- `DEBUG`: Debug mode flag
- AWS credentials (required for production with S3 storage; optional for local development):
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

- **Pre-commit Hooks**: Local code quality enforcement
  - Ruff linter with auto-fixing for Python code
  - Ruff formatter (compatible with Black) for Python code
  - Prettier formatter for CSS files (source files only)
  - CSS format checker to prevent minified source files from being committed
  - File quality checks (trailing whitespace, end-of-file, YAML validation, etc.)
  - Setup: Run `pre-commit install` after cloning the repository

### Performance Optimizations
- Graph data caching with 20-minute timeout
- File modification time tracking for cache invalidation
- Multi-resolution image generation (thumbnail, small, medium, large)
- Static file compression and optimization
- Database query optimization with select/prefetch related
- PostgreSQL full-text search with GIN indexes
- Trigram indexes for typo-tolerant search
