.PHONY: help test test-unit test-integration test-security lint format clean docs build up down restart logs

# Default target
help:
	@echo "Available commands:"
	@echo "Docker Operations:"
	@echo "  build            Build the Docker images"
	@echo "  up               Start the application with Docker Compose"
	@echo "  down             Stop the application"
	@echo "  restart          Restart the application"
	@echo "  logs             View application logs"
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

# Docker
build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

restart:
	docker-compose restart

logs:
	docker-compose logs -f

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
