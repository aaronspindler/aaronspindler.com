# Docker Bake configuration for multi-target builds
# Usage: docker buildx bake -f docker-bake.hcl [target]

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
    "type=gha",
    "type=registry,ref=${REGISTRY}/${IMAGE_PREFIX}-web:latest"
  ]
  cache-to = ["type=gha,mode=max"]
  platforms = ["linux/amd64"]
}

# Test image target (skips JS build for speed)
target "test" {
  inherits = ["_common"]
  dockerfile = "deployment/Dockerfile"
  tags = ["test-runner:latest"]
  args = {
    SKIP_JS_BUILD = "1"
  }
  output = ["type=docker"]
}

# Production web service
target "web" {
  inherits = ["_common"]
  dockerfile = "deployment/Dockerfile"
  tags = [
    "${REGISTRY}/${IMAGE_PREFIX}-web:latest"
  ]
  args = {
    SKIP_JS_BUILD = "0"
  }
}

# Celery worker service
target "celery" {
  inherits = ["_common"]
  dockerfile = "deployment/celery.Dockerfile"
  tags = [
    "${REGISTRY}/${IMAGE_PREFIX}-celery:latest"
  ]
}

# Celery beat scheduler service
target "celerybeat" {
  inherits = ["_common"]
  dockerfile = "deployment/celerybeat.Dockerfile"
  tags = [
    "${REGISTRY}/${IMAGE_PREFIX}-celerybeat:latest"
  ]
}

# Flower monitoring service
target "flower" {
  inherits = ["_common"]
  dockerfile = "deployment/flower.Dockerfile"
  tags = [
    "${REGISTRY}/${IMAGE_PREFIX}-flower:latest"
  ]
}

# Build all production services in parallel
group "production" {
  targets = ["web", "celery", "celerybeat", "flower"]
}

# Build only essential services (excludes flower)
group "essential" {
  targets = ["web", "celery", "celerybeat"]
}
