# CI/CD Pipeline Optimization Roadmap

**Current Runtime**: 23-27 minutes
**Optimized Runtime Target**: 12-15 minutes
**Total Additional Savings**: 10-12 minutes (45-50% improvement)

---

## Quick Reference: Priority Matrix

```
┌─────────────────────────────────────────────────────────────────┐
│                    IMPACT vs EFFORT                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  High Impact   │ 🔴 ELIMINATE TAG JOB      │ 📦 Multi-Stage   │
│                │    (5 min, LOW)           │    (4 min, MED)  │
│                │                            │                   │
│                │ 🚀 Registry Cache         │ 🏗️ Base Image   │
│                │    (30s, LOW)             │    (90s, MED)    │
│  ───────────────┼───────────────────────────┼──────────────────│
│                │ ⏩ Skip Chromium          │ 🧪 Test Split    │
│  Low Impact    │    (45s, LOW)             │    (3 min, MED)  │
│                │                            │   ⚠️ 2x cost     │
│                │ 📦 Test Packages          │                   │
│                │    (15s, LOW)             │                   │
└────────────────┴────────────────────────────┴──────────────────┘
                     Low Effort              Medium Effort
```

---

## Phase 1: Critical Quick Wins (Week 1)

### 🔴 Priority 1: Eliminate tag-production-images Job
**Savings**: 5 minutes | **Effort**: Low-Medium | **Risk**: Medium

#### Current State
```yaml
# Job dependency chain
build-production-images (8 min) → wait for tests → tag-production-images (5 min)
                                                    └─ Re-tags all 4 images
```

#### Optimized State
```yaml
# Tag during initial build
build-production-images (8 min) → tests → (no re-tagging needed)
└─ Tags with SHA immediately
```

#### Implementation Steps

**Step 1**: Modify `deployment/docker-bake.hcl`
```hcl
target "web" {
  tags = [
    "${REGISTRY}/${IMAGE_PREFIX}-web:build-${TAG}",
    "${REGISTRY}/${IMAGE_PREFIX}-web:${GITHUB_SHA}",  # ← Add this
    "${REGISTRY}/${IMAGE_PREFIX}-web:latest"
  ]
}

# Repeat for celery, celerybeat, flower targets
```

**Step 2**: Add cleanup job in `.github/workflows/test.yml`
```yaml
# Add new job to delete images if tests fail
cleanup-failed-images:
  runs-on: ubuntu-latest
  needs: [build-production-images, test-suite]
  if: github.ref == 'refs/heads/main' && needs.test-suite.result == 'failure'
  permissions:
    packages: write
  steps:
    - name: Delete pre-tagged images on test failure
      run: |
        for service in web celery celerybeat flower; do
          docker buildx imagetools create \
            --tag ghcr.io/${{ github.repository }}-${service}:deleted-${{ github.sha }} \
            ghcr.io/${{ github.repository }}-${service}:${{ github.sha }}

          # Or use GitHub API to delete version
          # gh api -X DELETE /user/packages/container/$REPO-$service/versions/$SHA
        done
```

**Step 3**: Update `deployment/deploy.yml`
```yaml
# No changes needed! Deployment already uses SHA tags
# Just verify it works with images tagged during build
deploy:
  steps:
    - name: Deploy Web to CapRover
      run: |
        docker run caprover/cli-caprover:latest caprover deploy \
          --imageName "${{ env.REGISTRY }}/${{ github.repository }}-web:${{ steps.commit.outputs.sha }}"
          # ↑ This already uses SHA tag, will work with new approach
```

**Step 4**: Remove `tag-production-images` job
```yaml
# Delete entire job from test.yml
# Update all-checks job to not depend on build-production-images
all-checks:
  needs: [build-docker-image, test-suite]  # Remove build-production-images
```

#### Testing Checklist
- [ ] Build images locally with multi-tag
- [ ] Verify all 3 tags created (build-*, SHA, latest)
- [ ] Test deployment with SHA-tagged image
- [ ] Simulate test failure and verify cleanup
- [ ] Monitor first production run closely

#### Rollback Plan
If issues occur:
1. Re-add `tag-production-images` job
2. Remove SHA tag from bake config
3. Deploy takes ~5 min longer but works as before

**Expected Result**: 23-27 min → 18-22 min (5 min savings)

---

### 🚀 Priority 2: Use Registry Cache
**Savings**: 20-30 seconds | **Effort**: Low | **Risk**: Low

#### Implementation

**Step 1**: Update cache configuration in `deployment/docker-bake.hcl`
```hcl
# Replace GitHub Actions cache with registry cache
target "_common" {
  cache-from = [
    "type=registry,ref=${REGISTRY}/${IMAGE_PREFIX}/cache:${GITHUB_REF_NAME}",
    "type=registry,ref=${REGISTRY}/${IMAGE_PREFIX}/cache:main",
    "type=gha,scope=buildx-main",  # Keep as fallback
  ]
  cache-to = [
    "type=registry,mode=max,ref=${REGISTRY}/${IMAGE_PREFIX}/cache:${GITHUB_REF_NAME}",
    "type=gha,mode=max,scope=buildx-main"
  ]
}
```

**Step 2**: Add cleanup workflow for cache images
Create `.github/workflows/cleanup-cache.yml`:
```yaml
name: Cleanup Cache Images

on:
  schedule:
    - cron: '0 2 * * 0'  # Weekly on Sunday at 2am
  workflow_dispatch:

jobs:
  cleanup:
    runs-on: ubuntu-latest
    permissions:
      packages: write
    steps:
      - name: Delete old cache images
        run: |
          # Keep main cache + last 5 PR caches
          gh api repos/${{ github.repository }}/packages/container/cache/versions \
            --jq '.[] | select(.metadata.container.tags[] | contains("pr-")) | .id' |
            tail -n +6 |
            xargs -I {} gh api -X DELETE repos/${{ github.repository }}/packages/container/cache/versions/{}
```

**Step 3**: Test cache performance
```bash
# First build (cold cache)
time docker buildx bake -f deployment/docker-bake.hcl test

# Second build (warm cache)
time docker buildx bake -f deployment/docker-bake.hcl test
# Should see "CACHED" for most layers
```

**Expected Result**: 18-22 min → 17-21 min (20-30s savings)

---

### 📦 Priority 3: Add Test Packages to Requirements
**Savings**: 10-15 seconds | **Effort**: Low | **Risk**: Very Low

#### Implementation

**Step 1**: Add packages to `requirements/base.txt`
```text
# Add these lines
unittest-xml-reporting==3.2.0
pytest-json-report==1.5.0
```

**Step 2**: Regenerate lockfile
```bash
pip-compile requirements/base.in > requirements/base.txt
```

**Step 3**: Update `.github/workflows/test.yml`
```yaml
# Remove this section from "Run all tests" step
- name: Run all tests
  run: |
    # DELETE THIS LINE:
    # pip install unittest-xml-reporting pytest-json-report --root-user-action=ignore &&

    # Keep the rest:
    export PYTHONDONTWRITEBYTECODE=1 &&
    coverage run manage.py test ...
```

**Step 4**: Test locally
```bash
# Build test image
docker buildx bake -f deployment/docker-bake.hcl test

# Run tests
docker compose -f deployment/docker-compose.test.yml run test_runner \
  coverage run manage.py test --settings=config.settings_test
```

**Expected Result**: 17-21 min → 17-20 min (15s savings)

---

## Phase 2: Medium Impact Wins (Week 2-3)

### 📦 Priority 4: Implement Multi-Stage Builds
**Savings**: 3-5 minutes | **Effort**: Medium | **Risk**: Medium

**Files Ready**: Already created in Phase 3 & 4!
- `deployment/Dockerfile.multistage`
- `deployment/docker-bake.multistage.hcl`
- `.github/workflows/deploy.multistage.yml`
- `docs/MULTI_STAGE_MIGRATION.md` (full guide)

#### Quick Implementation Steps

**Step 1**: Test locally
```bash
# Build all services
docker buildx bake -f deployment/docker-bake.multistage.hcl essential

# Verify image sizes
docker images | grep aaronspindler
# Should see:
# web:       ~1.1GB (was 1.8GB)
# celery:    ~1.1GB (was 1.8GB + 300MB for beat)
```

**Step 2**: Update test workflow
```yaml
# In .github/workflows/test.yml
- name: Build and push test image to GHCR
  uses: docker/bake-action@v5.10.0
  with:
    files: deployment/docker-bake.multistage.hcl  # ← Change from docker-bake.hcl
    targets: test
```

**Step 3**: Update build workflow
```yaml
# In .github/workflows/test.yml
- name: Build and push production images
  uses: docker/bake-action@v5.10.0
  with:
    files: deployment/docker-bake.multistage.hcl  # ← Change
    targets: essential  # ← Change from production (2 services instead of 4)
```

**Step 4**: Deploy and monitor
- Deploy to staging first
- Monitor for 48 hours
- Check service health, resource usage
- Verify celery worker + beat both running
- Full migration guide in `docs/MULTI_STAGE_MIGRATION.md`

**Expected Result**: 17-20 min → 13-16 min (3-5 min savings)

---

### 🏗️ Priority 5: Pre-bake Base Builder Image
**Savings**: 1-1.5 minutes | **Effort**: Medium | **Risk**: Low

#### Implementation

**Step 1**: Create base builder Dockerfile
Create `deployment/Dockerfile.base`:
```dockerfile
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies (everything except app-specific)
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates gnupg \
    libpq5 \
    chromium chromium-driver \
    fonts-liberation libasound2 libatk-bridge2.0-0 \
    libatk1.0-0 libatspi2.0-0 libcups2 libdbus-1-3 \
    libdrm2 libgbm1 libgtk-3-0 libnspr4 libnss3 \
    libx11-6 libxcb1 libxcomposite1 libxdamage1 \
    libxext6 libxfixes3 libxkbcommon0 libxrandr2 \
    xdg-utils nodejs npm \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip uv

# Pre-create directories
RUN mkdir -p /opt/pyppeteer && chmod -R 755 /opt/pyppeteer
WORKDIR /code
```

**Step 2**: Create weekly build workflow
Create `.github/workflows/build-base-image.yml`:
```yaml
name: Build Base Builder Image

on:
  schedule:
    - cron: '0 3 * * 1'  # Weekly on Monday at 3am
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      packages: write
    steps:
      - uses: actions/checkout@v5.0.1

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3.11.1

      - name: Log in to GHCR
        uses: docker/login-action@v3.6.0
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          file: deployment/Dockerfile.base
          push: true
          tags: |
            ghcr.io/${{ github.repository }}-base:latest
            ghcr.io/${{ github.repository }}-base:${{ github.run_number }}
          cache-from: type=registry,ref=ghcr.io/${{ github.repository }}-base:latest
          cache-to: type=registry,mode=max,ref=ghcr.io/${{ github.repository }}-base:latest
```

**Step 3**: Update main Dockerfile to use base
```dockerfile
# In deployment/Dockerfile (or Dockerfile.multistage)
FROM ghcr.io/aaronspindler/aaronspindler.com-base:latest

# Skip all the system package installation
# Jump straight to Python dependencies
COPY requirements/base.txt requirements.txt
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system --no-cache -r requirements.txt

# Rest of Dockerfile unchanged
```

**Expected Result**: 13-16 min → 12-14 min (1-1.5 min savings)

---

### ⏩ Priority 6: Skip Chromium in Test Builds
**Savings**: 45 seconds | **Effort**: Low | **Risk**: Low

#### Implementation

**Step 1**: Add build arg to Dockerfile
```dockerfile
# In deployment/Dockerfile or Dockerfile.multistage
ARG SKIP_CHROMIUM=0

# Modify Chromium download step
RUN if [ "$SKIP_CHROMIUM" = "0" ]; then \
      python -c "from pyppeteer import chromium_downloader; chromium_downloader.download_chromium()"; \
    else \
      echo "Skipping Chromium download for tests"; \
    fi
```

**Step 2**: Update bake config
```hcl
# In deployment/docker-bake.hcl
target "test" {
  args = {
    SKIP_JS_BUILD = "1"
    SKIP_CHROMIUM = "1"  # ← Add this
  }
}

# Production targets still download Chromium
target "web" {
  args = {
    SKIP_JS_BUILD = "0"
    SKIP_CHROMIUM = "0"  # ← Explicit
  }
}
```

**Step 3**: Test locally
```bash
# Build test image (should skip Chromium)
docker buildx bake -f deployment/docker-bake.hcl test

# Build production image (should include Chromium)
docker buildx bake -f deployment/docker-bake.hcl web
```

**Step 4**: Verify tests don't need Chromium
```bash
# Run full test suite
docker compose -f deployment/docker-compose.test.yml run test_runner \
  python manage.py test --settings=config.settings_test
# Should pass without Chromium
```

**Expected Result**: 12-14 min → 11-13 min (45s savings)

---

## Phase 3: Fine-Tuning (Week 4+)

### Additional Optimizations (1-2 min total)

#### 🐘 Optimize PostgreSQL Startup (20-30s)
```yaml
# In deployment/docker-compose.test.yml
services:
  postgres:
    image: postgres:17-alpine  # ← Change from postgres:17
    shm_size: 256mb
    healthcheck:
      interval: 3s  # ← Reduce from 5s
      timeout: 3s
      retries: 10
```

#### 📦 Use package.production.json (15-20s)
```dockerfile
# In production stages of Dockerfile.multistage
COPY package.production.json package.json
RUN npm ci --prefer-offline --no-audit
# Installs only 1 package (brotli) instead of 26
```

---

## Implementation Timeline

### Week 1: Quick Wins
```
Monday:    Eliminate tag-production-images job (4 hours)
Tuesday:   Test thoroughly in staging (8 hours)
Wednesday: Deploy to production, monitor (4 hours)
Thursday:  Implement registry cache (2 hours)
Friday:    Add test packages to requirements (1 hour)

Result: 23-27 min → 17-20 min (-25-30%)
```

### Week 2-3: Medium Impact
```
Week 2:
  Mon-Tue:   Test multi-stage builds locally (8 hours)
  Wed-Thu:   Deploy multi-stage to staging (8 hours)
  Fri:       Monitor staging (4 hours)

Week 3:
  Mon:       Deploy multi-stage to production (4 hours)
  Tue:       Create base builder image workflow (4 hours)
  Wed:       Implement skip Chromium (2 hours)
  Thu-Fri:   Monitor and fine-tune (8 hours)

Result: 17-20 min → 11-13 min (-55-60% total)
```

### Week 4+: Fine-Tuning
```
Week 4:
  Mon:       PostgreSQL optimization (2 hours)
  Tue:       package.production.json (2 hours)
  Wed-Fri:   Monitor and validate (12 hours)

Result: 11-13 min → 10-12 min (-60-65% total)
```

---

## Cost-Benefit Analysis

### Developer Time Investment
- **Phase 1**: 20 hours (1 dev, 1 week)
- **Phase 2**: 36 hours (1 dev, 2 weeks)
- **Phase 3**: 16 hours (1 dev, 1 week)
- **Total**: 72 hours

### CI/CD Time Savings
- **Per pipeline run**: 11-15 minutes saved
- **Runs per day**: ~10 (estimated)
- **Daily savings**: 110-150 minutes = 1.8-2.5 hours
- **Monthly savings**: 54-75 hours of CI/CD time

### ROI Calculation
- **Investment**: 72 developer hours
- **Monthly return**: 54-75 CI/CD hours saved
- **Break-even**: 1 month
- **Annual benefit**: 648-900 hours saved

### Cost Savings
- **Current**: ~$8/month GitHub Actions
- **Optimized**: ~$4/month (-50%)
- **Annual savings**: ~$48

**Note**: Primary benefit is faster feedback loops, not cost reduction.

---

## Success Metrics

### Key Performance Indicators

#### Pipeline Speed
- [ ] **Baseline**: 23-27 minutes (current)
- [ ] **Phase 1**: <20 minutes (-25%)
- [ ] **Phase 2**: <15 minutes (-50%)
- [ ] **Phase 3**: <13 minutes (-55%)
- [ ] **Target**: 10-12 minutes (-60%)

#### Cache Performance
- [ ] Cache hit rate: >98%
- [ ] Cache restore time: <15 seconds
- [ ] Cache size: <5GB total

#### Build Performance
- [ ] Docker build time: <3 minutes
- [ ] Test execution time: <8 minutes
- [ ] Image size reduction: 30-40%

#### Reliability
- [ ] Zero test failures from optimizations
- [ ] No increase in error rates
- [ ] Successful deployment rate: 100%

### Monitoring Dashboard

Track these metrics weekly:
```bash
# Average pipeline runtime
gh run list --workflow=test.yml --limit 50 --json conclusion,startedAt,updatedAt |
  jq '[.[] | select(.conclusion=="success")] |
      map((.updatedAt | fromdateiso8601) - (.startedAt | fromdateiso8601)) |
      add / length / 60'

# Cache hit rate
gh cache list --limit 100 | grep "hit" | wc -l

# Image sizes
docker images | grep aaronspindler | awk '{sum += $7} END {print sum " MB"}'
```

---

## Risk Mitigation

### Rollback Procedures

#### Phase 1: Tag Job Elimination
**If deployment fails**:
1. Re-add `tag-production-images` job from git history
2. Remove SHA tag from bake config
3. Redeploy previous commit (5 min rollback)

#### Phase 2: Multi-Stage Builds
**If services fail**:
1. Revert to single-stage Dockerfile
2. Change workflow to use `docker-bake.hcl`
3. Rebuild and redeploy (10 min rollback)

#### Phase 3: Base Image
**If base image breaks**:
1. Update Dockerfile FROM to use python:3.13-slim
2. Base image workflow can be disabled
3. No immediate impact (15 min rollback)

### Testing Strategy

#### Pre-Production Testing
1. **Local testing** (all phases)
   - Build images locally
   - Run full test suite
   - Verify functionality

2. **Staging deployment** (Phase 2+)
   - Deploy to staging environment
   - Run smoke tests
   - Monitor for 24-48 hours

3. **Canary deployment** (Phase 2+)
   - Deploy to 10% of production
   - Monitor error rates
   - Gradually increase to 100%

#### Validation Criteria
- [ ] All tests pass (100%)
- [ ] No increase in error rates
- [ ] Response times maintained
- [ ] Resource usage acceptable
- [ ] Zero deployment failures

---

## Next Steps

### Immediate Actions (Today)
1. Review this roadmap with team
2. Get approval for Phase 1 implementation
3. Schedule 1 week for Phase 1 work
4. Set up monitoring for baseline metrics

### This Week (Phase 1)
1. Implement tag job elimination
2. Test thoroughly in staging
3. Deploy to production
4. Add registry cache
5. Add test packages to requirements

### Next 2-3 Weeks (Phase 2)
1. Test multi-stage builds locally
2. Deploy to staging
3. Deploy to production
4. Create base builder image
5. Implement skip Chromium

### Month 2+ (Phase 3)
1. Optimize PostgreSQL startup
2. Use package.production.json
3. Monitor and fine-tune
4. Document final performance

---

## Questions & Answers

### Q: Why not parallelize tests across 6 jobs?
**A**: Cost increase (6x runner minutes) for 5-7 min savings. Better to optimize serial execution first. Consider for critical releases only.

### Q: Why not use pytest-xdist immediately?
**A**: Requires test suite refactor (high effort). Current optimizations give better ROI. Good long-term goal.

### Q: What if multi-stage breaks something?
**A**: Easy rollback to single-stage. Test thoroughly in staging first. Have rollback plan ready.

### Q: Should we implement all phases at once?
**A**: No. Incremental approach reduces risk. Each phase builds on previous. Monitor between phases.

### Q: What's the realistic best-case runtime?
**A**: 10-12 minutes with all optimizations. Going below 10 min requires test parallelization (cost increase).

---

**Document Version**: 1.0
**Last Updated**: 2025-11-21
**Owner**: DevOps Team
**Review Schedule**: After each phase completion
