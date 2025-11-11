# API Endpoint Template

> **Use this template when adding a new API endpoint to `docs/api.md`**

## Template

```markdown
### [HTTP Method] /api/resource/path/

[Brief 1-2 sentence description of what this endpoint does.]

**Authentication**: [Required / Not required]

**Request**:
\```http
[METHOD] /api/resource/path/?param=value HTTP/1.1
Host: aaronspindler.com
Content-Type: application/json
Authorization: Bearer <token>  # If authentication required
\```

**URL Parameters**:
- `id` (integer, required): Description

**Query Parameters**:
- `param1` (string, optional): Description (default: value)
- `param2` (integer, optional): Description
- `filter` (string, optional): Filter by field (choices: option1, option2)
- `limit` (integer, optional): Maximum results (default: 10, max: 100)
- `offset` (integer, optional): Pagination offset (default: 0)

**Request Body** (for POST/PUT/PATCH):
\```json
{
    "field1": "value1",
    "field2": "value2",
    "nested": {
        "sub_field": "value"
    }
}
\```

**Field Descriptions**:
- `field1` (string, required): Description and validation rules
- `field2` (integer, optional): Description (default: 0)

**Success Response** (200 OK):
\```json
{
    "status": "success",
    "data": {
        "id": 123,
        "field1": "value1",
        "field2": "value2",
        "created_at": "2025-01-10T14:30:00Z"
    },
    "meta": {
        "timestamp": "2025-01-10T14:30:00Z"
    }
}
\```

**Response Fields**:
- `status`: Always "success" for successful requests
- `data`: The main response payload
- `data.id`: Resource identifier
- `data.field1`: Description
- `meta`: Optional metadata (pagination, timing, etc.)

**Error Responses**:

**400 Bad Request**:
\```json
{
    "status": "error",
    "error": {
        "code": "INVALID_INPUT",
        "message": "Invalid field1 value",
        "details": {
            "field1": ["This field is required"]
        }
    }
}
\```

**404 Not Found**:
\```json
{
    "status": "error",
    "error": {
        "code": "NOT_FOUND",
        "message": "Resource not found"
    }
}
\```

**500 Internal Server Error**:
\```json
{
    "status": "error",
    "error": {
        "code": "INTERNAL_ERROR",
        "message": "An unexpected error occurred"
    }
}
\```

**Rate Limiting**:
- Limit: X requests per minute
- Headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`

**Caching**:
- Cache-Control: [public/private, max-age=X]
- ETag support: [Yes/No]

**Example Usage**:

**cURL**:
\```bash
# Basic request
curl -X GET "https://aaronspindler.com/api/resource/path/?param=value"

# With authentication
curl -X GET "https://aaronspindler.com/api/resource/path/" \
  -H "Authorization: Bearer YOUR_TOKEN"

# POST with data
curl -X POST "https://aaronspindler.com/api/resource/" \
  -H "Content-Type: application/json" \
  -d '{"field1": "value1", "field2": "value2"}'
\```

**Python**:
\```python
import requests

# GET request
response = requests.get(
    'https://aaronspindler.com/api/resource/path/',
    params={'param': 'value'}
)
data = response.json()

# POST request
response = requests.post(
    'https://aaronspindler.com/api/resource/',
    json={'field1': 'value1', 'field2': 'value2'},
    headers={'Authorization': 'Bearer YOUR_TOKEN'}
)
\```

**JavaScript**:
\```javascript
// Using fetch
const response = await fetch('https://aaronspindler.com/api/resource/path/?param=value');
const data = await response.json();

// POST with fetch
const response = await fetch('https://aaronspindler.com/api/resource/', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer YOUR_TOKEN'
    },
    body: JSON.stringify({
        field1: 'value1',
        field2: 'value2'
    })
});
\```

**Notes**:
- 💡 [Helpful tip about using this endpoint]
- ⚠️ [Important warning or limitation]
- 🔗 See [Feature Name](../features/feature-name.md) for more details

**Related Endpoints**:
- `GET /api/related/endpoint/`: How it relates
- `POST /api/another/endpoint/`: How it relates
```

## Placement in api.md

Add the endpoint to the appropriate section in `docs/api.md`:

- **Blog & Knowledge Graph**: Blog-related endpoints
- **Search**: Search and autocomplete endpoints
- **Photos**: Photo and album endpoints
- **Comments**: Comment-related endpoints
- **Performance Monitoring**: Lighthouse and metrics
- **[New Section]**: Create a new section if needed

## Checklist

Before adding an endpoint to api.md:

- [ ] Endpoint is fully implemented and tested
- [ ] Brief description clearly states purpose
- [ ] Authentication requirements documented
- [ ] All parameters documented with types and constraints
- [ ] Request example provided
- [ ] Success response example with field descriptions
- [ ] All error responses documented (400, 404, 500, etc.)
- [ ] Rate limiting documented (if applicable)
- [ ] Caching behavior documented (if applicable)
- [ ] Example usage in at least 2 languages (cURL + Python/JavaScript)
- [ ] Important notes and warnings included
- [ ] Related endpoints cross-referenced
- [ ] Link to feature documentation

## Example: Complete API Endpoint Documentation

```markdown
### GET /api/search/autocomplete/

Search autocomplete with typo tolerance for blog posts, photos, and albums.

**Authentication**: Not required

**Request**:
\```http
GET /api/search/autocomplete/?q=django&limit=10 HTTP/1.1
Host: aaronspindler.com
\```

**Query Parameters**:
- `q` (string, required): Search query (min 2 characters)
- `limit` (integer, optional): Maximum results (default: 10, max: 20)

**Success Response** (200 OK):
\```json
{
    "query": "django",
    "results": [
        {
            "type": "blog",
            "title": "Building with Django",
            "url": "/blog/tech/building-with-django/",
            "excerpt": "How to build scalable applications...",
            "score": 0.95
        },
        {
            "type": "photo",
            "title": "Django Conference 2024",
            "url": "/photos/123/",
            "thumbnail": "/media/photos/123-thumb.jpg",
            "score": 0.82
        }
    ],
    "total": 2,
    "response_time_ms": 15
}
\```

**Response Fields**:
- `query`: The search query that was processed
- `results`: Array of search results
- `results[].type`: Content type (blog, photo, album)
- `results[].title`: Content title
- `results[].url`: Direct URL to content
- `results[].score`: Relevance score (0-1)
- `total`: Number of results returned
- `response_time_ms`: Query execution time

**Error Responses**:

**400 Bad Request**:
\```json
{
    "error": "Query must be at least 2 characters"
}
\```

**Rate Limiting**:
- Limit: 60 requests per minute per IP
- Headers: `X-RateLimit-Limit: 60`, `X-RateLimit-Remaining: 59`

**Caching**:
- Cache-Control: public, max-age=300 (5 minutes)
- Cached by query string

**Example Usage**:

**cURL**:
\```bash
curl "https://aaronspindler.com/api/search/autocomplete/?q=python&limit=5"
\```

**Python**:
\```python
import requests

response = requests.get(
    'https://aaronspindler.com/api/search/autocomplete/',
    params={'q': 'python', 'limit': 5}
)
results = response.json()['results']
for result in results:
    print(f"{result['type']}: {result['title']} (score: {result['score']})")
\```

**JavaScript**:
\```javascript
// Using fetch
const response = await fetch(
    'https://aaronspindler.com/api/search/autocomplete/?q=python&limit=5'
);
const data = await response.json();
console.log(`Found ${data.total} results`);
\```

**Notes**:
- 💡 Uses PostgreSQL full-text search with trigram similarity for typo tolerance
- 💡 Sub-100ms response time for most queries
- ⚠️ Minimum 2 characters required to prevent performance issues
- 🔗 See [Search System](../features/search.md) for architecture details

**Related Endpoints**:
- `GET /api/blog/posts/`: Full blog post search
- `GET /api/photos/`: Photo search
```

## Tips for Writing Good API Documentation

1. **Be Complete**: Document every parameter, field, and error code

2. **Show Real Examples**: Use actual data structures users will encounter

3. **Multiple Languages**: Always provide cURL + at least one programming language

4. **Error Cases**: Document all possible error responses with examples

5. **Performance Notes**: Mention caching, rate limits, typical response times

6. **Security**: Be clear about authentication and authorization requirements

7. **Versioning**: If API is versioned, document version in endpoint path

8. **Response Fields**: Explain every field in the response, don't assume

---

**Remember**: Good API documentation means developers can integrate without asking questions!
