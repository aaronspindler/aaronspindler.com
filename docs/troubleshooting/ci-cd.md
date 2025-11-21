# CI/CD Troubleshooting Guide

*Last Updated: November 2024*

This guide provides solutions to common issues encountered in the CI/CD pipeline, GitHub Actions workflows, Docker builds, and deployment processes.

## Table of Contents

- [GitHub Actions Issues](#github-actions-issues)
- [Docker Build Problems](#docker-build-problems)
- [Test Failures](#test-failures)
- [Deployment Issues](#deployment-issues)
- [Performance Problems](#performance-problems)
- [GHCR Registry Issues](#ghcr-registry-issues)
- [Dependabot Issues](#dependabot-issues)
- [Quick Diagnostics](#quick-diagnostics)

## GitHub Actions Issues

### Workflow Not Triggering

**Symptoms**: Push to main or PR doesn't trigger workflow

**Diagnosis**:
```bash
# Check workflow syntax
gh workflow view test.yml

# View recent runs
gh run list --workflow=test.yml

# Check branch protection
gh api repos/:owner/:repo/branches/main/protection
```

**Solutions**:

1. **Check workflow file syntax**:
```yaml
# Correct trigger syntax
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
```

2. **Verify file location**:
```bash
# Must be in .github/workflows/
ls -la .github/workflows/
```

3. **Check permissions**:
```yaml
permissions:
  contents: read
  packages: write
  actions: read
```

### Permission Denied Errors

**Symptom**: `Error: Permission denied to github-actions[bot]`

**Solution**:
```yaml
# Add to workflow file
permissions:
  contents: read
  packages: write
  pull-requests: write
  issues: write
```

### Workflow Timeout

**Symptom**: Job cancelled after 6 hours

**Solutions**:

1. **Increase timeout**:
```yaml
jobs:
  test:
    timeout-minutes: 60  # Default is 360
```

2. **Split into smaller jobs**:
```yaml
jobs:
  test-group-1:
    runs-on: ubuntu-latest
    steps: ...

  test-group-2:
    runs-on: ubuntu-latest
    steps: ...
```

### Secret Not Available

**Symptom**: `Error: Input required and not supplied: token`

**Diagnosis**:
```bash
# List secrets (names only)
gh secret list

# Check if secret exists
gh secret list | grep GITHUB_TOKEN
```

**Solution**:
```bash
# Set secret
gh secret set GITHUB_TOKEN

# In workflow
${{ secrets.GITHUB_TOKEN }}
```

## Docker Build Problems

### Build Failing with Cache Issues

**Symptom**: `ERROR: failed to solve: failed to compute cache key`

**Solutions**:

1. **Clear builder cache**:
```bash
docker builder prune -a
docker buildx prune -a
```

2. **Rebuild without cache**:
```bash
docker buildx build --no-cache -f deployment/Dockerfile .
```

3. **Fix cache mounts**:
```dockerfile
# Correct syntax
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt
```

### Out of Disk Space

**Symptom**: `no space left on device`

**Solutions**:

1. **Clean Docker system**:
```bash
# Remove all unused images, containers, volumes
docker system prune -a --volumes

# Check space usage
docker system df
```

2. **GitHub Actions cleanup**:
```yaml
- name: Free disk space
  run: |
    sudo rm -rf /usr/local/lib/android
    sudo rm -rf /usr/share/dotnet
    df -h
```

### Platform Mismatch

**Symptom**: `The requested image's platform (linux/amd64) does not match the detected host platform`

**Solution**:
```bash
# Specify platform
docker buildx build --platform linux/amd64 .

# In Dockerfile
FROM --platform=linux/amd64 python:3.13-slim
```

### BuildKit Not Enabled

**Symptom**: `Unknown flag: --mount`

**Solutions**:

1. **Enable BuildKit**:
```bash
export DOCKER_BUILDKIT=1
docker build .
```

2. **In GitHub Actions**:
```yaml
- name: Set up Docker Buildx
  uses: docker/setup-buildx-action@v3

- name: Build
  uses: docker/build-push-action@v5
  with:
    context: .
    file: deployment/Dockerfile
```

## Test Failures

### Database Connection Errors

**Symptom**: `could not connect to server: Connection refused`

**Diagnosis**:
```yaml
# Check service health
services:
  postgres:
    options: >-
      --health-cmd pg_isready
      --health-interval 10s
      --health-timeout 5s
      --health-retries 5
```

**Solutions**:

1. **Wait for service**:
```yaml
- name: Wait for PostgreSQL
  run: |
    until pg_isready -h localhost -p 5432; do
      echo "Waiting for PostgreSQL..."
      sleep 2
    done
```

2. **Check connection string**:
```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/test_db
```

### Flaky Tests

**Symptom**: Tests pass locally but fail in CI intermittently

**Solutions**:

1. **Add retries**:
```python
from django.test import TransactionTestCase
from time import sleep

class FlakyTest(TransactionTestCase):
    def test_with_retry(self):
        max_retries = 3
        for i in range(max_retries):
            try:
                # Test code here
                break
            except AssertionError:
                if i == max_retries - 1:
                    raise
                sleep(1)
```

2. **Increase timeouts**:
```python
from django.test import override_settings

@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
class CeleryTest(TestCase):
    pass
```

3. **Use transactions**:
```python
from django.test import TransactionTestCase

class IsolatedTest(TransactionTestCase):
    # Each test runs in its own transaction
    pass
```

### Coverage Upload Failing

**Symptom**: `Error: Could not upload coverage to Codecov`

**Solution**:
```yaml
- name: Upload coverage
  uses: codecov/codecov-action@v3
  with:
    token: ${{ secrets.CODECOV_TOKEN }}
    fail_ci_if_error: false  # Don't fail build
    verbose: true
```

## Deployment Issues

### CapRover Deployment Failing

**Symptom**: `Error: Cannot connect to CapRover server`

**Diagnosis**:
```bash
# Test connection
curl https://captain.yourdomain.com/api/v2/login

# Check DNS
nslookup captain.yourdomain.com
```

**Solutions**:

1. **Verify credentials**:
```bash
# Check secrets
gh secret list | grep CAPROVER

# Update token
gh secret set CAPROVER_APP_TOKEN
```

2. **Fix captain-definition**:
```json
{
  "schemaVersion": 2,
  "imageName": "ghcr.io/aaronspindler/aaronspindler.com-web:latest"
}
```

### Image Not Found

**Symptom**: `Error: pull access denied for image`

**Solutions**:

1. **Check image exists**:
```bash
# List packages
gh api /user/packages/container/aaronspindler.com-web/versions

# Pull manually
docker pull ghcr.io/aaronspindler/aaronspindler.com-web:latest
```

2. **Fix image name**:
```yaml
image: ghcr.io/${{ github.repository_owner }}/aaronspindler.com-web:latest
```

### Health Check Failing

**Symptom**: Container repeatedly restarting

**Diagnosis**:
```bash
# Check logs
docker logs <container-id>

# Test health endpoint
curl http://localhost:8000/health/
```

**Solutions**:

1. **Increase start period**:
```dockerfile
HEALTHCHECK --start-period=60s --interval=30s \
  CMD curl -f http://localhost:8000/health/
```

2. **Fix health endpoint**:
```python
# health/views.py
def health_check(request):
    try:
        # Check database
        User.objects.exists()
        return JsonResponse({'status': 'healthy'})
    except Exception as e:
        return JsonResponse({'status': 'unhealthy', 'error': str(e)}, status=503)
```

## Performance Problems

### Slow Build Times

**Symptom**: Docker build takes >10 minutes

**Solutions**:

1. **Optimize Dockerfile**:
```dockerfile
# Good: Copy requirements first
COPY requirements/production.txt .
RUN pip install -r production.txt
COPY . .

# Bad: Invalidates cache on any change
COPY . .
RUN pip install -r requirements/production.txt
```

2. **Use BuildKit cache**:
```dockerfile
# syntax=docker/dockerfile:1.4
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=cache,target=/root/.cache/uv \
    uv pip install -r requirements.txt
```

3. **Use cache-from**:
```yaml
- name: Build
  uses: docker/build-push-action@v5
  with:
    cache-from: type=registry,ref=ghcr.io/user/app:buildcache
    cache-to: type=registry,ref=ghcr.io/user/app:buildcache,mode=max
```

### Slow Test Execution

**Symptom**: Tests take >30 minutes

**Solutions**:

1. **Optimize database**:
```yaml
services:
  postgres:
    command: >
      postgres
      -c fsync=off
      -c synchronous_commit=off
      -c full_page_writes=off
      -c checkpoint_segments=32
```

2. **Run tests in parallel**:
```bash
python manage.py test --parallel 4
```

3. **Use pytest-xdist**:
```bash
pytest -n auto
```

## GHCR Registry Issues

### Authentication Failed

**Symptom**: `Error: denied: permission_denied`

**Solutions**:

1. **Login to GHCR**:
```bash
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin
```

2. **In GitHub Actions**:
```yaml
- name: Login to GHCR
  uses: docker/login-action@v3
  with:
    registry: ghcr.io
    username: ${{ github.actor }}
    password: ${{ secrets.GITHUB_TOKEN }}
```

### Rate Limiting

**Symptom**: `Error: rate limit exceeded`

**Solution**:
```yaml
- name: Wait on rate limit
  if: failure()
  run: sleep 60
```

### Storage Quota Exceeded

**Symptom**: `Error: storage quota exceeded`

**Solutions**:

1. **Clean old images**:
```bash
# Delete versions older than 30 days
gh api --method DELETE \
  /user/packages/container/APP_NAME/versions/VERSION_ID
```

2. **Automated cleanup**:
```yaml
# .github/workflows/cleanup.yml
name: Cleanup
on:
  schedule:
    - cron: '0 0 * * 0'

jobs:
  cleanup:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/delete-package-versions@v4
        with:
          package-name: 'aaronspindler.com-web'
          package-type: 'container'
          min-versions-to-keep: 5
```

## Dependabot Issues

### Lockfile Out of Sync

**Symptom**: `requirements.txt is out of sync with requirements.in`

**Solution**:
```yaml
# .github/workflows/dependabot-lockfile.yml
name: Dependabot Lockfile
on:
  pull_request:
    paths:
      - 'requirements/*.in'

jobs:
  regenerate:
    if: github.actor == 'dependabot[bot]'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          ref: ${{ github.head_ref }}

      - name: Regenerate lockfiles
        run: |
          pip install uv
          for req in requirements/*.in; do
            uv pip compile "$req" -o "${req%.in}.txt" --generate-hashes
          done

      - name: Commit changes
        run: |
          git config user.name "github-actions[bot]"
          git add requirements/*.txt
          git commit -m "Regenerate lockfiles" || exit 0
          git push
```

### Merge Conflicts

**Symptom**: Dependabot PR has conflicts

**Solution**:
```bash
# Rebase Dependabot PR
gh pr checkout PR_NUMBER
git rebase main
git push --force-with-lease
```

## Quick Diagnostics

### Check Pipeline Status

```bash
# View recent runs
gh run list --limit 5

# View specific run
gh run view RUN_ID

# View job logs
gh run view RUN_ID --log

# Watch run in progress
gh run watch RUN_ID
```

### Debug Locally

```bash
# Run with act (GitHub Actions locally)
brew install act
act -j test

# Test Docker build
docker buildx build -f deployment/Dockerfile .

# Test with docker-compose
docker-compose -f docker-compose.test.yml up --abort-on-container-exit
```

### Emergency Rollback

```bash
# Deploy previous version
caprover deploy -i ghcr.io/aaronspindler/aaronspindler.com-web:sha-PREVIOUS

# Or via GitHub
gh workflow run deploy.yml -f image_tag=sha-PREVIOUS
```

### Performance Monitoring

```bash
# Check workflow timing
gh api /repos/:owner/:repo/actions/runs/RUN_ID/timing

# Resource usage in Docker
docker stats

# GitHub Actions usage
gh api /repos/:owner/:repo/actions/cache/usage
```

## Common Error Messages

### Error Reference

| Error | Cause | Solution |
|-------|-------|----------|
| `permission denied` | Missing permissions | Add permissions to workflow |
| `no space left on device` | Disk full | Clean Docker system |
| `exec format error` | Platform mismatch | Specify --platform |
| `connection refused` | Service not ready | Add health checks |
| `rate limit exceeded` | Too many API calls | Add retry logic |
| `storage quota exceeded` | Too many images | Clean old versions |
| `cannot find module` | Missing dependency | Rebuild with --no-cache |
| `ECONNRESET` | Network timeout | Increase timeout |

## Best Practices

### Preventive Measures

1. **Always test locally first**:
```bash
make test
docker buildx build .
pre-commit run --all-files
```

2. **Use matrix testing**:
```yaml
strategy:
  matrix:
    python-version: [3.11, 3.12, 3.13]
    os: [ubuntu-latest, macos-latest]
```

3. **Add retry logic**:
```yaml
- uses: nick-fields/retry@v2
  with:
    timeout_minutes: 10
    max_attempts: 3
    command: make test
```

4. **Monitor resource usage**:
```yaml
- name: Check resources
  run: |
    df -h
    free -m
    docker system df
```

## Related Documentation

- [CI/CD Pipeline](../features/ci-cd.md) - Pipeline architecture
- [Docker Architecture](../infrastructure/docker.md) - Container configuration
- [Deployment Guide](../deployment.md) - Deployment procedures
- [Development Guide](../development.md) - Local development
- [Testing Guide](../testing.md) - Test configuration
