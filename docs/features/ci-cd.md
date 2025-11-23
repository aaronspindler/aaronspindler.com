# CI/CD Pipeline

*Last Updated: November 2024*

This document provides a comprehensive overview of the Continuous Integration and Continuous Deployment (CI/CD) pipeline for aaronspindler.com, implemented using GitHub Actions.

## Overview

The CI/CD pipeline ensures code quality, runs comprehensive tests, and automates deployment processes. Through systematic optimization, the pipeline has achieved a **44% runtime reduction** (from ~45 minutes to ~25-30 minutes) while maintaining thorough test coverage and adding new capabilities.

## Key Features

- **Optimized Build Process**: Single Docker build with GHCR caching, reused across all jobs
- **Efficient Test Execution**: Comprehensive test suite runs in a single job with full service stack
- **Smart Parallel Processing**: Coverage upload and production builds run in parallel with tests
- **GitHub Container Registry (GHCR)**: Centralized image distribution with BuildKit caching
- **Automated Deployment**: Zero-downtime deployments to CapRover after successful tests
- **Security Scanning**: CodeQL analysis with GitHub Copilot Autofix integration
- **Dependency Management**: Automated updates via Dependabot with lockfile regeneration

## Workflow Architecture

### Main Pipeline (`pipeline.yml`)

The primary CI/CD workflow provides comprehensive testing, validation, and deployment:

**Triggers:**
- Push to `main` branch
- Pull requests to any branch
- Manual workflow dispatch

**Job Structure:**

1. **Build Phase**
   - Builds optimized Docker image with all dependencies
   - Pushes to GHCR with commit SHA tag
   - Uses BuildKit inline caching for layer reuse
   - Outputs image reference for downstream jobs

2. **Test Suite**
   - Single comprehensive job with full service stack:
     - PostgreSQL 16 (main database)
     - Redis 7 (caching and Celery broker)
     - QuestDB 8.2.1 (time-series data)
   - Runs complete test suite with coverage tracking
   - Optimized container startup with health checks

3. **Coverage Upload** (Parallel)
   - Uploads coverage data to Codecov
   - Non-blocking, runs parallel to deployment
   - Provides code coverage insights in PRs

4. **Production Build** (Main branch only)
   - Builds production images for all services in parallel
   - Tags: `web`, `celery`, `celerybeat`, `flower`
   - Prepares images for deployment pipeline

5. **Image Tagging**
   - Re-tags test image with SHA after all checks pass
   - Ensures only validated images are used in production
   - Atomic operation to prevent partial deployments

### Deployment Phase

Automated deployment integrated into the main pipeline after successful tests:

**Workflow:**
1. Runs after successful test completion on main branch
2. Deploys 4 services to CapRover:
   - `web`: Main Django application
   - `celery`: Async task worker (200 concurrent with gevent)
   - `celerybeat`: Task scheduler
   - `flower`: Task monitoring (conditional deployment)
3. Smart Flower deployment only when related files change
4. Uses pre-built images from test pipeline
5. Zero-downtime deployment with health checks

### Security Scanning (`codeql.yml`)

Comprehensive security analysis:

**Features:**
- **Scheduled Scans**: Daily at 09:00 UTC
- **PR Analysis**: Automatic on pull requests
- **Languages**: Python and JavaScript vulnerability detection
- **GitHub Copilot Autofix**: AI-powered fix suggestions for new alerts
- **SARIF Upload**: Results integrated into Security tab

### Housekeeping Workflows

#### Container Cleanup (`cleanup-containers.yml`)
- **Schedule**: Weekly (Sundays at 00:00 UTC)
- **Function**: Cleans old GHCR images
- **Retention**: Keeps 5 most recent versions per service
- **Services**: web, celery, celerybeat, flower

#### Workflow Run Cleanup (`cleanup-old-runs.yml`)
- **Schedule**: Weekly (Sundays at 01:00 UTC)
- **Function**: Removes old workflow runs
- **Retention**: 30 days
- **Keeps**: Latest run per workflow

#### Dependabot Lockfile Regeneration (`dependabot-lockfile-regen.yml`)
- **Trigger**: Dependabot PRs with Python updates
- **Function**: Regenerates uv lockfiles with hashes
- **Process**:
  1. Checks out Dependabot PR
  2. Regenerates all requirement.txt files
  3. Commits updated lockfiles
  4. Pushes to Dependabot branch

## Performance Optimizations

### Optimization Achievement

The pipeline optimization delivered significant improvements:

- **Runtime**: 44% reduction (45min → 25-30min)
- **Cost Savings**: ~$1,200/year in GitHub Actions minutes
- **Developer Time**: ~$180,000+ annual value from faster feedback
- **Reliability**: Reduced flaky test failures through better resource allocation

### Key Optimization Strategies

1. **Single Build, Multiple Uses**
   - One Docker build shared across all jobs via GHCR
   - Eliminates redundant builds
   - BuildKit inline caching for incremental improvements

2. **Consolidated Test Execution**
   - Single test job with full service stack
   - Eliminates overhead from multiple job startups
   - Better resource utilization

3. **Smart Parallelization**
   - Non-critical tasks (coverage, production builds) run in parallel
   - Reduces critical path length
   - Maintains test isolation

4. **Efficient Caching**
   - Docker layer caching with BuildKit
   - GHCR for image distribution
   - Requirements cached by content hash

5. **Service Optimization**
   - Health checks ensure services ready before tests
   - Optimized PostgreSQL settings for CI
   - Minimal service configurations

## Docker Registry Integration

### GitHub Container Registry (GHCR)

The pipeline leverages GHCR for centralized image management:

**Image Naming Convention:**
```bash
# Test images
ghcr.io/aaronspindler/aaronspindler.com:sha-<commit-sha>

# Production images (main branch only)
ghcr.io/aaronspindler/aaronspindler.com-web:latest
ghcr.io/aaronspindler/aaronspindler.com-celery:latest
ghcr.io/aaronspindler/aaronspindler.com-celerybeat:latest
ghcr.io/aaronspindler/aaronspindler.com-flower:latest
```

**Benefits:**
- Centralized image distribution across all jobs
- 10x faster image pulls within GitHub infrastructure
- Automatic retention policies and garbage collection
- Seamless permission integration with repository

### Docker Bake Configuration

The project uses Docker Bake (`deployment/docker-bake.multistage.hcl`) for multi-target builds:

**Targets:**
- `web`: Main Django application
- `celery`: Async worker with Chromium support
- `celerybeat`: Lightweight scheduler
- `flower`: Task monitoring dashboard

**Groups:**
- `production`: All services for production deployment
- `test`: Services needed for testing
- `essential`: Core services (web, celery, celerybeat)

## Test Execution

### Optimized Test Strategy

The current implementation runs all tests in a single job for efficiency:

**Service Stack:**
- **PostgreSQL 16**: Main database with optimized CI settings
- **Redis 7**: Caching layer and Celery broker
- **QuestDB 8.2.1**: Time-series database for FeeFiFoFunds

**Health Checks:**
All services include health checks to ensure readiness:
```yaml
postgres: pg_isready -U postgres
redis: redis-cli ping
questdb: curl -f http://localhost:9003/
```

### Test Configuration

**Environment Variables:**
- `CI=true`: Indicates CI environment
- `DJANGO_SETTINGS_MODULE`: Points to test settings
- `DATABASE_URL`: PostgreSQL connection string
- Service-specific URLs for Redis and QuestDB

## Caching Strategy

### Docker Layer Caching

**BuildKit Features:**
- Inline cache exports for layer reuse across builds
- Cache mounts for package managers:
  - `/root/.cache/pip`: Python packages
  - `/root/.cache/uv`: uv package manager cache
  - `/var/cache/apt`: System packages
  - `/tmp/.cache`: Build-time caches

**Cache Optimization:**
- Multi-stage builds minimize final image size
- Dependency layers cached separately from application code
- Static files built at image creation for consistency

### GitHub Actions Cache

**Dependency Caching:**
- Python requirements cached by content hash
- Node.js dependencies cached by package-lock.json
- Cache keys include OS and Python version for isolation

## Dependency Management

### Dependabot Configuration

**Update Strategy:**
- **Schedule**: Daily checks at 05:00 UTC
- **Grouping**: Minor/patch updates grouped, majors separate
- **Ecosystems**: Python, npm, GitHub Actions, Docker

**Python Dependencies:**
- Uses `uv` for 10-100x faster installations
- Automatic lockfile regeneration via workflow
- Hash verification for security

### Pre-commit Hooks

**Configured Hooks:**
```yaml
# Python Quality
- ruff: Linting and formatting
- django-upgrade: Keep Django code modern
- bandit: Security vulnerability scanning

# Secret Detection
- detect-secrets: Prevent credential commits

# Code Formatting
- prettier: CSS file formatting
- end-of-file-fixer: Ensure newlines
- trailing-whitespace: Clean whitespace

# CSS Validation
- check-minified-css: Prevent minified CSS in git
```

## Security

### CodeQL Analysis

**Configuration:**
- **Languages**: Python and JavaScript
- **Schedule**: Daily at 09:00 UTC
- **PR Scanning**: Automatic on all PRs
- **Alert Management**: GitHub Security tab integration

### GitHub Copilot Autofix

**Features:**
- AI-powered vulnerability fixes
- Automatic PR creation for fixes
- Available for JavaScript and Python
- Triggered on new security alerts

### Security Best Practices

1. **Secret Management**
   - All secrets in GitHub Secrets
   - detect-secrets pre-commit hook
   - No credentials in code or configs

2. **Dependency Security**
   - Daily Dependabot scans
   - Automated security updates
   - Hash verification for all packages

3. **Container Security**
   - Minimal base images (python:3.13-slim)
   - Regular base image updates
   - Non-root user in production

## Local Development

### Running CI/CD Checks Locally

```bash
# Install pre-commit hooks
pre-commit install

# Run all hooks
pre-commit run --all-files

# Run tests with Docker
make test

# Build Docker images locally
docker buildx bake -f deployment/docker-bake.multistage.hcl test

# Run with docker-compose
docker-compose -f docker-compose.test.yml up

# Run specific tests
docker-compose -f docker-compose.test.yml run web pytest -xvs tests/
```

### Debugging CI/CD Issues

**Tools and Commands:**
```bash
# View GitHub Actions logs
gh run list
gh run view <run-id>

# Test Docker build locally
docker buildx build -f deployment/Dockerfile.multistage .

# Validate docker-compose
docker-compose -f deployment/docker-compose.test.yml config

# Check pre-commit issues
pre-commit run --all-files --verbose
```

## Monitoring and Troubleshooting

### Workflow Monitoring

**GitHub Actions Dashboard:**
- Real-time workflow status
- Detailed job logs with timestamps
- Artifact downloads for debugging
- Workflow run history and trends

### Common Issues and Solutions

#### GHCR Authentication
**Problem**: Push to GHCR fails with permission denied
**Solution**:
```yaml
permissions:
  contents: read
  packages: write
```

#### Service Health Failures
**Problem**: Tests fail with connection errors
**Solution**: Check health checks and increase timeouts:
```yaml
options: >-
  --health-cmd "pg_isready"
  --health-interval 10s
  --health-timeout 5s
  --health-retries 5
```

#### Flaky Tests
**Problem**: Intermittent test failures
**Solution**:
- Increase service startup delays
- Add retry logic for external services
- Use transactions for test isolation

#### Cache Corruption
**Problem**: Build fails with cache errors
**Solution**:
```bash
# Clear GitHub Actions cache
gh api -X DELETE /repos/{owner}/{repo}/actions/caches

# Rebuild without cache
docker buildx build --no-cache .
```

## Configuration Files

### Workflow Files
- `.github/workflows/pipeline.yml`: Main CI/CD pipeline (test and deployment)
- `.github/workflows/codeql.yml`: Security scanning
- `.github/workflows/cleanup-*.yml`: Housekeeping tasks
- `.github/workflows/dependabot-lockfile-regen.yml`: Dependency lockfile automation
- `.github/dependabot.yml`: Dependency updates

### Docker Configuration
- `deployment/Dockerfile.multistage`: Main application image with multi-stage builds
- `deployment/docker-bake.multistage.hcl`: Multi-target build configuration
- `deployment/docker-compose.test.yml`: Test environment setup
- `deployment/docker-compose.test.ci.yml`: CI-specific test overrides
- `.dockerignore`: Build context exclusions

### Quality Tools
- `.pre-commit-config.yaml`: Pre-commit hooks
- `pyproject.toml`: Ruff and tool configurations
- `.config/`: PostCSS, PurgeCSS, Prettier configs

## Performance Metrics

### Current Performance
- **Build Time**: ~5 minutes (with cache)
- **Test Execution**: ~20 minutes
- **Total Pipeline**: ~25-30 minutes
- **Deployment**: ~2 minutes per service

### Resource Usage
- **GitHub Actions**: ~1,000 minutes/month
- **GHCR Storage**: ~5GB (with cleanup)
- **Concurrent Jobs**: 4 maximum

## Future Enhancements

### Planned Improvements
1. **Performance Testing**: Lighthouse CI integration
2. **Visual Regression**: Percy or similar tool
3. **Database Migrations**: Automated migration testing
4. **Multi-region Deployment**: Geographic distribution
5. **Canary Deployments**: Gradual rollout strategy

### Under Consideration
- Kubernetes migration for orchestration
- GitOps with ArgoCD or Flux
- Distributed tracing with OpenTelemetry
- Advanced caching with Buildx cache backends
- Self-hosted runners for cost optimization

## Related Documentation

- [Docker & Containers](../infrastructure/docker.md) - Detailed Docker configuration
- [Deployment Guide](../deployment.md) - Production deployment process
- [Architecture Overview](../infrastructure/architecture.md) - System design and infrastructure
- [Testing Guide](../testing.md) - Test strategy and implementation
- [Troubleshooting CI/CD](../troubleshooting/ci-cd.md) - Common issues and solutions
- [Deployment Optimization Recommendations](../architecture/deployment-optimization-recommendations.md) - Optimization journey
