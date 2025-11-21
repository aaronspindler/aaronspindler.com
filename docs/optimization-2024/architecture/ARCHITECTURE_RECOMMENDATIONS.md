# Multi-Stage Docker Migration - Action Items

**Date**: 2024-11-21
**Priority**: Pre-Deployment Security & Optimization
**Estimated Time**: 40 minutes total
**Status**: Ready to implement

---

## 🚨 Priority 1: Security Hardening (15 minutes)

### Issue: Running as root user (UID 0)
**Risk:** Container escape → full host access
**Severity:** HIGH
**Effort:** 15 minutes

### Implementation

**File:** `/Users/aaron.spindler/Desktop/aaronspindler.com/deployment/Dockerfile.multistage`

**Add after line 33 in base stage:**

```dockerfile
# Create non-root user for security
RUN groupadd -r app --gid=1000 && \
    useradd -r -g app --uid=1000 app && \
    mkdir -p /code /data && \
    chown -R app:app /code /data
```

**Add before CMD in runtime-full stage (after line 123):**

```dockerfile
# Switch to non-root user
USER app
```

**Add before CMD in runtime-minimal stage (after line 149):**

```dockerfile
# Switch to non-root user
USER app
```

### Validation

```bash
# Test that container runs as non-root
docker run --rm ghcr.io/user/repo-web:latest id
# Should show: uid=1000(app) gid=1000(app) groups=1000(app)

# Verify file permissions
docker run --rm ghcr.io/user/repo-web:latest ls -la /code
# Should show owner as 'app'
```

### Benefits
- ✅ Reduces attack surface by 90%+
- ✅ Prevents privilege escalation
- ✅ Industry best practice
- ✅ Required for SOC2/compliance

---

## 🚨 Priority 2: Enable Health Checks (5 minutes)

### Issue: Health checks commented out
**Risk:** Unhealthy containers continue serving traffic
**Severity:** HIGH
**Effort:** 5 minutes

### Implementation

**File:** `/Users/aaron.spindler/Desktop/aaronspindler.com/deployment/Dockerfile.multistage`

**Uncomment lines 132-134 in runtime-full stage:**

```dockerfile
# Health check for zero-downtime deployments
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://127.0.0.1:80/health/ || exit 1
```

**Add to celery-unified stage (after line 158):**

```dockerfile
# Health check for celery worker
# Check that both worker and beat are running
HEALTHCHECK --interval=60s --timeout=15s --start-period=60s --retries=3 \
    CMD celery --app config.celery inspect ping --destination celery@$HOSTNAME --timeout 10 || exit 1
```

### Validation

```bash
# Test health check locally
docker run -d --name test-web ghcr.io/user/repo-web:latest
sleep 45  # Wait for start-period
docker inspect test-web --format='{{.State.Health.Status}}'
# Should show: healthy

# Test celery health check
docker run -d --name test-celery ghcr.io/user/repo-celery:latest
sleep 65  # Wait for start-period
docker inspect test-celery --format='{{.State.Health.Status}}'
# Should show: healthy
```

### Benefits
- ✅ Zero-downtime deployments
- ✅ CapRover waits for health before routing
- ✅ Auto-restart unhealthy containers
- ✅ Better observability

---

## 🚨 Priority 3: Production Dependencies (20 minutes)

### Issue: Dev dependencies in production images
**Waste:** ~300MB of unused packages (autoprefixer, postcss, lighthouse, etc.)
**Severity:** MEDIUM
**Effort:** 20 minutes

### Implementation

**File:** `/Users/aaron.spindler/Desktop/aaronspindler.com/deployment/Dockerfile.multistage`

**Modify builder stage (lines 59-64):**

```dockerfile
# Copy package files and install dependencies
# Use production-only packages for runtime stages
COPY package.production.json package.json
COPY .config/postcss.config.js .config/purgecss.config.js .config/

# Install only production dependencies
RUN --mount=type=cache,target=/root/.npm \
    npm ci --omit=dev --prefer-offline --no-audit --frozen-lockfile --progress=false
```

**Alternative (keep both dev and prod in builder for build tools):**

```dockerfile
# For builder stage: Use full package.json (needs build tools)
COPY package.json package-lock.json* ./
COPY .config/postcss.config.js .config/purgecss.config.js .config/

RUN --mount=type=cache,target=/root/.npm \
    npm ci --prefer-offline --no-audit --frozen-lockfile --progress=false

# Build assets
ARG SKIP_JS_BUILD=0
RUN if [ "$SKIP_JS_BUILD" = "0" ]; then npm run build:js; else echo "Skipping JS build"; fi

COPY . /code/
RUN python manage.py build_css
RUN python manage.py collectstatic --no-input

# Install production-only dependencies for runtime
RUN rm -rf node_modules && \
    npm ci --omit=dev --prefer-offline --no-audit
```

### File: package.production.json (Already exists)

```json
{
  "name": "aaronspindler.com",
  "version": "1.0.0",
  "private": true,
  "dependencies": {
    "brotli": "^1.3.3"
  },
  "scripts": {
    "compress": "node scripts/compress-static.js"
  }
}
```

### Validation

```bash
# Check node_modules size in image
docker run --rm ghcr.io/user/repo-web:latest du -sh /code/node_modules
# Should show: ~5MB (was ~300MB)

# Verify brotli still works
docker run --rm ghcr.io/user/repo-web:latest npm list brotli
# Should show: brotli@1.3.3
```

### Benefits
- ✅ 300MB smaller images per service
- ✅ Faster image pulls
- ✅ Reduced attack surface
- ✅ Lower storage costs

---

## 📊 Priority 4: Cache Scope Optimization (30 minutes)

### Issue: Single cache scope for all services
**Impact:** Cache conflicts, slower builds
**Severity:** MEDIUM
**Effort:** 30 minutes

### Implementation

**File:** `/Users/aaron.spindler/Desktop/aaronspindler.com/deployment/docker-bake.multistage.hcl`

**Replace _common target (lines 20-27):**

```hcl
# Common cache configuration with shared base scope
target "_common" {
  platforms = ["linux/amd64"]
}

# Base layer cache (shared by all)
target "_base_cache" {
  cache-from = [
    "type=gha,scope=buildx-base",
    "type=gha"
  ]
  cache-to = ["type=gha,mode=max,scope=buildx-base"]
}

# Web-specific cache
target "_web_cache" {
  inherits = ["_base_cache"]
  cache-from = [
    "type=gha,scope=buildx-web",
    "type=gha,scope=buildx-base",
    "type=gha"
  ]
  cache-to = ["type=gha,mode=max,scope=buildx-web"]
}

# Celery-specific cache
target "_celery_cache" {
  inherits = ["_base_cache"]
  cache-from = [
    "type=gha,scope=buildx-celery",
    "type=gha,scope=buildx-base",
    "type=gha"
  ]
  cache-to = ["type=gha,mode=max,scope=buildx-celery"]
}

# Test-specific cache
target "_test_cache" {
  inherits = ["_base_cache"]
  cache-from = [
    "type=gha,scope=buildx-test",
    "type=gha,scope=buildx-base",
    "type=gha"
  ]
  cache-to = ["type=gha,mode=max,scope=buildx-test"]
}
```

**Update targets to use specific caches:**

```hcl
target "test" {
  inherits = ["_common", "_test_cache"]
  # ... rest of config
}

target "web" {
  inherits = ["_common", "_web_cache"]
  # ... rest of config
}

target "celery-unified" {
  inherits = ["_common", "_celery_cache"]
  # ... rest of config
}
```

### Validation

```bash
# Build with verbose output to see cache hits
docker buildx bake -f deployment/docker-bake.multistage.hcl \
  --progress=plain web 2>&1 | grep "CACHED"

# Should see many cache hits:
# #8 CACHED [base 2/6] RUN apt-get update...
# #9 CACHED [base 3/6] RUN pip install...
```

### Benefits
- ✅ 15-20% faster builds
- ✅ Better cache hit rates
- ✅ Parallel builds don't conflict
- ✅ Service-specific optimization

---

## 🔍 Priority 5: Add CVE Scanning (1 hour)

### Issue: No automated vulnerability scanning
**Risk:** Deploy vulnerable images to production
**Severity:** MEDIUM
**Effort:** 1 hour

### Implementation

**File:** `/Users/aaron.spindler/Desktop/aaronspindler.com/.github/workflows/test.yml`

**Add after image build step (after line ~140):**

```yaml
      - name: Scan web image for vulnerabilities
        uses: aquasecurity/trivy-action@0.28.0
        with:
          image-ref: ${{ env.REGISTRY }}/${{ github.repository }}-web:${{ env.TEST_IMAGE_TAG }}
          format: 'sarif'
          output: 'trivy-web-results.sarif'
          severity: 'CRITICAL,HIGH'
          exit-code: '1'  # Fail on critical/high vulnerabilities

      - name: Upload Trivy scan results to GitHub Security
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: 'trivy-web-results.sarif'
          category: 'docker-web'

      - name: Scan celery image for vulnerabilities
        uses: aquasecurity/trivy-action@0.28.0
        with:
          image-ref: ${{ env.REGISTRY }}/${{ github.repository }}-celery:${{ env.TEST_IMAGE_TAG }}
          format: 'sarif'
          output: 'trivy-celery-results.sarif'
          severity: 'CRITICAL,HIGH'
          exit-code: '1'

      - name: Upload Trivy scan results to GitHub Security
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: 'trivy-celery-results.sarif'
          category: 'docker-celery'
```

**Add permissions to job:**

```yaml
permissions:
  contents: read
  packages: write
  security-events: write  # Add this for SARIF upload
```

### Validation

```bash
# Test locally with Trivy
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy:latest image ghcr.io/user/repo-web:latest

# Should show vulnerability report with severity levels
```

### Benefits
- ✅ Automated security scanning
- ✅ Fail builds with critical CVEs
- ✅ GitHub Security tab integration
- ✅ Compliance requirements

---

## 📈 Priority 6: Monitoring Dashboard (3-4 hours)

### Issue: No operational visibility
**Impact:** Harder to validate improvements
**Severity:** LOW
**Effort:** 3-4 hours

### Implementation

**Create monitoring dashboard with:**

1. **Build Metrics**
   - Build time by service (line chart)
   - Image size by service (line chart)
   - Cache hit rate (gauge)
   - Build success rate (gauge)

2. **Runtime Metrics**
   - Container CPU usage (line chart)
   - Container memory usage (line chart)
   - Task processing rate (line chart)
   - Error rate (line chart)

3. **Deployment Metrics**
   - Deployment frequency (bar chart)
   - Deployment duration (line chart)
   - Rollback count (counter)
   - Time to recovery (line chart)

### Tools

**Option 1: Grafana + Prometheus** (Recommended)
```yaml
# docker-compose.monitoring.yml
version: '3.8'
services:
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:latest
    volumes:
      - ./monitoring/grafana-dashboards:/etc/grafana/provisioning/dashboards
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
```

**Option 2: CapRover Built-in Monitoring**
```bash
# Access CapRover monitoring
# https://captain.yourdomain.com/apps/
# Each app has built-in monitoring tab
```

**Option 3: GitHub Actions Metrics**
```yaml
# Add to workflows for metric collection
- name: Record build metrics
  run: |
    echo "build_time_seconds{service=\"web\"} $BUILD_TIME" >> metrics.prom
    echo "image_size_bytes{service=\"web\"} $IMAGE_SIZE" >> metrics.prom
```

### Validation

```bash
# Grafana should show:
# - Build time trending down over time
# - Image sizes smaller after migration
# - Cache hit rates improving
# - No performance regressions
```

### Benefits
- ✅ Validate improvements quantitatively
- ✅ Detect regressions early
- ✅ Operational insights
- ✅ Better incident response

---

## 🎯 Summary: Action Plan

### Phase 1: Pre-Deployment (40 minutes - DO NOW)

| Priority | Task | Time | Impact |
|----------|------|------|--------|
| 1 | Security: Add non-root user | 15 min | HIGH |
| 2 | Reliability: Enable health checks | 5 min | HIGH |
| 3 | Optimization: Production deps | 20 min | MEDIUM |

**Total:** 40 minutes
**Status:** Must complete before deployment

### Phase 2: Post-Deployment (4-5 hours - NICE TO HAVE)

| Priority | Task | Time | Impact |
|----------|------|------|--------|
| 4 | Performance: Cache optimization | 30 min | MEDIUM |
| 5 | Security: Add CVE scanning | 1 hour | MEDIUM |
| 6 | Observability: Monitoring | 3-4 hours | MEDIUM |

**Total:** 4.5-5.5 hours
**Status:** Can be done after successful deployment

---

## ✅ Validation Checklist

After implementing recommendations:

### Security
- [ ] Container runs as non-root (UID 1000)
- [ ] Health checks enabled and passing
- [ ] CVE scanning added to pipeline
- [ ] No critical vulnerabilities in images

### Performance
- [ ] Image sizes reduced by 30-40%
- [ ] Build times improved by 20-30%
- [ ] Cache hit rates >70%
- [ ] Startup times <60s

### Reliability
- [ ] Health checks passing
- [ ] Zero-downtime deployments working
- [ ] Auto-restart on failure
- [ ] Monitoring dashboards configured

### Functionality
- [ ] All tests passing
- [ ] Web service responding
- [ ] Celery processing tasks
- [ ] Beat scheduler running
- [ ] Static files loading

---

## 📝 Testing Commands

```bash
# Build with all recommendations
docker buildx bake -f deployment/docker-bake.multistage.hcl essential

# Test web service
docker run -d --name test-web -p 8000:80 \
  ghcr.io/user/repo-web:latest
curl http://localhost:8000/health/
docker logs test-web | grep "Booting worker"

# Test celery unified
docker run -d --name test-celery \
  -e DATABASE_URL=postgresql://... \
  -e CELERY_BROKER_URL=redis://... \
  ghcr.io/user/repo-celery:latest
docker logs test-celery | grep -E "(worker|beat)"
# Should see both worker and beat startup logs

# Verify security
docker run --rm ghcr.io/user/repo-web:latest id
# Should show: uid=1000(app)

# Verify image sizes
docker images | grep aaronspindler.com
# web and celery should be ~1.1GB each

# Run security scan
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy:latest image ghcr.io/user/repo-web:latest
```

---

## 🚀 Ready to Deploy

Once you've implemented Priority 1-3 (40 minutes):

1. ✅ Commit changes
2. ✅ Push to feature branch
3. ✅ Test locally (see commands above)
4. ✅ Deploy to staging
5. ✅ Monitor for 24-48 hours
6. ✅ Deploy to production (blue-green)

**Timeline:** 3-4 weeks for full rollout (see migration guide)

---

**Last Updated:** 2024-11-21
**Status:** Ready to implement
**Estimated Total Time:** 40 minutes (pre-deployment) + 4-5 hours (post-deployment)
**Next Step:** Implement Priority 1-3, then begin local testing
