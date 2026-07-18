# Evaluación BENCH + compare-runs en la consola — Diseño (Fase 2 / feature C)

- **Fecha:** 2026-07-04 · **Revisión:** 2026-07-04 (corregido tras auditoría adversarial contra el código real)
- **Estado:** aprobado para escribir plan de implementación
- **Repos:** `e-ovrt_media-plane` (servicio: evaluación) + `e-ovrt_experimental-setup/webconsole/` (BFF + SPA). Feature cross-repo, un solo spec/plan.
- **Depende de:** servicio de inferencia (Spec A, Fase 1) + webconsole MVP (Spec B, Fase 1), implementados. Reusa `eovrt_media.evaluation.run_evaluation` (existente).

## 0. Correcciones de la auditoría (por qué esta revisión difiere de lo obvio)

Verificado contra el código real (no resúmenes) y ejecutando `run_evaluation`:
- El resultado real es `EvalPerceptionResults` (schemas.py), **no** `PerceptionResult`; trae `type:"perception"` + `evaluated_at`; `AP50` es `0.0` (no `null`) cuando hay GT pero 0 matches.
- `run_evaluation` **NO distingue** un run no-BENCH: evalúa cualquier `detections.jsonl` y da ceros. El gate 422 es lógica del **endpoint** sobre la procedencia, no del runner.
- `bench_split` vive **solo** en `run_provenance.json` (`dataset_id/view/split`); el `get()`/`list_runs` del servicio hoy leen solo `summary.json`. Exponer `bench_split`/`evaluated` es el **prerequisito fundacional** (Tarea 1).
- **GT combinado:** el BENCH es UN COCO de 196 imgs (val 114 + test 82); no hay GT por-split. Evaluar un run de un split contra el GT completo deflacta AP/recall ~40-58% → **estrategia: restringir el GT a las imágenes del run** (§3.5).
- `run_evaluation` **ya persiste** `eval_perception.json` (no atómico, sin `mAP50`). El endpoint pasa a ser dueño de la persistencia enriquecida y atómica (§3.4).
- Helpers de F1 (`atomic_write_json`, `require_valid_run_id`) existen; eval es rápida (0.01s, stdlib puro, sin pycocotools); matching por basename funciona (196/196 verificado); `BFF no importa eovrt_media` se sostiene.

## 1. Propósito

Desde la consola: (a) **evaluar** un run terminado hecho sobre un split BENCH contra el GT de seguridad → AP@0.5 por clase, CR-01 recall, mAP@0.5; y (b) **comparar** varios runs (modelos) con tabla + gráfico. Objetivo académico: comparar GDINO / YOLOE / MM-GDINO sobre `person`/`helmet`/`vest`/`bare_head` y CR-01/CR-02. Reusa `run_evaluation`; no reimplementa métricas.

## 2. Restricción arquitectónica

La evaluación **corre en el servicio media-plane** (única capa con los artefactos + el GT + `eovrt_media.evaluation`). El **BFF nunca importa `eovrt_media`** → solo proxya y agrega. **El servicio debe correr desde la raíz del media-plane** (el auto-descubrimiento del GT usa paths relativos al CWD, igual que `configs/datasets/*`); si el GT no se encuentra → 422 accionable.

## 3. Capa servicio (media-plane)

### 3.1 Prerequisito (Tarea fundacional) — `bench_split`/`evaluated` en el info del run
Hoy `RunManager.get()`/`list_runs()` leen solo `summary.json`. Se agrega:
- `get(run_id)` y cada fila de `list_runs()` leen también `run_provenance.json` (barato: ya se recorre el dir) y derivan **`bench_split: str | null`** (de `split` de la procedencia si corresponde a un split BENCH conocido, sino `null`) y **`evaluated: bool`** (`(run_dir/"eval_perception.json").exists()` — un `stat` por run, sin depender de la hidratación N+1 del BFF).
- Splits BENCH reconocidos = los que tienen GT: `{bench_v2_test, bench_v2_val}` (resuelto contra la existencia del GT, no hardcode gratuito).
- Un run es **evaluable** ⇔ `bench_split != null` ∧ `status` terminal.

### 3.2 `POST /api/runs/{run_id}/evaluate`
- `require_valid_run_id(run_id)` (404 si inválido).
- **Gate 422 (endpoint, sobre la procedencia):** si `bench_split == null` → `422` "el run no fue sobre un split del BENCH". Si el run está `running` → `409` "no se evalúa un run en curso".
- Corre `run_evaluation(run_dir, iou_threshold=<default 0.5>, restrict_gt_to_detections=True)` (§3.5).
- **Enriquece** el resultado con `mAP50` (§3.3), `model` (de `summary.model_name`) y `bench_split`, y **persiste** `eval_perception.json` **atómico** (`atomic_write_json`). El endpoint es dueño de la persistencia enriquecida; `run_evaluation` no reescribe cuando el servicio la invoca (se le pasa `persist=False`, ver §3.4).
- `FileNotFoundError` del runner (GT ausente) → `422` con mensaje accionable ("verificá `../e-ovrt_datasets` / corré `build_person_gt.py`").
- Éxito → `200` con el objeto enriquecido (§3.3).

### 3.3 Shape del resultado (real + enriquecido)
```json
{
  "type": "perception",
  "run_id": "run_...",
  "benchmark": "construction_site_safety_bench",
  "iou_threshold": 0.5,
  "evaluated_at": "2026-07-04T07:53:54+00:00",
  "per_class": [
    {"class_name": "person",  "AP50": 0.72, "n_gt": 82,  "n_det": 90},
    {"class_name": "helmet",  "AP50": 0.61, "n_gt": 60,  "n_det": 70},
    {"class_name": "vest",    "AP50": 0.55, "n_gt": 48,  "n_det": 44},
    {"class_name": "bare_head","AP50": 0.0, "n_gt": 12,  "n_det": 20}
  ],
  "cr01_detection_recall": 0.64,
  "mAP50": 0.47,
  "model": "grounding_dino",
  "bench_split": "bench_v2_test"
}
```
- `type`/`evaluated_at`/`benchmark`/`iou_threshold`/`per_class`/`cr01_detection_recall` = passthrough de `EvalPerceptionResults`. `AP50` es `float | None` (`null` sin GT de esa clase; `0.0` con GT y 0 matches).
- `mAP50` = media de los `AP50` no-nulos (incluye `bare_head=0.0` si tiene GT — misma fórmula que el script de datasets). Calculado en el endpoint.
- `model`/`bench_split` embebidos → el compare no necesita un fetch extra de info por run (§4.2).

### 3.4 `GET /api/runs/{run_id}/evaluate`
Devuelve el `eval_perception.json` persistido (`200`, ya trae `mAP50`/`model`/`bench_split`) o `404` si no fue evaluado (sin correr nada). `run_id` sanitizado.
- **Reconciliación de la doble-escritura:** `run_evaluation` gana un parámetro `persist: bool = True` (default preserva el comportamiento CLI). El endpoint lo llama con `persist=False`, recibe el objeto, lo enriquece y persiste atómico él mismo. Así hay una sola escritura (atómica, enriquecida) y el `GET` siempre encuentra el `mAP50`.

### 3.5 Corrección de métrica — restringir el GT a las imágenes del run
`run_evaluation` gana `restrict_gt_to_detections: bool = False` (default preserva el CLI, que combina splits vía `nargs="+"`). Con `True` (como lo llama el servicio): tras cargar `detections`, `gt_by_image_id` e `images_by_filename`, se **filtran el GT y el person-GT al conjunto de imágenes presentes en las detecciones** (por basename) ANTES de `evaluate_class`/`evaluate_cr01`. Así un run sobre `bench_v2_test` (82 imgs) cuenta `n_gt` solo sobre esas 82 → AP/recall correctos por-run. Cambio localizado en `runner.py` (media-plane); **no** toca el script del repo de datasets.

## 4. Capa BFF (webconsole/backend)

### 4.1 RunBackend
Nuevos métodos async: `get_evaluation(run_id) -> dict` (GET; encaja en `_get_json`: 404→UnknownRun, 5xx→ServiceUnavailable) y **`evaluate(run_id) -> dict`** (POST **método propio** — ningún método existente mapea 404+409+422+5xx juntos; sigue el molde de `launch` pero agregando 404). El 409 (run en curso) se mapea a una excepción de estado **dedicada `RunNotFinished`** (sin `active_run_id`) — **no** `RunBusy` (que exige `active_run_id`, que este 409 no trae) ni `ServiceRejected` (reservada para 422).

### 4.2 Endpoints del BFF
- `POST /api/runs/{id}/evaluate` → proxya `RunBackend.evaluate`; `UnknownRun→404`, `ServiceRejected(422)→422` (campo `_service`), `409→409`, `ServiceUnavailable→502`.
- `GET /api/runs/{id}/evaluate` → proxya `get_evaluation`; `404` si no evaluado.
- `GET /api/compare?runs=id1,id2,...` (coma-separado, tope 8) → **N fetches** (solo el eval de cada run; `model`/`bench_split` ya vienen embebidos, §3.3). Arma:
```json
{
  "runs": [{"run_id":"...","label":"grounding_dino · bench_v2_test","model":"grounding_dino","bench_split":"bench_v2_test","mAP50":0.47,"cr01_detection_recall":0.64}],
  "classes": ["person","helmet","vest","bare_head"],
  "ap_by_class": {"person":[0.72,0.68],"helmet":[0.61,0.55],"vest":[0.55,0.5],"bare_head":[0.0,0.1]}
}
```
  `label` = `model · bench_split`. `ap_by_class[c]` es paralelo a `runs` (mismo orden); valores pueden ser `null`. Runs sin eval (404) se omiten → `skipped: ["run_x"]`. El set/orden de `classes` es idéntico entre runs (viene del mismo BENCH COCO).

## 5. Capa Frontend (webconsole/frontend)
- **`types.ts`:** `RunDetail`/`RunRow` ganan `bench_split?: string | null` y `evaluated?: boolean` (fluyen desde §3.1). Nuevos `EvalResult` (§3.3) y `CompareResult` (§4.2).
- **`api.ts`:** `evaluateRun(id)` (POST, molde `launchRun`), `getEvaluation(id)` (GET), `getCompare(ids)` (GET).
- **RunDetailPage** — botón **"Evaluar contra BENCH"** en el bloque de run terminado, visible solo si `run.bench_split != null`. Si `evaluated`, muestra el eval directo (GET); si no, el botón dispara el POST (estado "evaluando…"). Muestra tabla AP@0.5 por clase (con n_gt/n_det), **CR-01 recall** y **mAP@0.5** destacado. `null`→"—". Errores: 422 ("no fue sobre un split BENCH"), 502/409 con mensaje.
- **Página Compare (`/compare`)** + link en el nav: multi-select de runs con `evaluated: true` (del listado, que ya trae el flag §3.1), etiquetados por modelo+split. Con ≥2 → `getCompare` → **tabla** (filas: clases + CR-01 recall + mAP@0.5; columnas: runs; resalta el mejor por fila) **+ `GroupedBars`** (SVG propio, molde de `Sparkline`, sin librería) de AP@0.5 por clase entre runs, con leyenda. Runs omitidos → aviso.

## 6. Manejo de errores (end-to-end)
- Run no-BENCH → 422 (endpoint, sobre procedencia) → 422 BFF (`_service`) → UI "no evaluable". 
- Run en curso → 409 → UI "esperá a que termine".
- Servicio caído → 502 → UI muestra error, no rompe. 
- GT ausente en disco → 422 accionable.
- Compare con runs sin eval → omitidos con aviso; el resto se compara.

## 7. Testing
- **Servicio** (pytest, fixtures): `bench_split`/`evaluated` en `get`/`list_runs` desde una `run_provenance.json` de fixture; evaluate sobre un run "BENCH" sintético (detections + GT COCO mínimo en un datasets-root de fixture) → shape enriquecido (mAP50/model/bench_split) + persistencia atómica + `restrict_gt_to_detections` (verificar que n_gt se restringe a las imágenes del run); `422` run no-BENCH (bench_split null); `409` run activo; `404` desconocido/inválido; GET evaluado/no-evaluado.
- **BFF** (pytest, fake service extendido con knobs: run evaluable / no-BENCH-422 / no-evaluado-404): proxy evaluate/get_evaluation con mapeo; `compare` que agrega N, alinea por clase, omite sin-eval; degradación ante servicio caído.
- **Frontend** (vitest): armado de la tabla comparativa (mejor-por-fila) y `GroupedBars` (función pura de layout) con datos mockeados; flujo Evaluar con `vi.mock('../api')`; build TS strict.

## 8. Alcance y no-objetivos
- **Un spec/plan**, ~10-12 tasks (servicio: 4 — hint provenance, evaluate POST, GET, restrict_gt+mAP; BFF: 3 — RunBackend, proxy, compare; front: 4 — tipos/api, Evaluar, Compare, GroupedBars).
- **NO (YAGNI):** export CSV/JSON, eval automática al terminar, métricas nuevas (AP@[.5:.95], PR curves), tuning de IoU desde la UI (default 0.5, env override), eval de runs de video (el BENCH es de imágenes).

## 9. Verificación final
Correr GDINO-tiny e YOLOE-26s sobre `bench_v2_test` por la consola → "Evaluar" ambos → comparar en `/compare` (tabla + gráfico), confirmando AP@0.5 no-deflactados (n_gt = 82, no 196).
