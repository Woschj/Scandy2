.PHONY: help install install-dev install-prod install-system install-full install-custom test test-unit test-integration test-security lint format clean docs build deploy dev prod

# Default target
help:
	@echo "Available commands:"
	@echo "Installation (system-wide requires sudo):"
	@echo "  install-full     Full installation with all features (sudo)"
	@echo "  install-dev      Development environment only"
	@echo "  install-prod     Production installation in /opt/scandy (sudo) ✅"
	@echo "  install-system   System-wide installation in /usr/local/scandy (sudo)"
	@echo "  install-custom   Custom installation path (INSTALL_DIR=...) (sudo)"
	@echo "  install          Install dependencies only"
	@echo ""
	@echo "Testing:"
	@echo "  test             Run all tests"
	@echo "  test-unit        Run unit tests only"
	@echo "  test-integration Run integration tests only"
	@echo "  test-security    Run security tests only"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint             Run linter"
	@echo "  format           Format code"
	@echo ""
	@echo "Maintenance:"
	@echo "  clean            Clean up temporary files"
	@echo "  docs             Generate documentation"
	@echo ""
	@echo "Deployment:"
	@echo "  build            Build for production"
	@echo "  deploy           Deploy to production"
	@echo ""
	@echo "Development:"
	@echo "  dev              Start development server"
	@echo "  prod             Start production server"

# Installation
install:
	pip install -r requirements.txt
	pip install -e .

install-dev:
	./install_scandy.sh --dev

install-prod:
	sudo ./install_scandy.sh --production

install-system:
	sudo ./install_scandy.sh --system

install-full:
	sudo ./install_scandy.sh

install-custom:
	@echo "Verwendung: sudo make install-custom INSTALL_DIR=/custom/path"
	@if [ -z "$(INSTALL_DIR)" ]; then \
		echo "Fehler: INSTALL_DIR muss gesetzt werden"; \
		echo "Beispiel: sudo make install-custom INSTALL_DIR=/usr/local/scandy"; \
		exit 1; \
	fi
	sudo ./install_scandy.sh --install-dir "$(INSTALL_DIR)"

# Testing
test:
	pytest

test-unit:
	pytest tests/unit/ -v

test-integration:
	pytest tests/integration/ -v

test-security:
	pytest -k "security" -v

# Code quality
lint:
	flake8 app/ tests/
	mypy app/

format:
	black app/ tests/
	isort app/ tests/

# Cleanup
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .coverage htmlcov/ .pytest_cache/
	rm -rf app/logs/*.log
	rm -rf app/flask_session/*

# Documentation
docs:
	sphinx-build -b html docs/ docs/_build/html

# Build and deploy
build:
	docker build -t scandy:latest .

deploy:
	docker-compose up -d

# Development server
dev:
	export FLASK_ENV=development && flask run --host=0.0.0.0 --port=5000

# Production server
prod:
	export FLASK_ENV=production && gunicorn -w 4 -b 0.0.0.0:5000 wsgi:app

# Database operations
db-init:
	export FLASK_ENV=development && python -c "from app import create_app; app = create_app(); app.run()"

db-migrate:
	@echo "Migration commands would go here"

# Security audit
security-audit:
	safety check
	bandit -r app/

# Performance profiling
profile:
	python -m cProfile -o profile.prof -s time app/wsgi.py
	snakeviz profile.prof
