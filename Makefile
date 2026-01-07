# ============================================
# Rush Royale Bot - Makefile
# ============================================
# Cross-platform development convenience commands
# Usage: make <target>
# ============================================

.PHONY: help install install-dev test lint format clean run

# Default target
help:
	@echo "Rush Royale Bot - Available Commands"
	@echo "====================================="
	@echo "  make install      Install production dependencies"
	@echo "  make install-dev  Install development dependencies"
	@echo "  make run          Start the GUI"
	@echo "  make test         Run tests"
	@echo "  make lint         Run linting (ruff)"
	@echo "  make format       Format code (black + isort)"
	@echo "  make clean        Remove cache and build files"
	@echo ""

# === Installation ===
install:
	@echo "Installing production dependencies..."
	pip install -r requirements.txt

install-dev:
	@echo "Installing development dependencies..."
	pip install -r requirements-dev.txt

# === Running ===
run:
	@echo "Starting Rush Royale Bot GUI..."
	python Src/gui.py

# === Testing ===
test:
	@echo "Running tests..."
	pytest tests/ -v

test-cov:
	@echo "Running tests with coverage..."
	pytest tests/ -v --cov=Src --cov-report=html

# === Code Quality ===
lint:
	@echo "Running linter..."
	ruff check Src/

lint-fix:
	@echo "Running linter with auto-fix..."
	ruff check Src/ --fix

format:
	@echo "Formatting code..."
	black Src/
	isort Src/

format-check:
	@echo "Checking code formatting..."
	black Src/ --check
	isort Src/ --check-only

type-check:
	@echo "Running type checker..."
	pyright Src/

# === Cleaning ===
clean:
	@echo "Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf htmlcov/ .coverage 2>/dev/null || true
	@echo "Done!"

# === All-in-one ===
check: lint format-check type-check
	@echo "All checks passed!"

dev-setup: install-dev
	@echo "Development environment ready!"
