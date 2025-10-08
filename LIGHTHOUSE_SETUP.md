# Lighthouse Performance Monitoring Setup

This document provides instructions for setting up and using the Lighthouse performance monitoring system.

## Overview

The Lighthouse monitoring system automatically tracks 4 key Lighthouse metrics:
- **Performance** - Page load speed and optimization
- **Accessibility** - Web accessibility standards compliance
- **Best Practices** - Web development best practices
- **SEO** - Search engine optimization

## Features Implemented

✅ **Automated Lighthouse Audits** - Run via management command or Celery task
✅ **Historical Data Storage** - All audit results stored in database
✅ **Badge Display** - Shield.io-style badge in footer showing latest scores (4 metrics)
✅ **History Visualization** - Chart.js-powered trend visualization
✅ **Celery Beat Integration** - Nightly automated audits at 2 AM UTC
✅ **REST API Endpoint** - Badge data in shields.io format

## Quick Start

### 1. Install Dependencies

The npm package `@lhci/cli` has already been added to `package.json`:

```bash
npm install
```

### 2. Run Your First Audit

```bash
# Audit the production site
python manage.py run_lighthouse_audit

# Audit a different URL
python manage.py run_lighthouse_audit --url https://example.com
```

### 3. Set Up Automated Daily Audits

```bash
python manage.py setup_periodic_tasks
```

This configures a Celery Beat task to run audits daily at 2 AM UTC.

### 4. View Results

- **History Page**: Visit `/lighthouse/history/` to see the 30-day trend
- **Badge**: The badge in the footer updates automatically (appears after first audit)
- **Admin Panel**: View all audits in Django admin under "Lighthouse Monitor"

## Automated Audits with Celery Beat

Lighthouse audits are run automatically every day at 2 AM UTC using Celery Beat.

### Setup Periodic Task

Run the setup command to configure the scheduled task:

```bash
python manage.py setup_periodic_tasks
```

This creates a Celery Beat periodic task that:
- Runs nightly at 2 AM UTC
- Executes `lighthouse_monitor.tasks.run_lighthouse_audit`
- Audits https://aaronspindler.com
- Stores results in the database

### Requirements

Make sure Celery Beat is running in production:

```bash
celery -A config beat -l info
```

The task is configured in `lighthouse_monitor/tasks.py` and uses the `run_lighthouse_audit` management command under the hood.

## API Endpoints

### Badge Endpoint

**URL**: `/api/lighthouse/badge/`

**Response** (shields.io endpoint format):
```json
{
  "schemaVersion": 1,
  "label": "lighthouse",
  "message": "95/90/95/100",
  "color": "brightgreen"
}
```

Message format: `Performance/Accessibility/Best Practices/SEO`

Used by shields.io to generate the badge:
```
https://img.shields.io/endpoint?url=https://aaronspindler.com/api/lighthouse/badge/
```

### History Page

**URL**: `/lighthouse/history/`

Displays:
- Latest audit scores in card format
- 30-day trend chart with all 4 metrics
- Detailed table of all audits in the last 30 days

## Badge Display

The badge is displayed in the footer of every page (`templates/_footer.html`) and:
- Links to the history page
- Shows all 4 scores in format: Performance/Accessibility/Best Practices/SEO
- Color-coded: Green (avg ≥90), Yellow (avg ≥70), Red (avg <70)
- Cached for 1 hour for performance

## Database Schema

The `LighthouseAudit` model stores:
- `url` - Audited URL
- `performance_score` - Performance score (0-100)
- `accessibility_score` - Accessibility score (0-100)
- `best_practices_score` - Best Practices score (0-100)
- `seo_score` - SEO score (0-100)
- `audit_date` - Timestamp of audit (auto-set)
- `metadata` - Additional Lighthouse data (JSON)

## Manual Testing

To test the system locally:

```bash
# 1. Run a local audit (requires production site to be accessible)
python manage.py run_lighthouse_audit --url https://aaronspindler.com

# 2. Check the badge endpoint
curl http://localhost:8000/api/lighthouse/badge/

# 3. View the history page
open http://localhost:8000/lighthouse/history/
```

## Troubleshooting

### "Unable to run Lighthouse" Error

Make sure `@lhci/cli` is installed:
```bash
npm install
```

### Badge Shows "no data"

No audits have been run yet. Run the management command:
```bash
python manage.py run_lighthouse_audit
```

### Celery Task Not Running

1. Verify Celery Beat is running: `celery -A config beat -l info`
2. Check that the periodic task is enabled in Django admin
3. Check Celery logs for any errors
4. Ensure the task is registered: `python manage.py setup_periodic_tasks`

## Future Enhancements

Potential improvements for the future:
- Email notifications for score drops
- Comparison between audits
- More granular metrics (individual check scores)
- Trend analysis and anomaly detection
- Integration with PR checks (compare preview vs production)

## Technical Details

### Caching Strategy

- Badge endpoint is cached for 1 hour using Django's `@cache_page` decorator
- Reduces database queries for frequently accessed badge data
- Cache invalidates when new audits are run

### Performance Considerations

- Lighthouse audits take 30-60 seconds to complete
- Run audits during off-peak hours (2 AM UTC)
- History page queries are optimized with date filtering
- Chart.js renders client-side for better performance

## Support

For issues or questions:
1. Check the Django logs for error messages
2. Verify all dependencies are installed
3. Ensure the production site is accessible
4. Check GitHub Actions logs for workflow issues

