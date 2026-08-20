# Cierre de la distribución de alertas (backend + frontend)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** cerrar el servicio de distribución en webconsole: orquestación del comando `eovrt-distribute`, inclusión de resultados por alerta en el reporte y visualización en detalle de experimento.

**Architecture:** el runner de `e-ovrt_experimental-setup/webconsole` toma el manifiesto paraguas, ejecuta media/control/distribution en el orden correcto para cada modo y consolida+reporta solo si todo el flujo requerido termina OK.

**Tech Stack:** Python (FastAPI/asyncio), pytest, React + TypeScript, Vitest.

## Global Constraints

- `eovrt-control` y `eovrt-media` corren como servicios externos; el runner inyecta `experiment_id` y `bus` según modo.
- `distribution` es opcional y no rompe compatibilidad con corridas históricas sin ese bloque.
- Si falla la distribución solicitada, no se debe retornar reporte consolidado como final exitoso.

## Task 1: Manifesto acepta configuración de distribución

**Files:**
- Modify: `backend/src/eovrt_webconsole/experiment/manifest.py`

**Steps:**
- [ ] Escribir prueba en backend para manifest validate: `runs.distribution` acepta `endpoint` y `idle_timeout_ms` opcionales sin romper casos existentes.
- [ ] Añadir campos opcionales al modelo `PlaneRun`.
- [ ] Mantener compatibilidad de serialización y validación existente.

## Task 2: Consolidación de artefactos distribuidos

**Files:**
- Modify: `backend/src/eovrt_webconsole/experiment/consolidation.py`

**Steps:**
- [ ] Test: cuando existe `distribution` en `media_run_dir`, copia `summary`/`notifications`/`distribution_summary` si existen.
- [ ] Modificar constante y operación de copia para agregar `distribution` como sibling de `media` y `control`.
- [ ] Ejecutar test de consolidación para validar ruta nueva y tolerancia.

## Task 3: Orquestación de distribución en runner

**Files:**
- Modify: `backend/src/eovrt_webconsole/experiment/runner.py`
- Add tests: `backend/tests/test_runner_dbe_replay.py`, `backend/tests/test_runner_live.py`, `backend/tests/test_runner_report_wiring.py`

**Steps:**
- [ ] Test TDD para _validate: modos `control` y `distribution` deben coincidir.
- [ ] Test TDD para ejecución DBE: media → control → consolidación → distribution-replay → evaluación → report.
- [ ] Test TDD para ejecución live: control primero, confirmar `subscribed`, distribuir antes del media, esperar 3 procesos, limpiar distribution en fallo.
- [ ] Definir callable `run_distribution` inyectable y default de `eovrt-distribute` con resolución de executable.
- [ ] Agregar estado `distribution_status` al `ExperimentResult`.
- [ ] Marcar `ok=False` y abortar report si distribución fue pedida y falla (timeout / exit!=0 / summary inválido).

## Task 4: Reporte por alerta de distribución

**Files:**
- Modify: `backend/src/eovrt_webconsole/experiment/report.py`
- Update: `backend/tests/test_report_generator.py`

**Steps:**
- [ ] Test TDD: `distribution/notifications.jsonl` mapea último `DeliveryRecord` por `alert_id`.
- [ ] Test TDD sin directorio `distribution` devuelve `{}`.
- [ ] Agregar función `_distribution_outcomes_by_alert` y añadir `distribucion_por_alerta` al reporte.

## Task 5: UI de notificada + card de distribución

**Files:**
- Modify: `frontend/src/types.ts`, `frontend/src/labels.ts`, `frontend/src/pages/ExperimentDetailPage.tsx`
- Update: `frontend/src/__tests__/labels.test.ts`, `frontend/src/__tests__/ExperimentDetailPage.test.tsx`

**Steps:**
- [ ] Test TDD para nuevas etiquetas (`DISTRIBUTION_OUTCOME`, causas de distribución).
- [ ] Test TDD de columna "Notificada" con outcome y estados fallback.
- [ ] Test TDD de tarjeta de distribución con datos y estado vacío.
- [ ] Ajustar tabla de alertas para mostrar outcome en línea.

## Task 6: Verificación final

**Steps:**
- [ ] `pytest -q` en backend
- [ ] `npm test` / `make test` en frontend
- [ ] `ruff check` backend
