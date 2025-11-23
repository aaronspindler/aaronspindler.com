# Blog Management Commands

Management commands for the blog app, including blog post creation, knowledge graph rebuilding, and screenshot generation.

## Commands

### create_blog_post

Create a new blog post with automatic numbering and template generation.

**Usage**:
```bash
python manage.py create_blog_post --title "Your Post Title" --category tech
```

**Options**:
- `--title` (required): Title of the blog post
- `--category` (required): Category (hobbies, personal, projects, reviews, tech)

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
- Creates file at `blog/templates/blog/<category>/####_Post_Title.html`
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

## Related Documentation

- [Blog System](blog-system.md) - Blog architecture and template structure
- [Knowledge Graph](knowledge-graph.md) - Graph visualization system
- [Commands Index](../../commands/README.md) - All management commands
- [API Reference](../../api.md) - Blog and graph API endpoints
