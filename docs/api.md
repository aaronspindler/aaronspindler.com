# API Reference

## Overview

RESTful API endpoints for accessing knowledge graph data, search functionality, performance metrics, and photo management.

## Base URL

```
Production: https://aaronspindler.com
Development: http://localhost:8000
```

## Authentication

Most API endpoints are publicly accessible. Authenticated endpoints require Django session authentication or token authentication (if configured).

## Knowledge Graph API

### Get Full Graph Data

Retrieve the complete knowledge graph with all nodes and edges.

**Endpoint**: `GET /api/knowledge-graph/`

**Query Parameters**:
- `refresh` (optional): Force cache refresh
  - Values: `true`, `false`
  - Default: `false`

**Request Example**:
```bash
# Get cached graph
curl https://aaronspindler.com/api/knowledge-graph/

# Force refresh cache
curl https://aaronspindler.com/api/knowledge-graph/?refresh=true
```

**Response**: `200 OK`
```json
{
  "status": "success",
  "data": {
    "nodes": [
      {
        "id": "0001-django-tutorial",
        "label": "Django Tutorial",
        "category": "tech",
        "url": "/b/tech/django-tutorial/",
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
        "source": "0001-django-tutorial",
        "target": "0002-python-guide",
        "type": "internal"
      },
      {
        "source": "0001-django-tutorial",
        "target": "category-tech",
        "type": "category"
      }
    ]
  },
  "metadata": {
    "nodes_count": 50,
    "edges_count": 75,
    "has_errors": false,
    "cache_hit": true,
    "generated_at": "2025-01-15T10:30:00Z"
  }
}
```

**Node Fields**:
- `id`: Unique node identifier
- `label`: Display name
- `category`: Post category or null
- `url`: Relative or absolute URL
- `type`: Node type (`post`, `category`)

**Edge Fields**:
- `source`: Source node ID
- `target`: Target node ID
- `type`: Edge type (`internal`, `category`)

**Error Response**: `500 Internal Server Error`
```json
{
  "status": "error",
  "error": "Failed to build knowledge graph",
  "details": "Error message here"
}
```

---

### Get Post-Specific Graph

Retrieve graph data for a specific post and its connections.

**Endpoint**: `POST /api/knowledge-graph/`

**Content-Type**: `application/json`

**Request Body**:
```json
{
  "operation": "post_graph",
  "template_name": "0001_Django_Tutorial",
  "depth": 2
}
```

**Fields**:
- `operation`: Operation type
  - Values: `post_graph`, `full_graph`, `refresh`
- `template_name`: Blog post filename (without extension)
- `depth` (optional): Connection depth
  - `1`: Direct links only
  - `2`: Links of links
  - Default: `1`

**Request Example**:
```bash
curl -X POST https://aaronspindler.com/api/knowledge-graph/ \
  -H "Content-Type: application/json" \
  -d '{
    "operation": "post_graph",
    "template_name": "0001_Django_Tutorial",
    "depth": 2
  }'
```

**Response**: Same format as GET endpoint, filtered to post-specific subgraph.

---

### Get Knowledge Graph Screenshot

Retrieve the latest cached screenshot of the knowledge graph.

**Endpoint**: `GET /api/knowledge-graph/screenshot/`

**Request Example**:
```bash
curl https://aaronspindler.com/api/knowledge-graph/screenshot/ \
  -o knowledge-graph.png
```

**Response**: `200 OK`
- **Content-Type**: `image/png`
- **Body**: PNG image binary data

**Error Response**: `404 Not Found`
```json
{
  "error": "No screenshot available"
}
```

**Cache Behavior**:
- Returns latest screenshot from database
- Screenshots regenerated daily at 4 AM UTC
- Use `If-Modified-Since` header for conditional requests

---

## Search API

### Autocomplete Search

Get search suggestions as user types.

**Endpoint**: `GET /api/search/autocomplete/`

**Query Parameters**:
- `q` (required): Search query
  - Minimum: 2 characters
  - Maximum: 200 characters

**Request Example**:
```bash
# Search for "django"
curl "https://aaronspindler.com/api/search/autocomplete/?q=django"

# URL-encoded query
curl "https://aaronspindler.com/api/search/autocomplete/?q=full%20text%20search"
```

**Response**: `200 OK`
```json
{
  "suggestions": [
    {
      "title": "Django Full-Text Search Tutorial",
      "type": "Blog Post",
      "url": "/b/tech/django-search-tutorial/",
      "category": "tech",
      "match_type": "title",
      "external": false
    },
    {
      "title": "Django Logo",
      "type": "Photo",
      "url": "/photos/123/",
      "match_type": "title",
      "external": false
    },
    {
      "title": "California Photos",
      "type": "Photo Album",
      "url": "/photos/album/california/",
      "match_type": "description",
      "external": false
    },
    {
      "title": "Django Project",
      "type": "Project",
      "url": "https://github.com/user/django-project",
      "match_type": "title",
      "external": true
    },
    {
      "title": "Two Scoops of Django",
      "type": "Book",
      "url": "https://www.amazon.com/...",
      "match_type": "title",
      "external": true
    }
  ]
}
```

**Suggestion Fields**:
- `title`: Content title
- `type`: Content type (`Blog Post`, `Photo`, `Photo Album`, `Project`, `Book`)
- `url`: Link to content (relative or absolute)
- `category`: Content category (if applicable)
- `match_type`: Which field matched (`title`, `description`, `content`)
- `external`: Boolean indicating external link

**Empty Query Response**: `200 OK`
```json
{
  "suggestions": []
}
```

**Error Response**: `400 Bad Request`
```json
{
  "error": "Query parameter 'q' is required"
}
```

**Performance**:
- Sub-100ms response time
- Results limited to 10 suggestions
- Cached for 5 minutes

---

## Lighthouse API

### Get Performance Badge

Get shields.io-compatible badge data for current Lighthouse scores.

**Endpoint**: `GET /api/lighthouse/badge/`

**Request Example**:
```bash
curl https://aaronspindler.com/api/lighthouse/badge/
```

**Response**: `200 OK`
```json
{
  "schemaVersion": 1,
  "label": "lighthouse",
  "message": "95/98/100/100",
  "color": "brightgreen"
}
```

**Fields**:
- `schemaVersion`: shields.io schema version (always 1)
- `label`: Badge label text
- `message`: Score display (Performance/Accessibility/BestPractices/SEO)
- `color`: Badge color based on overall score

**Color Coding**:
- `brightgreen`: Overall average ≥ 95
- `green`: Overall average ≥ 90
- `yellow`: Overall average ≥ 80
- `orange`: Overall average ≥ 70
- `red`: Overall average < 70

**Usage in README**:
```markdown
![Lighthouse Scores](https://img.shields.io/endpoint?url=https://aaronspindler.com/api/lighthouse/badge/)
```

**Error Response**: `404 Not Found`
```json
{
  "schemaVersion": 1,
  "label": "lighthouse",
  "message": "no data",
  "color": "lightgrey"
}
```

---

### Get Lighthouse History

Retrieve historical Lighthouse audit results.

**Endpoint**: `GET /lighthouse/history/`

**Note**: This is an HTML view, not JSON API. For programmatic access, query the `LighthouseResult` model directly.

**Query Parameters**:
- `days` (optional): Number of days of history
  - Default: `30`
  - Maximum: `365`

**Request Example**:
```bash
# View last 30 days
curl https://aaronspindler.com/lighthouse/history/

# View last 90 days
curl https://aaronspindler.com/lighthouse/history/?days=90
```

**Response**: HTML page with chart visualization

---

## Photo API

### Get Album Detail

Retrieve photo album details with all photos.

**Endpoint**: `GET /photos/album/<slug>/`

**URL Parameters**:
- `slug`: Album slug (URL-friendly identifier)

**Request Example**:
```bash
curl https://aaronspindler.com/photos/album/california-trip-2025/
```

**Response**: HTML page with album details and photo gallery

**Access Control**:
- Public albums: Accessible to all
- Private albums: Requires authentication or password

---

### Get Album Download Status

Check status of album zip file generation.

**Endpoint**: `GET /photos/album/<slug>/download/status/`

**URL Parameters**:
- `slug`: Album slug

**Request Example**:
```bash
curl https://aaronspindler.com/photos/album/california-trip-2025/download/status/
```

**Response**: `200 OK`

**Status: Ready**
```json
{
  "status": "ready",
  "url": "https://s3.amazonaws.com/bucket/albums/california-trip-2025.zip",
  "size": 157286400,
  "updated_at": "2025-01-15T10:30:00Z",
  "photo_count": 25
}
```

**Status: Generating**
```json
{
  "status": "generating",
  "message": "Zip file is being generated. Please check back in a few minutes."
}
```

**Status: Error**
```json
{
  "status": "error",
  "error": "Failed to generate zip file",
  "details": "Error message here"
}
```

**Status: Disabled**
```json
{
  "status": "disabled",
  "message": "Downloads are not enabled for this album"
}
```

**Error Response**: `404 Not Found`
```json
{
  "error": "Album not found"
}
```

---

## Blog API

### Get Blog Comments

Retrieve comments for a blog post.

**Endpoint**: `GET /b/<category>/<slug>/comments/`

**URL Parameters**:
- `category`: Blog category (hobbies, personal, projects, reviews, tech)
- `slug`: Post slug

**Query Parameters**:
- `page` (optional): Page number for pagination
  - Default: `1`

**Request Example**:
```bash
curl https://aaronspindler.com/b/tech/django-tutorial/comments/
```

**Response**: `200 OK`
```json
{
  "comments": [
    {
      "id": 1,
      "author_name": "John Doe",
      "author_email": "john@example.com",
      "content": "Great tutorial!",
      "created_at": "2025-01-15T10:30:00Z",
      "is_approved": true,
      "upvotes": 5,
      "downvotes": 0,
      "replies": [
        {
          "id": 2,
          "author_name": "Jane Smith",
          "content": "Thanks for sharing!",
          "created_at": "2025-01-15T11:00:00Z",
          "upvotes": 2,
          "downvotes": 0
        }
      ]
    }
  ],
  "pagination": {
    "page": 1,
    "pages": 3,
    "count": 25
  }
}
```

---

### Submit Blog Comment

Submit a new comment on a blog post.

**Endpoint**: `POST /b/<category>/<slug>/comment/`

**Content-Type**: `application/x-www-form-urlencoded` or `multipart/form-data`

**URL Parameters**:
- `category`: Blog category
- `slug`: Post slug

**Form Data**:
- `content` (required): Comment text
- `author_name` (required): Commenter name
- `author_email` (required): Commenter email
- `parent` (optional): Parent comment ID (for replies)

**Request Example**:
```bash
curl -X POST https://aaronspindler.com/b/tech/django-tutorial/comment/ \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "author_name=John Doe" \
  -d "author_email=john@example.com" \
  -d "content=Great tutorial!"
```

**Response**: `302 Found` (redirect to blog post)

**Success Message**: Comment submitted for moderation

**Error Response**: `400 Bad Request`
```json
{
  "errors": {
    "content": ["This field is required."],
    "author_email": ["Enter a valid email address."]
  }
}
```

**Rate Limiting**:
- 5 comments per hour per IP
- 10 comments per day per IP

---

### Vote on Comment

Upvote or downvote a comment.

**Endpoint**: `POST /b/comment/<id>/vote/`

**Content-Type**: `application/x-www-form-urlencoded`

**URL Parameters**:
- `id`: Comment ID

**Form Data**:
- `vote_type` (required): Vote type
  - Values: `upvote`, `downvote`

**Request Example**:
```bash
curl -X POST https://aaronspindler.com/b/comment/123/vote/ \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "vote_type=upvote"
```

**Response**: `200 OK`
```json
{
  "status": "success",
  "upvotes": 6,
  "downvotes": 0,
  "total_score": 6
}
```

**Error Response**: `400 Bad Request`
```json
{
  "error": "Invalid vote type"
}
```

**Authentication**:
- Requires user authentication (session or token)
- One vote per user per comment
- Users can change their vote

---

## Health Check API

### Application Health

Check application health status.

**Endpoint**: `GET /health/`

**Request Example**:
```bash
curl https://aaronspindler.com/health/
```

**Response**: `200 OK`
```json
{
  "status": "healthy",
  "timestamp": "2025-01-15T10:30:00Z",
  "checks": {
    "database": "ok",
    "cache": "ok"
  },
  "version": "1.0.0"
}
```

**Unhealthy Response**: `503 Service Unavailable`
```json
{
  "status": "unhealthy",
  "timestamp": "2025-01-15T10:30:00Z",
  "checks": {
    "database": "error",
    "cache": "ok"
  },
  "errors": {
    "database": "Connection refused"
  }
}
```

**Use Case**: Monitoring, load balancer health checks

---

## Rate Limiting

### General Limits

- **Default**: 100 requests per minute per IP
- **Authenticated**: 200 requests per minute per user
- **Search API**: 30 requests per minute per IP
- **Comment Submission**: 5 per hour, 10 per day per IP

### Headers

**Rate Limit Headers**:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1642251600
```

**Rate Limit Exceeded**: `429 Too Many Requests`
```json
{
  "error": "Rate limit exceeded",
  "retry_after": 60
}
```

---

## Error Responses

### Standard Error Format

```json
{
  "error": "Error message",
  "details": "Additional details if available",
  "code": "ERROR_CODE"
}
```

### HTTP Status Codes

- `200 OK`: Success
- `201 Created`: Resource created
- `204 No Content`: Success with no response body
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Permission denied
- `404 Not Found`: Resource not found
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error
- `503 Service Unavailable`: Service temporarily unavailable

---

## CORS Configuration

### Allowed Origins

```
Production: https://aaronspindler.com
Development: http://localhost:3000, http://localhost:8000
```

### Allowed Methods

- `GET`
- `POST`
- `PUT`
- `PATCH`
- `DELETE`
- `OPTIONS`

### Allowed Headers

- `Content-Type`
- `Authorization`
- `X-Requested-With`

---

## Pagination

### Query Parameters

- `page`: Page number (1-indexed)
- `per_page`: Items per page (default: 20, max: 100)

### Response Format

```json
{
  "results": [...],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "pages": 5,
    "count": 95,
    "next": "https://aaronspindler.com/api/endpoint/?page=2",
    "previous": null
  }
}
```

---

## Webhooks

### Blog Post Published

**URL**: Configured in Django admin

**Method**: `POST`

**Payload**:
```json
{
  "event": "blog.post.published",
  "timestamp": "2025-01-15T10:30:00Z",
  "data": {
    "title": "New Blog Post",
    "slug": "new-blog-post",
    "category": "tech",
    "url": "https://aaronspindler.com/b/tech/new-blog-post/"
  }
}
```

---

## SDK Examples

### Python

```python
import requests

# Get knowledge graph
response = requests.get('https://aaronspindler.com/api/knowledge-graph/')
graph_data = response.json()

# Search autocomplete
response = requests.get(
    'https://aaronspindler.com/api/search/autocomplete/',
    params={'q': 'django'}
)
suggestions = response.json()['suggestions']

# Get Lighthouse badge
response = requests.get('https://aaronspindler.com/api/lighthouse/badge/')
badge_data = response.json()
```

### JavaScript

```javascript
// Get knowledge graph
fetch('https://aaronspindler.com/api/knowledge-graph/')
  .then(response => response.json())
  .then(data => console.log(data));

// Search autocomplete
const query = 'django';
fetch(`https://aaronspindler.com/api/search/autocomplete/?q=${query}`)
  .then(response => response.json())
  .then(data => console.log(data.suggestions));

// Submit blog comment
fetch('https://aaronspindler.com/b/tech/django-tutorial/comment/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/x-www-form-urlencoded',
  },
  body: new URLSearchParams({
    author_name: 'John Doe',
    author_email: 'john@example.com',
    content: 'Great tutorial!'
  })
});
```

---

## Related Documentation

- [Features](features/) - Feature-specific details
- [Architecture](architecture.md) - API implementation details
- [Commands](commands.md) - Management commands
- [Testing](testing.md) - API testing examples
