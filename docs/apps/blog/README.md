# Blog App Documentation

> **Template-based blog system** with knowledge graph visualization, comments, and syntax highlighting.

## Overview

The blog app provides a unique template-based blogging system where blog posts are HTML templates with extracted metadata. This approach offers maximum flexibility for rich content while maintaining a clean architecture.

**Key Features:**
- Template-based blog posts stored in `blog/templates/blog/`
- Automatic metadata extraction from template blocks
- Interactive knowledge graph visualization with D3.js
- Comment system with voting
- Syntax highlighting with Prism.js
- View count tracking
- Category-based organization (hobbies, personal, projects, reviews, tech)

## Documentation

### Core Documentation

- **[Blog System](blog-system.md)** - Complete blog architecture guide
  - Template-based post structure
  - Creating and managing blog posts
  - Categories and organization
  - Comment system
  - Syntax highlighting with Prism.js
  - View tracking

- **[Knowledge Graph](knowledge-graph.md)** - Interactive visualization system
  - Graph architecture and components
  - Link extraction and categorization
  - D3.js visualization
  - Server-side screenshot generation with Pyppeteer
  - API endpoints
  - Performance optimizations

### Related Documentation

**Core Docs:**
- [Architecture](../../architecture.md) - Blog app structure in Django apps section
- [Commands](../../commands.md#blog--knowledge-graph) - Blog-related management commands
- [API Reference](../../api.md) - Blog and knowledge graph API endpoints

**Related Features:**
- [Search System](../../features/search.md) - Blog posts are searchable
- [Performance Monitoring](../../features/performance-monitoring.md) - Graph screenshot generation pattern
- [Request Tracking](../../features/request-tracking.md) - Blog visit tracking

## Quick Start

### Creating a Blog Post

1. **Create template file**:
   ```bash
   # Create in blog/templates/blog/[category]/[slug].html
   touch blog/templates/blog/tech/my-new-post.html
   ```

2. **Add metadata blocks**:
   ```html
   {% extends "blog/post.html" %}

   {% block meta_title %}My New Post{% endblock %}
   {% block meta_description %}Post description{% endblock %}
   {% block meta_publish_date %}2025-01-10{% endblock %}
   {% block meta_post_type %}Tech{% endblock %}
   {% block meta_reading_time %}5{% endblock %}

   {% block content %}
   <p>Your content here...</p>
   {% endblock %}
   ```

3. **Rebuild knowledge graph**:
   ```bash
   python manage.py rebuild_knowledge_graph
   python manage.py generate_knowledge_graph_screenshot
   ```

**See [Blog System](blog-system.md) for complete guide.**

### Working with Knowledge Graph

```bash
# Rebuild graph data
python manage.py rebuild_knowledge_graph

# Generate screenshot (local)
python manage.py generate_knowledge_graph_screenshot

# Generate screenshot (production)
python manage.py generate_knowledge_graph_screenshot --url https://aaronspindler.com
```

**See [Knowledge Graph](knowledge-graph.md) for architecture and API details.**

## Project Structure

```
blog/
├── __init__.py
├── admin.py                    # Django admin configuration
├── models.py                   # BlogPost, BlogComment models
├── views.py                    # Blog views
├── views_json.py               # Knowledge graph API
├── knowledge_graph.py          # Graph building logic
├── management/
│   └── commands/
│       ├── rebuild_knowledge_graph.py
│       └── generate_knowledge_graph_screenshot.py
├── templates/
│   └── blog/                   # Base templates
│       ├── base.html
│       ├── post.html
│       └── [category]/         # Blog post templates
│           └── [slug].html
└── static/
    ├── css/blog.css
    └── js/knowledge-graph.js   # D3.js visualization
```

## Key Components

### Models

**BlogPost**: Dynamically loaded from template files
- Metadata extracted from template blocks
- Not stored in database
- File modification time tracking
- View count tracking

**BlogComment**: User comments on blog posts
- Stores in PostgreSQL
- Voting system (upvotes/downvotes)
- Moderation support

### Knowledge Graph System

**Components:**
- **LinkParser**: Extracts links from blog post content
- **GraphBuilder**: Constructs graph structure from posts and links
- **D3.js Visualization**: Interactive force-directed graph
- **Screenshot Generator**: Pyppeteer-based screenshot generation

**See [Knowledge Graph](knowledge-graph.md) for complete architecture.**

## Common Tasks

### Blog Management

```bash
# List all blog posts
python manage.py shell
>>> from blog.models import BlogPost
>>> BlogPost.objects.all()

# Rebuild knowledge graph
python manage.py rebuild_knowledge_graph

# Generate knowledge graph screenshot
python manage.py generate_knowledge_graph_screenshot
```

### Adding Syntax Highlighting

Use Prism.js syntax highlighting in posts:

```html
<pre><code class="language-python">
def hello_world():
    print("Hello, World!")
</code></pre>
```

**Supported languages**: python, javascript, html, css, bash, sql, json, and more

**See [Blog System](blog-system.md#syntax-highlighting) for complete list.**

## API Endpoints

- `GET /blog/api/graph/data/` - Knowledge graph data (nodes and links)
- `GET /blog/api/graph/screenshot/` - Latest graph screenshot
- `POST /blog/api/comments/{id}/vote/` - Vote on comment

**See [API Reference](../../api.md#blog--knowledge-graph) for complete API documentation.**

## Future Enhancements

### Planned Features

**Phase 2:**
- RSS feed generation
- Tag system (in addition to categories)
- Related posts suggestions
- Blog post series/collections

**Phase 3:**
- Full-text search within posts
- Blog post scheduling
- Draft system
- Multi-author support

**Phase 4:**
- Markdown support (in addition to HTML)
- Blog post analytics dashboard
- Email notifications for comments
- Social media sharing integrations

## Contributing

When contributing to the blog app:

1. **Follow template structure** for new posts
2. **Update knowledge graph** after adding posts
3. **Test syntax highlighting** for code examples
4. **Document new features** in this directory
5. **Update API docs** if adding endpoints

**See [Blog System](blog-system.md) for complete contribution guidelines.**

---

**Questions?** Check the [Documentation Index](../../README.md) or create a GitHub issue.
