# Knowledge Graph

## Overview

The knowledge graph automatically visualizes relationships between blog posts using a D3.js-powered force-directed graph. It parses internal links between posts to build an interactive network visualization, making it easy to explore content connections.

## Features

- **Automatic Relationship Detection**: Parses blog post templates to extract internal links
- **Interactive Visualization**: D3.js force-directed graph with zoom and pan
- **Category Color Coding**: Visual distinction between post categories
- **Adaptive Layout**: Automatically adjusts force simulation based on graph size
- **Server-Side Screenshots**: High-quality PNG generation for social sharing
- **Smart Caching**: 20-minute cache with file modification tracking
- **Performance Optimized**: Handles graphs with 100+ nodes efficiently

## How It Works

### Link Extraction

The system parses all blog post templates to find internal links:

1. **Template Scanning**: Reads all blog post HTML templates
2. **Link Parsing**: Extracts `<a>` tags and `href` attributes
3. **URL Matching**: Identifies links to other blog posts
4. **Relationship Building**: Creates edges between linked posts

### Graph Construction

**Nodes**:
- **Blog Posts**: Individual posts with metadata (title, category, URL)
- **Categories**: Category nodes that group related posts

**Edges**:
- **Internal Links**: Connections between posts based on links
- **Category Membership**: Connections from posts to their categories

### Visualization

The graph uses D3.js force simulation with adaptive parameters:

**Small Graphs** (< 30 nodes):
- Higher charge force (-300)
- Longer links (100)
- Faster convergence

**Medium Graphs** (30-60 nodes):
- Moderate charge force (-200)
- Medium links (80)
- Balanced performance

**Large Graphs** (60+ nodes):
- Lower charge force (-100)
- Shorter links (60)
- Grid layout for large category groups (8+ nodes)
- Velocity limiting to prevent jitter (max: 10)

**Stability Features**:
- Collision detection with 1.0x radius for blog posts
- Stabilization phase when alpha < 0.1
- Maximum iteration limit (500 ticks)
- Golden angle distribution for category positioning

## Usage

### Viewing the Knowledge Graph

Visit the knowledge graph page on your site:
```
https://yoursite.com/knowledge-graph/
```

**Interaction**:
- **Click nodes**: Navigate to blog posts or category pages
- **Drag nodes**: Reposition nodes in the graph
- **Zoom**: Scroll to zoom in/out
- **Pan**: Click and drag background to pan

### Generating Screenshots

High-quality screenshots for social media and previews:

```bash
# Generate screenshot with default settings (1920x1080)
python manage.py generate_knowledge_graph_screenshot

# Generate high-resolution screenshot (2400x1600, 2x DPI)
python manage.py generate_knowledge_graph_screenshot \
  --width 2400 \
  --height 1600 \
  --device-scale-factor 2.0 \
  --quality 100

# Generate with transparent background
python manage.py generate_knowledge_graph_screenshot \
  --transparent

# Screenshot production site instead of localhost
python manage.py generate_knowledge_graph_screenshot \
  --url https://aaronspindler.com
```

**Command Options**:
- `--width`: Screenshot width in pixels (default: 1920)
- `--height`: Screenshot height in pixels (default: 1080)
- `--device-scale-factor`: Device pixel ratio for high-DPI (default: 2.0)
- `--quality`: JPEG quality 1-100 (default: 90)
- `--transparent`: Use transparent background instead of white
- `--url`: URL to screenshot (default: http://localhost:8000)

**Automated Screenshots**:
Screenshots are automatically generated daily at 4 AM UTC via Celery Beat, capturing the production site.

### Rebuilding the Graph Cache

The graph cache automatically invalidates when blog posts change, but you can manually rebuild:

```bash
# Rebuild graph cache
python manage.py rebuild_knowledge_graph

# Force rebuild even if no changes detected
python manage.py rebuild_knowledge_graph --force

# Rebuild and test API endpoint
python manage.py rebuild_knowledge_graph --test-api
```

**When to rebuild**:
- After adding new blog posts
- After editing existing blog posts (especially links)
- After template modifications
- If graph appears out of sync

## API Endpoints

### Get Full Graph Data

```http
GET /api/knowledge-graph/
```

**Query Parameters**:
- `refresh`: Force cache refresh (values: `true`, `false`)

**Response**:
```json
{
  "status": "success",
  "data": {
    "nodes": [
      {
        "id": "post-slug",
        "label": "Post Title",
        "category": "tech",
        "url": "/b/tech/post-slug/",
        "type": "post"
      },
      {
        "id": "category-tech",
        "label": "Tech",
        "category": "tech",
        "url": "/b/tech/",
        "type": "category"
      }
    ],
    "edges": [
      {
        "source": "post-1",
        "target": "post-2",
        "type": "internal"
      },
      {
        "source": "post-1",
        "target": "category-tech",
        "type": "category"
      }
    ]
  },
  "metadata": {
    "nodes_count": 50,
    "edges_count": 75,
    "has_errors": false,
    "cache_hit": true
  }
}
```

### Get Post-Specific Graph

```http
POST /api/knowledge-graph/
Content-Type: application/json

{
  "operation": "post_graph",
  "template_name": "0001_Post_Name",
  "depth": 2
}
```

**Request Body**:
- `operation`: Operation type (`post_graph`, `full_graph`, `refresh`)
- `template_name`: Blog post filename without extension
- `depth`: Connection depth (1 = direct links, 2 = links of links)

**Response**: Same format as GET endpoint

### Get Graph Screenshot

```http
GET /api/knowledge-graph/screenshot/
```

**Response**: PNG image (latest cached screenshot)

**Cache Behavior**:
- Returns latest screenshot from database
- Screenshots regenerated daily via Celery
- 404 if no screenshot exists

## Configuration

### Cache Settings

Configure cache timeout in `config/settings.py`:

```python
# Knowledge graph cache timeout (seconds)
KNOWLEDGE_GRAPH_CACHE_TIMEOUT = 1200  # 20 minutes
```

### Force Simulation Parameters

Adjust force simulation parameters in `blog/static/js/knowledge-graph.js`:

```javascript
// Node count thresholds
const SMALL_GRAPH_THRESHOLD = 30;
const MEDIUM_GRAPH_THRESHOLD = 60;

// Force parameters
const forceParams = {
  charge: nodeCount < 30 ? -300 : nodeCount < 60 ? -200 : -100,
  linkDistance: nodeCount < 30 ? 100 : nodeCount < 60 ? 80 : 60,
  collisionRadius: 1.0
};
```

### Screenshot Settings

Configure Playwright screenshot parameters:

```python
# In blog/management/commands/generate_knowledge_graph_screenshot.py
DEFAULT_WIDTH = 1920
DEFAULT_HEIGHT = 1080
DEFAULT_DEVICE_SCALE_FACTOR = 2.0
DEFAULT_QUALITY = 90
```

## Performance Optimization

### Caching Strategy

**Multi-Level Caching**:
1. **Redis Cache**: 20-minute timeout for graph data
2. **File Modification Tracking**: Cache invalidates when templates change
3. **Database Cache**: Screenshots stored in database

**Cache Keys**:
- `knowledge_graph:full_graph` - Full graph data
- `knowledge_graph:post:{template_name}` - Post-specific graph data

### File Modification Tracking

The system tracks blog post template modification times:

```python
# Get latest modification time for all blog posts
latest_mtime = get_latest_blog_post_mtime()

# Compare with cached mtime
if cache_mtime < latest_mtime:
    # Invalidate cache and rebuild
    rebuild_graph()
```

### Graph Rendering Optimization

**Client-Side**:
- Progressive rendering (nodes → edges → labels)
- Canvas fallback for large graphs (SVG for < 100 nodes)
- Debounced zoom/pan events
- Simplified rendering during interactions

**Server-Side**:
- Playwright headless mode for screenshots
- Viewport optimization (high DPI, hardware acceleration)
- Parallel link parsing
- Cached graph data reuse

## Troubleshooting

### Graph Not Updating

**Symptoms**: Graph doesn't reflect recent blog post changes

**Solutions**:
1. Clear cache: `python manage.py clear_cache`
2. Rebuild graph: `python manage.py rebuild_knowledge_graph --force`
3. Check template modification times are updating
4. Restart Redis if cache seems stuck

### Screenshot Generation Failing

**Symptoms**: `generate_knowledge_graph_screenshot` command fails

**Solutions**:
1. Install Playwright browsers: `playwright install chromium`
2. Check URL is accessible: `curl http://localhost:8000/knowledge-graph/`
3. Ensure server is running (for localhost screenshots)
4. Check Playwright logs in command output
5. Try with `--url` parameter pointing to production site

### Performance Issues

**Symptoms**: Graph loads slowly or rendering is laggy

**Solutions**:
1. Check graph size: Graphs with 100+ nodes may be slow
2. Reduce connection depth in API calls
3. Use canvas rendering instead of SVG (modify JS)
4. Increase cache timeout to reduce rebuilds
5. Consider pagination for very large graphs

### Missing Connections

**Symptoms**: Expected links between posts not showing

**Solutions**:
1. Verify internal links use correct URL format (relative paths)
2. Check link targets exist as blog posts
3. Rebuild graph: `python manage.py rebuild_knowledge_graph`
4. Inspect link parsing in `blog/knowledge_graph.py`
5. Check browser console for graph data structure

### Screenshot Quality Issues

**Symptoms**: Screenshots are blurry or pixelated

**Solutions**:
1. Increase `--device-scale-factor` (try 2.0 or 3.0)
2. Increase `--width` and `--height` parameters
3. Set `--quality` to 100 for maximum JPEG quality
4. Consider PNG format instead of JPEG (modify command)
5. Ensure Chromium is using hardware acceleration

## Development

### Adding New Node Types

To add new node types beyond posts and categories:

1. **Update LinkParser** in `blog/knowledge_graph.py`:
   ```python
   def parse_links(self, content):
       # Add new link pattern matching
       if self.is_new_type_link(url):
           self.new_type_links.append(url)
   ```

2. **Update GraphBuilder**:
   ```python
   def add_new_type_nodes(self):
       for item in new_items:
           self.nodes.append({
               'id': f'new-{item.id}',
               'label': item.name,
               'type': 'new_type',
               'url': item.get_absolute_url()
           })
   ```

3. **Update D3.js Visualization**:
   ```javascript
   const nodeColors = {
       post: '#3498db',
       category: '#e74c3c',
       new_type: '#2ecc71'  // Add new color
   };
   ```

### Customizing Visualization

Modify `blog/static/js/knowledge-graph.js`:

```javascript
// Change node sizes
const nodeRadius = d => d.type === 'post' ? 10 : 15;

// Change link styles
const linkWidth = d => d.type === 'internal' ? 2 : 1;

// Add custom interactions
node.on('contextmenu', (event, d) => {
    // Custom right-click behavior
});
```

## Related Documentation

- [Blog System](blog-system.md) - Blog post structure and creation
- [Management Commands](../commands.md) - Command reference
- [API Reference](../api.md) - Complete API documentation
- [Architecture](../architecture.md) - Technical implementation details
