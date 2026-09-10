# Tramo 2 — validado, sin commit

> Registro histórico del 2026-09-09, conservado como evidencia de implementación.
> Estado vigente: [cierre actualizado](02-cierre-implementacion.md) y
> [verificaciones del punch-list](punch-list-verificaciones.md). D-8 revierte el
> gateo general de preflight descrito aquí; las menciones históricas de aprobación
> de ese gateo no representan la decisión vigente.

Fecha: 2026-09-09. Rama: `feature/webconsole-adopcion-front-design`.
Referencia: `3500923`, worktree conservado y limpio.

## Resultado y bloqueos

La capa TanStack Query está incorporada. De los 20 archivos indicados, 19 son idénticos byte por byte a la referencia; types.ts tiene únicamente el cambio de RunSummary de interface a type aprobado en la continuación. Se conservaron componentes, los seis hooks, CSS y todos los tests previos, incluido el contrato congelado. La única pantalla modificada es ComposePage: dos líneas para aplicar los bloqueos del preflight, excepción aprobada en la última continuación. El contrato conserva los mismos SHA-256.

Las dos correcciones aprobadas están aplicadas. Resultado final repetido: 403 tests frontend, 761 backend y build verdes. Se completó además la validación con seed_dev_data.py, detector mock y BFF/control reales en un entorno de rutas aisladas: 12 capturas antes/después sin cambios visuales apreciables y traza de 60 cuadros inferidos/recibidos por control sin errores. Tramo 2 validado; no se avanzó al tramo 3 ni hubo staging, commit, merge o push. Las salidas rojas históricas se conservan como registro de diagnóstico y del test de espera intermitente. Ver [validación integrada y capturas](../../webconsole/tools/captures/seeded-tramo2.iHTMAx/VALIDACION.md).

### Compilación y excepción aplicada en la continuación

RunDetailPage todavía usa helpers que esperan `Record<string, unknown>`. El RunSummary de referencia es una interfaz sin firma de índice; causa diez errores. Copiar la pantalla nueva adelantaría el tramo 3 y violaría el límite de este tramo.

El usuario respondió «continue» a la solicitud de esta excepción puntual y se aplicó únicamente:

```diff
-export interface RunSummary {
+export type RunSummary = {
```

Conserva todas las propiedades declaradas, sin `any`, casts ni supresiones. Una comprobación con el compilador TypeScript y sustitución exclusivamente en memoria produjo:

```text
Propuesta comprobada en memoria, sin editar archivos: 0 errores TypeScript
```

La comprobación en memoria fue preliminar. En la continuación se aplicó el alias en disco y `npm run build` terminó con exit 0. La salida nueva consta en la actualización al final de este reporte; las salidas anteriores se conservan como historial.

### Contrato de preflight resuelto

`nueva-corrida.contrato.test.tsx:86` exige que un preflight con bloqueos deshabilite Lanzar. Ya pasa: ComposePage incorpora los motivos al aviso existente y protege también el handler de envío. No se editó el contrato. Se agregaron dos pruebas independientes de recuperación por polling y reaparición del bloqueo.

## Archivos efectivamente tocados en este tramo

20 archivos traídos de referencia; types.ts tiene la excepción de declaración documentada:

- `webconsole/frontend/src/palette.ts`
- `webconsole/frontend/src/types.ts`
- `webconsole/frontend/src/runview.ts`
- `webconsole/frontend/src/test-utils.tsx`
- `webconsole/frontend/src/main.tsx`
- `webconsole/frontend/src/api/endpoints.ts`
- `webconsole/frontend/src/api/index.ts`
- `webconsole/frontend/src/api/keys.ts`
- `webconsole/frontend/src/api/queryClient.ts`
- `webconsole/frontend/src/api/queries/cameras.ts`
- `webconsole/frontend/src/api/queries/catalog.ts`
- `webconsole/frontend/src/api/queries/clips.ts`
- `webconsole/frontend/src/api/queries/experiments.ts`
- `webconsole/frontend/src/api/queries/platform.ts`
- `webconsole/frontend/src/api/queries/promptSets.ts`
- `webconsole/frontend/src/api/queries/runs.ts`
- `webconsole/frontend/src/api/queries/sidebar.ts`
- `webconsole/frontend/src/__tests__/queryClient.test.ts`
- `webconsole/frontend/package.json`
- `webconsole/frontend/package-lock.json`

Además:

- `webconsole/frontend/src/pages/ComposePage.tsx`: dos líneas de la excepción de preflight autorizada.
- `webconsole/frontend/src/__tests__/ComposePage.preflight.test.tsx`: dos pruebas nuevas; mocks en fetch, no en el módulo API.
- `webconsole/frontend/src/api.ts`: eliminado para que los imports `../api` resuelvan al nuevo `api/index.ts`, como en la referencia. El archivo anterior ocultaba el módulo nuevo y duplicaba ApiError, causando dos fallos de política de reintentos. Recuperable desde Git; los tests previos de API se conservaron.
- `webconsole/frontend/vite.config.ts`: puerto 5173 conservado y `strictPort: true`, desviación D-7 autorizada.
- `webconsole/tools/capture_console.mjs`: herramienta nueva para recorrer las rutas de App.tsx.
- `webconsole/tools/capture_fixtures.mjs`: respuestas HTTP sintéticas deterministas para capturas.
- `webconsole/.gitignore`: ignora `tools/.capture-runtime/` y `tools/captures/`.

La eliminación de api.ts completa la migración al módulo de referencia, pero no estaba enumerada en el tramo: se registra como ajuste adicional de resolución de dependencias. No se importaron pantallas extra.

`npm ci --no-audit --no-fund` instaló las versiones del lockfile de referencia. No se editaron otros archivos de producción, backend ni repos hermanos en este tramo. Se preservaron los cambios previos de `defensa/README.md`, `results/bench_imagenes/index.md`, documentación y tramos 0/1.

## Verificación inicial: salida real histórica, antes de aprobar el alias

### Frontend

Comando: `cd webconsole/frontend && npm test`. Exit 1. Salida de la ejecución anterior a la aprobación (advertencias incluidas):

```text
stderr | src/__tests__/ExperimentDetailPageRiskBanner.test.tsx > ExperimentDetailPage — banner de riesgo activo > muestra el banner con el condition_id cuando patterns no esta vacio y el experimento corre
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ExperimentsPage.test.tsx > ExperimentsPage > lista manifiestos y dispara un experimento con preflight verde
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ExperimentDetailPage.test.tsx > ExperimentDetailPage > muestra las alertas y avisa que el conjunto no es temporal
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ComposePage.test.tsx > ComposePage prefill > conserva active_ids del manifiesto y no lo pisan los defaults del set
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/TrimDialog.test.tsx (9 tests) 768ms
stderr | src/__tests__/RunsPage.test.tsx > RunsPage > lista corridas y marca la que está en curso
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ExperimentsPage.new.test.tsx > ExperimentsPage - crear nuevo experimento (/experiments/new) > abre el formulario con un selector "basado en" precargado con el primer manifiesto
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/ExperimentDetailPageRiskBanner.test.tsx (7 tests) 713ms
stderr | src/__tests__/RunDetailPage.test.tsx > RunDetailPage > muestra el estado de la corrida con el glosario, no con el código crudo
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/contrato/experimentos-distribucion.contrato.test.tsx > Contrato: experimentos y distribución > lista y abre un experimento con outcomes vinculados a cada alerta
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ComposePage.test.tsx > ComposePage prefill de source.type video > conserva el source.type original en la composición (round-trip sin colapso a video_file)
No routes matched location "/runs/r1"

stderr | src/__tests__/contrato/nueva-corrida.contrato.test.tsx > Contrato: nueva corrida > consulta preflight, compone fuente y prompts, lanza y abre el detalle real
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/ExperimentsPage.test.tsx (5 tests) 1741ms
   ✓ ExperimentsPage > lista manifiestos y dispara un experimento con preflight verde 727ms
   ✓ ExperimentsPage > espera la recarga de manifiestos antes de seleccionar el slug derivado 359ms
 ✓ src/__tests__/ExperimentDetailPage.test.tsx (15 tests) 2075ms
   ✓ ExperimentDetailPage > muestra las alertas y avisa que el conjunto no es temporal 412ms
stderr | src/__tests__/ComposePage.test.tsx > ComposePage nombre opcional del run > manda run.name cuando se completa, null cuando se deja vacío
No routes matched location "/runs/r1"

stderr | src/__tests__/ComposePage.test.tsx > ComposePage nombre opcional del run > deja run.name en null si el campo queda vacío (usa el id autogenerado)
No routes matched location "/runs/r2"

 ✓ src/__tests__/DeriveExperimentForm.test.tsx (13 tests) 2612ms
   ✓ DeriveExperimentForm > precarga los valores del manifiesto fuente 502ms
   ✓ DeriveExperimentForm > mode "derive" (default): título "Derivar de <source>" y botón "Derivar" 435ms
 ✓ src/__tests__/ExperimentsPage.new.test.tsx (4 tests) 2863ms
   ✓ ExperimentsPage - crear nuevo experimento (/experiments/new) > abre el formulario con un selector "basado en" precargado con el primer manifiesto 1082ms
   ✓ ExperimentsPage - crear nuevo experimento (/experiments/new) > al cambiar la fuente en el selector, vuelve a pedir los defaults y reprecarga los campos (bug central) 792ms
   ✓ ExperimentsPage - crear nuevo experimento (/experiments/new) > en modo nuevo la card dice "Nuevo experimento" y el botón "Crear" (no "Derivar de...") 564ms
   ✓ ExperimentsPage - crear nuevo experimento (/experiments/new) > el "Derivar" de una fila NO muestra el selector "basado en" (fuente fija, igual que antes) 420ms
 ✓ src/__tests__/RunDetailPage.test.tsx (10 tests) 2604ms
   ✓ RunDetailPage > muestra el estado de la corrida con el glosario, no con el código crudo 410ms
   ✓ RunDetailPage > las pestañas separan traza, resumen, evaluación y archivos 661ms
   ✓ RunDetailPage > borrado parcial muestra el detalle de los planos que fallaron y persiste (no navega) 363ms
 ✓ src/__tests__/ComparePage.test.tsx (14 tests) 3369ms
   ✓ ComparePage > lista las corridas por nombre, no por identificador crudo 698ms
   ✓ ComparePage > compara al elegir dos y nombra las métricas en español 632ms
   ✓ ComparePage > resalta el mejor valor de cada fila 413ms
   ✓ ComparePage > no avisa cuando comparten conjunto de evaluación 320ms
   ✓ ComparePage > informa las corridas que quedaron afuera en vez de omitirlas en silencio 472ms
 ✓ src/__tests__/contrato/experimentos-distribucion.contrato.test.tsx (4 tests) 3322ms
   ✓ Contrato: experimentos y distribución > lista y abre un experimento con outcomes vinculados a cada alerta 1671ms
   ✓ Contrato: experimentos y distribución > deriva un manifiesto con overrides y lanza la derivación seleccionada 1096ms
   ✓ Contrato: experimentos y distribución > seleccionar dos corridas evaluadas pide su comparación por HTTP 362ms
 ✓ src/__tests__/TraceSection.test.tsx (10 tests) 3538ms
   ✓ TraceSection > no vuelca todos los cuadros: la lista se acota y dice el total 1911ms
   ✓ TraceSection > el banner de alerta nombra la condición, no solo el código 321ms
 ✓ src/__tests__/RecordPanel.test.tsx (13 tests) 3979ms
   ✓ RecordPanel > mientras graba, consulta el backend periodicamente y muestra elapsed_ms/size_bytes de ahi 1121ms
   ✓ RecordPanel > si el backend informa error, deja de contar y muestra el motivo 1144ms
stderr | src/__tests__/ComposePage.test.tsx > ComposePage fuente RTSP > al elegir rtsp muestra el campo URL y arma config { url }
No routes matched location "/runs/r1"

stderr | src/__tests__/Shell.test.tsx > Shell > renderiza los tres títulos de grupo
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ComposePage.test.tsx > ComposePage cámara guardada (oak_d) > lanza con la config del preset de cámara elegido
No routes matched location "/runs/r1"

 ✓ src/__tests__/ComposePage.test.tsx (12 tests) 3764ms
   ✓ ComposePage prefill > conserva active_ids del manifiesto y no lo pisan los defaults del set 679ms
   ✓ ComposePage prefill de source.type video > conserva el source.type original en la composición (round-trip sin colapso a video_file) 562ms
   ✓ ComposePage nombre opcional del run > manda run.name cuando se completa, null cuando se deja vacío 504ms
   ✓ ComposePage aviso de 409 al lanzar > muestra aviso de run activo ante 409 con active_run_id 327ms
 ✓ src/__tests__/Shell.test.tsx (17 tests) 4008ms
   ✓ Shell > renderiza los tres títulos de grupo 509ms
   ✓ Shell > acorta la etiqueta que no entra, sin perder el nombre completo 497ms
   ✓ Shell > elegir un destino de la nav cierra la barra lateral 314ms
 ❯ src/__tests__/contrato/nueva-corrida.contrato.test.tsx (3 tests | 1 failed) 3965ms
   ✓ Contrato: nueva corrida > consulta preflight, compone fuente y prompts, lanza y abre el detalle real 2574ms
   ✓ Contrato: nueva corrida > impide lanzar con el formulario completo si el target aún no está listo 764ms
   × Contrato: nueva corrida > impide lanzar y muestra el motivo cuando el preflight informa bloqueos 624ms
     → expected <button></button> to have property "disabled" with value true
 ✓ src/__tests__/api.test.ts (12 tests) 83ms
 ✓ src/__tests__/RunsPage.test.tsx (16 tests) 5018ms
   ✓ RunsPage > lista corridas y marca la que está en curso 766ms
   ✓ RunsPage > pagina el listado en vez de volcar todas las filas 1578ms
   ✓ RunsPage > cancelar la confirmación no borra nada 393ms
   ✓ RunsPage > confirmar borra la corrida y refresca la lista 304ms
 ✓ src/__tests__/labels.test.ts (13 tests) 35ms
stderr | src/__tests__/CamerasPage.test.tsx > CamerasPage > lista los presets de cámara
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/traceview.test.ts (12 tests) 44ms
 ✓ src/__tests__/runview.test.ts (17 tests) 64ms
 ✓ src/__tests__/experimentview.test.ts (15 tests) 28ms
stderr | src/__tests__/spec44c_gate.test.tsx > spec44c gate: flujo de experimentos por la UI > ExperimentsPage: lista un manifiesto y dispara runExperiment al hacer click en "Ejecutar experimento"
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/runseries.test.ts (12 tests) 45ms
 ✓ src/__tests__/PromptSetEditor.test.tsx (5 tests) 1474ms
   ✓ PromptSetEditor > exploratory: permite editar y guardar via updatePromptSet 491ms
   ✓ PromptSetEditor > freeze flow: pedir congelamiento y confirmar 366ms
 ✓ src/__tests__/PreviewWithBoxes.test.tsx (8 tests) 420ms
 ✓ src/__tests__/useServiceHealth.test.ts (5 tests) 403ms
 ✓ src/__tests__/LiveViewer.test.tsx (4 tests) 362ms
 ✓ src/__tests__/spec44c_gate.test.tsx (3 tests) 1120ms
   ✓ spec44c gate: flujo de experimentos por la UI > ExperimentsPage: lista un manifiesto y dispara runExperiment al hacer click en "Ejecutar experimento" 831ms
 ✓ src/__tests__/CamerasPage.test.tsx (7 tests) 2559ms
   ✓ CamerasPage > lista los presets de cámara 440ms
   ✓ CamerasPage > muestra banner y deshabilita conectar ante 409 run_active 611ms
   ✓ CamerasPage > muestra banner ante 409 preview_active (sesión de preview ya activa) 510ms
   ✓ CamerasPage > activa por defecto las clases sin enabled_by_default declarado en el YAML 562ms
 ✓ src/__tests__/RunKpiStrip.test.tsx (7 tests) 750ms
   ✓ RunKpiStrip > rotula con el glosario, nunca con la clave cruda del sumario 310ms
 ✓ src/__tests__/charts/timeline.test.ts (9 tests) 86ms
 ✓ src/__tests__/charts/GroupedBars.test.tsx (8 tests) 531ms
   ✓ GroupedBars — render > etiqueta cada barra con su valor: no hace falta leer contra el eje 307ms
 ✓ src/__tests__/ClipsPage.test.tsx (5 tests) 866ms
   ✓ ClipsPage > lista masters y clips 385ms
 ✓ src/__tests__/ui/Table.test.tsx (6 tests) 853ms
   ✓ SortableHeader > muestra la flecha solo en la columna activa, en la direccion correcta 426ms
 ✓ src/__tests__/charts/layout.test.ts (9 tests) 43ms
 ✓ src/__tests__/nav.test.ts (10 tests) 28ms
 ✓ src/__tests__/EvalSection.test.tsx (4 tests) 370ms
 ✓ src/__tests__/PlatformPage.test.tsx (3 tests) 416ms
 ✓ src/__tests__/ui/primitives.test.tsx (10 tests) 396ms
stderr | src/__tests__/contrato/detalle-traza-evaluacion.contrato.test.tsx > Contrato: detalle, traza y evaluación > lee detalle y traza, permite inspeccionar cuadros y evaluar contra BENCH
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/api.test.ts (4 tests) 48ms
 ✓ src/__tests__/ui/Select.test.tsx (5 tests) 673ms
   ✓ Select > abre la lista al hacer click en el control 322ms
 ✓ src/__tests__/queryClient.test.ts (4 tests) 18ms
 ✓ src/__tests__/experiment-api.test.ts (4 tests) 24ms
 ✓ src/__tests__/charts/Meter.test.tsx (5 tests) 451ms
stderr | src/__tests__/contrato/corrida-viva.contrato.test.tsx > Contrato: corrida viva > permite alcanzar la corrida activa desde una ruta distinta del listado
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/contrato/detalle-traza-evaluacion.contrato.test.tsx (1 test) 1470ms
   ✓ Contrato: detalle, traza y evaluación > lee detalle y traza, permite inspeccionar cuadros y evaluar contra BENCH 1467ms
 ✓ src/__tests__/PromptSetsPage.test.tsx (2 tests) 702ms
   ✓ PromptSetsPage > un set frozen se muestra read-only con acción Derivar 423ms
 ✓ src/__tests__/contrato/corrida-viva.contrato.test.tsx (2 tests) 1340ms
   ✓ Contrato: corrida viva > permite alcanzar la corrida activa desde una ruta distinta del listado 935ms
   ✓ Contrato: corrida viva > consulta mientras corre, permite detener y cesa el polling del detalle al terminar 402ms
 ✓ src/__tests__/useSidebarCounts.test.ts (2 tests) 179ms
 ✓ src/__tests__/stream.test.ts (3 tests) 36ms
 ✓ src/__tests__/preview.test.ts (2 tests) 42ms
stderr | src/__tests__/LiveRunPill.test.tsx > LiveRunPill > no renderiza nada si no hay corrida viva
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/LiveRunPill.test.tsx (3 tests) 418ms
 ✓ src/__tests__/ui/Button.test.tsx (5 tests) 465ms
 ✓ src/__tests__/ui/Badge.test.tsx (4 tests) 142ms
 ✓ src/__tests__/ui/Banner.test.tsx (3 tests) 429ms
   ✓ Banner > tono warn con boton de cerrar 348ms
 ✓ src/__tests__/ui/ConditionName.test.tsx (3 tests) 101ms
 ✓ src/__tests__/promptview.test.ts (3 tests) 7ms
stderr | src/__tests__/App.test.tsx > App > renderiza el título de la consola
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/App.test.tsx (2 tests) 457ms
   ✓ App > renderiza el título de la consola 308ms
 ✓ src/__tests__/ui/InlineDeleteConfirm.test.tsx (2 tests) 363ms
   ✓ InlineDeleteConfirm > "Si, borrar" dispara onConfirm; "No" dispara onCancel 318ms
 ✓ src/__tests__/ui/SegmentedControl.test.tsx (2 tests) 342ms
 ✓ src/__tests__/ui/PageHeader.test.tsx (2 tests) 329ms
 ✓ src/__tests__/ui/icons.test.tsx (1 test) 89ms
 ✓ src/__tests__/ui/SearchInput.test.tsx (1 test) 117ms

⎯⎯⎯⎯⎯⎯⎯ Failed Tests 1 ⎯⎯⎯⎯⎯⎯⎯

 FAIL  src/__tests__/contrato/nueva-corrida.contrato.test.tsx > Contrato: nueva corrida > impide lanzar y muestra el motivo cuando el preflight informa bloqueos
AssertionError: expected <button></button> to have property "disabled" with value true

- Expected
+ Received

- true
+ false

 ❯ src/__tests__/contrato/nueva-corrida.contrato.test.tsx:86:20
     84|     expect(http.a('GET', '/api/preflight').length).toBeGreaterThan(0)
     85|     const lanzar = screen.getByRole('button', { name: /^Lanzar$/i })
     86|     expect(lanzar).toHaveProperty('disabled', true)
       |                    ^
     87|     expect(screen.getByText(/Bloqueo de contrato/)).toBeTruthy()
     88|     fireEvent.click(lanzar)

⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯[1/1]⎯

 Test Files  1 failed | 59 passed (60)
      Tests  1 failed | 400 passed (401)
   Start at  03:29:40
   Duration  23.62s (transform 9.80s, setup 0ms, collect 62.01s, tests 63.56s, environment 141.96s, prepare 22.37s)


```

### Build

Comando: `cd webconsole/frontend && npm run build`. Exit 2:

```text

> eovrt-webconsole-frontend@0.1.0 build
> tsc && vite build

src/pages/RunDetailPage.tsx(121,24): error TS2345: Argument of type 'RunSummary | undefined' is not assignable to parameter of type 'Record<string, unknown> | undefined'.
  Type 'RunSummary' is not assignable to type 'Record<string, unknown>'.
    Index signature for type 'string' is missing in type 'RunSummary'.
src/pages/RunDetailPage.tsx(141,36): error TS2345: Argument of type 'RunSummary | undefined' is not assignable to parameter of type 'Record<string, unknown> | undefined'.
  Type 'RunSummary' is not assignable to type 'Record<string, unknown>'.
    Index signature for type 'string' is missing in type 'RunSummary'.
src/pages/RunDetailPage.tsx(175,9): error TS2322: Type 'RunSummary | undefined' is not assignable to type 'Record<string, unknown> | undefined'.
  Type 'RunSummary' is not assignable to type 'Record<string, unknown>'.
    Index signature for type 'string' is missing in type 'RunSummary'.
src/pages/RunDetailPage.tsx(232,26): error TS2345: Argument of type 'RunSummary | undefined' is not assignable to parameter of type 'Record<string, unknown> | undefined'.
  Type 'RunSummary' is not assignable to type 'Record<string, unknown>'.
    Index signature for type 'string' is missing in type 'RunSummary'.
src/pages/RunDetailPage.tsx(232,63): error TS2345: Argument of type 'RunSummary | undefined' is not assignable to parameter of type 'Record<string, unknown> | undefined'.
  Type 'RunSummary' is not assignable to type 'Record<string, unknown>'.
    Index signature for type 'string' is missing in type 'RunSummary'.
src/pages/RunDetailPage.tsx(237,48): error TS2345: Argument of type 'RunSummary | undefined' is not assignable to parameter of type 'Record<string, unknown> | undefined'.
  Type 'RunSummary' is not assignable to type 'Record<string, unknown>'.
    Index signature for type 'string' is missing in type 'RunSummary'.
src/pages/RunDetailPage.tsx(241,48): error TS2345: Argument of type 'RunSummary | undefined' is not assignable to parameter of type 'Record<string, unknown> | undefined'.
  Type 'RunSummary' is not assignable to type 'Record<string, unknown>'.
    Index signature for type 'string' is missing in type 'RunSummary'.
src/pages/RunDetailPage.tsx(245,52): error TS2345: Argument of type 'RunSummary | undefined' is not assignable to parameter of type 'Record<string, unknown> | undefined'.
  Type 'RunSummary' is not assignable to type 'Record<string, unknown>'.
    Index signature for type 'string' is missing in type 'RunSummary'.
src/pages/RunDetailPage.tsx(250,34): error TS2345: Argument of type 'RunSummary | undefined' is not assignable to parameter of type 'Record<string, unknown> | undefined'.
  Type 'RunSummary' is not assignable to type 'Record<string, unknown>'.
    Index signature for type 'string' is missing in type 'RunSummary'.
src/pages/RunDetailPage.tsx(252,38): error TS2345: Argument of type 'RunSummary | undefined' is not assignable to parameter of type 'Record<string, unknown> | undefined'.
  Type 'RunSummary' is not assignable to type 'Record<string, unknown>'.
    Index signature for type 'string' is missing in type 'RunSummary'.

```

### Backend

Comando: `cd webconsole/backend && ./.venv/bin/python -m pytest -q`. Exit 0. Línea final real de la ejecución de este tramo:

```text
761 passed in 139.29s (0:02:19)
```

No reprodujo esta vez el CancelledError intermitente de WebSocket visto antes. No se modificó backend para obtener este resultado.

### Integridad y herramienta

Comandos con exit 0 y sin salida:

```bash
node --check webconsole/tools/capture_console.mjs
node --check webconsole/tools/capture_fixtures.mjs
git diff --check
git -C .worktrees/front-design status --short
```

Verificación contra git show 3500923:

```json
{"files":20,"mismatches":[]}
```

## Capturas antes y después

12 rutas, viewport 1440×1000, misma hora fija UTC y mismas respuestas HTTP sintéticas. Chromium 149.0.7827.55. Cero errores de página/fixtures en ambas tandas. Nueve PNG idénticos; tres sólo presentan diferencias de rasterización de amplitud máxima 1/255 por canal:

| Ruta | Píxeles distintos |
| --- | ---: |
| / | 32 |
| /catalog | 2 |
| /compare | 7 |
| Las otras 9 | 0 |

No se observan cambios de contenido ni distribución visual. Los manifiestos conservan SHA-256 por imagen: [antes](../../webconsole/tools/captures/tramo-2-antes/manifest.json), [después](../../webconsole/tools/captures/tramo-2-despues/manifest.json).

**Limitación:** las capturas usan fixtures HTTP, NO una ejecución de seed_dev_data.py ni integración real con el BFF. Son evidencia de conservación visual, no del circuito productor → artefacto → BFF. El sembrado real queda pendiente; la herramienta acepta también `--base-url`, `--run-id` y `--experiment-id` para ese modo. Cámaras y clips están vacíos; plataforma representa una instancia fija, no hardware conectado.

Comando usado (desde la raíz del componente; cambiar destino para cada tanda):

```bash
node webconsole/tools/capture_console.mjs --synthetic \
  --out tools/captures/tramo-2-despues \
  --playwright-module /home/simonll4/.cache/ms-playwright-go/1.57.0/package/index.mjs \
  --chromium /home/simonll4/.cache/ms-playwright/chromium-1228/chrome-linux64/chrome
```

La herramienta documenta instalación alternativa local y gitignorada. No agrega Playwright al package.json del frontend.

### 00-corridas

Antes:

![Antes 00-corridas](../../webconsole/tools/captures/tramo-2-antes/00-corridas.png)

Después:

![Después 00-corridas](../../webconsole/tools/captures/tramo-2-despues/00-corridas.png)

### 01-compose

Antes:

![Antes 01-compose](../../webconsole/tools/captures/tramo-2-antes/01-compose.png)

Después:

![Después 01-compose](../../webconsole/tools/captures/tramo-2-despues/01-compose.png)

### 02-catalog

Antes:

![Antes 02-catalog](../../webconsole/tools/captures/tramo-2-antes/02-catalog.png)

Después:

![Después 02-catalog](../../webconsole/tools/captures/tramo-2-despues/02-catalog.png)

### 03-compare

Antes:

![Antes 03-compare](../../webconsole/tools/captures/tramo-2-antes/03-compare.png)

Después:

![Después 03-compare](../../webconsole/tools/captures/tramo-2-despues/03-compare.png)

### 04-runs--id

Antes:

![Antes 04-runs--id](../../webconsole/tools/captures/tramo-2-antes/04-runs--id.png)

Después:

![Después 04-runs--id](../../webconsole/tools/captures/tramo-2-despues/04-runs--id.png)

### 05-platform

Antes:

![Antes 05-platform](../../webconsole/tools/captures/tramo-2-antes/05-platform.png)

Después:

![Después 05-platform](../../webconsole/tools/captures/tramo-2-despues/05-platform.png)

### 06-experiments

Antes:

![Antes 06-experiments](../../webconsole/tools/captures/tramo-2-antes/06-experiments.png)

Después:

![Después 06-experiments](../../webconsole/tools/captures/tramo-2-despues/06-experiments.png)

### 07-experiments-new

Antes:

![Antes 07-experiments-new](../../webconsole/tools/captures/tramo-2-antes/07-experiments-new.png)

Después:

![Después 07-experiments-new](../../webconsole/tools/captures/tramo-2-despues/07-experiments-new.png)

### 08-experiments--id

Antes:

![Antes 08-experiments--id](../../webconsole/tools/captures/tramo-2-antes/08-experiments--id.png)

Después:

![Después 08-experiments--id](../../webconsole/tools/captures/tramo-2-despues/08-experiments--id.png)

### 09-prompts

Antes:

![Antes 09-prompts](../../webconsole/tools/captures/tramo-2-antes/09-prompts.png)

Después:

![Después 09-prompts](../../webconsole/tools/captures/tramo-2-despues/09-prompts.png)

### 10-cameras

Antes:

![Antes 10-cameras](../../webconsole/tools/captures/tramo-2-antes/10-cameras.png)

Después:

![Después 10-cameras](../../webconsole/tools/captures/tramo-2-despues/10-cameras.png)

### 11-clips

Antes:

![Antes 11-clips](../../webconsole/tools/captures/tramo-2-antes/11-clips.png)

Después:

![Después 11-clips](../../webconsole/tools/captures/tramo-2-despues/11-clips.png)


## Actualización de la continuación — alias aprobado y build verde

Cambio de producción en esta continuación: una línea en `webconsole/frontend/src/types.ts:160` (interface → type). También se actualizó este reporte gitignorado. No se editaron pantallas, contratos, hooks, CSS ni backend. No se repitió backend: los 761 verdes anteriores son evidencia histórica, no una ejecución nueva. No se repitieron capturas porque la modificación sólo afecta tipos, no el JavaScript de ejecución. Sigue pendiente el sembrado real documentado arriba.

Verificación byte a byte contra referencia:

```json
{"files":20,"mismatches":["webconsole/frontend/src/types.ts"],"onlyApprovedTypeAliasChange":true}
```

### Build nuevo — exit 0

```text
> eovrt-webconsole-frontend@0.1.0 build
> tsc && vite build

vite v5.4.21 building for production...
transforming...
✓ 156 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.40 kB │ gzip:  0.27 kB
dist/assets/index-D1Xu6lb4.css   27.13 kB │ gzip:  5.78 kB
dist/assets/index-BUb2AmhY.js   313.17 kB │ gzip: 97.30 kB
✓ built in 2.96s

```

### Tests nuevos — exit 1

La primera ejecución simultánea con el build dio 399 passed / 2 failed: el contrato conocido y una espera en ExperimentsPage.new.test.tsx:57. La prueba de Nuevo experimento pasó aislada (4 passed en 3.03s) y en la repetición completa posterior, sin editar código ni tests. Se registra como fallo intermitente observado, no como una regresión confirmada.

Salida de la repetición completa:

```text
stderr | src/__tests__/ExperimentDetailPageRiskBanner.test.tsx > ExperimentDetailPage — banner de riesgo activo > muestra el banner con el condition_id cuando patterns no esta vacio y el experimento corre
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ExperimentsPage.test.tsx > ExperimentsPage > lista manifiestos y dispara un experimento con preflight verde
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ExperimentDetailPage.test.tsx > ExperimentDetailPage > muestra las alertas y avisa que el conjunto no es temporal
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ComposePage.test.tsx > ComposePage prefill > conserva active_ids del manifiesto y no lo pisan los defaults del set
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ExperimentsPage.new.test.tsx > ExperimentsPage - crear nuevo experimento (/experiments/new) > abre el formulario con un selector "basado en" precargado con el primer manifiesto
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/RunsPage.test.tsx > RunsPage > lista corridas y marca la que está en curso
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/TrimDialog.test.tsx (9 tests) 693ms
stderr | src/__tests__/RunDetailPage.test.tsx > RunDetailPage > muestra el estado de la corrida con el glosario, no con el código crudo
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/ExperimentDetailPageRiskBanner.test.tsx (7 tests) 681ms
stderr | src/__tests__/contrato/experimentos-distribucion.contrato.test.tsx > Contrato: experimentos y distribución > lista y abre un experimento con outcomes vinculados a cada alerta
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ComposePage.test.tsx > ComposePage prefill de source.type video > conserva el source.type original en la composición (round-trip sin colapso a video_file)
No routes matched location "/runs/r1"

stderr | src/__tests__/contrato/nueva-corrida.contrato.test.tsx > Contrato: nueva corrida > consulta preflight, compone fuente y prompts, lanza y abre el detalle real
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/ExperimentsPage.test.tsx (5 tests) 1155ms
   ✓ ExperimentsPage > lista manifiestos y dispara un experimento con preflight verde 524ms
stderr | src/__tests__/ComposePage.test.tsx > ComposePage nombre opcional del run > manda run.name cuando se completa, null cuando se deja vacío
No routes matched location "/runs/r1"

stderr | src/__tests__/ComposePage.test.tsx > ComposePage nombre opcional del run > deja run.name en null si el campo queda vacío (usa el id autogenerado)
No routes matched location "/runs/r2"

 ✓ src/__tests__/ExperimentDetailPage.test.tsx (15 tests) 1767ms
 ✓ src/__tests__/DeriveExperimentForm.test.tsx (13 tests) 1912ms
 ✓ src/__tests__/ExperimentsPage.new.test.tsx (4 tests) 2044ms
   ✓ ExperimentsPage - crear nuevo experimento (/experiments/new) > abre el formulario con un selector "basado en" precargado con el primer manifiesto 719ms
   ✓ ExperimentsPage - crear nuevo experimento (/experiments/new) > al cambiar la fuente en el selector, vuelve a pedir los defaults y reprecarga los campos (bug central) 564ms
   ✓ ExperimentsPage - crear nuevo experimento (/experiments/new) > en modo nuevo la card dice "Nuevo experimento" y el botón "Crear" (no "Derivar de...") 406ms
   ✓ ExperimentsPage - crear nuevo experimento (/experiments/new) > el "Derivar" de una fila NO muestra el selector "basado en" (fuente fija, igual que antes) 351ms
 ✓ src/__tests__/ComparePage.test.tsx (14 tests) 2192ms
   ✓ ComparePage > lista las corridas por nombre, no por identificador crudo 381ms
   ✓ ComparePage > compara al elegir dos y nombra las métricas en español 388ms
 ✓ src/__tests__/RunDetailPage.test.tsx (10 tests) 1962ms
   ✓ RunDetailPage > muestra el estado de la corrida con el glosario, no con el código crudo 384ms
   ✓ RunDetailPage > las pestañas separan traza, resumen, evaluación y archivos 461ms
 ✓ src/__tests__/contrato/experimentos-distribucion.contrato.test.tsx (4 tests) 2402ms
   ✓ Contrato: experimentos y distribución > lista y abre un experimento con outcomes vinculados a cada alerta 1228ms
   ✓ Contrato: experimentos y distribución > deriva un manifiesto con overrides y lanza la derivación seleccionada 751ms
   ✓ Contrato: experimentos y distribución > seleccionar dos corridas evaluadas pide su comparación por HTTP 314ms
stderr | src/__tests__/Shell.test.tsx > Shell > renderiza los tres títulos de grupo
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ComposePage.test.tsx > ComposePage fuente RTSP > al elegir rtsp muestra el campo URL y arma config { url }
No routes matched location "/runs/r1"

stderr | src/__tests__/ComposePage.test.tsx > ComposePage cámara guardada (oak_d) > lanza con la config del preset de cámara elegido
No routes matched location "/runs/r1"

 ✓ src/__tests__/ComposePage.test.tsx (12 tests) 2805ms
   ✓ ComposePage prefill > conserva active_ids del manifiesto y no lo pisan los defaults del set 464ms
   ✓ ComposePage prefill de source.type video > conserva el source.type original en la composición (round-trip sin colapso a video_file) 311ms
 ✓ src/__tests__/Shell.test.tsx (17 tests) 2857ms
   ✓ Shell > acorta la etiqueta que no entra, sin perder el nombre completo 335ms
 ✓ src/__tests__/TraceSection.test.tsx (10 tests) 3061ms
   ✓ TraceSection > no vuelca todos los cuadros: la lista se acota y dice el total 1637ms
 ❯ src/__tests__/contrato/nueva-corrida.contrato.test.tsx (3 tests | 1 failed) 2976ms
   ✓ Contrato: nueva corrida > consulta preflight, compone fuente y prompts, lanza y abre el detalle real 1753ms
   ✓ Contrato: nueva corrida > impide lanzar con el formulario completo si el target aún no está listo 610ms
   × Contrato: nueva corrida > impide lanzar y muestra el motivo cuando el preflight informa bloqueos 610ms
     → expected <button></button> to have property "disabled" with value true
 ✓ src/__tests__/RecordPanel.test.tsx (13 tests) 3638ms
   ✓ RecordPanel > mientras graba, consulta el backend periodicamente y muestra elapsed_ms/size_bytes de ahi 1132ms
   ✓ RecordPanel > si el backend informa error, deja de contar y muestra el motivo 1148ms
 ✓ src/__tests__/RunsPage.test.tsx (16 tests) 4118ms
   ✓ RunsPage > lista corridas y marca la que está en curso 535ms
   ✓ RunsPage > pagina el listado en vez de volcar todas las filas 1110ms
   ✓ RunsPage > borrado parcial muestra los planos que fallaron, y persiste tras el refresh 397ms
 ✓ src/__tests__/api.test.ts (12 tests) 65ms
 ✓ src/__tests__/labels.test.ts (13 tests) 31ms
stderr | src/__tests__/CamerasPage.test.tsx > CamerasPage > lista los presets de cámara
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/experimentview.test.ts (15 tests) 30ms
 ✓ src/__tests__/traceview.test.ts (12 tests) 29ms
 ✓ src/__tests__/runview.test.ts (17 tests) 65ms
 ✓ src/__tests__/PreviewWithBoxes.test.tsx (8 tests) 313ms
stderr | src/__tests__/spec44c_gate.test.tsx > spec44c gate: flujo de experimentos por la UI > ExperimentsPage: lista un manifiesto y dispara runExperiment al hacer click en "Ejecutar experimento"
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/runseries.test.ts (12 tests) 33ms
 ✓ src/__tests__/PromptSetEditor.test.tsx (5 tests) 1153ms
   ✓ PromptSetEditor > exploratory: permite editar y guardar via updatePromptSet 535ms
 ✓ src/__tests__/LiveViewer.test.tsx (4 tests) 200ms
 ✓ src/__tests__/useServiceHealth.test.ts (5 tests) 435ms
 ✓ src/__tests__/spec44c_gate.test.tsx (3 tests) 782ms
   ✓ spec44c gate: flujo de experimentos por la UI > ExperimentsPage: lista un manifiesto y dispara runExperiment al hacer click en "Ejecutar experimento" 554ms
 ✓ src/__tests__/CamerasPage.test.tsx (7 tests) 2004ms
   ✓ CamerasPage > muestra banner y deshabilita conectar ante 409 run_active 666ms
   ✓ CamerasPage > activa por defecto las clases sin enabled_by_default declarado en el YAML 407ms
 ✓ src/__tests__/charts/timeline.test.ts (9 tests) 58ms
 ✓ src/__tests__/RunKpiStrip.test.tsx (7 tests) 505ms
 ✓ src/__tests__/charts/GroupedBars.test.tsx (8 tests) 336ms
 ✓ src/__tests__/ClipsPage.test.tsx (5 tests) 679ms
 ✓ src/__tests__/ui/Table.test.tsx (6 tests) 447ms
 ✓ src/__tests__/charts/layout.test.ts (9 tests) 26ms
 ✓ src/__tests__/ui/primitives.test.tsx (10 tests) 547ms
 ✓ src/__tests__/PlatformPage.test.tsx (3 tests) 464ms
 ✓ src/__tests__/nav.test.ts (10 tests) 23ms
 ✓ src/__tests__/EvalSection.test.tsx (4 tests) 413ms
 ✓ src/api.test.ts (4 tests) 46ms
 ✓ src/__tests__/queryClient.test.ts (4 tests) 15ms
 ✓ src/__tests__/experiment-api.test.ts (4 tests) 30ms
stderr | src/__tests__/contrato/detalle-traza-evaluacion.contrato.test.tsx > Contrato: detalle, traza y evaluación > lee detalle y traza, permite inspeccionar cuadros y evaluar contra BENCH
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/charts/Meter.test.tsx (5 tests) 359ms
stderr | src/__tests__/contrato/corrida-viva.contrato.test.tsx > Contrato: corrida viva > permite alcanzar la corrida activa desde una ruta distinta del listado
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/ui/Select.test.tsx (5 tests) 716ms
   ✓ Select > abre la lista al hacer click en el control 363ms
 ✓ src/__tests__/PromptSetsPage.test.tsx (2 tests) 677ms
   ✓ PromptSetsPage > un set frozen se muestra read-only con acción Derivar 432ms
 ✓ src/__tests__/contrato/corrida-viva.contrato.test.tsx (2 tests) 1162ms
   ✓ Contrato: corrida viva > permite alcanzar la corrida activa desde una ruta distinta del listado 792ms
   ✓ Contrato: corrida viva > consulta mientras corre, permite detener y cesa el polling del detalle al terminar 367ms
 ✓ src/__tests__/useSidebarCounts.test.ts (2 tests) 185ms
 ✓ src/__tests__/contrato/detalle-traza-evaluacion.contrato.test.tsx (1 test) 1389ms
   ✓ Contrato: detalle, traza y evaluación > lee detalle y traza, permite inspeccionar cuadros y evaluar contra BENCH 1384ms
stderr | src/__tests__/LiveRunPill.test.tsx > LiveRunPill > no renderiza nada si no hay corrida viva
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/LiveRunPill.test.tsx (3 tests) 358ms
 ✓ src/__tests__/stream.test.ts (3 tests) 14ms
 ✓ src/__tests__/preview.test.ts (2 tests) 20ms
 ✓ src/__tests__/ui/Badge.test.tsx (4 tests) 108ms
stderr | src/__tests__/App.test.tsx > App > renderiza el título de la consola
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/ui/Banner.test.tsx (3 tests) 362ms
 ✓ src/__tests__/App.test.tsx (2 tests) 371ms
 ✓ src/__tests__/ui/Button.test.tsx (5 tests) 369ms
 ✓ src/__tests__/ui/SegmentedControl.test.tsx (2 tests) 315ms
 ✓ src/__tests__/ui/InlineDeleteConfirm.test.tsx (2 tests) 325ms
 ✓ src/__tests__/promptview.test.ts (3 tests) 5ms
 ✓ src/__tests__/ui/ConditionName.test.tsx (3 tests) 65ms
 ✓ src/__tests__/ui/SearchInput.test.tsx (1 test) 79ms
 ✓ src/__tests__/ui/PageHeader.test.tsx (2 tests) 197ms
 ✓ src/__tests__/ui/icons.test.tsx (1 test) 68ms

⎯⎯⎯⎯⎯⎯⎯ Failed Tests 1 ⎯⎯⎯⎯⎯⎯⎯

 FAIL  src/__tests__/contrato/nueva-corrida.contrato.test.tsx > Contrato: nueva corrida > impide lanzar y muestra el motivo cuando el preflight informa bloqueos
AssertionError: expected <button></button> to have property "disabled" with value true

- Expected
+ Received

- true
+ false

 ❯ src/__tests__/contrato/nueva-corrida.contrato.test.tsx:86:20
     84|     expect(http.a('GET', '/api/preflight').length).toBeGreaterThan(0)
     85|     const lanzar = screen.getByRole('button', { name: /^Lanzar$/i })
     86|     expect(lanzar).toHaveProperty('disabled', true)
       |                    ^
     87|     expect(screen.getByText(/Bloqueo de contrato/)).toBeTruthy()
     88|     fireEvent.click(lanzar)

⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯[1/1]⎯

 Test Files  1 failed | 59 passed (60)
      Tests  1 failed | 400 passed (401)
   Start at  12:17:06
   Duration  18.97s (transform 7.50s, setup 0ms, collect 47.60s, tests 50.14s, environment 114.17s, prepare 18.73s)


```

`git diff --check`: exit 0, sin salida.

### Bloqueo restante y siguiente decisión

ComposePage calcula `missingReason` con target y formulario, pero no consulta `preflight.blockers`. Por eso permite Lanzar aunque preflight informe bloqueos. La versión de referencia también omite ese enlace. Repararlo exige una segunda excepción explícita al límite del tramo 2 (no tocar pantallas), distinta del alias ya aprobado. Propuesta: incorporar los bloqueos al motivo de lanzamiento deshabilitado y mostrar su explicación, conservando el contrato intacto. No implementado sin esa decisión; tramo 2 continúa abierto.


## Actualización final — corrección de preflight aprobada y verificada

El usuario respondió «continue» a la solicitud de corregir ComposePage sin editar el contrato. Se agregaron exactamente dos líneas de producción:

```diff
 const submit = async () => {
+  if (missingReason !== null) return

 if (!target.ready) return 'el media-plane no terminó de cargar el modelo'
+if (preflight?.blockers.length) return preflight.blockers.join('; ')
```

El alcance es aplicar bloqueos explícitos. No se cambió la política de preflight nulo o fallido, ni se exigió globalmente ready cuando no hay bloqueos. El aviso usa el estilo existente; no hay CSS nuevo. La protección debe conservarse al copiar ComposePage en el tramo 3, porque la referencia no la tiene.

Archivos tocados en esta continuación: ComposePage.tsx, el nuevo ComposePage.preflight.test.tsx y este reporte ignorado. Se generaron PNG y manifiestos bajo tools/captures; dist fue regenerado por el build. Ningún archivo del contrato ni test previo fue editado. Backend sin cambios respecto a la continuación anterior.

### Pruebas nuevas: rojo antes del arreglo

```text
stderr | src/__tests__/ComposePage.preflight.test.tsx > ComposePage: bloqueos de preflight > bloquea por motivos explícitos con ready=false y se recupera por polling
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ❯ src/__tests__/ComposePage.preflight.test.tsx (2 tests | 2 failed) 473ms
   × ComposePage: bloqueos de preflight > bloquea por motivos explícitos con ready=false y se recupera por polling 371ms
     → expected <button></button> to have property "disabled" with value true
   × ComposePage: bloqueos de preflight > bloquea por motivos explícitos con ready=true y se recupera por polling 99ms
     → expected <button></button> to have property "disabled" with value true

⎯⎯⎯⎯⎯⎯⎯ Failed Tests 2 ⎯⎯⎯⎯⎯⎯⎯

 FAIL  src/__tests__/ComposePage.preflight.test.tsx > ComposePage: bloqueos de preflight > bloquea por motivos explícitos con ready=false y se recupera por polling
 FAIL  src/__tests__/ComposePage.preflight.test.tsx > ComposePage: bloqueos de preflight > bloquea por motivos explícitos con ready=true y se recupera por polling
AssertionError: expected <button></button> to have property "disabled" with value true

- Expected
+ Received

- true
+ false

 ❯ src/__tests__/ComposePage.preflight.test.tsx:21:20
     19|     })
     20|     const lanzar = screen.getByRole('button', { name: /^Lanzar$/i })
     21|     expect(lanzar).toHaveProperty('disabled', true)
       |                    ^
     22|     expect(screen.getByText(/Motor de reglas no disponible; Servicio o…
     23|     fireEvent.click(lanzar)

⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯[1/2]⎯

 Test Files  1 failed (1)
      Tests  2 failed (2)
   Start at  12:23:07
   Duration  2.89s (transform 456ms, setup 0ms, collect 751ms, tests 473ms, environment 817ms, prepare 167ms)


```

### Tests focales y contrato: exit 0 después del arreglo

Comando: `npm test -- src/__tests__/ComposePage.preflight.test.tsx src/__tests__/ComposePage.test.tsx src/__tests__/contrato`.

```text
stderr | src/__tests__/ComposePage.test.tsx > ComposePage prefill > conserva active_ids del manifiesto y no lo pisan los defaults del set
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ComposePage.preflight.test.tsx > ComposePage: bloqueos de preflight > bloquea por motivos explícitos con ready=false y se recupera por polling
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ComposePage.test.tsx > ComposePage prefill de source.type video > conserva el source.type original en la composición (round-trip sin colapso a video_file)
No routes matched location "/runs/r1"

stderr | src/__tests__/contrato/detalle-traza-evaluacion.contrato.test.tsx > Contrato: detalle, traza y evaluación > lee detalle y traza, permite inspeccionar cuadros y evaluar contra BENCH
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/contrato/experimentos-distribucion.contrato.test.tsx > Contrato: experimentos y distribución > lista y abre un experimento con outcomes vinculados a cada alerta
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/contrato/nueva-corrida.contrato.test.tsx > Contrato: nueva corrida > consulta preflight, compone fuente y prompts, lanza y abre el detalle real
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/contrato/corrida-viva.contrato.test.tsx > Contrato: corrida viva > permite alcanzar la corrida activa desde una ruta distinta del listado
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ComposePage.test.tsx > ComposePage nombre opcional del run > manda run.name cuando se completa, null cuando se deja vacío
No routes matched location "/runs/r1"

stderr | src/__tests__/ComposePage.test.tsx > ComposePage nombre opcional del run > deja run.name en null si el campo queda vacío (usa el id autogenerado)
No routes matched location "/runs/r2"

 ✓ src/__tests__/ComposePage.preflight.test.tsx (2 tests) 835ms
   ✓ ComposePage: bloqueos de preflight > bloquea por motivos explícitos con ready=false y se recupera por polling 620ms
 ✓ src/__tests__/contrato/corrida-viva.contrato.test.tsx (2 tests) 724ms
   ✓ Contrato: corrida viva > permite alcanzar la corrida activa desde una ruta distinta del listado 511ms
 ✓ src/__tests__/contrato/detalle-traza-evaluacion.contrato.test.tsx (1 test) 776ms
   ✓ Contrato: detalle, traza y evaluación > lee detalle y traza, permite inspeccionar cuadros y evaluar contra BENCH 773ms
stderr | src/__tests__/ComposePage.test.tsx > ComposePage fuente RTSP > al elegir rtsp muestra el campo URL y arma config { url }
No routes matched location "/runs/r1"

stderr | src/__tests__/ComposePage.test.tsx > ComposePage cámara guardada (oak_d) > lanza con la config del preset de cámara elegido
No routes matched location "/runs/r1"

 ✓ src/__tests__/ComposePage.test.tsx (12 tests) 1394ms
 ✓ src/__tests__/contrato/experimentos-distribucion.contrato.test.tsx (4 tests) 1269ms
   ✓ Contrato: experimentos y distribución > lista y abre un experimento con outcomes vinculados a cada alerta 647ms
   ✓ Contrato: experimentos y distribución > deriva un manifiesto con overrides y lanza la derivación seleccionada 429ms
 ✓ src/__tests__/contrato/nueva-corrida.contrato.test.tsx (3 tests) 1423ms
   ✓ Contrato: nueva corrida > consulta preflight, compone fuente y prompts, lanza y abre el detalle real 980ms

 Test Files  6 passed (6)
      Tests  24 passed (24)
   Start at  12:23:26
   Duration  4.84s (transform 2.00s, setup 0ms, collect 7.39s, tests 6.42s, environment 7.09s, prepare 1.18s)


```

### Suite completa frontend: exit 0 en la repetición

Comando: `npm test`. La primera ejecución completa, concurrente con las capturas, dio 402 passed / 1 failed en ExperimentsPage.new.test.tsx:57 (la misma espera intermitente observada en la continuación anterior). Se repitió sin capturas concurrentes, sin editar código ni tests entre ejecuciones:

```text
stderr | src/__tests__/ExperimentDetailPageRiskBanner.test.tsx > ExperimentDetailPage — banner de riesgo activo > muestra el banner con el condition_id cuando patterns no esta vacio y el experimento corre
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ExperimentsPage.test.tsx > ExperimentsPage > lista manifiestos y dispara un experimento con preflight verde
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ExperimentDetailPage.test.tsx > ExperimentDetailPage > muestra las alertas y avisa que el conjunto no es temporal
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ComposePage.test.tsx > ComposePage prefill > conserva active_ids del manifiesto y no lo pisan los defaults del set
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ExperimentsPage.new.test.tsx > ExperimentsPage - crear nuevo experimento (/experiments/new) > abre el formulario con un selector "basado en" precargado con el primer manifiesto
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/TrimDialog.test.tsx (9 tests) 870ms
stderr | src/__tests__/RunsPage.test.tsx > RunsPage > lista corridas y marca la que está en curso
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/ExperimentDetailPageRiskBanner.test.tsx (7 tests) 720ms
stderr | src/__tests__/RunDetailPage.test.tsx > RunDetailPage > muestra el estado de la corrida con el glosario, no con el código crudo
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ComposePage.test.tsx > ComposePage prefill de source.type video > conserva el source.type original en la composición (round-trip sin colapso a video_file)
No routes matched location "/runs/r1"

stderr | src/__tests__/contrato/experimentos-distribucion.contrato.test.tsx > Contrato: experimentos y distribución > lista y abre un experimento con outcomes vinculados a cada alerta
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/ExperimentsPage.test.tsx (5 tests) 1390ms
   ✓ ExperimentsPage > lista manifiestos y dispara un experimento con preflight verde 636ms
stderr | src/__tests__/contrato/nueva-corrida.contrato.test.tsx > Contrato: nueva corrida > consulta preflight, compone fuente y prompts, lanza y abre el detalle real
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ComposePage.test.tsx > ComposePage nombre opcional del run > manda run.name cuando se completa, null cuando se deja vacío
No routes matched location "/runs/r1"

stderr | src/__tests__/ComposePage.test.tsx > ComposePage nombre opcional del run > deja run.name en null si el campo queda vacío (usa el id autogenerado)
No routes matched location "/runs/r2"

 ✓ src/__tests__/ExperimentDetailPage.test.tsx (15 tests) 2586ms
   ✓ ExperimentDetailPage > muestra las alertas y avisa que el conjunto no es temporal 338ms
 ✓ src/__tests__/ExperimentsPage.new.test.tsx (4 tests) 2580ms
   ✓ ExperimentsPage - crear nuevo experimento (/experiments/new) > abre el formulario con un selector "basado en" precargado con el primer manifiesto 909ms
   ✓ ExperimentsPage - crear nuevo experimento (/experiments/new) > al cambiar la fuente en el selector, vuelve a pedir los defaults y reprecarga los campos (bug central) 656ms
   ✓ ExperimentsPage - crear nuevo experimento (/experiments/new) > en modo nuevo la card dice "Nuevo experimento" y el botón "Crear" (no "Derivar de...") 529ms
   ✓ ExperimentsPage - crear nuevo experimento (/experiments/new) > el "Derivar" de una fila NO muestra el selector "basado en" (fuente fija, igual que antes) 476ms
 ✓ src/__tests__/RunDetailPage.test.tsx (10 tests) 2448ms
   ✓ RunDetailPage > muestra el estado de la corrida con el glosario, no con el código crudo 472ms
   ✓ RunDetailPage > las pestañas separan traza, resumen, evaluación y archivos 549ms
   ✓ RunDetailPage > borrado parcial muestra el detalle de los planos que fallaron y persiste (no navega) 322ms
 ✓ src/__tests__/ComparePage.test.tsx (14 tests) 3188ms
   ✓ ComparePage > lista las corridas por nombre, no por identificador crudo 596ms
   ✓ ComparePage > compara al elegir dos y nombra las métricas en español 639ms
   ✓ ComparePage > resalta el mejor valor de cada fila 436ms
   ✓ ComparePage > avisa cuando se comparan conjuntos de evaluación distintos 364ms
   ✓ ComparePage > no avisa cuando comparten conjunto de evaluación 346ms
   ✓ ComparePage > informa las corridas que quedaron afuera en vez de omitirlas en silencio 332ms
 ✓ src/__tests__/DeriveExperimentForm.test.tsx (13 tests) 3259ms
   ✓ DeriveExperimentForm > precarga los valores del manifiesto fuente 370ms
   ✓ DeriveExperimentForm > con los valores precargados sin tocar, overrides sale vacío 321ms
   ✓ DeriveExperimentForm > un valor no numérico en warmup_frames no se manda (evita el borrado silencioso vía null) y muestra un error 319ms
   ✓ DeriveExperimentForm > mode "derive" (default): título "Derivar de <source>" y botón "Derivar" 562ms
 ✓ src/__tests__/RecordPanel.test.tsx (13 tests) 4215ms
   ✓ RecordPanel > mientras graba, consulta el backend periodicamente y muestra elapsed_ms/size_bytes de ahi 1129ms
   ✓ RecordPanel > si el backend informa error, deja de contar y muestra el motivo 1272ms
stderr | src/__tests__/ComposePage.test.tsx > ComposePage fuente RTSP > al elegir rtsp muestra el campo URL y arma config { url }
No routes matched location "/runs/r1"

 ✓ src/__tests__/ComposePage.test.tsx (12 tests) 3998ms
   ✓ ComposePage prefill > conserva active_ids del manifiesto y no lo pisan los defaults del set 476ms
   ✓ ComposePage prefill de source.type video > conserva el source.type original en la composición (round-trip sin colapso a video_file) 507ms
   ✓ ComposePage prefill survives catalog re-fetch (no clobber) > no reaplica el manifiesto cuando `experiments` cambia de referencia tras un re-fetch 406ms
   ✓ ComposePage nombre opcional del run > manda run.name cuando se completa, null cuando se deja vacío 639ms
   ✓ ComposePage fuente RTSP > bloquea Lanzar si la URL RTSP trae credenciales censuradas (***) 362ms
stderr | src/__tests__/ComposePage.test.tsx > ComposePage cámara guardada (oak_d) > lanza con la config del preset de cámara elegido
No routes matched location "/runs/r1"

 ✓ src/__tests__/TraceSection.test.tsx (10 tests) 4095ms
   ✓ TraceSection > no vuelca todos los cuadros: la lista se acota y dice el total 2086ms
   ✓ TraceSection > las flechas de navegación se deshabilitan en los extremos 375ms
 ✓ src/__tests__/contrato/experimentos-distribucion.contrato.test.tsx (4 tests) 4033ms
   ✓ Contrato: experimentos y distribución > lista y abre un experimento con outcomes vinculados a cada alerta 1891ms
   ✓ Contrato: experimentos y distribución > deriva un manifiesto con overrides y lanza la derivación seleccionada 1445ms
   ✓ Contrato: experimentos y distribución > seleccionar dos corridas evaluadas pide su comparación por HTTP 541ms
stderr | src/__tests__/Shell.test.tsx > Shell > renderiza los tres títulos de grupo
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/contrato/nueva-corrida.contrato.test.tsx (3 tests) 3975ms
   ✓ Contrato: nueva corrida > consulta preflight, compone fuente y prompts, lanza y abre el detalle real 2465ms
   ✓ Contrato: nueva corrida > impide lanzar con el formulario completo si el target aún no está listo 799ms
   ✓ Contrato: nueva corrida > impide lanzar y muestra el motivo cuando el preflight informa bloqueos 704ms
 ✓ src/__tests__/Shell.test.tsx (17 tests) 4418ms
   ✓ Shell > renderiza los tres títulos de grupo 379ms
   ✓ Shell > acorta la etiqueta que no entra, sin perder el nombre completo 523ms
   ✓ Shell > "Nuevo experimento" es acción primaria y apunta a /experiments/new 356ms
   ✓ Shell > el botón de menú abre la barra lateral 326ms
   ✓ Shell > hacer click en el scrim cierra la barra lateral 348ms
 ✓ src/__tests__/RunsPage.test.tsx (16 tests) 5297ms
   ✓ RunsPage > lista corridas y marca la que está en curso 757ms
   ✓ RunsPage > pagina el listado en vez de volcar todas las filas 1490ms
   ✓ RunsPage > no ofrece borrar una corrida en curso, sí una terminada 382ms
   ✓ RunsPage > la confirmación es en línea, no un diálogo del navegador 394ms
   ✓ RunsPage > cancelar la confirmación no borra nada 369ms
   ✓ RunsPage > confirmar borra la corrida y refresca la lista 439ms
   ✓ RunsPage > borrado parcial muestra los planos que fallaron, y persiste tras el refresh 303ms
 ✓ src/__tests__/api.test.ts (12 tests) 139ms
 ✓ src/__tests__/labels.test.ts (13 tests) 52ms
stderr | src/__tests__/CamerasPage.test.tsx > CamerasPage > lista los presets de cámara
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/traceview.test.ts (12 tests) 27ms
 ✓ src/__tests__/experimentview.test.ts (15 tests) 37ms
 ✓ src/__tests__/runview.test.ts (17 tests) 25ms
 ✓ src/__tests__/PreviewWithBoxes.test.tsx (8 tests) 330ms
 ✓ src/__tests__/PromptSetEditor.test.tsx (5 tests) 1767ms
   ✓ PromptSetEditor > exploratory: permite editar y guardar via updatePromptSet 752ms
   ✓ PromptSetEditor > freeze flow: pedir congelamiento y confirmar 389ms
stderr | src/__tests__/spec44c_gate.test.tsx > spec44c gate: flujo de experimentos por la UI > ExperimentsPage: lista un manifiesto y dispara runExperiment al hacer click en "Ejecutar experimento"
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/runseries.test.ts (12 tests) 52ms
 ✓ src/__tests__/CamerasPage.test.tsx (7 tests) 2610ms
   ✓ CamerasPage > lista los presets de cámara 564ms
   ✓ CamerasPage > muestra banner y deshabilita conectar ante 409 run_active 666ms
   ✓ CamerasPage > muestra banner ante 409 preview_active (sesión de preview ya activa) 322ms
   ✓ CamerasPage > activa por defecto las clases sin enabled_by_default declarado en el YAML 557ms
 ✓ src/__tests__/LiveViewer.test.tsx (4 tests) 288ms
 ✓ src/__tests__/spec44c_gate.test.tsx (3 tests) 1217ms
   ✓ spec44c gate: flujo de experimentos por la UI > ExperimentsPage: lista un manifiesto y dispara runExperiment al hacer click en "Ejecutar experimento" 923ms
 ✓ src/__tests__/charts/timeline.test.ts (9 tests) 92ms
 ✓ src/__tests__/useServiceHealth.test.ts (5 tests) 447ms
 ✓ src/__tests__/RunKpiStrip.test.tsx (7 tests) 751ms
   ✓ RunKpiStrip > rotula con el glosario, nunca con la clave cruda del sumario 318ms
 ✓ src/__tests__/charts/GroupedBars.test.tsx (8 tests) 382ms
 ✓ src/__tests__/ClipsPage.test.tsx (5 tests) 818ms
   ✓ ClipsPage > lista masters y clips 429ms
 ✓ src/__tests__/charts/layout.test.ts (9 tests) 36ms
 ✓ src/__tests__/ui/Table.test.tsx (6 tests) 520ms
 ✓ src/__tests__/PlatformPage.test.tsx (3 tests) 483ms
 ✓ src/__tests__/ui/primitives.test.tsx (10 tests) 606ms
 ✓ src/__tests__/EvalSection.test.tsx (4 tests) 421ms
 ✓ src/__tests__/nav.test.ts (10 tests) 30ms
 ✓ src/api.test.ts (4 tests) 36ms
 ✓ src/__tests__/ui/Select.test.tsx (5 tests) 888ms
   ✓ Select > abre la lista al hacer click en el control 459ms
 ✓ src/__tests__/queryClient.test.ts (4 tests) 23ms
 ✓ src/__tests__/charts/Meter.test.tsx (5 tests) 404ms
stderr | src/__tests__/contrato/corrida-viva.contrato.test.tsx > Contrato: corrida viva > permite alcanzar la corrida activa desde una ruta distinta del listado
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ComposePage.preflight.test.tsx > ComposePage: bloqueos de preflight > bloquea por motivos explícitos con ready=false y se recupera por polling
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/contrato/detalle-traza-evaluacion.contrato.test.tsx > Contrato: detalle, traza y evaluación > lee detalle y traza, permite inspeccionar cuadros y evaluar contra BENCH
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/contrato/corrida-viva.contrato.test.tsx (2 tests) 1558ms
   ✓ Contrato: corrida viva > permite alcanzar la corrida activa desde una ruta distinta del listado 1150ms
   ✓ Contrato: corrida viva > consulta mientras corre, permite detener y cesa el polling del detalle al terminar 405ms
 ✓ src/__tests__/experiment-api.test.ts (4 tests) 28ms
 ✓ src/__tests__/PromptSetsPage.test.tsx (2 tests) 863ms
   ✓ PromptSetsPage > un set frozen se muestra read-only con acción Derivar 572ms
 ✓ src/__tests__/ComposePage.preflight.test.tsx (2 tests) 1905ms
   ✓ ComposePage: bloqueos de preflight > bloquea por motivos explícitos con ready=false y se recupera por polling 1271ms
   ✓ ComposePage: bloqueos de preflight > bloquea por motivos explícitos con ready=true y se recupera por polling 630ms
 ✓ src/__tests__/contrato/detalle-traza-evaluacion.contrato.test.tsx (1 test) 2015ms
   ✓ Contrato: detalle, traza y evaluación > lee detalle y traza, permite inspeccionar cuadros y evaluar contra BENCH 2011ms
 ✓ src/__tests__/useSidebarCounts.test.ts (2 tests) 186ms
stderr | src/__tests__/LiveRunPill.test.tsx > LiveRunPill > no renderiza nada si no hay corrida viva
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/LiveRunPill.test.tsx (3 tests) 562ms
   ✓ LiveRunPill > muestra el run vivo con fps y linkea a su detalle 401ms
 ✓ src/__tests__/preview.test.ts (2 tests) 25ms
 ✓ src/__tests__/stream.test.ts (3 tests) 18ms
 ✓ src/__tests__/ui/Badge.test.tsx (4 tests) 145ms
 ✓ src/__tests__/ui/Button.test.tsx (5 tests) 480ms
   ✓ Button > por defecto es variant secondary 351ms
 ✓ src/__tests__/ui/Banner.test.tsx (3 tests) 479ms
   ✓ Banner > tono warn con boton de cerrar 414ms
stderr | src/__tests__/App.test.tsx > App > renderiza el título de la consola
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/App.test.tsx (2 tests) 442ms
   ✓ App > renderiza el título de la consola 308ms
 ✓ src/__tests__/ui/SegmentedControl.test.tsx (2 tests) 342ms
 ✓ src/__tests__/ui/ConditionName.test.tsx (3 tests) 137ms
 ✓ src/__tests__/promptview.test.ts (3 tests) 10ms
 ✓ src/__tests__/ui/InlineDeleteConfirm.test.tsx (2 tests) 369ms
   ✓ InlineDeleteConfirm > "Si, borrar" dispara onConfirm; "No" dispara onCancel 323ms
 ✓ src/__tests__/ui/SearchInput.test.tsx (1 test) 90ms
 ✓ src/__tests__/ui/icons.test.tsx (1 test) 69ms
 ✓ src/__tests__/ui/PageHeader.test.tsx (2 tests) 238ms

 Test Files  61 passed (61)
      Tests  403 passed (403)
   Start at  12:25:29
   Duration  26.12s (transform 10.06s, setup 0ms, collect 61.51s, tests 69.52s, environment 160.30s, prepare 25.09s)


```

### Build: exit 0

Comando: `npm run build`.

```text
> eovrt-webconsole-frontend@0.1.0 build
> tsc && vite build

vite v5.4.21 building for production...
transforming...
✓ 156 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.40 kB │ gzip:  0.27 kB
dist/assets/index-D1Xu6lb4.css   27.13 kB │ gzip:  5.78 kB
dist/assets/index-DbXvEX99.js   313.25 kB │ gzip: 97.32 kB
✓ built in 4.29s

```

### Backend completo: exit 0

Comando: `cd webconsole/backend && ./.venv/bin/python -m pytest -q`. Línea final de la ejecución nueva:

```text
761 passed in 142.80s (0:02:22)
```

### Capturas y navegador

Se ejecutó capture_console.mjs con los mismos argumentos documentados arriba, destinos `tools/captures/tramo-2-preflight-antes` y `tools/captures/tramo-2-preflight-despues`. Las 12 rutas cargaron sin errores de página ni fixtures faltantes en ambas tandas. Siete PNG coinciden exactamente; cinco tienen diferencias máximas de 1/255 por canal en 32 píxeles o menos. ComposePage sin bloqueos es idéntica píxel por píxel.

Antes:

![Compose antes](../../webconsole/tools/captures/tramo-2-preflight-antes/01-compose.png)

Después (sin bloqueos):

![Compose después](../../webconsole/tools/captures/tramo-2-preflight-despues/01-compose.png)

Prueba de navegador adicional: formulario completo, dos motivos de bloqueo, luego recuperación por polling sin recargar la página. Resultado real:

```json
{"blocked":true,"recoveredByPolling":true,"posts":0,"errors":[]}
```

Con bloqueos:

![Bloqueado](../../webconsole/tools/captures/tramo-2-preflight-despues/compose-bloqueado.png)

Recuperado por polling:

![Recuperado](../../webconsole/tools/captures/tramo-2-preflight-despues/compose-recuperado.png)

Estas pruebas interceptan HTTP con datos sintéticos; no ejecutan corridas ni conectan hardware. El servidor Vite temporal en 5199 se detuvo al terminar.

### Integridad y pendientes

`git diff --check`, estado del worktree de referencia y `git diff --cached --stat`: exit 0, sin salida. Los cinco archivos del contrato conservan sus SHA-256 anteriores.

No quedan tests rojos reproducibles en la ejecución final. Se mantiene registrado el fallo intermitente ajeno al cambio, sin alterar sus esperas. No se ejecutó seed_dev_data.py contra servicios reales: la validación integrada de capturas sigue pendiente y evita declarar cierre integral. No se inició tramo 3 ni se creó commit.


## Cierre de validación con datos sembrados — 2026-09-09

Se completó el pendiente de captura con BFF real. [Informe reproducible y las 24 imágenes](../../webconsole/tools/captures/seeded-tramo2.iHTMAx/VALIDACION.md), [respuestas y manifiestos de evidencia](../../webconsole/tools/captures/seeded-tramo2.iHTMAx/evidence.json).

Los servicios media/control/BFF no simulan respuestas HTTP. El detector es mock, el video es sintético y se ajustaron sólo las rutas de artefactos en un harness aislado. Las limitaciones y dos intentos preliminares fallidos del harness constan en el informe. El resultado válido es exp_seed_visual_tramo2_final: 60 cuadros procesados en cada plano, 60 descartes por rate_gate, cero cuadros no recibidos y cero errores. No se ejecutó distribución ni evaluación con GT.

No se modificó ningún archivo de producción ni test en esta continuación: sólo se añadieron artefactos, un harness y una copia de frontend para comparación dentro de tools/captures/seeded-tramo2.iHTMAx/ (gitignorado), y se actualizó este reporte. Los datos previos y la referencia están intactos. Se apagaron los cuatro procesos temporales; no quedó ningún listener en 18080, 18081, 18090 ni 18091. No se borraron las corridas de prueba (~20 MB de evidencia total).

### Backend — salida nueva, exit 0

Comando: `cd webconsole/backend && ./.venv/bin/python -m pytest -q`.

```text
........................................................................ [  9%]
........................................................................ [ 18%]
........................................................................ [ 28%]
........................................................................ [ 37%]
........................................................................ [ 47%]
........................................................................ [ 56%]
........................................................................ [ 66%]
........................................................................ [ 75%]
........................................................................ [ 85%]
........................................................................ [ 94%]
.........................................                                [100%]
761 passed in 126.91s (0:02:06)

```

### Build — salida nueva, exit 0

Comando: `cd webconsole/frontend && npm run build`.

```text
> eovrt-webconsole-frontend@0.1.0 build
> tsc && vite build

vite v5.4.21 building for production...
transforming...
✓ 156 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.40 kB │ gzip:  0.27 kB
dist/assets/index-D1Xu6lb4.css   27.13 kB │ gzip:  5.78 kB
dist/assets/index-DbXvEX99.js   313.25 kB │ gzip: 97.32 kB
✓ built in 2.92s
```

### Frontend — salida nueva, exit 0 en repetición sin procesos concurrentes de validación

La primera ejecución completa dio 402 passed / 1 failed por la espera intermitente de ExperimentsPage.new.test.tsx:57; duración 32.16 s. No se editó ese test ni se cambió configuración o timeouts. Se repitió el mismo `npm test` una vez terminados backend/build y apagados los servidores temporales:

```text
stderr | src/__tests__/ExperimentDetailPageRiskBanner.test.tsx > ExperimentDetailPage — banner de riesgo activo > muestra el banner con el condition_id cuando patterns no esta vacio y el experimento corre
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ExperimentDetailPage.test.tsx > ExperimentDetailPage > muestra las alertas y avisa que el conjunto no es temporal
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ExperimentsPage.test.tsx > ExperimentsPage > lista manifiestos y dispara un experimento con preflight verde
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/TrimDialog.test.tsx (9 tests) 628ms
stderr | src/__tests__/ComposePage.test.tsx > ComposePage prefill > conserva active_ids del manifiesto y no lo pisan los defaults del set
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ExperimentsPage.new.test.tsx > ExperimentsPage - crear nuevo experimento (/experiments/new) > abre el formulario con un selector "basado en" precargado con el primer manifiesto
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/RunsPage.test.tsx > RunsPage > lista corridas y marca la que está en curso
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/RunDetailPage.test.tsx > RunDetailPage > muestra el estado de la corrida con el glosario, no con el código crudo
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/ExperimentDetailPageRiskBanner.test.tsx (7 tests) 732ms
stderr | src/__tests__/contrato/experimentos-distribucion.contrato.test.tsx > Contrato: experimentos y distribución > lista y abre un experimento con outcomes vinculados a cada alerta
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ComposePage.test.tsx > ComposePage prefill de source.type video > conserva el source.type original en la composición (round-trip sin colapso a video_file)
No routes matched location "/runs/r1"

stderr | src/__tests__/contrato/nueva-corrida.contrato.test.tsx > Contrato: nueva corrida > consulta preflight, compone fuente y prompts, lanza y abre el detalle real
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/ExperimentsPage.test.tsx (5 tests) 1717ms
   ✓ ExperimentsPage > lista manifiestos y dispara un experimento con preflight verde 848ms
 ✓ src/__tests__/ExperimentDetailPage.test.tsx (15 tests) 1917ms
   ✓ ExperimentDetailPage > muestra las alertas y avisa que el conjunto no es temporal 321ms
   ✓ ExperimentDetailPage > un error real del reporte sí se muestra como error, con su código 311ms
stderr | src/__tests__/ComposePage.test.tsx > ComposePage nombre opcional del run > manda run.name cuando se completa, null cuando se deja vacío
No routes matched location "/runs/r1"

 ✓ src/__tests__/ExperimentsPage.new.test.tsx (4 tests) 2217ms
   ✓ ExperimentsPage - crear nuevo experimento (/experiments/new) > abre el formulario con un selector "basado en" precargado con el primer manifiesto 889ms
   ✓ ExperimentsPage - crear nuevo experimento (/experiments/new) > al cambiar la fuente en el selector, vuelve a pedir los defaults y reprecarga los campos (bug central) 501ms
   ✓ ExperimentsPage - crear nuevo experimento (/experiments/new) > en modo nuevo la card dice "Nuevo experimento" y el botón "Crear" (no "Derivar de...") 487ms
   ✓ ExperimentsPage - crear nuevo experimento (/experiments/new) > el "Derivar" de una fila NO muestra el selector "basado en" (fuente fija, igual que antes) 336ms
 ✓ src/__tests__/DeriveExperimentForm.test.tsx (13 tests) 2249ms
   ✓ DeriveExperimentForm > precarga los valores del manifiesto fuente 362ms
   ✓ DeriveExperimentForm > mode "derive" (default): título "Derivar de <source>" y botón "Derivar" 324ms
stderr | src/__tests__/ComposePage.test.tsx > ComposePage nombre opcional del run > deja run.name en null si el campo queda vacío (usa el id autogenerado)
No routes matched location "/runs/r2"

 ✓ src/__tests__/RunDetailPage.test.tsx (10 tests) 2185ms
   ✓ RunDetailPage > las pestañas separan traza, resumen, evaluación y archivos 579ms
   ✓ RunDetailPage > borrado parcial muestra el detalle de los planos que fallaron y persiste (no navega) 411ms
 ✓ src/__tests__/ComparePage.test.tsx (14 tests) 2628ms
   ✓ ComparePage > lista las corridas por nombre, no por identificador crudo 540ms
   ✓ ComparePage > compara al elegir dos y nombra las métricas en español 448ms
   ✓ ComparePage > resalta el mejor valor de cada fila 421ms
 ✓ src/__tests__/TraceSection.test.tsx (10 tests) 3363ms
   ✓ TraceSection > no vuelca todos los cuadros: la lista se acota y dice el total 1867ms
   ✓ TraceSection > el banner de alerta nombra la condición, no solo el código 328ms
 ✓ src/__tests__/RecordPanel.test.tsx (13 tests) 3875ms
   ✓ RecordPanel > mientras graba, consulta el backend periodicamente y muestra elapsed_ms/size_bytes de ahi 1176ms
   ✓ RecordPanel > si el backend informa error, deja de contar y muestra el motivo 1164ms
 ✓ src/__tests__/contrato/experimentos-distribucion.contrato.test.tsx (4 tests) 3379ms
   ✓ Contrato: experimentos y distribución > lista y abre un experimento con outcomes vinculados a cada alerta 1526ms
   ✓ Contrato: experimentos y distribución > deriva un manifiesto con overrides y lanza la derivación seleccionada 1189ms
   ✓ Contrato: experimentos y distribución > seleccionar dos corridas evaluadas pide su comparación por HTTP 481ms
stderr | src/__tests__/Shell.test.tsx > Shell > renderiza los tres títulos de grupo
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ComposePage.test.tsx > ComposePage fuente RTSP > al elegir rtsp muestra el campo URL y arma config { url }
No routes matched location "/runs/r1"

stderr | src/__tests__/ComposePage.test.tsx > ComposePage cámara guardada (oak_d) > lanza con la config del preset de cámara elegido
No routes matched location "/runs/r1"

 ✓ src/__tests__/ComposePage.test.tsx (12 tests) 3851ms
   ✓ ComposePage prefill > conserva active_ids del manifiesto y no lo pisan los defaults del set 779ms
   ✓ ComposePage prefill de source.type video > conserva el source.type original en la composición (round-trip sin colapso a video_file) 364ms
   ✓ ComposePage prefill survives catalog re-fetch (no clobber) > no reaplica el manifiesto cuando `experiments` cambia de referencia tras un re-fetch 303ms
   ✓ ComposePage nombre opcional del run > manda run.name cuando se completa, null cuando se deja vacío 308ms
   ✓ ComposePage aviso de 409 al lanzar > muestra aviso de prueba de cámara activa ante 409 preview_active 325ms
   ✓ ComposePage aviso de 409 al lanzar > muestra aviso de run activo ante 409 con active_run_id 433ms
   ✓ ComposePage fuente RTSP > bloquea Lanzar si la URL RTSP trae credenciales censuradas (***) 354ms
 ✓ src/__tests__/Shell.test.tsx (17 tests) 3982ms
   ✓ Shell > renderiza los tres títulos de grupo 350ms
   ✓ Shell > acorta la etiqueta que no entra, sin perder el nombre completo 453ms
   ✓ Shell > hacer click en el scrim cierra la barra lateral 461ms
 ✓ src/__tests__/contrato/nueva-corrida.contrato.test.tsx (3 tests) 3917ms
   ✓ Contrato: nueva corrida > consulta preflight, compone fuente y prompts, lanza y abre el detalle real 2691ms
   ✓ Contrato: nueva corrida > impide lanzar con el formulario completo si el target aún no está listo 580ms
   ✓ Contrato: nueva corrida > impide lanzar y muestra el motivo cuando el preflight informa bloqueos 636ms
 ✓ src/__tests__/RunsPage.test.tsx (16 tests) 4675ms
   ✓ RunsPage > lista corridas y marca la que está en curso 672ms
   ✓ RunsPage > pagina el listado en vez de volcar todas las filas 1246ms
   ✓ RunsPage > borrado parcial muestra los planos que fallaron, y persiste tras el refresh 335ms
 ✓ src/__tests__/api.test.ts (12 tests) 85ms
stderr | src/__tests__/CamerasPage.test.tsx > CamerasPage > lista los presets de cámara
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/labels.test.ts (13 tests) 38ms
 ✓ src/__tests__/experimentview.test.ts (15 tests) 37ms
 ✓ src/__tests__/traceview.test.ts (12 tests) 45ms
 ✓ src/__tests__/runview.test.ts (17 tests) 42ms
 ✓ src/__tests__/CamerasPage.test.tsx (7 tests) 2626ms
   ✓ CamerasPage > lista los presets de cámara 551ms
   ✓ CamerasPage > muestra banner y deshabilita conectar ante 409 run_active 682ms
   ✓ CamerasPage > muestra banner ante 409 preview_active (sesión de preview ya activa) 436ms
   ✓ CamerasPage > activa por defecto las clases sin enabled_by_default declarado en el YAML 477ms
stderr | src/__tests__/spec44c_gate.test.tsx > spec44c gate: flujo de experimentos por la UI > ExperimentsPage: lista un manifiesto y dispara runExperiment al hacer click en "Ejecutar experimento"
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/PreviewWithBoxes.test.tsx (8 tests) 455ms
 ✓ src/__tests__/PromptSetEditor.test.tsx (5 tests) 1387ms
   ✓ PromptSetEditor > exploratory: permite editar y guardar via updatePromptSet 762ms
 ✓ src/__tests__/useServiceHealth.test.ts (5 tests) 421ms
 ✓ src/__tests__/spec44c_gate.test.tsx (3 tests) 890ms
   ✓ spec44c gate: flujo de experimentos por la UI > ExperimentsPage: lista un manifiesto y dispara runExperiment al hacer click en "Ejecutar experimento" 653ms
 ✓ src/__tests__/runseries.test.ts (12 tests) 29ms
 ✓ src/__tests__/LiveViewer.test.tsx (4 tests) 251ms
 ✓ src/__tests__/charts/timeline.test.ts (9 tests) 85ms
 ✓ src/__tests__/RunKpiStrip.test.tsx (7 tests) 564ms
 ✓ src/__tests__/charts/GroupedBars.test.tsx (8 tests) 450ms
 ✓ src/__tests__/ClipsPage.test.tsx (5 tests) 668ms
 ✓ src/__tests__/ui/Table.test.tsx (6 tests) 462ms
 ✓ src/__tests__/charts/layout.test.ts (9 tests) 34ms
 ✓ src/__tests__/PlatformPage.test.tsx (3 tests) 436ms
 ✓ src/__tests__/EvalSection.test.tsx (4 tests) 394ms
 ✓ src/__tests__/ui/primitives.test.tsx (10 tests) 564ms
 ✓ src/__tests__/nav.test.ts (10 tests) 25ms
 ✓ src/api.test.ts (4 tests) 95ms
stderr | src/__tests__/contrato/corrida-viva.contrato.test.tsx > Contrato: corrida viva > permite alcanzar la corrida activa desde una ruta distinta del listado
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/queryClient.test.ts (4 tests) 25ms
 ✓ src/__tests__/ui/Select.test.tsx (5 tests) 909ms
   ✓ Select > abre la lista al hacer click en el control 433ms
 ✓ src/__tests__/charts/Meter.test.tsx (5 tests) 582ms
 ✓ src/__tests__/contrato/corrida-viva.contrato.test.tsx (2 tests) 1594ms
   ✓ Contrato: corrida viva > permite alcanzar la corrida activa desde una ruta distinta del listado 1055ms
   ✓ Contrato: corrida viva > consulta mientras corre, permite detener y cesa el polling del detalle al terminar 536ms
stderr | src/__tests__/contrato/detalle-traza-evaluacion.contrato.test.tsx > Contrato: detalle, traza y evaluación > lee detalle y traza, permite inspeccionar cuadros y evaluar contra BENCH
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/PromptSetsPage.test.tsx (2 tests) 983ms
   ✓ PromptSetsPage > lista los sets con badge de estado 361ms
   ✓ PromptSetsPage > un set frozen se muestra read-only con acción Derivar 616ms
stderr | src/__tests__/ComposePage.preflight.test.tsx > ComposePage: bloqueos de preflight > bloquea por motivos explícitos con ready=false y se recupera por polling
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/experiment-api.test.ts (4 tests) 64ms
 ✓ src/__tests__/contrato/detalle-traza-evaluacion.contrato.test.tsx (1 test) 1968ms
   ✓ Contrato: detalle, traza y evaluación > lee detalle y traza, permite inspeccionar cuadros y evaluar contra BENCH 1964ms
 ✓ src/__tests__/ComposePage.preflight.test.tsx (2 tests) 1866ms
   ✓ ComposePage: bloqueos de preflight > bloquea por motivos explícitos con ready=false y se recupera por polling 1317ms
   ✓ ComposePage: bloqueos de preflight > bloquea por motivos explícitos con ready=true y se recupera por polling 546ms
 ✓ src/__tests__/useSidebarCounts.test.ts (2 tests) 217ms
stderr | src/__tests__/LiveRunPill.test.tsx > LiveRunPill > no renderiza nada si no hay corrida viva
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/LiveRunPill.test.tsx (3 tests) 416ms
 ✓ src/__tests__/stream.test.ts (3 tests) 21ms
 ✓ src/__tests__/ui/Button.test.tsx (5 tests) 554ms
   ✓ Button > por defecto es variant secondary 340ms
 ✓ src/__tests__/preview.test.ts (2 tests) 12ms
stderr | src/__tests__/App.test.tsx > App > renderiza el título de la consola
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/App.test.tsx (2 tests) 503ms
 ✓ src/__tests__/ui/Badge.test.tsx (4 tests) 136ms
 ✓ src/__tests__/ui/Banner.test.tsx (3 tests) 585ms
   ✓ Banner > tono warn con boton de cerrar 471ms
 ✓ src/__tests__/ui/ConditionName.test.tsx (3 tests) 121ms
 ✓ src/__tests__/ui/SegmentedControl.test.tsx (2 tests) 420ms
   ✓ SegmentedControl > marca la opcion activa con aria-pressed 334ms
 ✓ src/__tests__/ui/SearchInput.test.tsx (1 test) 150ms
 ✓ src/__tests__/ui/InlineDeleteConfirm.test.tsx (2 tests) 450ms
   ✓ InlineDeleteConfirm > "Si, borrar" dispara onConfirm; "No" dispara onCancel 391ms
 ✓ src/__tests__/promptview.test.ts (3 tests) 13ms
 ✓ src/__tests__/ui/PageHeader.test.tsx (2 tests) 354ms
   ✓ PageHeader > renderiza titulo, meta y acciones 320ms
 ✓ src/__tests__/ui/icons.test.tsx (1 test) 102ms

 Test Files  61 passed (61)
      Tests  403 passed (403)
   Start at  12:38:35
   Duration  24.83s (transform 8.65s, setup 0ms, collect 59.62s, tests 63.44s, environment 145.86s, prepare 23.36s)


```

### Integridad

`git diff --check`, `git diff --cached --stat` y `git -C .worktrees/front-design status --short`: exit 0, sin salida. SHA-256 de los cinco archivos de contrato idénticos a los previos.

Queda registrado, fuera del alcance del tramo, el test de espera intermitente y la dependencia del runner de las rutas convencionales del workspace. No bloquean esta validación realizada con servicios reales y rutas explícitas; no se presentan como corregidos. Las excepciones aprobadas (alias RunSummary y gate de ComposePage) deben preservarse en los tramos siguientes. No se inició el tramo 3.
