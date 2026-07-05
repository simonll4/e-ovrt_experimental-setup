# Imagen de la webconsole (BFF FastAPI + SPA embebida + docker CLI para orquestar).
# Build context: raíz del repo e-ovrt_experimental-setup.
FROM node:20-slim AS spa
WORKDIR /build
COPY webconsole/frontend/package.json webconsole/frontend/package-lock.json ./
RUN npm ci
COPY webconsole/frontend ./
RUN npm run build

FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1
# docker CLI + compose plugin (solo cliente; opera contra el socket montado)
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl gnupg \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc \
    && echo "deb [signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian bookworm stable" \
       > /etc/apt/sources.list.d/docker.list \
    && apt-get update && apt-get install -y --no-install-recommends docker-ce-cli docker-compose-plugin \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY webconsole/backend/pyproject.toml ./backend/pyproject.toml
COPY webconsole/backend/src ./backend/src
RUN pip install --no-cache-dir ./backend
COPY --from=spa /build/dist /app/spa-dist

ENV EOVRT_CONSOLE_SPA_DIST=/app/spa-dist
EXPOSE 8090
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s \
    CMD curl -sf http://localhost:8090/api/health || exit 1
CMD ["python", "-m", "uvicorn", "--factory", "eovrt_webconsole.app:create_app", \
     "--host", "0.0.0.0", "--port", "8090"]
