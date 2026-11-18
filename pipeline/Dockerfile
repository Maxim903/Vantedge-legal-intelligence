FROM ghcr.io/astral-sh/uv:0.13.7 AS uv

FROM python:3.12-slim

COPY --from=uv /uv /uvx /bin/
ENV UV_PYTHON_DOWNLOADS=never \
    UV_NO_CACHE=1 \
    PATH="/app/pipeline/.venv/bin:${PATH}" \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1

WORKDIR /app/pipeline
COPY pipeline/pyproject.toml pipeline/uv.lock ./
RUN uv sync --frozen --no-dev --extra dbt --no-install-project

COPY pipeline/src ./src
COPY pipeline/prompts ./prompts
COPY pipeline/sql ./sql
COPY pipeline/job-entrypoint.sh ./job-entrypoint.sh
COPY graph/__init__.py graph/__main__.py graph/export.py graph/sync.py graph/constraints.cypher /app/graph/
COPY dbt /app/dbt
COPY docs/05-ia/golden-set.csv docs/05-ia/golden-set-titres.csv /app/docs/05-ia/
RUN uv sync --frozen --no-dev --extra dbt \
    && GCP_PROJECT_ID=build-placeholder dbt deps --project-dir /app/dbt --profiles-dir /app/dbt \
    && useradd --system --uid 10001 --create-home pipeline \
    && mkdir -p /app/docs/05-ia/evaluations \
    && chown pipeline:pipeline /app/docs/05-ia/evaluations \
    && chown -R pipeline:pipeline /app/dbt

USER pipeline
ENTRYPOINT ["python", "-m", "vil_pipeline.cli"]
