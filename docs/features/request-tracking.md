# Request Tracking & Security

## Overview

Comprehensive request fingerprinting and security monitoring system that tracks all HTTP requests, detects suspicious activity, and provides geolocation data for analytics—all while respecting user privacy.

## Features

- **Request Fingerprinting**: Unique identifiers for requests with/without IP
- **User Agent Parsing**: Browser, OS, and device detection
- **IP Geolocation**: Batch processing with ip-api.com integration
- **Suspicious Request Detection**: Automatic bot and scanner identification
- **Privacy-Focused**: Automatically skips local/private IP tracking
- **User Association**: Links requests to authenticated users
- **Static File Exclusion**: Skips tracking for assets
- **Batch Processing**: Efficient geolocation via management commands
- **Historical Data**: Query request patterns and trends

## RequestFingerprint Model

### Fields

**Request Information**:
- `ip_address`: Client IP address (IPv4 or IPv6)
- `user_agent`: Raw user agent string
- `path`: Requested URL path
- `method`: HTTP method (GET, POST, etc.)
- `referer`: HTTP referer header

**Parsed User Agent**:
- `browser`: Browser name (Chrome, Firefox, Safari, etc.)
- `browser_version`: Browser version
- `os`: Operating system (Windows, macOS, Linux, etc.)
- `device`: Device type (Desktop, Mobile, Tablet)

**Fingerprints**:
- `fingerprint`: Unique hash (includes IP)
- `fingerprint_without_ip`: Hash without IP (for tracking across IPs)

**Geolocation**:
- `geo_data`: JSONField with location details
  - `city`: City name
  - `region`: State/province
  - `country`: Country name
  - `country_code`: ISO country code
  - `lat`, `lon`: GPS coordinates
  - `timezone`: Timezone identifier
  - `isp`: Internet service provider
  - `org`: Organization
  - `as`: Autonomous system

**Security**:
- `is_suspicious`: Boolean flag for suspicious requests
- `user`: ForeignKey to User (if authenticated)

**Timestamps**:
- `created_at`: Request timestamp
- `updated_at`: Last update timestamp

### Fingerprint Generation

The system generates two fingerprints for each request:

**With IP** (tracks specific machines):
```python
fingerprint = md5(f"{ip_address}{user_agent}{browser}{os}{device}").hexdigest()
```

**Without IP** (tracks behavior across IPs):
```python
fingerprint_without_ip = md5(f"{user_agent}{browser}{os}{device}").hexdigest()
```

## Middleware

### RequestFingerprintMiddleware

Automatically tracks all requests via Django middleware:

**Configuration** (`config/settings.py`):
```python
MIDDLEWARE = [
    # ... other middleware
    'utils.middleware.RequestFingerprintMiddleware',
]
```

**Behavior**:
1. Checks if path should be tracked (excludes static files, media)
2. Skips local/private IP addresses (127.0.0.1, 10.x.x.x, 192.168.x.x)
3. Parses user agent string
4. Generates fingerprints
5. Detects suspicious requests
6. Stores RequestFingerprint record (geolocation happens later via command)
7. Attaches fingerprint to request object

**Accessing in Views**:
```python
def my_view(request):
    if hasattr(request, 'fingerprint'):
        fingerprint = request.fingerprint
        print(f"IP: {fingerprint.ip_address}")
        print(f"Browser: {fingerprint.browser}")
        print(f"Device: {fingerprint.device}")

        # Access geolocation (if available)
        if fingerprint.geo_data:
            city = fingerprint.geo_data.get('city')
            country = fingerprint.geo_data.get('country')
            print(f"Location: {city}, {country}")
```

## Local IP Cleanup

Remove historical local IP records:

```bash
# Preview deletions (dry-run)
python manage.py remove_local_fingerprints --dry-run

# Delete local IP records
python manage.py remove_local_fingerprints

# Limit deletions
python manage.py remove_local_fingerprints --limit 100
```

**Use Case**:
- One-time cleanup after deploying local IP filtering
- Remove development/testing records from production
- Clean up historical data

## Suspicious Request Detection

### Detection Criteria

Requests are flagged as suspicious if user agent contains:
- `bot`
- `crawler`
- `spider`
- `scraper`
- `curl`
- `wget`
- `python-requests`
- Scanner patterns (e.g., `nikto`, `nmap`)

### Custom Detection Logic

Extend suspicious request detection:

```python
# utils/middleware.py
def is_suspicious_request(user_agent, path, ip_address):
    """Custom suspicious request detection."""
    user_agent_lower = user_agent.lower()

    # Known bad patterns
    bad_patterns = [
        'bot', 'crawler', 'spider', 'scraper',
        'curl', 'wget', 'python-requests',
        'nikto', 'nmap', 'sqlmap',
    ]

    if any(pattern in user_agent_lower for pattern in bad_patterns):
        return True

    # Check for suspicious paths
    suspicious_paths = [
        '/admin', '/wp-admin', '/.env',
        '/phpMyAdmin', '/.git',
    ]

    if any(path.startswith(sus_path) for sus_path in suspicious_paths):
        return True

    # Check for excessive requests from single IP
    from datetime import timedelta
    from django.utils import timezone
    recent_threshold = timezone.now() - timedelta(minutes=5)
    recent_count = RequestFingerprint.objects.filter(
        ip_address=ip_address,
        created_at__gte=recent_threshold
    ).count()

    if recent_count > 100:  # More than 100 requests in 5 minutes
        return True

    return False
```

## Querying Request Data

### Common Queries

```python
from utils.models import RequestFingerprint
from django.utils import timezone
from datetime import timedelta

# Get suspicious requests in last 24 hours
suspicious = RequestFingerprint.objects.filter(
    is_suspicious=True,
    created_at__gte=timezone.now() - timedelta(hours=24)
)

# Get all requests from specific IP
ip_requests = RequestFingerprint.objects.filter(
    ip_address='203.0.113.42'
).order_by('-created_at')

# Get user's request history
user_requests = RequestFingerprint.objects.filter(
    user=request.user
).order_by('-created_at')

# Get requests from specific country
us_requests = RequestFingerprint.objects.filter(
    geo_data__country='United States'
)

# Get requests from specific city
nyc_requests = RequestFingerprint.objects.filter(
    geo_data__city='New York'
)

# Get mobile requests
mobile_requests = RequestFingerprint.objects.filter(
    device='Mobile'
)

# Get requests by browser
chrome_requests = RequestFingerprint.objects.filter(
    browser='Chrome'
)
```

### Analytics Queries

```python
from django.db.models import Count, Q
from django.db.models.functions import TruncDate

# Requests per day (last 30 days)
thirty_days_ago = timezone.now() - timedelta(days=30)
daily_requests = RequestFingerprint.objects.filter(
    created_at__gte=thirty_days_ago
).annotate(
    date=TruncDate('created_at')
).values('date').annotate(
    count=Count('id')
).order_by('date')

# Browser distribution
browser_stats = RequestFingerprint.objects.values('browser').annotate(
    count=Count('id')
).order_by('-count')

# Device distribution
device_stats = RequestFingerprint.objects.values('device').annotate(
    count=Count('id')
).order_by('-count')

# Top countries
country_stats = RequestFingerprint.objects.exclude(
    geo_data__isnull=True
).values('geo_data__country').annotate(
    count=Count('id')
).order_by('-count')[:10]

# Unique visitors (by fingerprint_without_ip)
unique_visitors = RequestFingerprint.objects.values(
    'fingerprint_without_ip'
).distinct().count()

# Authenticated vs anonymous requests
auth_stats = RequestFingerprint.objects.aggregate(
    authenticated=Count('id', filter=Q(user__isnull=False)),
    anonymous=Count('id', filter=Q(user__isnull=True)),
)
```

## PageVisit Tracking

### Decorator for Views

Track page visits with custom decorator:

```python
from pages.decorators import track_page_visit

@track_page_visit(page_name='home')
def home(request):
    """Home page view with visit tracking."""
    return render(request, 'pages/home.html')

@track_page_visit(page_name='blog_post')
def blog_post(request, slug):
    """Blog post view with visit tracking."""
    post = get_object_or_404(BlogPost, slug=slug)
    return render(request, 'blog/post.html', {'post': post})
```

### PageVisit Model

**Fields**:
- `page_name`: Page identifier
- `url`: Full URL path
- `fingerprint`: ForeignKey to RequestFingerprint
- `user`: ForeignKey to User (if authenticated)
- `created_at`: Visit timestamp

**Querying**:
```python
from pages.models import PageVisit

# Most visited pages
popular_pages = PageVisit.objects.values('page_name').annotate(
    count=Count('id')
).order_by('-count')

# Visits per page
home_visits = PageVisit.objects.filter(page_name='home').count()

# Unique visitors per page
unique_home_visitors = PageVisit.objects.filter(
    page_name='home'
).values('fingerprint__fingerprint_without_ip').distinct().count()
```

## Data Retention

### Cleanup Old Records

```python
# Clean up records older than 90 days
from utils.models import RequestFingerprint
from datetime import timedelta
from django.utils import timezone

ninety_days_ago = timezone.now() - timedelta(days=90)
deleted = RequestFingerprint.objects.filter(
    created_at__lt=ninety_days_ago
).delete()

print(f"Deleted {deleted[0]} old records")
```

### Management Command for Cleanup

```python
# utils/management/commands/cleanup_fingerprints.py
from django.core.management.base import BaseCommand
from utils.models import RequestFingerprint
from datetime import timedelta
from django.utils import timezone

class Command(BaseCommand):
    help = 'Clean up old request fingerprints'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=90)

    def handle(self, *args, **options):
        days = options['days']
        cutoff = timezone.now() - timedelta(days=days)

        deleted, _ = RequestFingerprint.objects.filter(
            created_at__lt=cutoff
        ).delete()

        self.stdout.write(
            self.style.SUCCESS(
                f'Deleted {deleted} records older than {days} days'
            )
        )
```

## Troubleshooting

### Geolocation Not Working

**Solutions**:
1. Check internet connectivity to ip-api.com
2. Verify no firewall blocking API requests
3. Check API rate limits (wait if exceeded)
4. Review command output for error messages
5. Test single IP manually: `curl http://ip-api.com/json/8.8.8.8`

### Too Many Requests Error

**Solutions**:
1. Reduce batch size: `--batch-size 50`
2. Wait 1 minute for rate limit reset
3. Process in smaller batches with `--limit`
4. Space out processing across multiple days

### Local IPs Being Tracked

**Solutions**:
1. Verify middleware is latest version
2. Check IP detection logic in middleware
3. Run cleanup: `python manage.py remove_local_fingerprints`
4. Check for proxy/load balancer forwarding headers

### Suspicious Requests Not Detected

**Solutions**:
1. Review detection logic in middleware
2. Add custom patterns for your use case
3. Check user agent string format
4. Test with known bot user agents
5. Review flagged requests in admin

### High Database Growth

**Solutions**:
1. Implement data retention policy
2. Run cleanup command regularly
3. Add database indexes for common queries
4. Consider archiving old data
5. Exclude more paths from tracking

## Configuration

### Django Settings

```python
# Request fingerprinting configuration
REQUEST_FINGERPRINT_ENABLED = True

# Paths to exclude from tracking
REQUEST_FINGERPRINT_EXCLUDE_PATHS = [
    '/static/',
    '/media/',
    '/favicon.ico',
    '/robots.txt',
    '/sitemap.xml',
]

# Suspicious user agent patterns
SUSPICIOUS_USER_AGENTS = [
    'bot', 'crawler', 'spider', 'scraper',
    'curl', 'wget', 'python-requests',
]

# Data retention
REQUEST_FINGERPRINT_RETENTION_DAYS = 90

# Geolocation
GEOLOCATION_BATCH_SIZE = 100
GEOLOCATION_API_URL = 'http://ip-api.com/batch'
```

## Related Documentation

- [Management Commands](../commands.md) - remove_local_fingerprints
- [Architecture](../architecture.md) - Middleware and security design
- [Maintenance](../maintenance.md) - Data retention and cleanup
- [Deployment](../deployment.md) - Production security configuration
