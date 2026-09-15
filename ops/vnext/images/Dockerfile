ARG PYTHON_IMAGE=python:3.13.15-slim-bookworm
ARG NODE_IMAGE=node:24.20.0-bookworm-slim
ARG UV_IMAGE=ghcr.io/astral-sh/uv:0.12.11
ARG KALI_IMAGE=kalilinux/kali-rolling:latest
FROM ${NODE_IMAGE} AS node
FROM ${UV_IMAGE} AS uv
FROM ${PYTHON_IMAGE} AS base
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_PYTHON_DOWNLOADS=never UV_LINK_MODE=copy \
    PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONUNBUFFERED=1
WORKDIR /opt/wuji
COPY packages/wuji-core /opt/wuji/packages/wuji-core
COPY packages/maf-worker /opt/wuji/packages/maf-worker
COPY packages/task-runtime /opt/wuji/packages/task-runtime
RUN uv sync --project /opt/wuji/packages/maf-worker --frozen --no-dev --python /usr/local/bin/python \
    && /opt/wuji/packages/maf-worker/.venv/bin/python -c "import sys; from importlib.metadata import version; assert sys.version_info[:3] == (3,13,15); assert version('agent-framework-core') == '1.18.0'; assert version('agent-framework-openai') == '1.14.3'" \
    && node -e "require('node:sqlite')" \
    && mkdir -p /var/lib/wuji/agent /var/lib/wuji/platform /workspace \
    && chown 10001:10000 /var/lib/wuji/agent /var/lib/wuji/platform \
    && chown 10002:10000 /workspace
COPY services/maf-supervisor /opt/wuji/services/maf-supervisor
RUN chmod -R a+rX /opt/wuji

FROM base AS agent
ENV NODE_EXTRA_CA_CERTS=/config/ca.crt \
    WUJI_DEPLOYMENT_CONFIG=/config/supervisor.json
USER 10001:10000
EXPOSE 8443
ENTRYPOINT ["node", "/opt/wuji/services/maf-supervisor/main.mjs", "--factory", "/opt/wuji/services/maf-supervisor/deployment.mjs"]

FROM base AS platform
COPY ops/vnext/pyproject.toml ops/vnext/uv.lock /opt/wuji/ops/vnext/
RUN uv sync --project /opt/wuji/ops/vnext --frozen --no-dev --python /usr/local/bin/python
COPY services/wuji-runtime /opt/wuji/services/wuji-runtime
COPY services/wuji-api /opt/wuji/services/wuji-api
COPY services/wuji-web-gateway /opt/wuji/services/wuji-web-gateway
COPY services/wuji-scheduler /opt/wuji/services/wuji-scheduler
COPY ops/vnext/deployment_common.py /opt/wuji/ops/vnext/deployment_common.py
COPY ops/vnext/gate_deployment.py ops/vnext/kali_deployment.py ops/vnext/pod_deployment.py /opt/wuji/ops/vnext/
COPY ops/vnext/bootstrap.py ops/vnext/synthetic_model.py /opt/wuji/ops/vnext/
COPY services/wuji-kali-executor /opt/wuji/services/wuji-kali-executor
RUN chmod -R a+rX /opt/wuji
ENV PATH=/opt/wuji/ops/vnext/.venv/bin:$PATH \
    PYTHONPATH=/opt/wuji/ops/vnext \
    WUJI_DEPLOYMENT_CONFIG=/config/deployment.json
USER 10001:10000
EXPOSE 8443
ENTRYPOINT ["python", "/opt/wuji/services/wuji-runtime/main.py", "--factory", "deployment:build_runtime", "--port", "8443", "--ssl-certfile", "/run/wuji/credentials/tls.crt", "--ssl-keyfile", "/run/wuji/credentials/tls.key"]

FROM ${KALI_IMAGE} AS kali
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates libbz2-1.0 libexpat1 libffi8 liblzma5 libsqlite3-0 libssl3t64 zlib1g \
    && rm -rf /var/lib/apt/lists/*
COPY --from=platform /usr/local /usr/local
COPY --from=platform /opt/wuji /opt/wuji
ENV PATH=/opt/wuji/ops/vnext/.venv/bin:$PATH PYTHONPATH=/opt/wuji/ops/vnext \
    PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONUNBUFFERED=1 \
    WUJI_DEPLOYMENT_CONFIG=/config/kali.json
RUN mkdir -p /workspace /var/lib/wuji/kali-receipts \
    && chown -R 10002:10000 /workspace /var/lib/wuji/kali-receipts
WORKDIR /opt/wuji
USER 10002:10000
EXPOSE 8444
ENTRYPOINT ["python", "-m", "uvicorn", "kali_deployment:build_kali", "--factory", "--host", "0.0.0.0", "--port", "8444", "--ssl-certfile", "/run/wuji/credentials/tls.crt", "--ssl-keyfile", "/run/wuji/credentials/tls.key", "--no-access-log"]
