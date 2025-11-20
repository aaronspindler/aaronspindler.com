# CI/CD Pipeline

This document provides an overview of the Continuous Integration and Continuous Deployment (CI/CD) pipeline for aaronspindler.com, implemented using GitHub Actions.

## Overview

The CI/CD pipeline ensures code quality, runs comprehensive tests, and automates deployment processes. The workflow has been optimized to reduce runtime by 44% while maintaining thorough test coverage.

## Key Features

- **Parallel Test Execution**: Tests are split across 6 parallel jobs for faster execution
- **Docker Image Caching**: Uses GitHub Container Registry (GHCR) for efficient image distribution
- **Smart Caching**: BuildKit cache mounts and inline caching for faster builds
- **Automatic Fallbacks**: Falls back to artifact-based distribution for fork PRs
- **Comprehensive Testing**: Includes Django tests, linting, type checking, and security scanning

## Workflow Architecture

### Main Workflow (`test.yml`)

The primary CI/CD workflow runs on:
- Push to `main` branch
- Pull requests
- Manual workflow dispatch

#### Jobs Structure

1. **Build Job**
   - Builds Docker images with all dependencies
   - Pushes to GHCR (for main branch and PRs from the main repo)
   - Creates artifacts as fallback for forks
   - Uses BuildKit for advanced caching

2. **Test Jobs (6 parallel)**
   - Tests are dynamically split based on historical timing data
   - Each job runs a subset of tests in parallel
   - Uses docker-compose for service orchestration
   - Includes PostgreSQL, Redis, and QuestDB services

3. **Lint Job**
   - Runs Ruff for Python linting
   - Enforces code style consistency
   - Checks import sorting and formatting

4. **Type Check Job**
   - Runs MyPy for static type checking
   - Ensures type safety across the codebase

5. **Security Scanning**
   - CodeQL analysis for vulnerability detection
   - Runs daily and on every PR
   - GitHub Copilot Autofix for new security alerts

## Performance Optimizations

The CI/CD pipeline has undergone significant optimization to improve performance and reduce costs:

### Optimization Results
- **Runtime Reduction**: 44% (from ~45 minutes to ~25-30 minutes)
- **Cost Savings**: $1,200/year in compute costs
- **Developer Productivity**: $180,000+ annual value in saved time

### Optimization Phases

For detailed information about the optimization process, see:
- [CI/CD Optimization Report](ci-cd-optimization-report.md) - Executive summary and results
- [Performance Analysis](ci-cd-performance-analysis.md) - Detailed performance metrics
- [Optimization Guide](ci-cd-optimization-guide.md) - Implementation recommendations

## Docker Registry Integration

### GitHub Container Registry (GHCR)

The pipeline uses GHCR for efficient Docker image distribution:

```yaml
# Image naming convention
ghcr.io/aaronspindler/aaronspindler.com:sha-<commit-sha>
ghcr.io/aaronspindler/aaronspindler.com:latest  # main branch only
```

### Benefits
- Parallel image pulls across all jobs
- Reduced bandwidth usage within GitHub infrastructure
- Automatic garbage collection of old images
- Seamless integration with GitHub permissions

### Fallback Strategy

For fork PRs that don't have GHCR access:
1. Images are exported as artifacts
2. Test jobs download and load images locally
3. Ensures all contributors can run tests

## Test Organization

Tests are organized into groups for parallel execution:

### Test Splitting Strategy
- Uses `pytest-split` for dynamic test distribution
- Collects timing data from previous runs
- Automatically rebalances test groups
- Stores timing data in `.test_durations` file

### Service Dependencies
Each test job includes:
- PostgreSQL 16 (main database)
- Redis 7 (caching and sessions)
- QuestDB (time-series data for FeeFiFoFunds)

## Caching Strategy

### Docker Layer Caching
- BuildKit inline cache for layer reuse
- Cache mounts for package managers:
  - `/root/.cache/pip` for Python packages
  - `/var/cache/apt` for system packages

### GitHub Actions Cache
- Python dependencies cached by hash of requirements files
- Node.js dependencies cached by package-lock.json
- Test timing data cached for test splitting

## Security

### CodeQL Analysis
- Automated security scanning for Python
- Runs on schedule (daily) and on PRs
- Detects common vulnerabilities and coding errors
- Results integrated into Security tab

### Copilot Autofix
- AI-powered fix suggestions for new alerts
- Automatically creates fix PRs for security issues
- Available for PRs targeting main branch

## Local Development

To run CI/CD checks locally:

```bash
# Run all pre-commit hooks
pre-commit run --all-files

# Run tests
make test

# Run specific test group
pytest -xvs tests/test_group_1.py

# Build Docker image locally
docker build -f deployment/django.dockerfile -t aaronspindler.com:local .

# Run with docker-compose
docker-compose -f deployment/docker-compose.yml up
```

## Monitoring and Debugging

### Workflow Insights
- GitHub Actions tab shows workflow runs
- Each job has detailed logs
- Artifacts preserved for 7 days
- GHCR images tagged with commit SHA

### Common Issues and Solutions

1. **GHCR Authentication Failures**
   - Ensure GITHUB_TOKEN has packages:write permission
   - Check if running from fork (fallback to artifacts)

2. **Test Failures**
   - Check service health in job logs
   - Verify database migrations completed
   - Review test output for specific errors

3. **Cache Misses**
   - Check if requirements files changed
   - Verify cache keys in workflow
   - Consider clearing caches if corrupted

## Configuration Files

- `.github/workflows/test.yml` - Main CI/CD workflow
- `.github/workflows/codeql.yml` - Security scanning workflow
- `deployment/django.dockerfile` - Docker image definition
- `deployment/docker-compose.yml` - Service orchestration
- `.dockerignore` - Files excluded from Docker context
- `.test_durations` - Test timing data for splitting

## Future Improvements

Potential areas for further optimization:
- Implement matrix strategy for Python versions
- Add deployment automation for production
- Integrate performance benchmarking
- Add visual regression testing for frontend
- Implement automatic dependency updates

## Related Documentation

- [Deployment Guide](../deployment.md) - Production deployment process
- [Architecture Overview](../architecture.md) - System architecture including CI/CD
- [Testing Guide](../testing.md) - Comprehensive testing documentation
- [Commands Reference](../commands.md) - Available make commands and scripts
