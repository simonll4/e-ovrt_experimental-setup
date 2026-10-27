# Imagen de la webconsole (BFF FastAPI + SPA embebida + docker CLI para orquestar).
# Build context: raíz del repo e-ovrt_experimental-setup, más el contexto con nombre
# `controlplane` = el repo e-ovrt_control-plane (lo pasa infra/platform/docker-compose.yml
# con `additional_contexts`; a mano: `docker build --build-context
# controlplane=../e-ovrt_control-plane -f infra/console/Dockerfile .`).
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
       ffmpeg \
    && rm -rf /var/lib/apt/lists/*
# ffmpeg: el video del Resultado de la demo en vivo (spec 2026-10-23 §6.4.5). Pillow y
# paho-mqtt (render y testigo MQTT de la demo) llegan como dependencias del BFF.

WORKDIR /app
COPY webconsole/backend/pyproject.toml ./backend/pyproject.toml
COPY webconsole/backend/src ./backend/src
RUN pip install --no-cache-dir ./backend
# Núcleo del control-plane (sin el extra [labs]): el runner evalúa las alertas contra el
# GT temporal con `eovrt-control evaluate-alerts` (spec 43 §6) y el driver de evidencia
# de la generación 2 (tools/evidencia, doc 134) lo usa igual. Sin esto, dentro del
# contenedor esa evaluación fallaba en silencio.
COPY --from=controlplane pyproject.toml /opt/control-plane/pyproject.toml
COPY --from=controlplane src /opt/control-plane/src
RUN pip install --no-cache-dir /opt/control-plane
COPY --from=spa /build/dist /app/spa-dist

ENV EOVRT_CONSOLE_SPA_DIST=/app/spa-dist
EXPOSE 8090
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s \
    CMD curl -sf http://localhost:8090/api/health || exit 1
CMD ["python", "-m", "uvicorn", "--factory", "eovrt_webconsole.app:create_app", \
     "--host", "0.0.0.0", "--port", "8090"]
