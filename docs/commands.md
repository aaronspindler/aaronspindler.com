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
- Playwright installed: `playwright install chromium`
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
1. **Phase 1**: Optimize each CSS file individually
   - Production: Full optimization and minification
   - Development: Copy without optimization
   - Output: `.opt.css` temporary files
2. **Phase 2**: Combine and process
   - Combine all `.opt.css` files
   - Run PostCSS with autoprefixer
   - Run PurgeCSS to remove unused CSS (production only)
   - Create versioned filename with hash
   - Generate gzip and brotli compressed versions
3. **Cleanup**: Remove temporary files

**CSS Source Files**:
- Stored in `static/css/` (formatted, developer-friendly)
- Never minified in git (pre-commit hooks enforce this)
- Build output in `static/css/` (gitignored)

**Output Files**:
- `combined.min.{hash}.css`: Minified, combined CSS
- `combined.min.{hash}.css.gz`: Gzip compressed
- `combined.min.{hash}.css.br`: Brotli compressed

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
