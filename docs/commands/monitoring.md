# Monitoring Commands

Management commands for performance monitoring and security/request tracking.

## Performance Monitoring Commands

### run_lighthouse_audit

Run Google Lighthouse performance audit and store results.

**Usage**:
```bash
python manage.py run_lighthouse_audit
```

**Options**:
- `--url URL`: URL to audit (default: site URL from settings)

**Examples**:
```bash
# Audit default URL
python manage.py run_lighthouse_audit

# Audit specific URL
python manage.py run_lighthouse_audit --url https://example.com

# Audit multiple pages
python manage.py run_lighthouse_audit --url https://example.com/
python manage.py run_lighthouse_audit --url https://example.com/blog/
python manage.py run_lighthouse_audit --url https://example.com/about/
```

**What It Does**:
1. Runs Lighthouse CLI via subprocess
2. Captures JSON report
3. Extracts 4 key scores:
   - Performance
   - Accessibility
   - Best Practices
   - SEO
4. Stores LighthouseResult in database
5. Displays results summary

**Requirements**:
- Lighthouse installed: `npm install -g lighthouse`
- Chromium/Chrome available
- Target URL accessible

**Automated Audits**:
- Runs nightly at 2 AM UTC via Celery Beat
- Results visible at `/lighthouse/history/`
- Badge endpoint: `/api/lighthouse/badge/`

---

### setup_periodic_tasks

Configure Celery Beat periodic tasks for automated operations.

**Usage**:
```bash
python manage.py setup_periodic_tasks
```

**What It Configures**:
1. **Daily Lighthouse Audit** - 2 AM UTC
2. **Daily Sitemap Rebuild** - 3 AM UTC
3. **Daily Knowledge Graph Screenshot** - 4 AM UTC
4. **Knowledge Graph Cache Rebuild** - Every 6 hours

**When to Run**:
- After initial deployment
- After Celery Beat configuration changes
- To reset periodic task schedules

---

## Security & Request Tracking

### geolocate_fingerprints

Batch process IP addresses to add geolocation data to request fingerprints.

**Usage**:
```bash
python manage.py geolocate_fingerprints
```

**Options**:
- `--limit N`: Maximum records to process
- `--force`: Re-geolocate all records (including those with existing geo_data)
- `--batch-size N`: IPs per batch request (default: 100, max: 100)
- `--yes`: Skip confirmation prompt (for automated runs)

**Examples**:
```bash
# Interactive mode (shows stats, waits for Enter)
python manage.py geolocate_fingerprints

# Automated mode (skip confirmation)
python manage.py geolocate_fingerprints --yes

# Limit to 100 records
python manage.py geolocate_fingerprints --limit 100

# Re-geolocate all records
python manage.py geolocate_fingerprints --force

# Custom batch size
python manage.py geolocate_fingerprints --batch-size 50

# Combined options
python manage.py geolocate_fingerprints --yes --limit 1000
```

**How It Works**:
1. Queries RequestFingerprint records without geo_data
2. Extracts unique IP addresses
3. Filters out local/private IPs
4. Shows statistics (total records vs unique IPs)
5. Waits for Enter key (unless `--yes` specified)
6. Batches IPs (100 per batch)
7. Calls ip-api.com batch endpoint
8. Updates all records with matching IP
9. Respects rate limits (15 requests/minute)

**API Details**:
- **Service**: ip-api.com (free tier)
- **Rate Limit**: 15 batch requests/minute
- **Batch Size**: Up to 100 IPs per request
- **Data Returned**: City, country, coordinates, timezone, ISP, organization

**Privacy**:
- Automatically skips local/private IPs
- No geolocation during request processing (batch only)
- No personally identifiable information stored

**Automation**:
```bash
# Cron job (daily at 3 AM)
0 3 * * * cd /path/to/project && /path/to/venv/bin/python manage.py geolocate_fingerprints --yes --limit 1000

# Or via Celery Beat
from django_celery_beat.models import PeriodicTask, CrontabSchedule
schedule, _ = CrontabSchedule.objects.get_or_create(minute='0', hour='3')
PeriodicTask.objects.get_or_create(
    name='Daily IP Geolocation',
    task='utils.tasks.geolocate_fingerprints_task',
    crontab=schedule,
)
```

---

### remove_local_fingerprints

Remove request fingerprints from local/private IP addresses.

**Usage**:
```bash
python manage.py remove_local_fingerprints
```

**Options**:
- `--dry-run`: Preview which records would be deleted without deleting
- `--limit N`: Limit number of records to delete

**Examples**:
```bash
# Preview deletions (dry-run)
python manage.py remove_local_fingerprints --dry-run

# Delete local IP records
python manage.py remove_local_fingerprints

# Limit deletions
python manage.py remove_local_fingerprints --limit 100
```

**What It Removes**:
- Local IPs: `127.0.0.1`, `::1`, `localhost`
- Private ranges:
  - `10.0.0.0/8`
  - `172.16.0.0/12`
  - `192.168.0.0/16`
- Link-local: `169.254.0.0/16`, `fe80::/10`

**Use Cases**:
- One-time cleanup after deploying local IP filtering
- Remove development/testing records from production
- Clean up historical data before middleware was updated

**Note**: Modern middleware automatically skips tracking local IPs, so this is mainly for historical cleanup.

---



## Related Documentation

- [Performance Monitoring](../features/performance-monitoring.md) - Lighthouse audit system
- [Request Tracking](../features/request-tracking.md) - Security and analytics
- [Commands Index](README.md) - All management commands
- [Maintenance](../maintenance.md) - Daily monitoring tasks
