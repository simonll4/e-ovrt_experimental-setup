# Avance de tramos 3–5 — NO CERRADOS

> Registro histórico del 2026-09-09, conservado como evidencia de implementación.
> Estado vigente: [cierre actualizado](02-cierre-implementacion.md) y
> [verificaciones del punch-list](punch-list-verificaciones.md). D-8 revierte el
> gateo general de preflight descrito aquí; las menciones históricas de aprobación
> de ese gateo no representan la decisión vigente.

> Registro histórico: el bloqueo y los recorridos pendientes se resolvieron en
> [el cierre completo](02-cierre-implementacion.md).

Fecha: 2026-09-09. Referencia: `3500923`. Rama: `feature/webconsole-adopcion-front-design`.

El pedido de ejecutar todos los tramos amplió la secuencia, no autorizó modificar el contrato congelado. El port y la salud del distribuidor están implementados, pero **el cierre sigue bloqueado por siete tests del contrato**. Se pidió autorización para adaptar fixtures HTTP y selectores; no hubo respuesta al momento de este reporte. No se modificó ningún archivo de contrato ni se omitió ningún test. No hubo staging, commits, merge ni push. Los cambios ajenos en defensa/README.md y results/bench_imagenes/index.md se preservaron. El worktree de referencia sigue limpio.

## Trabajo aplicado

- Tramo 3: los 30 archivos enumerados, desde la referencia; conserva el CSS de la píldora y las dos guardas de preflight ya aprobadas en ComposePage. Import de SERIES_COLORS corregido en GroupedBars.test.tsx, sin cambiar assertions. Se eliminan api.test.ts antiguo y useFullTrace.ts.
- Cierre de dependencias: ComparePage.tsx y su test adelantados desde tramo 4, porque el archivo antiguo importaba SERIES_COLORS desde el componente que la referencia ya no exporta.
- Tramo 4: los 33 archivos enumerados; píldora global restituida, alimentada por useRunsEnCurso, con nombre accesible y CSS colapsado. Su test conserva las tres comprobaciones, ahora usando el proveedor QueryClient y listRunsPaged. Se eliminan los otros cinco hooks manuales. No quedan imports a esos módulos antiguos; las funciones homónimas de api/queries son los reemplazos legítimos.
- Tramo 5 A: cliente HTTP persistente de distribución con timeout de 2 s, creado y cerrado en lifespan, y sondeo informativo en preflight. Los chequeos por manifiesto no se alteran. Tercer indicador en Shell, tipo opcional para compatibilidad y consulta compartida. Cinco tests nuevos de backend y tres de frontend.
- El test de preflight agregado por este trabajo fuera del contrato adapta únicamente interacción con Select y cadencia POLL.salud, conservando todos sus asserts: bloqueos con ready=true/false, recuperación y reaparición por polling, y cero POST al bloquear.

## Verificación: salida real

### Backend

Comando: `cd webconsole/backend && ./.venv/bin/python -m pytest -q`

```text
........................................................................ [  9%]
........................................................................ [ 18%]
........................................................................ [ 28%]
........................................................................ [ 37%]
........................................................................ [ 46%]
........................................................................ [ 56%]
........................................................................ [ 65%]
........................................................................ [ 75%]
........................................................................ [ 84%]
........................................................................ [ 93%]
..............................................                           [100%]
766 passed in 159.32s (0:02:39)
```

### Frontend

Comando: `cd webconsole/frontend && npm test`. Salida íntegra: [tramos-3-5-frontend.log](../../webconsole/tools/captures/tramos-3-5-frontend.log).

```text
 Test Files  4 failed | 59 passed (63)
      Tests  7 failed | 438 passed (445)
   Start at  12:57:37
   Duration  27.46s (transform 12.04s, setup 0ms, collect 79.41s, tests 93.88s, environment 146.21s, prepare 21.43s)
```

Fallos del contrato:

1. Corrida viva/polling: las verificaciones del cuerpo pasan, pero el teardown rechaza GET trace/index, artifacts y comparison sin fixture.
2. Detalle/traza/evaluación: falta la fixture del índice de traza, por eso el timeline no tiene cuadros; el teardown también rechaza las peticiones nuevas.
3. Derivar experimento: busca el nombre exacto del botón anterior.
4. Bloqueo de experimentos: busca el nombre del botón anterior.
5. Lanzamiento de corrida: busca checkbox helmet, reemplazado por chip button con aria-pressed.
6. Target no listo: busca botón con nombre exacto Lanzar; la referencia usa Lanzar corrida.
7. Bloqueos explícitos: mismo selector anterior de Lanzar.

Ejemplo literal de la salida:

```text
AssertionError: expected [ …(9) ] to deeply equal []
+   "GET /api/runs/contrato_run/trace/index",
+   "GET /api/runs/contrato_run/artifacts",
+   "GET /api/runs/contrato_run/comparison",
```

Esto no prueba que todos los comportamientos nuevos estén correctos: los flujos afectados deben volver a ejecutarse íntegros cuando se resuelva la discrepancia, manteniendo todas las verificaciones y la detección estricta de peticiones inesperadas.

### Compilación

Comando: `cd webconsole/frontend && npm run build`

```text
> eovrt-webconsole-frontend@0.1.0 build
> tsc && vite build

vite v5.4.21 building for production...
transforming...
✓ 162 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.40 kB │ gzip:   0.27 kB
dist/assets/index-VLiyTClE.css   35.32 kB │ gzip:   7.07 kB
dist/assets/index-08eFoFJt.js   395.88 kB │ gzip: 120.07 kB
✓ built in 2.67s
```

Ruff focal: `./.venv/bin/ruff check src/eovrt_webconsole/app.py src/eovrt_webconsole/preflight.py tests/test_preflight_distribution_health.py` → `All checks passed!`

`git diff --check` no está limpio: detecta siete líneas con espacios finales en ComposePage.tsx (362, 380, 413, 486, 539, 547, 564). Se verificó que las siete vienen literalmente de 3500923 (líneas 360, 378, 411, 484, 537, 545, 562); no se alteran por la regla de copia exacta.

## Evidencia visual y límites

- [Tramo 3 antes](../../webconsole/tools/captures/tramo-3-antes/manifest.json): 12 rutas. [Tramo 3 después](../../webconsole/tools/captures/tramo-3-despues/manifest.json): 12 rutas.
- El después de tramo 3 sirve de antes de tramo 4, con idénticos datos y viewport.
- [Tramo 4 después](../../webconsole/tools/captures/tramo-4-despues/manifest.json): 13 rutas, incluida /ruta-inexistente, sin errores de JavaScript ni títulos ausentes. Incluye ya el indicador de distribución del tramo 5.
- [Tres servicios arriba](../../webconsole/tools/captures/tramo-5-salud/tres-arriba.png), [barra colapsada](../../webconsole/tools/captures/tramo-5-salud/colapsada.png), [móvil](../../webconsole/tools/captures/tramo-5-salud/movil-abierta.png), [distribuidor caído](../../webconsole/tools/captures/tramo-5-salud/distribuidor-caido.png).
- Servicios reales aislados en 18080/18081/18082 y BFF 18090; modelo mock CPU, sin hardware, sin interceptar fetch. Los puertos 8080/8081/8082 de la UI son los rótulos previstos por el diseño. Las respuestas verificadas se guardan en tramo-5-salud/preflight-*.json.
- Verificación real de caída aislada: `Distribuidor caído; media/control operativos; ready=true y blockers=[]`. Al terminar se detuvieron únicamente los procesos temporales de esta validación; no se borraron datos ni el worktree.
- Se inspeccionaron ComposePage y ExperimentDetailPage: jerarquía nueva y tarjetas de métricas presentes; el experimento sembrado no tiene alertas ni distribución, así que muestra los vacíos explícitos. Eso NO satisface todavía la captura con outcomes poblados.
- Al reiniciar BFF se pierde el estado del manager, aunque el reporte persiste. El harness aislado recarga la respuesta real guardada en tramo3-state.json para comparar el mismo experimento; no se cambia producción. La primera captura posterior al reinicio falló por este motivo y se repitió una vez restablecido el estado.
- Una primera comprobación de distribuidor caído coincidió con la terminación del proceso media mock; el gate bloqueó correctamente por media. Se reinició el mock y se repitió aislando sólo la caída del distribuidor.

### Recorrido de los cuatro flujos: cierre pendiente

No se declara realizado el repaso manual integral de tramo 5 B. Hay navegación y capturas reales, más pruebas unitarias, pero quedan pendientes los cuatro recorridos completos con lanzamiento, parada/polling, inspección/evaluación BENCH y derivación/distribución con outcomes. Los tests de outcomes existentes y su contrato sí pasan; eso no reemplaza el recorrido manual solicitado.

## Archivos de implementación efectivamente tocados en esta continuación

Rutas relativas al repositorio. Se incluyen borrados y nuevos; se excluyen capturas y logs generados. Los archivos de contrato no aparecen porque sus hashes no cambiaron.

```text
webconsole/backend/src/eovrt_webconsole/app.py
webconsole/backend/src/eovrt_webconsole/preflight.py
webconsole/backend/tests/test_preflight_distribution_health.py
webconsole/frontend/src/App.tsx
webconsole/frontend/src/__tests__/App.test.tsx
webconsole/frontend/src/__tests__/CamerasPage.test.tsx
webconsole/frontend/src/__tests__/ClipsPage.test.tsx
webconsole/frontend/src/__tests__/ComparePage.test.tsx
webconsole/frontend/src/__tests__/ComposePage.preflight.test.tsx
webconsole/frontend/src/__tests__/ComposePage.test.tsx
webconsole/frontend/src/__tests__/DeriveExperimentForm.test.tsx
webconsole/frontend/src/__tests__/EvalSection.test.tsx
webconsole/frontend/src/__tests__/ExperimentDetailPage.test.tsx
webconsole/frontend/src/__tests__/ExperimentDetailPageRiskBanner.test.tsx
webconsole/frontend/src/__tests__/ExperimentsPage.new.test.tsx
webconsole/frontend/src/__tests__/ExperimentsPage.test.tsx
webconsole/frontend/src/__tests__/LiveRunPill.test.tsx
webconsole/frontend/src/__tests__/LiveViewer.test.tsx
webconsole/frontend/src/__tests__/PlatformPage.test.tsx
webconsole/frontend/src/__tests__/PreviewWithBoxes.test.tsx
webconsole/frontend/src/__tests__/PromptSetEditor.test.tsx
webconsole/frontend/src/__tests__/PromptSetsPage.test.tsx
webconsole/frontend/src/__tests__/RecordPanel.test.tsx
webconsole/frontend/src/__tests__/RunDetailPage.test.tsx
webconsole/frontend/src/__tests__/RunKpiStrip.test.tsx
webconsole/frontend/src/__tests__/RunsPage.test.tsx
webconsole/frontend/src/__tests__/Shell.distribution.test.tsx
webconsole/frontend/src/__tests__/Shell.test.tsx
webconsole/frontend/src/__tests__/TraceSection.test.tsx
webconsole/frontend/src/__tests__/TrimDialog.test.tsx
webconsole/frontend/src/__tests__/api.endpoints.test.ts
webconsole/frontend/src/__tests__/api.test.ts
webconsole/frontend/src/__tests__/charts/ActivityTimeline.test.tsx
webconsole/frontend/src/__tests__/charts/GroupedBars.test.tsx
webconsole/frontend/src/__tests__/spec44c_gate.test.tsx
webconsole/frontend/src/__tests__/traceview.test.ts
webconsole/frontend/src/__tests__/useServiceHealth.test.ts
webconsole/frontend/src/__tests__/useSidebarCounts.test.ts
webconsole/frontend/src/api.test.ts
webconsole/frontend/src/api/queries/platform.ts
webconsole/frontend/src/components/DeriveExperimentForm.tsx
webconsole/frontend/src/components/EvalSection.tsx
webconsole/frontend/src/components/LivePromptPanel.tsx
webconsole/frontend/src/components/LiveRunPill.tsx
webconsole/frontend/src/components/LiveViewer.tsx
webconsole/frontend/src/components/RecordPanel.tsx
webconsole/frontend/src/components/RunKpiStrip.tsx
webconsole/frontend/src/components/RunTimeline.tsx
webconsole/frontend/src/components/Shell.tsx
webconsole/frontend/src/components/TargetBadge.tsx
webconsole/frontend/src/components/TraceSection.tsx
webconsole/frontend/src/components/charts/ActivityTimeline.tsx
webconsole/frontend/src/components/charts/GroupedBars.tsx
webconsole/frontend/src/components/charts/Meter.tsx
webconsole/frontend/src/components/charts/Sparkline.tsx
webconsole/frontend/src/components/ui/Table.tsx
webconsole/frontend/src/components/ui/icons.tsx
webconsole/frontend/src/components/ui/index.ts
webconsole/frontend/src/experimentview.ts
webconsole/frontend/src/pages/CamerasPage.tsx
webconsole/frontend/src/pages/CatalogPage.tsx
webconsole/frontend/src/pages/ClipsPage.tsx
webconsole/frontend/src/pages/ComparePage.tsx
webconsole/frontend/src/pages/ComposePage.tsx
webconsole/frontend/src/pages/ExperimentDetailPage.tsx
webconsole/frontend/src/pages/ExperimentsPage.tsx
webconsole/frontend/src/pages/NotFoundPage.tsx
webconsole/frontend/src/pages/PlatformPage.tsx
webconsole/frontend/src/pages/PromptSetsPage.tsx
webconsole/frontend/src/pages/RunDetailPage.tsx
webconsole/frontend/src/pages/RunsPage.tsx
webconsole/frontend/src/styles/ui.css
webconsole/frontend/src/traceview.ts
webconsole/frontend/src/types.ts
webconsole/frontend/src/useFullTrace.ts
webconsole/frontend/src/useLiveRun.ts
webconsole/frontend/src/usePreflight.ts
webconsole/frontend/src/useServiceHealth.ts
webconsole/frontend/src/useSidebarCounts.ts
webconsole/frontend/src/useTarget.ts
```
