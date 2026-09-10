# Punch-list: salidas completas de verificación — 2026-09-10

Ejecuciones reales para P-2 → P-1 → P-3/P-4/P-5. No se ejecutaron los tramos 6/7.

Los seis cortes se materializaron desde el índice de Git en un checkout temporal mediante `git write-tree` y `git read-tree --reset -u <tree>`. Las dependencias instaladas se reutilizaron por enlaces; se ejecutaron los archivos de cada corte. Antes de cada commit se comprobó que su árbol coincidiera con el verificado. El directorio principal conservó el código final y los cambios ajenos.

En el backend del corte 1 se antepuso su `src/` mediante `PYTHONPATH`; los repos hermanos se enlazaron en `/tmp/` y el ejecutable del distribuidor se indicó por entorno. No se editaron fuentes ni tests para resolver esas rutas.

Las salidas conservan todos los mensajes; sólo se retiraron los códigos de color ANSI y los espacios al final de línea para versionarlas como Markdown. Los avisos de React Router y los de rutas ausentes en fixtures permanecen. Ruff termina con exit 1 por los 36 diagnósticos heredados: no se presenta como un check verde. Los comandos de pruebas/build finales terminan con exit 0.

## P-2: 50b666b intacto

```bash
cd /tmp/paridad/webconsole/frontend && npx vitest run src/__tests__/contrato
```

```text

 RUN  v2.1.9 /tmp/paridad/webconsole/frontend

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

 ✓ src/__tests__/contrato/corrida-viva.contrato.test.tsx (2 tests) 418ms
 ✓ src/__tests__/contrato/detalle-traza-evaluacion.contrato.test.tsx (1 test) 472ms
   ✓ Contrato: detalle, traza y evaluación > lee detalle y traza, permite inspeccionar cuadros y evaluar contra BENCH 470ms
 ✓ src/__tests__/contrato/experimentos-distribucion.contrato.test.tsx (4 tests) 979ms
   ✓ Contrato: experimentos y distribución > lista y abre un experimento con outcomes vinculados a cada alerta 348ms
   ✓ Contrato: experimentos y distribución > deriva un manifiesto con overrides y lanza la derivación seleccionada 413ms
 ✓ src/__tests__/contrato/nueva-corrida.contrato.test.tsx (3 tests) 1122ms
   ✓ Contrato: nueva corrida > consulta preflight, compone fuente y prompts, lanza y abre el detalle real 595ms

 Test Files  4 passed (4)
      Tests  10 passed (10)
   Start at  02:13:54
   Duration  3.83s (transform 1.19s, setup 0ms, collect 3.41s, tests 2.99s, environment 3.48s, prepare 1.46s)

```

## P-2: árbol actual

```bash
cd webconsole/frontend && npx vitest run src/__tests__/contrato
```

```text

 RUN  v2.1.9 /home/simonll4/projects/e-ovrt_experimental-setup/webconsole/frontend

stderr | src/__tests__/contrato/experimentos-distribucion.contrato.test.tsx > Contrato: experimentos y distribución > lista y abre un experimento con outcomes vinculados a cada alerta
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/contrato/detalle-traza-evaluacion.contrato.test.tsx > Contrato: detalle, traza y evaluación > lee detalle y traza, permite inspeccionar cuadros y evaluar contra BENCH
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/contrato/corrida-viva.contrato.test.tsx > Contrato: corrida viva > permite alcanzar la corrida activa desde una ruta distinta del listado
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/contrato/nueva-corrida.contrato.test.tsx > Contrato: nueva corrida > consulta preflight, compone fuente y prompts, lanza y abre el detalle real
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/contrato/detalle-traza-evaluacion.contrato.test.tsx (1 test) 491ms
   ✓ Contrato: detalle, traza y evaluación > lee detalle y traza, permite inspeccionar cuadros y evaluar contra BENCH 487ms
 ✓ src/__tests__/contrato/corrida-viva.contrato.test.tsx (2 tests) 554ms
   ✓ Contrato: corrida viva > permite alcanzar la corrida activa desde una ruta distinta del listado 324ms
 ✓ src/__tests__/contrato/experimentos-distribucion.contrato.test.tsx (4 tests) 1001ms
   ✓ Contrato: experimentos y distribución > lista y abre un experimento con outcomes vinculados a cada alerta 396ms
   ✓ Contrato: experimentos y distribución > deriva un manifiesto con overrides y lanza la derivación seleccionada 426ms
 ✓ src/__tests__/contrato/nueva-corrida.contrato.test.tsx (3 tests) 1341ms
   ✓ Contrato: nueva corrida > consulta preflight, compone fuente y prompts, lanza y abre el detalle real 757ms
   ✓ Contrato: nueva corrida > muestra los bloqueos del preflight y permite lanzar sólo medios con target listo 337ms

 Test Files  4 passed (4)
      Tests  10 passed (10)
   Start at  02:13:54
   Duration  4.10s (transform 1.17s, setup 0ms, collect 3.60s, tests 3.39s, environment 3.39s, prepare 1.42s)

```

## Corte 0: build

```bash
cd /tmp/eovrt-cortes-validation/webconsole/frontend && npm run build
```

```text

> eovrt-webconsole-frontend@0.1.0 build
> tsc && vite build

vite v5.4.21 building for production...
transforming...
✓ 106 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.40 kB │ gzip:  0.27 kB
dist/assets/index-D1Xu6lb4.css   27.13 kB │ gzip:  5.78 kB
dist/assets/index-oHbTuLXw.js   283.39 kB │ gzip: 88.47 kB
✓ built in 1.39s
```

## Corte 0: frontend completo

```bash
cd /tmp/eovrt-cortes-validation/webconsole/frontend && npm test
```

```text

> eovrt-webconsole-frontend@0.1.0 test
> vitest run


 RUN  v2.1.9 /tmp/eovrt-cortes-validation/webconsole/frontend

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

stderr | src/__tests__/RunDetailPage.test.tsx > RunDetailPage > muestra el estado de la corrida con el glosario, no con el código crudo
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/TrimDialog.test.tsx (9 tests) 1794ms
   ✓ TrimDialog > generar queda deshabilitado hasta tener las dos marcas 323ms
   ✓ TrimDialog > P6 pide cuatro marcas y las postea en orden 524ms
stderr | src/__tests__/RunsPage.test.tsx > RunsPage > lista corridas y marca la que está en curso
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/contrato/experimentos-distribucion.contrato.test.tsx > Contrato: experimentos y distribución > lista y abre un experimento con outcomes vinculados a cada alerta
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/ExperimentDetailPageRiskBanner.test.tsx (7 tests) 1882ms
   ✓ ExperimentDetailPage — banner de riesgo activo > muestra el banner con el condition_id cuando patterns no esta vacio y el experimento corre 487ms
   ✓ ExperimentDetailPage — banner de riesgo activo > un error transitorio de red no rompe la pagina ni borra el badge de estado 641ms
stderr | src/__tests__/contrato/nueva-corrida.contrato.test.tsx > Contrato: nueva corrida > consulta preflight, compone fuente y prompts, lanza y abre el detalle real
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ComposePage.test.tsx > ComposePage prefill de source.type video > conserva el source.type original en la composición (round-trip sin colapso a video_file)
No routes matched location "/runs/r1"

 ✓ src/__tests__/ExperimentsPage.test.tsx (5 tests) 3011ms
   ✓ ExperimentsPage > lista manifiestos y dispara un experimento con preflight verde 1498ms
   ✓ ExperimentsPage > muestra el detalle del 503 si el gate del BFF rechaza el lanzamiento 415ms
   ✓ ExperimentsPage > espera la recarga de manifiestos antes de seleccionar el slug derivado 569ms
 ✓ src/__tests__/ExperimentDetailPage.test.tsx (15 tests) 3064ms
   ✓ ExperimentDetailPage > muestra las alertas y avisa que el conjunto no es temporal 504ms
   ✓ ExperimentDetailPage > reporte no consolidado (404) se explica como pendiente, no como error 509ms
   ✓ ExperimentDetailPage > un error real del reporte sí se muestra como error, con su código 346ms
 ✓ src/__tests__/ExperimentsPage.new.test.tsx (4 tests) 3257ms
   ✓ ExperimentsPage - crear nuevo experimento (/experiments/new) > abre el formulario con un selector "basado en" precargado con el primer manifiesto 1860ms
   ✓ ExperimentsPage - crear nuevo experimento (/experiments/new) > al cambiar la fuente en el selector, vuelve a pedir los defaults y reprecarga los campos (bug central) 768ms
   ✓ ExperimentsPage - crear nuevo experimento (/experiments/new) > en modo nuevo la card dice "Nuevo experimento" y el botón "Crear" (no "Derivar de...") 358ms
 ✓ src/__tests__/RunDetailPage.test.tsx (10 tests) 3071ms
   ✓ RunDetailPage > muestra el estado de la corrida con el glosario, no con el código crudo 862ms
   ✓ RunDetailPage > las pestañas separan traza, resumen, evaluación y archivos 636ms
stderr | src/__tests__/ComposePage.test.tsx > ComposePage nombre opcional del run > manda run.name cuando se completa, null cuando se deja vacío
No routes matched location "/runs/r1"

 ✓ src/__tests__/DeriveExperimentForm.test.tsx (13 tests) 3636ms
   ✓ DeriveExperimentForm > precarga los valores del manifiesto fuente 763ms
   ✓ DeriveExperimentForm > con los valores precargados sin tocar, overrides sale vacío 712ms
   ✓ DeriveExperimentForm > sólo manda el campo que el usuario cambió respecto del fuente 334ms
   ✓ DeriveExperimentForm > muestra el detail real del backend (409), no el "API 409" genérico de ApiError 344ms
   ✓ DeriveExperimentForm > mode "derive" (default): título "Derivar de <source>" y botón "Derivar" 371ms
stderr | src/__tests__/ComposePage.test.tsx > ComposePage nombre opcional del run > deja run.name en null si el campo queda vacío (usa el id autogenerado)
No routes matched location "/runs/r2"

 ✓ src/__tests__/ComparePage.test.tsx (14 tests) 3993ms
   ✓ ComparePage > lista las corridas por nombre, no por identificador crudo 1254ms
   ✓ ComparePage > compara al elegir dos y nombra las métricas en español 864ms
   ✓ ComparePage > resalta el mejor valor de cada fila 591ms
 ✓ src/__tests__/TraceSection.test.tsx (10 tests) 4041ms
   ✓ TraceSection > no vuelca todos los cuadros: la lista se acota y dice el total 2914ms
stderr | src/__tests__/Shell.test.tsx > Shell > renderiza los tres títulos de grupo
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/contrato/experimentos-distribucion.contrato.test.tsx (4 tests) 4362ms
   ✓ Contrato: experimentos y distribución > lista y abre un experimento con outcomes vinculados a cada alerta 2723ms
   ✓ Contrato: experimentos y distribución > deriva un manifiesto con overrides y lanza la derivación seleccionada 1235ms
   ✓ Contrato: experimentos y distribución > seleccionar dos corridas evaluadas pide su comparación por HTTP 308ms
 ✓ src/__tests__/Shell.test.tsx (17 tests) 4499ms
   ✓ Shell > renderiza los tres títulos de grupo 526ms
   ✓ Shell > renderiza los 6 destinos 337ms
   ✓ Shell > acorta la etiqueta que no entra, sin perder el nombre completo 1235ms
   ✓ Shell > "Nueva corrida" es acción primaria y apunta a /compose 354ms
 ✓ src/__tests__/RecordPanel.test.tsx (13 tests) 5490ms
   ✓ RecordPanel > muestra el proximo basename propuesto 477ms
   ✓ RecordPanel > deshabilita grabar y explica por que cuando no hay camara elegida 441ms
   ✓ RecordPanel > arranca la grabacion con la camara, escenario y variante elegidos 714ms
   ✓ RecordPanel > mientras graba, consulta el backend periodicamente y muestra elapsed_ms/size_bytes de ahi 1186ms
   ✓ RecordPanel > si el backend informa error, deja de contar y muestra el motivo 1209ms
stderr | src/__tests__/ComposePage.test.tsx > ComposePage fuente RTSP > al elegir rtsp muestra el campo URL y arma config { url }
No routes matched location "/runs/r1"

stderr | src/__tests__/ComposePage.test.tsx > ComposePage cámara guardada (oak_d) > lanza con la config del preset de cámara elegido
No routes matched location "/runs/r1"

 ✓ src/__tests__/ComposePage.test.tsx (12 tests) 4753ms
   ✓ ComposePage prefill > conserva active_ids del manifiesto y no lo pisan los defaults del set 1471ms
   ✓ ComposePage prefill de source.type video > conserva el source.type original en la composición (round-trip sin colapso a video_file) 841ms
   ✓ ComposePage nombre opcional del run > manda run.name cuando se completa, null cuando se deja vacío 418ms
 ✓ src/__tests__/contrato/nueva-corrida.contrato.test.tsx (3 tests) 4490ms
   ✓ Contrato: nueva corrida > consulta preflight, compone fuente y prompts, lanza y abre el detalle real 3315ms
   ✓ Contrato: nueva corrida > impide lanzar con el formulario completo si el target aún no está listo 440ms
   ✓ Contrato: nueva corrida > muestra los bloqueos del preflight y permite lanzar sólo medios con target listo 731ms
 ✓ src/__tests__/RunsPage.test.tsx (16 tests) 6298ms
   ✓ RunsPage > lista corridas y marca la que está en curso 1731ms
   ✓ RunsPage > traduce los estados: nunca muestra el código crudo del backend 430ms
   ✓ RunsPage > pagina el listado en vez de volcar todas las filas 1356ms
   ✓ RunsPage > cancelar la confirmación no borra nada 382ms
   ✓ RunsPage > confirmar borra la corrida y refresca la lista 476ms
 ✓ src/__tests__/labels.test.ts (13 tests) 53ms
 ✓ src/__tests__/api.test.ts (12 tests) 94ms
 ✓ src/__tests__/traceview.test.ts (12 tests) 24ms
 ✓ src/__tests__/experimentview.test.ts (15 tests) 23ms
 ✓ src/__tests__/runview.test.ts (17 tests) 28ms
 ✓ src/__tests__/runseries.test.ts (12 tests) 35ms
 ✓ src/__tests__/useServiceHealth.test.ts (5 tests) 365ms
stderr | src/__tests__/spec44c_gate.test.tsx > spec44c gate: flujo de experimentos por la UI > ExperimentsPage: lista un manifiesto y dispara runExperiment al hacer click en "Ejecutar experimento"
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/CamerasPage.test.tsx > CamerasPage > lista los presets de cámara
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/PreviewWithBoxes.test.tsx (8 tests) 285ms
 ✓ src/__tests__/PromptSetEditor.test.tsx (5 tests) 963ms
   ✓ PromptSetEditor > exploratory: permite editar y guardar via updatePromptSet 344ms
 ✓ src/__tests__/spec44c_gate.test.tsx (3 tests) 718ms
   ✓ spec44c gate: flujo de experimentos por la UI > ExperimentsPage: lista un manifiesto y dispara runExperiment al hacer click en "Ejecutar experimento" 536ms
 ✓ src/__tests__/LiveViewer.test.tsx (4 tests) 166ms
 ✓ src/__tests__/RunKpiStrip.test.tsx (7 tests) 372ms
 ✓ src/__tests__/charts/GroupedBars.test.tsx (8 tests) 441ms
 ✓ src/__tests__/charts/timeline.test.ts (9 tests) 78ms
 ✓ src/__tests__/CamerasPage.test.tsx (7 tests) 1729ms
   ✓ CamerasPage > muestra banner y deshabilita conectar ante 409 run_active 396ms
   ✓ CamerasPage > activa por defecto las clases sin enabled_by_default declarado en el YAML 430ms
 ✓ src/__tests__/ClipsPage.test.tsx (5 tests) 604ms
 ✓ src/__tests__/ui/Table.test.tsx (6 tests) 356ms
 ✓ src/__tests__/charts/layout.test.ts (9 tests) 31ms
 ✓ src/__tests__/PlatformPage.test.tsx (3 tests) 316ms
 ✓ src/__tests__/ui/primitives.test.tsx (10 tests) 342ms
 ✓ src/__tests__/EvalSection.test.tsx (4 tests) 316ms
 ✓ src/__tests__/nav.test.ts (10 tests) 19ms
 ✓ src/api.test.ts (4 tests) 39ms
stderr | src/__tests__/contrato/corrida-viva.contrato.test.tsx > Contrato: corrida viva > permite alcanzar la corrida activa desde una ruta distinta del listado
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/experiment-api.test.ts (4 tests) 34ms
 ✓ src/__tests__/charts/Meter.test.tsx (5 tests) 263ms
 ✓ src/__tests__/contrato/corrida-viva.contrato.test.tsx (2 tests) 792ms
   ✓ Contrato: corrida viva > permite alcanzar la corrida activa desde una ruta distinta del listado 544ms
 ✓ src/__tests__/ui/Select.test.tsx (5 tests) 627ms
stderr | src/__tests__/contrato/detalle-traza-evaluacion.contrato.test.tsx > Contrato: detalle, traza y evaluación > lee detalle y traza, permite inspeccionar cuadros y evaluar contra BENCH
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/PromptSetsPage.test.tsx (2 tests) 590ms
   ✓ PromptSetsPage > un set frozen se muestra read-only con acción Derivar 383ms
 ✓ src/__tests__/useSidebarCounts.test.ts (2 tests) 142ms
 ✓ src/__tests__/contrato/detalle-traza-evaluacion.contrato.test.tsx (1 test) 1177ms
   ✓ Contrato: detalle, traza y evaluación > lee detalle y traza, permite inspeccionar cuadros y evaluar contra BENCH 1174ms
 ✓ src/__tests__/stream.test.ts (3 tests) 24ms
stderr | src/__tests__/LiveRunPill.test.tsx > LiveRunPill > no renderiza nada si no hay corrida viva
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/preview.test.ts (2 tests) 12ms
 ✓ src/__tests__/LiveRunPill.test.tsx (3 tests) 248ms
 ✓ src/__tests__/ui/Button.test.tsx (5 tests) 282ms
 ✓ src/__tests__/ui/Banner.test.tsx (3 tests) 241ms
 ✓ src/__tests__/ui/Badge.test.tsx (4 tests) 153ms
stderr | src/__tests__/App.test.tsx > App > renderiza el título de la consola
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/App.test.tsx (2 tests) 362ms
 ✓ src/__tests__/ui/SegmentedControl.test.tsx (2 tests) 351ms
 ✓ src/__tests__/ui/ConditionName.test.tsx (3 tests) 92ms
 ✓ src/__tests__/ui/SearchInput.test.tsx (1 test) 82ms
 ✓ src/__tests__/ui/icons.test.tsx (1 test) 64ms
 ✓ src/__tests__/ui/InlineDeleteConfirm.test.tsx (2 tests) 252ms
 ✓ src/__tests__/ui/PageHeader.test.tsx (2 tests) 232ms
 ✓ src/__tests__/promptview.test.ts (3 tests) 8ms

 Test Files  59 passed (59)
      Tests  397 passed (397)
   Start at  02:15:20
   Duration  22.15s (transform 17.92s, setup 0ms, collect 75.41s, tests 71.07s, environment 115.10s, prepare 17.40s)

```

## Corte 0: compilación Python

```bash
cd /tmp/eovrt-cortes-validation/webconsole/backend && .venv/bin/python -m compileall -q src tests
```

Salida vacía; exit 0.

## Corte 1: build

```bash
cd /tmp/eovrt-cortes-validation/webconsole/frontend && npm run build
```

```text

> eovrt-webconsole-frontend@0.1.0 build
> tsc && vite build

vite v5.4.21 building for production...
transforming...
✓ 106 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.40 kB │ gzip:  0.27 kB
dist/assets/index-D1Xu6lb4.css   27.13 kB │ gzip:  5.78 kB
dist/assets/index-oHbTuLXw.js   283.39 kB │ gzip: 88.47 kB
✓ built in 1.35s
```

## Corte 1: frontend completo

```bash
cd /tmp/eovrt-cortes-validation/webconsole/frontend && npm test
```

```text

> eovrt-webconsole-frontend@0.1.0 test
> vitest run


 RUN  v2.1.9 /tmp/eovrt-cortes-validation/webconsole/frontend

stderr | src/__tests__/ExperimentDetailPageRiskBanner.test.tsx > ExperimentDetailPage — banner de riesgo activo > muestra el banner con el condition_id cuando patterns no esta vacio y el experimento corre
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ExperimentsPage.test.tsx > ExperimentsPage > lista manifiestos y dispara un experimento con preflight verde
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ExperimentDetailPage.test.tsx > ExperimentDetailPage > muestra las alertas y avisa que el conjunto no es temporal
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/TrimDialog.test.tsx (9 tests) 334ms
stderr | src/__tests__/ComposePage.test.tsx > ComposePage prefill > conserva active_ids del manifiesto y no lo pisan los defaults del set
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/RunsPage.test.tsx > RunsPage > lista corridas y marca la que está en curso
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ExperimentsPage.new.test.tsx > ExperimentsPage - crear nuevo experimento (/experiments/new) > abre el formulario con un selector "basado en" precargado con el primer manifiesto
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/RunDetailPage.test.tsx > RunDetailPage > muestra el estado de la corrida con el glosario, no con el código crudo
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/ExperimentDetailPageRiskBanner.test.tsx (7 tests) 358ms
stderr | src/__tests__/contrato/experimentos-distribucion.contrato.test.tsx > Contrato: experimentos y distribución > lista y abre un experimento con outcomes vinculados a cada alerta
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ComposePage.test.tsx > ComposePage prefill de source.type video > conserva el source.type original en la composición (round-trip sin colapso a video_file)
No routes matched location "/runs/r1"

stderr | src/__tests__/contrato/nueva-corrida.contrato.test.tsx > Contrato: nueva corrida > consulta preflight, compone fuente y prompts, lanza y abre el detalle real
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/ExperimentsPage.test.tsx (5 tests) 791ms
   ✓ ExperimentsPage > lista manifiestos y dispara un experimento con preflight verde 329ms
stderr | src/__tests__/ComposePage.test.tsx > ComposePage nombre opcional del run > manda run.name cuando se completa, null cuando se deja vacío
No routes matched location "/runs/r1"

stderr | src/__tests__/ComposePage.test.tsx > ComposePage nombre opcional del run > deja run.name en null si el campo queda vacío (usa el id autogenerado)
No routes matched location "/runs/r2"

 ✓ src/__tests__/DeriveExperimentForm.test.tsx (13 tests) 1257ms
 ✓ src/__tests__/ExperimentDetailPage.test.tsx (15 tests) 1335ms
 ✓ src/__tests__/ExperimentsPage.new.test.tsx (4 tests) 1505ms
   ✓ ExperimentsPage - crear nuevo experimento (/experiments/new) > abre el formulario con un selector "basado en" precargado con el primer manifiesto 501ms
   ✓ ExperimentsPage - crear nuevo experimento (/experiments/new) > al cambiar la fuente en el selector, vuelve a pedir los defaults y reprecarga los campos (bug central) 349ms
   ✓ ExperimentsPage - crear nuevo experimento (/experiments/new) > en modo nuevo la card dice "Nuevo experimento" y el botón "Crear" (no "Derivar de...") 388ms
 ✓ src/__tests__/ComparePage.test.tsx (14 tests) 1558ms
 ✓ src/__tests__/RunDetailPage.test.tsx (10 tests) 1431ms
   ✓ RunDetailPage > las pestañas separan traza, resumen, evaluación y archivos 343ms
 ✓ src/__tests__/contrato/experimentos-distribucion.contrato.test.tsx (4 tests) 1800ms
   ✓ Contrato: experimentos y distribución > lista y abre un experimento con outcomes vinculados a cada alerta 705ms
   ✓ Contrato: experimentos y distribución > deriva un manifiesto con overrides y lanza la derivación seleccionada 764ms
stderr | src/__tests__/Shell.test.tsx > Shell > renderiza los tres títulos de grupo
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ComposePage.test.tsx > ComposePage fuente RTSP > al elegir rtsp muestra el campo URL y arma config { url }
No routes matched location "/runs/r1"

stderr | src/__tests__/ComposePage.test.tsx > ComposePage cámara guardada (oak_d) > lanza con la config del preset de cámara elegido
No routes matched location "/runs/r1"

 ✓ src/__tests__/ComposePage.test.tsx (12 tests) 1948ms
   ✓ ComposePage nombre opcional del run > manda run.name cuando se completa, null cuando se deja vacío 301ms
 ✓ src/__tests__/TraceSection.test.tsx (10 tests) 2011ms
   ✓ TraceSection > no vuelca todos los cuadros: la lista se acota y dice el total 1098ms
 ✓ src/__tests__/Shell.test.tsx (17 tests) 2016ms
 ✓ src/__tests__/contrato/nueva-corrida.contrato.test.tsx (3 tests) 2213ms
   ✓ Contrato: nueva corrida > consulta preflight, compone fuente y prompts, lanza y abre el detalle real 1188ms
   ✓ Contrato: nueva corrida > impide lanzar con el formulario completo si el target aún no está listo 467ms
   ✓ Contrato: nueva corrida > muestra los bloqueos del preflight y permite lanzar sólo medios con target listo 555ms
 ✓ src/__tests__/RecordPanel.test.tsx (13 tests) 2831ms
   ✓ RecordPanel > mientras graba, consulta el backend periodicamente y muestra elapsed_ms/size_bytes de ahi 1101ms
   ✓ RecordPanel > si el backend informa error, deja de contar y muestra el motivo 1113ms
 ✓ src/__tests__/RunsPage.test.tsx (16 tests) 2686ms
   ✓ RunsPage > pagina el listado en vez de volcar todas las filas 808ms
 ✓ src/__tests__/api.test.ts (12 tests) 66ms
 ✓ src/__tests__/labels.test.ts (13 tests) 16ms
stderr | src/__tests__/CamerasPage.test.tsx > CamerasPage > lista los presets de cámara
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/traceview.test.ts (12 tests) 23ms
 ✓ src/__tests__/experimentview.test.ts (15 tests) 19ms
 ✓ src/__tests__/PreviewWithBoxes.test.tsx (8 tests) 212ms
stderr | src/__tests__/spec44c_gate.test.tsx > spec44c gate: flujo de experimentos por la UI > ExperimentsPage: lista un manifiesto y dispara runExperiment al hacer click en "Ejecutar experimento"
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/runview.test.ts (17 tests) 24ms
 ✓ src/__tests__/spec44c_gate.test.tsx (3 tests) 787ms
   ✓ spec44c gate: flujo de experimentos por la UI > ExperimentsPage: lista un manifiesto y dispara runExperiment al hacer click en "Ejecutar experimento" 502ms
 ✓ src/__tests__/PromptSetEditor.test.tsx (5 tests) 1392ms
   ✓ PromptSetEditor > exploratory: permite editar y guardar via updatePromptSet 600ms
 ✓ src/__tests__/runseries.test.ts (12 tests) 29ms
 ✓ src/__tests__/LiveViewer.test.tsx (4 tests) 350ms
 ✓ src/__tests__/useServiceHealth.test.ts (5 tests) 429ms
 ✓ src/__tests__/charts/timeline.test.ts (9 tests) 67ms
 ✓ src/__tests__/CamerasPage.test.tsx (7 tests) 1709ms
   ✓ CamerasPage > muestra banner y deshabilita conectar ante 409 run_active 417ms
   ✓ CamerasPage > activa por defecto las clases sin enabled_by_default declarado en el YAML 416ms
 ✓ src/__tests__/RunKpiStrip.test.tsx (7 tests) 756ms
   ✓ RunKpiStrip > rotula con el glosario, nunca con la clave cruda del sumario 329ms
 ✓ src/__tests__/charts/GroupedBars.test.tsx (8 tests) 386ms
 ✓ src/__tests__/ClipsPage.test.tsx (5 tests) 711ms
   ✓ ClipsPage > lista masters y clips 309ms
 ✓ src/__tests__/ui/Table.test.tsx (6 tests) 301ms
 ✓ src/__tests__/charts/layout.test.ts (9 tests) 28ms
 ✓ src/__tests__/PlatformPage.test.tsx (3 tests) 316ms
 ✓ src/__tests__/ui/primitives.test.tsx (10 tests) 300ms
 ✓ src/__tests__/nav.test.ts (10 tests) 21ms
 ✓ src/__tests__/EvalSection.test.tsx (4 tests) 358ms
 ✓ src/api.test.ts (4 tests) 22ms
 ✓ src/__tests__/experiment-api.test.ts (4 tests) 47ms
stderr | src/__tests__/contrato/detalle-traza-evaluacion.contrato.test.tsx > Contrato: detalle, traza y evaluación > lee detalle y traza, permite inspeccionar cuadros y evaluar contra BENCH
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/charts/Meter.test.tsx (5 tests) 262ms
 ✓ src/__tests__/ui/Select.test.tsx (5 tests) 673ms
   ✓ Select > abre la lista al hacer click en el control 319ms
stderr | src/__tests__/contrato/corrida-viva.contrato.test.tsx > Contrato: corrida viva > permite alcanzar la corrida activa desde una ruta distinta del listado
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/useSidebarCounts.test.ts (2 tests) 161ms
 ✓ src/__tests__/PromptSetsPage.test.tsx (2 tests) 580ms
   ✓ PromptSetsPage > un set frozen se muestra read-only con acción Derivar 361ms
 ✓ src/__tests__/contrato/corrida-viva.contrato.test.tsx (2 tests) 984ms
   ✓ Contrato: corrida viva > permite alcanzar la corrida activa desde una ruta distinta del listado 678ms
   ✓ Contrato: corrida viva > consulta mientras corre, permite detener y cesa el polling del detalle al terminar 303ms
 ✓ src/__tests__/contrato/detalle-traza-evaluacion.contrato.test.tsx (1 test) 1093ms
   ✓ Contrato: detalle, traza y evaluación > lee detalle y traza, permite inspeccionar cuadros y evaluar contra BENCH 1090ms
stderr | src/__tests__/LiveRunPill.test.tsx > LiveRunPill > no renderiza nada si no hay corrida viva
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/LiveRunPill.test.tsx (3 tests) 245ms
 ✓ src/__tests__/stream.test.ts (3 tests) 14ms
 ✓ src/__tests__/preview.test.ts (2 tests) 13ms
 ✓ src/__tests__/ui/Button.test.tsx (5 tests) 418ms
 ✓ src/__tests__/ui/Badge.test.tsx (4 tests) 112ms
stderr | src/__tests__/App.test.tsx > App > renderiza el título de la consola
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/ui/Banner.test.tsx (3 tests) 361ms
 ✓ src/__tests__/App.test.tsx (2 tests) 304ms
 ✓ src/__tests__/ui/SegmentedControl.test.tsx (2 tests) 300ms
 ✓ src/__tests__/promptview.test.ts (3 tests) 8ms
 ✓ src/__tests__/ui/InlineDeleteConfirm.test.tsx (2 tests) 289ms
 ✓ src/__tests__/ui/ConditionName.test.tsx (3 tests) 102ms
 ✓ src/__tests__/ui/icons.test.tsx (1 test) 87ms
 ✓ src/__tests__/ui/PageHeader.test.tsx (2 tests) 287ms
 ✓ src/__tests__/ui/SearchInput.test.tsx (1 test) 71ms

 Test Files  59 passed (59)
      Tests  397 passed (397)
   Start at  02:16:35
   Duration  14.69s (transform 5.95s, setup 0ms, collect 35.56s, tests 38.81s, environment 87.58s, prepare 13.93s)

```

## Corte 1: compilación Python

```bash
cd /tmp/eovrt-cortes-validation/webconsole/backend && .venv/bin/python -m compileall -q src tests
```

Salida vacía; exit 0.

## Corte 2: build

```bash
cd /tmp/eovrt-cortes-validation/webconsole/frontend && npm run build
```

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
✓ built in 2.45s
```

## Corte 2: frontend completo

```bash
cd /tmp/eovrt-cortes-validation/webconsole/frontend && npm test
```

```text

> eovrt-webconsole-frontend@0.1.0 test
> vitest run


 RUN  v2.1.9 /tmp/eovrt-cortes-validation/webconsole/frontend

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

 ✓ src/__tests__/TrimDialog.test.tsx (9 tests) 593ms
stderr | src/__tests__/ExperimentsPage.new.test.tsx > ExperimentsPage - crear nuevo experimento (/experiments/new) > abre el formulario con un selector "basado en" precargado con el primer manifiesto
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/RunDetailPage.test.tsx > RunDetailPage > muestra el estado de la corrida con el glosario, no con el código crudo
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/RunsPage.test.tsx > RunsPage > lista corridas y marca la que está en curso
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/ExperimentDetailPageRiskBanner.test.tsx (7 tests) 586ms
stderr | src/__tests__/contrato/experimentos-distribucion.contrato.test.tsx > Contrato: experimentos y distribución > lista y abre un experimento con outcomes vinculados a cada alerta
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ComposePage.test.tsx > ComposePage prefill de source.type video > conserva el source.type original en la composición (round-trip sin colapso a video_file)
No routes matched location "/runs/r1"

stderr | src/__tests__/contrato/nueva-corrida.contrato.test.tsx > Contrato: nueva corrida > consulta preflight, compone fuente y prompts, lanza y abre el detalle real
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/ExperimentsPage.test.tsx (5 tests) 1132ms
   ✓ ExperimentsPage > lista manifiestos y dispara un experimento con preflight verde 484ms
stderr | src/__tests__/ComposePage.test.tsx > ComposePage nombre opcional del run > manda run.name cuando se completa, null cuando se deja vacío
No routes matched location "/runs/r1"

 ✓ src/__tests__/ExperimentDetailPage.test.tsx (15 tests) 1464ms
stderr | src/__tests__/ComposePage.test.tsx > ComposePage nombre opcional del run > deja run.name en null si el campo queda vacío (usa el id autogenerado)
No routes matched location "/runs/r2"

 ✓ src/__tests__/DeriveExperimentForm.test.tsx (13 tests) 1865ms
 ✓ src/__tests__/ExperimentsPage.new.test.tsx (4 tests) 1921ms
   ✓ ExperimentsPage - crear nuevo experimento (/experiments/new) > abre el formulario con un selector "basado en" precargado con el primer manifiesto 711ms
   ✓ ExperimentsPage - crear nuevo experimento (/experiments/new) > al cambiar la fuente en el selector, vuelve a pedir los defaults y reprecarga los campos (bug central) 528ms
   ✓ ExperimentsPage - crear nuevo experimento (/experiments/new) > en modo nuevo la card dice "Nuevo experimento" y el botón "Crear" (no "Derivar de...") 399ms
 ✓ src/__tests__/ComparePage.test.tsx (14 tests) 2026ms
   ✓ ComparePage > lista las corridas por nombre, no por identificador crudo 384ms
   ✓ ComparePage > compara al elegir dos y nombra las métricas en español 397ms
 ✓ src/__tests__/RunDetailPage.test.tsx (10 tests) 1801ms
   ✓ RunDetailPage > las pestañas separan traza, resumen, evaluación y archivos 421ms
stderr | src/__tests__/ComposePage.test.tsx > ComposePage fuente RTSP > al elegir rtsp muestra el campo URL y arma config { url }
No routes matched location "/runs/r1"

stderr | src/__tests__/Shell.test.tsx > Shell > renderiza los tres títulos de grupo
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ComposePage.test.tsx > ComposePage cámara guardada (oak_d) > lanza con la config del preset de cámara elegido
No routes matched location "/runs/r1"

 ✓ src/__tests__/ComposePage.test.tsx (12 tests) 2509ms
   ✓ ComposePage prefill > conserva active_ids del manifiesto y no lo pisan los defaults del set 456ms
   ✓ ComposePage prefill de source.type video > conserva el source.type original en la composición (round-trip sin colapso a video_file) 321ms
 ✓ src/__tests__/contrato/experimentos-distribucion.contrato.test.tsx (4 tests) 2571ms
   ✓ Contrato: experimentos y distribución > lista y abre un experimento con outcomes vinculados a cada alerta 1233ms
   ✓ Contrato: experimentos y distribución > deriva un manifiesto con overrides y lanza la derivación seleccionada 919ms
   ✓ Contrato: experimentos y distribución > seleccionar dos corridas evaluadas pide su comparación por HTTP 306ms
 ✓ src/__tests__/TraceSection.test.tsx (10 tests) 2728ms
   ✓ TraceSection > no vuelca todos los cuadros: la lista se acota y dice el total 1638ms
 ✓ src/__tests__/Shell.test.tsx (17 tests) 2720ms
   ✓ Shell > acorta la etiqueta que no entra, sin perder el nombre completo 385ms
 ✓ src/__tests__/RecordPanel.test.tsx (13 tests) 3497ms
   ✓ RecordPanel > mientras graba, consulta el backend periodicamente y muestra elapsed_ms/size_bytes de ahi 1130ms
   ✓ RecordPanel > si el backend informa error, deja de contar y muestra el motivo 1234ms
 ✓ src/__tests__/contrato/nueva-corrida.contrato.test.tsx (3 tests) 3054ms
   ✓ Contrato: nueva corrida > consulta preflight, compone fuente y prompts, lanza y abre el detalle real 1687ms
   ✓ Contrato: nueva corrida > impide lanzar con el formulario completo si el target aún no está listo 568ms
   ✓ Contrato: nueva corrida > muestra los bloqueos del preflight y permite lanzar sólo medios con target listo 793ms
 ✓ src/__tests__/RunsPage.test.tsx (16 tests) 3660ms
   ✓ RunsPage > lista corridas y marca la que está en curso 603ms
   ✓ RunsPage > pagina el listado en vez de volcar todas las filas 943ms
 ✓ src/__tests__/api.test.ts (12 tests) 70ms
 ✓ src/__tests__/labels.test.ts (13 tests) 25ms
stderr | src/__tests__/CamerasPage.test.tsx > CamerasPage > lista los presets de cámara
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/traceview.test.ts (12 tests) 32ms
 ✓ src/__tests__/experimentview.test.ts (15 tests) 26ms
 ✓ src/__tests__/runview.test.ts (17 tests) 34ms
 ✓ src/__tests__/PreviewWithBoxes.test.tsx (8 tests) 453ms
stderr | src/__tests__/spec44c_gate.test.tsx > spec44c gate: flujo de experimentos por la UI > ExperimentsPage: lista un manifiesto y dispara runExperiment al hacer click en "Ejecutar experimento"
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/runseries.test.ts (12 tests) 34ms
 ✓ src/__tests__/PromptSetEditor.test.tsx (5 tests) 1287ms
   ✓ PromptSetEditor > exploratory: permite editar y guardar via updatePromptSet 600ms
 ✓ src/__tests__/useServiceHealth.test.ts (5 tests) 389ms
 ✓ src/__tests__/CamerasPage.test.tsx (7 tests) 1890ms
   ✓ CamerasPage > lista los presets de cámara 349ms
   ✓ CamerasPage > muestra banner y deshabilita conectar ante 409 run_active 517ms
   ✓ CamerasPage > activa por defecto las clases sin enabled_by_default declarado en el YAML 372ms
 ✓ src/__tests__/spec44c_gate.test.tsx (3 tests) 732ms
   ✓ spec44c gate: flujo de experimentos por la UI > ExperimentsPage: lista un manifiesto y dispara runExperiment al hacer click en "Ejecutar experimento" 513ms
 ✓ src/__tests__/LiveViewer.test.tsx (4 tests) 212ms
 ✓ src/__tests__/charts/timeline.test.ts (9 tests) 86ms
 ✓ src/__tests__/RunKpiStrip.test.tsx (7 tests) 763ms
 ✓ src/__tests__/charts/GroupedBars.test.tsx (8 tests) 393ms
 ✓ src/__tests__/ClipsPage.test.tsx (5 tests) 563ms
 ✓ src/__tests__/ui/Table.test.tsx (6 tests) 423ms
 ✓ src/__tests__/charts/layout.test.ts (9 tests) 24ms
 ✓ src/__tests__/ui/primitives.test.tsx (10 tests) 412ms
 ✓ src/__tests__/PlatformPage.test.tsx (3 tests) 380ms
 ✓ src/__tests__/nav.test.ts (10 tests) 29ms
 ✓ src/__tests__/EvalSection.test.tsx (4 tests) 574ms
 ✓ src/api.test.ts (4 tests) 33ms
 ✓ src/__tests__/queryClient.test.ts (4 tests) 29ms
 ✓ src/__tests__/ui/Select.test.tsx (5 tests) 639ms
   ✓ Select > abre la lista al hacer click en el control 333ms
 ✓ src/__tests__/charts/Meter.test.tsx (5 tests) 349ms
 ✓ src/__tests__/experiment-api.test.ts (4 tests) 54ms
stderr | src/__tests__/contrato/detalle-traza-evaluacion.contrato.test.tsx > Contrato: detalle, traza y evaluación > lee detalle y traza, permite inspeccionar cuadros y evaluar contra BENCH
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/contrato/corrida-viva.contrato.test.tsx > Contrato: corrida viva > permite alcanzar la corrida activa desde una ruta distinta del listado
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/PromptSetsPage.test.tsx (2 tests) 665ms
   ✓ PromptSetsPage > un set frozen se muestra read-only con acción Derivar 420ms
 ✓ src/__tests__/contrato/corrida-viva.contrato.test.tsx (2 tests) 1301ms
   ✓ Contrato: corrida viva > permite alcanzar la corrida activa desde una ruta distinta del listado 955ms
   ✓ Contrato: corrida viva > consulta mientras corre, permite detener y cesa el polling del detalle al terminar 341ms
 ✓ src/__tests__/contrato/detalle-traza-evaluacion.contrato.test.tsx (1 test) 1387ms
   ✓ Contrato: detalle, traza y evaluación > lee detalle y traza, permite inspeccionar cuadros y evaluar contra BENCH 1377ms
 ✓ src/__tests__/useSidebarCounts.test.ts (2 tests) 155ms
stderr | src/__tests__/LiveRunPill.test.tsx > LiveRunPill > no renderiza nada si no hay corrida viva
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/stream.test.ts (3 tests) 26ms
 ✓ src/__tests__/LiveRunPill.test.tsx (3 tests) 428ms
 ✓ src/__tests__/preview.test.ts (2 tests) 16ms
 ✓ src/__tests__/ui/Button.test.tsx (5 tests) 373ms
 ✓ src/__tests__/ui/Banner.test.tsx (3 tests) 334ms
stderr | src/__tests__/App.test.tsx > App > renderiza el título de la consola
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/App.test.tsx (2 tests) 353ms
 ✓ src/__tests__/ui/Badge.test.tsx (4 tests) 144ms
 ✓ src/__tests__/ui/SegmentedControl.test.tsx (2 tests) 307ms
 ✓ src/__tests__/ui/InlineDeleteConfirm.test.tsx (2 tests) 295ms
 ✓ src/__tests__/ui/ConditionName.test.tsx (3 tests) 95ms
 ✓ src/__tests__/ui/PageHeader.test.tsx (2 tests) 270ms
 ✓ src/__tests__/promptview.test.ts (3 tests) 9ms
 ✓ src/__tests__/ui/SearchInput.test.tsx (1 test) 110ms
 ✓ src/__tests__/ui/icons.test.tsx (1 test) 101ms

 Test Files  60 passed (60)
      Tests  401 passed (401)
   Start at  02:21:35
   Duration  19.13s (transform 6.57s, setup 0ms, collect 46.54s, tests 48.43s, environment 117.24s, prepare 18.37s)

```

## Corte 2: compilación Python

```bash
cd /tmp/eovrt-cortes-validation/webconsole/backend && .venv/bin/python -m compileall -q src tests
```

Salida vacía; exit 0.

## Corte 3: build

```bash
cd /tmp/eovrt-cortes-validation/webconsole/frontend && npm run build
```

```text

> eovrt-webconsole-frontend@0.1.0 build
> tsc && vite build

vite v5.4.21 building for production...
transforming...
✓ 162 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.40 kB │ gzip:   0.27 kB
dist/assets/index-BvOvplTA.css   35.35 kB │ gzip:   7.07 kB
dist/assets/index-lpqrC_Ib.js   388.64 kB │ gzip: 118.20 kB
✓ built in 1.54s
```

## Corte 3: frontend completo

```bash
cd /tmp/eovrt-cortes-validation/webconsole/frontend && npm test
```

```text

> eovrt-webconsole-frontend@0.1.0 test
> vitest run


 RUN  v2.1.9 /tmp/eovrt-cortes-validation/webconsole/frontend

 ✓ src/__tests__/api.test.ts (15 tests) 38ms
 ✓ src/__tests__/TrimDialog.test.tsx (9 tests) 336ms
stderr | src/__tests__/ExperimentDetailPageRiskBanner.test.tsx > ExperimentDetailPage — banner de riesgo activo > muestra el banner con el condition_id cuando patterns no esta vacio y el experimento corre
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/RunsPage.test.tsx > RunsPage > lista corridas y marca la que está en curso
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ExperimentsPage.test.tsx > ExperimentsPage > lista manifiestos y dispara un experimento con preflight verde
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ExperimentDetailPage.test.tsx > ExperimentDetailPage > muestra las alertas y avisa que el conjunto no es temporal
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/CamerasPage.test.tsx > CamerasPage > lista los presets de cámara
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/RunDetailPage.test.tsx > RunDetailPage > muestra el estado de la corrida con el glosario, no con el código crudo
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ComposePage.test.tsx > ComposePage prefill > conserva active_ids del manifiesto y no lo pisan los defaults del set
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/ExperimentDetailPageRiskBanner.test.tsx (7 tests) 366ms
stderr | src/__tests__/contrato/experimentos-distribucion.contrato.test.tsx > Contrato: experimentos y distribución > lista y abre un experimento con outcomes vinculados a cada alerta
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/ExperimentsPage.test.tsx (5 tests) 711ms
 ✓ src/__tests__/ExperimentDetailPage.test.tsx (15 tests) 960ms
 ✓ src/__tests__/DeriveExperimentForm.test.tsx (13 tests) 1069ms
stderr | src/__tests__/ComposePage.test.tsx > ComposePage prefill de source.type video > conserva el source.type original en la composición (round-trip sin colapso a video_file)
No routes matched location "/runs/r1"

 ✓ src/__tests__/RunDetailPage.test.tsx (10 tests) 1173ms
 ✓ src/__tests__/ComparePage.test.tsx (14 tests) 1405ms
stderr | src/__tests__/ExperimentsPage.new.test.tsx > ExperimentsPage - crear nuevo experimento (/experiments/new) > abre el formulario con un selector "basado en" precargado con el primer manifiesto
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/Shell.test.tsx > Shell > renderiza los tres títulos de grupo
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/contrato/experimentos-distribucion.contrato.test.tsx (4 tests) 1515ms
   ✓ Contrato: experimentos y distribución > lista y abre un experimento con outcomes vinculados a cada alerta 635ms
   ✓ Contrato: experimentos y distribución > deriva un manifiesto con overrides y lanza la derivación seleccionada 601ms
 ✓ src/__tests__/Shell.test.tsx (17 tests) 1762ms
 ✓ src/__tests__/TraceSection.test.tsx (10 tests) 1864ms
   ✓ TraceSection > no vuelca todos los cuadros: la lista se acota y dice el total 967ms
 ✓ src/__tests__/CamerasPage.test.tsx (14 tests) 1937ms
   ✓ CamerasPage > muestra banner y deshabilita conectar ante 409 run_active 310ms
stderr | src/__tests__/ComposePage.test.tsx > ComposePage nombre opcional de la corrida > manda run.name cuando se completa, null cuando se deja vacío
No routes matched location "/runs/r1"

stderr | src/__tests__/ComposePage.test.tsx > ComposePage nombre opcional de la corrida > deja run.name en null si el campo queda vacío (usa el id autogenerado)
No routes matched location "/runs/r2"

 ✓ src/__tests__/ExperimentsPage.new.test.tsx (4 tests) 1082ms
   ✓ ExperimentsPage - crear nuevo experimento (/experiments/new) > abre el formulario con un selector "basado en" precargado con el primer manifiesto 434ms
 ✓ src/__tests__/RecordPanel.test.tsx (13 tests) 2817ms
   ✓ RecordPanel > mientras graba, consulta el backend periodicamente y muestra elapsed_ms/size_bytes de ahi 1063ms
   ✓ RecordPanel > si el backend informa error, deja de contar y muestra el motivo 1082ms
 ✓ src/__tests__/labels.test.ts (13 tests) 26ms
stderr | src/__tests__/contrato/nueva-corrida.contrato.test.tsx > Contrato: nueva corrida > consulta preflight, compone fuente y prompts, lanza y abre el detalle real
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/LiveViewer.test.tsx (5 tests) 158ms
 ✓ src/__tests__/traceview.test.ts (12 tests) 19ms
stderr | src/__tests__/spec44c_gate.test.tsx > spec44c gate: flujo de experimentos por la UI > ExperimentsPage: lista un manifiesto y dispara runExperiment al hacer click en "Ejecutar experimento"
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/PromptSetEditor.test.tsx (5 tests) 709ms
   ✓ PromptSetEditor > exploratory: permite editar y guardar via updatePromptSet 308ms
 ✓ src/__tests__/experimentview.test.ts (15 tests) 14ms
 ✓ src/__tests__/PreviewWithBoxes.test.tsx (8 tests) 170ms
 ✓ src/__tests__/runview.test.ts (17 tests) 23ms
 ✓ src/__tests__/spec44c_gate.test.tsx (3 tests) 559ms
 ✓ src/__tests__/RunsPage.test.tsx (22 tests) 4091ms
   ✓ RunsPage > lista corridas y marca la que está en curso 334ms
   ✓ RunsPage > el pedido de la página lleva el filtro, el orden y la página al servidor 820ms
   ✓ RunsPage > el buscador manda `q` al servidor en vez de filtrar en el cliente 714ms
 ✓ src/__tests__/contrato/nueva-corrida.contrato.test.tsx (3 tests) 1918ms
   ✓ Contrato: nueva corrida > consulta preflight, compone fuente y prompts, lanza y abre el detalle real 963ms
   ✓ Contrato: nueva corrida > impide lanzar con el formulario completo si el target aún no está listo 431ms
   ✓ Contrato: nueva corrida > muestra los bloqueos del preflight y permite lanzar sólo medios con target listo 522ms
 ✓ src/__tests__/charts/ActivityTimeline.test.tsx (7 tests) 401ms
 ✓ src/__tests__/useServiceHealth.test.ts (5 tests) 380ms
 ✓ src/__tests__/charts/GroupedBars.test.tsx (8 tests) 219ms
 ✓ src/__tests__/RunKpiStrip.test.tsx (7 tests) 378ms
 ✓ src/__tests__/runseries.test.ts (12 tests) 14ms
stderr | src/__tests__/RunDetailArtifacts.test.tsx > expone el inventario limitado del servicio anterior con descargas verificadas
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/charts/timeline.test.ts (9 tests) 29ms
stderr | src/__tests__/ComposePage.test.tsx > ComposePage fuente RTSP > al elegir rtsp muestra el campo de dirección y arma config { url }
No routes matched location "/runs/r1"

 ✓ src/__tests__/ui/Table.test.tsx (6 tests) 270ms
 ✓ src/__tests__/ClipsPage.test.tsx (5 tests) 332ms
 ✓ src/__tests__/RunDetailArtifacts.test.tsx (3 tests) 981ms
   ✓ expone el inventario limitado del servicio anterior con descargas verificadas 468ms
   ✓ actualiza los archivos después de evaluar sin recargar el detalle 345ms
stderr | src/__tests__/ComposePage.test.tsx > ComposePage cámara guardada (oak_d) > lanza con la config de la cámara guardada elegida
No routes matched location "/runs/r1"

 ✓ src/__tests__/ComposePage.test.tsx (18 tests) 5976ms
   ✓ ComposePage prefill > conserva active_ids del manifiesto y no lo pisan los defaults del set 696ms
   ✓ ComposePage prefill de source.type video > conserva el source.type original en la composición (round-trip sin colapso a video_file) 449ms
   ✓ ComposePage prefill survives catalog re-fetch (no clobber) > no reaplica el manifiesto cuando `experiments` cambia de referencia tras un re-fetch 450ms
   ✓ ComposePage nombre opcional de la corrida > manda run.name cuando se completa, null cuando se deja vacío 349ms
   ✓ ComposePage nombre opcional de la corrida > deja run.name en null si el campo queda vacío (usa el id autogenerado) 324ms
   ✓ ComposePage aviso de 409 al lanzar > muestra aviso de prueba de cámara activa ante 409 preview_active 348ms
   ✓ ComposePage aviso de 409 al lanzar > muestra aviso de corrida activa ante 409 con active_run_id 357ms
   ✓ ComposePage panel «Antes de lanzar» > los requisitos se van cumpliendo y el botón se habilita al final 338ms
   ✓ ComposePage panel «Antes de lanzar» > desactivar todas las clases vuelve a bloquear, diciendo qué falta 553ms
   ✓ ComposePage fuente RTSP > bloquea el lanzamiento si la dirección RTSP trae credenciales censuradas (***) 345ms
   ✓ ComposePage fuente RTSP > al elegir rtsp muestra el campo de dirección y arma config { url } 343ms
   ✓ ComposePage cámara guardada (oak_d) > lanza con la config de la cámara guardada elegida 458ms
 ✓ src/__tests__/TraceQueries.final.test.tsx (1 test) 79ms
 ✓ src/__tests__/charts/layout.test.ts (9 tests) 14ms
stderr | src/__tests__/ComposePage.preflight.test.tsx > ComposePage: bloqueos de preflight > informa los motivos con ready=false sin bloquear DBE y los actualiza por polling
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/PlatformPage.test.tsx (3 tests) 247ms
 ✓ src/__tests__/ui/primitives.test.tsx (10 tests) 274ms
 ✓ src/__tests__/EvalSection.test.tsx (4 tests) 212ms
 ✓ src/__tests__/nav.test.ts (10 tests) 17ms
stderr | src/__tests__/contrato/corrida-viva.contrato.test.tsx > Contrato: corrida viva > permite alcanzar la corrida activa desde una ruta distinta del listado
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/ComposePage.preflight.test.tsx (2 tests) 1345ms
   ✓ ComposePage: bloqueos de preflight > informa los motivos con ready=false sin bloquear DBE y los actualiza por polling 916ms
   ✓ ComposePage: bloqueos de preflight > informa los motivos con ready=true sin bloquear DBE y los actualiza por polling 427ms
stderr | src/__tests__/contrato/detalle-traza-evaluacion.contrato.test.tsx > Contrato: detalle, traza y evaluación > lee detalle y traza, permite inspeccionar cuadros y evaluar contra BENCH
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/ui/Select.test.tsx (5 tests) 343ms
 ✓ src/__tests__/PromptSetsPage.test.tsx (2 tests) 347ms
 ✓ src/__tests__/contrato/corrida-viva.contrato.test.tsx (2 tests) 877ms
   ✓ Contrato: corrida viva > permite alcanzar la corrida activa desde una ruta distinta del listado 491ms
   ✓ Contrato: corrida viva > consulta mientras corre, permite detener y cesa el polling del detalle al terminar 383ms
 ✓ src/__tests__/queryClient.test.ts (4 tests) 8ms
 ✓ src/__tests__/api.endpoints.test.ts (4 tests) 19ms
 ✓ src/__tests__/experiment-api.test.ts (4 tests) 26ms
 ✓ src/__tests__/charts/Meter.test.tsx (5 tests) 205ms
 ✓ src/__tests__/contrato/detalle-traza-evaluacion.contrato.test.tsx (1 test) 871ms
   ✓ Contrato: detalle, traza y evaluación > lee detalle y traza, permite inspeccionar cuadros y evaluar contra BENCH 869ms
 ✓ src/__tests__/useSidebarCounts.test.ts (2 tests) 148ms
stderr | src/__tests__/LiveRunPill.test.tsx > LiveRunPill > no renderiza nada si no hay corrida viva
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/LiveRunPill.test.tsx (3 tests) 278ms
 ✓ src/__tests__/stream.test.ts (3 tests) 18ms
 ✓ src/__tests__/ui/Button.test.tsx (5 tests) 274ms
stderr | src/__tests__/App.test.tsx > App > renderiza el título de la consola
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/App.test.tsx (2 tests) 296ms
 ✓ src/__tests__/preview.test.ts (2 tests) 16ms
 ✓ src/__tests__/ui/Banner.test.tsx (3 tests) 218ms
 ✓ src/__tests__/ui/Badge.test.tsx (4 tests) 78ms
 ✓ src/__tests__/ui/SegmentedControl.test.tsx (2 tests) 173ms
 ✓ src/__tests__/ui/Select.field.test.tsx (1 test) 190ms
 ✓ src/__tests__/ui/InlineDeleteConfirm.test.tsx (2 tests) 174ms
 ✓ src/__tests__/ui/ConditionName.test.tsx (3 tests) 70ms
 ✓ src/__tests__/ui/PageHeader.test.tsx (2 tests) 177ms
 ✓ src/__tests__/promptview.test.ts (3 tests) 6ms
 ✓ src/__tests__/ui/SearchInput.test.tsx (1 test) 61ms
 ✓ src/__tests__/ui/icons.test.tsx (1 test) 53ms
stderr | src/__tests__/CamerasPage.preview-error.test.tsx > muestra el fallo del sondeo de preview sin rechazar una promesa sin manejar
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/CamerasPage.preview-error.test.tsx (1 test) 146ms

 Test Files  66 passed (66)
      Tests  439 passed (439)
   Start at  02:24:19
   Duration  13.11s (transform 5.33s, setup 0ms, collect 33.45s, tests 40.96s, environment 73.43s, prepare 11.93s)

```

## Corte 3: compilación Python

```bash
cd /tmp/eovrt-cortes-validation/webconsole/backend && .venv/bin/python -m compileall -q src tests
```

Salida vacía; exit 0.

## Corte 4: build

```bash
cd /tmp/eovrt-cortes-validation/webconsole/frontend && npm run build
```

```text

> eovrt-webconsole-frontend@0.1.0 build
> tsc && vite build

vite v5.4.21 building for production...
transforming...
✓ 162 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.40 kB │ gzip:   0.27 kB
dist/assets/index-BvOvplTA.css   35.35 kB │ gzip:   7.07 kB
dist/assets/index-DiYFhCsP.js   396.38 kB │ gzip: 120.34 kB
✓ built in 1.59s
```

## Corte 4: frontend completo

```bash
cd /tmp/eovrt-cortes-validation/webconsole/frontend && npm test
```

```text

> eovrt-webconsole-frontend@0.1.0 test
> vitest run


 RUN  v2.1.9 /tmp/eovrt-cortes-validation/webconsole/frontend

 ✓ src/__tests__/api.test.ts (15 tests) 179ms
stderr | src/__tests__/ExperimentDetailPageRiskBanner.test.tsx > ExperimentDetailPage — banner de riesgo activo > muestra el banner con el condition_id cuando patterns no esta vacio y el experimento corre
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ExperimentsPage.test.tsx > ExperimentsPage > lista manifiestos y dispara un experimento con preflight verde
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ExperimentDetailPage.test.tsx > ExperimentDetailPage > muestra las alertas y avisa que el conjunto no es temporal
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/RunsPage.test.tsx > RunsPage > lista corridas y marca la que está en curso
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/TrimDialog.test.tsx (9 tests) 307ms
stderr | src/__tests__/contrato/experimentos-distribucion.contrato.test.tsx > Contrato: experimentos y distribución > lista y abre un experimento con outcomes vinculados a cada alerta
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/CamerasPage.test.tsx > CamerasPage > lista los presets de cámara
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ComposePage.test.tsx > ComposePage prefill > conserva active_ids del manifiesto y no lo pisan los defaults del set
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/RunDetailPage.test.tsx > RunDetailPage > muestra el estado de la corrida con el glosario, no con el código crudo
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/ExperimentDetailPageRiskBanner.test.tsx (7 tests) 418ms
 ✓ src/__tests__/ExperimentsPage.test.tsx (5 tests) 860ms
   ✓ ExperimentsPage > lista manifiestos y dispara un experimento con preflight verde 303ms
 ✓ src/__tests__/PromptSetsPage.test.tsx (7 tests) 1019ms
 ✓ src/__tests__/ExperimentDetailPage.test.tsx (15 tests) 1049ms
 ✓ src/__tests__/DeriveExperimentForm.test.tsx (13 tests) 1068ms
stderr | src/__tests__/ComposePage.test.tsx > ComposePage prefill de source.type video > conserva el source.type original en la composición (round-trip sin colapso a video_file)
No routes matched location "/runs/r1"

 ✓ src/__tests__/ComparePage.test.tsx (14 tests) 1400ms
 ✓ src/__tests__/contrato/experimentos-distribucion.contrato.test.tsx (4 tests) 1487ms
   ✓ Contrato: experimentos y distribución > lista y abre un experimento con outcomes vinculados a cada alerta 644ms
   ✓ Contrato: experimentos y distribución > deriva un manifiesto con overrides y lanza la derivación seleccionada 552ms
stderr | src/__tests__/Shell.test.tsx > Shell > renderiza los tres títulos de grupo
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/RunDetailPage.test.tsx (10 tests) 1418ms
 ✓ src/__tests__/Shell.test.tsx (17 tests) 1789ms
stderr | src/__tests__/ComposePage.test.tsx > ComposePage nombre opcional de la corrida > manda run.name cuando se completa, null cuando se deja vacío
No routes matched location "/runs/r1"

 ✓ src/__tests__/CamerasPage.test.tsx (14 tests) 1996ms
   ✓ CamerasPage > muestra banner y deshabilita conectar ante 409 run_active 320ms
stderr | src/__tests__/ComposePage.test.tsx > ComposePage nombre opcional de la corrida > deja run.name en null si el campo queda vacío (usa el id autogenerado)
No routes matched location "/runs/r2"

 ✓ src/__tests__/RecordPanel.test.tsx (13 tests) 2872ms
   ✓ RecordPanel > mientras graba, consulta el backend periodicamente y muestra elapsed_ms/size_bytes de ahi 1086ms
   ✓ RecordPanel > si el backend informa error, deja de contar y muestra el motivo 1107ms
stderr | src/__tests__/ExperimentsPage.new.test.tsx > ExperimentsPage - crear nuevo experimento (/experiments/new) > abre el formulario con un selector "basado en" precargado con el primer manifiesto
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/labels.test.ts (13 tests) 20ms
 ✓ src/__tests__/TraceSection.test.tsx (10 tests) 2046ms
   ✓ TraceSection > no vuelca todos los cuadros: la lista se acota y dice el total 1072ms
stderr | src/__tests__/contrato/nueva-corrida.contrato.test.tsx > Contrato: nueva corrida > consulta preflight, compone fuente y prompts, lanza y abre el detalle real
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/LiveViewer.test.tsx (5 tests) 180ms
 ✓ src/__tests__/traceview.test.ts (12 tests) 13ms
stderr | src/__tests__/spec44c_gate.test.tsx > spec44c gate: flujo de experimentos por la UI > ExperimentsPage: lista un manifiesto y dispara runExperiment al hacer click en "Ejecutar experimento"
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/ExperimentsPage.new.test.tsx (4 tests) 1278ms
   ✓ ExperimentsPage - crear nuevo experimento (/experiments/new) > abre el formulario con un selector "basado en" precargado con el primer manifiesto 559ms
 ✓ src/__tests__/experimentview.test.ts (15 tests) 13ms
 ✓ src/__tests__/PreviewWithBoxes.test.tsx (8 tests) 187ms
 ✓ src/__tests__/PlatformPage.test.tsx (6 tests) 626ms
   ✓ PlatformPage > lista el fleet y activa una instancia 326ms
 ✓ src/__tests__/PromptSetEditor.test.tsx (5 tests) 666ms
 ✓ src/__tests__/spec44c_gate.test.tsx (3 tests) 546ms
   ✓ spec44c gate: flujo de experimentos por la UI > ExperimentsPage: lista un manifiesto y dispara runExperiment al hacer click en "Ejecutar experimento" 387ms
 ✓ src/__tests__/RunsPage.test.tsx (22 tests) 4495ms
   ✓ RunsPage > el pedido de la página lleva el filtro, el orden y la página al servidor 738ms
   ✓ RunsPage > el buscador manda `q` al servidor en vez de filtrar en el cliente 779ms
   ✓ RunsPage > el segmentado manda `estado` al servidor 309ms
   ✓ RunsPage > el total es el del servidor, no la cantidad de filas de la página 384ms
 ✓ src/__tests__/charts/ActivityTimeline.test.tsx (7 tests) 385ms
 ✓ src/__tests__/runview.test.ts (17 tests) 15ms
 ✓ src/__tests__/contrato/nueva-corrida.contrato.test.tsx (3 tests) 2050ms
   ✓ Contrato: nueva corrida > consulta preflight, compone fuente y prompts, lanza y abre el detalle real 1185ms
   ✓ Contrato: nueva corrida > impide lanzar con el formulario completo si el target aún no está listo 405ms
   ✓ Contrato: nueva corrida > muestra los bloqueos del preflight y permite lanzar sólo medios con target listo 458ms
 ✓ src/__tests__/useServiceHealth.test.ts (5 tests) 396ms
 ✓ src/__tests__/runseries.test.ts (12 tests) 15ms
stderr | src/__tests__/ComposePage.test.tsx > ComposePage fuente RTSP > al elegir rtsp muestra el campo de dirección y arma config { url }
No routes matched location "/runs/r1"

 ✓ src/__tests__/charts/GroupedBars.test.tsx (8 tests) 273ms
 ✓ src/__tests__/RunKpiStrip.test.tsx (7 tests) 392ms
 ✓ src/__tests__/charts/timeline.test.ts (9 tests) 44ms
stderr | src/__tests__/RunDetailArtifacts.test.tsx > expone el inventario limitado del servicio anterior con descargas verificadas
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ComposePage.test.tsx > ComposePage cámara guardada (oak_d) > lanza con la config de la cámara guardada elegida
No routes matched location "/runs/r1"

 ✓ src/__tests__/ComposePage.test.tsx (18 tests) 6215ms
   ✓ ComposePage prefill > conserva active_ids del manifiesto y no lo pisan los defaults del set 650ms
   ✓ ComposePage prefill de source.type video > conserva el source.type original en la composición (round-trip sin colapso a video_file) 474ms
   ✓ ComposePage prefill survives catalog re-fetch (no clobber) > no reaplica el manifiesto cuando `experiments` cambia de referencia tras un re-fetch 378ms
   ✓ ComposePage nombre opcional de la corrida > manda run.name cuando se completa, null cuando se deja vacío 391ms
   ✓ ComposePage nombre opcional de la corrida > deja run.name en null si el campo queda vacío (usa el id autogenerado) 520ms
   ✓ ComposePage aviso de 409 al lanzar > muestra aviso de prueba de cámara activa ante 409 preview_active 438ms
   ✓ ComposePage aviso de 409 al lanzar > muestra aviso de corrida activa ante 409 con active_run_id 445ms
   ✓ ComposePage panel «Antes de lanzar» > los requisitos se van cumpliendo y el botón se habilita al final 318ms
   ✓ ComposePage panel «Antes de lanzar» > desactivar todas las clases vuelve a bloquear, diciendo qué falta 415ms
   ✓ ComposePage fuente RTSP > bloquea el lanzamiento si la dirección RTSP trae credenciales censuradas (***) 312ms
   ✓ ComposePage fuente RTSP > al elegir rtsp muestra el campo de dirección y arma config { url } 397ms
   ✓ ComposePage cámara guardada (oak_d) > lanza con la config de la cámara guardada elegida 457ms
 ✓ src/__tests__/TraceQueries.final.test.tsx (1 test) 73ms
 ✓ src/__tests__/ui/Table.test.tsx (6 tests) 303ms
 ✓ src/__tests__/charts/layout.test.ts (9 tests) 16ms
stderr | src/__tests__/ComposePage.preflight.test.tsx > ComposePage: bloqueos de preflight > informa los motivos con ready=false sin bloquear DBE y los actualiza por polling
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/ClipsPage.test.tsx (5 tests) 459ms
stderr | src/__tests__/Shell.live.test.tsx > seguir la corrida viva cierra el cajón de navegación móvil
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/RunDetailArtifacts.test.tsx (3 tests) 1134ms
   ✓ expone el inventario limitado del servicio anterior con descargas verificadas 520ms
   ✓ actualiza los archivos después de evaluar sin recargar el detalle 425ms
 ✓ src/__tests__/ui/primitives.test.tsx (10 tests) 235ms
 ✓ src/__tests__/EvalSection.test.tsx (4 tests) 176ms
 ✓ src/__tests__/nav.test.ts (10 tests) 18ms
 ✓ src/__tests__/ui/Select.test.tsx (5 tests) 397ms
stderr | src/__tests__/contrato/corrida-viva.contrato.test.tsx > Contrato: corrida viva > permite alcanzar la corrida activa desde una ruta distinta del listado
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/ComposePage.preflight.test.tsx (2 tests) 1257ms
   ✓ ComposePage: bloqueos de preflight > informa los motivos con ready=false sin bloquear DBE y los actualiza por polling 813ms
   ✓ ComposePage: bloqueos de preflight > informa los motivos con ready=true sin bloquear DBE y los actualiza por polling 442ms
 ✓ src/__tests__/Shell.live.test.tsx (2 tests) 1542ms
   ✓ seguir la corrida viva cierra el cajón de navegación móvil 616ms
   ✓ lanzar desde el formulario invalida la lista vacía y muestra la corrida global 919ms
 ✓ src/__tests__/useSidebarCounts.test.ts (3 tests) 209ms
stderr | src/__tests__/contrato/detalle-traza-evaluacion.contrato.test.tsx > Contrato: detalle, traza y evaluación > lee detalle y traza, permite inspeccionar cuadros y evaluar contra BENCH
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/ExperimentQueries.final.test.tsx (1 test) 73ms
 ✓ src/__tests__/contrato/corrida-viva.contrato.test.tsx (2 tests) 889ms
   ✓ Contrato: corrida viva > permite alcanzar la corrida activa desde una ruta distinta del listado 558ms
   ✓ Contrato: corrida viva > consulta mientras corre, permite detener y cesa el polling del detalle al terminar 329ms
 ✓ src/__tests__/queryClient.test.ts (4 tests) 14ms
 ✓ src/__tests__/api.endpoints.test.ts (4 tests) 21ms
 ✓ src/__tests__/charts/Meter.test.tsx (5 tests) 264ms
 ✓ src/__tests__/experiment-api.test.ts (4 tests) 24ms
 ✓ src/__tests__/contrato/detalle-traza-evaluacion.contrato.test.tsx (1 test) 819ms
   ✓ Contrato: detalle, traza y evaluación > lee detalle y traza, permite inspeccionar cuadros y evaluar contra BENCH 814ms
stderr | src/__tests__/LiveRunPill.test.tsx > LiveRunPill > no renderiza nada si no hay corrida viva
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/LiveRunPill.test.tsx (3 tests) 266ms
 ✓ src/__tests__/stream.test.ts (3 tests) 17ms
 ✓ src/__tests__/ui/Button.test.tsx (5 tests) 313ms
 ✓ src/__tests__/preview.test.ts (2 tests) 8ms
stderr | src/__tests__/App.test.tsx > App > renderiza el título de la consola
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/App.test.tsx (2 tests) 434ms
   ✓ App > renderiza el título de la consola 360ms
 ✓ src/__tests__/ui/Banner.test.tsx (3 tests) 252ms
 ✓ src/__tests__/ui/Badge.test.tsx (4 tests) 71ms
 ✓ src/__tests__/ui/Select.field.test.tsx (1 test) 213ms
 ✓ src/__tests__/ui/SegmentedControl.test.tsx (2 tests) 188ms
 ✓ src/__tests__/ui/InlineDeleteConfirm.test.tsx (2 tests) 198ms
 ✓ src/__tests__/ui/ConditionName.test.tsx (3 tests) 59ms
 ✓ src/__tests__/ui/SearchInput.test.tsx (1 test) 72ms
 ✓ src/__tests__/ui/PageHeader.test.tsx (2 tests) 142ms
 ✓ src/__tests__/promptview.test.ts (3 tests) 4ms
stderr | src/__tests__/CamerasPage.preview-error.test.tsx > muestra el fallo del sondeo de preview sin rechazar una promesa sin manejar
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/ui/icons.test.tsx (1 test) 50ms
 ✓ src/__tests__/CamerasPage.preview-error.test.tsx (1 test) 178ms

 Test Files  68 passed (68)
      Tests  451 passed (451)
   Start at  02:24:52
   Duration  14.02s (transform 5.55s, setup 0ms, collect 37.00s, tests 46.10s, environment 79.31s, prepare 11.87s)

```

## Corte 4: compilación Python

```bash
cd /tmp/eovrt-cortes-validation/webconsole/backend && .venv/bin/python -m compileall -q src tests
```

Salida vacía; exit 0.

## Corte 5: build

```bash
cd /tmp/eovrt-cortes-validation/webconsole/frontend && npm run build
```

```text

> eovrt-webconsole-frontend@0.1.0 build
> tsc && vite build

vite v5.4.21 building for production...
transforming...
✓ 162 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.40 kB │ gzip:   0.27 kB
dist/assets/index-BvOvplTA.css   35.35 kB │ gzip:   7.07 kB
dist/assets/index-DCkIvqyD.js   396.82 kB │ gzip: 120.39 kB
✓ built in 1.48s
```

## Corte 5: frontend completo

```bash
cd /tmp/eovrt-cortes-validation/webconsole/frontend && npm test
```

```text

> eovrt-webconsole-frontend@0.1.0 test
> vitest run


 RUN  v2.1.9 /tmp/eovrt-cortes-validation/webconsole/frontend

 ✓ src/__tests__/api.test.ts (15 tests) 202ms
stderr | src/__tests__/ExperimentDetailPageRiskBanner.test.tsx > ExperimentDetailPage — banner de riesgo activo > muestra el banner con el condition_id cuando patterns no esta vacio y el experimento corre
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ExperimentsPage.test.tsx > ExperimentsPage > lista manifiestos y dispara un experimento con preflight verde
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ExperimentDetailPage.test.tsx > ExperimentDetailPage > muestra las alertas y avisa que el conjunto no es temporal
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/RunsPage.test.tsx > RunsPage > lista corridas y marca la que está en curso
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/contrato/experimentos-distribucion.contrato.test.tsx > Contrato: experimentos y distribución > lista y abre un experimento con outcomes vinculados a cada alerta
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/TrimDialog.test.tsx (9 tests) 399ms
stderr | src/__tests__/CamerasPage.test.tsx > CamerasPage > lista los presets de cámara
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ComposePage.test.tsx > ComposePage prefill > conserva active_ids del manifiesto y no lo pisan los defaults del set
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/RunDetailPage.test.tsx > RunDetailPage > muestra el estado de la corrida con el glosario, no con el código crudo
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/ExperimentDetailPageRiskBanner.test.tsx (7 tests) 439ms
 ✓ src/__tests__/ExperimentsPage.test.tsx (5 tests) 820ms
   ✓ ExperimentsPage > lista manifiestos y dispara un experimento con preflight verde 347ms
 ✓ src/__tests__/PromptSetsPage.test.tsx (7 tests) 986ms
   ✓ PromptSetsPage > lista los sets con badge de estado 320ms
stderr | src/__tests__/ComposePage.test.tsx > ComposePage prefill de source.type video > conserva el source.type original en la composición (round-trip sin colapso a video_file)
No routes matched location "/runs/r1"

 ✓ src/__tests__/ExperimentDetailPage.test.tsx (15 tests) 1101ms
 ✓ src/__tests__/DeriveExperimentForm.test.tsx (13 tests) 1158ms
 ✓ src/__tests__/ComparePage.test.tsx (14 tests) 1383ms
 ✓ src/__tests__/RunDetailPage.test.tsx (10 tests) 1217ms
 ✓ src/__tests__/contrato/experimentos-distribucion.contrato.test.tsx (4 tests) 1505ms
   ✓ Contrato: experimentos y distribución > lista y abre un experimento con outcomes vinculados a cada alerta 646ms
   ✓ Contrato: experimentos y distribución > deriva un manifiesto con overrides y lanza la derivación seleccionada 582ms
stderr | src/__tests__/Shell.test.tsx > Shell > renderiza los tres títulos de grupo
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ComposePage.test.tsx > ComposePage nombre opcional de la corrida > manda run.name cuando se completa, null cuando se deja vacío
No routes matched location "/runs/r1"

 ✓ src/__tests__/Shell.test.tsx (17 tests) 1908ms
 ✓ src/__tests__/CamerasPage.test.tsx (14 tests) 1933ms
   ✓ CamerasPage > muestra banner y deshabilita conectar ante 409 run_active 337ms
stderr | src/__tests__/ComposePage.test.tsx > ComposePage nombre opcional de la corrida > deja run.name en null si el campo queda vacío (usa el id autogenerado)
No routes matched location "/runs/r2"

stderr | src/__tests__/ExperimentsPage.new.test.tsx > ExperimentsPage - crear nuevo experimento (/experiments/new) > abre el formulario con un selector "basado en" precargado con el primer manifiesto
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/RecordPanel.test.tsx (13 tests) 2897ms
   ✓ RecordPanel > mientras graba, consulta el backend periodicamente y muestra elapsed_ms/size_bytes de ahi 1070ms
   ✓ RecordPanel > si el backend informa error, deja de contar y muestra el motivo 1076ms
 ✓ src/__tests__/labels.test.ts (13 tests) 26ms
stderr | src/__tests__/contrato/nueva-corrida.contrato.test.tsx > Contrato: nueva corrida > consulta preflight, compone fuente y prompts, lanza y abre el detalle real
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/traceview.test.ts (12 tests) 24ms
 ✓ src/__tests__/LiveViewer.test.tsx (5 tests) 201ms
 ✓ src/__tests__/TraceSection.test.tsx (10 tests) 2170ms
   ✓ TraceSection > no vuelca todos los cuadros: la lista se acota y dice el total 1033ms
 ✓ src/__tests__/experimentview.test.ts (15 tests) 15ms
stderr | src/__tests__/spec44c_gate.test.tsx > spec44c gate: flujo de experimentos por la UI > ExperimentsPage: lista un manifiesto y dispara runExperiment al hacer click en "Ejecutar experimento"
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/PreviewWithBoxes.test.tsx (8 tests) 188ms
 ✓ src/__tests__/ExperimentsPage.new.test.tsx (4 tests) 1269ms
   ✓ ExperimentsPage - crear nuevo experimento (/experiments/new) > abre el formulario con un selector "basado en" precargado con el primer manifiesto 495ms
   ✓ ExperimentsPage - crear nuevo experimento (/experiments/new) > al cambiar la fuente en el selector, vuelve a pedir los defaults y reprecarga los campos (bug central) 363ms
 ✓ src/__tests__/PromptSetEditor.test.tsx (5 tests) 733ms
   ✓ PromptSetEditor > exploratory: permite editar y guardar via updatePromptSet 341ms
 ✓ src/__tests__/PlatformPage.test.tsx (6 tests) 748ms
   ✓ PlatformPage > lista el fleet y activa una instancia 467ms
 ✓ src/__tests__/RunsPage.test.tsx (22 tests) 3955ms
   ✓ RunsPage > lista corridas y marca la que está en curso 321ms
   ✓ RunsPage > el pedido de la página lleva el filtro, el orden y la página al servidor 725ms
   ✓ RunsPage > el buscador manda `q` al servidor en vez de filtrar en el cliente 740ms
 ✓ src/__tests__/spec44c_gate.test.tsx (3 tests) 531ms
   ✓ spec44c gate: flujo de experimentos por la UI > ExperimentsPage: lista un manifiesto y dispara runExperiment al hacer click en "Ejecutar experimento" 365ms
 ✓ src/__tests__/charts/ActivityTimeline.test.tsx (7 tests) 368ms
 ✓ src/__tests__/runview.test.ts (17 tests) 21ms
 ✓ src/__tests__/contrato/nueva-corrida.contrato.test.tsx (3 tests) 2016ms
   ✓ Contrato: nueva corrida > consulta preflight, compone fuente y prompts, lanza y abre el detalle real 1092ms
   ✓ Contrato: nueva corrida > impide lanzar con el formulario completo si el target aún no está listo 382ms
   ✓ Contrato: nueva corrida > muestra los bloqueos del preflight y permite lanzar sólo medios con target listo 538ms
 ✓ src/__tests__/runseries.test.ts (12 tests) 13ms
 ✓ src/__tests__/useServiceHealth.test.ts (5 tests) 406ms
 ✓ src/__tests__/charts/timeline.test.ts (9 tests) 47ms
stderr | src/__tests__/ComposePage.test.tsx > ComposePage fuente RTSP > al elegir rtsp muestra el campo de dirección y arma config { url }
No routes matched location "/runs/r1"

 ✓ src/__tests__/charts/GroupedBars.test.tsx (8 tests) 220ms
 ✓ src/__tests__/RunKpiStrip.test.tsx (7 tests) 342ms
stderr | src/__tests__/ComposePage.test.tsx > ComposePage cámara guardada (oak_d) > lanza con la config de la cámara guardada elegida
No routes matched location "/runs/r1"

 ✓ src/__tests__/ComposePage.test.tsx (18 tests) 5998ms
   ✓ ComposePage prefill > conserva active_ids del manifiesto y no lo pisan los defaults del set 643ms
   ✓ ComposePage prefill de source.type video > conserva el source.type original en la composición (round-trip sin colapso a video_file) 455ms
   ✓ ComposePage prefill survives catalog re-fetch (no clobber) > no reaplica el manifiesto cuando `experiments` cambia de referencia tras un re-fetch 410ms
   ✓ ComposePage nombre opcional de la corrida > manda run.name cuando se completa, null cuando se deja vacío 375ms
   ✓ ComposePage nombre opcional de la corrida > deja run.name en null si el campo queda vacío (usa el id autogenerado) 340ms
   ✓ ComposePage aviso de 409 al lanzar > muestra aviso de prueba de cámara activa ante 409 preview_active 354ms
   ✓ ComposePage aviso de 409 al lanzar > muestra aviso de corrida activa ante 409 con active_run_id 339ms
   ✓ ComposePage panel «Antes de lanzar» > los requisitos se van cumpliendo y el botón se habilita al final 314ms
   ✓ ComposePage panel «Antes de lanzar» > desactivar todas las clases vuelve a bloquear, diciendo qué falta 451ms
   ✓ ComposePage fuente RTSP > bloquea el lanzamiento si la dirección RTSP trae credenciales censuradas (***) 421ms
   ✓ ComposePage fuente RTSP > al elegir rtsp muestra el campo de dirección y arma config { url } 355ms
   ✓ ComposePage cámara guardada (oak_d) > lanza con la config de la cámara guardada elegida 396ms
stderr | src/__tests__/RunDetailArtifacts.test.tsx > expone el inventario limitado del servicio anterior con descargas verificadas
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/TraceQueries.final.test.tsx (1 test) 70ms
 ✓ src/__tests__/charts/layout.test.ts (9 tests) 16ms
 ✓ src/__tests__/ui/Table.test.tsx (6 tests) 327ms
 ✓ src/__tests__/ClipsPage.test.tsx (5 tests) 414ms
stderr | src/__tests__/Shell.live.test.tsx > seguir la corrida viva cierra el cajón de navegación móvil
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ComposePage.preflight.test.tsx > ComposePage: bloqueos de preflight > informa los motivos con ready=false sin bloquear DBE y los actualiza por polling
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/ui/primitives.test.tsx (10 tests) 301ms
 ✓ src/__tests__/EvalSection.test.tsx (4 tests) 284ms
 ✓ src/__tests__/RunDetailArtifacts.test.tsx (3 tests) 1085ms
   ✓ expone el inventario limitado del servicio anterior con descargas verificadas 489ms
   ✓ actualiza los archivos después de evaluar sin recargar el detalle 445ms
 ✓ src/__tests__/Shell.live.test.tsx (2 tests) 1534ms
   ✓ seguir la corrida viva cierra el cajón de navegación móvil 570ms
   ✓ lanzar desde el formulario invalida la lista vacía y muestra la corrida global 962ms
 ✓ src/__tests__/ComposePage.preflight.test.tsx (2 tests) 1304ms
   ✓ ComposePage: bloqueos de preflight > informa los motivos con ready=false sin bloquear DBE y los actualiza por polling 868ms
   ✓ ComposePage: bloqueos de preflight > informa los motivos con ready=true sin bloquear DBE y los actualiza por polling 433ms
 ✓ src/__tests__/nav.test.ts (10 tests) 23ms
 ✓ src/__tests__/useSidebarCounts.test.ts (3 tests) 251ms
 ✓ src/__tests__/ui/Select.test.tsx (5 tests) 396ms
 ✓ src/__tests__/queryClient.test.ts (4 tests) 9ms
stderr | src/__tests__/contrato/corrida-viva.contrato.test.tsx > Contrato: corrida viva > permite alcanzar la corrida activa desde una ruta distinta del listado
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/contrato/detalle-traza-evaluacion.contrato.test.tsx > Contrato: detalle, traza y evaluación > lee detalle y traza, permite inspeccionar cuadros y evaluar contra BENCH
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/ExperimentQueries.final.test.tsx (1 test) 65ms
stderr | src/__tests__/Shell.distribution.test.tsx > Salud del distribuidor en la barra lateral > informa healthy=true y conserva los dos motores
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/charts/Meter.test.tsx (5 tests) 192ms
 ✓ src/__tests__/contrato/corrida-viva.contrato.test.tsx (2 tests) 812ms
   ✓ Contrato: corrida viva > permite alcanzar la corrida activa desde una ruta distinta del listado 429ms
   ✓ Contrato: corrida viva > consulta mientras corre, permite detener y cesa el polling del detalle al terminar 382ms
 ✓ src/__tests__/Shell.distribution.test.tsx (3 tests) 536ms
 ✓ src/__tests__/api.endpoints.test.ts (4 tests) 16ms
 ✓ src/__tests__/contrato/detalle-traza-evaluacion.contrato.test.tsx (1 test) 841ms
   ✓ Contrato: detalle, traza y evaluación > lee detalle y traza, permite inspeccionar cuadros y evaluar contra BENCH 838ms
 ✓ src/__tests__/experiment-api.test.ts (4 tests) 20ms
stderr | src/__tests__/LiveRunPill.test.tsx > LiveRunPill > no renderiza nada si no hay corrida viva
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/LiveRunPill.test.tsx (3 tests) 252ms
stderr | src/__tests__/App.test.tsx > App > renderiza el título de la consola
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/App.test.tsx (2 tests) 418ms
   ✓ App > renderiza el título de la consola 319ms
 ✓ src/__tests__/stream.test.ts (3 tests) 12ms
 ✓ src/__tests__/preview.test.ts (2 tests) 8ms
 ✓ src/__tests__/ui/Button.test.tsx (5 tests) 269ms
 ✓ src/__tests__/ui/Badge.test.tsx (4 tests) 72ms
 ✓ src/__tests__/ui/Banner.test.tsx (3 tests) 226ms
 ✓ src/__tests__/ui/Select.field.test.tsx (1 test) 203ms
 ✓ src/__tests__/ui/SegmentedControl.test.tsx (2 tests) 176ms
 ✓ src/__tests__/ui/ConditionName.test.tsx (3 tests) 58ms
 ✓ src/__tests__/ui/InlineDeleteConfirm.test.tsx (2 tests) 169ms
 ✓ src/__tests__/ui/icons.test.tsx (1 test) 45ms
 ✓ src/__tests__/ui/PageHeader.test.tsx (2 tests) 158ms
 ✓ src/__tests__/ui/SearchInput.test.tsx (1 test) 45ms
 ✓ src/__tests__/promptview.test.ts (3 tests) 4ms
stderr | src/__tests__/CamerasPage.preview-error.test.tsx > muestra el fallo del sondeo de preview sin rechazar una promesa sin manejar
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/CamerasPage.preview-error.test.tsx (1 test) 162ms

 Test Files  69 passed (69)
      Tests  454 passed (454)
   Start at  02:25:28
   Duration  14.03s (transform 5.13s, setup 0ms, collect 37.02s, tests 46.02s, environment 77.73s, prepare 12.74s)

```

## Corte 5: compilación Python

```bash
cd /tmp/eovrt-cortes-validation/webconsole/backend && .venv/bin/python -m compileall -q src tests
```

Salida vacía; exit 0.

## Corte 1: backend completo con entorno corregido

```bash
cd /tmp/eovrt-cortes-validation/webconsole/backend && PYTHONPATH="$PWD/src:$PWD" EOVRT_DISTRIBUTION_EXECUTABLE=/home/simonll4/projects/e-ovrt_alert-distribution/.venv/bin/eovrt-distribute .venv/bin/python -m pytest -q
```

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
761 passed in 114.40s (0:01:54)
```

## Árbol final: backend completo

```bash
cd webconsole/backend && ./.venv/bin/python -m pytest -q
```

```text
........................................................................ [  9%]
........................................................................ [ 18%]
........................................................................ [ 27%]
........................................................................ [ 36%]
........................................................................ [ 45%]
........................................................................ [ 55%]
........................................................................ [ 64%]
........................................................................ [ 73%]
........................................................................ [ 82%]
........................................................................ [ 91%]
................................................................         [100%]
784 passed in 120.81s (0:02:00)
```

## Árbol final: frontend completo

```bash
cd webconsole/frontend && npm test
```

```text

> eovrt-webconsole-frontend@0.1.0 test
> vitest run


 RUN  v2.1.9 /home/simonll4/projects/e-ovrt_experimental-setup/webconsole/frontend

 ✓ src/__tests__/api.test.ts (15 tests) 117ms
stderr | src/__tests__/ExperimentDetailPageRiskBanner.test.tsx > ExperimentDetailPage — banner de riesgo activo > muestra el banner con el condition_id cuando patterns no esta vacio y el experimento corre
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ExperimentsPage.test.tsx > ExperimentsPage > lista manifiestos y dispara un experimento con preflight verde
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/RunsPage.test.tsx > RunsPage > lista corridas y marca la que está en curso
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ExperimentDetailPage.test.tsx > ExperimentDetailPage > muestra las alertas y avisa que el conjunto no es temporal
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/TrimDialog.test.tsx (9 tests) 766ms
stderr | src/__tests__/contrato/experimentos-distribucion.contrato.test.tsx > Contrato: experimentos y distribución > lista y abre un experimento con outcomes vinculados a cada alerta
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/CamerasPage.test.tsx > CamerasPage > lista los presets de cámara
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ComposePage.test.tsx > ComposePage prefill > conserva active_ids del manifiesto y no lo pisan los defaults del set
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/ExperimentDetailPageRiskBanner.test.tsx (7 tests) 1055ms
   ✓ ExperimentDetailPage — banner de riesgo activo > muestra el banner con el condition_id cuando patterns no esta vacio y el experimento corre 346ms
stderr | src/__tests__/RunDetailPage.test.tsx > RunDetailPage > muestra el estado de la corrida con el glosario, no con el código crudo
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/ExperimentsPage.test.tsx (5 tests) 1822ms
   ✓ ExperimentsPage > lista manifiestos y dispara un experimento con preflight verde 819ms
   ✓ ExperimentsPage > derivar recarga los manifiestos, y cada fila lanza el suyo 324ms
 ✓ src/__tests__/PromptSetsPage.test.tsx (7 tests) 1893ms
   ✓ PromptSetsPage > lista los sets con badge de estado 612ms
   ✓ PromptSetsPage > un conjunto congelado no ofrece editar, sino ver 383ms
   ✓ PromptSetsPage > abre el editor en la columna derecha, sin perder la lista 336ms
 ✓ src/__tests__/DeriveExperimentForm.test.tsx (13 tests) 2139ms
   ✓ DeriveExperimentForm > precarga los valores del manifiesto fuente 404ms
   ✓ DeriveExperimentForm > mode "derive" (default): título "Derivar de <source>" y botón "Derivar" 321ms
stderr | src/__tests__/ComposePage.test.tsx > ComposePage prefill de source.type video > conserva el source.type original en la composición (round-trip sin colapso a video_file)
No routes matched location "/runs/r1"

 ✓ src/__tests__/ExperimentDetailPage.test.tsx (15 tests) 2440ms
   ✓ ExperimentDetailPage > muestra las alertas y avisa que el conjunto no es temporal 554ms
   ✓ ExperimentDetailPage > un error real del reporte sí se muestra como error, con su código 322ms
 ✓ src/__tests__/ComparePage.test.tsx (14 tests) 2706ms
   ✓ ComparePage > lista las corridas por nombre, no por identificador crudo 527ms
   ✓ ComparePage > compara al elegir dos y nombra las métricas en español 456ms
   ✓ ComparePage > resalta el mejor valor de cada fila 416ms
   ✓ ComparePage > dibuja las barras con leyenda nombrada por corrida 328ms
stderr | src/__tests__/Shell.test.tsx > Shell > renderiza los tres títulos de grupo
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/RecordPanel.test.tsx (13 tests) 3661ms
   ✓ RecordPanel > mientras graba, consulta el backend periodicamente y muestra elapsed_ms/size_bytes de ahi 1125ms
   ✓ RecordPanel > si el backend informa error, deja de contar y muestra el motivo 1152ms
 ✓ src/__tests__/contrato/experimentos-distribucion.contrato.test.tsx (4 tests) 3155ms
   ✓ Contrato: experimentos y distribución > lista y abre un experimento con outcomes vinculados a cada alerta 1398ms
   ✓ Contrato: experimentos y distribución > deriva un manifiesto con overrides y lanza la derivación seleccionada 1061ms
   ✓ Contrato: experimentos y distribución > seleccionar dos corridas evaluadas pide su comparación por HTTP 551ms
 ✓ src/__tests__/Shell.test.tsx (17 tests) 3420ms
   ✓ Shell > renderiza los tres títulos de grupo 319ms
   ✓ Shell > acorta la etiqueta que no entra, sin perder el nombre completo 454ms
   ✓ Shell > muestra el contador de corridas en curso cuando es mayor a 0 306ms
 ✓ src/__tests__/RunDetailPage.test.tsx (10 tests) 2861ms
   ✓ RunDetailPage > muestra el estado de la corrida con el glosario, no con el código crudo 515ms
   ✓ RunDetailPage > las pestañas separan traza, resumen, evaluación y archivos 539ms
   ✓ RunDetailPage > confirmar borra la corrida y vuelve al listado 495ms
   ✓ RunDetailPage > borrado parcial muestra el detalle de los planos que fallaron y persiste (no navega) 375ms
 ✓ src/__tests__/CamerasPage.test.tsx (14 tests) 3911ms
   ✓ CamerasPage > lista los presets de cámara 375ms
   ✓ CamerasPage > muestra banner y deshabilita conectar ante 409 run_active 688ms
   ✓ CamerasPage > activa por defecto las clases sin enabled_by_default declarado en el YAML 518ms
   ✓ CamerasPage > borrar pide confirmación en línea, no un diálogo del navegador 321ms
   ✓ CamerasPage > cancelar la confirmación no borra nada 357ms
   ✓ CamerasPage > confirmar borra la cámara y refresca el listado 391ms
stderr | src/__tests__/ComposePage.test.tsx > ComposePage nombre opcional de la corrida > manda run.name cuando se completa, null cuando se deja vacío
No routes matched location "/runs/r1"

stderr | src/__tests__/ComposePage.test.tsx > ComposePage nombre opcional de la corrida > deja run.name en null si el campo queda vacío (usa el id autogenerado)
No routes matched location "/runs/r2"

stderr | src/__tests__/ExperimentsPage.new.test.tsx > ExperimentsPage - crear nuevo experimento (/experiments/new) > abre el formulario con un selector "basado en" precargado con el primer manifiesto
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/labels.test.ts (13 tests) 39ms
 ✓ src/__tests__/LiveViewer.test.tsx (5 tests) 314ms
stderr | src/__tests__/contrato/nueva-corrida.contrato.test.tsx > Contrato: nueva corrida > consulta preflight, compone fuente y prompts, lanza y abre el detalle real
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/traceview.test.ts (12 tests) 31ms
 ✓ src/__tests__/experimentview.test.ts (15 tests) 28ms
 ✓ src/__tests__/PlatformPage.test.tsx (6 tests) 1052ms
   ✓ PlatformPage > lista el fleet y activa una instancia 551ms
 ✓ src/__tests__/TraceSection.test.tsx (10 tests) 3686ms
   ✓ TraceSection > no vuelca todos los cuadros: la lista se acota y dice el total 2031ms
 ✓ src/__tests__/ExperimentsPage.new.test.tsx (4 tests) 2088ms
   ✓ ExperimentsPage - crear nuevo experimento (/experiments/new) > abre el formulario con un selector "basado en" precargado con el primer manifiesto 1032ms
   ✓ ExperimentsPage - crear nuevo experimento (/experiments/new) > al cambiar la fuente en el selector, vuelve a pedir los defaults y reprecarga los campos (bug central) 443ms
   ✓ ExperimentsPage - crear nuevo experimento (/experiments/new) > en modo nuevo la card dice "Nuevo experimento" y el botón "Crear" (no "Derivar de...") 332ms
 ✓ src/__tests__/PromptSetEditor.test.tsx (5 tests) 1186ms
   ✓ PromptSetEditor > exploratory: permite editar y guardar via updatePromptSet 568ms
stderr | src/__tests__/spec44c_gate.test.tsx > spec44c gate: flujo de experimentos por la UI > ExperimentsPage: lista un manifiesto y dispara runExperiment al hacer click en "Ejecutar experimento"
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/RunsPage.test.tsx (22 tests) 7713ms
   ✓ RunsPage > lista corridas y marca la que está en curso 869ms
   ✓ RunsPage > el pedido de la página lleva el filtro, el orden y la página al servidor 1564ms
   ✓ RunsPage > el buscador manda `q` al servidor en vez de filtrar en el cliente 983ms
   ✓ RunsPage > ordenar cambia `orden` y `direccion`, y el tercer click vuelve al orden por fecha 473ms
   ✓ RunsPage > el total es el del servidor, no la cantidad de filas de la página 534ms
   ✓ RunsPage > estado vacío distinto cuando lo que no coincide es el filtro 304ms
 ✓ src/__tests__/PreviewWithBoxes.test.tsx (8 tests) 394ms
 ✓ src/__tests__/spec44c_gate.test.tsx (3 tests) 891ms
   ✓ spec44c gate: flujo de experimentos por la UI > ExperimentsPage: lista un manifiesto y dispara runExperiment al hacer click en "Ejecutar experimento" 678ms
 ✓ src/__tests__/charts/ActivityTimeline.test.tsx (7 tests) 661ms
 ✓ src/__tests__/useServiceHealth.test.ts (5 tests) 497ms
 ✓ src/__tests__/runview.test.ts (17 tests) 28ms
 ✓ src/__tests__/contrato/nueva-corrida.contrato.test.tsx (3 tests) 3204ms
   ✓ Contrato: nueva corrida > consulta preflight, compone fuente y prompts, lanza y abre el detalle real 1743ms
   ✓ Contrato: nueva corrida > impide lanzar con el formulario completo si el target aún no está listo 766ms
   ✓ Contrato: nueva corrida > muestra los bloqueos del preflight y permite lanzar sólo medios con target listo 683ms
stderr | src/__tests__/ComposePage.test.tsx > ComposePage fuente RTSP > al elegir rtsp muestra el campo de dirección y arma config { url }
No routes matched location "/runs/r1"

 ✓ src/__tests__/runseries.test.ts (12 tests) 45ms
stderr | src/__tests__/ComposePage.test.tsx > ComposePage cámara guardada (oak_d) > lanza con la config de la cámara guardada elegida
No routes matched location "/runs/r1"

 ✓ src/__tests__/ComposePage.test.tsx (18 tests) 10569ms
   ✓ ComposePage prefill > conserva active_ids del manifiesto y no lo pisan los defaults del set 1535ms
   ✓ ComposePage prefill de source.type video > conserva el source.type original en la composición (round-trip sin colapso a video_file) 858ms
   ✓ ComposePage prefill survives catalog re-fetch (no clobber) > no reaplica el manifiesto cuando `experiments` cambia de referencia tras un re-fetch 1089ms
   ✓ ComposePage nombre opcional de la corrida > manda run.name cuando se completa, null cuando se deja vacío 643ms
   ✓ ComposePage nombre opcional de la corrida > deja run.name en null si el campo queda vacío (usa el id autogenerado) 616ms
   ✓ ComposePage aviso de 409 al lanzar > muestra aviso de prueba de cámara activa ante 409 preview_active 754ms
   ✓ ComposePage aviso de 409 al lanzar > muestra aviso de corrida activa ante 409 con active_run_id 559ms
   ✓ ComposePage panel «Antes de lanzar» > los requisitos se van cumpliendo y el botón se habilita al final 490ms
   ✓ ComposePage panel «Antes de lanzar» > desactivar todas las clases vuelve a bloquear, diciendo qué falta 706ms
   ✓ ComposePage rejilla de fuentes > muestra el nombre legible de cada fuente, no su identificador 365ms
   ✓ ComposePage rejilla de fuentes > una fuente deshabilitada explica el motivo que manda el backend 353ms
   ✓ ComposePage rejilla de fuentes > la fuente elegida queda marcada con aria-pressed 344ms
   ✓ ComposePage fuente RTSP > bloquea el lanzamiento si la dirección RTSP trae credenciales censuradas (***) 406ms
   ✓ ComposePage fuente RTSP > al elegir rtsp muestra el campo de dirección y arma config { url } 532ms
   ✓ ComposePage cámara guardada (oak_d) > lanza con la config de la cámara guardada elegida 677ms
 ✓ src/__tests__/charts/timeline.test.ts (9 tests) 92ms
 ✓ src/__tests__/charts/GroupedBars.test.tsx (8 tests) 339ms
 ✓ src/__tests__/RunKpiStrip.test.tsx (7 tests) 742ms
stderr | src/__tests__/RunDetailArtifacts.test.tsx > expone el inventario limitado del servicio anterior con descargas verificadas
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/TraceQueries.final.test.tsx (1 test) 131ms
 ✓ src/__tests__/ui/Table.test.tsx (6 tests) 455ms
 ✓ src/__tests__/charts/layout.test.ts (9 tests) 22ms
 ✓ src/__tests__/ClipsPage.test.tsx (5 tests) 787ms
   ✓ ClipsPage > lista masters y clips 427ms
stderr | src/__tests__/ComposePage.preflight.test.tsx > ComposePage: bloqueos de preflight > informa los motivos con ready=false sin bloquear DBE y los actualiza por polling
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/Shell.live.test.tsx > seguir la corrida viva cierra el cajón de navegación móvil
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/RunDetailArtifacts.test.tsx (3 tests) 1603ms
   ✓ expone el inventario limitado del servicio anterior con descargas verificadas 756ms
   ✓ actualiza los archivos después de evaluar sin recargar el detalle 649ms
 ✓ src/__tests__/ui/primitives.test.tsx (10 tests) 545ms
 ✓ src/__tests__/EvalSection.test.tsx (4 tests) 343ms
 ✓ src/__tests__/Shell.live.test.tsx (2 tests) 2170ms
   ✓ seguir la corrida viva cierra el cajón de navegación móvil 978ms
   ✓ lanzar desde el formulario invalida la lista vacía y muestra la corrida global 1184ms
stderr | src/__tests__/contrato/corrida-viva.contrato.test.tsx > Contrato: corrida viva > permite alcanzar la corrida activa desde una ruta distinta del listado
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/ComposePage.preflight.test.tsx (2 tests) 1998ms
   ✓ ComposePage: bloqueos de preflight > informa los motivos con ready=false sin bloquear DBE y los actualiza por polling 1322ms
   ✓ ComposePage: bloqueos de preflight > informa los motivos con ready=true sin bloquear DBE y los actualiza por polling 673ms
 ✓ src/__tests__/ui/Select.test.tsx (5 tests) 584ms
 ✓ src/__tests__/useSidebarCounts.test.ts (3 tests) 277ms
stderr | src/__tests__/contrato/detalle-traza-evaluacion.contrato.test.tsx > Contrato: detalle, traza y evaluación > lee detalle y traza, permite inspeccionar cuadros y evaluar contra BENCH
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/contrato/corrida-viva.contrato.test.tsx (2 tests) 1282ms
   ✓ Contrato: corrida viva > permite alcanzar la corrida activa desde una ruta distinta del listado 840ms
   ✓ Contrato: corrida viva > consulta mientras corre, permite detener y cesa el polling del detalle al terminar 435ms
 ✓ src/__tests__/nav.test.ts (10 tests) 26ms
 ✓ src/__tests__/ExperimentQueries.final.test.tsx (1 test) 101ms
 ✓ src/__tests__/api.endpoints.test.ts (4 tests) 27ms
stderr | src/__tests__/Shell.distribution.test.tsx > Salud del distribuidor en la barra lateral > informa healthy=true y conserva los dos motores
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/queryClient.test.ts (4 tests) 18ms
 ✓ src/__tests__/contrato/detalle-traza-evaluacion.contrato.test.tsx (1 test) 1179ms
   ✓ Contrato: detalle, traza y evaluación > lee detalle y traza, permite inspeccionar cuadros y evaluar contra BENCH 1172ms
 ✓ src/__tests__/charts/Meter.test.tsx (5 tests) 516ms
 ✓ src/__tests__/Shell.distribution.test.tsx (3 tests) 938ms
   ✓ Salud del distribuidor en la barra lateral > informa healthy=true y conserva los dos motores 494ms
stderr | src/__tests__/LiveRunPill.test.tsx > LiveRunPill > no renderiza nada si no hay corrida viva
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/experiment-api.test.ts (4 tests) 58ms
 ✓ src/__tests__/LiveRunPill.test.tsx (3 tests) 507ms
   ✓ LiveRunPill > muestra el run vivo con fps y linkea a su detalle 310ms
stderr | src/__tests__/App.test.tsx > App > renderiza el título de la consola
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/App.test.tsx (2 tests) 889ms
   ✓ App > renderiza el título de la consola 727ms
 ✓ src/__tests__/stream.test.ts (3 tests) 23ms
 ✓ src/__tests__/preview.test.ts (2 tests) 15ms
 ✓ src/__tests__/ui/Button.test.tsx (5 tests) 460ms
   ✓ Button > por defecto es variant secondary 344ms
 ✓ src/__tests__/ui/Badge.test.tsx (4 tests) 128ms
 ✓ src/__tests__/ui/Banner.test.tsx (3 tests) 412ms
   ✓ Banner > tono warn con boton de cerrar 355ms
 ✓ src/__tests__/ui/Select.field.test.tsx (1 test) 390ms
   ✓ Select dentro de Field > cancela la activación del label al elegir, sin reabrir el control 387ms
 ✓ src/__tests__/ui/ConditionName.test.tsx (3 tests) 143ms
 ✓ src/__tests__/ui/SegmentedControl.test.tsx (2 tests) 416ms
   ✓ SegmentedControl > marca la opcion activa con aria-pressed 348ms
 ✓ src/__tests__/ui/PageHeader.test.tsx (2 tests) 348ms
   ✓ PageHeader > renderiza titulo, meta y acciones 320ms
 ✓ src/__tests__/ui/InlineDeleteConfirm.test.tsx (2 tests) 390ms
   ✓ InlineDeleteConfirm > "Si, borrar" dispara onConfirm; "No" dispara onCancel 336ms
 ✓ src/__tests__/ui/SearchInput.test.tsx (1 test) 103ms
stderr | src/__tests__/CamerasPage.preview-error.test.tsx > muestra el fallo del sondeo de preview sin rechazar una promesa sin manejar
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/CamerasPage.preview-error.test.tsx (1 test) 348ms
   ✓ muestra el fallo del sondeo de preview sin rechazar una promesa sin manejar 346ms
 ✓ src/__tests__/promptview.test.ts (3 tests) 6ms
 ✓ src/__tests__/ui/icons.test.tsx (1 test) 76ms

 Test Files  69 passed (69)
      Tests  454 passed (454)
   Start at  02:19:34
   Duration  24.78s (transform 9.65s, setup 0ms, collect 64.33s, tests 81.26s, environment 138.76s, prepare 21.24s)

```

## Árbol final: build

```bash
cd webconsole/frontend && npm run build
```

```text

> eovrt-webconsole-frontend@0.1.0 build
> tsc && vite build

vite v5.4.21 building for production...
transforming...
✓ 162 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.40 kB │ gzip:   0.27 kB
dist/assets/index-BvOvplTA.css   35.35 kB │ gzip:   7.07 kB
dist/assets/index-DCkIvqyD.js   396.82 kB │ gzip: 120.39 kB
✓ built in 3.36s
```

## Ruff: diagnósticos existentes

```bash
cd webconsole/backend && .venv/bin/ruff check src tests --output-format concise
```

```text
src/eovrt_webconsole/clips/trim.py:40:21: PLW1510 `subprocess.run` without explicit `check` argument
src/eovrt_webconsole/clips/window.py:18:5: PIE790 [*] Unnecessary `pass` statement
src/eovrt_webconsole/experiment/applicability.py:59:34: UP037 [*] Remove quotes from type annotation
src/eovrt_webconsole/experiment/run_manager.py:138:9: S110 `try`-`except`-`pass` detected, consider logging the exception
src/eovrt_webconsole/orchestrator.py:14:1: UP035 [*] Import from `collections.abc` instead: `Awaitable`, `Callable`
src/eovrt_webconsole/orchestrator.py:46:12: UP041 [*] Replace aliased errors with `TimeoutError`
src/eovrt_webconsole/recording/ffmpeg_recorder.py:3:1: I001 [*] Import block is un-sorted or un-formatted
src/eovrt_webconsole/recording/oakd_recorder.py:33:17: PLW1510 `subprocess.run` without explicit `check` argument
src/eovrt_webconsole/recording/probe.py:34:21: PLW1510 `subprocess.run` without explicit `check` argument
src/eovrt_webconsole/recording/probe.py:60:21: RUF046 Value being cast to `int` is already an integer
src/eovrt_webconsole/recording/types.py:67:42: UP037 [*] Remove quotes from type annotation
src/eovrt_webconsole/routers/experiments.py:4:1: I001 [*] Import block is un-sorted or un-formatted
src/eovrt_webconsole/routers/recordings.py:63:31: RUF100 [*] Unused `noqa` directive (unused: `BLE001`)
src/eovrt_webconsole/routers/runs.py:2:1: I001 [*] Import block is un-sorted or un-formatted
tests/test_control_backend.py:24:14: RUF059 Unpacked variable `state` is never used
tests/test_distribution_http.py:278:5: SIM117 [*] Use a single `with` statement with multiple contexts instead of nested `with` statements
tests/test_distribution_http.py:421:5: SIM117 [*] Use a single `with` statement with multiple contexts instead of nested `with` statements
tests/test_distribution_preflight_unit.py:5:8: F401 [*] `pytest` imported but unused
tests/test_record_oakd_script.py:17:12: PLW1510 `subprocess.run` without explicit `check` argument
tests/test_recording_sidecar.py:10:12: C408 Unnecessary `dict()` call (rewrite as a literal)
tests/test_runner_clip_id_injection.py:23:46: UP017 [*] Use `datetime.UTC` alias
tests/test_runner_gate.py:30:46: UP017 [*] Use `datetime.UTC` alias
tests/test_runner_report_wiring.py:19:46: UP017 [*] Use `datetime.UTC` alias
tests/test_runner_temporal_evaluation.py:28:46: UP017 [*] Use `datetime.UTC` alias
tests/test_runner_temporal_evaluation.py:207:9: RET501 [*] Do not explicitly `return None` in function if it is the only possible return value
tests/test_runner_temporal_evaluation.py:207:9: PLR1711 [*] Useless `return` statement at end of function
tests/test_runs_router.py:249:5: I001 [*] Import block is un-sorted or un-formatted
tests/test_runs_router.py:308:5: I001 [*] Import block is un-sorted or un-formatted
tests/test_runs_router.py:342:5: I001 [*] Import block is un-sorted or un-formatted
tests/test_stream_proxy.py:24:5: SIM117 [*] Use a single `with` statement with multiple contexts instead of nested `with` statements
tests/test_stream_proxy.py:30:13: S110 `try`-`except`-`pass` detected, consider logging the exception
tests/test_stream_proxy.py:57:9: S110 `try`-`except`-`pass` detected, consider logging the exception
tests/test_stream_proxy.py:77:9: S110 `try`-`except`-`pass` detected, consider logging the exception
tests/test_stream_proxy.py:106:9: S110 `try`-`except`-`pass` detected, consider logging the exception
tests/test_stream_proxy.py:129:5: SIM117 [*] Use a single `with` statement with multiple contexts instead of nested `with` statements
tests/test_stream_proxy.py:133:13: S110 `try`-`except`-`pass` detected, consider logging the exception
Found 36 errors.
[*] 23 fixable with the `--fix` option (3 hidden fixes can be enabled with the `--unsafe-fixes` option).
```

## Ruff: comparación por archivo, código y mensaje

```bash
Comparación de las salidas JSON de Ruff del árbol final y 3500923, sin comparar números de línea.
```

```text
Referencia 3500923: 36 diagnósticos
Árbol final: 36 diagnósticos
Nuevos: 0
Eliminados: 0
```

## Integridad del contrato y del código final

El payload del primer POST /api/runs, soporte.tsx, la prueba D-5 y la igualdad exacta del reporte son idénticos a la instantánea anterior. Sólo cambió la interacción de los dos archivos autorizados de contrato y el caso D-8 decidido por el usuario.

```text
0e03e520e9d647ccda097430ea83353d57bca0f661a9a019085b32b61d02c299  webconsole/frontend/src/__tests__/contrato/corrida-viva.contrato.test.tsx
b2c2c69f6ea35020d0daf72a2cbd3ebb7b70e4d37085f0e9926aef2c88d0c306  webconsole/frontend/src/__tests__/contrato/detalle-traza-evaluacion.contrato.test.tsx
74e10a0e16f3083a55859c1a4bd935abece05c5393d43c5eb566b32842efcd75  webconsole/frontend/src/__tests__/contrato/experimentos-distribucion.contrato.test.tsx
71d8c8d870506d2add2cfa9f4ec3c6d05fe278d543a4e95c0ccb0f938cb66423  webconsole/frontend/src/__tests__/contrato/nueva-corrida.contrato.test.tsx
2a422da8e919925522b5a66f88a7a3c8293ab607ed7acc4fd55ad5dd81f04b45  webconsole/frontend/src/__tests__/contrato/soporte.tsx
```

Todos los hashes de `webconsole/` coinciden con la instantánea final de P-2 utilizada para las suites finales; reconstruir los commits no cambió esos contenidos.

## Inventario por commit

Los mensajes contienen las dependencias desplazadas. El tramo 5 recibe además los documentos del cierre; su SHA definitivo se consulta con `git log`.

### Tramo 0

```text
feat(webconsole): tramo 0 — contrato congelado del flujo troncal

Caracteriza los cuatro flujos sobre 50b666b sin cambios de producción.
P-2/D-8: controles compatibles con ambas interfaces; el preflight agregado
informa sin impedir una corrida DBE con target listo. Se conserva intacta
la aserción del payload POST /api/runs y el soporte opcional de render.

Verificación: contrato 10/10 contra 50b666b y contra el árbol final;
este corte: frontend 397/397, tsc + vite build y compilación Python.
Reconstrucción del historial solicitada en P-1, sin alterar fechas pasadas.

```

```text
A	webconsole/frontend/src/__tests__/contrato/corrida-viva.contrato.test.tsx
A	webconsole/frontend/src/__tests__/contrato/detalle-traza-evaluacion.contrato.test.tsx
A	webconsole/frontend/src/__tests__/contrato/experimentos-distribucion.contrato.test.tsx
A	webconsole/frontend/src/__tests__/contrato/nueva-corrida.contrato.test.tsx
A	webconsole/frontend/src/__tests__/contrato/soporte.tsx
```

### Tramo 1

```text
feat(webconsole): tramo 1 — backend de front-design y seed de datos

Agrega inventarios, filtros, paginación, comparación, índice de traza y
umbrales del reporte, junto con las pruebas y el generador de datos local.
Conserva la igualdad exacta del reporte con los tres campos aditivos de D-4.

routers/experiments.py y run_backend.py entran desde 3500923; los añadidos
posteriores de historial tras reinicio y compatibilidad con servicios sin
inventario se conservan para el tramo 5 y quedan pendientes de decisión P-4.
Las exclusiones de capturas se incluyen completas por ser configuración
compartida con las herramientas del tramo 2.

Verificación del corte: frontend 397/397, tsc + vite build y compileall.
Backend validado con el código de este árbol y los repos hermanos enlazados
al entorno temporal; sin cambios a los tests para resolver rutas del entorno.

```

```text
M	webconsole/.gitignore
M	webconsole/backend/src/eovrt_webconsole/clips/inventory.py
M	webconsole/backend/src/eovrt_webconsole/clips/trim.py
M	webconsole/backend/src/eovrt_webconsole/experiment/applicability.py
M	webconsole/backend/src/eovrt_webconsole/experiment/control_backend.py
M	webconsole/backend/src/eovrt_webconsole/experiment/report.py
M	webconsole/backend/src/eovrt_webconsole/prompt_store.py
M	webconsole/backend/src/eovrt_webconsole/repo_catalog.py
M	webconsole/backend/src/eovrt_webconsole/routers/catalog.py
M	webconsole/backend/src/eovrt_webconsole/routers/experiments.py
M	webconsole/backend/src/eovrt_webconsole/routers/prompts.py
M	webconsole/backend/src/eovrt_webconsole/routers/runs.py
M	webconsole/backend/src/eovrt_webconsole/run_backend.py
M	webconsole/backend/src/eovrt_webconsole/trace.py
M	webconsole/backend/tests/fake_control_service.py
M	webconsole/backend/tests/fake_service.py
A	webconsole/backend/tests/test_artifacts_index.py
A	webconsole/backend/tests/test_conditions_catalog.py
A	webconsole/backend/tests/test_experiments_listing_fields.py
A	webconsole/backend/tests/test_metric_thresholds.py
A	webconsole/backend/tests/test_plugin_disabled_reason.py
A	webconsole/backend/tests/test_prompt_set_diff.py
M	webconsole/backend/tests/test_report_generator.py
A	webconsole/backend/tests/test_run_comparison.py
A	webconsole/backend/tests/test_run_created_at.py
A	webconsole/backend/tests/test_runs_listing_server_side.py
A	webconsole/backend/tests/test_trace_filter.py
A	webconsole/backend/tests/test_trace_index.py
A	webconsole/tools/seed_dev_data.py
```

### Tramo 2

```text
feat(webconsole): tramo 2 — capa de datos TanStack Query, sin cambio visual

Incorpora API modular, queries, caché compartida, proveedor, tipos y paleta.
Conserva pantallas, componentes, CSS y los seis hooks anteriores.
Vite mantiene 5173 y agrega strictPort; herramientas de captura reproducible.

Cierre de dependencias: api.ts se elimina en este corte para que las queries
resuelvan api/index.ts y sus nuevos endpoints, manteniendo las exportaciones
que usan los hooks antiguos. RunSummary conserva el alias de tipo del árbol
entregado, compatible con los lectores Record<string, unknown> anteriores.
Los módulos compartidos de queries entran completos con las invalidaciones
y el tipado opcional del distribuidor; sus consumidores visuales llegan después.

```

```text
M	webconsole/frontend/package-lock.json
M	webconsole/frontend/package.json
A	webconsole/frontend/src/__tests__/queryClient.test.ts
D	webconsole/frontend/src/api.ts
A	webconsole/frontend/src/api/endpoints.ts
A	webconsole/frontend/src/api/index.ts
A	webconsole/frontend/src/api/keys.ts
A	webconsole/frontend/src/api/queries/cameras.ts
A	webconsole/frontend/src/api/queries/catalog.ts
A	webconsole/frontend/src/api/queries/clips.ts
A	webconsole/frontend/src/api/queries/experiments.ts
A	webconsole/frontend/src/api/queries/platform.ts
A	webconsole/frontend/src/api/queries/promptSets.ts
A	webconsole/frontend/src/api/queries/runs.ts
A	webconsole/frontend/src/api/queries/sidebar.ts
A	webconsole/frontend/src/api/queryClient.ts
M	webconsole/frontend/src/main.tsx
A	webconsole/frontend/src/palette.ts
M	webconsole/frontend/src/runview.ts
A	webconsole/frontend/src/test-utils.tsx
M	webconsole/frontend/src/types.ts
M	webconsole/frontend/vite.config.ts
A	webconsole/tools/capture_console.mjs
A	webconsole/tools/capture_fixtures.mjs
```

### Tramo 3

```text
feat(webconsole): tramo 3 — ui.css y las pantallas troncales

Adopta composición, listado, detalle, traza y gráficos con sus pruebas.
D-8 conserva el lanzamiento DBE con target listo aunque control no responda;
el estado agregado permanece informativo. Mantiene el CSS de la píldora viva.

ComparePage y su prueba se adelantan desde el tramo 4 por el cambio compartido
de GroupedBars/SERIES_COLORS. Select y su regresión del label entran juntos
para que los selectores de Compose no se reabran al elegir una opción.
TargetBadge se difiere al tramo 4 junto con Shell; App.test incorpora sólo
el import del proveedor, dejando su adaptación al armazón para ese tramo.
Los módulos de gráficos/CSS y las queries del tramo 2 no se fragmentan para
recrear cambios intermedios que no pueden separarse limpiamente.

useLiveRun permanece hasta el tramo 4 porque la píldora anterior todavía lo
importa; retirarlo aquí rompía TypeScript.

CamerasPage y sus pruebas también se adelantan: comparten LivePromptPanel
con el detalle de corrida. El panel nuevo cambia los controles que consumía
la pantalla antigua y dejaba dos pruebas rojas; se mueve el conjunto ya
entregado, sin modificar las aserciones para acomodar ese corte intermedio.

```

```text
M	webconsole/frontend/src/__tests__/App.test.tsx
A	webconsole/frontend/src/__tests__/CamerasPage.preview-error.test.tsx
M	webconsole/frontend/src/__tests__/CamerasPage.test.tsx
M	webconsole/frontend/src/__tests__/ComparePage.test.tsx
A	webconsole/frontend/src/__tests__/ComposePage.preflight.test.tsx
M	webconsole/frontend/src/__tests__/ComposePage.test.tsx
M	webconsole/frontend/src/__tests__/EvalSection.test.tsx
M	webconsole/frontend/src/__tests__/LiveViewer.test.tsx
A	webconsole/frontend/src/__tests__/RunDetailArtifacts.test.tsx
M	webconsole/frontend/src/__tests__/RunDetailPage.test.tsx
M	webconsole/frontend/src/__tests__/RunKpiStrip.test.tsx
M	webconsole/frontend/src/__tests__/RunsPage.test.tsx
A	webconsole/frontend/src/__tests__/TraceQueries.final.test.tsx
M	webconsole/frontend/src/__tests__/TraceSection.test.tsx
A	webconsole/frontend/src/__tests__/api.endpoints.test.ts
M	webconsole/frontend/src/__tests__/api.test.ts
A	webconsole/frontend/src/__tests__/charts/ActivityTimeline.test.tsx
M	webconsole/frontend/src/__tests__/charts/GroupedBars.test.tsx
M	webconsole/frontend/src/__tests__/traceview.test.ts
A	webconsole/frontend/src/__tests__/ui/Select.field.test.tsx
D	webconsole/frontend/src/api.test.ts
M	webconsole/frontend/src/components/EvalSection.tsx
M	webconsole/frontend/src/components/LivePromptPanel.tsx
M	webconsole/frontend/src/components/LiveViewer.tsx
M	webconsole/frontend/src/components/RunKpiStrip.tsx
M	webconsole/frontend/src/components/RunTimeline.tsx
M	webconsole/frontend/src/components/TraceSection.tsx
M	webconsole/frontend/src/components/charts/ActivityTimeline.tsx
M	webconsole/frontend/src/components/charts/GroupedBars.tsx
M	webconsole/frontend/src/components/charts/Meter.tsx
M	webconsole/frontend/src/components/charts/Sparkline.tsx
M	webconsole/frontend/src/components/ui/Select.tsx
M	webconsole/frontend/src/components/ui/Table.tsx
M	webconsole/frontend/src/components/ui/icons.tsx
M	webconsole/frontend/src/components/ui/index.ts
M	webconsole/frontend/src/pages/CamerasPage.tsx
M	webconsole/frontend/src/pages/ComparePage.tsx
M	webconsole/frontend/src/pages/ComposePage.tsx
M	webconsole/frontend/src/pages/RunDetailPage.tsx
M	webconsole/frontend/src/pages/RunsPage.tsx
M	webconsole/frontend/src/styles/ui.css
M	webconsole/frontend/src/traceview.ts
D	webconsole/frontend/src/useFullTrace.ts
```

### Tramo 4

```text
feat(webconsole): tramo 4 — resto de pantallas y armazón

Adopta experimentos, prompts, cámaras, clips, plataforma, catálogo y 404.
Conserva la píldora de corrida viva global con useRunsEnCurso, también en
la barra colapsada y el cajón móvil. Retira los hooks antiguos sin consumidores.

Completa Shell, TargetBadge y las pruebas del armazón con el proveedor de
queries. El indicador visual del distribuidor se reserva para el tramo 5;
los tipos y queries compartidos entraron completos en el tramo 2.

```

```text
M	webconsole/frontend/src/App.tsx
M	webconsole/frontend/src/__tests__/App.test.tsx
M	webconsole/frontend/src/__tests__/ClipsPage.test.tsx
M	webconsole/frontend/src/__tests__/DeriveExperimentForm.test.tsx
M	webconsole/frontend/src/__tests__/ExperimentDetailPage.test.tsx
M	webconsole/frontend/src/__tests__/ExperimentDetailPageRiskBanner.test.tsx
A	webconsole/frontend/src/__tests__/ExperimentQueries.final.test.tsx
M	webconsole/frontend/src/__tests__/ExperimentsPage.new.test.tsx
M	webconsole/frontend/src/__tests__/ExperimentsPage.test.tsx
M	webconsole/frontend/src/__tests__/LiveRunPill.test.tsx
M	webconsole/frontend/src/__tests__/PlatformPage.test.tsx
M	webconsole/frontend/src/__tests__/PreviewWithBoxes.test.tsx
M	webconsole/frontend/src/__tests__/PromptSetEditor.test.tsx
M	webconsole/frontend/src/__tests__/PromptSetsPage.test.tsx
M	webconsole/frontend/src/__tests__/RecordPanel.test.tsx
A	webconsole/frontend/src/__tests__/Shell.live.test.tsx
M	webconsole/frontend/src/__tests__/Shell.test.tsx
M	webconsole/frontend/src/__tests__/TrimDialog.test.tsx
M	webconsole/frontend/src/__tests__/spec44c_gate.test.tsx
M	webconsole/frontend/src/__tests__/useServiceHealth.test.ts
M	webconsole/frontend/src/__tests__/useSidebarCounts.test.ts
M	webconsole/frontend/src/components/DeriveExperimentForm.tsx
M	webconsole/frontend/src/components/LiveRunPill.tsx
M	webconsole/frontend/src/components/RecordPanel.tsx
M	webconsole/frontend/src/components/Shell.tsx
M	webconsole/frontend/src/components/TargetBadge.tsx
M	webconsole/frontend/src/experimentview.ts
M	webconsole/frontend/src/pages/CatalogPage.tsx
M	webconsole/frontend/src/pages/ClipsPage.tsx
M	webconsole/frontend/src/pages/ExperimentDetailPage.tsx
M	webconsole/frontend/src/pages/ExperimentsPage.tsx
A	webconsole/frontend/src/pages/NotFoundPage.tsx
M	webconsole/frontend/src/pages/PlatformPage.tsx
M	webconsole/frontend/src/pages/PromptSetsPage.tsx
D	webconsole/frontend/src/useLiveRun.ts
D	webconsole/frontend/src/usePreflight.ts
D	webconsole/frontend/src/useServiceHealth.ts
D	webconsole/frontend/src/useSidebarCounts.ts
D	webconsole/frontend/src/useTarget.ts
```

### Tramo 5

```text
feat(webconsole): tramo 5 — salud del distribuidor y repaso integral

Agrega el cliente persistente y el sondeo informativo del tercer servicio,
con su indicador en Shell. Mantiene los gates específicos de los manifiestos
y los outcomes de distribución. Completa los archivos del árbol entregado.

P-4: la compatibilidad del inventario con servicios anteriores y la lectura
de evidencia tras reiniciar el BFF quedan explícitamente pendientes de
aceptación de alcance. Se conservan implementación y pruebas para revisión;
ni su inclusión en este commit ni las suites verdes aprueban esas capacidades.

```

```text
M	webconsole/README.md
M	webconsole/backend/src/eovrt_webconsole/app.py
M	webconsole/backend/src/eovrt_webconsole/preflight.py
M	webconsole/backend/src/eovrt_webconsole/routers/experiments.py
M	webconsole/backend/src/eovrt_webconsole/run_backend.py
A	webconsole/backend/tests/test_artifacts_legacy_service.py
A	webconsole/backend/tests/test_experiment_history.py
A	webconsole/backend/tests/test_preflight_distribution_health.py
A	webconsole/frontend/src/__tests__/Shell.distribution.test.tsx
M	webconsole/frontend/src/components/Shell.tsx
```

## Intentos intermedios: no son resultados de cierre

Se conservan para explicar la corrección del entorno y los límites de cada corte.

### Backend del corte 1 antes de enlazar los repos hermanos: 15 skips

```text
..................................................................ssss.. [  9%]
...........................ssssssssss................................... [ 18%]
........................................................................ [ 28%]
........................................................................ [ 37%]
........................................................................ [ 47%]
........................................................................ [ 56%]
.......................s................................................ [ 66%]
........................................................................ [ 75%]
........................................................................ [ 85%]
........................................................................ [ 94%]
.........................................                                [100%]
746 passed, 15 skipped in 72.83s (0:01:12)
```

### Primer build del corte 3: useLiveRun seguía siendo necesario para la píldora antigua

```text

> eovrt-webconsole-frontend@0.1.0 build
> tsc && vite build

src/components/LiveRunPill.tsx(2,28): error TS2307: Cannot find module '../useLiveRun' or its corresponding type declarations.
```

### Primer frontend del corte 3: Cámaras antigua no coincidía con LivePromptPanel nuevo

```text

> eovrt-webconsole-frontend@0.1.0 test
> vitest run


 RUN  v2.1.9 /tmp/eovrt-cortes-validation/webconsole/frontend

 ✓ src/__tests__/api.test.ts (15 tests) 295ms
stderr | src/__tests__/ExperimentDetailPage.test.tsx > ExperimentDetailPage > muestra las alertas y avisa que el conjunto no es temporal
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/RunsPage.test.tsx > RunsPage > lista corridas y marca la que está en curso
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ExperimentDetailPageRiskBanner.test.tsx > ExperimentDetailPage — banner de riesgo activo > muestra el banner con el condition_id cuando patterns no esta vacio y el experimento corre
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ExperimentsPage.test.tsx > ExperimentsPage > lista manifiestos y dispara un experimento con preflight verde
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/TrimDialog.test.tsx (9 tests) 822ms
stderr | src/__tests__/ExperimentsPage.new.test.tsx > ExperimentsPage - crear nuevo experimento (/experiments/new) > abre el formulario con un selector "basado en" precargado con el primer manifiesto
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/RunDetailPage.test.tsx > RunDetailPage > muestra el estado de la corrida con el glosario, no con el código crudo
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ComposePage.test.tsx > ComposePage prefill > conserva active_ids del manifiesto y no lo pisan los defaults del set
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/ExperimentDetailPageRiskBanner.test.tsx (7 tests) 894ms
   ✓ ExperimentDetailPage — banner de riesgo activo > muestra el banner con el condition_id cuando patterns no esta vacio y el experimento corre 481ms
stderr | src/__tests__/contrato/experimentos-distribucion.contrato.test.tsx > Contrato: experimentos y distribución > lista y abre un experimento con outcomes vinculados a cada alerta
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/ExperimentsPage.test.tsx (5 tests) 1521ms
   ✓ ExperimentsPage > lista manifiestos y dispara un experimento con preflight verde 787ms
 ✓ src/__tests__/ExperimentDetailPage.test.tsx (15 tests) 2018ms
   ✓ ExperimentDetailPage > muestra las alertas y avisa que el conjunto no es temporal 506ms
 ✓ src/__tests__/ExperimentsPage.new.test.tsx (4 tests) 2155ms
   ✓ ExperimentsPage - crear nuevo experimento (/experiments/new) > abre el formulario con un selector "basado en" precargado con el primer manifiesto 1110ms
   ✓ ExperimentsPage - crear nuevo experimento (/experiments/new) > al cambiar la fuente en el selector, vuelve a pedir los defaults y reprecarga los campos (bug central) 367ms
   ✓ ExperimentsPage - crear nuevo experimento (/experiments/new) > en modo nuevo la card dice "Nuevo experimento" y el botón "Crear" (no "Derivar de...") 410ms
stderr | src/__tests__/ComposePage.test.tsx > ComposePage prefill de source.type video > conserva el source.type original en la composición (round-trip sin colapso a video_file)
No routes matched location "/runs/r1"

 ✓ src/__tests__/DeriveExperimentForm.test.tsx (13 tests) 2351ms
   ✓ DeriveExperimentForm > precarga los valores del manifiesto fuente 628ms
 ✓ src/__tests__/ComparePage.test.tsx (14 tests) 2735ms
   ✓ ComparePage > lista las corridas por nombre, no por identificador crudo 684ms
   ✓ ComparePage > compara al elegir dos y nombra las métricas en español 484ms
   ✓ ComparePage > resalta el mejor valor de cada fila 350ms
   ✓ ComparePage > informa las corridas que quedaron afuera en vez de omitirlas en silencio 310ms
 ✓ src/__tests__/RunDetailPage.test.tsx (10 tests) 2266ms
   ✓ RunDetailPage > muestra el estado de la corrida con el glosario, no con el código crudo 318ms
   ✓ RunDetailPage > las pestañas separan traza, resumen, evaluación y archivos 481ms
   ✓ RunDetailPage > confirmar borra la corrida y vuelve al listado 309ms
   ✓ RunDetailPage > borrado parcial muestra el detalle de los planos que fallaron y persiste (no navega) 333ms
 ✓ src/__tests__/RecordPanel.test.tsx (13 tests) 3542ms
   ✓ RecordPanel > mientras graba, consulta el backend periodicamente y muestra elapsed_ms/size_bytes de ahi 1096ms
   ✓ RecordPanel > si el backend informa error, deja de contar y muestra el motivo 1170ms
 ✓ src/__tests__/contrato/experimentos-distribucion.contrato.test.tsx (4 tests) 2705ms
   ✓ Contrato: experimentos y distribución > lista y abre un experimento con outcomes vinculados a cada alerta 1117ms
   ✓ Contrato: experimentos y distribución > deriva un manifiesto con overrides y lanza la derivación seleccionada 993ms
   ✓ Contrato: experimentos y distribución > seleccionar dos corridas evaluadas pide su comparación por HTTP 389ms
stderr | src/__tests__/Shell.test.tsx > Shell > renderiza los tres títulos de grupo
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/TraceSection.test.tsx (10 tests) 3458ms
   ✓ TraceSection > no vuelca todos los cuadros: la lista se acota y dice el total 2005ms
   ✓ TraceSection > el filtro de solo alertas deja únicamente los cuadros con alerta 313ms
 ✓ src/__tests__/Shell.test.tsx (17 tests) 3372ms
   ✓ Shell > renderiza los tres títulos de grupo 450ms
   ✓ Shell > acorta la etiqueta que no entra, sin perder el nombre completo 420ms
stderr | src/__tests__/ComposePage.test.tsx > ComposePage nombre opcional de la corrida > manda run.name cuando se completa, null cuando se deja vacío
No routes matched location "/runs/r1"

stderr | src/__tests__/contrato/nueva-corrida.contrato.test.tsx > Contrato: nueva corrida > consulta preflight, compone fuente y prompts, lanza y abre el detalle real
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ComposePage.test.tsx > ComposePage nombre opcional de la corrida > deja run.name en null si el campo queda vacío (usa el id autogenerado)
No routes matched location "/runs/r2"

 ✓ src/__tests__/labels.test.ts (13 tests) 49ms
stderr | src/__tests__/CamerasPage.test.tsx > CamerasPage > lista los presets de cámara
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/PromptSetEditor.test.tsx (5 tests) 832ms
   ✓ PromptSetEditor > exploratory: permite editar y guardar via updatePromptSet 333ms
 ✓ src/__tests__/experimentview.test.ts (15 tests) 14ms
 ✓ src/__tests__/traceview.test.ts (12 tests) 12ms
 ✓ src/__tests__/LiveViewer.test.tsx (5 tests) 152ms
 ✓ src/__tests__/PreviewWithBoxes.test.tsx (8 tests) 195ms
stderr | src/__tests__/spec44c_gate.test.tsx > spec44c gate: flujo de experimentos por la UI > ExperimentsPage: lista un manifiesto y dispara runExperiment al hacer click en "Ejecutar experimento"
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/contrato/nueva-corrida.contrato.test.tsx (3 tests) 3053ms
   ✓ Contrato: nueva corrida > consulta preflight, compone fuente y prompts, lanza y abre el detalle real 2007ms
   ✓ Contrato: nueva corrida > impide lanzar con el formulario completo si el target aún no está listo 557ms
   ✓ Contrato: nueva corrida > muestra los bloqueos del preflight y permite lanzar sólo medios con target listo 486ms
 ✓ src/__tests__/runview.test.ts (17 tests) 17ms
 ✓ src/__tests__/useServiceHealth.test.ts (5 tests) 333ms
 ✓ src/__tests__/spec44c_gate.test.tsx (3 tests) 685ms
   ✓ spec44c gate: flujo de experimentos por la UI > ExperimentsPage: lista un manifiesto y dispara runExperiment al hacer click en "Ejecutar experimento" 477ms
 ✓ src/__tests__/RunsPage.test.tsx (22 tests) 6918ms
   ✓ RunsPage > lista corridas y marca la que está en curso 874ms
   ✓ RunsPage > el pedido de la página lleva el filtro, el orden y la página al servidor 1523ms
   ✓ RunsPage > el buscador manda `q` al servidor en vez de filtrar en el cliente 938ms
   ✓ RunsPage > el segmentado manda `estado` al servidor 361ms
   ✓ RunsPage > ordenar cambia `orden` y `direccion`, y el tercer click vuelve al orden por fecha 401ms
   ✓ RunsPage > el total es el del servidor, no la cantidad de filas de la página 431ms
 ✓ src/__tests__/charts/ActivityTimeline.test.tsx (7 tests) 777ms
 ✓ src/__tests__/RunKpiStrip.test.tsx (7 tests) 1045ms
   ✓ RunKpiStrip > rotula con el glosario, nunca con la clave cruda del sumario 455ms
 ❯ src/__tests__/CamerasPage.test.tsx (7 tests | 2 failed) 3132ms
   ✓ CamerasPage > muestra banner y deshabilita conectar ante 409 run_active 349ms
   × CamerasPage > activa por defecto las clases sin enabled_by_default declarado en el YAML 1081ms
     → Unable to find a label with the text of: /detección \(desmarcado/i

Ignored nodes: comments, script, style
<body>
  <div>
    <div>
      <header
        class="eo-pageheader"
      >
        <div>
          <h1>
            Cámaras
          </h1>
        </div>
      </header>
      <section
        class="eo-card"
      >
        <h3
          class="eo-card__title"
        >
          Viewer
        </h3>
        <div
          class="eo-card__body"
        >
          <div
            class="eo-live-viewer"
            style="aspect-ratio: 1.7777777777777777;"
          >
            <canvas
              class="eo-live-viewer__canvas"
            />
            <span
              class="eo-live-viewer__empty"
            >
              sin señal
            </span>
            <div
              class="eo-live-viewer__overlay"
            >
              <span
                class="eo-badge eo-badge--neutral"
              >
                desconectado
              </span>
              <span>
                0
                 cuadros/s
              </span>
              <span>
                modo:
                imagen directa
              </span>
            </div>
          </div>
        </div>
      </section>
      <section
        class="record-panel"
      >
        <h3>
          Grabar toma
        </h3>
        <label
          for="rec-camera"
        >
          Cámara
        </label>
        <select
          id="rec-camera"
        >
          <option
            value=""
          >
            — elegir cámara —
          </option>
          <option
            value="oak_d_lab"
          >
            OAK-D laboratorio
             (
            oak_d
            )
          </option>
        </select>
        <label
          for="rec-scenario"
        >
          Escenario
        </label>
        <select
          id="rec-scenario"
        >
          <option
            value="P1"
          >
            P1
          </option>
          <option
            value="P2"
          >
            P2
          </option>
          <option
            value="P3"
          >
            P3
          </option>
          <option
            value="P4"
          >
            P4
          </option>
          <option
            value="P5"
          >
            P5
          </option>
          <option
            value="P6"
          >
            P6
          </option>
          <option
            value="P7"
          >
            P7
          </option>
          <option
            value="P8"
          >
            P8
          </option>
          <option
            value="P9"
          >
            P9
          </option>
        </select>
        <label
          for="rec-variant"
        >
          Variante
        </label>
        <select
          id="rec-variant"
        >
          <option
            value="a"
          >
            a
          </option>
          <option
            value="b"
          >
            b
          </option>
          <option
            value="c"
          >
            c
          </option>
        </select>
        <p
          class="record-basename"
        >
          Próxima toma:
          <strong>
            —
          </strong>
        </p>
        <button
          disabled=""
          type="button"
        >
          Grabar
        </button>
        <p
          class="eo-note"
        >
          Elegí una cámara para poder grabar.
        </p>
        <p
          class="record-error"
        >
          Failed to parse URL from /api/recordings/next?scenario=P1&variant=a
        </p>
      </section>
      <div
        style="display: grid; grid-template-columns: minmax(220px, 1fr) minmax(280px, 1.4fr); gap: var(--space-5); align-items: start; margin-top: var(--space-5);"
      >
        <section
          class="eo-card"
        >
          <h3
            class="eo-card__title"
          >
            Presets
          </h3>
          <div
            class="eo-card__body"
          >
            <button
              type="button"
            >
              Nuevo preset
            </button>
            <ul
              class="eo-list"
            >
              <li>
                <span>
                  OAK-D laboratorio
                </span>

                <small
                  class="eo-note"
                >
                  (
                  oak_d
                  )
                </small>
                <div
                  class="eo-actions"
                >
                  <button
                    type="button"
                  >
                    Conectar
                  </button>
                  <button
                    type="button"
                  >
                    Editar
                  </button>
                  <button
                    class="eo-btn--danger"
                    type="button"
                  >
                    Eliminar
                  </button>
                </div>
              </li>
            </ul>
          </div>
        </section>
        <section
          class="eo-card"
        >
          <h3
            class="eo-card__title"
          >
            Qué mostrar
          </h3>
          <div
            class="eo-card__body"
          >
            <div
              class="eo-segmented"
            >
              <button
                aria-pressed="true"
                type="button"
              >
                Imagen directa
              </button>
              <button
                aria-pressed="false"
                type="button"
              >
                Con detecciones
              </button>
            </div>
            <p
              class="eo-cap"
            >
              La imagen directa no pasa por el modelo: sirve para verificar encuadre, foco y luz.
            </p>
            <div
              class="eo-actions"
            >
              <button
                class="eo-btn eo-btn--primary"
                disabled=""
                type="button"
              >
                Aplicar
              </button>
            </div>
          </div>
        </section>
      </div>
    </div>
  </div>
</body>

Ignored nodes: comments, script, style
<body>
  <div>
    <div>
      <header
        class="eo-pageheader"
      >
        <div>
          <h1>
            Cámaras
          </h1>
        </div>
      </header>
      <section
        class="eo-card"
      >
        <h3
          class="eo-card__title"
        >
          Viewer
        </h3>
        <div
          class="eo-card__body"
        >
          <div
            class="eo-live-viewer"
            style="aspect-ratio: 1.7777777777777777;"
          >
            <canvas
              class="eo-live-viewer__canvas"
            />
            <span
              class="eo-live-viewer__empty"
            >
              sin señal
            </span>
            <div
              class="eo-live-viewer__overlay"
            >
              <span
                class="eo-badge eo-badge--neutral"
              >
                desconectado
              </span>
              <span>
                0
                 cuadros/s
              </span>
              <span>
                modo:
                imagen directa
              </span>
            </div>
          </div>
        </div>
      </section>
      <section
        class="record-panel"
      >
        <h3>
          Grabar toma
        </h3>
        <label
          for="rec-camera"
        >
          Cámara
        </label>
        <select
          id="rec-camera"
        >
          <option
            value=""
          >
            — elegir cámara —
          </option>
          <option
            value="oak_d_lab"
          >
            OAK-D laboratorio
             (
            oak_d
            )
          </option>
        </select>
        <label
          for="rec-scenario"
        >
          Escenario
        </label>
        <select
          id="rec-scenario"
        >
          <option
            value="P1"
          >
            P1
          </option>
          <option
            value="P2"
          >
            P2
          </option>
          <option
            value="P3"
          >
            P3
          </option>
          <option
            value="P4"
          >
            P4
          </option>
          <option
            value="P5"
          >
            P5
          </option>
          <option
            value="P6"
          >
            P6
          </option>
          <option
            value="P7"
          >
            P7
          </option>
          <option
            value="P8"
          >
            P8
          </option>
          <option
            value="P9"
          >
            P9
          </option>
        </select>
        <label
          for="rec-variant"
        >
          Variante
        </label>
        <select
          id="rec-variant"
        >
          <option
            value="a"
          >
            a
          </option>
          <option
            value="b"
          >
            b
          </option>
          <option
            value="c"
          >
            c
          </option>
        </select>
        <p
          class="record-basename"
        >
          Próxima toma:
          <strong>
            —
          </strong>
        </p>
        <button
          disabled=""
          type="button"
        >
          Grabar
        </button>
        <p
          class="eo-note"
        >
          Elegí una cámara para poder grabar.
        </p>
        <p
          class="record-error"
        >
          Failed to parse URL from /api/recordings/next?scenario=P1&variant=a
        </p>
      </section>
      <div
        style="display: grid; grid-template-columns: minmax(220px, 1fr) minmax(280px, 1.4fr); gap: var(--space-5); align-items: start; margin-top: var(--space-5);"
      >
        <section
          class="eo-card"
        >
          <h3
            class="eo-card__title"
          >
            Presets
          </h3>
          <div
            class="eo-card__body"
          >
            <button
              type="button"
            >
              Nuevo preset
            </button>
            <ul
              class="eo-list"
            >
              <li>
                <span>
                  OAK-D laboratorio
                </span>

                <small
                  class="eo-note"
                >
                  (
                  oak_d
                  )
                </small>
                <div
                  class="eo-actions"
                >
                  <button
                    type="button"
                  >
                    Conectar
                  </button>
                  <button
                    type="button"
                  >
                    Editar
                  </button>
                  <button
                    class="eo-btn--danger"
                    type="button"
                  >
                    Eliminar
                  </button>
                </div>
              </li>
            </ul>
          </div>
        </section>
        <section
          class="eo-card"
        >
          <h3
            class="eo-card__title"
          >
            Qué mostrar
          </h3>
          <div
            class="eo-card__body"
          >
            <div
              class="eo-segmented"
            >
              <button
                aria-pressed="true"
                type="button"
              >
                Imagen directa
              </button>
              <button
                aria-pressed="false"
                type="button"
              >
                Con detecciones
              </button>
            </div>
            <p
              class="eo-cap"
            >
              La imagen directa no pasa por el modelo: sirve para verificar encuadre, foco y luz.
            </p>
            <div
              class="eo-actions"
            >
              <button
                class="eo-btn eo-btn--primary"
                disabled=""
                type="button"
              >
                Aplicar
              </button>
            </div>
          </div>
        </section>
      </div>
    </div>
  </div>
</body>
   × CamerasPage > deshabilita Conectar en modo detect sin prompt set cargado 1074ms
     → Unable to find a label with the text of: /detección \(desmarcado/i

Ignored nodes: comments, script, style
<body>
  <div>
    <div>
      <header
        class="eo-pageheader"
      >
        <div>
          <h1>
            Cámaras
          </h1>
        </div>
      </header>
      <section
        class="eo-card"
      >
        <h3
          class="eo-card__title"
        >
          Viewer
        </h3>
        <div
          class="eo-card__body"
        >
          <div
            class="eo-live-viewer"
            style="aspect-ratio: 1.7777777777777777;"
          >
            <canvas
              class="eo-live-viewer__canvas"
            />
            <span
              class="eo-live-viewer__empty"
            >
              sin señal
            </span>
            <div
              class="eo-live-viewer__overlay"
            >
              <span
                class="eo-badge eo-badge--neutral"
              >
                desconectado
              </span>
              <span>
                0
                 cuadros/s
              </span>
              <span>
                modo:
                imagen directa
              </span>
            </div>
          </div>
        </div>
      </section>
      <section
        class="record-panel"
      >
        <h3>
          Grabar toma
        </h3>
        <label
          for="rec-camera"
        >
          Cámara
        </label>
        <select
          id="rec-camera"
        >
          <option
            value=""
          >
            — elegir cámara —
          </option>
          <option
            value="oak_d_lab"
          >
            OAK-D laboratorio
             (
            oak_d
            )
          </option>
        </select>
        <label
          for="rec-scenario"
        >
          Escenario
        </label>
        <select
          id="rec-scenario"
        >
          <option
            value="P1"
          >
            P1
          </option>
          <option
            value="P2"
          >
            P2
          </option>
          <option
            value="P3"
          >
            P3
          </option>
          <option
            value="P4"
          >
            P4
          </option>
          <option
            value="P5"
          >
            P5
          </option>
          <option
            value="P6"
          >
            P6
          </option>
          <option
            value="P7"
          >
            P7
          </option>
          <option
            value="P8"
          >
            P8
          </option>
          <option
            value="P9"
          >
            P9
          </option>
        </select>
        <label
          for="rec-variant"
        >
          Variante
        </label>
        <select
          id="rec-variant"
        >
          <option
            value="a"
          >
            a
          </option>
          <option
            value="b"
          >
            b
          </option>
          <option
            value="c"
          >
            c
          </option>
        </select>
        <p
          class="record-basename"
        >
          Próxima toma:
          <strong>
            —
          </strong>
        </p>
        <button
          disabled=""
          type="button"
        >
          Grabar
        </button>
        <p
          class="eo-note"
        >
          Elegí una cámara para poder grabar.
        </p>
        <p
          class="record-error"
        >
          Failed to parse URL from /api/recordings/next?scenario=P1&variant=a
        </p>
      </section>
      <div
        style="display: grid; grid-template-columns: minmax(220px, 1fr) minmax(280px, 1.4fr); gap: var(--space-5); align-items: start; margin-top: var(--space-5);"
      >
        <section
          class="eo-card"
        >
          <h3
            class="eo-card__title"
          >
            Presets
          </h3>
          <div
            class="eo-card__body"
          >
            <button
              type="button"
            >
              Nuevo preset
            </button>
            <ul
              class="eo-list"
            >
              <li>
                <span>
                  OAK-D laboratorio
                </span>

                <small
                  class="eo-note"
                >
                  (
                  oak_d
                  )
                </small>
                <div
                  class="eo-actions"
                >
                  <button
                    type="button"
                  >
                    Conectar
                  </button>
                  <button
                    type="button"
                  >
                    Editar
                  </button>
                  <button
                    class="eo-btn--danger"
                    type="button"
                  >
                    Eliminar
                  </button>
                </div>
              </li>
            </ul>
          </div>
        </section>
        <section
          class="eo-card"
        >
          <h3
            class="eo-card__title"
          >
            Qué mostrar
          </h3>
          <div
            class="eo-card__body"
          >
            <div
              class="eo-segmented"
            >
              <button
                aria-pressed="true"
                type="button"
              >
                Imagen directa
              </button>
              <button
                aria-pressed="false"
                type="button"
              >
                Con detecciones
              </button>
            </div>
            <p
              class="eo-cap"
            >
              La imagen directa no pasa por el modelo: sirve para verificar encuadre, foco y luz.
            </p>
            <div
              class="eo-actions"
            >
              <button
                class="eo-btn eo-btn--primary"
                disabled=""
                type="button"
              >
                Aplicar
              </button>
            </div>
          </div>
        </section>
      </div>
    </div>
  </div>
</body>

Ignored nodes: comments, script, style
<body>
  <div>
    <div>
      <header
        class="eo-pageheader"
      >
        <div>
          <h1>
            Cámaras
          </h1>
        </div>
      </header>
      <section
        class="eo-card"
      >
        <h3
          class="eo-card__title"
        >
          Viewer
        </h3>
        <div
          class="eo-card__body"
        >
          <div
            class="eo-live-viewer"
            style="aspect-ratio: 1.7777777777777777;"
          >
            <canvas
              class="eo-live-viewer__canvas"
            />
            <span
              class="eo-live-viewer__empty"
            >
              sin señal
            </span>
            <div
              class="eo-live-viewer__overlay"
            >
              <span
                class="eo-badge eo-badge--neutral"
              >
                desconectado
              </span>
              <span>
                0
                 cuadros/s
              </span>
              <span>
                modo:
                imagen directa
              </span>
            </div>
          </div>
        </div>
      </section>
      <section
        class="record-panel"
      >
        <h3>
          Grabar toma
        </h3>
        <label
          for="rec-camera"
        >
          Cámara
        </label>
        <select
          id="rec-camera"
        >
          <option
            value=""
          >
            — elegir cámara —
          </option>
          <option
            value="oak_d_lab"
          >
            OAK-D laboratorio
             (
            oak_d
            )
          </option>
        </select>
        <label
          for="rec-scenario"
        >
          Escenario
        </label>
        <select
          id="rec-scenario"
        >
          <option
            value="P1"
          >
            P1
          </option>
          <option
            value="P2"
          >
            P2
          </option>
          <option
            value="P3"
          >
            P3
          </option>
          <option
            value="P4"
          >
            P4
          </option>
          <option
            value="P5"
          >
            P5
          </option>
          <option
            value="P6"
          >
            P6
          </option>
          <option
            value="P7"
          >
            P7
          </option>
          <option
            value="P8"
          >
            P8
          </option>
          <option
            value="P9"
          >
            P9
          </option>
        </select>
        <label
          for="rec-variant"
        >
          Variante
        </label>
        <select
          id="rec-variant"
        >
          <option
            value="a"
          >
            a
          </option>
          <option
            value="b"
          >
            b
          </option>
          <option
            value="c"
          >
            c
          </option>
        </select>
        <p
          class="record-basename"
        >
          Próxima toma:
          <strong>
            —
          </strong>
        </p>
        <button
          disabled=""
          type="button"
        >
          Grabar
        </button>
        <p
          class="eo-note"
        >
          Elegí una cámara para poder grabar.
        </p>
        <p
          class="record-error"
        >
          Failed to parse URL from /api/recordings/next?scenario=P1&variant=a
        </p>
      </section>
      <div
        style="display: grid; grid-template-columns: minmax(220px, 1fr) minmax(280px, 1.4fr); gap: var(--space-5); align-items: start; margin-top: var(--space-5);"
      >
        <section
          class="eo-card"
        >
          <h3
            class="eo-card__title"
          >
            Presets
          </h3>
          <div
            class="eo-card__body"
          >
            <button
              type="button"
            >
              Nuevo preset
            </button>
            <ul
              class="eo-list"
            >
              <li>
                <span>
                  OAK-D laboratorio
                </span>

                <small
                  class="eo-note"
                >
                  (
                  oak_d
                  )
                </small>
                <div
                  class="eo-actions"
                >
                  <button
                    type="button"
                  >
                    Conectar
                  </button>
                  <button
                    type="button"
                  >
                    Editar
                  </button>
                  <button
                    class="eo-btn--danger"
                    type="button"
                  >
                    Eliminar
                  </button>
                </div>
              </li>
            </ul>
          </div>
        </section>
        <section
          class="eo-card"
        >
          <h3
            class="eo-card__title"
          >
            Qué mostrar
          </h3>
          <div
            class="eo-card__body"
          >
            <div
              class="eo-segmented"
            >
              <button
                aria-pressed="true"
                type="button"
              >
                Imagen directa
              </button>
              <button
                aria-pressed="false"
                type="button"
              >
                Con detecciones
              </button>
            </div>
            <p
              class="eo-cap"
            >
              La imagen directa no pasa por el modelo: sirve para verificar encuadre, foco y luz.
            </p>
            <div
              class="eo-actions"
            >
              <button
                class="eo-btn eo-btn--primary"
                disabled=""
                type="button"
              >
                Aplicar
              </button>
            </div>
          </div>
        </section>
      </div>
    </div>
  </div>
</body>
 ✓ src/__tests__/charts/GroupedBars.test.tsx (8 tests) 361ms
 ✓ src/__tests__/runseries.test.ts (12 tests) 22ms
 ✓ src/__tests__/charts/timeline.test.ts (9 tests) 59ms
stderr | src/__tests__/ComposePage.test.tsx > ComposePage fuente RTSP > al elegir rtsp muestra el campo de dirección y arma config { url }
No routes matched location "/runs/r1"

stderr | src/__tests__/RunDetailArtifacts.test.tsx > expone el inventario limitado del servicio anterior con descargas verificadas
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ComposePage.test.tsx > ComposePage cámara guardada (oak_d) > lanza con la config de la cámara guardada elegida
No routes matched location "/runs/r1"

 ✓ src/__tests__/ComposePage.test.tsx (18 tests) 10270ms
   ✓ ComposePage prefill > conserva active_ids del manifiesto y no lo pisan los defaults del set 1521ms
   ✓ ComposePage prefill de source.type video > conserva el source.type original en la composición (round-trip sin colapso a video_file) 769ms
   ✓ ComposePage prefill survives catalog re-fetch (no clobber) > no reaplica el manifiesto cuando `experiments` cambia de referencia tras un re-fetch 745ms
   ✓ ComposePage nombre opcional de la corrida > manda run.name cuando se completa, null cuando se deja vacío 629ms
   ✓ ComposePage nombre opcional de la corrida > deja run.name en null si el campo queda vacío (usa el id autogenerado) 884ms
   ✓ ComposePage aviso de 409 al lanzar > muestra aviso de prueba de cámara activa ante 409 preview_active 601ms
   ✓ ComposePage aviso de 409 al lanzar > muestra aviso de corrida activa ante 409 con active_run_id 425ms
   ✓ ComposePage panel «Antes de lanzar» > los requisitos se van cumpliendo y el botón se habilita al final 473ms
   ✓ ComposePage panel «Antes de lanzar» > desactivar todas las clases vuelve a bloquear, diciendo qué falta 926ms
   ✓ ComposePage rejilla de fuentes > muestra el nombre legible de cada fuente, no su identificador 450ms
   ✓ ComposePage rejilla de fuentes > una fuente deshabilitada explica el motivo que manda el backend 370ms
   ✓ ComposePage rejilla de fuentes > la fuente elegida queda marcada con aria-pressed 376ms
   ✓ ComposePage fuente RTSP > bloquea el lanzamiento si la dirección RTSP trae credenciales censuradas (***) 465ms
   ✓ ComposePage fuente RTSP > al elegir rtsp muestra el campo de dirección y arma config { url } 502ms
   ✓ ComposePage cámara guardada (oak_d) > lanza con la config de la cámara guardada elegida 679ms
 ✓ src/__tests__/TraceQueries.final.test.tsx (1 test) 93ms
 ✓ src/__tests__/ui/Table.test.tsx (6 tests) 623ms
 ✓ src/__tests__/charts/layout.test.ts (9 tests) 88ms
 ✓ src/__tests__/ClipsPage.test.tsx (5 tests) 701ms
   ✓ ClipsPage > lista masters y clips 308ms
 ✓ src/__tests__/ui/primitives.test.tsx (10 tests) 554ms
 ✓ src/__tests__/EvalSection.test.tsx (4 tests) 594ms
   ✓ EvalSection > evalúa al click y muestra la tabla con mAP 327ms
 ✓ src/__tests__/RunDetailArtifacts.test.tsx (3 tests) 1815ms
   ✓ expone el inventario limitado del servicio anterior con descargas verificadas 826ms
   ✓ actualiza los archivos después de evaluar sin recargar el detalle 709ms
 ✓ src/__tests__/PlatformPage.test.tsx (3 tests) 547ms
   ✓ PlatformPage > lista el fleet y activa una instancia 311ms
stderr | src/__tests__/ComposePage.preflight.test.tsx > ComposePage: bloqueos de preflight > informa los motivos con ready=false sin bloquear DBE y los actualiza por polling
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/contrato/corrida-viva.contrato.test.tsx > Contrato: corrida viva > permite alcanzar la corrida activa desde una ruta distinta del listado
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/ui/Select.test.tsx (5 tests) 816ms
   ✓ Select > abre la lista al hacer click en el control 412ms
 ✓ src/__tests__/nav.test.ts (10 tests) 27ms
stderr | src/__tests__/contrato/detalle-traza-evaluacion.contrato.test.tsx > Contrato: detalle, traza y evaluación > lee detalle y traza, permite inspeccionar cuadros y evaluar contra BENCH
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/contrato/corrida-viva.contrato.test.tsx (2 tests) 1373ms
   ✓ Contrato: corrida viva > permite alcanzar la corrida activa desde una ruta distinta del listado 736ms
   ✓ Contrato: corrida viva > consulta mientras corre, permite detener y cesa el polling del detalle al terminar 612ms
 ✓ src/__tests__/ComposePage.preflight.test.tsx (2 tests) 2845ms
   ✓ ComposePage: bloqueos de preflight > informa los motivos con ready=false sin bloquear DBE y los actualiza por polling 2122ms
   ✓ ComposePage: bloqueos de preflight > informa los motivos con ready=true sin bloquear DBE y los actualiza por polling 721ms
 ✓ src/__tests__/api.endpoints.test.ts (4 tests) 67ms
 ✓ src/__tests__/PromptSetsPage.test.tsx (2 tests) 1001ms
   ✓ PromptSetsPage > un set frozen se muestra read-only con acción Derivar 695ms
 ✓ src/__tests__/contrato/detalle-traza-evaluacion.contrato.test.tsx (1 test) 1603ms
   ✓ Contrato: detalle, traza y evaluación > lee detalle y traza, permite inspeccionar cuadros y evaluar contra BENCH 1586ms
 ✓ src/__tests__/charts/Meter.test.tsx (5 tests) 390ms
 ✓ src/__tests__/queryClient.test.ts (4 tests) 19ms
 ✓ src/__tests__/experiment-api.test.ts (4 tests) 24ms
 ✓ src/__tests__/useSidebarCounts.test.ts (2 tests) 243ms
 ✓ src/__tests__/stream.test.ts (3 tests) 10ms
stderr | src/__tests__/LiveRunPill.test.tsx > LiveRunPill > no renderiza nada si no hay corrida viva
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/LiveRunPill.test.tsx (3 tests) 749ms
   ✓ LiveRunPill > muestra el run vivo con fps y linkea a su detalle 583ms
 ✓ src/__tests__/ui/Button.test.tsx (5 tests) 434ms
 ✓ src/__tests__/preview.test.ts (2 tests) 19ms
stderr | src/__tests__/App.test.tsx > App > renderiza el título de la consola
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/App.test.tsx (2 tests) 450ms
   ✓ App > renderiza el título de la consola 309ms
 ✓ src/__tests__/ui/Banner.test.tsx (3 tests) 388ms
   ✓ Banner > tono warn con boton de cerrar 312ms
 ✓ src/__tests__/ui/InlineDeleteConfirm.test.tsx (2 tests) 324ms
 ✓ src/__tests__/promptview.test.ts (3 tests) 9ms
 ✓ src/__tests__/ui/Select.field.test.tsx (1 test) 349ms
   ✓ Select dentro de Field > cancela la activación del label al elegir, sin reabrir el control 346ms
 ✓ src/__tests__/ui/Badge.test.tsx (4 tests) 106ms
 ✓ src/__tests__/ui/SearchInput.test.tsx (1 test) 166ms
 ✓ src/__tests__/ui/ConditionName.test.tsx (3 tests) 113ms
 ✓ src/__tests__/ui/SegmentedControl.test.tsx (2 tests) 323ms
 ✓ src/__tests__/ui/icons.test.tsx (1 test) 71ms
 ✓ src/__tests__/ui/PageHeader.test.tsx (2 tests) 353ms
   ✓ PageHeader > renderiza titulo, meta y acciones 308ms

⎯⎯⎯⎯⎯⎯⎯ Failed Tests 2 ⎯⎯⎯⎯⎯⎯⎯

 FAIL  src/__tests__/CamerasPage.test.tsx > CamerasPage > activa por defecto las clases sin enabled_by_default declarado en el YAML
TestingLibraryElementError: Unable to find a label with the text of: /detección \(desmarcado/i

Ignored nodes: comments, script, style
<body>
  <div>
    <div>
      <header
        class="eo-pageheader"
      >
        <div>
          <h1>
            Cámaras
          </h1>
        </div>
      </header>
      <section
        class="eo-card"
      >
        <h3
          class="eo-card__title"
        >
          Viewer
        </h3>
        <div
          class="eo-card__body"
        >
          <div
            class="eo-live-viewer"
            style="aspect-ratio: 1.7777777777777777;"
          >
            <canvas
              class="eo-live-viewer__canvas"
            />
            <span
              class="eo-live-viewer__empty"
            >
              sin señal
            </span>
            <div
              class="eo-live-viewer__overlay"
            >
              <span
                class="eo-badge eo-badge--neutral"
              >
                desconectado
              </span>
              <span>
                0
                 cuadros/s
              </span>
              <span>
                modo:
                imagen directa
              </span>
            </div>
          </div>
        </div>
      </section>
      <section
        class="record-panel"
      >
        <h3>
          Grabar toma
        </h3>
        <label
          for="rec-camera"
        >
          Cámara
        </label>
        <select
          id="rec-camera"
        >
          <option
            value=""
          >
            — elegir cámara —
          </option>
          <option
            value="oak_d_lab"
          >
            OAK-D laboratorio
             (
            oak_d
            )
          </option>
        </select>
        <label
          for="rec-scenario"
        >
          Escenario
        </label>
        <select
          id="rec-scenario"
        >
          <option
            value="P1"
          >
            P1
          </option>
          <option
            value="P2"
          >
            P2
          </option>
          <option
            value="P3"
          >
            P3
          </option>
          <option
            value="P4"
          >
            P4
          </option>
          <option
            value="P5"
          >
            P5
          </option>
          <option
            value="P6"
          >
            P6
          </option>
          <option
            value="P7"
          >
            P7
          </option>
          <option
            value="P8"
          >
            P8
          </option>
          <option
            value="P9"
          >
            P9
          </option>
        </select>
        <label
          for="rec-variant"
        >
          Variante
        </label>
        <select
          id="rec-variant"
        >
          <option
            value="a"
          >
            a
          </option>
          <option
            value="b"
          >
            b
          </option>
          <option
            value="c"
          >
            c
          </option>
        </select>
        <p
          class="record-basename"
        >
          Próxima toma:
          <strong>
            —
          </strong>
        </p>
        <button
          disabled=""
          type="button"
        >
          Grabar
        </button>
        <p
          class="eo-note"
        >
          Elegí una cámara para poder grabar.
        </p>
        <p
          class="record-error"
        >
          Failed to parse URL from /api/recordings/next?scenario=P1&variant=a
        </p>
      </section>
      <div
        style="display: grid; grid-template-columns: minmax(220px, 1fr) minmax(280px, 1.4fr); gap: var(--space-5); align-items: start; margin-top: var(--space-5);"
      >
        <section
          class="eo-card"
        >
          <h3
            class="eo-card__title"
          >
            Presets
          </h3>
          <div
            class="eo-card__body"
          >
            <button
              type="button"
            >
              Nuevo preset
            </button>
            <ul
              class="eo-list"
            >
              <li>
                <span>
                  OAK-D laboratorio
                </span>

                <small
                  class="eo-note"
                >
                  (
                  oak_d
                  )
                </small>
                <div
                  class="eo-actions"
                >
                  <button
                    type="button"
                  >
                    Conectar
                  </button>
                  <button
                    type="button"
                  >
                    Editar
                  </button>
                  <button
                    class="eo-btn--danger"
                    type="button"
                  >
                    Eliminar
                  </button>
                </div>
              </li>
            </ul>
          </div>
        </section>
        <section
          class="eo-card"
        >
          <h3
            class="eo-card__title"
          >
            Qué mostrar
          </h3>
          <div
            class="eo-card__body"
          >
            <div
              class="eo-segmented"
            >
              <button
                aria-pressed="true"
                type="button"
              >
                Imagen directa
              </button>
              <button
                aria-pressed="false"
                type="button"
              >
                Con detecciones
              </button>
            </div>
            <p
              class="eo-cap"
            >
              La imagen directa no pasa por el modelo: sirve para verificar encuadre, foco y luz.
            </p>
            <div
              class="eo-actions"
            >
              <button
                class="eo-btn eo-btn--primary"
                disabled=""
                type="button"
              >
                Aplicar
              </button>
            </div>
          </div>
        </section>
      </div>
    </div>
  </div>
</body>

Ignored nodes: comments, script, style
<body>
  <div>
    <div>
      <header
        class="eo-pageheader"
      >
        <div>
          <h1>
            Cámaras
          </h1>
        </div>
      </header>
      <section
        class="eo-card"
      >
        <h3
          class="eo-card__title"
        >
          Viewer
        </h3>
        <div
          class="eo-card__body"
        >
          <div
            class="eo-live-viewer"
            style="aspect-ratio: 1.7777777777777777;"
          >
            <canvas
              class="eo-live-viewer__canvas"
            />
            <span
              class="eo-live-viewer__empty"
            >
              sin señal
            </span>
            <div
              class="eo-live-viewer__overlay"
            >
              <span
                class="eo-badge eo-badge--neutral"
              >
                desconectado
              </span>
              <span>
                0
                 cuadros/s
              </span>
              <span>
                modo:
                imagen directa
              </span>
            </div>
          </div>
        </div>
      </section>
      <section
        class="record-panel"
      >
        <h3>
          Grabar toma
        </h3>
        <label
          for="rec-camera"
        >
          Cámara
        </label>
        <select
          id="rec-camera"
        >
          <option
            value=""
          >
            — elegir cámara —
          </option>
          <option
            value="oak_d_lab"
          >
            OAK-D laboratorio
             (
            oak_d
            )
          </option>
        </select>
        <label
          for="rec-scenario"
        >
          Escenario
        </label>
        <select
          id="rec-scenario"
        >
          <option
            value="P1"
          >
            P1
          </option>
          <option
            value="P2"
          >
            P2
          </option>
          <option
            value="P3"
          >
            P3
          </option>
          <option
            value="P4"
          >
            P4
          </option>
          <option
            value="P5"
          >
            P5
          </option>
          <option
            value="P6"
          >
            P6
          </option>
          <option
            value="P7"
          >
            P7
          </option>
          <option
            value="P8"
          >
            P8
          </option>
          <option
            value="P9"
          >
            P9
          </option>
        </select>
        <label
          for="rec-variant"
        >
          Variante
        </label>
        <select
          id="rec-variant"
        >
          <option
            value="a"
          >
            a
          </option>
          <option
            value="b"
          >
            b
          </option>
          <option
            value="c"
          >
            c
          </option>
        </select>
        <p
          class="record-basename"
        >
          Próxima toma:
          <strong>
            —
          </strong>
        </p>
        <button
          disabled=""
          type="button"
        >
          Grabar
        </button>
        <p
          class="eo-note"
        >
          Elegí una cámara para poder grabar.
        </p>
        <p
          class="record-error"
        >
          Failed to parse URL from /api/recordings/next?scenario=P1&variant=a
        </p>
      </section>
      <div
        style="display: grid; grid-template-columns: minmax(220px, 1fr) minmax(280px, 1.4fr); gap: var(--space-5); align-items: start; margin-top: var(--space-5);"
      >
        <section
          class="eo-card"
        >
          <h3
            class="eo-card__title"
          >
            Presets
          </h3>
          <div
            class="eo-card__body"
          >
            <button
              type="button"
            >
              Nuevo preset
            </button>
            <ul
              class="eo-list"
            >
              <li>
                <span>
                  OAK-D laboratorio
                </span>

                <small
                  class="eo-note"
                >
                  (
                  oak_d
                  )
                </small>
                <div
                  class="eo-actions"
                >
                  <button
                    type="button"
                  >
                    Conectar
                  </button>
                  <button
                    type="button"
                  >
                    Editar
                  </button>
                  <button
                    class="eo-btn--danger"
                    type="button"
                  >
                    Eliminar
                  </button>
                </div>
              </li>
            </ul>
          </div>
        </section>
        <section
          class="eo-card"
        >
          <h3
            class="eo-card__title"
          >
            Qué mostrar
          </h3>
          <div
            class="eo-card__body"
          >
            <div
              class="eo-segmented"
            >
              <button
                aria-pressed="true"
                type="button"
              >
                Imagen directa
              </button>
              <button
                aria-pressed="false"
                type="button"
              >
                Con detecciones
              </button>
            </div>
            <p
              class="eo-cap"
            >
              La imagen directa no pasa por el modelo: sirve para verificar encuadre, foco y luz.
            </p>
            <div
              class="eo-actions"
            >
              <button
                class="eo-btn eo-btn--primary"
                disabled=""
                type="button"
              >
                Aplicar
              </button>
            </div>
          </div>
        </section>
      </div>
    </div>
  </div>
</body>
 ❯ waitForWrapper ../../../../home/simonll4/projects/e-ovrt_experimental-setup/webconsole/frontend/node_modules/@testing-library/dom/dist/wait-for.js:163:27
 ❯ ../../../../home/simonll4/projects/e-ovrt_experimental-setup/webconsole/frontend/node_modules/@testing-library/dom/dist/query-helpers.js:86:33
 ❯ src/__tests__/CamerasPage.test.tsx:107:34
    105|     })
    106|     renderPage()
    107|     fireEvent.click(await screen.findByLabelText(/detección \(desmarca…
       |                                  ^
    108|     const select = await screen.findByRole('combobox', { name: /conjun…
    109|     fireEvent.change(select, { target: { value: 'cr01_cr02_v2_short' }…

⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯[1/2]⎯

 FAIL  src/__tests__/CamerasPage.test.tsx > CamerasPage > deshabilita Conectar en modo detect sin prompt set cargado
TestingLibraryElementError: Unable to find a label with the text of: /detección \(desmarcado/i

Ignored nodes: comments, script, style
<body>
  <div>
    <div>
      <header
        class="eo-pageheader"
      >
        <div>
          <h1>
            Cámaras
          </h1>
        </div>
      </header>
      <section
        class="eo-card"
      >
        <h3
          class="eo-card__title"
        >
          Viewer
        </h3>
        <div
          class="eo-card__body"
        >
          <div
            class="eo-live-viewer"
            style="aspect-ratio: 1.7777777777777777;"
          >
            <canvas
              class="eo-live-viewer__canvas"
            />
            <span
              class="eo-live-viewer__empty"
            >
              sin señal
            </span>
            <div
              class="eo-live-viewer__overlay"
            >
              <span
                class="eo-badge eo-badge--neutral"
              >
                desconectado
              </span>
              <span>
                0
                 cuadros/s
              </span>
              <span>
                modo:
                imagen directa
              </span>
            </div>
          </div>
        </div>
      </section>
      <section
        class="record-panel"
      >
        <h3>
          Grabar toma
        </h3>
        <label
          for="rec-camera"
        >
          Cámara
        </label>
        <select
          id="rec-camera"
        >
          <option
            value=""
          >
            — elegir cámara —
          </option>
          <option
            value="oak_d_lab"
          >
            OAK-D laboratorio
             (
            oak_d
            )
          </option>
        </select>
        <label
          for="rec-scenario"
        >
          Escenario
        </label>
        <select
          id="rec-scenario"
        >
          <option
            value="P1"
          >
            P1
          </option>
          <option
            value="P2"
          >
            P2
          </option>
          <option
            value="P3"
          >
            P3
          </option>
          <option
            value="P4"
          >
            P4
          </option>
          <option
            value="P5"
          >
            P5
          </option>
          <option
            value="P6"
          >
            P6
          </option>
          <option
            value="P7"
          >
            P7
          </option>
          <option
            value="P8"
          >
            P8
          </option>
          <option
            value="P9"
          >
            P9
          </option>
        </select>
        <label
          for="rec-variant"
        >
          Variante
        </label>
        <select
          id="rec-variant"
        >
          <option
            value="a"
          >
            a
          </option>
          <option
            value="b"
          >
            b
          </option>
          <option
            value="c"
          >
            c
          </option>
        </select>
        <p
          class="record-basename"
        >
          Próxima toma:
          <strong>
            —
          </strong>
        </p>
        <button
          disabled=""
          type="button"
        >
          Grabar
        </button>
        <p
          class="eo-note"
        >
          Elegí una cámara para poder grabar.
        </p>
        <p
          class="record-error"
        >
          Failed to parse URL from /api/recordings/next?scenario=P1&variant=a
        </p>
      </section>
      <div
        style="display: grid; grid-template-columns: minmax(220px, 1fr) minmax(280px, 1.4fr); gap: var(--space-5); align-items: start; margin-top: var(--space-5);"
      >
        <section
          class="eo-card"
        >
          <h3
            class="eo-card__title"
          >
            Presets
          </h3>
          <div
            class="eo-card__body"
          >
            <button
              type="button"
            >
              Nuevo preset
            </button>
            <ul
              class="eo-list"
            >
              <li>
                <span>
                  OAK-D laboratorio
                </span>

                <small
                  class="eo-note"
                >
                  (
                  oak_d
                  )
                </small>
                <div
                  class="eo-actions"
                >
                  <button
                    type="button"
                  >
                    Conectar
                  </button>
                  <button
                    type="button"
                  >
                    Editar
                  </button>
                  <button
                    class="eo-btn--danger"
                    type="button"
                  >
                    Eliminar
                  </button>
                </div>
              </li>
            </ul>
          </div>
        </section>
        <section
          class="eo-card"
        >
          <h3
            class="eo-card__title"
          >
            Qué mostrar
          </h3>
          <div
            class="eo-card__body"
          >
            <div
              class="eo-segmented"
            >
              <button
                aria-pressed="true"
                type="button"
              >
                Imagen directa
              </button>
              <button
                aria-pressed="false"
                type="button"
              >
                Con detecciones
              </button>
            </div>
            <p
              class="eo-cap"
            >
              La imagen directa no pasa por el modelo: sirve para verificar encuadre, foco y luz.
            </p>
            <div
              class="eo-actions"
            >
              <button
                class="eo-btn eo-btn--primary"
                disabled=""
                type="button"
              >
                Aplicar
              </button>
            </div>
          </div>
        </section>
      </div>
    </div>
  </div>
</body>

Ignored nodes: comments, script, style
<body>
  <div>
    <div>
      <header
        class="eo-pageheader"
      >
        <div>
          <h1>
            Cámaras
          </h1>
        </div>
      </header>
      <section
        class="eo-card"
      >
        <h3
          class="eo-card__title"
        >
          Viewer
        </h3>
        <div
          class="eo-card__body"
        >
          <div
            class="eo-live-viewer"
            style="aspect-ratio: 1.7777777777777777;"
          >
            <canvas
              class="eo-live-viewer__canvas"
            />
            <span
              class="eo-live-viewer__empty"
            >
              sin señal
            </span>
            <div
              class="eo-live-viewer__overlay"
            >
              <span
                class="eo-badge eo-badge--neutral"
              >
                desconectado
              </span>
              <span>
                0
                 cuadros/s
              </span>
              <span>
                modo:
                imagen directa
              </span>
            </div>
          </div>
        </div>
      </section>
      <section
        class="record-panel"
      >
        <h3>
          Grabar toma
        </h3>
        <label
          for="rec-camera"
        >
          Cámara
        </label>
        <select
          id="rec-camera"
        >
          <option
            value=""
          >
            — elegir cámara —
          </option>
          <option
            value="oak_d_lab"
          >
            OAK-D laboratorio
             (
            oak_d
            )
          </option>
        </select>
        <label
          for="rec-scenario"
        >
          Escenario
        </label>
        <select
          id="rec-scenario"
        >
          <option
            value="P1"
          >
            P1
          </option>
          <option
            value="P2"
          >
            P2
          </option>
          <option
            value="P3"
          >
            P3
          </option>
          <option
            value="P4"
          >
            P4
          </option>
          <option
            value="P5"
          >
            P5
          </option>
          <option
            value="P6"
          >
            P6
          </option>
          <option
            value="P7"
          >
            P7
          </option>
          <option
            value="P8"
          >
            P8
          </option>
          <option
            value="P9"
          >
            P9
          </option>
        </select>
        <label
          for="rec-variant"
        >
          Variante
        </label>
        <select
          id="rec-variant"
        >
          <option
            value="a"
          >
            a
          </option>
          <option
            value="b"
          >
            b
          </option>
          <option
            value="c"
          >
            c
          </option>
        </select>
        <p
          class="record-basename"
        >
          Próxima toma:
          <strong>
            —
          </strong>
        </p>
        <button
          disabled=""
          type="button"
        >
          Grabar
        </button>
        <p
          class="eo-note"
        >
          Elegí una cámara para poder grabar.
        </p>
        <p
          class="record-error"
        >
          Failed to parse URL from /api/recordings/next?scenario=P1&variant=a
        </p>
      </section>
      <div
        style="display: grid; grid-template-columns: minmax(220px, 1fr) minmax(280px, 1.4fr); gap: var(--space-5); align-items: start; margin-top: var(--space-5);"
      >
        <section
          class="eo-card"
        >
          <h3
            class="eo-card__title"
          >
            Presets
          </h3>
          <div
            class="eo-card__body"
          >
            <button
              type="button"
            >
              Nuevo preset
            </button>
            <ul
              class="eo-list"
            >
              <li>
                <span>
                  OAK-D laboratorio
                </span>

                <small
                  class="eo-note"
                >
                  (
                  oak_d
                  )
                </small>
                <div
                  class="eo-actions"
                >
                  <button
                    type="button"
                  >
                    Conectar
                  </button>
                  <button
                    type="button"
                  >
                    Editar
                  </button>
                  <button
                    class="eo-btn--danger"
                    type="button"
                  >
                    Eliminar
                  </button>
                </div>
              </li>
            </ul>
          </div>
        </section>
        <section
          class="eo-card"
        >
          <h3
            class="eo-card__title"
          >
            Qué mostrar
          </h3>
          <div
            class="eo-card__body"
          >
            <div
              class="eo-segmented"
            >
              <button
                aria-pressed="true"
                type="button"
              >
                Imagen directa
              </button>
              <button
                aria-pressed="false"
                type="button"
              >
                Con detecciones
              </button>
            </div>
            <p
              class="eo-cap"
            >
              La imagen directa no pasa por el modelo: sirve para verificar encuadre, foco y luz.
            </p>
            <div
              class="eo-actions"
            >
              <button
                class="eo-btn eo-btn--primary"
                disabled=""
                type="button"
              >
                Aplicar
              </button>
            </div>
          </div>
        </section>
      </div>
    </div>
  </div>
</body>
 ❯ waitForWrapper ../../../../home/simonll4/projects/e-ovrt_experimental-setup/webconsole/frontend/node_modules/@testing-library/dom/dist/wait-for.js:163:27
 ❯ ../../../../home/simonll4/projects/e-ovrt_experimental-setup/webconsole/frontend/node_modules/@testing-library/dom/dist/query-helpers.js:86:33
 ❯ src/__tests__/CamerasPage.test.tsx:118:34
    116|   it('deshabilita Conectar en modo detect sin prompt set cargado', asy…
    117|     renderPage()
    118|     fireEvent.click(await screen.findByLabelText(/detección \(desmarca…
       |                                  ^
    119|     const conectar = await screen.findByRole('button', { name: /conect…
    120|     expect((conectar as HTMLButtonElement).disabled).toBeTruthy()

⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯[2/2]⎯

 Test Files  1 failed | 64 passed (65)
      Tests  2 failed | 429 passed (431)
   Start at  02:23:11
   Duration  24.88s (transform 10.15s, setup 0ms, collect 67.20s, tests 73.35s, environment 140.03s, prepare 23.72s)

```

Se preservaron los tests del árbol entregado: el corte 3 mantuvo useLiveRun hasta el tramo 4 y adelantó Cámaras con sus pruebas. Las ejecuciones finales por corte que aparecen arriba pasan completas.

## Integridad final y documentación incorporada al tramo 5

```text
Commits desde 50b666b: 6; todos con un solo padre.
main y rama operativa: referencias intactas; sin Co-Authored-By.
Cambios ajenos en defensa/README.md y results/bench_imagenes/index.md: idénticos.
Contrato: 5/5 archivos congelados idénticos en el árbol final y /tmp/paridad.
/tmp/paridad: worktree conservado en 50b666b; cero cambios versionados.
Código final: idéntico al snapshot probado; los documentos no alteran webconsole.
Documentación: 13 textos; cero capturas, runs o archivos de tramos 6/7 preparados.
git diff --check y git diff --cached --check: salida vacía, exit 0.
```

Documentos incorporados al cierre:

```text
docs/rediseno-consola/00-diseno.md
docs/rediseno-consola/01-reglas-codex.md
docs/rediseno-consola/02-cierre-implementacion.md
docs/rediseno-consola/03-pendientes-codex.md
docs/rediseno-consola/punch-list-verificaciones.md
docs/rediseno-consola/tramo-0.md
docs/rediseno-consola/tramo-1.md
docs/rediseno-consola/tramo-2-reporte.md
docs/rediseno-consola/tramo-2.md
docs/rediseno-consola/tramo-3.md
docs/rediseno-consola/tramo-4.md
docs/rediseno-consola/tramo-5.md
docs/rediseno-consola/tramos-3-5-reporte.md
```
