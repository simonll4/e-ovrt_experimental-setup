# E-OVRT Web Console

Consola web de la plataforma E-OVRT-VDP: BFF FastAPI (`backend/`) + SPA React (`frontend/`),
**cliente** del servicio media-plane (Spec B). No ejecuta el pipeline: habla HTTP/WS con la
instancia del servicio (`EOVRT_CONSOLE_SERVICE_URL`, default `http://localhost:8080`).

Funciones: componer y lanzar corridas, ver el detalle en vivo (WS), **evaluar un run
BENCH contra el GT de seguridad** (AP@0.5 por clase, CR-01 recall, mAP@0.5) y **comparar
varios runs** (tabla + gráfico) en la página `/compare`.

### Fuentes de ingesta

La consola lanza runs desde: carpetas de imágenes (`image_folder`), archivos de
video (`video_file`) y cámaras IP por RTSP (`rtsp`). Las fuentes vivas (rtsp)
generan runs **infinitos**: se detienen manualmente desde la vista de run
("■ Detener"). Al guardar un manifiesto con una cámara RTSP, las credenciales
de la URL se escriben redactadas (`rtsp://***:***@...`); recompletá usuario y
clave al re-lanzar. `oak_d` no está soportado hasta contar con el hardware.

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
