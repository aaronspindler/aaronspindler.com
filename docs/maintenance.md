# Maintenance Guide

## Overview

Ongoing maintenance tasks, monitoring procedures, and troubleshooting guides for keeping the application running smoothly in production.

## Daily Tasks

### Automated (Via Celery Beat)

These tasks run automatically and require no manual intervention:

- **2 AM UTC**: Lighthouse performance audit
- **3 AM UTC**: Geolocate new request fingerprints
- **4 AM UTC**: Knowledge graph screenshot generation
- **Every 6 hours**: Knowledge graph cache rebuild

### Manual Monitoring

Check these daily during business hours:

```bash
# 1. Check application health
curl https://yourdomain.com/health/

# 2. Review error logs
docker-compose logs --tail=100 web | grep ERROR

# 3. Check Celery tasks (via Flower)
open https://yourdomain.com:5555

# 4. Monitor disk space
df -h

# 5. Check Docker container status
docker ps
```

## Weekly Tasks

### Database Maintenance

```bash
# Analyze tables for query optimization
docker exec -it postgres_db psql -U aaronspindler -d aaronspindler_db -c "ANALYZE;"

# Vacuum to reclaim space
docker exec -it postgres_db psql -U aaronspindler -d aaronspindler_db -c "VACUUM ANALYZE;"

# Check database size
docker exec -it postgres_db psql -U aaronspindler -d aaronspindler_db -c "
SELECT pg_size_pretty(pg_database_size('aaronspindler_db'));
"
```

### Cache Management

```bash
# Check Redis memory usage
docker exec -it redis_cache redis-cli INFO memory

# Check cache hit rate
docker exec -it redis_cache redis-cli INFO stats | grep hit

# Clear stale cache keys (if needed)
docker exec -it website python manage.py clear_cache
```

### Log Rotation

```bash
# Rotate nginx logs
sudo logrotate -f /etc/logrotate.d/nginx

# View log sizes
du -sh /var/log/nginx/*.log

# Archive old logs
gzip /var/log/nginx/*.log.1
```

## Monthly Tasks

### Security Updates

```bash
# Update system packages
sudo apt-get update
sudo apt-get upgrade -y

# Update Docker images
docker-compose pull
docker-compose up -d

# Update Python dependencies
docker exec -it website pip install --upgrade -r requirements.txt
docker-compose restart web

# Check for security vulnerabilities
docker exec -it website safety check
```

### SSL Certificate Renewal

```bash
# Check certificate expiration
sudo certbot certificates

# Renew certificates (if needed)
sudo certbot renew

# Test auto-renewal
sudo certbot renew --dry-run
```

### Backup Verification

```bash
# Test database restore from backup
# 1. Download latest backup
aws s3 cp s3://your-backup-bucket/postgres/backup_latest.sql.gz /tmp/

# 2. Create test database
docker exec -it postgres_db psql -U aaronspindler -c "CREATE DATABASE test_restore;"

# 3. Restore backup
gunzip -c /tmp/backup_latest.sql.gz | docker exec -i postgres_db psql -U aaronspindler -d test_restore

# 4. Verify data
docker exec -it postgres_db psql -U aaronspindler -d test_restore -c "SELECT COUNT(*) FROM blog_blogcomment;"

# 5. Clean up
docker exec -it postgres_db psql -U aaronspindler -c "DROP DATABASE test_restore;"
```

### Performance Review

```bash
# Review Lighthouse history
open https://yourdomain.com/lighthouse/history/

# Check database query performance
docker exec -it postgres_db psql -U aaronspindler -d aaronspindler_db -c "
SELECT calls, total_time, mean_time, query
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
"

# Review slow requests in logs
docker-compose logs web | grep "slow request"
```

## Quarterly Tasks

### Data Cleanup

```bash
# Clean up old request fingerprints (> 90 days)
docker exec -it website python manage.py shell -c "
from utils.models import RequestFingerprint
from datetime import timedelta
from django.utils import timezone

cutoff = timezone.now() - timedelta(days=90)
deleted, _ = RequestFingerprint.objects.filter(created_at__lt=cutoff).delete()
print(f'Deleted {deleted} old records')
"

# Clean up old page visits (> 180 days)
docker exec -it website python manage.py shell -c "
from pages.models import PageVisit
from datetime import timedelta
from django.utils import timezone

cutoff = timezone.now() - timedelta(days=180)
deleted, _ = PageVisit.objects.filter(created_at__lt=cutoff).delete()
print(f'Deleted {deleted} old records')
"

# Clean up old Lighthouse results (> 365 days)
docker exec -it website python manage.py shell -c "
from utils.models import LighthouseResult
from datetime import timedelta
from django.utils import timezone

cutoff = timezone.now() - timedelta(days=365)
deleted, _ = LighthouseResult.objects.filter(created_at__lt=cutoff).delete()
print(f'Deleted {deleted} old records')
"
```

### Dependency Audit

```bash
# Check for outdated dependencies
docker exec -it website pip list --outdated

# Update non-breaking dependencies
docker exec -it website pip install --upgrade package-name

# Review CHANGELOG for major updates before upgrading
```

### Backup Audit

```bash
# List all backups
aws s3 ls s3://your-backup-bucket/postgres/ --recursive

# Check backup size trends
aws s3 ls s3://your-backup-bucket/postgres/ --recursive | awk '{print $3, $4}' | tail -10

# Verify old backups are being deleted (retention policy)
```

## Monitoring & Alerts

### Application Monitoring

**Uptime Monitoring** (UptimeRobot, Pingdom, etc.):
- Health check: `https://yourdomain.com/health/`
- Check interval: 5 minutes
- Alert on: 3 consecutive failures

**Error Tracking** (Sentry):
- Automatic error reporting
- Alert on: New errors, error rate increases
- Review: Daily

**Performance Monitoring** (Lighthouse):
- Automated nightly audits
- Alert on: Score drop > 5 points
- Review: Weekly

### Infrastructure Monitoring

```bash
# CPU and memory usage
docker stats --no-stream

# Disk space alerts
df -h | grep -E '8[0-9]%|9[0-9]%|100%'

# Container restart counts
docker inspect website --format='{{.RestartCount}}'

# Check for OOM kills
dmesg | grep -i oom
```

### Database Monitoring

```bash
# Active connections
docker exec -it postgres_db psql -U aaronspindler -d aaronspindler_db -c "
SELECT count(*) FROM pg_stat_activity;
"

# Long-running queries
docker exec -it postgres_db psql -U aaronspindler -d aaronspindler_db -c "
SELECT pid, now() - pg_stat_activity.query_start AS duration, query
FROM pg_stat_activity
WHERE state = 'active'
  AND now() - pg_stat_activity.query_start > interval '5 minutes'
ORDER BY duration DESC;
"

# Deadlocks
docker exec -it postgres_db psql -U aaronspindler -d aaronspindler_db -c "
SELECT * FROM pg_stat_database_conflicts WHERE datname = 'aaronspindler_db';
"
```

### Redis Monitoring

```bash
# Memory usage
docker exec -it redis_cache redis-cli INFO memory | grep used_memory_human

# Connected clients
docker exec -it redis_cache redis-cli INFO clients

# Operations per second
docker exec -it redis_cache redis-cli INFO stats | grep instantaneous_ops_per_sec

# Evicted keys
docker exec -it redis_cache redis-cli INFO stats | grep evicted_keys
```

## Troubleshooting

### High Memory Usage

**Symptoms**: Server slowdown, OOM kills

**Diagnosis**:
```bash
# Check process memory
docker stats

# Check Redis memory
docker exec -it redis_cache redis-cli INFO memory

# Check PostgreSQL connections
docker exec -it postgres_db psql -U aaronspindler -d aaronspindler_db -c "
SELECT count(*) FROM pg_stat_activity;
"
```

**Solutions**:
1. Restart affected services: `docker-compose restart web`
2. Clear cache: `docker exec -it website python manage.py clear_cache`
3. Optimize database: `VACUUM ANALYZE`
4. Review recent code changes for memory leaks
5. Increase server resources if needed

---

### High CPU Usage

**Symptoms**: Slow response times, high load average

**Diagnosis**:
```bash
# Check CPU usage per container
docker stats

# Check system load
uptime

# Check for runaway processes
top -c
```

**Solutions**:
1. Check for long-running Celery tasks
2. Review recent API traffic spikes
3. Check for inefficient database queries
4. Restart services: `docker-compose restart`
5. Scale horizontally if sustained high load

---

### Database Connection Errors

**Symptoms**: `OperationalError: connection refused`

**Diagnosis**:
```bash
# Check PostgreSQL is running
docker ps | grep postgres

# Check PostgreSQL logs
docker logs postgres_db

# Test connection
docker exec -it website python manage.py dbshell
```

**Solutions**:
1. Restart PostgreSQL: `docker-compose restart postgres`
2. Check `DATABASE_URL` environment variable
3. Verify PostgreSQL max_connections setting
4. Check for connection leaks in code
5. Implement connection pooling (pgbouncer)

---

### Celery Tasks Not Running

**Symptoms**: Tasks stuck in queue, no processing

**Diagnosis**:
```bash
# Check Celery worker logs
docker logs celery_worker

# Check Celery Beat logs
docker logs celery_beat

# Check Flower dashboard
open https://yourdomain.com:5555

# Check Redis connection
docker exec -it redis_cache redis-cli PING
```

**Solutions**:
1. Restart Celery workers: `docker-compose restart celery`
2. Restart Celery Beat: `docker-compose restart celery-beat`
3. Check Redis is running: `docker ps | grep redis`
4. Review task code for errors
5. Purge failed tasks if needed

---

### Static Files Not Loading

**Symptoms**: 404 errors for CSS/JS, broken styling

**Diagnosis**:
```bash
# Check S3 bucket
aws s3 ls s3://your-bucket-name/static/

# Check CloudFront distribution
aws cloudfront get-distribution --id YOUR_DIST_ID

# Test direct S3 URL
curl -I https://your-bucket-name.s3.amazonaws.com/static/css/main.css
```

**Solutions**:
1. Re-collect static files: `docker exec -it website python manage.py collectstatic --noinput`
2. Check AWS credentials in environment
3. Verify S3 bucket permissions
4. Invalidate CloudFront cache
5. Check `AWS_S3_CUSTOM_DOMAIN` setting

---

### SSL Certificate Expired

**Symptoms**: Browser security warnings

**Diagnosis**:
```bash
# Check certificate expiration
sudo certbot certificates

# Check certificate dates
openssl s_client -connect yourdomain.com:443 -servername yourdomain.com < /dev/null | openssl x509 -noout -dates
```

**Solutions**:
1. Renew certificate: `sudo certbot renew`
2. Reload nginx: `sudo systemctl reload nginx`
3. Check auto-renewal cron job
4. Verify DNS is pointing correctly
5. Check Certbot logs for errors

---

### Out of Disk Space

**Symptoms**: Write errors, application crashes

**Diagnosis**:
```bash
# Check disk usage
df -h

# Find large files
du -sh /* | sort -hr | head -10

# Check Docker disk usage
docker system df
```

**Solutions**:
1. Clean up Docker: `docker system prune -a`
2. Rotate logs: `sudo logrotate -f /etc/logrotate.d/nginx`
3. Clean old backups
4. Remove unused Docker images/volumes
5. Increase disk size if needed

---

## Performance Optimization

### Database Optimization

```sql
-- Add missing indexes
CREATE INDEX idx_blogcomment_post_slug ON blog_blogcomment(post_slug);
CREATE INDEX idx_pagevisit_created_at ON pages_pagevisit(created_at);
CREATE INDEX idx_requestfingerprint_ip ON utils_requestfingerprint(ip_address);

-- Analyze table statistics
ANALYZE blog_blogcomment;
ANALYZE pages_pagevisit;
ANALYZE utils_requestfingerprint;

-- Check index usage
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
ORDER BY idx_scan ASC
LIMIT 20;
```

### Cache Optimization

```python
# Increase cache timeouts for stable content
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'MAX_ENTRIES': 10000,  # Increase max entries
        },
        'TIMEOUT': 7200,  # 2 hours default
    }
}
```

### Query Optimization

```python
# Use select_related for foreign keys
BlogComment.objects.select_related('author').all()

# Use prefetch_related for many-to-many
PhotoAlbum.objects.prefetch_related('photos').all()

# Add indexes for frequent lookups
class Meta:
    indexes = [
        models.Index(fields=['created_at']),
        models.Index(fields=['is_approved', 'created_at']),
    ]
```

## Backup & Recovery

### Database Backup

**Automated Backup Script** (`/scripts/backup-db.sh`):

```bash
#!/bin/bash
set -e

BACKUP_DIR="/backups/postgres"
DATE=$(date +%Y%m%d_%H%M%S)
FILENAME="backup_$DATE.sql.gz"

# Create backup
docker exec postgres_db pg_dump -U aaronspindler aaronspindler_db | gzip > "$BACKUP_DIR/$FILENAME"

# Upload to S3
aws s3 cp "$BACKUP_DIR/$FILENAME" s3://your-backup-bucket/postgres/

# Keep only last 30 days locally
find "$BACKUP_DIR" -type f -mtime +30 -delete

echo "Backup completed: $FILENAME"
```

**Crontab**:
```cron
0 2 * * * /scripts/backup-db.sh >> /var/log/backup.log 2>&1
```

### Database Restore

```bash
# Download backup
aws s3 cp s3://your-backup-bucket/postgres/backup_20250115_020000.sql.gz /tmp/

# Stop application
docker-compose stop web celery

# Restore database
gunzip -c /tmp/backup_20250115_020000.sql.gz | docker exec -i postgres_db psql -U aaronspindler -d aaronspindler_db

# Restart application
docker-compose start web celery

# Verify data
docker exec -it website python manage.py shell -c "
from blog.models import BlogComment
print(f'Comments: {BlogComment.objects.count()}')
"
```

## Emergency Procedures

### Complete System Outage

1. **Check Service Status**:
```bash
docker ps
systemctl status nginx
systemctl status docker
```

2. **Review Logs**:
```bash
docker-compose logs --tail=100
journalctl -u nginx -n 100
journalctl -u docker -n 100
```

3. **Restart Services**:
```bash
docker-compose restart
sudo systemctl restart nginx
```

4. **Verify Health**:
```bash
curl https://yourdomain.com/health/
```

### Database Corruption

1. **Stop Application**:
```bash
docker-compose stop web celery
```

2. **Check Database**:
```bash
docker exec -it postgres_db psql -U aaronspindler -d aaronspindler_db -c "
SELECT * FROM pg_stat_database WHERE datname = 'aaronspindler_db';
"
```

3. **Restore from Backup**:
```bash
# See Database Restore section above
```

4. **Verify Data Integrity**:
```bash
docker exec -it website python manage.py check
docker exec -it website python manage.py migrate
```

### Security Breach

1. **Immediate Actions**:
```bash
# Change all passwords
docker exec -it website python manage.py changepassword admin

# Rotate SECRET_KEY
# Update .env.production with new SECRET_KEY
docker-compose restart web

# Revoke AWS credentials
aws iam delete-access-key --access-key-id OLD_KEY_ID

# Create new credentials
aws iam create-access-key --user-name aaronspindler
```

2. **Audit**:
```bash
# Review access logs
docker-compose logs web | grep -i "401\|403\|POST /admin"

# Check request fingerprints for suspicious activity
docker exec -it website python manage.py shell -c "
from utils.models import RequestFingerprint
suspicious = RequestFingerprint.objects.filter(is_suspicious=True).order_by('-created_at')[:100]
for fp in suspicious:
    print(f'{fp.created_at}: {fp.ip_address} - {fp.path}')
"
```

3. **Recovery**:
- Review recent code changes
- Update all dependencies
- Run security audit: `docker exec -it website safety check`
- Implement additional security measures

## Related Documentation

- [Architecture](architecture.md) - System design
- [Deployment](deployment.md) - Deployment procedures
- [Commands](commands.md) - Management commands
- [Monitoring](features/performance-monitoring.md) - Lighthouse monitoring
