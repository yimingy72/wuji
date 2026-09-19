FROM --platform=$BUILDPLATFORM node:24.20.0-bookworm-slim@sha256:ba849c60be29959425b8734d57b8b4b7d56f98edd9504c9af091d5281095a71e AS build
WORKDIR /opt/wuji
ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0
RUN corepack enable && corepack prepare pnpm@10.32.1 --activate
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json apps/web/package.json
COPY packages/contracts/package.json packages/contracts/package.json
COPY packages/theme/package.json packages/theme/package.json
RUN pnpm install --frozen-lockfile --filter @wuji/web...
COPY apps/web apps/web
COPY packages/contracts packages/contracts
COPY packages/theme packages/theme
RUN pnpm --filter @wuji/web build

FROM nginxinc/nginx-unprivileged:1.29.1-alpine@sha256:27985295bdb22a1ef8f712863210bd5877c0f3006494a593e86b3fe0fa55467e
COPY --chmod=0644 apps/web/nginx.conf /etc/nginx/nginx.conf
COPY --from=build /opt/wuji/apps/web/dist /usr/share/nginx/html
USER 101:101
EXPOSE 8080
