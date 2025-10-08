# Lighthouse Performance Monitoring Setup

This document provides instructions for setting up and using the Lighthouse performance monitoring system.

## Overview

The Lighthouse monitoring system automatically tracks all 5 Lighthouse metrics:
- **Performance** - Page load speed and optimization
- **Accessibility** - Web accessibility standards compliance
- **Best Practices** - Web development best practices
- **SEO** - Search engine optimization
- **PWA** - Progressive Web App capabilities

## Features Implemented

✅ **Automated Lighthouse Audits** - Run via management command
✅ **Historical Data Storage** - All audit results stored in database
✅ **Badge Display** - Shield.io-style badge in footer showing latest scores
✅ **History Visualization** - Chart.js-powered trend visualization
✅ **GitHub Actions Integration** - Nightly automated audits
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

### 3. View Results

- **History Page**: Visit `/lighthouse/history/` to see the 30-day trend
- **Badge**: The badge in the footer updates automatically
- **Admin Panel**: View all audits in Django admin under "Lighthouse Monitor"

## GitHub Actions Setup

The nightly audit workflow is configured in `.github/workflows/lighthouse-audit.yml` but requires the following secrets to be set in your repository:

### Required GitHub Secrets

1. `SECRET_KEY` - Django secret key
2. `DATABASE_URL` - Production database connection string (e.g., `postgres://user:pass@host:5432/dbname`)
3. `REDIS_URL` - Redis connection URL (e.g., `redis://host:6379/1`)

### Setting Up Secrets

1. Go to your GitHub repository
2. Navigate to Settings → Secrets and variables → Actions
3. Add the required secrets

The workflow will:
- Run nightly at 2 AM UTC
- Connect to your production database
- Run a Lighthouse audit of https://aaronspindler.com
- Store the results in the database
- Can also be triggered manually via "Actions" tab

## API Endpoints

### Badge Endpoint

**URL**: `/api/lighthouse/badge/`

**Response** (shields.io endpoint format):
```json
{
  "schemaVersion": 1,
  "label": "lighthouse",
  "message": "95/90/95/100/80",
  "color": "brightgreen"
}
```

Used by shields.io to generate the badge:
```
https://img.shields.io/endpoint?url=https://aaronspindler.com/api/lighthouse/badge/
```

### History Page

**URL**: `/lighthouse/history/`

Displays:
- Latest audit scores in card format
- 30-day trend chart with all 5 metrics
- Detailed table of all audits in the last 30 days

## Badge Display

The badge is displayed in the footer of every page (`templates/_footer.html`) and:
- Links to the history page
- Shows all 5 scores in format: Performance/Accessibility/Best Practices/SEO/PWA
- Color-coded: Green (avg ≥90), Yellow (avg ≥70), Red (avg <70)
- Cached for 1 hour for performance

## Database Schema

The `LighthouseAudit` model stores:
- `url` - Audited URL
- `performance_score` - Performance score (0-100)
- `accessibility_score` - Accessibility score (0-100)
- `best_practices_score` - Best Practices score (0-100)
- `seo_score` - SEO score (0-100)
- `pwa_score` - PWA score (0-100)
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

### GitHub Actions Failing

1. Check that all required secrets are set
2. Verify the production database is accessible from GitHub Actions
3. Check the Actions logs for specific error messages

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

