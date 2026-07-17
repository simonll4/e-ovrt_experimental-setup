# E-OVRT Web Console

Consola web de la plataforma E-OVRT-VDP: BFF FastAPI (`backend/`) + SPA React (`frontend/`),
**cliente** del servicio media-plane (Spec B). No ejecuta el pipeline: habla HTTP/WS con la
instancia del servicio (`EOVRT_CONSOLE_SERVICE_URL`, default `http://localhost:8080`).

Funciones: componer y lanzar corridas, ver el detalle en vivo (WS), **evaluar un run
BENCH contra el GT de seguridad** (AP@0.5 por clase, CR-01 recall, mAP@0.5) y **comparar
varios runs** (tabla + gráfico) en la página `/compare`.

Desde 2026-07-17 el detalle de un run terminado incluye la **vista correlacionada
media↔control** ("Evaluación del control-plane"): el BFF compone un trace por-frame
(`GET /api/runs/{id}/trace`) uniendo por `unit_id` las detecciones (con bboxes dibujadas
sobre los previews), el ledger de descartes del media-plane (`rate_gate`/sobrecarga), los
`unit_id` que el control-plane recibió (la diferencia = drops del bus en EBE), el progreso
parcial de patrones (barra 0–100% por condición) y las alertas confirmadas. La correlación
es automática (lookup por `media_run_id` en el control-plane, `EOVRT_CONSOLE_CONTROL_SERVICE_URL`,
default `:8081`); degradación explícita si el control está caído, el run no fue evaluado,
o es two-node (descartes internos "n/d").

### Fuentes de ingesta

La consola lanza runs desde: carpetas de imágenes (`image_folder`), archivos de
video (`video_file`) y cámaras IP por RTSP (`rtsp`). Las fuentes vivas (rtsp)
generan runs **infinitos**: se detienen manualmente desde la vista de run
("■ Detener"). Al guardar un manifiesto con una cámara RTSP, las credenciales
de la URL se escriben redactadas (`rtsp://***:***@...`); recompletá usuario y
clave al re-lanzar. `oak_d` (OAK-D Pro PoE) está soportado desde 2026-07-13:
requiere `url` = IP fija de la cámara, y aparece deshabilitado si el servicio
no tiene el SDK DepthAI instalado (extra `edge` del media-plane).

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

## Gestión de prompt sets

La vista `/prompts` lista y edita los prompt sets del repo (`prompts/*.yaml`) sin salir
de la consola: alta, edición, freeze con confirmación en dos pasos y derivación de un
set nuevo a partir de uno existente. El BFF expone el ciclo de vida completo en
`/api/prompt-sets`:

- `GET /api/prompt-sets` — lista todos los sets con `status`/`track`/conteos.
- `GET /api/prompt-sets/{set_id}` — detalle completo, incluye `frozen_sha256` si aplica.
- `POST /api/prompt-sets` — crea un set nuevo (`exploratory` por defecto).
- `PUT /api/prompt-sets/{set_id}` — actualiza un set no congelado.
- `DELETE /api/prompt-sets/{set_id}` — borra un set no congelado.
- `POST /api/prompt-sets/{set_id}/freeze-request` — pasa a `frozen_pending_review`.
- `POST /api/prompt-sets/{set_id}/freeze` — confirma el freeze, calcula y persiste
  `frozen_sha256`.
- `POST /api/prompt-sets/{set_id}/derive` — crea un set nuevo (`exploratory`) a partir de
  uno existente, con `derives_from` apuntando al origen.

Tres garantías, no negociables:

1. **Validación de schema**: todo alta/edición pasa por un espejo Pydantic del schema de
   prompt set (clases, phrasings, campos de lifecycle); un payload inválido devuelve 422
   con el detalle de qué campo falló, nunca se escribe a disco a medias.
2. **Inmutabilidad de los sets `frozen` por hash**: un set congelado no se puede editar ni
   borrar; `freeze` calcula `frozen_sha256` sobre las clases y lo persiste junto al set —
   cualquier intento de modificar un frozen es un 409, y el hash permite verificar en
   cualquier momento que el contenido no cambió desde el freeze.
3. **Transiciones de estado solo por acciones explícitas**: no hay edición implícita de
   `status`; se pasa de `exploratory` a `frozen` únicamente vía `freeze-request` →
   `freeze` (dos pasos, con revisión humana en el medio), y de un set existente a uno
   nuevo únicamente vía `derive`.

La consola nunca commitea: todos los cambios (crear, editar, borrar, freeze, derive)
quedan como working tree del repo — para revisión y `git commit` del usuario, no
automático.
