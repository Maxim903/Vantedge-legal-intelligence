.DEFAULT_GOAL := help

.PHONY: help install lint format test pipeline-test web-test dbt-run clean

help:
	@printf '%s\n' \
		'Usage: make <target>' \
		'' \
		'Targets:' \
		'  install       Install pipeline dependencies and development tools' \
		'  lint          Run Ruff linting and strict mypy checks' \
		'  format        Format pipeline code with Ruff' \
		'  test          Run all available tests' \
		'  pipeline-test Run pipeline tests with coverage' \
		'  web-test      Run web tests when the app is initialized' \
		'  dbt-run       Run dbt models when the project is initialized' \
		'  clean         Remove generated caches and build artifacts' \
		'  help          Show this help message'

install:
	uv sync --project pipeline --extra dev

lint:
	cd pipeline && uv run --extra dev ruff check .
	cd pipeline && uv run --extra dev mypy

format:
	cd pipeline && uv run --extra dev ruff format .

test: pipeline-test web-test

pipeline-test:
	cd pipeline && uv run --extra dev pytest

web-test:
	@if [ -f apps/web/package.json ]; then \
		npm --prefix apps/web test; \
	else \
		printf '%s\n' 'Skipping web tests: apps/web/package.json does not exist yet.'; \
	fi

dbt-run:
	@if [ -f dbt/dbt_project.yml ]; then \
		dbt run --project-dir dbt; \
	else \
		printf '%s\n' 'Skipping dbt: dbt/dbt_project.yml does not exist yet.'; \
	fi

clean:
	rm -rf .ruff_cache pipeline/.pytest_cache pipeline/.mypy_cache \
		pipeline/.ruff_cache pipeline/src/vil_pipeline/__pycache__ \
		pipeline/tests/__pycache__ pipeline/.coverage pipeline/build pipeline/dist \
		dbt/target dbt/logs dbt/dbt_packages
