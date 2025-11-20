.PHONY: help install test run clean lint format check-env list-channels

help:  ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## Install dependencies and setup project
	@echo "Installing dependencies..."
	python3 -m venv venv
	. venv/bin/activate && pip install --upgrade pip
	. venv/bin/activate && pip install -r requirements.txt
	@if [ ! -f .env ]; then cp .env.example .env; echo "Created .env file - please configure it"; fi
	@echo "Setup complete!"

test:  ## Run all tests
	@echo "Running tests..."
	pytest tests/ -v

test-coverage:  ## Run tests with coverage report
	@echo "Running tests with coverage..."
	pytest tests/ --cov=. --cov-report=html --cov-report=term
	@echo "Coverage report generated in htmlcov/index.html"

run:  ## Run the bot
	@echo "Starting bot..."
	python main.py

run-dry:  ## Run the bot in dry-run mode
	@echo "Starting bot in DRY_RUN mode..."
	DRY_RUN=true python main.py

list-channels:  ## List configured channels
	python main.py --list-channels

get-channel-ids:  ## Run GetChannelId.py to find channel IDs
	python GetChannelId.py

clean:  ## Clean up cache and temporary files
	@echo "Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ .coverage
	@echo "Cleaned up cache files"

lint:  ## Run linting checks
	@echo "Running linting..."
	@which pylint > /dev/null 2>&1 || (echo "Installing pylint..." && pip install pylint)
	pylint *.py --disable=C0111,R0903 || true

format:  ## Format code with black
	@echo "Formatting code..."
	@which black > /dev/null 2>&1 || (echo "Installing black..." && pip install black)
	black *.py tests/*.py

check-env:  ## Check if .env file is configured
	@if [ ! -f .env ]; then \
		echo "❌ .env file not found. Run 'make install' or copy .env.example to .env"; \
		exit 1; \
	fi
	@echo "✅ .env file exists"
	@if grep -q "your_api_hash_here" .env; then \
		echo "⚠️  Warning: .env appears to contain example values. Please configure it."; \
	else \
		echo "✅ .env appears to be configured"; \
	fi

logs:  ## Tail the bot logs
	tail -f bot.log

health:  ## Check bot health status
	@if [ -f health.txt ]; then \
		echo "Health status:"; \
		cat health.txt; \
	else \
		echo "No health file found. Bot may not be running."; \
	fi

dev-install:  ## Install development dependencies
	pip install pytest pytest-cov black pylint mypy

requirements:  ## Update requirements.txt with current environment
	pip freeze > requirements.txt
	@echo "Updated requirements.txt"

