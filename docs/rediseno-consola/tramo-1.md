# Tramo 1 — Backend y herramientas

Leé antes `01-reglas-codex.md`. Este tramo **no toca el frontend**.

Es enteramente aditivo: cuatro rutas nuevas, campos nuevos en respuestas
existentes, y parámetros de consulta nuevos con valores por defecto que
reproducen el comportamiento de hoy. Ninguna ruta existente cambia de forma.

---

## Archivos, desde `3500923`

### `webconsole/backend/src/eovrt_webconsole/`

```
clips/inventory.py
clips/trim.py
experiment/applicability.py
experiment/control_backend.py
experiment/report.py            ← se pisa con ADR-019/020, ver abajo
prompt_store.py                 ← se pisa con ADR-019/020, ver abajo
repo_catalog.py
routers/catalog.py
routers/experiments.py          ← se pisa con ADR-019/020, ver abajo
routers/prompts.py
routers/runs.py
run_backend.py
trace.py
```

### Tests nuevos

```
tests/test_artifacts_index.py
tests/test_conditions_catalog.py
tests/test_experiments_listing_fields.py
tests/test_metric_thresholds.py
tests/test_plugin_disabled_reason.py
tests/test_prompt_set_diff.py
tests/test_run_comparison.py
tests/test_run_created_at.py
tests/test_runs_listing_server_side.py
tests/test_trace_filter.py
tests/test_trace_index.py
```

### Tests modificados y herramientas

```
tests/fake_control_service.py
tests/fake_service.py
webconsole/tools/seed_dev_data.py
webconsole/.gitignore
```

---

## Los tres archivos que se pisan

`experiment/report.py`, `prompt_store.py` y `routers/experiments.py` son los
únicos que tocaron **tanto** `d042ad1` **como** los 22 commits de ADR-019/020
(distribución por HTTP).

**La versión de `3500923` ya tiene las dos cosas resueltas** — el cherry-pick las
fusionó sin conflicto y se verificó que las suites de distribución quedan verdes.
Tomala tal cual.

Lo que **sí** tenés que hacer es confirmarlo explícitamente: después de traerlos,
corré las suites de distribución y pegá la salida en el reporte.

```bash
cd webconsole/backend && ./.venv/bin/python -m pytest -q \
  tests/test_runner_distribution.py \
  tests/test_distribution_http.py \
  tests/test_report_generator.py
```

---

## El defecto que hay que arreglar acá

`tests/test_report_generator.py::test_t_alert_system_y_clasificacion_se_proyectan_desde_evaluacion_temporal`
va a fallar. Es la única regresión real del port y está diagnosticada.

**Causa:** el `report.py` nuevo agrega `passed`, `threshold` y
`threshold_direction` a cada entrada de `resultados`. El test compara el dict de
`t_alert-system` **por igualdad exacta**, así que las tres claves de más lo
rompen.

**Arreglo autorizado (decisión D-4):** actualizar ese test para que espere las
tres claves nuevas.

**Prohibido:** aflojarlo a comparación parcial, sacarle claves al `assert`,
marcarlo `xfail` o `skip`. La igualdad exacta es lo que lo hace útil sobre una
métrica que va al informe. `value` sigue siendo `2.5` — si te cambia, algo está
mal y hay que parar.

---

## Si trabajás en un worktree

`tests/test_runner_distribution.py::test_subprocess_failure_does_not_expose_child_output`
falla desde cualquier worktree, **también en la rama sin tocar**:
`resolve_distribution_executable` busca el binario en
`_repo_root().parent / e-ovrt_alert-distribution`, que desde `.worktrees/` no
existe.

No es una regresión y **no se arregla en este tramo**. Si lo ves rojo, confirmalo
corriendo el mismo test en la rama sin tocar y decilo en el reporte.

---

## Cierre

```bash
cd webconsole/backend && ./.venv/bin/python -m pytest -q
cd webconsole/frontend && npm test
```

- Backend: **668 + las 11 suites nuevas**, todos verdes (salvo lo del worktree,
  si aplica).
- Frontend: **387 + contrato**, verdes y sin tocar — este tramo no lo toca.
- `seed_dev_data.py` presente y ejecutable.

Commit: `feat(webconsole): tramo 1 — backend de front-design y seed de datos`
