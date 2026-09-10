# E-OVRT Web Console

Consola web de la plataforma E-OVRT-VDP: BFF FastAPI (`backend/`) + SPA React (`frontend/`),
**cliente de los TRES servicios HTTP config-driven** (ADR-019): media-plane
(`EOVRT_CONSOLE_SERVICE_URL`, default `http://localhost:8080`), control-plane
(`EOVRT_CONSOLE_CONTROL_SERVICE_URL`, default `:8081`) y distribución de alertas
(`EOVRT_CONSOLE_DISTRIBUTION_SERVICE_URL`, default `:8082`). No ejecuta el pipeline ni
consume el bus ZeroMQ: habla HTTP/WS con cada servicio.

Funciones: componer y lanzar corridas, ver el detalle en vivo (WS), **evaluar un run
BENCH contra el GT de seguridad** (AP@0.5 por clase, CR-01 recall, mAP@0.5) y **comparar
varios runs** (tabla + gráfico) en la página `/compare`.

El detalle de un experimento terminado puede abrirse después de reiniciar la
consola: recupera su identidad desde `runs/<experiment_id>/report/report.json`
y sus alertas desde `control/alerts.jsonl` del consolidado. La consulta conserva
los artefactos originales y no relanza corridas. Si falta el archivo de alertas,
intenta consultarlas al servicio de control; la ausencia de reporte no se
interpreta como una ejecución exitosa.

Corridas y Experimentos abren la vista **Evidencia**; el selector permite ver
**Archivadas** o **Todas** y recuerda la elección en el navegador. Archivar sólo
oculta filas. La API conserva `vista=todas` por defecto tanto en `GET /api/runs`
como en `GET /api/experiments/manifests`; las pantallas solicitan la vista explícita.

El registro se carga una vez al crear la consola desde los cuatro CSV de
`results/evidence-runs/collections/`. Si falta, se informa en pantalla y Todas
permite consultar el historial. `results/evidence-runs/consola.yaml` contiene las
excepciones de experimentos revisadas por el usuario; reiniciar el BFF carga los
cambios del registro y de las excepciones.

La clasificación de los paraguas descubre `manifest.effective.yaml` a cualquier
profundidad dentro de `runs/` y busca identidades en todo el consolidado. Los
conteos históricos de ejecución se mantienen; los enlaces de evidencia se
presentan aparte y también abren consolidaciones anidadas después de reiniciar.
La tabla de clasificación se reproduce desde la raíz del repo con
`webconsole/backend/.venv/bin/python webconsole/tools/classify_evidence.py`.

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
en `../e-ovrt_media-plane`); si la distribución está habilitada, también el servicio
de distribución en `:8082`. Env vars:

- `EOVRT_CONSOLE_SERVICE_URL` — servicio media-plane (default `http://localhost:8080`).
- `EOVRT_CONSOLE_CONTROL_SERVICE_URL` — servicio control-plane (default `http://localhost:8081`).
- `EOVRT_CONSOLE_DISTRIBUTION_SERVICE_URL` — servicio de distribución de alertas
  (default `http://localhost:8082`).
- `EOVRT_CONSOLE_DISTRIBUTION_TRANSPORT` — transporte runner→distribución: `http`
  (default, ADR-020) o `subprocess` (**fallback operativo**, invoca la CLI
  `eovrt-distribute` como subproceso; ya no es un patrón de acople).
- `EOVRT_CONSOLE_REPO_ROOT` (default: autodescubierto).
- `EOVRT_CONSOLE_FROZEN_SETS` (default vacío — el `status` propio de cada YAML ya basta;
  ver `settings.py`).

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
