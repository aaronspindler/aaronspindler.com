# Docker & Container Architecture

*Last Updated: November 2024*

This document provides comprehensive documentation of the Docker containerization strategy, multi-service architecture, and build configurations for aaronspindler.com.

## Overview

The project uses a sophisticated Docker-based architecture with multiple specialized containers, optimized builds using Docker Bake, and efficient deployment through GitHub Container Registry (GHCR).

## Container Architecture

### Service Containers

#### Web Container (`deployment/Dockerfile`)
**Purpose**: Main Django application server
**Base Image**: `python:3.13-slim`
**Key Features**:
- Multi-stage build for size optimization
- Chromium and Node.js for screenshot generation
- WhiteNoise for static file serving
- Health check endpoint at `/health/`
- Non-root user for security

**Build Optimizations**:
- Static files collected at build time
- CSS/JS optimization during build
- Dependency caching with BuildKit
- Final image ~500MB

#### Celery Worker (`deployment/celery.Dockerfile`)
**Purpose**: Asynchronous task processing
**Base Image**: Extends web container
**Key Features**:
- Gevent pool with 200 concurrent workers
- Chromium support for screenshot tasks
- Memory-optimized for high concurrency
- Automatic task retry logic

**Configuration**:
```bash
celery -A config.celery_app worker \
  --pool=gevent \
  --concurrency=200 \
  --loglevel=info
```

#### Celerybeat Scheduler (`deployment/celerybeat.Dockerfile`)
**Purpose**: Periodic task scheduling
**Base Image**: Extends web container (lightweight)
**Key Features**:
- DatabaseScheduler for dynamic schedules
- Minimal resource footprint
- Persistent schedule storage
- Health monitoring

**Configuration**:
```bash
celery -A config.celery_app beat \
  --loglevel=info \
  --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

#### Flower Monitor (`deployment/flower.Dockerfile`)
**Purpose**: Celery task monitoring dashboard
**Base Image**: Extends web container
**Key Features**:
- Real-time task monitoring
- Worker status tracking
- Task history persistence
- Optional basic authentication

**Configuration**:
```bash
celery -A config.celery_app flower \
  --persistent=True \
  --db=/data/flower.db \
  --state_save_interval=30000
```

### Support Services

#### PostgreSQL 16
**Purpose**: Primary application database
**Features**:
- Full-text search support
- JSON field support
- Optimized for Django ORM
- CI-specific configurations

#### Redis 7
**Purpose**: Caching and message broker
**Features**:
- Session storage
- Celery broker/backend
- Cache backend
- Pub/sub support

#### QuestDB 8.2.1
**Purpose**: Time-series data for FeeFiFoFunds
**Features**:
- 50K-100K records/sec ingestion
- SQL interface
- REST API
- Prometheus metrics

## Docker Bake Configuration

### Configuration File (`docker-bake.hcl`)

```hcl
variable "REGISTRY" {
  default = "ghcr.io/aaronspindler"
}

variable "TAG" {
  default = "latest"
}

target "web" {
  dockerfile = "deployment/Dockerfile"
  context = "."
  tags = ["${REGISTRY}/aaronspindler.com-web:${TAG}"]
  cache-from = ["type=registry,ref=${REGISTRY}/aaronspindler.com-web:buildcache"]
  cache-to = ["type=registry,ref=${REGISTRY}/aaronspindler.com-web:buildcache,mode=max"]
  platforms = ["linux/amd64"]
}

target "celery" {
  dockerfile = "deployment/celery.Dockerfile"
  context = "."
  tags = ["${REGISTRY}/aaronspindler.com-celery:${TAG}"]
  inherits = ["web"]
}

target "celerybeat" {
  dockerfile = "deployment/celerybeat.Dockerfile"
  context = "."
  tags = ["${REGISTRY}/aaronspindler.com-celerybeat:${TAG}"]
  inherits = ["web"]
}

target "flower" {
  dockerfile = "deployment/flower.Dockerfile"
  context = "."
  tags = ["${REGISTRY}/aaronspindler.com-flower:${TAG}"]
  inherits = ["web"]
}

group "production" {
  targets = ["web", "celery", "celerybeat", "flower"]
}

group "essential" {
  targets = ["web", "celery", "celerybeat"]
}

group "test" {
  targets = ["web"]
}
```

### Build Commands

```bash
# Build all production images
docker buildx bake -f docker-bake.hcl production

# Build with custom tag
docker buildx bake -f docker-bake.hcl --set "*.tags=myregistry/myapp:v1.0" production

# Build for multiple platforms
docker buildx bake -f docker-bake.hcl --set "*.platform=linux/amd64,linux/arm64" production

# Push to registry
docker buildx bake -f docker-bake.hcl production --push
```

## Dockerfile Optimization Strategies

### Multi-Stage Builds

```dockerfile
# Stage 1: Build dependencies
FROM python:3.13-slim as builder
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/ /requirements/
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r /requirements/production.txt

# Stage 2: Final image
FROM python:3.13-slim
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*.whl
```

### BuildKit Cache Mounts

```dockerfile
# Syntax for BuildKit
# syntax=docker/dockerfile:1.4

# Cache mount for package managers
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=cache,target=/root/.cache/uv \
    uv pip install -r requirements/production.txt

# Cache mount for apt
RUN --mount=type=cache,target=/var/cache/apt \
    --mount=type=cache,target=/var/lib/apt \
    apt-get update && apt-get install -y chromium
```

### Layer Optimization

```dockerfile
# Combine commands to reduce layers
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        chromium \
        chromium-driver \
        fonts-liberation \
        nodejs \
        npm \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy requirements before code for better caching
COPY requirements/ /app/requirements/
RUN pip install -r /app/requirements/production.txt

# Copy application code last
COPY . /app/
```

## Docker Compose Configurations

### Test Environment (`docker-compose.test.yml`)

```yaml
version: '3.8'

services:
  web:
    build:
      context: .
      dockerfile: deployment/Dockerfile
    environment:
      - DATABASE_URL=postgres://postgres:postgres@postgres:5432/test_db
      - REDIS_URL=redis://redis:6379/0
      - QUESTDB_HOST=questdb
      - CI=true
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      questdb:
        condition: service_healthy
    volumes:
      - ./staticfiles:/app/staticfiles
      - ./media:/app/media
    command: python manage.py test

  postgres:
    image: postgres:16-alpine
    environment:
      - POSTGRES_DB=test_db
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
    command: >
      postgres
      -c shared_buffers=256MB
      -c max_connections=200
      -c fsync=off
      -c synchronous_commit=off
      -c full_page_writes=off
      -c checkpoint_segments=64
      -c checkpoint_completion_target=0.9

  redis:
    image: redis:7-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  questdb:
    image: questdb/questdb:8.2.1
    environment:
      - QDB_CAIRO_SQL_COPY_BUFFER_SIZE=4M
      - QDB_TELEMETRY_ENABLED=false
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9003/"]
      interval: 10s
      timeout: 5s
      retries: 5
```

### Local Development

```yaml
version: '3.8'

services:
  web:
    build:
      context: .
      dockerfile: deployment/Dockerfile
      target: development
    volumes:
      - .:/app
      - /app/node_modules
    ports:
      - "8000:8000"
    environment:
      - DEBUG=True
      - DJANGO_SETTINGS_MODULE=config.settings.local
    command: python manage.py runserver 0.0.0.0:8000
```

## Container Security

### Non-Root User

```dockerfile
# Create non-root user
RUN groupadd -r django && useradd -r -g django django

# Change ownership
RUN chown -R django:django /app

# Switch to non-root user
USER django
```

### Security Scanning

```dockerfile
# Scan for vulnerabilities
RUN pip install safety && safety check

# Use minimal base images
FROM python:3.13-slim

# Remove unnecessary packages
RUN apt-get purge -y --auto-remove \
    && rm -rf /var/lib/apt/lists/*
```

### Secret Management

```dockerfile
# Use build args for sensitive data
ARG DATABASE_URL
ENV DATABASE_URL=${DATABASE_URL}

# Never hardcode secrets
# Use environment variables or mounted secrets
```

## Health Checks

### Application Health Check

```dockerfile
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health/')" || exit 1
```

### Service Health Endpoints

```python
# health/views.py
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
import redis

def health_check(request):
    """Comprehensive health check endpoint."""
    checks = {
        'database': check_database(),
        'cache': check_cache(),
        'redis': check_redis(),
        'static_files': check_static_files(),
    }

    healthy = all(checks.values())
    status_code = 200 if healthy else 503

    return JsonResponse({
        'status': 'healthy' if healthy else 'unhealthy',
        'checks': checks,
        'version': settings.VERSION,
    }, status=status_code)
```

## Registry Management

### GitHub Container Registry (GHCR)

**Authentication**:
```bash
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin
```

**Image Naming Convention**:
```
ghcr.io/aaronspindler/aaronspindler.com-{service}:{tag}
```

**Tags**:
- `latest`: Latest stable release
- `sha-{commit}`: Specific commit
- `v{version}`: Semantic version
- `main`: Latest from main branch

### Image Cleanup

**Automated Cleanup Workflow**:
```yaml
name: Cleanup Containers
on:
  schedule:
    - cron: '0 0 * * 0'  # Weekly

jobs:
  cleanup:
    runs-on: ubuntu-latest
    steps:
      - name: Delete old images
        uses: actions/github-script@v6
        with:
          script: |
            const packages = ['web', 'celery', 'celerybeat', 'flower'];
            for (const pkg of packages) {
              // Keep latest 5 versions
              const versions = await github.rest.packages.getAllPackageVersionsForPackageOwnedByOrg({
                package_type: 'container',
                package_name: `aaronspindler.com-${pkg}`,
                org: 'aaronspindler',
              });

              // Delete old versions
              for (const version of versions.data.slice(5)) {
                await github.rest.packages.deletePackageVersionForOrg({
                  package_type: 'container',
                  package_name: `aaronspindler.com-${pkg}`,
                  org: 'aaronspindler',
                  package_version_id: version.id,
                });
              }
            }
```

## Performance Optimization

### Image Size Reduction

**Strategies**:
1. **Multi-stage builds**: Separate build and runtime
2. **Minimal base images**: Use `-slim` or `-alpine` variants
3. **Layer caching**: Order commands by change frequency
4. **Cleanup in same layer**: Remove temporary files immediately
5. **Exclude unnecessary files**: Use `.dockerignore`

**Example .dockerignore**:
```
# Version control
.git
.gitignore

# Python
__pycache__
*.pyc
*.pyo
*.pyd
.Python
env/
venv/
.venv/
pip-log.txt
pip-delete-this-directory.txt
.tox/
.coverage
.coverage.*
.cache
coverage.xml
*.cover
.pytest_cache/

# Django
*.log
local_settings.py
media/
staticfiles/

# IDE
.idea
.vscode
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Documentation
docs/
*.md

# Tests
tests/
test/
```

### Build Performance

**Optimization Techniques**:
1. **BuildKit**: Enable with `DOCKER_BUILDKIT=1`
2. **Inline cache**: Export cache with build
3. **Registry cache**: Use GHCR as cache source
4. **Parallel builds**: Use Docker Bake
5. **Content-addressed storage**: Deduplicate layers

**Benchmark Results**:
- Cold build: ~10 minutes
- Cached build: ~2 minutes
- Layer cache hit rate: ~85%
- Image size reduction: ~40%

## Monitoring and Logging

### Container Metrics

**Docker Stats**:
```bash
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
```

**Prometheus Metrics**:
```yaml
# docker-compose.yml
cadvisor:
  image: gcr.io/cadvisor/cadvisor:latest
  ports:
    - 8080:8080
  volumes:
    - /:/rootfs:ro
    - /var/run:/var/run:ro
    - /sys:/sys:ro
    - /var/lib/docker/:/var/lib/docker:ro
```

### Logging Configuration

**Centralized Logging**:
```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
    labels: "service,environment"
```

**Application Logging**:
```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            'class': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json'
        }
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console']
    }
}
```

## Troubleshooting

### Common Issues

#### 1. Container Won't Start
```bash
# Check logs
docker logs <container-id>

# Inspect container
docker inspect <container-id>

# Debug interactively
docker run -it --entrypoint /bin/bash <image>
```

#### 2. Permission Errors
```dockerfile
# Fix ownership issues
RUN chown -R django:django /app
USER django
```

#### 3. Network Connectivity
```bash
# Test DNS resolution
docker exec <container> nslookup postgres

# Check network
docker network inspect <network-name>
```

#### 4. Resource Constraints
```yaml
# Set resource limits
services:
  web:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

## Migration Guide

### From Docker Compose to Kubernetes

```yaml
# kubernetes/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      containers:
      - name: web
        image: ghcr.io/aaronspindler/aaronspindler.com-web:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
        livenessProbe:
          httpGet:
            path: /health/
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
```

## Best Practices

### Development Workflow

1. **Local Development**:
   - Use docker-compose for service dependencies
   - Mount code volumes for hot reloading
   - Use development Dockerfile target

2. **Testing**:
   - Run tests in containers matching production
   - Use test-specific configurations
   - Isolate test databases

3. **CI/CD**:
   - Build once, use everywhere
   - Tag with commit SHA
   - Use GHCR for distribution

4. **Production**:
   - Use specific version tags
   - Implement health checks
   - Monitor resource usage

### Security Checklist

- [ ] Use non-root users
- [ ] Scan images for vulnerabilities
- [ ] Use minimal base images
- [ ] Don't hardcode secrets
- [ ] Keep base images updated
- [ ] Use read-only filesystems where possible
- [ ] Implement network policies
- [ ] Enable security monitoring

## Related Documentation

- [CI/CD Pipeline](../features/ci-cd.md) - Build and deployment automation
- [Deployment Guide](../deployment.md) - Production deployment process
- [Architecture Overview](architecture.md) - System architecture
- [Troubleshooting CI/CD](../troubleshooting/ci-cd.md) - Build and deployment issues
