# Search & Cache Management Commands

Management commands for rebuilding search indexes and managing application caches.

## Commands

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



## Related Documentation

- [Search System](../features/search.md) - Full-text search architecture
- [Commands Index](README.md) - All management commands
- [Architecture](../architecture.md) - Caching strategy
