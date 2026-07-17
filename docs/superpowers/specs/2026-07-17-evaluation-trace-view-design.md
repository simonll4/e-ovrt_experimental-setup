# Vista correlacionada media↔control (Pieza B) — Diseño

**Fecha**: 2026-07-17
**Estado**: aprobado en brainstorming; pendiente de plan de implementación
**Repos**: `e-ovrt_experimental-setup` (webconsole BFF + SPA, el grueso) + `e-ovrt_control-plane`
(2 endpoints de lectura triviales)
**Alcance**: post-hoc. Para una corrida terminada, la consola muestra el ciclo completo de
cada frame: qué detectó el media-plane, si llegó al control-plane (o por qué se descartó),
cómo progresó cada patrón de riesgo, y qué alertas se confirmaron.

## 1. Propósito y contexto

Cierra la feature de tres piezas. Los cimientos ya están construidos y verificados:

- **Pieza A (control-plane)**: `GET :8081/api/runs/{id}/pattern-progress` — progreso
  parcial por-frame (`control.pattern_progress.v1`).
- **Pieza A2 (media-plane)**: `GET :8080/api/runs/{id}/dropped` — ledger de descartes
  por-frame (`media.dropped_unit.v1`).
- Preexistentes: `GET /api/runs/{id}/detections` (media, paginado, un `DetectionEvent` por
  frame con previews), `GET :8081/api/runs/{id}/alerts` (control), y el `ControlPlaneBackend`
  del BFF (spec 44b) que ya proxea el control-plane.

La clave de join entre planos es `unit_id`/`frame_index` (convención documentada del
proyecto). Todo es post-hoc: se relee sobre artefactos de corridas terminadas.

## 2. Decisiones cerradas

| # | Decisión | Razón |
|---|---|---|
| D1 | La vista vive como **sección de `RunDetailPage`** (Card "Evaluación del control-plane") | Un solo lugar por run; el detalle ya tiene detecciones/métricas/artefactos; cero navegación extra |
| D2 | **Tabla unificada por frame** (preview, detecciones, control, patrón) | Densa y escaneable; perfil de herramienta diaria; reusa `.eo-table` del kit |
| D3 | **El join se compone en el BFF**, no en el frontend | 4 fuentes con paginaciones distintas y frames intercalados: el merge cliente-side sería frágil; el BFF ya es la capa de traducción con ambos clientes |
| D4 | Dos endpoints de lectura nuevos en el control-plane: lookup por `media_run_id` y `received-units` | Sin ellos la correlación y la columna "llegó/no llegó" no son computables (el `metrics.jsonl` del control no se sirve hoy) |
| D5 | Degradación explícita y honesta en los 4 casos feos (§6) | Un vacío mentiroso ("cero descartes" cuando en realidad es "no instrumentado") es peor que un "n/d" |
| D6 | Barra de progreso en CSS puro sobre tokens (sin librería de charting) | Convención dependency-light del repo; un `<div>` con ancho % alcanza |

## 3. Endpoints nuevos en el control-plane (repo `e-ovrt_control-plane`)

Ambos espejo del patrón `RunManager.alerts()` ya existente (lectura tolerante de jsonl,
`UnknownRunError`→404):

1. **`GET /api/runs?media_run_id=<id>`** — lookup: escanea `runs/*/summary.json` y devuelve
   los runs de control cuyo `media_run_id` coincide: `[{control_run_id, status, started_at,
   alerts_count}]`, más reciente primero. Sin query param devuelve el listado completo (mismo
   shape). Summaries corruptos se saltean (mismo criterio que el resto del servicio).
2. **`GET /api/runs/{id}/received-units?limit=`** — los `unit_id` que el control recibió:
   lee `metrics.jsonl` (una fila por evento recibido, `ControlMetricSample`) y devuelve
   `[{unit_id}]` en orden (el contrato del control no guarda `frame_index`; el join
   unit_id→frame lo resuelve el BFF con los datos del lado media). Run inexistente → 404;
   sin archivo → 200 `[]`.

Aditivo estricto: nada existente cambia.

## 4. El trace compuesto en el BFF (repo `e-ovrt_experimental-setup`)

`GET /api/runs/{media_run_id}/trace?page=&page_size=&control_run_id=`

El BFF:
1. Trae el summary del run de medios (topología, totals) — ya lo hace.
2. Resuelve el run de control: `control_run_id` del query param si vino; si no, lookup por
   `media_run_id` y toma el **más reciente**.
3. Trae en paralelo: detecciones (media, todas las páginas), dropped (media, todas),
   pattern-progress (control), alerts (control), received-units (control).
4. Merge por `frame_index` en un eje unificado ordenado, y pagina el resultado.

Respuesta:

```
{
  media_run_id, control_run_id | null, topology,
  totals: { frames, detections, dropped_by_reason: {...}, alerts,
            received: int | null, not_received: int | null },
  page, page_size, total,
  frames: [ {
    frame_index, unit_id | null, timestamp_ms | null,
    detections: [{label, confidence}] | null,   # null = frame descartado (no procesado)
    control: "received" | "dropped:<reason>" | "not_received" | "n/d",
    progress: [{condition_id, progress, elapsed_ms, threshold_ms, mode}],  # [] si nada en curso
    alert: [{condition_id, severity}]           # [] si no se confirmó acá
  } ]
}
```

Semántica de `control` por frame:
- frame en el ledger de descartes → `"dropped:<reason>"` (nunca llegó a emitirse).
- frame con detección y `unit_id ∈ received-units` → `"received"`.
- frame con detección y `unit_id ∉ received-units` (habiendo run de control con
  received-units disponible) → `"not_received"` — los drops del bus EBE, derivados por
  set-difference, sin instrumentación extra.
- sin run de control, o run two-node sin ledger (ver §6) → `"n/d"`.

## 5. La vista (SPA)

Card "Evaluación del control-plane" en `RunDetailPage`, visible solo cuando el run terminó
(mismo gating que las detecciones actuales):

- **Tiles** (`StatTile`, fila `eo-stats-row`): run de control (id + status), alertas,
  descartados por motivo (uno por reason con conteo), no-recibidos (bus) si aplica.
- **La tabla** (mock aprobado): una fila por frame del eje unificado —
  `preview | detecciones (label + score) | control (Badge: ✓ received / ✗ reason / ~ n/d) |
  patrón (barra de progreso + condition_id; Badge de ALERTA al confirmarse)`.
  Barra: `<div class="eo-progressbar">` con ancho `progress*100%`; color `--status-warn`
  en curso, `--status-error` cuando el frame trae alerta.
- **Filtro** "solo frames con actividad" (checkbox): oculta filas sin detecciones, sin
  descarte, sin progreso y sin alerta. Estado local, default apagado.
- **Paginación real** (a diferencia de las detecciones actuales que muestran solo pág. 1):
  botones anterior/siguiente sobre el `trace`.

Lógica de mapeo estado→tono en un módulo de vista (`traceview.ts`), siguiendo el patrón
`runview.ts`/`experimentview.ts`: `controlTone("received")→ok`, `dropped:*→warn`,
`not_received→error`, `n/d→neutral`. Testeable sin render.

## 6. Degradación explícita (D5)

| Caso | Detección | Comportamiento |
|---|---|---|
| Run **two-node** | `summary.run_descriptor.topology == "two_node"` | Columna control muestra `n/d (two-node)` para descartes internos (gap documentado de A2 §8); `not_received` sí se computa si hay received-units |
| **Sin run de control** | lookup devuelve `[]` | Tiles y columnas de control muestran "no evaluado"; la tabla queda con las columnas de media (sigue útil) |
| **Control-plane caído** | error del `ControlPlaneBackend` | `ErrorBanner` en la sección; el resto del detalle intacto; el trace devuelve las columnas de media con `control: "n/d"` y un campo `control_error` |
| Run **en curso** | `status == running` | La sección no se muestra (post-hoc por diseño) |

## 7. Trampa de volumen

El BFF trae todas las páginas de detecciones/dropped para componer el eje (los endpoints
de plano cargan el jsonl completo por request — deuda preexistente compartida, anotada en
el review de A2). Para runs de escala demo/bench (cientos a pocos miles de frames) es
aceptable. Mitigación barata en el BFF: cache en memoria por `(media_run_id, control_run_id)`
del eje compuesto de runs **terminados** (inmutables por definición post-hoc), invalidado
por LRU chico. Si un run gigante lo vuelve lento, la paginación del trace ya acota la
respuesta; optimizar la lectura de origen es follow-up compartido con `/detections`.

## 8. Fuera de alcance

- Streaming en vivo del trace (post-hoc por diseño; D1 de la Pieza A).
- Cablear el ledger de descartes en two-node (follow-up de diseño propio, A2 §8).
- Dibujar bboxes sobre los previews (candidato a mejora posterior de la misma tabla).
- Tocar el motor, los artefactos o los contratos de los planos: B es consumidor puro de
  A + A2 + lo preexistente, salvo los dos endpoints de lectura del §3.

## 9. Testing

- **Control-plane** (pytest): lookup con/sin match, más-reciente-primero, summaries
  corruptos salteados; received-units 200/404/vacío. Espejo de los tests de A.
- **BFF** (pytest): el merge (frames intercalados procesado/descartado quedan ordenados);
  semántica de `control` en los 4 valores; set-difference `not_received`; paginación del
  eje unificado; degradación (sin control run, control caído → `control_error`, two-node);
  override `?control_run_id=`.
- **SPA** (vitest, patrón del repo: fireEvent, sin jest-dom): la sección renderiza tiles y
  tabla desde un trace mockeado; el filtro oculta filas sin actividad; los estados de
  degradación muestran su mensaje; `traceview.ts` testeado puro.

## 10. Criterios de éxito

1. Para un run DBE real evaluado por el control-plane, la sección muestra el ciclo completo
   frame a frame: detecciones, `received`, progreso creciente y la alerta en el frame en que
   se confirmó — sin tipear ningún id de control (correlación automática).
2. Un run con `stride>1` muestra sus frames descartados intercalados con reason, y la unión
   procesados ∪ descartados no tiene huecos inexplicados (criterio 3 de A2, ahora visible).
3. Un run EBE con drops de bus muestra `not_received` en los frames que el control no
   registró.
4. Los 4 casos de degradación del §6 muestran su estado sin romper el resto del detalle.
5. Suites de los tres repos verdes; cero cambios en artefactos/contratos existentes.
