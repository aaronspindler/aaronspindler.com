# Docker Bake configuration for multi-stage builds
# Usage: docker buildx bake -f deployment/docker-bake.multistage.hcl [target]
#
# This configuration uses a single Dockerfile.multistage with multiple targets
# Replaces 4 separate Dockerfiles with 1 consolidated file

variable "REGISTRY" {
  default = "ghcr.io"
}

variable "IMAGE_PREFIX" {
  default = "aaronspindler/aaronspindler.com"
}

variable "TAG" {
  default = "latest"
}

# Common cache configuration
target "_common" {
  cache-from = [
    "type=gha,scope=buildx-multistage",
    "type=gha"
  ]
  cache-to = ["type=gha,mode=max,scope=buildx-multistage"]
  platforms = ["linux/amd64"]
}

# =============================================================================
# Test image target (skips JS build for speed)
# =============================================================================
target "test" {
  inherits = ["_common"]
  dockerfile = "deployment/Dockerfile.multistage"
  target = "test"
  tags = [
    "${REGISTRY}/${IMAGE_PREFIX}/test-runner:${TAG}",
    "${REGISTRY}/${IMAGE_PREFIX}/test-runner:latest"
  ]
  args = {
    SKIP_JS_BUILD = "1"
  }
}

# =============================================================================
# Production Web Service
# =============================================================================
target "web" {
  inherits = ["_common"]
  dockerfile = "deployment/Dockerfile.multistage"
  target = "runtime-full"
  tags = [
    "${REGISTRY}/${IMAGE_PREFIX}-web:${TAG}",
    "${REGISTRY}/${IMAGE_PREFIX}-web:latest"
  ]
  args = {
    SKIP_JS_BUILD = "0"
  }
}

# =============================================================================
# Unified Celery Service (Worker + Beat combined)
# =============================================================================
target "celery-unified" {
  inherits = ["_common"]
  dockerfile = "deployment/Dockerfile.multistage"
  target = "celery-unified"
  tags = [
    "${REGISTRY}/${IMAGE_PREFIX}-celery:${TAG}",
    "${REGISTRY}/${IMAGE_PREFIX}-celery:latest"
  ]
}

# =============================================================================
# Flower (Monitoring) - Optional/On-Demand
# =============================================================================
target "flower" {
  inherits = ["_common"]
  dockerfile = "deployment/Dockerfile.multistage"
  target = "runtime-minimal"
  tags = [
    "${REGISTRY}/${IMAGE_PREFIX}-flower:${TAG}",
    "${REGISTRY}/${IMAGE_PREFIX}-flower:latest"
  ]
}

# =============================================================================
# Build Groups
# =============================================================================

# Essential services (web + celery-unified)
# This is the recommended production setup
group "essential" {
  targets = ["web", "celery-unified"]
}

# Full production (includes optional Flower)
group "production" {
  targets = ["web", "celery-unified", "flower"]
}

# Legacy targets for backward compatibility
# These maintain separate worker/beat services
target "celery-legacy" {
  inherits = ["_common"]
  dockerfile = "deployment/Dockerfile.multistage"
  target = "runtime-full"
  tags = [
    "${REGISTRY}/${IMAGE_PREFIX}-celery-worker:${TAG}",
    "${REGISTRY}/${IMAGE_PREFIX}-celery-worker:latest"
  ]
}

target "celerybeat-legacy" {
  inherits = ["_common"]
  dockerfile = "deployment/Dockerfile.multistage"
  target = "runtime-minimal"
  tags = [
    "${REGISTRY}/${IMAGE_PREFIX}-celerybeat:${TAG}",
    "${REGISTRY}/${IMAGE_PREFIX}-celerybeat:latest"
  ]
}

# Legacy full production (4 services)
group "production-legacy" {
  targets = ["web", "celery-legacy", "celerybeat-legacy", "flower"]
}
