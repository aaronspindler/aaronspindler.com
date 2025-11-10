# Management Commands Reference

## Overview

Comprehensive reference for all custom Django management commands in the project, organized by functionality.

## Blog Management

### create_blog_post

Create a new blog post with automatic numbering and template generation.

**Usage**:
```bash
python manage.py create_blog_post --title "Your Post Title" --category tech
```

**Options**:
- `--title` (required): Title of the blog post
- `--category` (required): Category (personal, projects, reviews, tech)

**Example**:
```bash
# Create tech blog post
python manage.py create_blog_post --title "Django Full-Text Search Guide" --category tech

# Create personal blog post
python manage.py create_blog_post --title "Weekend Adventures" --category personal

# Create project showcase
python manage.py create_blog_post --title "Building a Knowledge Graph" --category projects

# Create product review
python manage.py create_blog_post --title "Book Review: Clean Code" --category reviews
```

**Output**:
- Creates file at `templates/blog/<category>/####_Post_Title.html`
- Automatically assigns next available blog number
- Includes template with metadata blocks and formatting examples
- Provides code block examples for syntax highlighting

**Next Steps After Creation**:
1. Edit the generated template file
2. Add your content
3. Rebuild knowledge graph: `python manage.py rebuild_knowledge_graph`
4. Update search index: `python manage.py rebuild_search_index --content-type blog`

---

### rebuild_knowledge_graph

Rebuild the knowledge graph cache by parsing all blog posts and extracting relationships.

**Usage**:
```bash
python manage.py rebuild_knowledge_graph
```

**Options**:
- `--force`: Force rebuild even if no changes detected
- `--test-api`: Test the API endpoint after rebuild

**Examples**:
```bash
# Standard rebuild
python manage.py rebuild_knowledge_graph

# Force rebuild (ignore modification times)
python manage.py rebuild_knowledge_graph --force

# Rebuild and test API
python manage.py rebuild_knowledge_graph --test-api
```

**When to Run**:
- After adding new blog posts
- After modifying blog post content or links
- After template changes
- If graph appears out of sync

**What It Does**:
1. Scans all blog post templates
2. Extracts internal links between posts
3. Builds node and edge data structures
4. Stores graph data in cache (20-minute timeout)
5. Updates file modification tracking

---

### generate_knowledge_graph_screenshot

Generate high-quality screenshots of the knowledge graph for social sharing.

**Usage**:
```bash
python manage.py generate_knowledge_graph_screenshot
```

**Options**:
- `--width`: Screenshot width in pixels (default: 1920)
- `--height`: Screenshot height in pixels (default: 1080)
- `--device-scale-factor`: Device pixel ratio (default: 2.0)
- `--quality`: JPEG quality 1-100 (default: 90)
- `--transparent`: Use transparent background
- `--url`: URL to screenshot (default: http://localhost:8000)

**Examples**:
```bash
# Default settings (1920x1080, 2x DPI)
python manage.py generate_knowledge_graph_screenshot

# High-resolution screenshot (2400x1600, 2x DPI, max quality)
python manage.py generate_knowledge_graph_screenshot \
  --width 2400 \
  --height 1600 \
  --device-scale-factor 2.0 \
  --quality 100

# Transparent background
python manage.py generate_knowledge_graph_screenshot --transparent

# Screenshot production site
python manage.py generate_knowledge_graph_screenshot \
  --url https://aaronspindler.com
```

**Requirements**:
- Pyppeteer installed with Chromium: `pip install pyppeteer`
- Django server running (for localhost screenshots)

**Automated Generation**:
- Runs daily at 4 AM UTC via Celery Beat
- Screenshots production site automatically
- Stores in database with hash-based caching

---

## Static File Management

### collectstatic_optimize

Collect static files with automatic image optimization and compression.

**Usage**:
```bash
python manage.py collectstatic_optimize
```

**What It Does**:
1. Runs standard Django collectstatic
2. Optimizes images (JPEG, PNG, WebP)
3. Creates gzip compressed versions
4. Creates brotli compressed versions (if available)
5. Uploads to S3 (if configured)

**Optimizations**:
- **JPEG**: Optimized quality, progressive encoding
- **PNG**: Lossless optimization
- **WebP**: Modern format generation
- **Compression**: Gzip and Brotli for faster serving

**Production Build**:
```bash
# Complete static file pipeline
python manage.py build_css
python manage.py optimize_js
python manage.py collectstatic_optimize
```

---

### build_css

Build and optimize CSS with PostCSS, PurgeCSS, and minification.

**Usage**:
```bash
python manage.py build_css
```

**Options**:
- `--dev`: Development mode (skip purging, keep source maps)

**Examples**:
```bash
# Production build (full optimization)
python manage.py build_css

# Development build (faster, unminified)
python manage.py build_css --dev
```

**Build Process**:
1. **Combine**: Concatenate all CSS files in load order → `combined.css`
2. **Minify**: Run PostCSS with cssnano for minification → `combined.processed.css`
3. **Purge**: Run PurgeCSS to remove unused CSS → `combined.purged.css` (production only)
4. **Output**: Create final `combined.min.css`
5. **Compress**: Generate Gzip (`.gz`) and Brotli (`.br`) compressed versions
6. **Cleanup**: Remove temporary build files

**CSS Source Files**:
- Stored in `static/css/` (formatted, developer-friendly)
- Never minified in git (pre-commit hooks enforce this)
- Build output: `combined.min.css` in `static/css/` (gitignored)

**Output Files**:
- `combined.min.css`: Non-versioned file for development
- `combined.min.css.gz`: Gzip compressed version
- `combined.min.css.br`: Brotli compressed version

**Versioning**:
- Content-hashed versions automatically created by WhiteNoise during `collectstatic`
- Example: `combined.min.css` → `combined.min.263d67867382.css`
- Manifest file maps non-versioned to versioned filenames
- Cache headers set to 1 year with `immutable` directive

---

### optimize_js

Optimize and minify JavaScript files with Terser.

**Usage**:
```bash
python manage.py optimize_js
```

**Options**:
- `--skip-minify`: Skip minification
- `--skip-compress`: Skip gzip/brotli compression

**Examples**:
```bash
# Full optimization
python manage.py optimize_js

# Skip minification (debugging)
python manage.py optimize_js --skip-minify

# Skip compression
python manage.py optimize_js --skip-compress
```

**What It Does**:
1. Minifies JavaScript with Terser
2. Removes console.log statements (production)
3. Creates source maps
4. Generates gzip compressed versions
5. Generates brotli compressed versions

---

### clear_cache

Clear all cache keys from Redis.

**Usage**:
```bash
python manage.py clear_cache
```

**What It Clears**:
- Knowledge graph cache
- Blog post cache
- Page cache
- Search cache
- Template cache
- View cache

**When to Use**:
- After major content updates
- After template changes
- When debugging cache issues
- Before deployment

---

## Photo Management

### generate_album_zips

Generate downloadable zip files for photo albums.

**Usage**:
```bash
python manage.py generate_album_zips
```

**Options**:
- `--all`: Generate for all albums with downloads enabled
- `--album-id ID`: Generate for specific album by ID
- `--album-slug SLUG`: Generate for specific album by slug
- `--async`: Use Celery for background processing

**Examples**:
```bash
# Generate for all albums with downloads enabled
python manage.py generate_album_zips --all

# Generate for specific album by ID
python manage.py generate_album_zips --album-id 1

# Generate for specific album by slug
python manage.py generate_album_zips --album-slug "california-trip-2025"

# Use Celery for async processing
python manage.py generate_album_zips --album-id 1 --async
```

**What It Does**:
1. Collects all photos in album
2. Downloads images from S3 (if applicable)
3. Creates zip file with original images
4. Uploads zip to storage
5. Updates album zip_file and zip_updated_at fields

**Requirements**:
- Album must have `download_enabled=True`
- Photos must exist in storage

---

## Search Index Management

### rebuild_search_index

Rebuild PostgreSQL full-text search index for all searchable content.

**Usage**:
```bash
python manage.py rebuild_search_index
```

**Options**:
- `--clear`: Clear existing index before rebuilding
- `--content-type TYPE`: Rebuild specific type (blog, photos, albums, books, projects, all)

**Examples**:
```bash
# Rebuild all content types
python manage.py rebuild_search_index

# Clear and rebuild entire index
python manage.py rebuild_search_index --clear

# Rebuild only blog posts
python manage.py rebuild_search_index --content-type blog

# Rebuild only photos
python manage.py rebuild_search_index --content-type photos

# Rebuild only photo albums
python manage.py rebuild_search_index --content-type albums

# Rebuild only books
python manage.py rebuild_search_index --content-type books

# Rebuild only projects
python manage.py rebuild_search_index --content-type projects

# Clear and rebuild specific type
python manage.py rebuild_search_index --clear --content-type blog
```

**What It Does**:
1. Parses content based on type:
   - **Blog**: Reads templates, extracts title/description/content
   - **Photos**: Indexes title, description, location, camera/lens
   - **Albums**: Indexes title and description
   - **Books**: Indexes from utility functions
   - **Projects**: Indexes from utility functions
2. Creates/updates SearchableContent records
3. Updates PostgreSQL search vectors
4. Applies field weights (Title: A, Description: B, Content: C)

**When to Run**:
- After adding new blog posts
- After modifying blog post content
- After adding photos or albums
- After updating project or book data
- After initial setup

---

## Performance Monitoring

### run_lighthouse_audit

Run Google Lighthouse performance audit and store results.

**Usage**:
```bash
python manage.py run_lighthouse_audit
```

**Options**:
- `--url URL`: URL to audit (default: site URL from settings)

**Examples**:
```bash
# Audit default URL
python manage.py run_lighthouse_audit

# Audit specific URL
python manage.py run_lighthouse_audit --url https://example.com

# Audit multiple pages
python manage.py run_lighthouse_audit --url https://example.com/
python manage.py run_lighthouse_audit --url https://example.com/blog/
python manage.py run_lighthouse_audit --url https://example.com/about/
```

**What It Does**:
1. Runs Lighthouse CLI via subprocess
2. Captures JSON report
3. Extracts 4 key scores:
   - Performance
   - Accessibility
   - Best Practices
   - SEO
4. Stores LighthouseResult in database
5. Displays results summary

**Requirements**:
- Lighthouse installed: `npm install -g lighthouse`
- Chromium/Chrome available
- Target URL accessible

**Automated Audits**:
- Runs nightly at 2 AM UTC via Celery Beat
- Results visible at `/lighthouse/history/`
- Badge endpoint: `/api/lighthouse/badge/`

---

### setup_periodic_tasks

Configure Celery Beat periodic tasks for automated operations.

**Usage**:
```bash
python manage.py setup_periodic_tasks
```

**What It Configures**:
1. **Daily Lighthouse Audit** - 2 AM UTC
2. **Daily Sitemap Rebuild** - 3 AM UTC
3. **Daily Knowledge Graph Screenshot** - 4 AM UTC
4. **Knowledge Graph Cache Rebuild** - Every 6 hours

**When to Run**:
- After initial deployment
- After Celery Beat configuration changes
- To reset periodic task schedules

---

## Security & Request Tracking

### geolocate_fingerprints

Batch process IP addresses to add geolocation data to request fingerprints.

**Usage**:
```bash
python manage.py geolocate_fingerprints
```

**Options**:
- `--limit N`: Maximum records to process
- `--force`: Re-geolocate all records (including those with existing geo_data)
- `--batch-size N`: IPs per batch request (default: 100, max: 100)
- `--yes`: Skip confirmation prompt (for automated runs)

**Examples**:
```bash
# Interactive mode (shows stats, waits for Enter)
python manage.py geolocate_fingerprints

# Automated mode (skip confirmation)
python manage.py geolocate_fingerprints --yes

# Limit to 100 records
python manage.py geolocate_fingerprints --limit 100

# Re-geolocate all records
python manage.py geolocate_fingerprints --force

# Custom batch size
python manage.py geolocate_fingerprints --batch-size 50

# Combined options
python manage.py geolocate_fingerprints --yes --limit 1000
```

**How It Works**:
1. Queries RequestFingerprint records without geo_data
2. Extracts unique IP addresses
3. Filters out local/private IPs
4. Shows statistics (total records vs unique IPs)
5. Waits for Enter key (unless `--yes` specified)
6. Batches IPs (100 per batch)
7. Calls ip-api.com batch endpoint
8. Updates all records with matching IP
9. Respects rate limits (15 requests/minute)

**API Details**:
- **Service**: ip-api.com (free tier)
- **Rate Limit**: 15 batch requests/minute
- **Batch Size**: Up to 100 IPs per request
- **Data Returned**: City, country, coordinates, timezone, ISP, organization

**Privacy**:
- Automatically skips local/private IPs
- No geolocation during request processing (batch only)
- No personally identifiable information stored

**Automation**:
```bash
# Cron job (daily at 3 AM)
0 3 * * * cd /path/to/project && /path/to/venv/bin/python manage.py geolocate_fingerprints --yes --limit 1000

# Or via Celery Beat
from django_celery_beat.models import PeriodicTask, CrontabSchedule
schedule, _ = CrontabSchedule.objects.get_or_create(minute='0', hour='3')
PeriodicTask.objects.get_or_create(
    name='Daily IP Geolocation',
    task='utils.tasks.geolocate_fingerprints_task',
    crontab=schedule,
)
```

---

### remove_local_fingerprints

Remove request fingerprints from local/private IP addresses.

**Usage**:
```bash
python manage.py remove_local_fingerprints
```

**Options**:
- `--dry-run`: Preview which records would be deleted without deleting
- `--limit N`: Limit number of records to delete

**Examples**:
```bash
# Preview deletions (dry-run)
python manage.py remove_local_fingerprints --dry-run

# Delete local IP records
python manage.py remove_local_fingerprints

# Limit deletions
python manage.py remove_local_fingerprints --limit 100
```

**What It Removes**:
- Local IPs: `127.0.0.1`, `::1`, `localhost`
- Private ranges:
  - `10.0.0.0/8`
  - `172.16.0.0/12`
  - `192.168.0.0/16`
- Link-local: `169.254.0.0/16`, `fe80::/10`

**Use Cases**:
- One-time cleanup after deploying local IP filtering
- Remove development/testing records from production
- Clean up historical data before middleware was updated

**Note**: Modern middleware automatically skips tracking local IPs, so this is mainly for historical cleanup.

---

## FeeFiFoFunds Data Management

### ingest_sequential

**Fast sequential ingestion of Kraken OHLCVT files (both OHLCV and trade data).**

**Usage**:
```bash
python manage.py ingest_sequential [--tier TIER] [--file-type TYPE]
```

**Options**:
- `--tier`: Asset tier to ingest (TIER1/TIER2/TIER3/TIER4/ALL). Default: ALL
- `--file-type`: Type of files to ingest (ohlcv/trade/both). Default: both
- `--yes`, `-y`: Skip confirmation prompts
- `--database`: Database to use (default: timescaledb)
- `--data-dir`: Custom data directory (for testing)
- `--stop-on-error`: Stop processing on first error (default: continue)

**Examples**:
```bash
# Ingest only TIER1 assets (BTC, ETH, etc. - fastest)
python manage.py ingest_sequential --tier TIER1

# Ingest only OHLCV (candle) data
python manage.py ingest_sequential --file-type ohlcv

# Ingest only trade (tick) data
python manage.py ingest_sequential --file-type trade

# Ingest TIER1 OHLCV data only
python manage.py ingest_sequential --tier TIER1 --file-type ohlcv

# Ingest all assets and all file types (default)
python manage.py ingest_sequential

# Automated run (skip prompts)
python manage.py ingest_sequential --tier TIER1 --yes

# Stop on first error
python manage.py ingest_sequential --stop-on-error
```

**Key Features**:
- **PostgreSQL COPY operations**: Direct database bulk loading for maximum speed
- **Flexible filtering**: Filter by asset tier (TIER1-4) and/or file type (ohlcv/trade)
- **Idempotent**: Uses ON CONFLICT DO NOTHING, safe to re-run
- **Auto file management**: Moves completed files to `ingested/` directory
- **Empty file cleanup**: Deletes invalid/empty files automatically
- **Rich progress display**: Real-time stats with progress tracking
- **Handles both OHLCV and trade files**: Automatically detects file type
- **Smart header detection**: Handles files with or without headers
- **Float timestamp support**: Handles microsecond precision timestamps

**Performance**:
- TIER1 assets: ~10-15 seconds
- TIER2 assets: ~30-60 seconds
- Full dataset: ~1.5-2 hours
- Speed: ~50K-100K records/second per file

**Error Handling**:
```bash
# By default, continues processing on errors
python manage.py ingest_sequential

# To stop on first error
python manage.py ingest_sequential --stop-on-error
```

**When to Use**:
- **Preferred method** for all Kraken data ingestion
- Handles both OHLCV candle data and individual trade data
- Simple, reliable sequential processing

---

### backload_massive

Backload historical price data from Massive.com (formerly Polygon.io) for stocks and ETFs. Free tier provides 2 years (730 days) of historical data.

**Usage**:
```bash
python manage.py backload_massive <ticker> [<ticker> ...] [options]
```

**Options**:
- `tickers`: One or more ticker symbols (e.g., SPY, QQQ, VOO)
- `--all`: Backload data for all existing funds in database
- `--days <N>`: Number of days to fetch (default: 730, max: 730)
- `--create-fund`: Create fund if it doesn't exist
- `--skip-existing`: Skip performance data that already exists

**Examples**:
```bash
# Backload 2 years of data for SPY
python manage.py backload_massive SPY --days 730

# Backload multiple tickers with fund creation
python manage.py backload_massive SPY QQQ VOO --days 365 --create-fund

# Backload all existing funds
python manage.py backload_massive --all --days 730

# Backload without overwriting existing data
python manage.py backload_massive AAPL --skip-existing
```

**When to Run**:
- Initial setup for new funds
- Historical data recovery
- After adding new funds to track
- To fill gaps in existing data

**What It Does**:
1. Validates ticker symbols format
2. Fetches fund information (if --create-fund)
3. Retrieves historical OHLCV data from Massive.com
4. Stores data in FundPerformance model
5. Updates fund current/previous values
6. Creates DataSync records for tracking
7. Wraps all operations in transactions for consistency

**Performance**:
- Free tier: ~100 requests/second
- No hard daily limit
- 2 years of historical data included

**Requirements**:
- `MASSIVE_API_KEY` environment variable must be set
- Get free API key from: https://massive.com

---

### update_massive_daily

Fetch daily price updates from Massive.com for active funds. Should be run daily via cron or Celery Beat.

**Usage**:
```bash
python manage.py update_massive_daily [<ticker> ...] [options]
```

**Options**:
- `tickers`: Optional specific ticker symbols (default: all active funds)
- `--days <N>`: Number of days to fetch (default: 1)
- `--force`: Force update even if data exists for today

**Examples**:
```bash
# Update all active funds with today's data
python manage.py update_massive_daily

# Update specific tickers
python manage.py update_massive_daily SPY QQQ

# Catch up after weekend (fetch last 5 days)
python manage.py update_massive_daily --days 5

# Force update even if data exists
python manage.py update_massive_daily --force
```

**When to Run**:
- Daily (automated via cron/Celery Beat recommended)
- After weekends/holidays (use --days to catch up)
- When fund prices need refreshing

**What It Does**:
1. Checks each fund for up-to-date data
2. Skips funds that already have today's data (unless --force)
3. Fetches recent price data from Massive.com
4. Updates FundPerformance records
5. Updates fund current/previous values
6. Creates DataSync records
7. All operations in transactions

**Automation**:
```bash
# Add to crontab for daily 6 PM updates
0 18 * * 1-5 /path/to/venv/bin/python /path/to/manage.py update_massive_daily

# Or configure Celery Beat task
from celery import shared_task
@shared_task
def update_fund_prices():
    call_command('update_massive_daily')
```

**Requirements**:
- `MASSIVE_API_KEY` environment variable must be set
- Free tier provides end-of-day data only

**Recommended Workflow**:
1. Use `backload_massive` for initial 2-year data load
2. Use `update_massive_daily` for ongoing daily updates
3. Consider switching to Finnhub for real-time data after backload

---

## Common Workflows

### Complete Production Build

```bash
# 1. Build and optimize CSS
python manage.py build_css

# 2. Optimize JavaScript
python manage.py optimize_js

# 3. Collect and optimize static files
python manage.py collectstatic_optimize

# 4. Rebuild knowledge graph
python manage.py rebuild_knowledge_graph

# 5. Generate knowledge graph screenshot
python manage.py generate_knowledge_graph_screenshot \
  --width 2400 \
  --height 1600 \
  --quality 100

# 6. Rebuild search index
python manage.py rebuild_search_index

# 7. Clear cache
python manage.py clear_cache
```

Or use the Makefile:
```bash
make static  # Runs CSS build, JS optimization, collectstatic, and pre-commit
```

---

### Development Workflow

```bash
# 1. Development CSS build (faster, unminified)
python manage.py build_css --dev

# 2. Run development server
python manage.py runserver

# 3. After adding blog post
python manage.py rebuild_knowledge_graph
python manage.py rebuild_search_index --content-type blog
```

---

### Post-Deployment Tasks

```bash
# 1. Setup periodic tasks
python manage.py setup_periodic_tasks

# 2. Run initial audits
python manage.py run_lighthouse_audit

# 3. Geolocate existing fingerprints
python manage.py geolocate_fingerprints --yes

# 4. Generate album zips
python manage.py generate_album_zips --all
```

---

### Pre-Commit Checks

```bash
# Run all pre-commit hooks
pre-commit run --all-files

# Run specific hook
pre-commit run ruff
pre-commit run ruff-format
pre-commit run prettier

# Update hooks to latest versions
pre-commit autoupdate
```

---

## Troubleshooting

### Command Not Found

```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Verify Django can find the command
python manage.py help

# Check INSTALLED_APPS includes the app with the command
```

### Permission Errors

```bash
# Check file permissions
ls -la manage.py

# Make manage.py executable
chmod +x manage.py

# Check directory permissions for static files
ls -la static/
```

### Database Errors

```bash
# Ensure migrations are up to date
python manage.py migrate

# Check database connection
python manage.py shell
>>> from django.db import connection
>>> connection.ensure_connection()
```

### Cache Errors

```bash
# Check Redis is running
redis-cli ping

# Clear cache if corrupted
python manage.py clear_cache

# Restart Redis
sudo systemctl restart redis
```

## Related Documentation

- [Features](features/) - Feature-specific documentation
- [Testing](testing.md) - Testing commands and workflow
- [Deployment](deployment.md) - Production command usage
- [Maintenance](maintenance.md) - Maintenance commands and schedules
