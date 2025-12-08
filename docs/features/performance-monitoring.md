# Performance Monitoring (Lighthouse)

## Overview

Automated performance monitoring using Google Lighthouse to track key web vitals and ensure optimal site performance. The system runs nightly audits and provides historical trends with badge integration for README files.

## Features

- **Automated Audits**: Nightly Lighthouse audits via Celery Beat (2 AM UTC)
- **4 Key Metrics**: Performance, Accessibility, Best Practices, SEO
- **Historical Tracking**: 30-day trend visualization
- **Badge Endpoint**: shields.io integration for README badges
- **Detailed Reports**: Full Lighthouse JSON reports stored
- **Alert System**: Optional notifications for score drops
- **Manual Audits**: On-demand audit execution
- **Multi-URL Support**: Audit multiple pages

## Metrics Tracked

### Performance Score (0-100)

Measures page load speed and runtime performance:
- First Contentful Paint (FCP)
- Largest Contentful Paint (LCP)
- Total Blocking Time (TBT)
- Cumulative Layout Shift (CLS)
- Speed Index

**Target**: > 90

### Accessibility Score (0-100)

Measures accessibility for users with disabilities:
- ARIA attributes
- Color contrast
- Alt text for images
- Keyboard navigation
- Screen reader compatibility

**Target**: > 95

### Best Practices Score (0-100)

Measures adherence to web development best practices:
- HTTPS usage
- Console errors
- Deprecated APIs
- Security vulnerabilities
- Browser compatibility

**Target**: > 95

### SEO Score (0-100)

Measures search engine optimization:
- Meta descriptions
- Title tags
- Mobile-friendly design
- Crawlability
- Structured data

**Target**: > 95

## Usage

### Running Manual Audits

```bash
# Audit the default URL (from settings)
python manage.py run_lighthouse_audit

# Audit a specific URL
python manage.py run_lighthouse_audit --url https://example.com

# Audit multiple pages
python manage.py run_lighthouse_audit --url https://example.com/
python manage.py run_lighthouse_audit --url https://example.com/blog/
python manage.py run_lighthouse_audit --url https://example.com/about/
```

**Command Options**:
- `--url`: URL to audit (defaults to site URL from settings)

### Automated Audits

Audits run automatically via Celery Beat:

**Schedule**: Daily at 2 AM UTC

**Setup**:
```bash
# Configure periodic tasks
python manage.py setup_periodic_tasks

# Start Celery Beat scheduler
celery -A config beat --loglevel=info

# Start Celery worker to process tasks
celery -A config worker --loglevel=info
```

**Monitoring with Flower**:
```bash
# Start Flower dashboard
celery -A config flower

# View at http://localhost:5555
```

### Viewing Results

**Web Interface**:
Visit `/lighthouse/history/` to view historical trends

**Django Admin**:
Navigate to `/admin/utils/lighthouseresult/` for detailed results

**API Badge**:
Access `/api/lighthouse/badge/` for shields.io badge data

## LighthouseResult Model

### Fields

**Scores**:
- `performance_score`: Performance score (0-100)
- `accessibility_score`: Accessibility score (0-100)
- `best_practices_score`: Best practices score (0-100)
- `seo_score`: SEO score (0-100)

**Metadata**:
- `url`: URL audited
- `created_at`: Audit timestamp
- `report_json`: Full Lighthouse JSON report

**Computed Fields**:
- `overall_score`: Average of all 4 scores

### Querying Results

```python
from utils.models import LighthouseResult
from datetime import datetime, timedelta

# Get latest result
latest = LighthouseResult.objects.latest('created_at')
print(f"Performance: {latest.performance_score}")
print(f"Accessibility: {latest.accessibility_score}")
print(f"Best Practices: {latest.best_practices_score}")
print(f"SEO: {latest.seo_score}")

# Get results from last 30 days
thirty_days_ago = datetime.now() - timedelta(days=30)
recent_results = LighthouseResult.objects.filter(
    created_at__gte=thirty_days_ago
).order_by('-created_at')

# Calculate average scores
from django.db.models import Avg
averages = LighthouseResult.objects.aggregate(
    avg_performance=Avg('performance_score'),
    avg_accessibility=Avg('accessibility_score'),
    avg_best_practices=Avg('best_practices_score'),
    avg_seo=Avg('seo_score'),
)

# Find score drops
results = LighthouseResult.objects.order_by('-created_at')[:2]
if len(results) == 2:
    current, previous = results
    perf_drop = previous.performance_score - current.performance_score
    if perf_drop > 5:
        print(f"Performance dropped by {perf_drop} points!")
```

## Badge Integration

### shields.io Badge

Display current Lighthouse scores in your README:

```markdown
![Lighthouse Scores](https://img.shields.io/endpoint?url=https://yourdomain.com/api/lighthouse/badge/)
```

### Badge Endpoint

```http
GET /api/lighthouse/badge/
```

**Response (shields.io format)**:
```json
{
  "schemaVersion": 1,
  "label": "lighthouse",
  "message": "95/98/100/100",
  "color": "brightgreen"
}
```

**Message Format**: `Performance/Accessibility/BestPractices/SEO`

**Color Coding**:
- **brightgreen**: Overall average ≥ 95
- **green**: Overall average ≥ 90
- **yellow**: Overall average ≥ 80
- **orange**: Overall average ≥ 70
- **red**: Overall average < 70

### Custom Badge

Create a custom badge URL:

```markdown
![Performance](https://img.shields.io/badge/lighthouse-95%2F98%2F100%2F100-brightgreen)
```

## Celery Configuration

### Task Definition

```python
# utils/tasks.py
from celery import shared_task
from django.conf import settings
import subprocess
import json

@shared_task
def run_lighthouse_audit_task(url=None):
    """Run Lighthouse audit via Celery."""
    if url is None:
        url = settings.SITE_URL

    # Run Lighthouse CLI
    cmd = [
        'lighthouse',
        url,
        '--output=json',
        '--output-path=stdout',
        '--chrome-flags="--headless --no-sandbox"',
        '--quiet',
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    report = json.loads(result.stdout)

    # Save result
    from utils.models import LighthouseResult
    LighthouseResult.objects.create(
        url=url,
        performance_score=int(report['categories']['performance']['score'] * 100),
        accessibility_score=int(report['categories']['accessibility']['score'] * 100),
        best_practices_score=int(report['categories']['best-practices']['score'] * 100),
        seo_score=int(report['categories']['seo']['score'] * 100),
        report_json=report,
    )

    return f"Audit completed for {url}"
```

### Periodic Task Setup

```python
# Management command: setup_periodic_tasks
from django_celery_beat.models import PeriodicTask, CrontabSchedule

# Create schedule: Daily at 2 AM UTC
schedule, _ = CrontabSchedule.objects.get_or_create(
    minute='0',
    hour='2',
    day_of_week='*',
    day_of_month='*',
    month_of_year='*',
)

# Create task
PeriodicTask.objects.get_or_create(
    name='Daily Lighthouse Audit',
    task='utils.tasks.run_lighthouse_audit_task',
    crontab=schedule,
)
```

## Lighthouse CLI Configuration

### Installation

```bash
# Install Lighthouse globally
npm install -g lighthouse

# Or via package.json
npm install --save-dev lighthouse

# Verify installation
lighthouse --version
```

### Configuration File

Create `lighthouserc.json` for custom configuration:

```json
{
  "ci": {
    "collect": {
      "numberOfRuns": 1,
      "settings": {
        "preset": "desktop",
        "throttling": {
          "rttMs": 40,
          "throughputKbps": 10240,
          "cpuSlowdownMultiplier": 1
        }
      }
    },
    "assert": {
      "assertions": {
        "categories:performance": ["error", {"minScore": 0.9}],
        "categories:accessibility": ["error", {"minScore": 0.95}],
        "categories:best-practices": ["error", {"minScore": 0.95}],
        "categories:seo": ["error", {"minScore": 0.95}]
      }
    }
  }
}
```

### CLI Options

```bash
# Basic audit
lighthouse https://example.com

# Desktop configuration
lighthouse https://example.com --preset=desktop

# Mobile configuration
lighthouse https://example.com --preset=mobile

# Specific categories
lighthouse https://example.com --only-categories=performance,accessibility

# Custom output
lighthouse https://example.com --output=json --output-path=./report.json

# Headless Chrome
lighthouse https://example.com --chrome-flags="--headless --no-sandbox"
```

## Historical Tracking

### 30-Day Trend View

```python
# views.py
from django.shortcuts import render
from utils.models import LighthouseResult
from datetime import datetime, timedelta

def lighthouse_history(request):
    """Display 30-day Lighthouse score trends."""
    thirty_days_ago = datetime.now() - timedelta(days=30)

    results = LighthouseResult.objects.filter(
        created_at__gte=thirty_days_ago
    ).order_by('created_at')

    # Format data for charts
    chart_data = {
        'labels': [r.created_at.strftime('%Y-%m-%d') for r in results],
        'performance': [r.performance_score for r in results],
        'accessibility': [r.accessibility_score for r in results],
        'best_practices': [r.best_practices_score for r in results],
        'seo': [r.seo_score for r in results],
    }

    return render(request, 'lighthouse/history.html', {
        'results': results,
        'chart_data': chart_data,
    })
```

### Chart Visualization

Use Chart.js to visualize trends:

```html
<canvas id="lighthouseChart"></canvas>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
const ctx = document.getElementById('lighthouseChart').getContext('2d');
const chart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: {{ chart_data.labels|safe }},
        datasets: [
            {
                label: 'Performance',
                data: {{ chart_data.performance|safe }},
                borderColor: 'rgb(75, 192, 192)',
            },
            {
                label: 'Accessibility',
                data: {{ chart_data.accessibility|safe }},
                borderColor: 'rgb(54, 162, 235)',
            },
            {
                label: 'Best Practices',
                data: {{ chart_data.best_practices|safe }},
                borderColor: 'rgb(255, 206, 86)',
            },
            {
                label: 'SEO',
                data: {{ chart_data.seo|safe }},
                borderColor: 'rgb(153, 102, 255)',
            },
        ]
    },
    options: {
        scales: {
            y: {
                beginAtZero: true,
                max: 100
            }
        }
    }
});
</script>
```

## Alert System

### Score Drop Detection

```python
from utils.models import LighthouseResult, Notification

def check_score_drops():
    """Check for significant score drops and send alerts."""
    results = LighthouseResult.objects.order_by('-created_at')[:2]

    if len(results) < 2:
        return

    current, previous = results

    # Check each metric
    metrics = [
        ('Performance', current.performance_score, previous.performance_score),
        ('Accessibility', current.accessibility_score, previous.accessibility_score),
        ('Best Practices', current.best_practices_score, previous.best_practices_score),
        ('SEO', current.seo_score, previous.seo_score),
    ]

    for name, current_score, previous_score in metrics:
        drop = previous_score - current_score
        if drop >= 5:  # Alert on 5+ point drop
            Notification.send_email(
                subject=f'Lighthouse Alert: {name} Score Drop',
                message=f'{name} score dropped from {previous_score} to {current_score} ({drop} points)',
                recipient='admin@example.com',
            )
```

### Integration with Celery Task

```python
@shared_task
def run_lighthouse_audit_with_alerts(url=None):
    """Run audit and check for score drops."""
    # Run audit
    run_lighthouse_audit_task(url)

    # Check for drops
    check_score_drops()
```

## Troubleshooting

### Lighthouse Command Not Found

**Solutions**:
1. Install Lighthouse: `npm install -g lighthouse`
2. Verify PATH includes npm global bin: `npm config get prefix`
3. Check installation: `lighthouse --version`
4. Try local installation: `npm install --save-dev lighthouse`

### Audit Fails with Chrome Error

**Solutions**:
1. Install Chrome/Chromium: `apt-get install chromium-browser`
2. Add flags: `--chrome-flags="--headless --no-sandbox --disable-dev-shm-usage"`
3. Increase system resources (RAM, CPU)
4. Check Chrome process limits
5. Run as non-root user (security)

### Celery Task Not Running

**Solutions**:
1. Check Celery worker is running: `celery -A config worker`
2. Check Celery Beat is running: `celery -A config beat`
3. Verify periodic task exists: Check Django admin
4. Check task logs in Flower dashboard
5. Test task manually: `run_lighthouse_audit_task.delay()`

### Scores Lower Than Expected

**Solutions**:
1. Check audit conditions (network, server load)
2. Review full Lighthouse report JSON
3. Compare desktop vs mobile scores
4. Check for recent code changes
5. Verify CDN/caching is working

### Badge Not Updating

**Solutions**:
1. Check latest audit ran successfully
2. Clear cache: `python manage.py clear_cache`
3. Verify badge endpoint accessible: `/api/lighthouse/badge/`
4. Check shields.io cache (may take time to update)
5. Force refresh badge URL with query param: `?refresh=timestamp`

## Configuration

### Django Settings

```python
# Lighthouse configuration
LIGHTHOUSE_CLI_PATH = 'lighthouse'  # or '/usr/local/bin/lighthouse'
LIGHTHOUSE_CHROME_FLAGS = '--headless --no-sandbox'
LIGHTHOUSE_AUDIT_URL = 'https://yourdomain.com'

# Alert thresholds
LIGHTHOUSE_ALERT_THRESHOLD = 5  # Points drop to trigger alert
LIGHTHOUSE_ALERT_EMAIL = 'admin@example.com'

# Result retention
LIGHTHOUSE_RETENTION_DAYS = 90  # Keep results for 90 days
```

### Environment Variables

```bash
# Lighthouse configuration
LIGHTHOUSE_AUDIT_URL=https://yourdomain.com
LIGHTHOUSE_ALERT_EMAIL=admin@example.com
LIGHTHOUSE_RETENTION_DAYS=90
```

## Performance Optimizations

The following optimizations have been implemented to improve Lighthouse Performance scores:

### Response Compression

- **GZipMiddleware**: Compresses dynamic HTML responses (static files already compressed by WhiteNoise)

### Caching Strategy

- **Homepage HTTP Caching**: `@cache_page(300)` decorator for 5-minute full-page caching
- **Data-Level Caching**: Blog posts (1hr), projects (24hr), books (24hr), photo albums (24hr)

### JavaScript Optimization

- **Self-Hosted D3.js**: Moved from CDN to local hosting (`static/js/vendor/d3.v7.min.js`) for:
  - 1-year cache headers via WhiteNoise
  - Elimination of external DNS/TLS overhead
  - Better control over versioning

- **Lazy Loading Knowledge Graph**: D3.js and knowledge graph scripts load via Intersection Observer only when scrolled into view (200px rootMargin for preloading)

### Font Optimization

- **Reduced Font Preloads**: Only the regular weight font is preloaded; medium and bold weights load on demand via `font-display: swap`

### Resource Hints Cleanup

- **Removed D3.js Preconnect**: Since D3.js is now self-hosted, removed unnecessary preconnect and dns-prefetch directives

### Expected Impact

| Optimization | LCP | TBT | FCP |
|--------------|-----|-----|-----|
| GZipMiddleware | + | + | ++ |
| Homepage caching | +++ | + | ++ |
| Self-hosted D3.js | ++ | + | + |
| Lazy load knowledge graph | +++ | ++ | ++ |
| Reduced font preloads | ++ | + | ++ |

## Related Documentation

- [Management Commands](../commands.md) - run_lighthouse_audit, setup_periodic_tasks
- [API Reference](../api.md) - Badge endpoint documentation
- [Deployment](../deployment.md) - Production Lighthouse setup
- [Maintenance](../maintenance.md) - Result cleanup and monitoring
