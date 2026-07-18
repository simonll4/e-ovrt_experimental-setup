# Spec 44 A2 — Consolidación de artefactos (ADR-014) + generador de reporte (Tabla D.6)

> **EJECUTADO el 2026-07-11.** Las 5 tareas completas (webconsole/backend **204 passed**, ruff
> limpio; revisión final **LISTO PARA MERGE**, sin Critical/Important). Resultados y deuda:
> `docs/operacion/53-experimental-setup-runner-y-reporte.md` (repo `docs`). Invariante ADR-014
> (`detections.jsonl` referenciado, nunca copiado) y aplicabilidad por fuente verificadas por
> mutación. Fix del review: `re_alerts` en fuente no-temporal → `non_temporal_source` (no `no_ground_truth`).

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cerrar el núcleo reproducible del experimental-setup (spec 44 §4): (a) **consolidación de artefactos** (ADR-014) — armar `runs/<experiment_id>/` copiando los artefactos livianos de ambos planos y **referenciando** por `run_id` los `detections.jsonl` pesados, con chequeo anti-drift de hash; y (b) el **generador de reporte** (ADR-006) — `report.json`/`report.md` que **agrega, no recalcula**, mapeando el diccionario de métricas de spec 40 §5.1 con `status`+`cause` de aplicabilidad, con la **única excepción** de recomputar el join `t_capture→alert` (spec 40 §5.2.4). El runner de A1 le pasa los run_ids.

**Architecture:** Repo `e-ovrt_experimental-setup`, package `eovrt_webconsole` (`webconsole/backend/src/`), módulos nuevos bajo `eovrt_webconsole/experiment/`. El generador es un script (no servicio, no DB): entrada `experiment_id` → dir consolidado (o los `runs/` de ambos planos); salida `report.json` (máquina) + `report.md` (humano). **No importa de los repos de los planos** (los dos repos no se importan): reimplementa el join leyendo los artefactos. La consolidación es colección, no cómputo: el `runs/` de cada plano sigue siendo la fuente de verdad (DA-03).

**Tech Stack:** Python 3.11+, Pydantic v2, pyyaml, hashlib (stdlib), pytest, ruff. NO nuevas dependencias.

## Global Constraints

- **Nunca commitear sin pedido explícito del usuario en ese turno.** Pasos "Commit" preparan; sólo se ejecutan si el usuario lo pide. Si no, `git add -A` sin `git commit`. SDD usa `git write-tree` (no es commit).
- **Nunca `Co-Authored-By`. Nada en GitHub; todo local.**
- **El runner (A1) ya está en el árbol** (`eovrt_webconsole/experiment/{manifest,control_backend,runner}.py`). A2 agrega `consolidation.py`, `applicability.py`, `report.py` y los cablea. No romper A1.
- **El reporte NO recalcula (ADR-006):** agrega lo persistido; insumo faltante ⇒ `applicable_not_computed` con causa, y el reporte sale igual. En el tramo plataforma (ADR-010), las métricas que exigen GT salen **`not_applicable / no_ground_truth`** — figuran, no se omiten.
- **Única excepción a "no recalcula": el join `t_capture→alert`** (spec 40 §5.2.4). Por cada alerta: `first_evidence_unit_id` → fila de `metrics.jsonl` del media-plane con ese `unit_id`. Aplicabilidad por `source_clock` del summary del media: `media` ⇒ `not_interpretable/dbe_media_time`; two-node sin sync ⇒ `not_interpretable/clock_skew`; resto (single-host/live) ⇒ `computed`; falta `first_evidence_unit_id` ⇒ `applicable_not_computed/missing_join_key` (no aborta). Fuente no temporal (`source_clock: none`) ⇒ `not_applicable/non_temporal_source`, pero `t_compute-budget` sigue `computed`.
- **Estados de aplicabilidad (ADR-006), enum exacto:** `computed | applicable_not_computed | not_applicable | not_interpretable`. Cada métrica lleva `status` + `cause`. Las `causes` del control-plane (`pattern_evaluation.causes`) son una **lista** — el reporte las consume verbatim.
- **Consolidación híbrida (ADR-014):** COPIA lo liviano (`effective_config`, `summary.json`, `metrics.jsonl`, `alerts.jsonl`, `pattern_events.jsonl`, `manifest.effective.yaml`); REFERENCIA `detections.jsonl` por `run_id` (`media/detections.ref.json` = `{run_id, path}`). No duplica los crudos. `runs/<experiment_id>/` va git-ignored (agregar la regla).
- **Anti-drift:** el reporte compara el hash de la config **enviada** (del manifiesto efectivo) vs la `effective_config` persistida y marca discrepancias.
- `ruff` line-length 100. Comentarios/docstrings en español, sin tildes ni ñ dentro del código.
- **Entorno/tests:** desde `webconsole/backend/`, `.venv/bin/python -m pytest -q` (asyncio_mode=auto), `.venv/bin/python -m ruff check src tests`.
- **Baseline MEDIDA (2026-07-11):** `pytest -q` → **171 passed** (A1 incluido).

---

## Task 1: Modelo de aplicabilidad + join `t_capture→alert`

**Files:**
- Create: `webconsole/backend/src/eovrt_webconsole/experiment/applicability.py`
- Test: `webconsole/backend/tests/test_applicability_join.py`

**Interfaces:**
- Produces: `MetricResult(name: str, value: float | None, unit: str | None, status: str, cause: str | None)` (Pydantic); `APPLICABILITY_STATES = ("computed","applicable_not_computed","not_applicable","not_interpretable")`; `join_capture_to_alert(alerts: list[dict], media_metrics_by_unit: dict[str, dict], *, source_clock: str, two_node: bool = False) -> list[dict]` → por alerta `{alert_id, first_evidence_unit_id, status, cause, t_capture_to_alert_ms, t_compute_budget_ms}`.

- [ ] **Step 1: Escribir el test que falla** — casos: (a) `source_clock="wallclock"` single-host + captura presente ⇒ `computed`, `t_capture_to_alert_ms = alert_registered_ms − capture_monotonic_ns/1e6`, y `t_compute_budget_ms = t_capture→alert − T_persistencia` (T_persistencia = `confirmed_at_ms − first_evidence_ms` si están, si no `t_compute_budget_ms is None`); (b) `source_clock="media"` ⇒ `not_interpretable/dbe_media_time`, valor None, **pero t_compute_budget computed** si hay monotónicos; (c) `source_clock="none"` ⇒ `not_applicable/non_temporal_source`; (d) `two_node=True` ⇒ `not_interpretable/clock_skew`; (e) falta `first_evidence_unit_id` o no está en el dict ⇒ `applicable_not_computed/missing_join_key`. Valores exactos como en el join del control-plane (`{"u1": capture_monotonic_ns}`, ns→ms `/1e6`).

- [ ] **Step 2: Correr — falla** (ImportError).

- [ ] **Step 3: Implementación.** `join_capture_to_alert` con la precedencia: `none` → `not_applicable/non_temporal_source`; `media` → `not_interpretable/dbe_media_time` (t_capture→alert None, pero t_compute_budget `computed` desde monotónicos si están); `two_node` → `not_interpretable/clock_skew`; else `wallclock` single-host: si falta la unidad o `alert_registered_ms` None ⇒ `applicable_not_computed/missing_join_key`; si no ⇒ `computed`, `t_capture_to_alert_ms = alert_registered_ms − capture_monotonic_ns/1e6`. `t_compute_budget_ms = t_capture_to_alert_ms − T_persistencia_efectiva` cuando ambos existen. (Espeja `e-ovrt_control-plane/src/eovrt_control/metrics/latency.py::join_capture_to_alert` — leerlo como referencia, pero reimplementar acá, sin importar; extender con `t_compute_budget`.)

- [ ] **Step 4-5:** correr nuevos (pasan) + suite completa (Expected: 171 + N).
- [ ] **Step 6: Commit (sólo si el usuario lo pidió).**

---

## Task 2: Consolidación de artefactos (ADR-014)

**Files:**
- Create: `webconsole/backend/src/eovrt_webconsole/experiment/consolidation.py`
- Modify: `.gitignore` (agregar `runs/`)
- Test: `webconsole/backend/tests/test_consolidation.py`

**Interfaces:**
- Produces: `consolidate_experiment(experiment_id, *, media_run_dir, control_run_dir, manifest_effective: dict, dest_root) -> Path` → arma `dest_root/<experiment_id>/` con `media/` (copia `effective_config`, `summary.json`, `metrics.jsonl`; escribe `detections.ref.json` = `{"run_id":..., "path": str(media_run_dir/'detections.jsonl')}`) y `control/` (copia `effective_config`, `summary.json`, `metrics.jsonl`, `alerts.jsonl`, `pattern_events.jsonl`), `manifest.effective.yaml`, y un `report/` vacío. Copia sólo lo liviano; NO copia `detections.jsonl`. `sha256_file(path) -> str` para el anti-drift.

- [ ] **Step 1: Escribir el test que falla** — arma dirs temporales de media/control con los artefactos livianos + un `detections.jsonl` grande; llama `consolidate_experiment`; asserta: existen `media/summary.json`, `control/alerts.jsonl`, `manifest.effective.yaml`; **NO existe** `media/detections.jsonl` (referenciado, no copiado); `media/detections.ref.json` tiene `run_id`+`path` correctos; artefactos faltantes de un plano no rompen (se omiten y se anota). Test de `sha256_file` determinista.

- [ ] **Step 2-6:** falla → impl (usar `shutil.copy2` para los livianos; `hashlib.sha256` para el hash; crear dirs con `mkdir(parents=True, exist_ok=True)`; tolerar artefactos ausentes) → pasan → suite → commit guarded. Agregar `runs/` al `.gitignore`.

---

## Task 3: Generador de reporte (`report.json` / `report.md`)

**Files:**
- Create: `webconsole/backend/src/eovrt_webconsole/experiment/report.py`
- Test: `webconsole/backend/tests/test_report_generator.py`

**Interfaces:**
- Consumes: Task 1 (`MetricResult`, `join_capture_to_alert`), Task 2 (dir consolidado).
- Produces: `generate_report(consolidated_dir) -> dict` (el `report.json`) + `render_markdown(report: dict) -> str`; `write_report(consolidated_dir) -> tuple[Path, Path]` (escribe `report/report.json` + `report/report.md`). El schema de `report.json` (spec 40 §6, mapeado a D.6): secciones `identificacion` (`experiment_id`, run ids, fecha), `modelo`, `entrada`, `parametros`, `hardware_entorno`, `temporalidad` (warm-up, `source_clock`, criterio de relojes), `eventos` (conteos de pattern/alertas + hitos §5.4), `resultados` (lista de `MetricResult` del diccionario §5.1), `anti_drift` (hash enviado vs efectivo), `observaciones`.

- [ ] **Step 1: Escribir el test que falla** — arma un dir consolidado sintético (summary de media con `source_clock: media`, summary de control, `alerts.jsonl` con `first_evidence_unit_id`/`alert_registered_ms`, `metrics.jsonl` de ambos). Llama `generate_report`. Asserta:
  - **`t_capture→alert`** figura con `status: not_interpretable, cause: dbe_media_time` (fuente video); **`t_compute-budget`** `computed` (monotónico).
  - Las métricas que exigen GT (`t_alert-system`, `TTFD`, `SDR`, y `mAP`/`AP`/`recall` si no hay eval de percepción) figuran `not_applicable / no_ground_truth` — **figuran** en `resultados`, no se omiten.
  - `re_alerts` toma el conteo del summary del control-plane si está.
  - `anti_drift` marca si el hash de la config enviada difiere de la `effective_config`.
  - Un caso `source_clock: none` (imágenes): `t_capture→alert` `not_applicable/non_temporal_source`, `t_compute-budget` `computed`, y la corrida rotulada "diagnostico espacial / smoke de contrato".
  - `render_markdown` produce un `.md` no vacío con las secciones.

- [ ] **Step 2-6:** falla → impl (agregar, no recalcular: leer los summaries/metrics/alerts; el diccionario §5.1 se enumera SIEMPRE, cada métrica con su `status`/`cause`; sólo el join se computa) → pasan → suite → commit guarded.

Métricas del diccionario a enumerar (spec 40 §5.1): `G2A` (del summary media, `computed`), `t_alert-system` (GT ⇒ `not_applicable/no_ground_truth`), `t_capture→alert` (join), `t_compute-budget` (join, `computed`), `t_alert-notification` (sin distribución ⇒ `applicable_not_computed/no_distribution` o `not_applicable`), `TTFD`/`SDR` (`not_applicable/no_ground_truth`), `TTFA interna` (del summary control si hay, `computed`; en no-temporal `not_applicable/non_temporal_source`), `ΔFP_tracker` (`not_applicable` si no hay tracker), latencias por sub-etapa/FPS/drops (`computed`), y percepción `mAP`/`AP por clase`/`recall CR-01`/`re_alerts` (`computed` si hay eval; si no, GT ⇒ `not_applicable/no_ground_truth`).

---

## Task 4: Cableado en el runner (post-run: consolidar + reportar)

**Files:**
- Modify: `webconsole/backend/src/eovrt_webconsole/experiment/runner.py`
- Test: `webconsole/backend/tests/test_runner_report_wiring.py`

**Interfaces:**
- Produces: `run_experiment` gana un paso final opcional: tras ambas corridas OK, si `manifest.report` lo pide (o siempre), invoca `consolidate_experiment` + `write_report`, y `ExperimentResult` gana `consolidated_dir: str | None` y `report_path: str | None`. La resolución de los `runs/` de cada plano se hace por convención (`<plane>/runs/<run_id>/`) con una función inyectable `resolve_run_dir` (para tests). Si una corrida falla, NO consolida ni reporta.

- [ ] **Step 1: Escribir el test que falla** — `run_experiment` en DBE-replay con `resolve_run_dir` inyectado apuntando a dirs sintéticos de artefactos; asserta que al terminar OK se creó el dir consolidado + `report/report.json`, y que `result.consolidated_dir`/`result.report_path` están set. Caso: media falla ⇒ no se consolida (`result.consolidated_dir is None`).

- [ ] **Step 2-6:** falla → impl (paso final protegido; no debe tumbar la corrida si la consolidación/reporte fallan — logea y sigue, `ExperimentResult` refleja qué se logró) → pasan → suite → commit guarded.

---

## Task 5: **Gate** — e2e consolidación + reporte + verificación por mutación

**Files:**
- Test: `webconsole/backend/tests/test_a2_gate.py`

- [ ] **Step 1: Escribir el gate** — end-to-end: artefactos sintéticos de ambos planos (un caso video `source_clock: media`, un caso imágenes `source_clock: none`) → `consolidate_experiment` → `generate_report`. Asserta el layout ADR-014 (livianos copiados, `detections.jsonl` referenciado no copiado) y los estados de aplicabilidad clave del reporte (video: `t_capture→alert` `not_interpretable/dbe_media_time`, `t_compute-budget` `computed`; imágenes: `not_applicable/non_temporal_source`; GT: `not_applicable/no_ground_truth`).

- [ ] **Step 2: Correr el gate** — Expected: PASS.

- [ ] **Step 3: Verificar que el gate es significativo (mutación) — obligatorio.** Dos mutaciones, una por vez, salida literal:
  1. En `consolidation.py`, copiar también `detections.jsonl` (en vez de referenciarlo). Esperado: **falla** la aserción de ADR-014 (el crudo NO debe copiarse). Revertí.
  2. En el reporte/join, para `source_clock: media` devolver `computed` en vez de `not_interpretable/dbe_media_time`. Esperado: **falla** la aserción de aplicabilidad. Revertí.
  Si alguna no hace fallar el gate, es vacuo: arreglalo.

- [ ] **Step 4: Suite completa + lint** — Expected: verde total; `All checks passed!`.
- [ ] **Step 5: Commit (sólo si el usuario lo pidió).**

---

## Cierre

- [ ] **Registrar la deuda:** el "sellado" opt-in (ADR-014 §4, materializar los crudos) queda para cuando haga falta archivado permanente (campañas R1–R4). El generador `report.md` legible puede enriquecerse; los números REALES de percepción/temporales llegan con el GT (spec 43, diferido). El `GET /api/config` shape (deuda de A1) se alinea si el reporte lee config del control-plane vivo.
- [ ] **Escribir el doc de resultados** en `docs/operacion/` del repo `docs` (siguiente número de la serie 50-) cubriendo A1+A2 (el runner + consolidación + reporte = el núcleo reproducible del experimental-setup). Banner EJECUTADO en A1 y A2.
- [ ] **Verificación final:** pegar `pytest -q` (verde), `ruff check` (limpio), la salida de las dos mutaciones del gate.

## Alineación con spec 44 §4 (self-review)

| Requisito §4 | Task |
|---|---|
| Consolidación ADR-014: copiar livianos, referenciar `detections.jsonl` por run_id | 2 |
| `manifest.effective.yaml` + anti-drift hash | 2, 3 |
| Reporte agrega, no recalcula; `report.json` mapeado a D.6 + diccionario §5.1 con estados | 3 |
| Única excepción: join `t_capture→alert` + `t_compute-budget` | 1, 3 |
| GT en tramo plataforma ⇒ `not_applicable/no_ground_truth` (figuran) | 3 |
| §4.1 fuente no temporal ⇒ `non_temporal_source`, `t_compute-budget` computed | 1, 3 |
| Runner invoca consolidación + reporte | 4 |
| Gate + mutación | 5 |
