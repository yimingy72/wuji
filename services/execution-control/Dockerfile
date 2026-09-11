FROM ghcr.io/astral-sh/uv:0.12.11@sha256:79c6f4776b851471cc73b7d21d0cc834bb94383c292e83640d27eff512864df7 AS uv
FROM python:3.13.15-slim-bookworm@sha256:ed86c82274b3c69b52fb5820f358f0bd7df0b603332063cb5c6e32bd220c3e6e
COPY --from=uv /uv /usr/local/bin/uv
RUN sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources \
 && apt-get update && apt-get install -y --no-install-recommends git ca-certificates \
 && rm -rf /var/lib/apt/lists/*
# BuildKit supplies only the verified public Cairn Git cache, never a user checkout.
COPY --from=cairn-git / /opt/wuji-upstream/cairn.git/
RUN test "$(git --git-dir=/opt/wuji-upstream/cairn.git rev-parse 8e7e0ea67552383851dfcabfba0c4e9c8d007878^{commit})" = "8e7e0ea67552383851dfcabfba0c4e9c8d007878" \
 && git config --global url."file:///opt/wuji-upstream/cairn.git".insteadOf https://github.com/oritera/Cairn.git
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
