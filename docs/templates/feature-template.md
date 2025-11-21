# Feature Documentation Checklist

Use this lightweight checklist when documenting new features. Include only sections relevant to your feature.

## Essential Elements

### ✅ Overview (Required)
- [ ] Feature name and purpose (1-2 sentences)
- [ ] Key capabilities (bullet list)

### ✅ Technical Details (As Needed)
- [ ] **Data Models**: List models and key fields
- [ ] **API Endpoints**: Document new endpoints with examples
- [ ] **Management Commands**: Command syntax and common usage
- [ ] **Configuration**: Environment variables or settings

### ✅ Usage (Recommended)
- [ ] Basic example showing most common use case
- [ ] When to use this feature

### ✅ Notes (Optional)
- [ ] Performance considerations
- [ ] Common issues and solutions
- [ ] Integration with other features

## Example

```markdown
# Search System

Full-text search across blog posts, photos, and projects using PostgreSQL.

**Capabilities:**
- PostgreSQL full-text search with trigram similarity
- Multi-model search (blog, photos, projects)
- Auto-complete suggestions

**Models:** `SearchableContent` - stores searchable text with vectors

**Command:** `python manage.py rebuild_search_index [--content-type TYPE]`

**API:** `GET /api/search/?q=query` - Returns ranked results

**Usage:**
```python
from utils.models import SearchableContent
results = SearchableContent.search("django tips")
```

**Performance:** Uses PostgreSQL GIN indexes, ~50ms average query time
```

## Tips

- Keep it concise - aim for 1-2 pages max
- Focus on what developers need to know
- Link to commands.md for detailed command docs
- Link to api.md for detailed API docs
- Skip sections that don't apply
- Use code examples over lengthy descriptions
