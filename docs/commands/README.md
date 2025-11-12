# Management Commands Reference

## Overview

Comprehensive reference for all custom Django management commands in the project, organized by functionality.

## Command Categories

### App-Specific Commands

Commands specific to individual Django apps:

- **[Blog Commands](../../apps/blog/commands.md)** - Blog and knowledge graph management
  - `create_blog_post` - Create new blog post from template
  - `rebuild_knowledge_graph` - Rebuild graph cache
  - `generate_knowledge_graph_screenshot` - Generate high-quality screenshot

- **[FeeFiFoFunds Commands](../../apps/feefifofunds/commands.md)** - Financial data management
  - `setup_questdb_schema` - Initialize QuestDB tables
  - `create_asset` - Manually create asset records
  - `ingest_sequential` - Fast Kraken OHLCV CSV ingestion (50K-100K records/sec)
  - `load_prices` - Load prices from external APIs
  - `backfill_prices` - Backfill historical data

### Cross-Cutting Commands

Commands that work across multiple apps:

- **[Static File Commands](static.md)** - CSS, JavaScript, and static asset management
  - `build_css` - Build and optimize CSS
  - `optimize_js` - Minify JavaScript
  - `collectstatic_optimize` - Collect and optimize all static files

- **[Search & Cache Commands](search-cache.md)** - Search index and cache management
  - `rebuild_search_index` - Rebuild full-text search index
  - `clear_cache` - Clear all application caches

- **[Monitoring Commands](monitoring.md)** - Performance, security, and request tracking
  - `run_lighthouse_audit` - Run Lighthouse performance audit
  - `geolocate_fingerprints` - Geolocate IP addresses
  - `remove_local_fingerprints` - Remove local/private IP records

## Quick Reference

| Command | Category | Description |
|---------|----------|-------------|
| `rebuild_knowledge_graph` | Blog | Rebuild knowledge graph cache |
| `ingest_sequential` | FeeFiFoFunds | Fast Kraken OHLCV CSV ingestion |
| `build_css` | Static | Build and optimize CSS |
| `rebuild_search_index` | Search | Rebuild full-text search index |
| `run_lighthouse_audit` | Monitoring | Run performance audit |
| `backfill_prices` | FeeFiFoFunds | Backfill historical prices |
| `clear_cache` | Cache | Clear all caches |

## Command Patterns

### Common Options

Most commands support these common patterns:

- **Dry Run**: `--dry-run` - Preview changes without applying
- **Verbosity**: `--verbosity [0-3]` - Control output detail
- **Yes/No Prompts**: `--yes` or `--no-input` - Skip confirmations

### Output Standards

All commands follow consistent output formatting:
- 📊 Summary statistics at start
- ⏱️ Real-time progress with percentage and ETA
- ✓/✗/⊘ Status indicators for success/failure/skip
- ─── Visual separators between sections
- 📈 Final summary with totals and elapsed time

### Example Command Structure

```bash
# Pattern: python manage.py <command> [args] [options]
python manage.py rebuild_search_index --content-type blog --clear
```

## Related Documentation

- [Architecture](../architecture.md) - Django apps and management command locations
- [Testing](../testing.md) - Testing management commands
- [Deployment](../deployment.md) - Commands for production environments
- [Documentation Index](../README.md) - Complete documentation map

### App-Specific Documentation

- [Blog App](../apps/blog/) - Blog system architecture and usage
- [Photos App](../apps/photos/) - Photo management system
- [FeeFiFoFunds App](../apps/feefifofunds/) - Multi-asset tracking system

---

**For complete command documentation, see the category-specific files linked above.**
