# Simple Makefile for static file management

# Variables
VENV := venv
PYTHON := $(VENV)/bin/python
MANAGE := $(PYTHON) manage.py

# Default target
.DEFAULT_GOAL := static

# Build CSS and collect static files
.PHONY: static
static:
	@echo "Building CSS..."
	$(MANAGE) build_css
	@echo "Collecting static files..."
	$(MANAGE) collectstatic_optimize
	@echo "Static files ready!"

# Just build CSS
.PHONY: css
css:
	$(MANAGE) build_css

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

# Help
.PHONY: help
help:
	@echo "Available commands:"
	@echo "  make static          - Build CSS and collect/optimize static files (default)"
	@echo "  make css            - Build CSS only"
	@echo "  make collect        - Collect static files only"
	@echo "  make collect-optimize - Collect and optimize static files"
	@echo "  make clean          - Remove generated static files"