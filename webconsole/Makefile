PY = backend/.venv/bin/python
PORT ?= 8090

install:
	cd backend && python3 -m venv .venv && .venv/bin/pip install --upgrade pip && .venv/bin/pip install -e ".[dev]"
	cd frontend && npm install

test:
	cd backend && .venv/bin/python -m pytest -q && .venv/bin/ruff check src tests
	cd frontend && npx vitest run

build:
	cd frontend && npm run build

# Herramienta local sin auth: bind por defecto a loopback. Para exponerla en la LAN,
# invocá uvicorn manualmente con --host 0.0.0.0 bajo tu propia responsabilidad.
serve: build
	cd backend && .venv/bin/uvicorn eovrt_webconsole.app:create_app --factory --host 127.0.0.1 --port $(PORT)

dev-backend:
	cd backend && .venv/bin/uvicorn eovrt_webconsole.app:create_app --factory --port $(PORT) --reload

dev-frontend:
	cd frontend && npm run dev

smoke:
	curl -sf http://localhost:$(PORT)/api/health && curl -sf http://localhost:$(PORT)/api/target && echo OK
