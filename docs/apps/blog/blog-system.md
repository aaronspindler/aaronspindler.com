# Blog System

## Overview

The blog system uses a unique template-based approach where blog posts are HTML templates rather than database entries. This design provides version control, developer-friendly editing, and rich formatting capabilities without database overhead.

## Features

- **Template-Based Posts**: Blog posts stored as HTML templates with metadata blocks
- **Automatic Numbering**: Posts follow `####_Post_Name.html` naming convention
- **Category Organization**: Posts organized into personal, projects, reviews, and tech categories
- **Comment System**: Threaded comments with moderation and voting
- **Internal Linking**: Automatic relationship tracking via knowledge graph
- **Syntax Highlighting**: Prism.js-powered code highlighting with copy-to-clipboard
- **Reading Time**: Automatic calculation of estimated reading time
- **SEO Optimized**: Meta descriptions, titles, and structured data

## Blog Post Structure

### Template Format

Blog posts are stored in `blog/templates/blog/<category>/####_Post_Name.html`:

```html
{% extends "blog/blog_post.html" %}

{% block meta_description %}
A brief description of your blog post for search engines and social media.
{% endblock %}

{% block meta_title %}Your Blog Post Title{% endblock %}
{% block meta_publish_date %}2025-01-15{% endblock %}
{% block meta_post_type %}tech{% endblock %}
{% block meta_reading_time %}5{% endblock %}

{% block content %}
<h2>Your Post Content</h2>
<p>Write your content here with full HTML formatting.</p>
{% endblock %}
```

### Metadata Blocks

**Required Blocks**:
- `meta_title`: Post title displayed in browser and search results
- `meta_description`: Brief summary for SEO and social sharing
- `meta_publish_date`: Publication date (YYYY-MM-DD format)
- `meta_post_type`: Category (personal, projects, reviews, tech)
- `meta_reading_time`: Estimated reading time in minutes

**Optional Blocks**:
- `extra_head`: Additional CSS or scripts for specific posts
- `pre_content`: Content before main article (e.g., table of contents)
- `post_content`: Content after main article (e.g., related posts)

### Categories

**Available Categories**:
- **hobbies**: Hobby-related posts and interests
- **personal**: Personal stories, experiences, life updates
- **projects**: Project showcases, technical deep-dives
- **reviews**: Product reviews, book reviews, service reviews
- **tech**: Technical tutorials, guides, and insights

## Creating Blog Posts

### Using Management Command (Recommended)

The easiest way to create a new blog post:

```bash
# Create a new blog post with automatic numbering
python manage.py create_blog_post --title "Your Blog Title" --category tech

# Create in different categories
python manage.py create_blog_post --title "Weekend Adventures" --category personal
python manage.py create_blog_post --title "Project Showcase" --category projects
python manage.py create_blog_post --title "Book Review" --category reviews
```

The command will:
- Automatically assign the next available blog number
- Create the file in the correct category directory
- Generate a template with formatting guidelines and examples
- Include code block examples for syntax highlighting

### Manual Creation

1. **Determine the next blog number**:
   ```bash
   ls blog/templates/blog/*/*.html | wc -l
   ```

2. **Create the template file**:
   ```
   blog/templates/blog/<category>/####_Post_Name.html
   ```

3. **Add metadata and content** using the template format above

4. **Rebuild knowledge graph** to include the new post:
   ```bash
   python manage.py rebuild_knowledge_graph
   ```

5. **Update search index**:
   ```bash
   python manage.py rebuild_search_index --content-type blog
   ```

## Code Formatting

Blog posts use Prism.js for syntax highlighting. Always format code blocks properly:

### Multi-line Code Blocks

```html
<pre><code class="language-python">
def hello_world():
    print("Hello, World!")
</code></pre>
```

### Supported Languages

Use `language-{name}` format for the class attribute:

- `language-python` - Python code
- `language-bash` - Bash/shell commands
- `language-javascript` or `language-js` - JavaScript
- `language-html` - HTML markup
- `language-css` - CSS styles
- `language-sql` - SQL queries
- `language-json` - JSON data
- `language-text` - Plain text output

### Inline Code

For inline code within paragraphs:

```html
<p>Use the <code>manage.py</code> command to run migrations.</p>
```

### Styling Notes

- **DO NOT** add custom borders, backgrounds, or margins to code elements
- Prism.js automatically adds line numbers and copy-to-clipboard functionality
- The site's CSS overrides Prism colors to match the theme
- Copy button appears on hover for easy code copying

## Comment System

### Features

- **Threaded Comments**: Reply to comments with unlimited nesting
- **Moderation**: All comments require approval by default
- **Voting**: Upvote/downvote system for community feedback
- **Anonymous Support**: Allow comments without authentication
- **Spam Protection**: CSRF tokens and rate limiting

### Moderation Workflow

1. User submits comment via blog post page
2. Comment stored with `is_approved=False`
3. Admin reviews comment in Django admin panel
4. Admin approves or deletes comment
5. Approved comments appear on blog post

### Vote Tracking

- Users can upvote or downvote comments
- Vote counts displayed next to each comment
- One vote per user per comment
- Users can change their vote
- Total score = upvotes - downvotes

## Internal Linking

The blog system automatically tracks relationships between posts through internal links:

### Link Types

- **Internal Links**: Links to other blog posts (included in knowledge graph)
- **External Links**: Links to external websites (tracked but not graphed)
- **Category Links**: Links to category pages

### Best Practices

Use relative URLs for internal links to enable automatic relationship tracking:

```html
<!-- Good: Relative URL -->
<a href="{% url 'blog_detail' category='tech' slug='django-tutorial' %}">Django Tutorial</a>

<!-- Also Good: Project-relative path -->
<a href="/b/tech/django-tutorial/">Django Tutorial</a>

<!-- Avoid: Absolute URLs (won't be tracked) -->
<a href="https://aaronspindler.com/b/tech/django-tutorial/">Django Tutorial</a>
```

## Template Normalization

The blog system includes a template normalization command to ensure consistent formatting:

```bash
# Normalize all blog post templates
python manage.py normalize_blog_templates

# Check for issues without making changes
python manage.py normalize_blog_templates --dry-run
```

### What it does:

- Ensures consistent metadata block formatting
- Adds missing required blocks with placeholders
- Fixes common template syntax issues
- Validates category values
- Checks date formats

## View Count Tracking

Each blog post automatically tracks view counts:

- **PageVisit Model**: Tracks individual visits with timestamps
- **Request Fingerprinting**: Associates visits with unique users
- **Privacy-Focused**: No personally identifiable information stored
- **Analytics**: View counts displayed in admin panel

## Search Integration

Blog posts are automatically indexed for full-text search:

### Indexed Fields

- **Title**: Weighted 'A' (highest priority)
- **Description**: Weighted 'B' (medium priority)
- **Content**: Weighted 'C' (lower priority)
- **Category**: Used for filtering

### Search Features

- PostgreSQL full-text search with GIN indexes
- Trigram similarity for typo tolerance
- Autocomplete after 2 characters
- Sub-100ms response time
- Category filtering

### Rebuilding Search Index

```bash
# Rebuild blog post index
python manage.py rebuild_search_index --content-type blog

# Clear and rebuild
python manage.py rebuild_search_index --clear --content-type blog
```

## Related Management Commands

```bash
# Create new blog post
python manage.py create_blog_post --title "Title" --category tech

# Rebuild knowledge graph
python manage.py rebuild_knowledge_graph

# Generate graph screenshot
python manage.py generate_knowledge_graph_screenshot

# Normalize templates
python manage.py normalize_blog_templates

# Rebuild search index
python manage.py rebuild_search_index --content-type blog
```

## API Endpoints

### Get Post Metadata

The blog system automatically generates metadata for all posts, accessible via template utilities:

```python
from blog.utils import get_all_blog_posts, get_blog_post_by_slug

# Get all posts
all_posts = get_all_blog_posts()

# Get specific post
post = get_blog_post_by_slug(category='tech', slug='post-slug')
```

### Comment Endpoints

- **POST** `/b/<category>/<slug>/comment/` - Submit new comment
- **POST** `/b/comment/<id>/vote/` - Vote on comment

## Troubleshooting

### Post Not Appearing

1. Check template file location: `templates/blog/<category>/####_Post_Name.html`
2. Verify all required metadata blocks are present
3. Check for template syntax errors
4. Rebuild knowledge graph cache: `python manage.py rebuild_knowledge_graph`
5. Clear cache: `python manage.py clear_cache`

### Code Highlighting Not Working

1. Verify Prism.js is loaded in base template
2. Check code block format matches documentation
3. Ensure language class is correct: `language-{name}`
4. Clear browser cache
5. Check browser console for JavaScript errors

### Comments Not Showing

1. Check comment approval status in admin panel
2. Verify comment is associated with correct post slug
3. Ensure CSRF token is present in comment form
4. Check for JavaScript errors in browser console

### Search Not Finding Post

1. Rebuild search index: `python manage.py rebuild_search_index --content-type blog`
2. Verify post has content in title, description, or content blocks
3. Check PostgreSQL search extensions are installed (pg_trgm, unaccent)
4. Clear cache and try again

## Related Documentation

- [Knowledge Graph](knowledge-graph.md) - Post relationship visualization
- [Search System](../../features/search.md) - Full-text search implementation
- [Management Commands](../../commands.md) - Complete command reference
- [Architecture](../../architecture.md) - Technical implementation details
