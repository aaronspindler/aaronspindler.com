# Management Commands Reference

Comprehensive reference for all Django management commands in the project.

## Quick Reference

| Command | Category | Description |
|---------|----------|-------------|
| `rebuild_knowledge_graph` | Blog | Rebuild knowledge graph cache |
| `generate_knowledge_graph_screenshot` | Blog | Generate graph screenshots |
| `create_blog_post` | Blog | Create new blog post template |
| `rebuild_search_index` | Search | Rebuild full-text search index |
| `clear_cache` | Cache | Clear all Redis caches |
| `build_css` | Static | Build and optimize CSS |
| `optimize_js` | Static | Minify JavaScript |
| `collectstatic_optimize` | Static | Collect and optimize static files |
| `run_lighthouse_audit` | Monitoring | Run performance audit |
| `geolocate_fingerprints` | Security | Geolocate IP addresses |
| `remove_local_fingerprints` | Security | Remove local IP records |
| `ingest_sequential` | FeeFiFoFunds | Fast Kraken OHLCV ingestion |
| `backfill_prices` | FeeFiFoFunds | Backfill historical prices |
| `load_prices` | FeeFiFoFunds | Load prices from APIs |

## Most Frequently Used Commands

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

# FeeFiFoFunds
python manage.py ingest_sequential --tier TIER1 --yes
python manage.py backfill_prices --source massive --days 365 --all --grouped

# Static Assets
make static  # Or: python manage.py build_css && python manage.py optimize_js
```

---

## Blog Commands

### create_blog_post

Create a new blog post with automatic numbering and template generation.

**Usage**:
```bash
python manage.py create_blog_post --title "Your Post Title" --category tech
```

**Options**:
- `--title` (required): Title of the blog post
- `--category` (required): Category (personal, projects, reviews, tech)

**Examples**:
```bash
# Create tech blog post
python manage.py create_blog_post --title "Django Full-Text Search Guide" --category tech

# Create personal blog post
python manage.py create_blog_post --title "Weekend Adventures" --category personal
```

**Output**:
- Creates file at `templates/blog/<category>/####_Post_Title.html`
- Automatically assigns next available blog number
- Includes template with metadata blocks

### rebuild_knowledge_graph

Rebuild the knowledge graph cache by parsing all blog posts and extracting relationships.

**Usage**:
```bash
python manage.py rebuild_knowledge_graph
```

**Options**:
- `--force`: Force rebuild even if no changes detected
- `--test-api`: Test the API endpoint after rebuild

**What It Does**:
1. Scans all blog post templates
2. Extracts internal links between posts
3. Builds node and edge data structures
4. Stores graph data in cache (20-minute timeout)

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
# High-resolution screenshot
python manage.py generate_knowledge_graph_screenshot \
  --width 2400 --height 1600 --quality 100

# Transparent background
python manage.py generate_knowledge_graph_screenshot --transparent
```

---

## Search & Cache Commands

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
```

**What It Does**:
1. Parses content based on type
2. Creates/updates SearchableContent records
3. Updates PostgreSQL search vectors
4. Applies field weights (Title: A, Description: B, Content: C)

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

## Static File Commands

### build_css

Build and optimize CSS with PostCSS, PurgeCSS, and minification.

**Usage**:
```bash
python manage.py build_css
```

**Options**:
- `--dev`: Development mode (skip purging, keep source maps)

**Build Process**:
1. Combine all CSS files → `combined.css`
2. Minify with cssnano → `combined.processed.css`
3. Purge unused CSS → `combined.purged.css` (production only)
4. Output final `combined.min.css`
5. Generate `.gz` and `.br` compressed versions

**Output Files**:
- `combined.min.css`: Production CSS
- `combined.min.css.gz`: Gzip compressed
- `combined.min.css.br`: Brotli compressed

### optimize_js

Optimize and minify JavaScript files with Terser.

**Usage**:
```bash
python manage.py optimize_js
```

**Options**:
- `--skip-minify`: Skip minification
- `--skip-compress`: Skip gzip/brotli compression

**What It Does**:
1. Minifies JavaScript with Terser
2. Removes console.log statements (production)
3. Creates source maps
4. Generates compressed versions

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
4. Creates brotli compressed versions
5. Uploads to S3 (if configured)

**Production Build Pipeline**:
```bash
python manage.py build_css
python manage.py optimize_js
python manage.py collectstatic_optimize
```

---

## Monitoring Commands

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
```

**What It Does**:
1. Runs Lighthouse CLI via subprocess
2. Captures JSON report
3. Extracts 4 key scores (Performance, Accessibility, Best Practices, SEO)
4. Stores LighthouseResult in database

**Requirements**:
- Lighthouse installed: `npm install -g lighthouse`
- Chromium/Chrome available

### geolocate_fingerprints

Batch process IP addresses to add geolocation data to request fingerprints.

**Usage**:
```bash
python manage.py geolocate_fingerprints
```

**Options**:
- `--limit N`: Maximum records to process
- `--force`: Re-geolocate all records
- `--batch-size N`: IPs per batch request (default: 100)
- `--yes`: Skip confirmation prompt

**Examples**:
```bash
# Interactive mode
python manage.py geolocate_fingerprints

# Automated mode
python manage.py geolocate_fingerprints --yes --limit 1000
```

**How It Works**:
1. Queries RequestFingerprint records without geo_data
2. Filters out local/private IPs
3. Batches IPs to ip-api.com
4. Updates records with geolocation data
5. Respects rate limits (15 requests/minute)

### remove_local_fingerprints

Remove request fingerprints from local/private IP addresses.

**Usage**:
```bash
python manage.py remove_local_fingerprints
```

**Options**:
- `--dry-run`: Preview which records would be deleted
- `--limit N`: Limit number of records to delete

**What It Removes**:
- Local IPs: `127.0.0.1`, `::1`, `localhost`
- Private ranges: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`
- Link-local: `169.254.0.0/16`, `fe80::/10`

### setup_periodic_tasks

Configure Celery Beat periodic tasks for automated operations.

**Usage**:
```bash
python manage.py setup_periodic_tasks
```

**What It Configures**:
1. Daily Lighthouse Audit - 2 AM UTC
2. Daily Sitemap Rebuild - 3 AM UTC
3. Daily Knowledge Graph Screenshot - 4 AM UTC
4. Knowledge Graph Cache Rebuild - Every 6 hours

---

## FeeFiFoFunds Commands

### ingest_sequential

Fast sequential ingestion of Kraken OHLCV data files using QuestDB ILP (50K-100K records/sec).

**Usage**:
```bash
python manage.py ingest_sequential [--tier TIER] [--intervals INTERVALS]
```

**Options**:
- `--tier`: Asset tier to ingest (TIER1/TIER2/TIER3/TIER4/ALL)
- `--intervals`: Comma-separated intervals in minutes
- `--yes`, `-y`: Skip confirmation prompts
- `--stop-on-error`: Stop processing on first error

**Examples**:
```bash
# Ingest only TIER1 assets (fastest)
python manage.py ingest_sequential --tier TIER1

# Ingest with specific intervals
python manage.py ingest_sequential --tier TIER1 --intervals 60,1440

# Automated run
python manage.py ingest_sequential --tier TIER1 --yes
```

**Asset Tiers**:
- **TIER1**: Major cryptos (BTC, ETH, USDT, etc.)
- **TIER2**: Established projects (UNI, AAVE, LINK, etc.)
- **TIER3**: Emerging projects (BAT, ENJ, GALA, etc.)
- **TIER4**: Small/speculative (all others)

**Performance**:
- TIER1 OHLCV: ~10-15 seconds
- Full dataset: ~30-60 minutes

### backfill_prices

Backfill historical asset price data from external sources.

**Usage**:
```bash
python manage.py backfill_prices --source SOURCE [--ticker SYMBOL | --all] --days N
```

**Options**:
- `--source` (required): Data source (massive/finnhub)
- `--ticker`: Single asset ticker
- `--all`: Backfill all active assets
- `--days`: Number of days to backfill
- `--grouped`: Use grouped endpoint (massive only, MUCH faster)
- `--dry-run`: Preview without saving

**Examples**:
```bash
# Single asset
python manage.py backfill_prices --ticker AAPL --source massive --days 730

# All assets with grouped endpoint (fastest)
python manage.py backfill_prices --source massive --days 365 --all --grouped

# Filter by category
python manage.py backfill_prices --source massive --days 365 --all --category CRYPTO
```

**Grouped Mode Benefits**:
- 1 API call per day instead of N calls per asset
- Example: 365 days × 100 assets = 365 calls vs 36,500 calls

### load_prices

Load asset price data from external sources.

**Usage**:
```bash
python manage.py load_prices --ticker SYMBOL --source SOURCE --days N
```

**Options**:
- `--ticker` (required): Asset ticker symbol
- `--source` (required): Data source (massive/finnhub)
- `--days`: Number of days to fetch (default: 7)
- `--dry-run`: Preview data without saving

### create_asset

Create a new asset record in PostgreSQL.

**Usage**:
```bash
python manage.py create_asset --ticker SYMBOL --name "Asset Name" --category TYPE
```

**Options**:
- `--ticker` (required): Asset ticker symbol
- `--name` (required): Full asset name
- `--category` (required): Asset category (STOCK/CRYPTO/COMMODITY/CURRENCY)
- `--quote-currency`: Currency for pricing (default: USD)
- `--description`: Optional description

### backfill_kraken_gaps

Detect and backfill gaps in Kraken asset price data.

**Usage**:
```bash
python manage.py backfill_kraken_gaps [--tier TIER] [--asset TICKER]
```

**Options**:
- `--tier`: Filter by asset tier
- `--asset`: Filter by specific asset
- `--interval`: Filter by specific interval
- `--yes`: Auto-confirm all backfills
- `--dry-run`: Only detect gaps
- `--show-unfillable-only`: Show gaps beyond API limit
- `--export-unfillable`: Export unfillable gaps to CSV

**720-Candle Limitation**:
- Daily (1440 min): ~2 years from today
- Hourly (60 min): 30 days from today
- 5-minute: ~2.5 days from today

### check_questdb_version

Check QuestDB version for DEDUP support (requires 7.3+).

**Usage**:
```bash
python manage.py check_questdb_version
```

---

## Command Patterns

### Common Options

Most commands support:
- **Dry Run**: `--dry-run` - Preview changes without applying
- **Verbosity**: `--verbosity [0-3]` - Control output detail
- **Yes/No Prompts**: `--yes` or `--no-input` - Skip confirmations

### Output Standards

All commands follow consistent formatting:
- 📊 Summary statistics at start
- ⏱️ Real-time progress with percentage and ETA
- ✓/✗/⊘ Status indicators for success/failure/skip
- ─── Visual separators between sections
- 📈 Final summary with totals and elapsed time

---

## Related Documentation

- [Architecture](architecture.md) - Django apps and system design
- [Testing](testing.md) - Testing management commands
- [Deployment](deployment.md) - Production deployment
- [Blog App](apps/blog/) - Blog system documentation
- [FeeFiFoFunds App](apps/feefifofunds/) - Multi-asset tracking system
- [Search System](features/search.md) - Full-text search architecture
- [Performance Monitoring](features/performance-monitoring.md) - Lighthouse audits
- [Request Tracking](features/request-tracking.md) - Security and analytics
