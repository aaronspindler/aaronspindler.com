# Full-Text Search System

## Overview

The search system provides powerful full-text search across blog posts, photos, albums, projects, and books using PostgreSQL's built-in search capabilities with trigram similarity for typo tolerance.

## Features

- **PostgreSQL Full-Text Search**: Native database search with ranking
- **Trigram Similarity**: Typo-tolerant matching for better user experience
- **Autocomplete**: Real-time suggestions after 2 characters
- **Weighted Fields**: Prioritize title matches over content
- **Sub-100ms Performance**: Optimized with GIN indexes
- **Multi-Content Search**: Unified search across all content types
- **Keyboard Navigation**: Arrow keys, enter, and escape support
- **Mobile-Friendly**: Responsive design with touch support

## Architecture

### SearchableContent Model

Centralized search index stored in the `utils` app:

**Fields**:
- `title`: Content title (indexed)
- `description`: Brief description (indexed)
- `content`: Full content text (indexed)
- `content_type`: Type of content (blog, project, book)
- `url`: Link to content
- `category`: Content category (for filtering)
- `search_vector`: PostgreSQL tsvector field (GIN indexed)
- `published_at`: Publication date
- `updated_at`: Last update timestamp

### Photo/Album Search Vectors

Photos and albums have their own `search_vector` fields:

**Photo Search Fields**:
- Title (weight: A)
- Description (weight: B)
- Location (weight: B)
- Camera make/model (weight: C)
- Lens make/model (weight: C)

**PhotoAlbum Search Fields**:
- Title (weight: A)
- Description (weight: B)

## Search Algorithm

### Combined Scoring

The search system uses a hybrid approach:

**70% Full-Text Search Rank** + **30% Trigram Similarity**

```python
combined_score = (0.7 * fts_rank) + (0.3 * trigram_similarity)
```

### Relevance Thresholds

Results must meet one of these thresholds:
- FTS rank > 0.01 (meaningful full-text match)
- Trigram similarity > 0.2 (20% similarity for typos)

### Field Weights

PostgreSQL weights for FTS:
- **A**: Title (highest priority, weight 1.0)
- **B**: Description (medium priority, weight 0.4)
- **C**: Content (lower priority, weight 0.2)

## Usage

### Frontend Autocomplete

The autocomplete is already implemented in vanilla JavaScript:

**File**: `/static/js/search-autocomplete.js`

**Features**:
- Triggers after 2 characters typed
- 300ms debounce to reduce API calls
- Keyboard navigation (↑↓ arrows, Enter, Escape)
- Click or Enter to navigate
- Escape to close dropdown
- Automatic dropdown positioning

**HTML Integration**:
```html
<input
    type="text"
    id="search-input"
    placeholder="Search posts, photos, projects..."
    autocomplete="off"
>
<div id="search-results" class="search-dropdown"></div>

<script src="{% static 'js/search-autocomplete.js' %}"></script>
```

### Backend API

#### Autocomplete Endpoint

```http
GET /api/search/autocomplete/?q=<query>
```

**Query Parameters**:
- `q`: Search query (minimum 2 characters)

**Response**:
```json
{
  "suggestions": [
    {
      "title": "Django Full-Text Search Tutorial",
      "type": "Blog Post",
      "url": "/b/tech/django-search-tutorial/",
      "category": "tech",
      "match_type": "title"
    },
    {
      "title": "Photo Gallery",
      "type": "Photo Album",
      "url": "/photos/album/gallery/",
      "match_type": "content"
    },
    {
      "title": "Search Engine Project",
      "type": "Project",
      "url": "https://github.com/user/search-engine",
      "external": true,
      "match_type": "description"
    }
  ]
}
```

**Response Fields**:
- `title`: Content title
- `type`: Content type (Blog Post, Photo, Album, Project, Book)
- `url`: Link to content
- `category`: Content category (if applicable)
- `external`: Boolean for external links
- `match_type`: Which field matched (title, description, content)

## Search Index Management

### Rebuilding Index

Rebuild the search index after adding or modifying content:

```bash
# Rebuild all content types
python manage.py rebuild_search_index

# Rebuild specific content type
python manage.py rebuild_search_index --content-type blog
python manage.py rebuild_search_index --content-type photos
python manage.py rebuild_search_index --content-type albums
python manage.py rebuild_search_index --content-type books
python manage.py rebuild_search_index --content-type projects

# Clear and rebuild entire index
python manage.py rebuild_search_index --clear

# Clear and rebuild specific type
python manage.py rebuild_search_index --clear --content-type blog
```

**Command Options**:
- `--clear`: Delete existing index before rebuilding
- `--content-type`: Rebuild specific type (blog, photos, albums, books, projects, all)

### When to Rebuild

**Required**:
- After adding new blog posts
- After modifying blog post content
- After adding photos or albums
- After updating project or book data
- After initial setup

**Optional**:
- Periodically (e.g., weekly) to ensure consistency
- After bulk imports
- If search results seem outdated

### Automatic Updates

Some models automatically update search vectors on save:
- **Photo**: Updates on create/update
- **PhotoAlbum**: Updates on create/update

Blog posts, projects, and books require manual rebuild since they're not database models.

## PostgreSQL Configuration

### Required Extensions

```sql
-- Trigram similarity for typo tolerance
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Unaccent for accent-insensitive search
CREATE EXTENSION IF NOT EXISTS unaccent;
```

### GIN Indexes

Indexes are automatically created by migrations:

```python
# SearchableContent model
class Meta:
    indexes = [
        GinIndex(fields=['search_vector']),
        models.Index(fields=['content_type']),
        models.Index(fields=['published_at']),
    ]

# Photo model
class Meta:
    indexes = [
        GinIndex(fields=['search_vector']),
    ]

# PhotoAlbum model
class Meta:
    indexes = [
        GinIndex(fields=['search_vector']),
    ]
```

### Trigram Index

For similarity matching:

```sql
CREATE INDEX photo_title_trigram_idx ON photos_photo USING gin (title gin_trgm_ops);
CREATE INDEX album_title_trigram_idx ON photos_photoalbum USING gin (title gin_trgm_ops);
```

## Search Implementation

### Python Search Function

```python
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector, TrigramSimilarity
from django.db.models import F, Q
from utils.models import SearchableContent

def search_content(query_text, content_types=None, limit=10):
    """
    Search across all content types with FTS + trigram similarity.

    Args:
        query_text: Search query string
        content_types: List of content types to search (None = all)
        limit: Maximum results to return

    Returns:
        QuerySet of SearchableContent ordered by relevance
    """
    if len(query_text) < 2:
        return SearchableContent.objects.none()

    # Build search query
    search_query = SearchQuery(query_text, config='english')

    # Base queryset
    qs = SearchableContent.objects.all()

    # Filter by content types if specified
    if content_types:
        qs = qs.filter(content_type__in=content_types)

    # Annotate with search rank and trigram similarity
    qs = qs.annotate(
        rank=SearchRank(F('search_vector'), search_query),
        similarity=TrigramSimilarity('title', query_text),
    )

    # Combined scoring: 70% FTS, 30% similarity
    qs = qs.annotate(
        combined_score=(0.7 * F('rank')) + (0.3 * F('similarity'))
    )

    # Filter by relevance thresholds
    qs = qs.filter(
        Q(rank__gt=0.01) | Q(similarity__gt=0.2)
    )

    # Order by combined score
    qs = qs.order_by('-combined_score')

    return qs[:limit]
```

### View Implementation

```python
from django.http import JsonResponse
from django.views.decorators.http import require_GET

@require_GET
def autocomplete_search(request):
    """API endpoint for search autocomplete."""
    query = request.GET.get('q', '').strip()

    if len(query) < 2:
        return JsonResponse({'suggestions': []})

    # Search content
    results = search_content(query, limit=10)

    # Format suggestions
    suggestions = [
        {
            'title': result.title,
            'type': result.get_content_type_display(),
            'url': result.url,
            'category': result.category,
            'external': result.url.startswith('http'),
        }
        for result in results
    ]

    return JsonResponse({'suggestions': suggestions})
```

## Performance Optimization

### Query Performance

**Typical Performance**:
- Simple queries: 10-30ms
- Complex queries: 30-80ms
- Autocomplete: < 100ms (target)

**Optimization Techniques**:
1. **GIN Indexes**: Fast full-text search
2. **Trigram Indexes**: Fast similarity matching
3. **Selective Fields**: Only index relevant content
4. **Query Limits**: Restrict result count (10-20 items)
5. **Connection Pooling**: Reuse database connections

### Caching Strategy

```python
from django.core.cache import cache

def cached_search(query_text, cache_timeout=300):
    """Cache search results for 5 minutes."""
    cache_key = f"search:{query_text.lower()}"

    # Check cache
    results = cache.get(cache_key)
    if results is not None:
        return results

    # Perform search
    results = list(search_content(query_text))

    # Cache results
    cache.set(cache_key, results, cache_timeout)

    return results
```

### Index Maintenance

```sql
-- Analyze tables periodically for optimal query planning
ANALYZE utils_searchablecontent;
ANALYZE photos_photo;
ANALYZE photos_photoalbum;

-- Vacuum to reclaim space and update statistics
VACUUM ANALYZE utils_searchablecontent;
```

## Advanced Features

### Search Filters

Add filters to search queries:

```python
# Filter by content type
results = search_content('django', content_types=['blog'])

# Filter by date range
from datetime import datetime, timedelta
recent = datetime.now() - timedelta(days=30)
results = search_content('django').filter(published_at__gte=recent)

# Filter by category
results = search_content('django').filter(category='tech')
```

### Highlighting Matches

Highlight matching terms in results:

```python
from django.contrib.postgres.search import SearchHeadline

results = SearchableContent.objects.annotate(
    headline=SearchHeadline(
        'content',
        search_query,
        start_sel='<mark>',
        stop_sel='</mark>',
    )
).filter(search_vector=search_query)
```

### Search Analytics

Track search queries for insights:

```python
from utils.models import SearchQuery as SearchQueryLog

def log_search(query_text, results_count, user=None):
    """Log search query for analytics."""
    SearchQueryLog.objects.create(
        query=query_text,
        results_count=results_count,
        user=user,
    )

# In view
results = search_content(query)
log_search(query, results.count(), request.user)
```

## Troubleshooting

### Search Returns No Results

**Solutions**:
1. Rebuild search index: `python manage.py rebuild_search_index`
2. Check PostgreSQL extensions are installed: `pg_trgm`, `unaccent`
3. Verify content exists in SearchableContent table
4. Check search query length (minimum 2 characters)
5. Review query syntax (no special characters causing issues)

### Search Performance is Slow

**Solutions**:
1. Check GIN indexes exist: `\di` in psql
2. Analyze tables: `ANALYZE utils_searchablecontent;`
3. Reduce result limit in queries
4. Enable query caching
5. Consider read replicas for heavy traffic

### Trigram Similarity Not Working

**Solutions**:
1. Verify `pg_trgm` extension is installed: `CREATE EXTENSION IF NOT EXISTS pg_trgm;`
2. Check trigram indexes exist
3. Restart PostgreSQL after extension installation
4. Review similarity threshold (may need adjustment)

### Autocomplete Not Triggering

**Solutions**:
1. Check JavaScript console for errors
2. Verify `search-autocomplete.js` is loaded
3. Check API endpoint is accessible: `/api/search/autocomplete/`
4. Verify CSRF token is included (if POST)
5. Check debounce timing (300ms default)

### Search Missing Recent Content

**Solutions**:
1. Rebuild search index: `python manage.py rebuild_search_index`
2. Check content is published (not draft)
3. Verify search vector is populated in database
4. Clear cache: `python manage.py clear_cache`
5. Check content dates are not in future

## Configuration

### Django Settings

```python
# Search configuration
SEARCH_MIN_QUERY_LENGTH = 2
SEARCH_RESULTS_LIMIT = 10
SEARCH_CACHE_TIMEOUT = 300  # 5 minutes

# PostgreSQL search configuration
SEARCH_CONFIG = 'english'  # Language configuration

# Field weights
SEARCH_WEIGHTS = {
    'A': 1.0,   # Title
    'B': 0.4,   # Description
    'C': 0.2,   # Content
}

# Similarity thresholds
SIMILARITY_THRESHOLD = 0.2  # 20% similarity
RANK_THRESHOLD = 0.01  # Minimum FTS rank
```

### Frontend Configuration

```javascript
// search-autocomplete.js configuration
const SEARCH_CONFIG = {
    minQueryLength: 2,
    debounceDelay: 300,  // milliseconds
    maxResults: 10,
    apiEndpoint: '/api/search/autocomplete/',
};
```

## Related Documentation

- [Blog System](blog-system.md) - Blog post indexing
- [Photo Management](photo-management.md) - Photo/album indexing
- [Management Commands](../commands.md) - rebuild_search_index command
- [API Reference](../api.md) - Search API documentation
- [Architecture](../architecture.md) - Search system architecture
