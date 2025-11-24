# FeeFiFoFunds Celery Tasks

## Overview

Automated tasks for maintaining Kraken OHLCV data using Celery and Celery Beat. These tasks keep your data current by automatically backfilling gaps and monitoring data quality.

---

## Available Tasks

### 1. Incremental Gap Backfill (`backfill_gaps_incremental`)

**Purpose:** Automatically backfill gaps from the last saved data point to now for all assets in a tier.

**How it works:**
1. Finds the last data point for each asset/interval
2. Calculates gap from last data point to now
3. Backfills via Kraken API (if within 720-candle limit)
4. Creates `GapRecord` entries for tracking
5. Logs unfillable gaps (>720 candles) for manual CSV download

**Parameters:**
- `tier` (str): Asset tier to process - `TIER1`, `TIER2`, `TIER3`, `TIER4`, or `ALL` (default: `TIER1`)
- `intervals` (List[int]): Interval minutes to process (default: `[60, 1440]`)
- `lookback_days` (int): Only process assets with data within last N days (default: `7`)
- `max_gaps_per_asset` (int): Maximum gaps to fill per asset (default: `10`)

**Returns:** Summary dict with statistics:
```python
{
    "task_id": "abc-123",
    "tier": "TIER1",
    "intervals": [60, 1440],
    "assets_processed": 20,
    "gaps_detected": 5,
    "gaps_filled": 4,
    "gaps_unfillable": 1,
    "gaps_failed": 0,
    "total_candles_filled": 240,
    "errors": []
}
```

**Example Usage:**
```python
# Trigger manually via Django shell
from feefifofunds.tasks import backfill_gaps_incremental
result = backfill_gaps_incremental.delay(tier='TIER1', intervals=[60, 1440])

# Check result
print(result.get())
```

**Scheduled via Celery Beat:**
```python
# In settings.py or celery.py
CELERY_BEAT_SCHEDULE = {
    'backfill-tier1-daily': {
        'task': 'feefifofunds.backfill_gaps_incremental',
        'schedule': crontab(hour=2, minute=0),  # 2 AM daily
        'kwargs': {
            'tier': 'TIER1',
            'intervals': [60, 1440],
            'lookback_days': 7
        }
    },
}
```

---

### 2. Cleanup Old Gap Records (`cleanup_old_gap_records`)

**Purpose:** Clean up old resolved gap records to prevent database bloat.

**How it works:**
- Deletes `FILLED` gaps older than N days
- Deletes `FAILED` gaps older than N days (gives time for retry)
- Keeps `UNFILLABLE` gaps indefinitely (documentation of missing CSV files)

**Parameters:**
- `days` (int): Delete filled/failed gaps older than this many days (default: `90`)

**Returns:**
```python
{
    "filled_deleted": 123,
    "failed_deleted": 5
}
```

**Scheduled via Celery Beat:**
```python
CELERY_BEAT_SCHEDULE = {
    'cleanup-gap-records-weekly': {
        'task': 'feefifofunds.cleanup_old_gap_records',
        'schedule': crontab(day_of_week='sunday', hour=3, minute=0),
        'kwargs': {'days': 90}
    },
}
```

---

### 3. Data Completeness Report (`report_data_completeness`)

**Purpose:** Generate and log data completeness metrics for monitoring.

**How it works:**
- Counts gaps by status (fillable vs unfillable)
- Calculates completeness percentage
- Logs summary to application logs

**Parameters:**
- `tier` (str): Asset tier to report on (default: `TIER1`)
- `intervals` (List[int]): Intervals to report on (default: `[60, 1440]`)

**Returns:**
```python
{
    "tier": "TIER1",
    "total_assets": 20,
    "assets_with_gaps": 2,
    "completeness_pct": 90.0,
    "intervals": {
        60: {
            "fillable_gaps": 3,
            "unfillable_gaps": 1,
            "total_gaps": 4
        },
        1440: {
            "fillable_gaps": 0,
            "unfillable_gaps": 0,
            "total_gaps": 0
        }
    }
}
```

**Scheduled via Celery Beat:**
```python
CELERY_BEAT_SCHEDULE = {
    'completeness-report-daily': {
        'task': 'feefifofunds.report_data_completeness',
        'schedule': crontab(hour=8, minute=0),  # 8 AM daily
        'kwargs': {'tier': 'TIER1', 'intervals': [60, 1440]}
    },
}
```

---

### 4. Validate Recent Data (`validate_recent_data`)

**Purpose:** Alert if critical assets are missing recent data (monitoring/alerting).

**How it works:**
- Checks TIER1 and TIER2 assets for recent data
- Identifies assets with stale data (older than N hours)
- Logs warnings for investigation

**Parameters:**
- `hours` (int): Alert if no data within last N hours (default: `24`)

**Returns:**
```python
{
    "assets_checked": 50,
    "interval_minutes": 1440,
    "assets_missing_data": [
        {
            "ticker": "XBTUSD",
            "tier": "TIER1",
            "last_timestamp": "2024-12-30T00:00:00",
            "hours_behind": 48
        }
    ]
}
```

**Scheduled via Celery Beat:**
```python
CELERY_BEAT_SCHEDULE = {
    'validate-data-hourly': {
        'task': 'feefifofunds.validate_recent_data',
        'schedule': crontab(minute=0),  # Every hour
        'kwargs': {'hours': 24}
    },
}
```

---

## Complete Celery Beat Configuration

Add this to your `config/settings.py` or `config/celery.py`:

```python
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    # Daily incremental backfill for TIER1 (most critical)
    'backfill-tier1-daily': {
        'task': 'feefifofunds.backfill_gaps_incremental',
        'schedule': crontab(hour=2, minute=0),  # 2 AM daily
        'kwargs': {
            'tier': 'TIER1',
            'intervals': [60, 1440],  # Hourly and daily
            'lookback_days': 7,
            'max_gaps_per_asset': 10
        }
    },

    # Daily incremental backfill for TIER2
    'backfill-tier2-daily': {
        'task': 'feefifofunds.backfill_gaps_incremental',
        'schedule': crontab(hour=3, minute=0),  # 3 AM daily
        'kwargs': {
            'tier': 'TIER2',
            'intervals': [1440],  # Daily only
            'lookback_days': 7
        }
    },

    # Weekly cleanup of old gap records
    'cleanup-gap-records-weekly': {
        'task': 'feefifofunds.cleanup_old_gap_records',
        'schedule': crontab(day_of_week='sunday', hour=4, minute=0),
        'kwargs': {'days': 90}
    },

    # Daily completeness report
    'completeness-report-daily': {
        'task': 'feefifofunds.report_data_completeness',
        'schedule': crontab(hour=8, minute=0),  # 8 AM daily
        'kwargs': {'tier': 'TIER1', 'intervals': [60, 1440]}
    },

    # Hourly validation (monitoring)
    'validate-data-hourly': {
        'task': 'feefifofunds.validate_recent_data',
        'schedule': crontab(minute=0),  # Every hour
        'kwargs': {'hours': 24}
    },
}
```

---

## Manual Task Execution

### Via Django Shell

```python
# Start Django shell
python manage.py shell

# Import tasks
from feefifofunds.tasks import (
    backfill_gaps_incremental,
    cleanup_old_gap_records,
    report_data_completeness,
    validate_recent_data
)

# Execute task asynchronously (returns AsyncResult)
result = backfill_gaps_incremental.delay(tier='TIER1', intervals=[60, 1440])

# Get task ID
print(f"Task ID: {result.id}")

# Wait for result (blocking)
summary = result.get(timeout=3600)  # 1 hour timeout
print(summary)

# Check task status
print(f"Status: {result.status}")  # PENDING, STARTED, SUCCESS, FAILURE
print(f"Ready: {result.ready()}")  # True if completed
```

### Via Management Command (Synchronous)

```python
# Execute task synchronously (useful for testing)
from feefifofunds.tasks import backfill_gaps_incremental
summary = backfill_gaps_incremental(tier='TIER1', intervals=[60, 1440])
print(summary)
```

### Via Celery CLI

```bash
# Trigger task via CLI
celery -A config call feefifofunds.backfill_gaps_incremental \
    --kwargs='{"tier": "TIER1", "intervals": [60, 1440]}'

# Inspect scheduled tasks
celery -A config inspect scheduled

# Inspect active tasks
celery -A config inspect active

# Purge all tasks
celery -A config purge
```

---

## Monitoring and Debugging

### Check Task Status

```python
from celery.result import AsyncResult

# Get task by ID
result = AsyncResult('task-id-here')
print(f"Status: {result.status}")
print(f"Result: {result.result}")
print(f"Traceback: {result.traceback}")
```

### View Logs

```bash
# Celery worker logs
tail -f logs/celery.log

# Django logs (task execution)
tail -f logs/django.log

# Filter for feefifofunds tasks
tail -f logs/celery.log | grep feefifofunds
```

### Inspect GapRecords

```python
from feefifofunds.models import GapRecord

# Recent fillable gaps
fillable = GapRecord.objects.filter(
    is_api_fillable=True,
    status__in=['DETECTED', 'FAILED']
).order_by('-detected_at')[:10]

# Unfillable gaps (need CSV download)
unfillable = GapRecord.objects.filter(
    status='UNFILLABLE'
).order_by('-detected_at')

# Gaps by asset
from feefifofunds.models import Asset
asset = Asset.objects.get(ticker='XBTUSD')
gaps = GapRecord.objects.filter(asset=asset).order_by('-detected_at')

for gap in gaps:
    print(f"{gap.interval_minutes}min: {gap.gap_start} to {gap.gap_end} - {gap.status}")
```

---

## Error Handling

### Task Failures

Tasks automatically log errors and create failed `GapRecord` entries. Check logs for details:

```bash
# Find failed tasks
grep "ERROR" logs/celery.log | grep feefifofunds

# Check failed gaps
from feefifofunds.models import GapRecord
failed = GapRecord.objects.filter(status='FAILED').order_by('-detected_at')

for gap in failed:
    print(f"{gap.asset.ticker} {gap.interval_minutes}min: {gap.error_message}")
```

### Retry Failed Gaps

```python
# Retry all failed gaps
from feefifofunds.tasks import backfill_gaps_incremental
from feefifofunds.models import GapRecord

# Reset failed gaps to detected
failed_gaps = GapRecord.objects.filter(status='FAILED', is_api_fillable=True)
for gap in failed_gaps:
    gap.status = 'DETECTED'
    gap.save()

# Run backfill task
result = backfill_gaps_incremental.delay(tier='TIER1')
```

### Rate Limiting

Kraken API has rate limits. The task includes 1-second delays between API calls. If you hit rate limits:

1. Reduce `max_gaps_per_asset` parameter
2. Increase spacing between scheduled runs
3. Spread different tiers across different hours

```python
# Conservative configuration
CELERY_BEAT_SCHEDULE = {
    'backfill-tier1-conservative': {
        'task': 'feefifofunds.backfill_gaps_incremental',
        'schedule': crontab(hour=2, minute=0),
        'kwargs': {
            'tier': 'TIER1',
            'intervals': [1440],  # Daily only (fewer API calls)
            'max_gaps_per_asset': 5  # Reduced from 10
        }
    },
}
```

---

## Performance Considerations

### Task Duration Estimates

| Task | Tier | Intervals | Est. Duration |
|------|------|-----------|---------------|
| `backfill_gaps_incremental` | TIER1 | [1440] | 2-5 minutes |
| `backfill_gaps_incremental` | TIER1 | [60, 1440] | 5-10 minutes |
| `backfill_gaps_incremental` | TIER2 | [1440] | 5-10 minutes |
| `backfill_gaps_incremental` | ALL | [1440] | 20-30 minutes |
| `cleanup_old_gap_records` | - | - | < 1 minute |
| `report_data_completeness` | TIER1 | [60, 1440] | < 1 minute |
| `validate_recent_data` | - | - | 1-2 minutes |

### Resource Usage

- **CPU**: Low (mostly I/O bound - API calls and database queries)
- **Memory**: Low (~50-100 MB per task)
- **Network**: Moderate (API calls, rate-limited to 1 req/sec)
- **Database**: Low (small writes to GapRecord table, reads from QuestDB)

### Optimization Tips

1. **Stagger schedules**: Don't run all tiers at the same time
2. **Prioritize intervals**: Daily (1440) data is more critical than hourly (60)
3. **Use lookback_days**: Avoid reprocessing old assets unnecessarily
4. **Monitor queue length**: If tasks pile up, increase worker count or reduce frequency

---

## Production Deployment

### Celery Worker Configuration

```bash
# Start Celery worker
celery -A config worker \
    --loglevel=info \
    --logfile=logs/celery.log \
    --concurrency=2 \
    --max-tasks-per-child=100

# Start Celery Beat (scheduler)
celery -A config beat \
    --loglevel=info \
    --logfile=logs/celery-beat.log \
    --pidfile=celery-beat.pid

# Or combined (development only)
celery -A config worker --beat --loglevel=info
```

### Systemd Service (Production)

```ini
# /etc/systemd/system/celery-feefifofunds.service
[Unit]
Description=Celery Worker - FeeFiFoFunds
After=network.target redis.target

[Service]
Type=forking
User=www-data
Group=www-data
WorkingDirectory=/app
ExecStart=/app/venv/bin/celery -A config worker \
    --loglevel=info \
    --logfile=/app/logs/celery.log \
    --pidfile=/app/run/celery.pid \
    --concurrency=2
ExecStop=/app/venv/bin/celery -A config control shutdown
Restart=always

[Install]
WantedBy=multi-user.target
```

```ini
# /etc/systemd/system/celerybeat-feefifofunds.service
[Unit]
Description=Celery Beat - FeeFiFoFunds Scheduler
After=network.target redis.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/app
ExecStart=/app/venv/bin/celery -A config beat \
    --loglevel=info \
    --logfile=/app/logs/celery-beat.log \
    --pidfile=/app/run/celery-beat.pid
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start services
sudo systemctl daemon-reload
sudo systemctl enable celery-feefifofunds
sudo systemctl enable celerybeat-feefifofunds
sudo systemctl start celery-feefifofunds
sudo systemctl start celerybeat-feefifofunds

# Check status
sudo systemctl status celery-feefifofunds
sudo systemctl status celerybeat-feefifofunds
```

---

## Integration with Unified Ingestion

These tasks are designed to work with both:

1. **Current system**: Uses QuestDB queries directly via `KrakenDataSource`
2. **Future unified system**: Creates `GapRecord` entries that integrate with `ingest_kraken_unified` command

**Migration path:**
1. Use tasks with current system (immediate benefit)
2. Migrate to unified ingestion when ready
3. Tasks continue to work seamlessly (same models, same API)

**Example workflow:**
```bash
# 1. Daily automated incremental updates via Celery
# (Runs via Celery Beat at 2 AM)

# 2. Weekly manual completeness check
python manage.py shell
>>> from feefifofunds.tasks import report_data_completeness
>>> report = report_data_completeness('TIER1')
>>> print(report)

# 3. If unfillable gaps are found, download CSV and ingest
# (Future: will integrate with unified command)
python manage.py ingest_sequential --tier TIER1 --intervals 60

# 4. Weekly cleanup
# (Runs via Celery Beat on Sundays at 3 AM)
```

---

## Alerting and Monitoring

### Sentry Integration (Recommended)

```python
# In config/settings.py
import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration

sentry_sdk.init(
    dsn="your-sentry-dsn",
    integrations=[CeleryIntegration()],
    traces_sample_rate=0.1,
)
```

### Custom Alerting

```python
# In feefifofunds/tasks.py
def send_alert(message: str):
    """Send alert via email, Slack, etc."""
    # Implement your alerting logic here
    pass

# In validate_recent_data task
if results["assets_missing_data"]:
    send_alert(
        f"⚠️ {len(results['assets_missing_data'])} assets missing recent data:\n"
        + "\n".join([f"  - {a['ticker']}: {a['hours_behind']}h behind"
                     for a in results['assets_missing_data']])
    )
```

---

## Troubleshooting

### Task Not Running

```bash
# 1. Check Celery worker is running
ps aux | grep celery

# 2. Check Celery Beat is running
ps aux | grep "celery beat"

# 3. Check task is registered
celery -A config inspect registered | grep feefifofunds

# 4. Check Beat schedule
celery -A config inspect scheduled
```

### Task Running But No Results

```python
# Check task in Django logs
tail -f logs/django.log | grep feefifofunds

# Check GapRecords are being created
from feefifofunds.models import GapRecord
recent = GapRecord.objects.filter(
    detected_at__gte=datetime.now() - timedelta(hours=24)
)
print(f"Recent gaps: {recent.count()}")
```

### High Memory Usage

```python
# Reduce concurrency
celery -A config worker --concurrency=1

# Or reduce max_gaps_per_asset
CELERY_BEAT_SCHEDULE = {
    'backfill-tier1-daily': {
        'kwargs': {
            'max_gaps_per_asset': 3  # Reduced from 10
        }
    },
}
```

---

## Future Enhancements

1. **Intelligent scheduling**: Adjust frequency based on gap rate
2. **Priority queue**: Process TIER1 gaps before TIER2
3. **Batch API calls**: Fetch multiple assets in single request (if Kraken API supports)
4. **Retry with exponential backoff**: Smart retry logic for failed gaps
5. **CSV auto-download**: Automatically download quarterly CSV files for unfillable gaps
6. **Slack/Discord notifications**: Real-time alerts for critical gaps

---

## Summary

The Celery tasks provide automated, hands-off maintenance of your Kraken OHLCV data:

✅ **Incremental backfilling** keeps data current (runs daily)
✅ **Gap tracking** identifies missing data requiring manual CSV download
✅ **Completeness monitoring** provides visibility into data quality
✅ **Data validation** alerts on stale data for critical assets
✅ **Automated cleanup** prevents database bloat

Set up Celery Beat with the recommended schedule and your data will stay current automatically!
