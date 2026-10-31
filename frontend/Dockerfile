# Production image for the dashboard: nginx serves the built app and proxies the API.
# Build from the repo root, which holds the pnpm workspace and lockfile:
#   docker build -f frontend/Dockerfile .

FROM node:25-slim AS build

WORKDIR /app
# pnpm 10 matches CI.
RUN npm install --global pnpm@10

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY frontend/package.json frontend/
RUN pnpm install --frozen-lockfile --filter ./frontend

COPY frontend/ frontend/
# Leave empty to call the API on the same origin, through the proxy below.
ARG VITE_API_URL=
RUN pnpm --dir frontend build


FROM nginxinc/nginx-unprivileged:1-alpine AS runtime

# Filled in at startup by the image's envsubst step.
ENV API_UPSTREAM=http://backend:8000 \
    PORT=8080
COPY frontend/nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/frontend/dist /usr/share/nginx/html

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO /dev/null "http://127.0.0.1:${PORT}/" || exit 1
