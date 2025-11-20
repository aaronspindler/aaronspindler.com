# GitHub Actions Workflow Optimization Recommendations

## Executive Summary

Current workflow runtime: ~45 minutes
Optimized workflow runtime: ~15-20 minutes
**Potential time savings: 55-67% reduction**

## Bottleneck Analysis

### Current Issues
1. **Docker Image Distribution** (20-30 min): 6 artifact downloads of 2-3GB image
2. **Broken Pip Cache** (6-12 min): Using `--no-cache-dir` flag
3. **Database Stack Redundancy** (9-18 min): 6 separate database startups
4. **Test Group Imbalance** (5-8 min): Uneven test distribution
5. **Sequential Coverage Upload** (3-5 min): Waiting for all tests before upload

---

## Priority 1: Docker Registry Distribution (20-30 min savings)

### Current Problematic Code

```yaml
# Lines 97-110: Artifact-based distribution
- name: Save Docker image to file with optimized compression
  run: |
    docker save ${{ env.DOCKER_IMAGE_NAME }}:latest | pigz -6 > "${{ env.DOCKER_IMAGE_ARCHIVE }}"
    echo "📦 Compressed image size: $(du -h "${{ env.DOCKER_IMAGE_ARCHIVE }}" | cut -f1)"

- name: Upload Docker image as artifact
  uses: actions/upload-artifact@v5
  with:
    name: docker-image
    path: ${{ env.DOCKER_IMAGE_ARCHIVE }}
    retention-days: 1

# Lines 166-180: Download and load in each job (repeated 6 times)
- name: Download Docker image artifact
  uses: actions/download-artifact@v6
  with:
    name: docker-image
    path: /tmp

- name: Load Docker image with optimized decompression
  run: |
    pigz -dc "/tmp/${{ env.DOCKER_IMAGE_ARCHIVE }}" | docker load
```

### Optimized Implementation

```yaml
# =============================================================================
# OPTIMIZED: Docker Registry Distribution
# Time savings: 20-30 minutes
# =============================================================================

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}/test-runner
  IMAGE_TAG: ${{ github.sha }}

jobs:
  build-and-push-test-image:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    permissions:
      contents: read
      packages: write  # Required for pushing to GHCR
    outputs:
      image: ${{ steps.meta.outputs.image }}
    steps:
      - uses: actions/checkout@v5

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
        with:
          driver-opts: |
            network=host
            image=moby/buildkit:buildx-stable-1

      - name: Log in to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Generate image metadata
        id: meta
        run: |
          IMAGE="${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ env.IMAGE_TAG }}"
          echo "image=${IMAGE}" >> $GITHUB_OUTPUT
          echo "📦 Test image will be: ${IMAGE}"

      - name: Build and push test image to GHCR
        uses: docker/bake-action@v5
        env:
          REGISTRY: ${{ env.REGISTRY }}
          IMAGE_PREFIX: ${{ github.repository }}
          TAG: ${{ env.IMAGE_TAG }}
        with:
          files: deployment/docker-bake.hcl
          targets: test
          push: true  # Push to registry instead of saving as artifact
          set: |
            *.cache-from=type=gha,scope=test-${{ env.DOCKER_CACHE_VERSION }}
            *.cache-from=type=registry,ref=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:cache
            *.cache-to=type=gha,mode=max,scope=test-${{ env.DOCKER_CACHE_VERSION }}
            *.cache-to=type=registry,ref=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:cache,mode=max

  django-checks:
    runs-on: ubuntu-latest
    needs: build-and-push-test-image
    timeout-minutes: 10
    permissions:
      packages: read  # Required for pulling from GHCR
    strategy:
      matrix:
        check: [migrations, system]
    steps:
      - uses: actions/checkout@v5

      - name: Log in to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      # OPTIMIZED: Pull image directly from registry (parallel, fast)
      - name: Pull test image from registry
        run: |
          IMAGE="${{ needs.build-and-push-test-image.outputs.image }}"
          echo "📥 Pulling image: ${IMAGE}"
          docker pull "${IMAGE}"
          # Tag for docker-compose compatibility
          docker tag "${IMAGE}" test-runner:latest
          docker images | grep test-runner

      - name: Start required services
        run: |
          # Same as before...
          docker compose ${{ env.TEST_COMPOSE_FILES }} up -d postgres redis questdb

      - name: Run Django ${{ matrix.check }} check
        run: |
          # Same as before...
          docker compose ${{ env.TEST_COMPOSE_FILES }} run --rm test_runner \
            python manage.py check --settings=config.settings_test

  test-suite:
    runs-on: ubuntu-latest
    needs: build-and-push-test-image
    timeout-minutes: 30
    permissions:
      packages: read  # Required for pulling from GHCR
    strategy:
      fail-fast: false
      matrix:
        test-group:
          - name: "core"
            apps: "accounts pages config"
          - name: "blog"
            apps: "blog"
          - name: "photos"
            apps: "photos"
          - name: "utils"
            apps: "utils"
    steps:
      - uses: actions/checkout@v5

      - name: Log in to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      # OPTIMIZED: Pull image directly from registry (parallel, fast)
      - name: Pull test image from registry
        run: |
          IMAGE="${{ needs.build-and-push-test-image.outputs.image }}"
          echo "📥 Pulling image: ${IMAGE}"
          docker pull "${IMAGE}"
          # Tag for docker-compose compatibility
          docker tag "${IMAGE}" test-runner:latest

      # Rest of the job remains the same...
```

### Benefits
- **Parallel downloads**: All jobs pull from registry simultaneously
- **Layer caching**: Docker registry leverages layer deduplication
- **No compression overhead**: No pigz compression/decompression
- **Faster transfers**: Registry is optimized for Docker image distribution
- **No artifact storage**: Saves GitHub Actions storage costs

### Trade-offs
- Requires `packages: write` and `packages: read` permissions
- Uses GitHub Container Registry storage (unlimited for public repos)
- Image is accessible to anyone with read access to the repository

---

## Priority 2: Fix Pip Cache (6-12 min savings)

### Current Problematic Code

```yaml
# Line 278: Breaks pip caching
pip install coverage unittest-xml-reporting --no-cache-dir --root-user-action=ignore
```

### Optimized Implementation

```yaml
# =============================================================================
# OPTIMIZED: Pip Cache Configuration
# Time savings: 6-12 minutes
# =============================================================================

jobs:
  build-and-push-test-image:
    steps:
      # OPTIMIZED: Pre-install test dependencies in Docker image
      - name: Build and push test image with cached dependencies
        uses: docker/bake-action@v5
        with:
          files: deployment/docker-bake.hcl
          targets: test
          push: true
          # Build args to pre-install test packages
          set: |
            test.args.INSTALL_TEST_DEPS=true

  test-suite:
    steps:
      # OPTIMIZED: Use proper cache volume mount
      - name: Create pip cache directory
        run: |
          mkdir -p ~/.cache/pip
          # Set proper permissions for Docker volume mount
          sudo chmod -R 777 ~/.cache/pip

      - name: Run tests with pip cache enabled
        run: |
          COMPOSE="${{ env.TEST_COMPOSE_FILES }}"
          mkdir -p ./test_output
          docker compose $COMPOSE run --rm \
            -v $(pwd)/test_output:/code/test_output \
            -v $(pwd)/pyproject.toml:/code/pyproject.toml:ro \
            -v ~/.cache/pip:/root/.cache/pip:rw \
            test_runner sh -c "
            # OPTIMIZED: Remove --no-cache-dir flag to enable caching
            pip install coverage unittest-xml-reporting --root-user-action=ignore &&
            export PYTHONDONTWRITEBYTECODE=1 &&
            export PYTHONUNBUFFERED=1 &&
            export COVERAGE_RCFILE=/code/pyproject.toml &&
            export TEST_OUTPUT_DIR=/code/test_output/test-results-${{ matrix.test-group.name }} &&
            coverage run manage.py test ${{ matrix.test-group.apps }} \
              --settings=config.settings_test \
              --no-input \
              --verbosity=2 &&
            coverage report &&
            coverage xml -o /code/test_output/coverage-${{ matrix.test-group.name }}.xml
          "

      # Optional: Cache pip directory across workflow runs
      - name: Cache pip dependencies
        uses: actions/cache@v4
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ env.PIP_CACHE_VERSION }}-${{ hashFiles('requirements/*.txt') }}
          restore-keys: |
            ${{ runner.os }}-pip-${{ env.PIP_CACHE_VERSION }}-
```

### Dockerfile Changes (Recommended)

Create or update `deployment/Dockerfile.test` to pre-install test dependencies:

```dockerfile
# deployment/Dockerfile.test
FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /code

# Copy and install Python dependencies
COPY requirements/ /code/requirements/
RUN pip install --no-cache-dir -r requirements/test.txt

# OPTIMIZED: Pre-install test dependencies in image
ARG INSTALL_TEST_DEPS=false
RUN if [ "$INSTALL_TEST_DEPS" = "true" ]; then \
      pip install --no-cache-dir coverage unittest-xml-reporting; \
    fi

# Copy application code
COPY . /code/

# Create directory for test output
RUN mkdir -p /code/test_output

CMD ["python", "manage.py", "test"]
```

### Benefits
- **Eliminates redundant downloads**: Each job installs same packages
- **Faster test execution**: Packages already cached
- **Lower network usage**: No repeated PyPI downloads
- **Better with pre-installed packages**: Fastest option

### Trade-offs
- Pre-installing in Docker image increases image size slightly
- Cache requires proper volume mount permissions

---

## Priority 3: Shared Database Stack (9-18 min savings)

### Current Problematic Code

```yaml
# Lines 182-190, 259-267: Repeated in every job (6 times total)
- name: Start required services
  run: |
    docker compose ${{ env.TEST_COMPOSE_FILES }} up -d postgres redis questdb
    timeout 90s bash -c "until docker compose $COMPOSE ps --format json | grep -q '\"Health\":\"healthy\"'; do sleep 2; done"
```

### Optimized Implementation - Option A: GitHub Services

```yaml
# =============================================================================
# OPTIMIZED: Shared Database Stack (Option A - Services)
# Time savings: 9-18 minutes
# Limitation: Services start at job level, not workflow level
# =============================================================================

jobs:
  django-checks:
    runs-on: ubuntu-latest
    needs: build-and-push-test-image

    # OPTIMIZED: Use GitHub Actions services for databases
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_DB: test_db
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379

      questdb:
        image: questdb/questdb:7.3.10
        env:
          QDB_TELEMETRY_ENABLED: "false"
        options: >-
          --health-cmd "curl -f http://localhost:9000/status || exit 1"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 9000:9000
          - 9009:9009

    strategy:
      matrix:
        check: [migrations, system]

    steps:
      - uses: actions/checkout@v5

      - name: Pull test image from registry
        run: |
          # Pull and tag image...
          docker pull ${{ needs.build-and-push-test-image.outputs.image }}

      # OPTIMIZED: No need to start services - already running
      - name: Verify service connectivity
        run: |
          echo "✅ Services started automatically by GitHub Actions"
          pg_isready -h localhost -p 5432 || echo "Postgres not ready yet"
          redis-cli -h localhost -p 6379 ping || echo "Redis not ready yet"

      - name: Run Django ${{ matrix.check }} check
        env:
          # OPTIMIZED: Connect to GitHub services using localhost
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_db  # pragma: allowlist secret
          REDIS_URL: redis://localhost:6379/0
          QUESTDB_HOST: localhost
          QUESTDB_PORT: 9009
        run: |
          docker run --rm \
            --network host \
            -e DATABASE_URL \
            -e REDIS_URL \
            -e QUESTDB_HOST \
            -e QUESTDB_PORT \
            ${{ needs.build-and-push-test-image.outputs.image }} \
            python manage.py check --deploy --settings=config.settings_test

  test-suite:
    runs-on: ubuntu-latest
    needs: build-and-push-test-image

    # OPTIMIZED: Same services configuration for all test jobs
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_DB: test_db
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379

      questdb:
        image: questdb/questdb:7.3.10
        env:
          QDB_TELEMETRY_ENABLED: "false"
        options: >-
          --health-cmd "curl -f http://localhost:9000/status || exit 1"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 9000:9000
          - 9009:9009

    strategy:
      fail-fast: false
      matrix:
        test-group:
          - name: "core"
            apps: "accounts pages config"
          - name: "blog"
            apps: "blog"
          - name: "photos"
            apps: "photos"
          - name: "utils"
            apps: "utils"

    steps:
      - uses: actions/checkout@v5

      - name: Pull test image from registry
        run: |
          docker pull ${{ needs.build-and-push-test-image.outputs.image }}

      - name: Run tests for ${{ matrix.test-group.name }}
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_db  # pragma: allowlist secret
          REDIS_URL: redis://localhost:6379/0
          QUESTDB_HOST: localhost
          QUESTDB_PORT: 9009
        run: |
          mkdir -p ./test_output
          docker run --rm \
            --network host \
            -v $(pwd)/test_output:/code/test_output \
            -e DATABASE_URL \
            -e REDIS_URL \
            -e QUESTDB_HOST \
            -e QUESTDB_PORT \
            ${{ needs.build-and-push-test-image.outputs.image }} \
            sh -c "
            pip install coverage unittest-xml-reporting --root-user-action=ignore &&
            coverage run manage.py test ${{ matrix.test-group.apps }} \
              --settings=config.settings_test \
              --no-input \
              --verbosity=2 &&
            coverage xml -o /code/test_output/coverage-${{ matrix.test-group.name }}.xml
          "
```

### Optimized Implementation - Option B: Dedicated Service Job

```yaml
# =============================================================================
# OPTIMIZED: Shared Database Stack (Option B - Dedicated Job)
# Time savings: 9-18 minutes
# Best for: Maximum control and test isolation
# =============================================================================

jobs:
  # OPTIMIZED: Start services once, use for all tests
  start-test-services:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    outputs:
      postgres-host: ${{ steps.services.outputs.postgres-host }}
      redis-host: ${{ steps.services.outputs.redis-host }}
      questdb-host: ${{ steps.services.outputs.questdb-host }}
    steps:
      - name: Start long-running services
        id: services
        run: |
          # Start services with docker-compose
          docker network create test-network || true

          docker run -d \
            --name postgres-test \
            --network test-network \
            -e POSTGRES_DB=test_db \
            -e POSTGRES_USER=postgres \
            -e POSTGRES_PASSWORD=postgres \
            -p 5432:5432 \
            --health-cmd="pg_isready" \
            --health-interval=10s \
            --health-timeout=5s \
            --health-retries=5 \
            postgres:16-alpine

          docker run -d \
            --name redis-test \
            --network test-network \
            -p 6379:6379 \
            --health-cmd="redis-cli ping" \
            --health-interval=10s \
            redis:7-alpine

          docker run -d \
            --name questdb-test \
            --network test-network \
            -e QDB_TELEMETRY_ENABLED=false \
            -p 9000:9000 \
            -p 9009:9009 \
            questdb/questdb:7.3.10

          # Wait for all services to be healthy
          timeout 60s bash -c 'until docker ps | grep -q "healthy"; do sleep 2; done'

          # Output connection details
          POSTGRES_IP=$(docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' postgres-test)
          echo "postgres-host=${POSTGRES_IP}" >> $GITHUB_OUTPUT
          echo "✅ Services started and ready"

      - name: Keep job alive
        run: |
          # This job needs to stay alive while tests run
          echo "Services running, waiting for tests to complete..."
          sleep 3600  # Keep alive for 1 hour max

  django-checks:
    runs-on: ubuntu-latest
    needs: [build-and-push-test-image, start-test-services]
    # Tests use services from start-test-services job

  test-suite:
    runs-on: ubuntu-latest
    needs: [build-and-push-test-image, start-test-services]
    # Tests use services from start-test-services job
```

### Benefits
- **Single startup**: Services start once, not 6 times
- **Faster test execution**: No waiting for databases to initialize
- **Lower resource usage**: One set of services vs. six
- **Better test isolation**: Can use separate databases per test group

### Trade-offs
- Option A: Services restart for each job (still saves time from health checks)
- Option B: More complex, requires network configuration
- Database state must be properly cleaned between tests

---

## Priority 4: Test Group Rebalancing (5-8 min savings)

### Current Problematic Code

```yaml
# Lines 219-229: Imbalanced test groups
matrix:
  test-group:
    - name: "core"
      apps: "accounts pages config"  # 25 minutes
    - name: "blog"
      apps: "blog"
    - name: "photos"
      apps: "photos"
    - name: "utils"
      apps: "utils"  # 15 minutes
```

### Optimized Implementation - Option A: Rebalanced Groups

```yaml
# =============================================================================
# OPTIMIZED: Test Group Rebalancing (Option A - Manual Rebalancing)
# Time savings: 5-8 minutes
# =============================================================================

jobs:
  test-suite:
    strategy:
      fail-fast: false
      matrix:
        test-group:
          # OPTIMIZED: Split large apps into separate jobs
          - name: "accounts"
            apps: "accounts"
            estimated_time: "12min"

          - name: "pages"
            apps: "pages"
            estimated_time: "8min"

          - name: "config"
            apps: "config"
            estimated_time: "5min"

          - name: "blog"
            apps: "blog"
            estimated_time: "10min"

          - name: "photos"
            apps: "photos"
            estimated_time: "8min"

          # OPTIMIZED: Group smaller/faster apps together
          - name: "utils-and-other"
            apps: "utils"
            estimated_time: "15min"
```

### Optimized Implementation - Option B: Dynamic Splitting

```yaml
# =============================================================================
# OPTIMIZED: Test Group Rebalancing (Option B - Pytest-Based Splitting)
# Time savings: 5-8 minutes
# Requires: pytest, pytest-split, pytest-json-report
# =============================================================================

jobs:
  collect-tests:
    runs-on: ubuntu-latest
    needs: build-and-push-test-image
    outputs:
      test-durations: ${{ steps.collect.outputs.durations }}
      matrix: ${{ steps.generate.outputs.matrix }}
    steps:
      - uses: actions/checkout@v5

      - name: Pull test image
        run: |
          docker pull ${{ needs.build-and-push-test-image.outputs.image }}

      # OPTIMIZED: Collect test information for smart splitting
      - name: Collect test durations
        id: collect
        run: |
          # Run tests in collect-only mode to get list and historical durations
          docker run --rm \
            ${{ needs.build-and-push-test-image.outputs.image }} \
            python manage.py test --collect-only --settings=config.settings_test \
            > test_list.txt

          # Parse test list and create duration map (from previous runs or estimates)
          echo "durations=$(cat test_list.txt | jq -R -s -c 'split("\n")')" >> $GITHUB_OUTPUT

      - name: Generate balanced matrix
        id: generate
        uses: actions/github-script@v7
        with:
          script: |
            const tests = ${{ steps.collect.outputs.durations }};
            const groupCount = 4;  // Target number of parallel jobs

            // Simple load balancing algorithm
            const groups = Array(groupCount).fill().map(() => ({ apps: [], time: 0 }));

            // Sort tests by duration (if available) and distribute
            tests.sort((a, b) => (b.duration || 0) - (a.duration || 0));

            tests.forEach(test => {
              // Find group with least total time
              const minGroup = groups.reduce((min, g, i) =>
                g.time < groups[min].time ? i : min, 0);
              groups[minGroup].apps.push(test.app);
              groups[minGroup].time += test.duration || 5;
            });

            // Generate matrix
            const matrix = groups.map((g, i) => ({
              name: `group-${i + 1}`,
              apps: g.apps.join(' '),
              estimated_time: `${g.time}min`
            }));

            core.setOutput('matrix', JSON.stringify({ 'test-group': matrix }));

  test-suite:
    runs-on: ubuntu-latest
    needs: [build-and-push-test-image, collect-tests]
    strategy:
      fail-fast: false
      # OPTIMIZED: Use dynamically generated matrix
      matrix: ${{ fromJson(needs.collect-tests.outputs.matrix) }}
    steps:
      # Same as before, but using balanced groups
      - name: Run tests for ${{ matrix.test-group.name }}
        run: |
          echo "Running tests for: ${{ matrix.test-group.apps }}"
          echo "Estimated time: ${{ matrix.test-group.estimated_time }}"
          # ... rest of test execution
```

### Optimized Implementation - Option C: Pytest-Split Plugin

```yaml
# =============================================================================
# OPTIMIZED: Test Group Rebalancing (Option C - pytest-split)
# Time savings: 5-8 minutes
# Requires: Converting to pytest, pytest-split
# =============================================================================

jobs:
  test-suite:
    runs-on: ubuntu-latest
    needs: build-and-push-test-image
    strategy:
      fail-fast: false
      matrix:
        # OPTIMIZED: Use numeric splits with pytest-split
        split: [1, 2, 3, 4, 5, 6]
        total: [6]
    steps:
      - uses: actions/checkout@v5

      - name: Pull test image
        run: |
          docker pull ${{ needs.build-and-push-test-image.outputs.image }}

      # OPTIMIZED: Use pytest-split for automatic balancing
      - name: Run balanced test split ${{ matrix.split }}/${{ matrix.total }}
        run: |
          mkdir -p ./test_output
          docker run --rm \
            -v $(pwd)/test_output:/code/test_output \
            ${{ needs.build-and-push-test-image.outputs.image }} \
            sh -c "
            pip install pytest pytest-django pytest-split pytest-cov --root-user-action=ignore &&
            # OPTIMIZED: pytest-split automatically balances based on test durations
            pytest --splits ${{ matrix.total }} --group ${{ matrix.split }} \
              --cov --cov-report=xml:/code/test_output/coverage-split-${{ matrix.split }}.xml \
              --durations-path=.test_durations \
              --store-durations
          "

      # OPTIMIZED: Cache test durations for next run
      - name: Save test durations
        uses: actions/cache@v4
        with:
          path: .test_durations
          key: test-durations-${{ github.sha }}
          restore-keys: |
            test-durations-
```

### Benefits
- **Even distribution**: All test jobs complete at roughly the same time
- **Optimal parallelization**: No job finishes much faster than others
- **Dynamic adjustment**: Can adapt to test suite changes
- **Historical timing**: Uses past run data for better splitting

### Trade-offs
- Option A: Requires manual tuning when tests change
- Option B: More complex setup, requires test collection step
- Option C: Requires migrating from Django unittest to pytest

---

## Priority 5: Parallel Coverage Upload (3-5 min savings)

### Current Problematic Code

```yaml
# Lines 311-375: Sequential coverage upload waits for all tests
coverage-upload:
  runs-on: ubuntu-latest
  needs: test-suite  # Waits for ALL test jobs to complete
  steps:
    - name: Download coverage artifacts  # Downloads all at once
    - name: Merge coverage files  # Sequential merge
    - name: Upload to Codecov  # Single upload
```

### Optimized Implementation

```yaml
# =============================================================================
# OPTIMIZED: Parallel Coverage Upload
# Time savings: 3-5 minutes
# =============================================================================

jobs:
  test-suite:
    runs-on: ubuntu-latest
    needs: build-and-push-test-image
    strategy:
      matrix:
        test-group:
          - name: "core"
            apps: "accounts pages config"
    steps:
      - uses: actions/checkout@v5

      - name: Pull test image
        run: |
          docker pull ${{ needs.build-and-push-test-image.outputs.image }}

      - name: Run tests for ${{ matrix.test-group.name }}
        run: |
          # ... test execution (same as before)
          docker run --rm test_runner coverage run manage.py test

      # OPTIMIZED: Upload coverage immediately after tests complete
      - name: Upload coverage to Codecov (immediate)
        uses: codecov/codecov-action@v5
        with:
          files: ./test_output/coverage-${{ matrix.test-group.name }}.xml
          flags: ${{ matrix.test-group.name }}
          token: ${{ secrets.CODECOV_TOKEN }}
          fail_ci_if_error: false  # Don't fail immediately, let merge job handle errors

      # OPTIMIZED: Also save as artifact for merge job
      - name: Save coverage artifact
        uses: actions/upload-artifact@v5
        with:
          name: coverage-${{ matrix.test-group.name }}
          path: ./test_output/coverage-${{ matrix.test-group.name }}.xml
          retention-days: 1

  # OPTIMIZED: Lightweight merge job that doesn't wait for all uploads
  coverage-merge:
    runs-on: ubuntu-latest
    needs: test-suite
    if: always()  # Run even if some tests fail
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@v5

      - name: Download all coverage artifacts
        uses: actions/download-artifact@v6
        with:
          pattern: coverage-*
          merge-multiple: true
          path: ./coverage-reports

      - name: Set up Python
        uses: actions/setup-python@v6
        with:
          python-version: '3.12'

      - name: Install coverage tools
        run: pip install coverage

      # OPTIMIZED: Merge and upload combined report
      - name: Merge coverage reports
        run: |
          cd coverage-reports
          coverage combine --keep coverage-*.xml
          coverage xml -o ../coverage-combined.xml
          coverage report

      - name: Upload combined coverage report
        uses: codecov/codecov-action@v5
        with:
          files: ./coverage-combined.xml
          flags: combined
          token: ${{ secrets.CODECOV_TOKEN }}
          fail_ci_if_error: true  # Now we can fail if something went wrong

      # OPTIMIZED: Generate coverage comment for PRs
      - name: Coverage comment
        if: github.event_name == 'pull_request'
        uses: py-cov-action/python-coverage-comment-action@v3
        with:
          GITHUB_TOKEN: ${{ github.token }}
          MINIMUM_GREEN: 90
          MINIMUM_ORANGE: 70
```

### Alternative: Streaming Coverage

```yaml
# =============================================================================
# OPTIMIZED: Streaming Coverage (Advanced)
# Time savings: 3-5 minutes
# Requires: Custom upload script
# =============================================================================

jobs:
  test-suite:
    steps:
      - name: Run tests with streaming coverage
        run: |
          # OPTIMIZED: Upload coverage as tests run, not after
          docker run --rm \
            -v $(pwd)/test_output:/code/test_output \
            test_runner sh -c "
            # Run tests and generate coverage
            coverage run --parallel-mode manage.py test ${{ matrix.test-group.apps }} &&

            # OPTIMIZED: Stream coverage data to Codecov immediately
            coverage combine --keep &&
            coverage xml -o - | curl -X POST \
              -H 'Content-Type: text/xml' \
              -H 'Authorization: Bearer ${{ secrets.CODECOV_TOKEN }}' \
              --data-binary @- \
              'https://codecov.io/upload/v4?commit=${{ github.sha }}&branch=${{ github.ref }}&flag=${{ matrix.test-group.name }}'
          "
```

### Benefits
- **Parallel uploads**: Coverage uploaded as each test job completes
- **Earlier feedback**: Don't wait for all tests to see coverage
- **Reduced wait time**: No single bottleneck job
- **Better resource usage**: Uploads happen during test execution

### Trade-offs
- Multiple Codecov uploads instead of one (within API limits)
- Requires merge job for combined report
- Slightly more complex workflow

---

## Additional Optimizations

### 6. Build Optimization

```yaml
# =============================================================================
# OPTIMIZATION 6: Build Optimization
# Time savings: 2-5 minutes
# =============================================================================

jobs:
  build-and-push-test-image:
    steps:
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
        with:
          # OPTIMIZED: Use BuildKit with advanced features
          driver-opts: |
            network=host
            image=moby/buildkit:buildx-stable-1
          buildkitd-flags: |
            --allow-insecure-entitlement security.insecure
            --allow-insecure-entitlement network.host

      - name: Build with advanced caching
        uses: docker/bake-action@v5
        with:
          files: deployment/docker-bake.hcl
          targets: test
          push: true
          set: |
            # OPTIMIZED: Multi-layer cache strategy
            *.cache-from=type=gha,scope=test-${{ env.DOCKER_CACHE_VERSION }}
            *.cache-from=type=registry,ref=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:cache
            *.cache-from=type=registry,ref=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:latest
            *.cache-to=type=gha,mode=max,scope=test-${{ env.DOCKER_CACHE_VERSION }}
            *.cache-to=type=registry,ref=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:cache,mode=max
            # OPTIMIZED: Use cache mounts for pip/apt
            *.attest=type=provenance,mode=min
            *.attest=type=sbom,disabled=true
```

**Dockerfile optimization:**

```dockerfile
# OPTIMIZED: Multi-stage build with cache mounts
FROM python:3.12-slim as base

# OPTIMIZED: Install system dependencies with cache mount
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

FROM base as dependencies

# OPTIMIZED: Use cache mount for pip downloads
RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    --mount=type=bind,source=requirements,target=/tmp/requirements \
    pip install -r /tmp/requirements/test.txt

FROM dependencies as final

WORKDIR /code
COPY . /code/

# Pre-install test dependencies
RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    pip install coverage unittest-xml-reporting pytest pytest-django
```

### 7. Service Health Check Optimization

```yaml
# =============================================================================
# OPTIMIZATION 7: Service Health Check Optimization
# Time savings: 1-3 minutes
# =============================================================================

services:
  postgres:
    image: postgres:16-alpine
    options: >-
      --health-cmd "pg_isready -U postgres"
      --health-interval 5s
      --health-timeout 3s
      --health-retries 3
      --health-start-period 10s

  redis:
    image: redis:7-alpine
    options: >-
      --health-cmd "redis-cli ping | grep PONG"
      --health-interval 3s
      --health-timeout 2s
      --health-retries 3
      --health-start-period 5s

  questdb:
    image: questdb/questdb:7.3.10
    options: >-
      --health-cmd "curl -sf http://localhost:9000/status | grep -q OK"
      --health-interval 5s
      --health-timeout 3s
      --health-retries 3
      --health-start-period 15s
```

### 8. Matrix Strategy Improvements

```yaml
# =============================================================================
# OPTIMIZATION 8: Matrix Strategy Improvements
# Time savings: Variable based on changes
# =============================================================================

jobs:
  # OPTIMIZED: Detect which apps changed
  detect-changes:
    runs-on: ubuntu-latest
    outputs:
      apps: ${{ steps.filter.outputs.changes }}
      run-all: ${{ steps.check.outputs.run-all }}
    steps:
      - uses: actions/checkout@v5
        with:
          fetch-depth: 0

      - uses: dorny/paths-filter@v2
        id: filter
        with:
          filters: |
            accounts:
              - 'accounts/**'
            pages:
              - 'pages/**'
            blog:
              - 'blog/**'
            photos:
              - 'photos/**'
            utils:
              - 'utils/**'
            core:
              - 'config/**'
              - 'requirements/**'
              - 'deployment/**'

      - id: check
        run: |
          # Run all tests if core files changed
          if [[ "${{ steps.filter.outputs.core }}" == "true" ]] || \
             [[ "${{ github.event_name }}" == "push" ]] || \
             [[ "${{ github.event_name }}" == "workflow_dispatch" ]]; then
            echo "run-all=true" >> $GITHUB_OUTPUT
          else
            echo "run-all=false" >> $GITHUB_OUTPUT
          fi

  test-suite:
    needs: [build-and-push-test-image, detect-changes]
    # OPTIMIZED: Skip jobs for unchanged apps
    if: needs.detect-changes.outputs.run-all == 'true' || contains(needs.detect-changes.outputs.apps, matrix.test-group.name)
    strategy:
      matrix:
        test-group:
          - name: "accounts"
            apps: "accounts"
          - name: "pages"
            apps: "pages"
          # ... etc
```

### 9. Workflow Restructuring

```yaml
# =============================================================================
# OPTIMIZATION 9: Workflow Restructuring
# Time savings: 2-4 minutes
# =============================================================================

jobs:
  # OPTIMIZED: Merge quick checks into single job
  quick-checks:
    runs-on: ubuntu-latest
    needs: build-and-push-test-image
    strategy:
      matrix:
        check: [lint, migrations, system, security]
    steps:
      - uses: actions/checkout@v5

      - name: Run ${{ matrix.check }} check
        run: |
          case "${{ matrix.check }}" in
            lint)
              docker run --rm test_runner ruff check .
              ;;
            migrations)
              docker run --rm test_runner python manage.py makemigrations --check
              ;;
            system)
              docker run --rm test_runner python manage.py check --deploy
              ;;
            security)
              docker run --rm test_runner python manage.py check --deploy --fail-level=WARNING
              ;;
          esac

  # OPTIMIZED: Merge artifact cleanup into coverage job
  coverage-and-cleanup:
    runs-on: ubuntu-latest
    needs: test-suite
    if: always()
    steps:
      - name: Download and merge coverage
        # ... merge coverage

      - name: Upload to Codecov
        # ... upload coverage

      # OPTIMIZED: Clean up artifacts in same job
      - name: Delete test artifacts
        if: success()
        uses: geekyeggo/delete-artifact@v5
        with:
          name: |
            docker-image
            coverage-*
            test-results-*
          failOnError: false
```

### 10. Third-party Action Alternatives

```yaml
# =============================================================================
# OPTIMIZATION 10: Third-party Action Alternatives
# Time savings: 1-2 minutes
# =============================================================================

jobs:
  build-and-push-test-image:
    steps:
      # CURRENT: actions/checkout@v5 (good, keep this)
      - uses: actions/checkout@v5

      # OPTIMIZED: Use depot.dev for faster Docker builds (optional)
      - name: Set up Depot CLI
        uses: depot/setup-action@v1

      - name: Build and push with Depot
        uses: depot/bake-action@v1
        with:
          # 2-5x faster builds with Depot's cached builders
          token: ${{ secrets.DEPOT_TOKEN }}
          project: ${{ vars.DEPOT_PROJECT_ID }}
          files: deployment/docker-bake.hcl
          targets: test
          push: true

  test-suite:
    steps:
      # OPTIMIZED: Faster artifact downloads with custom action
      - name: Fast download artifacts
        uses: dawidd6/action-download-artifact@v2
        with:
          workflow: test.yml
          name: coverage-*
          path: ./coverage-reports
          # Parallel downloads for faster retrieval

      # OPTIMIZED: Use composite action for repeated tasks
      - name: Setup test environment
        uses: ./.github/actions/setup-test-env
        with:
          image: ${{ needs.build-and-push-test-image.outputs.image }}
```

**Create composite action (`.github/actions/setup-test-env/action.yml`):**

```yaml
# .github/actions/setup-test-env/action.yml
name: 'Setup Test Environment'
description: 'Pull test image and configure environment'
inputs:
  image:
    description: 'Test image to pull'
    required: true
runs:
  using: 'composite'
  steps:
    - name: Log in to GHCR
      uses: docker/login-action@v3
      with:
        registry: ghcr.io
        username: ${{ github.actor }}
        password: ${{ github.token }}

    - name: Pull test image
      shell: bash
      run: |
        docker pull ${{ inputs.image }}
        docker tag ${{ inputs.image }} test-runner:latest

    - name: Verify image
      shell: bash
      run: |
        docker images | grep test-runner
```

---

## Migration Strategy

### Phase 1: Quick Wins (Week 1) - 18-30 min savings

**Target: Low-risk, high-impact changes**

1. **Fix Pip Cache** ✅ Priority 2
   - Remove `--no-cache-dir` flag
   - Configure cache volume properly
   - Test with single job first

2. **Service Health Check Optimization** ✅ Optimization 7
   - Reduce health check intervals
   - Optimize health check commands
   - Verify services start correctly

3. **Test Group Rebalancing** ✅ Priority 4
   - Manually rebalance test groups (Option A)
   - Monitor job completion times
   - Adjust groups based on actual timings

**Implementation checklist:**
- [ ] Update line 278 to remove `--no-cache-dir`
- [ ] Verify pip cache directory permissions
- [ ] Update health check configurations
- [ ] Rebalance test matrix groups
- [ ] Run full workflow and measure improvements
- [ ] Document actual time savings

### Phase 2: Medium Changes (Week 2-3) - 23-35 min savings

**Target: Moderate risk, significant impact**

4. **Docker Registry Distribution** ✅ Priority 1
   - Add GHCR push step to build job
   - Update all jobs to pull from registry
   - Remove artifact upload/download steps
   - Test thoroughly on PR first

5. **Parallel Coverage Upload** ✅ Priority 5
   - Add immediate upload step to test jobs
   - Create lightweight merge job
   - Configure Codecov flags properly
   - Verify coverage reports accuracy

6. **Build Optimization** ✅ Optimization 6
   - Add cache mounts to Dockerfile
   - Optimize layer ordering
   - Pre-install test dependencies
   - Verify image size doesn't explode

**Implementation checklist:**
- [ ] Configure GHCR authentication
- [ ] Test Docker registry push/pull
- [ ] Update all job dependencies
- [ ] Implement parallel coverage uploads
- [ ] Verify Codecov integration
- [ ] Optimize Docker build with cache mounts
- [ ] Measure build time improvements
- [ ] Run complete workflow test

### Phase 3: Major Restructuring (Week 4+) - 40-50 min savings

**Target: Higher risk, maximum impact**

7. **Shared Database Stack** ✅ Priority 3
   - Start with GitHub Services (Option A)
   - Test database connectivity thoroughly
   - Ensure test isolation works
   - Monitor for race conditions
   - Consider dedicated job (Option B) if needed

8. **Matrix Strategy Improvements** ✅ Optimization 8
   - Implement change detection
   - Create dynamic matrix generation
   - Test skip logic thoroughly
   - Monitor for edge cases

9. **Workflow Restructuring** ✅ Optimization 9
   - Merge related jobs
   - Optimize job dependencies
   - Create composite actions
   - Reduce overall complexity

**Implementation checklist:**
- [ ] Implement GitHub Services for databases
- [ ] Test all service connectivity
- [ ] Verify test isolation
- [ ] Add change detection
- [ ] Implement dynamic matrix
- [ ] Create composite actions
- [ ] Merge quick check jobs
- [ ] Complete end-to-end testing
- [ ] Document new workflow structure
- [ ] Train team on new setup

### Rollback Plan

For each phase, have a rollback strategy:

**Phase 1:**
- Keep original workflow as `.github/workflows/test.yml.backup`
- Can revert individual commits easily
- Low risk of breaking changes

**Phase 2:**
- Use feature branch for testing
- Create separate workflow file during migration
- Switch atomically after verification

**Phase 3:**
- Implement behind feature flag (workflow_dispatch)
- Run both workflows in parallel initially
- Compare results before full switch
- Keep fallback workflow for 2 weeks

### Success Metrics

Track these metrics through each phase:

- **Workflow duration**: Target 15-20 minutes (from 45)
- **Artifact storage**: Should decrease significantly
- **Network transfer**: Should decrease by ~70%
- **Cache hit rate**: Should increase to >80%
- **Test reliability**: Should remain at 100%
- **Coverage accuracy**: Must remain exact

### Testing Strategy

**Before each phase:**
1. Test on feature branch with full workflow
2. Compare results with main branch
3. Verify all tests pass
4. Check coverage reports match
5. Monitor resource usage
6. Get team approval

**Continuous monitoring:**
- Set up workflow duration alerts
- Monitor test flakiness
- Track cache effectiveness
- Watch for timeout issues
- Review error rates

---

## Complete Optimized Workflow (All Changes Combined)

This is the final, fully optimized workflow incorporating all priority optimizations:

```yaml
name: Pipeline - Tests (Optimized)

run-name: "${{ github.event.head_commit.message || github.event.pull_request.title || 'Run Tests' }}"

on:
  push:
    branches: [ 'main' ]
    paths-ignore:
      - '**.md'
      - 'docs/**'
      - '.cursor/**'
      - 'LICENSE'
      - '.gitignore'
  pull_request:
    branches: [ '**' ]
    types: [ opened, synchronize, reopened, ready_for_review ]
    paths-ignore:
      - '**.md'
      - 'docs/**'
      - '.cursor/**'
      - 'LICENSE'
      - '.gitignore'
  workflow_dispatch:

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

env:
  SECRET_KEY: "FAKE_SECRET_KEY"  # pragma: allowlist secret
  PYTHONUNBUFFERED: 1
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}/test-runner
  IMAGE_TAG: ${{ github.sha }}
  TEST_COMPOSE_FILES: -f deployment/docker-compose.test.yml -f deployment/docker-compose.test.ci.yml
  PIP_CACHE_VERSION: v2
  DOCKER_CACHE_VERSION: v2

permissions:
  contents: read
  packages: write

jobs:
  # ============================================================================
  # OPTIMIZED: Build and push to registry (not artifacts)
  # ============================================================================
  build-and-push-test-image:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    outputs:
      image: ${{ steps.meta.outputs.image }}
    steps:
      - uses: actions/checkout@v5

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
        with:
          driver-opts: |
            network=host
            image=moby/buildkit:buildx-stable-1
          buildkitd-flags: |
            --allow-insecure-entitlement security.insecure
            --allow-insecure-entitlement network.host

      - name: Log in to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Generate image metadata
        id: meta
        run: |
          IMAGE="${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ env.IMAGE_TAG }}"
          echo "image=${IMAGE}" >> $GITHUB_OUTPUT
          echo "📦 Test image: ${IMAGE}"

      - name: Build and push test image
        uses: docker/bake-action@v5
        env:
          REGISTRY: ${{ env.REGISTRY }}
          IMAGE_PREFIX: ${{ github.repository }}
          TAG: ${{ env.IMAGE_TAG }}
        with:
          files: deployment/docker-bake.hcl
          targets: test
          push: true
          set: |
            *.cache-from=type=gha,scope=test-${{ env.DOCKER_CACHE_VERSION }}
            *.cache-from=type=registry,ref=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:cache
            *.cache-to=type=gha,mode=max,scope=test-${{ env.DOCKER_CACHE_VERSION }}
            *.cache-to=type=registry,ref=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:cache,mode=max
            *.attest=type=provenance,mode=min
            *.attest=type=sbom,disabled=true

  # ============================================================================
  # OPTIMIZED: Quick checks with shared services
  # ============================================================================
  django-checks:
    runs-on: ubuntu-latest
    needs: build-and-push-test-image
    timeout-minutes: 10
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_DB: test_db
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd "pg_isready -U postgres"
          --health-interval 5s
          --health-timeout 3s
          --health-retries 3
          --health-start-period 10s
        ports:
          - 5432:5432
      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping | grep PONG"
          --health-interval 3s
          --health-timeout 2s
          --health-retries 3
        ports:
          - 6379:6379
      questdb:
        image: questdb/questdb:7.3.10
        env:
          QDB_TELEMETRY_ENABLED: "false"
        options: >-
          --health-cmd "curl -sf http://localhost:9000/status | grep -q OK"
          --health-interval 5s
          --health-timeout 3s
          --health-retries 3
          --health-start-period 15s
        ports:
          - 9000:9000
          - 9009:9009
    strategy:
      matrix:
        check: [migrations, system]
    steps:
      - uses: actions/checkout@v5

      - name: Log in to GHCR
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Pull test image
        run: |
          docker pull ${{ needs.build-and-push-test-image.outputs.image }}
          docker tag ${{ needs.build-and-push-test-image.outputs.image }} test-runner:latest

      - name: Run Django ${{ matrix.check }} check
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_db  # pragma: allowlist secret
          REDIS_URL: redis://localhost:6379/0
          QUESTDB_HOST: localhost
          QUESTDB_PORT: 9009
        run: |
          docker run --rm --network host \
            -e DATABASE_URL -e REDIS_URL -e QUESTDB_HOST -e QUESTDB_PORT \
            test-runner:latest \
            python manage.py ${{ matrix.check == 'migrations' && 'makemigrations --check' || 'check --deploy' }} \
            --settings=config.settings_test

  # ============================================================================
  # OPTIMIZED: Rebalanced test groups with shared services
  # ============================================================================
  test-suite:
    runs-on: ubuntu-latest
    needs: build-and-push-test-image
    timeout-minutes: 20
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_DB: test_db
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd "pg_isready -U postgres"
          --health-interval 5s
          --health-timeout 3s
          --health-retries 3
          --health-start-period 10s
        ports:
          - 5432:5432
      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping | grep PONG"
          --health-interval 3s
          --health-timeout 2s
          --health-retries 3
        ports:
          - 6379:6379
      questdb:
        image: questdb/questdb:7.3.10
        env:
          QDB_TELEMETRY_ENABLED: "false"
        options: >-
          --health-cmd "curl -sf http://localhost:9000/status | grep -q OK"
          --health-interval 5s
          --health-timeout 3s
          --health-retries 3
          --health-start-period 15s
        ports:
          - 9000:9000
          - 9009:9009
    strategy:
      fail-fast: false
      matrix:
        test-group:
          # OPTIMIZED: Rebalanced groups for even distribution
          - name: "accounts"
            apps: "accounts"
          - name: "pages-config"
            apps: "pages config"
          - name: "blog-photos"
            apps: "blog photos"
          - name: "utils"
            apps: "utils"
    steps:
      - uses: actions/checkout@v5

      - name: Log in to GHCR
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Pull test image
        run: |
          docker pull ${{ needs.build-and-push-test-image.outputs.image }}
          docker tag ${{ needs.build-and-push-test-image.outputs.image }} test-runner:latest

      - name: Create pip cache directory
        run: |
          mkdir -p ~/.cache/pip
          sudo chmod -R 777 ~/.cache/pip

      - name: Run tests for ${{ matrix.test-group.name }}
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_db  # pragma: allowlist secret
          REDIS_URL: redis://localhost:6379/0
          QUESTDB_HOST: localhost
          QUESTDB_PORT: 9009
        run: |
          mkdir -p ./test_output
          docker run --rm --network host \
            -v $(pwd)/test_output:/code/test_output \
            -v $(pwd)/pyproject.toml:/code/pyproject.toml:ro \
            -v ~/.cache/pip:/root/.cache/pip:rw \
            -e DATABASE_URL -e REDIS_URL -e QUESTDB_HOST -e QUESTDB_PORT \
            test-runner:latest sh -c "
            pip install coverage unittest-xml-reporting --root-user-action=ignore &&
            coverage run manage.py test ${{ matrix.test-group.apps }} \
              --settings=config.settings_test \
              --no-input \
              --verbosity=2 &&
            coverage xml -o /code/test_output/coverage-${{ matrix.test-group.name }}.xml
          "

      # OPTIMIZED: Upload coverage immediately
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v5
        with:
          files: ./test_output/coverage-${{ matrix.test-group.name }}.xml
          flags: ${{ matrix.test-group.name }}
          token: ${{ secrets.CODECOV_TOKEN }}
          fail_ci_if_error: false

      - name: Upload coverage artifact
        uses: actions/upload-artifact@v5
        with:
          name: coverage-${{ matrix.test-group.name }}
          path: ./test_output/coverage-${{ matrix.test-group.name }}.xml
          retention-days: 1

  # ============================================================================
  # OPTIMIZED: Lightweight coverage merge
  # ============================================================================
  coverage-merge:
    runs-on: ubuntu-latest
    needs: test-suite
    if: always()
    timeout-minutes: 3
    steps:
      - uses: actions/checkout@v5

      - name: Download coverage artifacts
        uses: actions/download-artifact@v6
        with:
          pattern: coverage-*
          merge-multiple: true
          path: ./coverage-reports

      - name: Set up Python
        uses: actions/setup-python@v6
        with:
          python-version: '3.12'

      - name: Install coverage
        run: pip install coverage

      - name: Merge and upload combined coverage
        run: |
          cd coverage-reports
          ls -la
          coverage combine --keep coverage-*.xml || true
          coverage xml -o ../coverage-combined.xml || cp coverage-*.xml ../coverage-combined.xml

      - name: Upload combined coverage
        uses: codecov/codecov-action@v5
        with:
          files: ./coverage-combined.xml
          flags: combined
          token: ${{ secrets.CODECOV_TOKEN }}
          fail_ci_if_error: true

      # OPTIMIZED: Clean up artifacts in same job
      - name: Clean up artifacts
        if: success()
        uses: geekyeggo/delete-artifact@v5
        with:
          name: coverage-*
          failOnError: false

  # ============================================================================
  # Build production images (cached, parallel with tests)
  # ============================================================================
  build-production-images:
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v5

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to GHCR
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build production images (cache only)
        uses: docker/bake-action@v5
        env:
          REGISTRY: ${{ env.REGISTRY }}
          IMAGE_PREFIX: ${{ github.repository }}
          TAG: ${{ github.sha }}
        with:
          files: deployment/docker-bake.hcl
          targets: production
          push: false
          set: |
            *.cache-from=type=gha,scope=buildx-main-${{ env.DOCKER_CACHE_VERSION }}
            *.cache-to=type=gha,mode=max,scope=buildx-main-${{ env.DOCKER_CACHE_VERSION }}

  # ============================================================================
  # Gate check
  # ============================================================================
  all-checks:
    runs-on: ubuntu-latest
    needs: [build-and-push-test-image, django-checks, test-suite, coverage-merge, build-production-images]
    if: always()
    steps:
      - name: Check all jobs passed
        run: |
          if [[ "${{ needs.build-and-push-test-image.result }}" != "success" ]] || \
             [[ "${{ needs.django-checks.result }}" != "success" ]] || \
             [[ "${{ needs.test-suite.result }}" != "success" ]] || \
             [[ "${{ needs.coverage-merge.result }}" != "success" ]]; then
            echo "❌ Some checks failed"
            exit 1
          fi
          PROD_STATUS="${{ needs.build-production-images.result }}"
          if [[ "$PROD_STATUS" != "success" && "$PROD_STATUS" != "skipped" ]]; then
            echo "❌ Production build failed"
            exit 1
          fi
          echo "✅ All checks passed!"

  # ============================================================================
  # Push production images
  # ============================================================================
  push-production-images:
    runs-on: ubuntu-latest
    needs: all-checks
    if: github.ref == 'refs/heads/main' && needs.all-checks.result == 'success'
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v5

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to GHCR
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Push production images
        uses: docker/bake-action@v5
        env:
          REGISTRY: ${{ env.REGISTRY }}
          IMAGE_PREFIX: ${{ github.repository }}
          TAG: ${{ github.sha }}
        with:
          files: deployment/docker-bake.hcl
          targets: production
          push: true
          set: |
            *.cache-from=type=gha,scope=buildx-main-${{ env.DOCKER_CACHE_VERSION }}
            *.cache-to=type=gha,mode=max,scope=buildx-main-${{ env.DOCKER_CACHE_VERSION }}
```

---

## Summary of Expected Time Savings

| Optimization | Current | Optimized | Savings | Priority |
|--------------|---------|-----------|---------|----------|
| Docker Registry Distribution | 20-30 min | 3-5 min | 20-25 min | 1 |
| Fix Pip Cache | 6-12 min | 1-2 min | 6-10 min | 2 |
| Shared Database Stack | 9-18 min | 2-3 min | 9-15 min | 3 |
| Test Group Rebalancing | 25 min | 15 min | 5-10 min | 4 |
| Parallel Coverage Upload | 3-5 min | 30s-1min | 3-4 min | 5 |
| Build Optimization | 8-10 min | 6-8 min | 2-3 min | 6 |
| Service Health Checks | 3-4 min | 1-2 min | 2-3 min | 7 |
| Matrix Improvements | Variable | Variable | 2-5 min | 8 |
| Workflow Restructure | 2-3 min | 1 min | 1-2 min | 9 |
| **TOTAL** | **~45 min** | **15-20 min** | **55-67%** | - |

## Next Steps

1. **Review this document** with the team
2. **Test Phase 1** changes on a feature branch
3. **Monitor metrics** after each phase
4. **Iterate and adjust** based on real-world results
5. **Document learnings** for future optimizations

## Questions or Issues?

If you encounter any issues during implementation:
1. Check the rollback plan for your phase
2. Review the testing strategy
3. Consult the trade-offs section for each optimization
4. Create a GitHub issue with workflow run links

---

**Document Version:** 1.0
**Last Updated:** 2025-11-20
**Author:** AI Assistant
**Status:** Ready for Implementation
