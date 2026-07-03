# E-OVRT Web Console (MVP)

Consola web de la plataforma E-OVRT-VDP: BFF FastAPI (`backend/`) + SPA React (`frontend/`),
**cliente** del servicio media-plane (Spec B). No ejecuta el pipeline: habla HTTP/WS con la
instancia del servicio (`EOVRT_CONSOLE_SERVICE_URL`, default `http://localhost:8080`).

## Uso

```bash
make install                       # venv backend + npm install
make test                          # pytest + ruff + vitest
make build                         # solo build de la SPA (npm run build); make serve depende de este target
make serve                         # build SPA + BFF en :8090 (sirve la SPA)
# Dev con hot-reload (dos terminales):
make dev-backend                   # BFF :8090
make dev-frontend                  # Vite :5173 (proxy /api -> :8090)
make smoke                         # curl /api/health + /api/target contra :8090 (con el server ya levantado)
```

Requiere el servicio media-plane corriendo (p.ej. `EOVRT_MODEL_REF=mock make serve`
en `../e-ovrt_media-plane`). Env vars: `EOVRT_CONSOLE_SERVICE_URL`,
`EOVRT_CONSOLE_REPO_ROOT` (default: autodescubierto), `EOVRT_CONSOLE_FROZEN_SETS`
(default `cr01_cr02_bench_v2`).
