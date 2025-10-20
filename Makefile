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
	@echo "Running pre-commit hooks..."
	@if command -v pre-commit >/dev/null 2>&1; then \
		pre-commit run -a; \
	else \
		echo "Warning: pre-commit not found, skipping hooks"; \
	fi
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
	rm -f static/css/*.opt.css
	rm -f static/css/combined.css static/css/combined.processed.css static/css/combined.purged.css
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


.PHONY: test-coverage
test-coverage:
	@echo "Running tests with coverage in Docker..."
	docker-compose -f docker-compose.test.yml --env-file env.test run --rm test_runner sh -c "coverage run --source='.' manage.py test --settings=config.settings_test && coverage report && coverage html"
	@echo "Coverage report generated in htmlcov/"

.PHONY: test
test: test-build test-run test-down
	@echo "Test suite completed!"

# FeeFiFoFunds Development Environment Commands
.PHONY: dev-up
dev-up:
	@echo "🚀 Starting FeeFiFoFunds development environment..."
	docker-compose -f docker-compose.dev.yml up -d
	@echo "✅ Development environment is running!"
	@echo ""
	@echo "Available services:"
	@echo "  - Django Web UI: http://localhost:8002"
	@echo "  - Flower (Celery monitoring): http://localhost:5557"
	@echo "  - PostgreSQL: localhost:5434"
	@echo "  - Redis: localhost:6381"
	@echo ""
	@echo "Admin credentials: admin / admin123"
	@echo ""
	@echo "Useful commands:"
	@echo "  make dev-logs      - View all logs"
	@echo "  make dev-shell     - Open Django shell"
	@echo "  make dev-down      - Stop environment"

.PHONY: dev-build
dev-build:
	@echo "🔨 Building development Docker images..."
	docker-compose -f docker-compose.dev.yml build

.PHONY: dev-down
dev-down:
	@echo "🛑 Stopping development environment..."
	docker-compose -f docker-compose.dev.yml down
	@echo "✅ Development environment stopped!"

.PHONY: dev-clean
dev-clean:
	@echo "🧹 Cleaning development environment (removing volumes)..."
	docker-compose -f docker-compose.dev.yml down -v
	@echo "✅ Development environment cleaned!"

.PHONY: dev-restart
dev-restart:
	@echo "🔄 Restarting development environment..."
	docker-compose -f docker-compose.dev.yml restart
	@echo "✅ Development environment restarted!"

.PHONY: dev-logs
dev-logs:
	@echo "📋 Showing development environment logs..."
	docker-compose -f docker-compose.dev.yml logs -f

.PHONY: dev-shell
dev-shell:
	@echo "🐚 Opening Django shell in development container..."
	docker-compose -f docker-compose.dev.yml exec web python manage.py shell

.PHONY: dev-bash
dev-bash:
	@echo "💻 Opening bash shell in development container..."
	docker-compose -f docker-compose.dev.yml exec web bash

.PHONY: dev-migrate
dev-migrate:
	@echo "🗄️  Running migrations in development environment..."
	docker-compose -f docker-compose.dev.yml exec web python manage.py migrate

.PHONY: dev-makemigrations
dev-makemigrations:
	@echo "📝 Creating migrations in development environment..."
	docker-compose -f docker-compose.dev.yml exec web python manage.py makemigrations

.PHONY: dev-test
dev-test:
	@echo "🧪 Running tests in development environment..."
	docker-compose -f docker-compose.dev.yml exec web python manage.py test

.PHONY: dev-psql
dev-psql:
	@echo "🗄️  Opening PostgreSQL shell..."
	docker-compose -f docker-compose.dev.yml exec postgres psql -U feefifofunds_dev -d feefifofunds_dev

.PHONY: dev-redis
dev-redis:
	@echo "💾 Opening Redis CLI..."
	docker-compose -f docker-compose.dev.yml exec redis redis-cli

# Help
.PHONY: help
help:
	@echo "Available commands:"
	@echo ""
	@echo "Static File Management:"
	@echo "  make static         - Build CSS, optimize JS, collect/optimize static files, and run pre-commit hooks (default)"
	@echo "  make css            - Build CSS only"
	@echo "  make js             - Build and optimize JavaScript only"
	@echo "  make collect        - Collect static files only"
	@echo "  make collect-optimize - Collect and optimize static files"
	@echo "  make clean          - Remove generated static files"
	@echo ""
	@echo "FeeFiFoFunds Development Environment:"
	@echo "  make dev-up         - Start development environment (Django + PostgreSQL + Redis + Celery + Flower)"
	@echo "  make dev-build      - Build development Docker images"
	@echo "  make dev-down       - Stop development environment"
	@echo "  make dev-clean      - Stop and remove all development volumes"
	@echo "  make dev-restart    - Restart all development services"
	@echo "  make dev-logs       - Show all logs (follow mode)"
	@echo "  make dev-shell      - Open Django shell"
	@echo "  make dev-bash       - Open bash shell in web container"
	@echo "  make dev-migrate    - Run database migrations"
	@echo "  make dev-makemigrations - Create new migrations"
	@echo "  make dev-test       - Run tests in development environment"
	@echo "  make dev-psql       - Open PostgreSQL shell"
	@echo "  make dev-redis      - Open Redis CLI"
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
	@echo "  make test-coverage  - Run tests with coverage report"
	@echo ""
	@echo "Examples:"
	@echo "  make dev-up && make dev-logs     - Start and watch logs"
	@echo "  make test-run-app APP=blog"
	@echo "  make test-run-specific TEST=blog.tests.test_models"
