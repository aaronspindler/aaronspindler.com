# Celery Deployment Fix - Summary

## Issues Fixed

### 1. Celery Worker Shutdown After ~75 Seconds ✅

**Root Cause:**
- The `celery-unified` container inherited a health check from `runtime-full` that tried to curl `http://127.0.0.1:80/health/`
- Celery workers don't run an HTTP server on port 80
- Health check failed → container marked unhealthy → orchestrator killed the container

**Fix Applied:**
- Added `HEALTHCHECK NONE` to the `celery-unified` stage in `Dockerfile.multistage`
- This disables the inherited health check for celery containers

### 2. Unnecessary Web Initialization ✅

**Root Cause:**
- Celery containers were using `docker-entrypoint.sh` which runs Django migrations and collectstatic
- These operations are unnecessary for Celery and slow down container startup

**Fix Applied:**
- Created `deployment/docker-entrypoint-celery.sh` specifically for Celery
- Only includes database readiness check (no migrations or collectstatic)
- Modified `celery-unified` stage to use this new entrypoint

### 3. Multiple Celery Beat Instances (Needs Verification) ⚠️

**Symptoms:**
- Constant "DatabaseScheduler: Schedule changed" messages every 20-30 seconds
- Tasks not executing reliably
- Beat schedule being constantly modified

**Root Cause:**
- Multiple celery-beat instances running simultaneously
- They compete to update the `django_celery_beat_periodictask` table
- Causes schedule thrashing and prevents reliable task execution

**Verification Steps:**

1. **Check running containers in CapRover:**
   ```bash
   # SSH into CapRover server
   ssh your-caprover-server

   # List all running containers with "celery" or "beat" in the name
   docker ps | grep -iE "celery|beat"
   ```

2. **Check for duplicate beat processes:**
   ```bash
   # Check if any containers are running celery beat
   docker ps --format "table {{.Names}}\t{{.Command}}" | grep -i beat
   ```

3. **Expected Result:**
   - You should see ONLY ONE container running `celery ... worker --beat`
   - NO separate containers running just `celery ... beat`

4. **If you find multiple beat instances:**
   ```bash
   # Stop and remove old celerybeat containers
   docker stop $(docker ps -q --filter "name=celerybeat")
   docker rm $(docker ps -aq --filter "name=celerybeat")
   ```

5. **Check CapRover Apps:**
   - Log into CapRover dashboard
   - Check if there's a separate "celerybeat" app running
   - If yes, you can either:
     - **Option A (Recommended):** Delete the separate celerybeat app (since celery-unified handles both)
     - **Option B:** Keep it but ensure it's stopped/disabled

## Deployment Steps

### 1. Test Locally (Recommended)

```bash
# Build the fixed image
docker build -f deployment/Dockerfile.multistage --target celery-unified -t test-celery .

# Run it locally to verify
docker run -d --name test-celery \
  -e DATABASE_URL="your-db-url" \
  -e CELERY_BROKER_URL="redis://your-redis:6379/1" \
  -e CELERY_RESULT_BACKEND="redis://your-redis:6379/2" \
  test-celery

# Check logs
docker logs -f test-celery

# You should see:
# - "Starting Celery container..."
# - "Database is ready!"
# - Celery worker starting
# - "celery@hostname ready"
# - NO health check failures
# - NO "Warm shutdown" after 75 seconds
```

### 2. Deploy to Production

```bash
# Commit changes
git add deployment/Dockerfile.multistage deployment/docker-entrypoint-celery.sh
git commit -m "fix: celery container health check and beat scheduler conflicts"
git push origin main

# The GitHub Actions workflow will:
# 1. Build new celery image with fixes
# 2. Push to GHCR
# 3. Deploy to CapRover
```

### 3. Verify Deployment

```bash
# After deployment completes, check logs in CapRover
# Look for:
# ✅ Container stays running (no shutdown after 75 seconds)
# ✅ Beat schedule changes stop after initial sync
# ✅ Scheduled tasks execute at their defined times
```

## Monitoring Post-Deployment

### Expected Celery Worker Logs
```
Starting Celery container...
Database is ready!
Celery container initialization complete!

-------------- celery@hostname v5.5.3 (immunity)
--- ***** -----
...
[tasks]
  . blog.tasks.generate_knowledge_graph_screenshot
  . blog.tasks.rebuild_knowledge_graph
  ...

[INFO/MainProcess] Connected to redis://...
[INFO/MainProcess] mingle: searching for neighbors
[INFO/MainProcess] celery@hostname ready.
[INFO/Beat] beat: Starting...
```

### Expected Celery Beat Behavior
After initial startup, you should see:
- **ONE** "DatabaseScheduler: Schedule changed" message at startup
- Then scheduled tasks executing at their defined times
- NO constant "Schedule changed" messages every 20-30 seconds

### Red Flags (Indicates Issues)
- ❌ Container shuts down after ~75 seconds
- ❌ "Schedule changed" messages every 20-30 seconds
- ❌ Health check failures in logs
- ❌ Migrations running in celery container logs

## Additional Recommendations

### 1. Add Celery Health Check (Optional)
If you want monitoring, consider adding a Celery-specific health check:

```dockerfile
# In celery-unified stage
HEALTHCHECK --interval=60s --timeout=5s --start-period=60s --retries=3 \
  CMD celery -A config inspect ping -d celery@$HOSTNAME || exit 1
```

### 2. Monitor Beat Schedule Lock
Add monitoring to detect multiple beat instances:

```python
# In Django admin or monitoring dashboard
from django_celery_beat.models import PeriodicTask
from datetime import datetime, timedelta

# Check if schedule is being modified too frequently
recent_modifications = PeriodicTask.objects.filter(
    last_run_at__gte=datetime.now() - timedelta(minutes=5)
).count()

if recent_modifications > 10:
    # Alert: Possible multiple beat instances
    pass
```

### 3. Resource Limits
Consider adding resource limits in CapRover:

```yaml
# In CapRover app settings
resources:
  limits:
    cpus: '2.0'
    memory: 2G
  reservations:
    cpus: '0.5'
    memory: 512M
```

## Rollback Plan

If issues occur after deployment:

```bash
# Option 1: Revert the commit
git revert HEAD
git push origin main

# Option 2: Deploy previous SHA
# In CapRover: Deploy → Specify previous image tag

# Option 3: Scale down celery-unified and use legacy setup
# Deploy separate celery-worker and celery-beat containers
```

## Questions to Verify

Before proceeding, please verify:

1. ✅ Is there a separate "celerybeat" or "celery-beat" app in CapRover?
2. ✅ Are you using the `celery-unified` target from docker-bake?
3. ✅ Do you want to keep Beat and Worker combined (recommended) or separate?

## Files Modified

- ✅ `deployment/Dockerfile.multistage` - Added health check override and celery entrypoint
- ✅ `deployment/docker-entrypoint-celery.sh` - New celery-specific entrypoint (created)

## References

- Celery Health Checks: https://docs.celeryproject.org/en/stable/userguide/workers.html#inspecting-workers
- django-celery-beat: https://github.com/celery/django-celery-beat
- Docker Health Checks: https://docs.docker.com/engine/reference/builder/#healthcheck
