# Ventana "Cámaras": preview de fuentes en vivo — Diseño

**Fecha**: 2026-07-18
**Repos afectados**: `e-ovrt_media-plane` (sesión de preview), `e-ovrt_experimental-setup` (webconsole + presets de cámara)
**Estado**: aprobado en brainstorming, pendiente de plan de implementación

## Problema

Hoy no hay forma de ver una fuente de video (cámara RTSP, OAK-D) en vivo sin ejecutar
toda la plataforma experimental: cada prueba implica crear un run completo, con
artefactos, ciclo de vida y sin visualización de frames en tiempo real (la consola solo
muestra telemetría en vivo; los previews con cajas son post-hoc). Se necesita una
herramienta de **posicionamiento de cámara** y **prueba rápida de sets de prompts** con
detección visible en tiempo real desde la UI.

## Decisiones tomadas (brainstorming)

1. **Dos modos**: "solo video" (sin inferencia, fluido, para posicionar) y "detección en
   vivo" (con set de prompts activo). No hay toggle de inferencia en caliente: cambiar de
   modo o de prompts reconecta la sesión.
2. **Prompts**: se selecciona un prompt set del catálogo y se puede **editar al vuelo sin
   guardar** (frases/clases); si el resultado convence, se guarda como set nuevo
   (`exploratory`) vía el prompt store existente.
3. **Cámaras como presets guardados**: YAML con nombre en el repo experimental-setup,
   editables desde la UI. Sin override puntual en v1.
4. **Exclusión mutua estricta**: cualquier modo de la ventana ocupa el mismo slot único
   que los runs del media-plane. Run activo bloquea preview y viceversa, con mensaje
   claro y botón de inicio deshabilitado en ambas direcciones.
5. **Arquitectura**: sesión de preview propia en el media-plane (Enfoque 1). Se descartó
   reutilizar la maquinaria de runs (ensucia la lista de corridas, arranque pesado) y
   MJPEG + WS separados (overlay desincronizado).

## Arquitectura

```
webconsole SPA ── BFF (FastAPI) ── media-plane :8080
   /cameras        preview.py        POST/GET/DELETE /api/preview
                   (proxy REST+WS)   WS /api/preview/stream  ← frame JPEG + detecciones juntos
                   cameras.py        (PreviewManager, slot compartido con RunManager)
                   camera_store.py → cameras/*.yaml (presets)
```

## 1. Media-plane: sesión de preview

Nuevo `PreviewManager` en `app.state`, hermano de `RunManager`.

### Endpoints

- `POST /api/preview` → 201 `{preview_id}`. Body:

  ```yaml
  mode: raw | detect
  ingest: {plugin: <id del registro de fuentes>, config: {...}}   # mismo contrato que runs
  prompts: {set_inline: {...}, active_ids: [...]}                 # requerido si mode=detect
  params: {score_threshold: float}                                # opcional, solo detect
  ```

  Reutiliza el registro de fuentes tal cual (`rtsp`, `oak_d`; `video_file` e
  `image_folder` quedan disponibles gratis) y el modelo ya cargado en memoria.
  - 409 si hay run activo: `{reason: "run_active", active_run_id}`.
  - 409 si ya hay preview activa: `{reason: "preview_active"}`.
  - 422 si config inválida (mismo criterio de validación que runs).
- `DELETE /api/preview` → 204. Parada cooperativa vía `request_stop()` de la fuente
  (respeta la trampa ZeroMQ/threads: nunca cerrar sockets desde otro hilo).
- `GET /api/preview` → estado: `idle | streaming | error` (+ mensaje de error, config
  activa, mode).
- `WS /api/preview/stream` → un mensaje **binario** por frame:

  ```
  [uint32 BE: longitud del header][header JSON UTF-8][bytes JPEG]
  ```

  Header: `{seq, ts, width, height, mode, detections: [{bbox_norm_xyxy, label, score}]}`.
  En modo `raw`, `detections` va vacío. Frame y cajas viajan juntos: overlay siempre
  sincronizado. Códigos de cierre análogos al WS de runs (4404 sin sesión, 4503 no listo).

### Política de frames

Siempre se envía el **último frame disponible**; si el cliente va lento se descartan
intermedios, nunca se encola. En `raw`: re-escala a máx. ~960 px de ancho, JPEG calidad
media, objetivo 10-15 fps por WS. En `detect`: el ritmo lo marca la inferencia del
modelo; se envía el frame que se infirió con sus detecciones.

### Sin persistencia

La preview no escribe nada: sin `runs/<id>/`, sin `detections.jsonl`, sin artefactos,
sin publicación al bus ZeroMQ.

### Cambios de config en caliente

No hay update in-place: la UI hace `DELETE` + `POST` con la nueva config (prompts,
threshold, modo). Con el modelo ya cargado el ciclo es ~1 s.

## 2. Exclusión mutua con los runs

Slot de actividad único compartido:

- `RunManager.start_run` → `409 {reason: "preview_active"}` si hay preview activa.
- `PreviewManager.start` → `409 {reason: "run_active", active_run_id}` si hay run activo.

**Único cambio a código existente del media-plane**: el chequeo cruzado en
`RunManager.start_run`. Todo lo demás de runs (schema `RunRequest`, pipeline,
artefactos, WS de telemetría, bus) queda intacto.

## 3. Webconsole

### BFF

- `routers/preview.py`: proxy REST (`POST/GET/DELETE /api/preview`) + passthrough
  binario del WS hacia el media-plane (mismo patrón que `routers/stream.py`).
- `routers/cameras.py` + `camera_store.py` (estilo `prompt_store.py`): CRUD de presets.
  Presets en `e-ovrt_experimental-setup/cameras/*.yaml`:

  ```yaml
  id: oak-d-lab
  name: OAK-D laboratorio
  plugin: oak_d
  config: {ip: 192.168.1.50, ...}   # se pasa verbatim como ingest.config
  ```

  La consola no valida la config de fuente: el media-plane es el validador final
  (mismo principio que con los prompt sets).

### Frontend: página `/cameras` ("Cámaras", grupo Sistema)

Construida con el kit existente (tokens, `Card`, `Badge`, `StatTile`, `DetChip`, …).

- **Columna izquierda**: lista de presets + botón conectar + editor de preset
  (crear/editar/borrar).
- **Centro (viewer)**: `<canvas>` que pinta el JPEG del WS y superpone las cajas
  reutilizando la lógica de `PreviewWithBoxes` / `traceview.labelColor`. Indicador de
  fps y estado de conexión; toggle de labels; leyenda de clases con conteos (`DetChip`).
- **Panel derecho**: toggle "Solo video / Detección". Con detección activa: selector de
  prompt set del catálogo, editor liviano de frases al vuelo (sin guardar), slider de
  `score_threshold`, botón **Aplicar** (reconecta con la nueva config) y **Guardar como
  set nuevo** (prompt store existente, entra como `exploratory`).
- **Estado ocupado**: ante 409, banner claro ("Hay un run en ejecución: `<run_id>`.
  Detenelo para usar la prueba de cámaras") y botón de conectar deshabilitado. Inverso
  en la página de composición de runs: "Hay una prueba de cámara activa".
- Si el servicio corre con `EOVRT_MODEL_REF=mock`, badge visible "modelo: mock".

## 4. Manejo de errores

- Fallo de fuente (RTSP caída, OAK-D inaccesible): la sesión pasa a `error` con mensaje;
  el WS lo notifica y la UI lo muestra sin romper la página. El reconnect de RTSP ya lo
  maneja la fuente existente.
- Cliente WS desconectado: la sesión sigue viva (se puede reconectar el WS); el
  `DELETE` explícito o el cierre de la página (best-effort) la detienen.
- Caída del media-plane: el BFF responde 502 como ya hace en `catalog.py`; la UI muestra
  estado desconectado.

## 5. Garantía de no-regresión (plataforma experimental)

- **Cero cambios** en: schemas de `RunRequest`, pipeline de runs, artefactos, WS de
  telemetría de runs, bus ZeroMQ, control-plane, flujo de experimentos, evaluación.
- Cambios a código existente, exhaustivo: (a) chequeo de slot en `RunManager.start_run`;
  (b) manejo del nuevo motivo de 409 en la UI de compose (que ya maneja 409 hoy);
  (c) alta de la ruta/nav en la consola.
- La suite completa existente de media-plane y webconsole debe pasar intacta.

## 6. Testing

- **media-plane** (pytest, sin hardware): exclusión mutua en ambas direcciones (409 con
  `reason` correcto); protocolo WS binario (header + JPEG parseables, `seq` creciente);
  modo `raw` vs `detect` con modelo mock y fuente `image_folder` sintética; `DELETE`
  detiene limpio; sesión pasa a `error` ante fuente inválida.
- **webconsole**: fakes de servicio extendidos con los endpoints de preview; CRUD de
  presets de cámara; render de la página con estados idle/streaming/error/ocupado.
- **Manual con hardware** (no bloqueante): OAK-D real y cámara RTSP del lab.

## Fuera de alcance (v1)

- Toggle de inferencia en caliente sin reconectar.
- Override puntual de parámetros de un preset sin editarlo.
- Múltiples previews simultáneas / multi-cámara en grilla.
- Grabación o persistencia de lo visto en la preview.
