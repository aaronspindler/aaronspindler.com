# Request Tracking & Banning System

## Overview

Comprehensive request fingerprinting, security monitoring, and banning system that tracks HTTP requests, detects suspicious activity, provides geolocation data, and enables blocking bad actors by fingerprint, IP, or user agent pattern.

## Features

- **Request Fingerprinting**: Unique identifiers for requests (SHA256 hash of browser characteristics)
- **User Agent Parsing**: Accurate browser, version, OS, and device detection via `user-agents` library
- **IP Geolocation**: Batch processing with ip-api.com integration
- **Suspicious Request Detection**: Automatic bot, scanner, and malicious path detection
- **Banning System**: Block bad actors by fingerprint (cross-IP), IP address, or user agent pattern
- **Privacy-Focused**: Automatically skips local/private IP tracking
- **Configurable Path Exclusions**: Skip tracking for static files, media, admin assets
- **User Association**: Links requests to authenticated users
- **Referrer Tracking**: Capture traffic sources

## Data Models

### TrackedRequest

Stores individual request data with fingerprinting and security analysis.

**Request Information**:
- `ip_address`: ForeignKey to IPAddress model
- `fingerprint_obj`: ForeignKey to Fingerprint model
- `method`: HTTP method (GET, POST, etc.)
- `path`: Requested URL path
- `query_params`: Query string parameters (JSON)
- `referer`: HTTP Referer header
- `is_secure`: HTTPS flag
- `is_ajax`: XMLHttpRequest flag

**Parsed User Agent**:
- `user_agent`: Raw user agent string
- `browser`: Browser name (Chrome, Firefox, Safari, etc.)
- `browser_version`: Browser version number
- `os`: Operating system (Windows, macOS, Linux, etc.)
- `device`: Device type (Desktop, Mobile, Tablet, Bot)

**Headers**:
- `headers`: Relevant HTTP headers (JSON)

**Security**:
- `is_suspicious`: Boolean flag for suspicious requests
- `suspicious_reason`: Why the request was flagged

**Associations**:
- `user`: ForeignKey to User (if authenticated)
- `created_at`: Request timestamp

### Fingerprint

SHA256 hash of browser characteristics (excluding IP) for tracking users across IP changes.

- `hash`: 64-character SHA256 fingerprint
- `first_seen`: When fingerprint was first seen
- `last_seen`: Most recent request with this fingerprint

### IPAddress

Stores unique IP addresses with geolocation data.

- `ip_address`: IPv4 or IPv6 address (unique)
- `geo_data`: JSONField with location details (city, country, lat/lon, ISP, etc.)
- `created_at`, `updated_at`: Timestamps

### Ban

Block bad actors by fingerprint, IP, or user agent pattern.

- `fingerprint`: ForeignKey to Fingerprint (optional)
- `ip_address`: ForeignKey to IPAddress (optional)
- `user_agent_pattern`: Regex pattern to match (optional)
- `reason`: Why the ban was created
- `is_active`: Whether ban is currently active
- `expires_at`: When ban expires (null = permanent)
- `created_by`: User who created the ban
- `created_at`: When ban was created

**Note**: At least one target (fingerprint, IP, or user agent pattern) must be specified.

## Configuration

### Django Settings

```python
# config/settings.py

# Paths to exclude from tracking
REQUEST_TRACKING_EXCLUDE_PATHS = [
    '/static/',
    '/media/',
    '/favicon.ico',
    '/robots.txt',
    '/sitemap.xml',
    '/admin/jsi18n/',
    '/__debug__/',
    '/health/',
]

# Paths that flag requests as suspicious
REQUEST_TRACKING_SUSPICIOUS_PATHS = [
    '/wp-admin',
    '/wp-login',
    '/wp-content',
    '/.env',
    '/.git',
    '/.htaccess',
    '/phpMyAdmin',
    '/phpmyadmin',
    '/pma',
    '/mysql',
    '/admin.php',
    '/config.php',
    '/setup.php',
    '/install.php',
    '/xmlrpc.php',
    '/shell',
    '/cmd',
    '/eval',
]

# User agent patterns that flag requests as suspicious
REQUEST_TRACKING_SUSPICIOUS_USER_AGENTS = [
    'curl',
    'wget',
    'python-requests',
    'scrapy',
    'bot',
    'crawler',
    'spider',
    'nikto',
    'nmap',
    'sqlmap',
    'masscan',
    'zgrab',
]
```

## Middleware

### RequestFingerprintMiddleware

Automatically tracks requests and enforces bans.

**Flow**:
1. Skip excluded paths (static, media, etc.)
2. Skip local/reserved IP addresses
3. Check IP ban → block if banned
4. Generate fingerprint → check fingerprint ban → block if banned
5. Check user agent against ban patterns → block if banned
6. Track the request
7. Flag suspicious requests

**Configuration** (`config/settings.py`):
```python
MIDDLEWARE = [
    # ... other middleware
    'utils.middleware.RequestFingerprintMiddleware',
]
```

**Accessing in Views**:
```python
def my_view(request):
    if hasattr(request, 'tracked_request'):
        tr = request.tracked_request
        print(f"IP: {tr.ip_address.ip_address}")
        print(f"Browser: {tr.browser} {tr.browser_version}")
        print(f"Device: {tr.device}")
        print(f"Fingerprint: {tr.fingerprint_obj.hash[:16]}...")

        # Access geolocation (if available)
        if tr.ip_address.geo_data:
            city = tr.ip_address.geo_data.get('city')
            country = tr.ip_address.geo_data.get('country')
            print(f"Location: {city}, {country}")
```

## Banning System

### Creating Bans

**Via Admin Interface**:
1. Go to Admin → Utils → Bans → Add Ban
2. Select target: Fingerprint, IP Address, and/or User Agent Pattern
3. Enter reason and optional expiration
4. Save

**Via Admin Actions**:
1. Go to Admin → Utils → Fingerprints or IP Addresses
2. Select items to ban
3. Choose "Ban selected fingerprints" or "Ban selected IP addresses" action

**Programmatically**:
```python
from utils.models import Ban, Fingerprint, IPAddress

# Ban a fingerprint
fingerprint = Fingerprint.objects.get(hash='abc123...')
Ban.objects.create(
    fingerprint=fingerprint,
    reason='Automated scraping detected',
    created_by=admin_user,
)

# Ban an IP address
ip = IPAddress.objects.get(ip_address='203.0.113.42')
Ban.objects.create(
    ip_address=ip,
    reason='DDoS source',
    created_by=admin_user,
)

# Ban by user agent pattern (regex)
Ban.objects.create(
    user_agent_pattern=r'BadBot/\d+',
    reason='Known malicious bot',
    created_by=admin_user,
)

# Temporary ban (expires in 24 hours)
from django.utils import timezone
from datetime import timedelta

Ban.objects.create(
    fingerprint=fingerprint,
    reason='Rate limit exceeded',
    expires_at=timezone.now() + timedelta(hours=24),
    created_by=admin_user,
)
```

### Checking Ban Status

```python
from utils.models import Ban, Fingerprint

# Check if fingerprint is banned
fingerprint = Fingerprint.objects.get(hash='abc123...')
active_ban = Ban.objects.filter(
    fingerprint=fingerprint,
    is_active=True,
).filter(
    Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
).first()

if active_ban:
    print(f"Banned: {active_ban.reason}")
```

### Managing Bans

```python
# Deactivate a ban
ban.is_active = False
ban.save()

# Reactivate a ban
ban.is_active = True
ban.save()

# Get all effective bans
from django.db.models import Q
from django.utils import timezone

effective_bans = Ban.objects.filter(
    is_active=True,
).filter(
    Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
)
```

## Suspicious Request Detection

### Detection Criteria

Requests are flagged as suspicious if:

1. **Missing User-Agent header**
2. **Suspicious user agent patterns** (configurable):
   - curl, wget, python-requests, scrapy
   - bot, crawler, spider
   - nikto, nmap, sqlmap, masscan, zgrab
3. **Suspicious paths** (configurable):
   - WordPress paths: /wp-admin, /wp-login, /wp-content
   - Config files: /.env, /.git, /.htaccess
   - Admin panels: /phpMyAdmin, /pma
   - Common attack vectors: /shell, /cmd, /eval
4. **Missing Accept header**
5. **Unknown IP address**

**Note**: Allowed search engine bots (googlebot, bingbot, etc.) are excluded from suspicious detection.

## Querying Request Data

### Common Queries

```python
from utils.models import TrackedRequest, Fingerprint, IPAddress
from django.utils import timezone
from datetime import timedelta

# Get suspicious requests in last 24 hours
suspicious = TrackedRequest.objects.filter(
    is_suspicious=True,
    created_at__gte=timezone.now() - timedelta(hours=24)
)

# Get all requests from specific IP
ip_obj = IPAddress.objects.get(ip_address='203.0.113.42')
ip_requests = TrackedRequest.objects.filter(
    ip_address=ip_obj
).order_by('-created_at')

# Get all requests with a specific fingerprint
fp = Fingerprint.objects.get(hash='abc123...')
fp_requests = TrackedRequest.objects.filter(
    fingerprint_obj=fp
).order_by('-created_at')

# Get requests from specific country
us_requests = TrackedRequest.objects.filter(
    ip_address__geo_data__country='United States'
)

# Get mobile requests
mobile_requests = TrackedRequest.objects.filter(device='Mobile')

# Get requests by browser
chrome_requests = TrackedRequest.objects.filter(browser='Chrome')
```

### Analytics Queries

```python
from django.db.models import Count, Q
from django.db.models.functions import TruncDate

# Requests per day (last 30 days)
thirty_days_ago = timezone.now() - timedelta(days=30)
daily_requests = TrackedRequest.objects.filter(
    created_at__gte=thirty_days_ago
).annotate(
    date=TruncDate('created_at')
).values('date').annotate(
    count=Count('id')
).order_by('date')

# Browser distribution
browser_stats = TrackedRequest.objects.values('browser').annotate(
    count=Count('id')
).order_by('-count')

# Device distribution
device_stats = TrackedRequest.objects.values('device').annotate(
    count=Count('id')
).order_by('-count')

# Top countries
country_stats = TrackedRequest.objects.exclude(
    ip_address__geo_data__isnull=True
).values('ip_address__geo_data__country').annotate(
    count=Count('id')
).order_by('-count')[:10]

# Unique visitors (by fingerprint)
unique_visitors = Fingerprint.objects.count()

# Authenticated vs anonymous requests
auth_stats = TrackedRequest.objects.aggregate(
    authenticated=Count('id', filter=Q(user__isnull=False)),
    anonymous=Count('id', filter=Q(user__isnull=True)),
)
```

## Admin Interface

### IP Addresses

- View all tracked IP addresses with geolocation
- See request count per IP
- Filter by geo data availability
- **Actions**: Ban selected IPs, Delete local/private IPs

### Fingerprints

- View all tracked fingerprints
- See request count per fingerprint
- View first/last seen timestamps
- **Actions**: Ban selected fingerprints
- **Indicators**: Shows if fingerprint is currently banned

### Tracked Requests

- View all tracked requests
- Filter by suspicious status, method, date
- Search by IP, path, user agent, fingerprint
- Click-through to IP and fingerprint details

### Bans

- Create, view, and manage all bans
- Filter by status (effective, expired, inactive)
- **Actions**: Activate/deactivate selected bans
- See ban target (fingerprint, IP, or UA pattern)
- Track who created the ban and when

## Troubleshooting

### Banned User Still Getting Through

1. Check if ban is active: `ban.is_active` should be `True`
2. Check if ban has expired: `ban.expires_at` should be `None` or in the future
3. Verify the ban target matches the request
4. Check middleware order in `settings.py`

### Geolocation Not Working

1. Check internet connectivity to ip-api.com
2. Verify no firewall blocking API requests
3. Check API rate limits (45/min for single, 15/min for batch)
4. Test manually: `curl http://ip-api.com/json/8.8.8.8`

### Local IPs Being Tracked

1. Verify `is_global_ip()` is filtering correctly
2. Run cleanup: `python manage.py remove_local_fingerprints`
3. Check proxy/load balancer headers (X-Forwarded-For)

### High Database Growth

1. Add more paths to `REQUEST_TRACKING_EXCLUDE_PATHS`
2. Ensure indexes are applied for common queries
3. Consider archiving old data periodically

## Related Documentation

- [Architecture](../architecture.md) - System design
- [Maintenance](../maintenance.md) - Monitoring and troubleshooting
- [Deployment](../deployment.md) - Production configuration
