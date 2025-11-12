# Management Commands Reference

> **Note**: Commands have been organized into category-specific files for easier navigation. See [commands/README.md](commands/README.md) for the complete index.

## Quick Links

### App-Specific Commands

- **[Blog Commands](apps/blog/commands.md)** - Blog post creation, knowledge graph, screenshots
- **[FeeFiFoFunds Commands](apps/feefifofunds/commands.md)** - Database setup, asset management, data ingestion

### Cross-Cutting Commands

- **[Static File Commands](commands/static.md)** - CSS, JavaScript, static asset optimization
- **[Search & Cache Commands](commands/search-cache.md)** - Search index and cache management
- **[Monitoring Commands](commands/monitoring.md)** - Performance audits, request tracking, geolocation

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
make static
```

## Command Index by App

### Blog App
- `create_blog_post` - Create new blog post from template
- `rebuild_knowledge_graph` - Rebuild graph cache
- `generate_knowledge_graph_screenshot` - Generate high-quality screenshot

**See** [apps/blog/commands.md](apps/blog/commands.md)

### FeeFiFoFunds App
- `setup_questdb_schema` - Initialize QuestDB tables
- `create_asset` - Create asset records
- `ingest_sequential` - Fast Kraken OHLCV CSV ingestion (50K-100K records/sec)
- `load_prices` - Load prices from APIs
- `backfill_prices` - Backfill historical data

**See** [apps/feefifofunds/commands.md](apps/feefifofunds/commands.md)

### Static File Management
- `collectstatic_optimize` - Collect and optimize static files
- `build_css` - Build and optimize CSS
- `optimize_js` - Minify JavaScript

**See** [commands/static.md](commands/static.md)

### Search & Cache
- `rebuild_search_index` - Rebuild full-text search index
- `clear_cache` - Clear all caches
- `setup_periodic_tasks` - Setup Celery Beat tasks

**See** [commands/search-cache.md](commands/search-cache.md)

### Monitoring
- `run_lighthouse_audit` - Run performance audit
- `geolocate_fingerprints` - Geolocate IP addresses
- `remove_local_fingerprints` - Remove local/private IPs

**See** [commands/monitoring.md](commands/monitoring.md)

## Related Documentation

- [Commands Index](commands/README.md) - Complete command reference with organization
- [Architecture](architecture.md) - Django apps and command locations
- [Testing](testing.md) - Testing management commands
- [Deployment](deployment.md) - Production command usage

---

**For detailed command documentation, see the category-specific files linked above.**
