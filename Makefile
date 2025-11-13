.PHONY: help install install-dev test test-verbose test-coverage lint format clean run

# Default target
help:
	@echo "YANA Development Commands"
	@echo "========================="
	@echo ""
	@echo "Setup:"
	@echo "  make install          Install package"
	@echo "  make install-dev      Install package with dev dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  make test             Run tests"
	@echo "  make test-verbose     Run tests with verbose output"
	@echo "  make test-coverage    Run tests with coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint             Run linter (ruff)"
	@echo "  make format           Format code with black"
	@echo "  make format-check     Check formatting without modifying"
	@echo ""
	@echo "Running:"
	@echo "  make run              Run yana"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean            Remove cache and build artifacts"

# Installation
install:
	uv pip install -e .

install-dev:
	uv pip install -e ".[dev]"

# Testing
test:
	.venv/bin/pytest tests/

test-verbose:
	.venv/bin/pytest tests/ -v

test-coverage:
	.venv/bin/pytest tests/ --cov=src --cov-report=html --cov-report=term

# Code quality
lint:
	.venv/bin/ruff check src/ tests/

format:
	.venv/bin/black src/ tests/

format-check:
	.venv/bin/black --check src/ tests/

# Running
run:
	.venv/bin/python -m src.cli

# Cleanup
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
