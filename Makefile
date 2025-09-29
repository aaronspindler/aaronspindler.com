# Simple Makefile for static file management

# Variables
VENV := venv
PYTHON := $(VENV)/bin/python
MANAGE := $(PYTHON) manage.py

# Default target
.DEFAULT_GOAL := static

# Build CSS and JavaScript, then collect static files
.PHONY: static
static:
	@echo "Building CSS..."
	$(MANAGE) build_css
	@echo "Building and optimizing JavaScript..."
	@if command -v npm >/dev/null 2>&1; then \
		npm run build:js; \
	else \
		echo "Warning: npm not found, skipping JavaScript optimization"; \
	fi
	@echo "Collecting static files..."
	$(MANAGE) collectstatic_optimize
	@echo "Static files ready!"

# Just build CSS
.PHONY: css
css:
	$(MANAGE) build_css

# Just build and optimize JavaScript
.PHONY: js
js:
	@if command -v npm >/dev/null 2>&1; then \
		echo "Building JavaScript..."; \
		npm run build:js; \
		echo "JavaScript build complete!"; \
	else \
		echo "Error: npm not found. Please install Node.js and npm."; \
		exit 1; \
	fi

# Just collect static files
.PHONY: collect
collect:
	$(MANAGE) collectstatic --no-input

# Collect and optimize
.PHONY: collect-optimize
collect-optimize:
	$(MANAGE) collectstatic_optimize

# Clean static files
.PHONY: clean
clean:
	rm -rf staticfiles/
	rm -f static/css/combined.min.css*
	rm -f static/js/*.min.js static/js/*.min.js.gz static/js/*.min.js.br

# Docker test commands
.PHONY: test-build
test-build:
	@echo "Building Docker test images..."
	docker-compose -f docker-compose.test.yml build

.PHONY: test-up
test-up:
	@echo "Starting test environment..."
	docker-compose -f docker-compose.test.yml --env-file env.test up -d
	@echo "Test environment is running!"
	@echo "  - Web UI: http://localhost:8001"
	@echo "  - Flower (Celery monitoring): http://localhost:5556"
	@echo "  - LocalStack (S3): http://localhost:4566"

.PHONY: test-run
test-run:
	@echo "Running tests in Docker..."
	docker-compose -f docker-compose.test.yml --env-file env.test run --rm test_runner

.PHONY: test-run-app
test-run-app:
	@echo "Running specific app tests in Docker..."
	@if [ -z "$(APP)" ]; then \
		echo "Error: APP variable not set. Usage: make test-run-app APP=blog"; \
		exit 1; \
	fi
	docker-compose -f docker-compose.test.yml --env-file env.test run --rm test_runner python manage.py test $(APP) --settings=config.settings_test --parallel --keepdb

.PHONY: test-run-specific
test-run-specific:
	@echo "Running specific test in Docker..."
	@if [ -z "$(TEST)" ]; then \
		echo "Error: TEST variable not set. Usage: make test-run-specific TEST=blog.tests.test_models.BlogCommentModelTest"; \
		exit 1; \
	fi
	docker-compose -f docker-compose.test.yml --env-file env.test run --rm test_runner python manage.py test $(TEST) --settings=config.settings_test --keepdb

.PHONY: test-shell
test-shell:
	@echo "Opening shell in test container..."
	docker-compose -f docker-compose.test.yml --env-file env.test run --rm web bash

.PHONY: test-down
test-down:
	@echo "Stopping test environment..."
	docker-compose -f docker-compose.test.yml down
	@echo "Test environment stopped!"

.PHONY: test-clean
test-clean:
	@echo "Cleaning test environment (removing volumes)..."
	docker-compose -f docker-compose.test.yml down -v
	@echo "Test environment cleaned!"

.PHONY: test-logs
test-logs:
	@echo "Showing test environment logs..."
	docker-compose -f docker-compose.test.yml logs -f

.PHONY: test-logs-service
test-logs-service:
	@if [ -z "$(SERVICE)" ]; then \
		echo "Error: SERVICE variable not set. Usage: make test-logs-service SERVICE=web"; \
		exit 1; \
	fi
	docker-compose -f docker-compose.test.yml logs -f $(SERVICE)

.PHONY: test-localstack-check
test-localstack-check:
	@echo "Checking LocalStack S3 buckets..."
	docker-compose -f docker-compose.test.yml --env-file env.test exec localstack aws --endpoint-url=http://localhost:4566 s3 ls

.PHONY: test-coverage
test-coverage:
	@echo "Running tests with coverage in Docker..."
	docker-compose -f docker-compose.test.yml --env-file env.test run --rm test_runner sh -c "coverage run --source='.' manage.py test --settings=config.settings_test && coverage report && coverage html"
	@echo "Coverage report generated in htmlcov/"

.PHONY: test
test: test-build test-run test-down
	@echo "Test suite completed!"

# Help
.PHONY: help
help:
	@echo "Available commands:"
	@echo ""
	@echo "Static File Management:"
	@echo "  make static         - Build CSS, optimize JS, and collect/optimize static files (default)"
	@echo "  make css            - Build CSS only"
	@echo "  make js             - Build and optimize JavaScript only"
	@echo "  make collect        - Collect static files only"
	@echo "  make collect-optimize - Collect and optimize static files"
	@echo "  make clean          - Remove generated static files"
	@echo ""
	@echo "Docker Testing Commands:"
	@echo "  make test           - Run full test suite (build, run, cleanup)"
	@echo "  make test-build     - Build Docker test images"
	@echo "  make test-up        - Start test environment in background"
	@echo "  make test-run       - Run all tests"
	@echo "  make test-run-app APP=<app>    - Run tests for specific app"
	@echo "  make test-run-specific TEST=<path>  - Run specific test"
	@echo "  make test-shell     - Open shell in test container"
	@echo "  make test-down      - Stop test environment"
	@echo "  make test-clean     - Stop and remove test volumes"
	@echo "  make test-logs      - Show all test logs"
	@echo "  make test-logs-service SERVICE=<name> - Show logs for specific service"
	@echo "  make test-localstack-check  - Check LocalStack S3 buckets"
	@echo "  make test-coverage  - Run tests with coverage report"
	@echo ""
	@echo "Examples:"
	@echo "  make test-run-app APP=blog"
	@echo "  make test-run-specific TEST=blog.tests.test_models"
	@echo "  make test-logs-service SERVICE=localstack"