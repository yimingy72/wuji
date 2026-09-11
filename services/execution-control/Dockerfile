FROM ghcr.io/astral-sh/uv:0.12.11 AS uv
FROM python:3.13.15-slim-bookworm
COPY --from=uv /uv /usr/local/bin/uv
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY apps/api/pyproject.toml apps/api/pyproject.toml
COPY packages/agent-integration/pyproject.toml packages/agent-integration/pyproject.toml
COPY packages/task-runtime/pyproject.toml packages/task-runtime/pyproject.toml
COPY packages/cairn-bridge/pyproject.toml packages/cairn-bridge/pyproject.toml
RUN uv sync --frozen --no-dev --group task-runtime --group cairn-bridge --no-install-workspace
COPY apps/api apps/api
COPY packages/agent-integration packages/agent-integration
COPY packages/task-runtime packages/task-runtime
COPY packages/cairn-bridge packages/cairn-bridge
COPY scripts/platform/run-file.schema.json scripts/platform/run-file.schema.json
COPY services/execution-control services/execution-control
COPY services/cairn-dispatcher services/cairn-dispatcher
COPY services/core-fixtures services/core-fixtures
RUN uv sync --frozen --no-dev --group task-runtime --group cairn-bridge
ENV PATH="/app/.venv/bin:$PATH" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
