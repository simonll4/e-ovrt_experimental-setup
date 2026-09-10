# Tramo 6 — cierre: archivar lo que no es evidencia

Fecha: 2026-09-10. Rama: `feature/webconsole-adopcion-front-design`.
**Tramo 6 terminado. Tramo 7 no iniciado.**

La decisión del usuario confirma los catálogos separados y el único paraguas que
queda en la vista Evidencia: **`talert_integrated_video`**. La clasificación
recursiva encuentra sus **4 ejecuciones**, de las que **3** están en los CSV bajo
`realtime/t_alert_notification`. Admisión queda archivada. `diag_riesgo_activo`
tiene 5 ejecuciones y ninguna de evidencia; los otros nueve paraguas no tienen
ejecuciones consolidadas. Las dos listas de `consola.yaml` siguen vacías.

La [tabla A.4 completa y regenerada](tramo-6-clasificacion.md) incluye los 11
paraguas, todos los grupos huérfanos y cada ejecución con ruta, ids y motivo.
Los 19 individuales se documentan aparte: no se clasifican ni entran en el filtro.
La tabla coincide con la revisión y el resultado esperado que aprobó el usuario.

## Corrección del falso cero anterior

El avance previo exploraba sólo el primer nivel de runs/. Su conclusión de
«cero evidencia» era falsa: no había llegado a las consolidaciones de la campaña.
Ahora se descubre cada `manifest.effective.yaml` recursivamente y se recorren
JSON, JSONL y YAML de todo el subárbol, sin abrir destinos externos de archivos
`.ref`. Se extraen identidades de objetos y listas anidados.

Antes de dar el resultado por válido se contrastaron **directamente**
`media/summary.json` y `control/summary.json` de las cuatro ejecuciones contra
los CSV, con un chequeo independiente que no llama al clasificador. Esa salida
se pega abajo. Las tres repeticiones también se abrieron desde el navegador:
detalle, reporte y alertas devolvieron 200, con manager recién creado.

## Comportamiento final y paridad

- El registro se carga una vez al **crear la app**, en `app.state.evidence`.
  Es estado local sin recursos HTTP que cerrar; queda disponible también para
  las rutas de catálogo usadas sin entrar al lifespan. Si falta el directorio
  o alguno de los cuatro CSV, la UI lo informa y permite elegir Todas.
- `GET /api/runs` y `GET /api/experiments/manifests` conservan **`vista=todas`**
  por defecto. El bloque `evidence` y las cabeceras son aditivos. El filtro de
  Corridas se aplica antes de hidratar.
- **`_ejecuciones_por_slug` es idéntica** a la función inicial. Los campos y
  conteos preexistentes del listado se compararon contra el BFF anterior:
  permanecen iguales. `n_runs` de talert sigue en 0; `evidence.n_executions`
  informa 4 y `evidence.executions` ofrece los tres ids de evidencia.
- El clasificador es independiente del listado histórico. Incluye explícitamente
  las huérfanas `orq_*`, `gate_orq`, `gate`, `d1` y `video16_clip10_gt`; no les
  inventa un manifiesto del catálogo. El contador de ejecuciones archivadas las
  incluye aunque no tengan una fila de receta en la pantalla.
- La resolución de detalle conserva la prioridad del manager y de runs/id;
  cuando ese directorio no existe, descubre el id exacto en las consolidaciones
  anidadas. Conserva la contención de rutas y rechaza ids anidados ambiguos.
  Es lo necesario para que los enlaces de evidencia encontrados sean abribles.
- Corridas y Experimentos piden Evidencia explícitamente y recuerdan la elección
  en `eo-evidence-view-runs` y `eo-evidence-view-experiments`. Los estados son
  Evidencia, Archivadas y Todas. La UI muestra la cantidad archivada y un solo
  distintivo de resultado, con los restantes ids en `title`.
- La partición real de Experimentos es **1 / 10 / 11**, sin solapamientos.
  Corridas conserva **420 de evidencia / 52 archivadas / 472 totales**.
- `consola.yaml` queda versionado con listas vacías; el resto del archivo de
  evidencia sigue ignorado. Reiniciar el BFF carga cambios de CSV/excepciones.

## Verificación y capturas

Backend **800**, frontend **460**, build correcto, contrato **10/10** contra
`50b666b` y **10/10** contra el árbol final, Ruff **36 heredados y cero nuevos**.
No se editó ni se saltó ningún test preexistente, incluido el contrato y los
nueve tests de backend y tres de frontend del avance anterior. `/tmp/paridad`
se reutilizó y se conserva registrado, con la base versionada intacta.

Las capturas de ambas pantallas en los tres estados, y las tres aperturas de
evidencia, están en `/tmp/eovrt-tramo6-cierre/captures/`, fuera de Git. Viewport
1440 × 1000; se verificó persistencia. El recorrido registra los anchos reales
con y sin distintivos. Corridas conserva desbordes de 4 px y 44 px según la vista; Experimentos
en Todas también excede el viewport aun quitando los distintivos del DOM. El ancho adicional observado con etiquetas largas se
resolvió acortando sólo su texto visible y conservando el id completo en `title`. Las capturas anteriores se conservaron desde el avance previo. Los
manifiestos listados y las corridas de los planos no se modificaron en el recorrido.
Las suites existentes agregan smokes huérfanos en runs/; la tabla y las capturas
finales se regeneraron después de terminar los tests para usar el mismo inventario.

## Archivos y dependencias

No se trajeron módulos de 3500923: el tramo 6 autoriza desarrollo nuevo.
`api/queries/sidebar.ts` sólo adapta la llamada a la firma ampliada del cliente;
continúa pidiendo el catálogo completo y no comparte caché con una vista filtrada.
`styles/ui.css` incorpora sólo la regla del distintivo de evidencia que limita
su ancho visual. No se cambió `nav.ts` ni se agregaron destinos o dependencias.

Archivos del commit del tramo:

- `.gitignore`
- `docs/rediseno-consola/04-evidencia-diseno.md`
- `docs/rediseno-consola/tramo-6-clasificacion.md`
- `docs/rediseno-consola/tramo-6-reporte.md`
- `docs/rediseno-consola/tramo-6.md`
- `results/evidence-runs/consola.yaml`
- `webconsole/README.md`
- `webconsole/backend/src/eovrt_webconsole/app.py`
- `webconsole/backend/src/eovrt_webconsole/evidence.py`
- `webconsole/backend/src/eovrt_webconsole/routers/experiments.py`
- `webconsole/backend/src/eovrt_webconsole/routers/runs.py`
- `webconsole/backend/tests/test_evidence.py`
- `webconsole/backend/tests/test_evidence_recursive.py`
- `webconsole/frontend/src/__tests__/EvidenceView.test.tsx`
- `webconsole/frontend/src/__tests__/ExperimentsEvidence.test.tsx`
- `webconsole/frontend/src/api/endpoints.ts`
- `webconsole/frontend/src/api/queries/experiments.ts`
- `webconsole/frontend/src/api/queries/runs.ts`
- `webconsole/frontend/src/api/queries/sidebar.ts`
- `webconsole/frontend/src/components/EvidenceViewControl.tsx`
- `webconsole/frontend/src/pages/ExperimentsPage.tsx`
- `webconsole/frontend/src/pages/RunsPage.tsx`
- `webconsole/frontend/src/styles/ui.css`
- `webconsole/frontend/src/types.ts`
- `webconsole/tools/classify_evidence.py`

Los documentos 04 y tramo-6 fueron aportados por el usuario y se incorporan tal
como se leyeron; el párrafo de corrección del tramo-6 manda sobre los conteos
históricos del diseño. No hubo merge, push ni cambios a main. Los dos cambios
ajenos y el documento del tramo 7 permanecen intactos.

## Hallazgos y límites conservados

- Hay desborde horizontal en Corridas y en Experimentos/Todas aun quitando
  los distintivos nuevos; el recorrido pega ambos anchos y no se amplía este
  tramo a una reforma del layout de tablas.
- Los tests existentes siguen escribiendo cinco smokes de orquestación por suite
  completa. No se corrigieron ni se borraron esas ejecuciones; A.4 registra el
  conteo real final, no el estimado histórico de 385.
- En Archivadas/Todas, la receta `talert_camera_smoke` conserva el id de plantilla
  `${EOVRT_EXPERIMENT_ID}` que ya exponía el listado. Se registra; no se cambió
  el contrato histórico para resolver una plantilla sin ejecución.
- El archivo de evidencia debe existir en la máquina. Los resultados curados y
  la pantalla Evidencia del tramo 7 no se implementaron en esta tarea.

## Salidas reales completas

Las salidas siguientes se pegan completas; sólo se retiran secuencias ANSI y
espacios al final de línea para conservar texto Markdown sin ruido de terminal.

### Backend completo

```text
$ cd webconsole/backend && ./.venv/bin/python -m pytest -q
........................................................................ [  9%]
........................................................................ [ 18%]
........................................................................ [ 27%]
........................................................................ [ 36%]
........................................................................ [ 45%]
........................................................................ [ 54%]
........................................................................ [ 63%]
........................................................................ [ 72%]
........................................................................ [ 81%]
........................................................................ [ 90%]
........................................................................ [ 99%]
........                                                                 [100%]
800 passed in 86.79s (0:01:26)
```

### Frontend completo

```text
$ cd webconsole/frontend && npm test

> eovrt-webconsole-frontend@0.1.0 test
> vitest run


 RUN  v2.1.9 /home/simonll4/projects/e-ovrt_experimental-setup/webconsole/frontend

 ✓ src/__tests__/api.test.ts (15 tests) 118ms
stderr | src/__tests__/ExperimentDetailPageRiskBanner.test.tsx > ExperimentDetailPage — banner de riesgo activo > muestra el banner con el condition_id cuando patterns no esta vacio y el experimento corre
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ExperimentsPage.test.tsx > ExperimentsPage > lista manifiestos y dispara un experimento con preflight verde
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ExperimentDetailPage.test.tsx > ExperimentDetailPage > muestra las alertas y avisa que el conjunto no es temporal
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/TrimDialog.test.tsx (9 tests) 356ms
stderr | src/__tests__/RunsPage.test.tsx > RunsPage > lista corridas y marca la que está en curso
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/CamerasPage.test.tsx > CamerasPage > lista los presets de cámara
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/contrato/experimentos-distribucion.contrato.test.tsx > Contrato: experimentos y distribución > lista y abre un experimento con outcomes vinculados a cada alerta
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ComposePage.test.tsx > ComposePage prefill > conserva active_ids del manifiesto y no lo pisan los defaults del set
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/ExperimentDetailPageRiskBanner.test.tsx (7 tests) 444ms
stderr | src/__tests__/RunDetailPage.test.tsx > RunDetailPage > muestra el estado de la corrida con el glosario, no con el código crudo
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/ExperimentsPage.test.tsx (5 tests) 967ms
   ✓ ExperimentsPage > lista manifiestos y dispara un experimento con preflight verde 360ms
 ✓ src/__tests__/ExperimentDetailPage.test.tsx (15 tests) 1195ms
 ✓ src/__tests__/PromptSetsPage.test.tsx (7 tests) 1211ms
   ✓ PromptSetsPage > lista los sets con badge de estado 341ms
stderr | src/__tests__/ComposePage.test.tsx > ComposePage prefill de source.type video > conserva el source.type original en la composición (round-trip sin colapso a video_file)
No routes matched location "/runs/r1"

 ✓ src/__tests__/DeriveExperimentForm.test.tsx (13 tests) 1539ms
 ✓ src/__tests__/ComparePage.test.tsx (14 tests) 1895ms
   ✓ ComparePage > lista las corridas por nombre, no por identificador crudo 321ms
   ✓ ComparePage > compara al elegir dos y nombra las métricas en español 312ms
   ✓ ComparePage > no avisa cuando comparten conjunto de evaluación 329ms
 ✓ src/__tests__/RunDetailPage.test.tsx (10 tests) 1658ms
   ✓ RunDetailPage > las pestañas separan traza, resumen, evaluación y archivos 306ms
 ✓ src/__tests__/contrato/experimentos-distribucion.contrato.test.tsx (4 tests) 1956ms
   ✓ Contrato: experimentos y distribución > lista y abre un experimento con outcomes vinculados a cada alerta 760ms
   ✓ Contrato: experimentos y distribución > deriva un manifiesto con overrides y lanza la derivación seleccionada 817ms
stderr | src/__tests__/Shell.test.tsx > Shell > renderiza los tres títulos de grupo
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/Shell.test.tsx (17 tests) 2480ms
stderr | src/__tests__/ComposePage.test.tsx > ComposePage nombre opcional de la corrida > manda run.name cuando se completa, null cuando se deja vacío
No routes matched location "/runs/r1"

 ✓ src/__tests__/RecordPanel.test.tsx (13 tests) 3095ms
   ✓ RecordPanel > mientras graba, consulta el backend periodicamente y muestra elapsed_ms/size_bytes de ahi 1101ms
   ✓ RecordPanel > si el backend informa error, deja de contar y muestra el motivo 1113ms
 ✓ src/__tests__/CamerasPage.test.tsx (14 tests) 2690ms
   ✓ CamerasPage > muestra banner y deshabilita conectar ante 409 run_active 380ms
   ✓ CamerasPage > activa por defecto las clases sin enabled_by_default declarado en el YAML 494ms
stderr | src/__tests__/ComposePage.test.tsx > ComposePage nombre opcional de la corrida > deja run.name en null si el campo queda vacío (usa el id autogenerado)
No routes matched location "/runs/r2"

stderr | src/__tests__/ExperimentsPage.new.test.tsx > ExperimentsPage - crear nuevo experimento (/experiments/new) > abre el formulario con un selector "basado en" precargado con el primer manifiesto
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/contrato/nueva-corrida.contrato.test.tsx > Contrato: nueva corrida > consulta preflight, compone fuente y prompts, lanza y abre el detalle real
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/labels.test.ts (13 tests) 22ms
 ✓ src/__tests__/TraceSection.test.tsx (10 tests) 2477ms
   ✓ TraceSection > no vuelca todos los cuadros: la lista se acota y dice el total 1321ms
stderr | src/__tests__/ExperimentsEvidence.test.tsx > pide evidencia, conserva el conteo histórico y ofrece los tres enlaces de consolidaciones
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/LiveViewer.test.tsx (5 tests) 175ms
stderr | src/__tests__/spec44c_gate.test.tsx > spec44c gate: flujo de experimentos por la UI > ExperimentsPage: lista un manifiesto y dispara runExperiment al hacer click en "Ejecutar experimento"
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/PreviewWithBoxes.test.tsx (8 tests) 263ms
 ✓ src/__tests__/traceview.test.ts (12 tests) 34ms
 ✓ src/__tests__/ExperimentsPage.new.test.tsx (4 tests) 1741ms
   ✓ ExperimentsPage - crear nuevo experimento (/experiments/new) > abre el formulario con un selector "basado en" precargado con el primer manifiesto 745ms
   ✓ ExperimentsPage - crear nuevo experimento (/experiments/new) > al cambiar la fuente en el selector, vuelve a pedir los defaults y reprecarga los campos (bug central) 412ms
   ✓ ExperimentsPage - crear nuevo experimento (/experiments/new) > en modo nuevo la card dice "Nuevo experimento" y el botón "Crear" (no "Derivar de...") 381ms
 ✓ src/__tests__/PlatformPage.test.tsx (6 tests) 844ms
   ✓ PlatformPage > lista el fleet y activa una instancia 469ms
 ✓ src/__tests__/PromptSetEditor.test.tsx (5 tests) 789ms
   ✓ PromptSetEditor > exploratory: permite editar y guardar via updatePromptSet 382ms
 ✓ src/__tests__/RunsPage.test.tsx (22 tests) 5177ms
   ✓ RunsPage > lista corridas y marca la que está en curso 352ms
   ✓ RunsPage > el pedido de la página lleva el filtro, el orden y la página al servidor 1116ms
   ✓ RunsPage > el buscador manda `q` al servidor en vez de filtrar en el cliente 772ms
   ✓ RunsPage > el total es el del servidor, no la cantidad de filas de la página 311ms
 ✓ src/__tests__/contrato/nueva-corrida.contrato.test.tsx (3 tests) 2091ms
   ✓ Contrato: nueva corrida > consulta preflight, compone fuente y prompts, lanza y abre el detalle real 1115ms
   ✓ Contrato: nueva corrida > impide lanzar con el formulario completo si el target aún no está listo 452ms
   ✓ Contrato: nueva corrida > muestra los bloqueos del preflight y permite lanzar sólo medios con target listo 521ms
 ✓ src/__tests__/spec44c_gate.test.tsx (3 tests) 649ms
   ✓ spec44c gate: flujo de experimentos por la UI > ExperimentsPage: lista un manifiesto y dispara runExperiment al hacer click en "Ejecutar experimento" 475ms
 ✓ src/__tests__/ExperimentsEvidence.test.tsx (3 tests) 1176ms
   ✓ pide evidencia, conserva el conteo histórico y ofrece los tres enlaces de consolidaciones 546ms
   ✓ alterna Archivadas y Todas, persiste y vuelve a evidencia sin cruzar cachés 479ms
 ✓ src/__tests__/charts/ActivityTimeline.test.tsx (7 tests) 453ms
stderr | src/__tests__/EvidenceView.test.tsx > pide evidencia y alterna los tres estados sin filtrar en el cliente
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/experimentview.test.ts (15 tests) 17ms
 ✓ src/__tests__/runview.test.ts (17 tests) 14ms
stderr | src/__tests__/ComposePage.test.tsx > ComposePage fuente RTSP > al elegir rtsp muestra el campo de dirección y arma config { url }
No routes matched location "/runs/r1"

 ✓ src/__tests__/EvidenceView.test.tsx (3 tests) 1296ms
   ✓ pide evidencia y alterna los tres estados sin filtrar en el cliente 732ms
   ✓ persiste la elección al remontar y muestra un solo distintivo con ambos resultados en title 387ms
 ✓ src/__tests__/runseries.test.ts (12 tests) 13ms
 ✓ src/__tests__/useServiceHealth.test.ts (5 tests) 374ms
 ✓ src/__tests__/charts/GroupedBars.test.tsx (8 tests) 263ms
 ✓ src/__tests__/charts/timeline.test.ts (9 tests) 51ms
stderr | src/__tests__/ComposePage.test.tsx > ComposePage cámara guardada (oak_d) > lanza con la config de la cámara guardada elegida
No routes matched location "/runs/r1"

 ✓ src/__tests__/ComposePage.test.tsx (18 tests) 7694ms
   ✓ ComposePage prefill > conserva active_ids del manifiesto y no lo pisan los defaults del set 749ms
   ✓ ComposePage prefill de source.type video > conserva el source.type original en la composición (round-trip sin colapso a video_file) 495ms
   ✓ ComposePage prefill survives catalog re-fetch (no clobber) > no reaplica el manifiesto cuando `experiments` cambia de referencia tras un re-fetch 709ms
   ✓ ComposePage nombre opcional de la corrida > manda run.name cuando se completa, null cuando se deja vacío 536ms
   ✓ ComposePage nombre opcional de la corrida > deja run.name en null si el campo queda vacío (usa el id autogenerado) 580ms
   ✓ ComposePage aviso de 409 al lanzar > muestra aviso de prueba de cámara activa ante 409 preview_active 555ms
   ✓ ComposePage aviso de 409 al lanzar > muestra aviso de corrida activa ante 409 con active_run_id 392ms
   ✓ ComposePage panel «Antes de lanzar» > los requisitos se van cumpliendo y el botón se habilita al final 446ms
   ✓ ComposePage panel «Antes de lanzar» > desactivar todas las clases vuelve a bloquear, diciendo qué falta 554ms
   ✓ ComposePage rejilla de fuentes > una fuente deshabilitada explica el motivo que manda el backend 323ms
   ✓ ComposePage fuente RTSP > bloquea el lanzamiento si la dirección RTSP trae credenciales censuradas (***) 438ms
   ✓ ComposePage fuente RTSP > al elegir rtsp muestra el campo de dirección y arma config { url } 376ms
   ✓ ComposePage cámara guardada (oak_d) > lanza con la config de la cámara guardada elegida 564ms
stderr | src/__tests__/RunDetailArtifacts.test.tsx > expone el inventario limitado del servicio anterior con descargas verificadas
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/TraceQueries.final.test.tsx (1 test) 91ms
 ✓ src/__tests__/RunKpiStrip.test.tsx (7 tests) 412ms
 ✓ src/__tests__/ui/Table.test.tsx (6 tests) 330ms
 ✓ src/__tests__/ClipsPage.test.tsx (5 tests) 652ms
 ✓ src/__tests__/ui/primitives.test.tsx (10 tests) 291ms
stderr | src/__tests__/Shell.live.test.tsx > seguir la corrida viva cierra el cajón de navegación móvil
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ComposePage.preflight.test.tsx > ComposePage: bloqueos de preflight > informa los motivos con ready=false sin bloquear DBE y los actualiza por polling
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/charts/layout.test.ts (9 tests) 25ms
 ✓ src/__tests__/RunDetailArtifacts.test.tsx (3 tests) 1319ms
   ✓ expone el inventario limitado del servicio anterior con descargas verificadas 540ms
   ✓ actualiza los archivos después de evaluar sin recargar el detalle 544ms
 ✓ src/__tests__/EvalSection.test.tsx (4 tests) 264ms
 ✓ src/__tests__/Shell.live.test.tsx (2 tests) 1891ms
   ✓ seguir la corrida viva cierra el cajón de navegación móvil 723ms
   ✓ lanzar desde el formulario invalida la lista vacía y muestra la corrida global 1159ms
 ✓ src/__tests__/useSidebarCounts.test.ts (3 tests) 272ms
 ✓ src/__tests__/ui/Select.test.tsx (5 tests) 540ms
 ✓ src/__tests__/ComposePage.preflight.test.tsx (2 tests) 1811ms
   ✓ ComposePage: bloqueos de preflight > informa los motivos con ready=false sin bloquear DBE y los actualiza por polling 1210ms
   ✓ ComposePage: bloqueos de preflight > informa los motivos con ready=true sin bloquear DBE y los actualiza por polling 597ms
stderr | src/__tests__/contrato/detalle-traza-evaluacion.contrato.test.tsx > Contrato: detalle, traza y evaluación > lee detalle y traza, permite inspeccionar cuadros y evaluar contra BENCH
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/nav.test.ts (10 tests) 48ms
stderr | src/__tests__/contrato/corrida-viva.contrato.test.tsx > Contrato: corrida viva > permite alcanzar la corrida activa desde una ruta distinta del listado
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/queryClient.test.ts (4 tests) 14ms
 ✓ src/__tests__/ExperimentQueries.final.test.tsx (1 test) 109ms
stderr | src/__tests__/Shell.distribution.test.tsx > Salud del distribuidor en la barra lateral > informa healthy=true y conserva los dos motores
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/charts/Meter.test.tsx (5 tests) 254ms
 ✓ src/__tests__/contrato/corrida-viva.contrato.test.tsx (2 tests) 1230ms
   ✓ Contrato: corrida viva > permite alcanzar la corrida activa desde una ruta distinta del listado 726ms
   ✓ Contrato: corrida viva > consulta mientras corre, permite detener y cesa el polling del detalle al terminar 502ms
 ✓ src/__tests__/contrato/detalle-traza-evaluacion.contrato.test.tsx (1 test) 1128ms
   ✓ Contrato: detalle, traza y evaluación > lee detalle y traza, permite inspeccionar cuadros y evaluar contra BENCH 1125ms
 ✓ src/__tests__/Shell.distribution.test.tsx (3 tests) 822ms
   ✓ Salud del distribuidor en la barra lateral > informa healthy=true y conserva los dos motores 512ms
 ✓ src/__tests__/api.endpoints.test.ts (4 tests) 21ms
stderr | src/__tests__/LiveRunPill.test.tsx > LiveRunPill > no renderiza nada si no hay corrida viva
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/App.test.tsx > App > renderiza el título de la consola
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/App.test.tsx (2 tests) 512ms
   ✓ App > renderiza el título de la consola 385ms
 ✓ src/__tests__/experiment-api.test.ts (4 tests) 24ms
 ✓ src/__tests__/LiveRunPill.test.tsx (3 tests) 356ms
 ✓ src/__tests__/stream.test.ts (3 tests) 16ms
 ✓ src/__tests__/preview.test.ts (2 tests) 21ms
 ✓ src/__tests__/ui/Button.test.tsx (5 tests) 313ms
 ✓ src/__tests__/ui/Banner.test.tsx (3 tests) 311ms
 ✓ src/__tests__/ui/Select.field.test.tsx (1 test) 305ms
   ✓ Select dentro de Field > cancela la activación del label al elegir, sin reabrir el control 300ms
 ✓ src/__tests__/ui/Badge.test.tsx (4 tests) 85ms
 ✓ src/__tests__/ui/SegmentedControl.test.tsx (2 tests) 253ms
 ✓ src/__tests__/ui/InlineDeleteConfirm.test.tsx (2 tests) 210ms
 ✓ src/__tests__/ui/ConditionName.test.tsx (3 tests) 65ms
 ✓ src/__tests__/ui/SearchInput.test.tsx (1 test) 68ms
 ✓ src/__tests__/ui/PageHeader.test.tsx (2 tests) 190ms
stderr | src/__tests__/CamerasPage.preview-error.test.tsx > muestra el fallo del sondeo de preview sin rechazar una promesa sin manejar
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/promptview.test.ts (3 tests) 4ms
 ✓ src/__tests__/CamerasPage.preview-error.test.tsx (1 test) 205ms
 ✓ src/__tests__/ui/icons.test.tsx (1 test) 42ms

 Test Files  71 passed (71)
      Tests  460 passed (460)
   Start at  04:05:11
   Duration  18.47s (transform 6.18s, setup 0ms, collect 46.85s, tests 59.72s, environment 103.80s, prepare 16.37s)

```

### Build

```text
$ cd webconsole/frontend && npm run build

> eovrt-webconsole-frontend@0.1.0 build
> tsc && vite build

vite v5.4.21 building for production...
transforming...
✓ 163 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.40 kB │ gzip:   0.27 kB
dist/assets/index-DVXN0UpI.css   35.48 kB │ gzip:   7.10 kB
dist/assets/index-DMmpiV3K.js   399.78 kB │ gzip: 121.44 kB
✓ built in 3.38s
```

### Contrato contra 50b666b intacto

```text
$ cd /tmp/paridad/webconsole/frontend && npx vitest run src/__tests__/contrato

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

 ✓ src/__tests__/contrato/corrida-viva.contrato.test.tsx (2 tests) 636ms
   ✓ Contrato: corrida viva > permite alcanzar la corrida activa desde una ruta distinta del listado 402ms
 ✓ src/__tests__/contrato/detalle-traza-evaluacion.contrato.test.tsx (1 test) 710ms
   ✓ Contrato: detalle, traza y evaluación > lee detalle y traza, permite inspeccionar cuadros y evaluar contra BENCH 708ms
 ✓ src/__tests__/contrato/experimentos-distribucion.contrato.test.tsx (4 tests) 1262ms
   ✓ Contrato: experimentos y distribución > lista y abre un experimento con outcomes vinculados a cada alerta 557ms
   ✓ Contrato: experimentos y distribución > deriva un manifiesto con overrides y lanza la derivación seleccionada 546ms
 ✓ src/__tests__/contrato/nueva-corrida.contrato.test.tsx (3 tests) 1378ms
   ✓ Contrato: nueva corrida > consulta preflight, compone fuente y prompts, lanza y abre el detalle real 924ms

 Test Files  4 passed (4)
      Tests  10 passed (10)
   Start at  03:46:27
   Duration  4.87s (transform 1.50s, setup 0ms, collect 4.79s, tests 3.99s, environment 4.19s, prepare 1.77s)

```

### Contrato contra el árbol final

```text
$ cd webconsole/frontend && npx vitest run src/__tests__/contrato

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

 ✓ src/__tests__/contrato/detalle-traza-evaluacion.contrato.test.tsx (1 test) 317ms
   ✓ Contrato: detalle, traza y evaluación > lee detalle y traza, permite inspeccionar cuadros y evaluar contra BENCH 316ms
 ✓ src/__tests__/contrato/corrida-viva.contrato.test.tsx (2 tests) 331ms
 ✓ src/__tests__/contrato/experimentos-distribucion.contrato.test.tsx (4 tests) 586ms
 ✓ src/__tests__/contrato/nueva-corrida.contrato.test.tsx (3 tests) 705ms
   ✓ Contrato: nueva corrida > consulta preflight, compone fuente y prompts, lanza y abre el detalle real 420ms

 Test Files  4 passed (4)
      Tests  10 passed (10)
   Start at  04:06:15
   Duration  2.96s (transform 1.04s, setup 0ms, collect 2.91s, tests 1.94s, environment 3.96s, prepare 545ms)

```

### Ruff completo; exit 1 heredado

```text
$ cd webconsole/backend && ./.venv/bin/ruff check src tests
PLW1510 `subprocess.run` without explicit `check` argument
  --> src/eovrt_webconsole/clips/trim.py:40:21
   |
38 |     ]
39 |     try:
40 |         completed = subprocess.run(
   |                     ^^^^^^^^^^^^^^
41 |             cmd, capture_output=True, text=True, timeout=_TIMEOUT_S
42 |         )
   |
help: Add explicit `check=False`

PIE790 [*] Unnecessary `pass` statement
  --> src/eovrt_webconsole/clips/window.py:18:5
   |
16 |     """Excepción de validación: marcas inválidas o fuera del master."""
17 |
18 |     pass
   |     ^^^^
help: Remove unnecessary `pass`
   |
17 |
   -     pass
18 |
   |

UP037 [*] Remove quotes from type annotation
  --> src/eovrt_webconsole/experiment/applicability.py:59:34
   |
58 |     @model_validator(mode="after")
59 |     def _evaluar_umbral(self) -> "MetricResult":
   |                                  ^^^^^^^^^^^^^^
60 |         """Deriva `passed` del valor y el umbral.
   |
help: Remove quotes
   |
58 |     @model_validator(mode="after")
   -     def _evaluar_umbral(self) -> "MetricResult":
59 +     def _evaluar_umbral(self) -> MetricResult:
60 |         """Deriva `passed` del valor y el umbral.
   |

S110 `try`-`except`-`pass` detected, consider logging the exception
   --> src/eovrt_webconsole/experiment/run_manager.py:138:9
    |
136 |           try:
137 |               await task
138 | /         except (asyncio.CancelledError, Exception):  # noqa: BLE001 -- solo drenar el teardown
139 | |             pass
    | |________________^

UP035 [*] Import from `collections.abc` instead: `Awaitable`, `Callable`
  --> src/eovrt_webconsole/orchestrator.py:14:1
   |
12 | import time
13 | from pathlib import Path
14 | from typing import Any, Awaitable, Callable
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
15 |
16 | import httpx
   |
help: Import from `collections.abc`
   |
13 | from pathlib import Path
   - from typing import Any, Awaitable, Callable
14 + from typing import Any
15 + from collections.abc import Awaitable, Callable
16 |
   |

UP041 [*] Replace aliased errors with `TimeoutError`
  --> src/eovrt_webconsole/orchestrator.py:46:12
   |
44 |     try:
45 |         stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=_COMPOSE_TIMEOUT_S)
46 |     except asyncio.TimeoutError:
   |            ^^^^^^^^^^^^^^^^^^^^
47 |         proc.kill()
48 |         await proc.wait()  # reap: evita proceso zombie
   |
help: Replace `asyncio.TimeoutError` with builtin `TimeoutError`
   |
45 |         stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=_COMPOSE_TIMEOUT_S)
   -     except asyncio.TimeoutError:
46 +     except TimeoutError:
47 |         proc.kill()
   |

I001 [*] Import block is un-sorted or un-formatted
  --> src/eovrt_webconsole/recording/ffmpeg_recorder.py:3:1
   |
 1 |   """Rama RTSP: ffmpeg -c copy, sin transcodificar. El host no toca los píxeles."""
 2 |
 3 | / from __future__ import annotations
 4 | |
 5 | | import logging
 6 | | import signal
 7 | | import subprocess
 8 | | import time
 9 | | from pathlib import Path
10 | |
11 | | from eovrt_webconsole.redact import redact_rtsp_credentials
12 | | from eovrt_webconsole.recording.types import RecordingResult, RecordingSpec, RecordingStatus
   | |____________________________________________________________________________________________^
13 |
14 |   logger = logging.getLogger(__name__)
   |
help: Organize imports
   |
10 |
11 + from eovrt_webconsole.recording.types import RecordingResult, RecordingSpec, RecordingStatus
12 | from eovrt_webconsole.redact import redact_rtsp_credentials
   - from eovrt_webconsole.recording.types import RecordingResult, RecordingSpec, RecordingStatus
13 |
   |

PLW1510 `subprocess.run` without explicit `check` argument
  --> src/eovrt_webconsole/recording/oakd_recorder.py:33:17
   |
31 |     mux resultó silenciosamente incompleto.
32 |     """
33 |     completed = subprocess.run(
   |                 ^^^^^^^^^^^^^^
34 |         [
35 |             "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
   |
help: Add explicit `check=False`

PLW1510 `subprocess.run` without explicit `check` argument
  --> src/eovrt_webconsole/recording/probe.py:34:21
   |
32 | def measure(path: Path) -> Measured:
33 |     try:
34 |         completed = subprocess.run(
   |                     ^^^^^^^^^^^^^^
35 |             [
36 |                 "ffprobe", "-v", "error",
   |
help: Add explicit `check=False`

RUF046 Value being cast to `int` is already an integer
  --> src/eovrt_webconsole/recording/probe.py:60:21
   |
58 |         height=int(stream["height"]),
59 |         fps=_parse_rate(str(stream.get("avg_frame_rate", "0/0"))),
60 |         duration_ms=int(round(float(duration_raw) * 1000)) if duration_raw else 0,
   |                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
61 |     )
   |
help: Remove unnecessary `int` call

UP037 [*] Remove quotes from type annotation
  --> src/eovrt_webconsole/recording/types.py:67:42
   |
66 |     @model_validator(mode="after")
67 |     def _capture_solo_para_oakd(self) -> "RecordingSpec":
   |                                          ^^^^^^^^^^^^^^^
68 |         if self.plugin == "rtsp" and self.capture is not None:
69 |             raise ValueError(
   |
help: Remove quotes
   |
66 |     @model_validator(mode="after")
   -     def _capture_solo_para_oakd(self) -> "RecordingSpec":
67 +     def _capture_solo_para_oakd(self) -> RecordingSpec:
68 |         if self.plugin == "rtsp" and self.capture is not None:
   |

I001 [*] Import block is un-sorted or un-formatted
  --> src/eovrt_webconsole/routers/experiments.py:4:1
   |
 2 |   disparo orquestado en background (Tarea 3) + vista de alertas y lectura del
 3 |   reporte consolidado (Tarea 4)."""
 4 | / from __future__ import annotations
 5 | |
 6 | | import json
 7 | | import logging
 8 | | import re
 9 | | from datetime import UTC, datetime
10 | | from pathlib import Path
11 | | from typing import Any
12 | |
13 | | import yaml
14 | | from fastapi import APIRouter, HTTPException, Query, Request, Response
15 | | from fastapi.responses import JSONResponse
16 | | from pydantic import ValidationError
17 | |
18 | | from eovrt_webconsole.evidence import (
19 | |     Vista, clasificar_ejecuciones, coincide_vista, directorios_consolidados,
20 | | )
21 | | from eovrt_webconsole.experiment.control_backend import ServiceUnavailable, UnknownRun
22 | | from eovrt_webconsole.experiment.manifest import ExperimentManifest, load_manifest
23 | | from eovrt_webconsole.experiment.run_manager import ExperimentBusy
24 | | from eovrt_webconsole.preflight import platform_preflight
25 | | from eovrt_webconsole.manifest_writer import (
26 | |     ManifestExistsError,
27 | |     ProtectedManifestError,
28 | |     write_manifest,
29 | |     write_manifest_dir,
30 | | )
31 | | from eovrt_webconsole.experiment_deriver import DeriveError, derive_payloads
32 | | from eovrt_webconsole.repo_catalog import get_prompt_set
33 | | from eovrt_webconsole import camera_store as cs
   | |_______________________________________________^
34 |
35 |   logger = logging.getLogger(__name__)
   |
help: Organize imports
   |
17 |
18 + from eovrt_webconsole import camera_store as cs
19 | from eovrt_webconsole.evidence import (
   -     Vista, clasificar_ejecuciones, coincide_vista, directorios_consolidados,
20 +     Vista,
21 +     clasificar_ejecuciones,
22 +     coincide_vista,
23 +     directorios_consolidados,
24 | )
25 | from eovrt_webconsole.experiment.control_backend import ServiceUnavailable, UnknownRun
26 | from eovrt_webconsole.experiment.manifest import ExperimentManifest, load_manifest
27 | from eovrt_webconsole.experiment.run_manager import ExperimentBusy
   - from eovrt_webconsole.preflight import platform_preflight
28 + from eovrt_webconsole.experiment_deriver import DeriveError, derive_payloads
29 | from eovrt_webconsole.manifest_writer import (
--------------------------------------------------------------------------------
34 | )
   - from eovrt_webconsole.experiment_deriver import DeriveError, derive_payloads
35 + from eovrt_webconsole.preflight import platform_preflight
36 | from eovrt_webconsole.repo_catalog import get_prompt_set
   - from eovrt_webconsole import camera_store as cs
37 |
   |

RUF100 [*] Unused `noqa` directive (unused: `BLE001`)
  --> src/eovrt_webconsole/routers/recordings.py:63:31
   |
61 |     try:
62 |         spec = RecordingSpec(**body)
63 |     except Exception as exc:  # noqa: BLE001 - ValidationError de pydantic y kwargs sobrantes
   |                               ^^^^^^^^^^^^^^
64 |         # pydantic incluye el valor recibido en el mensaje de error (p. ej. si
65 |         # `config` llega como string en vez de objeto, "input_value=" repite la
   |
help: Remove unused `noqa` directive
   |
62 |         spec = RecordingSpec(**body)
   -     except Exception as exc:  # noqa: BLE001 - ValidationError de pydantic y kwargs sobrantes
63 +     except Exception as exc:
64 |         # pydantic incluye el valor recibido en el mensaje de error (p. ej. si
   |

I001 [*] Import block is un-sorted or un-formatted
  --> src/eovrt_webconsole/routers/runs.py:2:1
   |
 1 |   """Runs: lanzar (compose→launch), listar hidratado, estado y stop (Spec B §5.5/§6)."""
 2 | / from __future__ import annotations
 3 | |
 4 | | import logging
 5 | | import re
 6 | | from datetime import UTC, datetime
 7 | |
 8 | | from fastapi import APIRouter, HTTPException, Query, Request
 9 | | from fastapi.responses import JSONResponse, Response, StreamingResponse
10 | | from starlette.background import BackgroundTask
11 | |
12 | | from eovrt_webconsole.evidence import Vista, coincide_vista
13 | | from eovrt_webconsole.experiment.control_backend import (
14 | |     RunActive as ControlRunActive,
15 | |     ServiceUnavailable as ControlServiceUnavailable,
16 | |     UnknownRun as ControlUnknownRun,
17 | | )
18 | | from eovrt_webconsole.routers.compose import validate_composition
19 | | from eovrt_webconsole.run_backend import (
20 | |     RunActive, RunBusy, RunNotFinished, ServiceRejected, ServiceUnavailable, UnknownRun,
21 | | )
22 | | from eovrt_webconsole.trace import build_trace_index, compose_trace, filtrar_frames
23 | | from eovrt_webconsole.translation import Composition, composition_to_run_request
   | |________________________________________________________________________________^
24 |
25 |   logger = logging.getLogger(__name__)
   |
help: Organize imports
   |
14 |     RunActive as ControlRunActive,
15 + )
16 + from eovrt_webconsole.experiment.control_backend import (
17 |     ServiceUnavailable as ControlServiceUnavailable,
18 + )
19 + from eovrt_webconsole.experiment.control_backend import (
20 |     UnknownRun as ControlUnknownRun,
21 | )
22 | from eovrt_webconsole.routers.compose import validate_composition
23 | from eovrt_webconsole.run_backend import (
   -     RunActive, RunBusy, RunNotFinished, ServiceRejected, ServiceUnavailable, UnknownRun,
24 +     RunActive,
25 +     RunBusy,
26 +     RunNotFinished,
27 +     ServiceRejected,
28 +     ServiceUnavailable,
29 +     UnknownRun,
30 | )
   |

RUF059 Unpacked variable `state` is never used
  --> tests/test_control_backend.py:24:14
   |
23 | async def test_launch_live_returns_control_run_id_and_subscribed(control_backend):
24 |     backend, state = control_backend
   |              ^^^^^
25 |     run_id = await backend.launch({"input": {"type": "bus"}}, mode="live", experiment_id="exp-1")
26 |     assert run_id
   |
help: Prefix it with an underscore or any other dummy variable pattern

SIM117 [*] Use a single `with` statement with multiple contexts instead of nested `with` statements
   --> tests/test_distribution_http.py:278:5
    |
276 |   async def test_timeout_es_diagnosticable_y_queda_logueado(monkeypatch, tmp_path, caplog):
277 |       monkeypatch.setattr(f"{_MOD}.httpx.AsyncClient", _FakeClientNeverTerminal)
278 | /     with caplog.at_level(logging.WARNING, logger=_MOD):
279 | |         with pytest.raises(TimeoutError) as excinfo:
    | |____________________________________________________^
280 |               await run_distribution_http(
281 |                   mode="replay",
    |
help: Combine `with` statements
    |
277 |     monkeypatch.setattr(f"{_MOD}.httpx.AsyncClient", _FakeClientNeverTerminal)
    -     with caplog.at_level(logging.WARNING, logger=_MOD):
    -         with pytest.raises(TimeoutError) as excinfo:
    -             await run_distribution_http(
    -                 mode="replay",
    -                 alerts_path=tmp_path / "a.jsonl",
    -                 out_dir=tmp_path / "out",
    -                 config_path=None,
    -                 endpoint=None,
    -                 control_run_id=None,
    -                 backfill_path=None,
    -                 idle_timeout_ms=None,
    -                 timeout_s=0.05,
    -                 base_url="http://x",
    -                 poll_interval_s=0.01,
    -             )
278 +     with caplog.at_level(logging.WARNING, logger=_MOD), pytest.raises(TimeoutError) as excinfo:
279 +         await run_distribution_http(
280 +             mode="replay",
281 +             alerts_path=tmp_path / "a.jsonl",
282 +             out_dir=tmp_path / "out",
283 +             config_path=None,
284 +             endpoint=None,
285 +             control_run_id=None,
286 +             backfill_path=None,
287 +             idle_timeout_ms=None,
288 +             timeout_s=0.05,
289 +             base_url="http://x",
290 +             poll_interval_s=0.01,
291 +         )
292 |     message = str(excinfo.value)
    |

SIM117 [*] Use a single `with` statement with multiple contexts instead of nested `with` statements
   --> tests/test_distribution_http.py:421:5
    |
419 |   ):
420 |       monkeypatch.setattr(f"{_MOD}.httpx.AsyncClient", _FakeClientCancelPostFails)
421 | /     with caplog.at_level(logging.WARNING, logger=_MOD):
422 | |         with pytest.raises(TimeoutError) as excinfo:
    | |____________________________________________________^
423 |               await run_distribution_http(
424 |                   mode="replay",
    |
help: Combine `with` statements
    |
420 |     monkeypatch.setattr(f"{_MOD}.httpx.AsyncClient", _FakeClientCancelPostFails)
    -     with caplog.at_level(logging.WARNING, logger=_MOD):
    -         with pytest.raises(TimeoutError) as excinfo:
    -             await run_distribution_http(
    -                 mode="replay",
    -                 alerts_path=tmp_path / "a.jsonl",
    -                 out_dir=tmp_path / "out",
    -                 config_path=None,
    -                 endpoint=None,
    -                 control_run_id=None,
    -                 backfill_path=None,
    -                 idle_timeout_ms=None,
    -                 timeout_s=0.05,
    -                 base_url="http://x",
    -                 poll_interval_s=0.01,
    -             )
421 +     with caplog.at_level(logging.WARNING, logger=_MOD), pytest.raises(TimeoutError) as excinfo:
422 +         await run_distribution_http(
423 +             mode="replay",
424 +             alerts_path=tmp_path / "a.jsonl",
425 +             out_dir=tmp_path / "out",
426 +             config_path=None,
427 +             endpoint=None,
428 +             control_run_id=None,
429 +             backfill_path=None,
430 +             idle_timeout_ms=None,
431 +             timeout_s=0.05,
432 +             base_url="http://x",
433 +             poll_interval_s=0.01,
434 +         )
435 |     # la excepcion original (timeout, con run_id/timeout_s/ultimo status) llega intacta
    |

F401 [*] `pytest` imported but unused
 --> tests/test_distribution_preflight_unit.py:5:8
  |
4 | import httpx
5 | import pytest
  |        ^^^^^^
6 | import yaml
  |
help: Remove unused import: `pytest`
  |
4 | import httpx
  - import pytest
5 | import yaml
  |

PLW1510 `subprocess.run` without explicit `check` argument
  --> tests/test_record_oakd_script.py:17:12
   |
15 | def _run(args, env_extra=None, timeout=20):
16 |     env = {**os.environ, **(env_extra or {})}
17 |     return subprocess.run(
   |            ^^^^^^^^^^^^^^
18 |         [sys.executable, str(SCRIPT), *args],
19 |         capture_output=True, text=True, timeout=timeout, env=env,
   |
help: Add explicit `check=False`

C408 Unnecessary `dict()` call (rewrite as a literal)
  --> tests/test_recording_sidecar.py:10:12
   |
 9 |   def _result(path, **kwargs):
10 |       base = dict(
   |  ____________^
11 | |         path=path,
12 | |         started_wallclock_ms=1784646000000,
13 | |         duration_ms=33150,
14 | |         size_bytes=path.stat().st_size,
15 | |         truncated=False,
16 | |         error=None,
17 | |     )
   | |_____^
18 |       base.update(kwargs)
19 |       return RecordingResult(**base)
   |
help: Rewrite as a literal

UP017 [*] Use `datetime.UTC` alias
  --> tests/test_runner_clip_id_injection.py:23:46
   |
21 | from tests.fake_service import FakeState, make_fake_service
22 |
23 | NOW = datetime(2026, 7, 12, 14, 0, 0, tzinfo=timezone.utc)
   |                                              ^^^^^^^^^^^^
24 |
25 | CONTROL_CONFIG = {"pattern_set": "cr01_cr02_v2"}
   |
help: Convert to `datetime.UTC` alias
   |
10 |
   - from datetime import datetime, timezone
11 + from datetime import datetime, timezone, UTC
12 |
--------------------------------------------------------------------------------
22 |
   - NOW = datetime(2026, 7, 12, 14, 0, 0, tzinfo=timezone.utc)
23 + NOW = datetime(2026, 7, 12, 14, 0, 0, tzinfo=UTC)
24 |
   |

UP017 [*] Use `datetime.UTC` alias
  --> tests/test_runner_gate.py:30:46
   |
28 | from tests.fake_service import FakeState, make_fake_service
29 |
30 | NOW = datetime(2026, 7, 12, 14, 0, 0, tzinfo=timezone.utc)
   |                                              ^^^^^^^^^^^^
31 |
32 | REPLAY_MEDIA_CONFIG = {
   |
help: Convert to `datetime.UTC` alias
   |
18 |
   - from datetime import datetime, timezone
19 + from datetime import datetime, timezone, UTC
20 |
--------------------------------------------------------------------------------
29 |
   - NOW = datetime(2026, 7, 12, 14, 0, 0, tzinfo=timezone.utc)
30 + NOW = datetime(2026, 7, 12, 14, 0, 0, tzinfo=UTC)
31 |
   |

UP017 [*] Use `datetime.UTC` alias
  --> tests/test_runner_report_wiring.py:19:46
   |
17 | from tests.fake_service import FakeState, make_fake_service
18 |
19 | NOW = datetime(2026, 7, 12, 14, 0, 0, tzinfo=timezone.utc)
   |                                              ^^^^^^^^^^^^
20 |
21 | MEDIA_CONFIG = {"ingest": {"type": "image_folder", "path": "demo"}, "prompts": {"ref": "demo_set"}}
   |
help: Convert to `datetime.UTC` alias
   |
5  | import logging
   - from datetime import datetime, timezone
6  + from datetime import datetime, timezone, UTC
7  | from pathlib import Path
--------------------------------------------------------------------------------
18 |
   - NOW = datetime(2026, 7, 12, 14, 0, 0, tzinfo=timezone.utc)
19 + NOW = datetime(2026, 7, 12, 14, 0, 0, tzinfo=UTC)
20 |
   |

UP017 [*] Use `datetime.UTC` alias
  --> tests/test_runner_temporal_evaluation.py:28:46
   |
26 | from tests.fake_service import FakeState, make_fake_service
27 |
28 | NOW = datetime(2026, 7, 12, 14, 0, 0, tzinfo=timezone.utc)
   |                                              ^^^^^^^^^^^^
29 |
30 | MEDIA_CONFIG = {"ingest": {"plugin": "video_file", "config": {"path": "clip.mp4"}},
   |
help: Convert to `datetime.UTC` alias
   |
13 | import logging
   - from datetime import datetime, timezone
14 + from datetime import datetime, timezone, UTC
15 | from pathlib import Path
--------------------------------------------------------------------------------
27 |
   - NOW = datetime(2026, 7, 12, 14, 0, 0, tzinfo=timezone.utc)
28 + NOW = datetime(2026, 7, 12, 14, 0, 0, tzinfo=UTC)
29 |
   |

RET501 [*] Do not explicitly `return None` in function if it is the only possible return value
   --> tests/test_runner_temporal_evaluation.py:207:9
    |
205 |     def fake_evaluate_temporal(*args):
206 |         calls.append(args)
207 |         return None
    |         ^^^^^^^^^^^
208 |
209 |     dest_root = tmp_path / "runs"
    |
help: Remove explicit `return None`
    |
206 |         calls.append(args)
    -         return None
207 +         return
208 |
    |

PLR1711 [*] Useless `return` statement at end of function
   --> tests/test_runner_temporal_evaluation.py:207:9
    |
205 |     def fake_evaluate_temporal(*args):
206 |         calls.append(args)
207 |         return None
    |         ^^^^^^^^^^^
208 |
209 |     dest_root = tmp_path / "runs"
    |
help: Remove useless `return` statement
    |
206 |         calls.append(args)
    -         return None
207 |
    |

I001 [*] Import block is un-sorted or un-formatted
   --> tests/test_runs_router.py:249:5
    |
248 | def test_delete_reintento_idempotente_tras_fallo_parcial(two_plane_client, fake_state, control_state, monkeypatch):
249 |     from eovrt_webconsole.experiment.control_backend import ServiceUnavailable as ControlServiceUnavailable
    |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
250 |
251 |     control_state.runs_index = [
    |
help: Organize imports
    |
248 | def test_delete_reintento_idempotente_tras_fallo_parcial(two_plane_client, fake_state, control_state, monkeypatch):
    -     from eovrt_webconsole.experiment.control_backend import ServiceUnavailable as ControlServiceUnavailable
249 +     from eovrt_webconsole.experiment.control_backend import (
250 +         ServiceUnavailable as ControlServiceUnavailable,
251 +     )
252 |
    |

I001 [*] Import block is un-sorted or un-formatted
   --> tests/test_runs_router.py:308:5
    |
306 |     media NUNCA se llega a tocar en esa llamada: solo aparece "control" en
307 |     errors, y el lado media queda intacto (visible) para el reintento."""
308 |     from eovrt_webconsole.experiment.control_backend import ServiceUnavailable as ControlServiceUnavailable
    |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
309 |
310 |     control_state.runs_index = [
    |
help: Organize imports
    |
307 |     errors, y el lado media queda intacto (visible) para el reintento."""
    -     from eovrt_webconsole.experiment.control_backend import ServiceUnavailable as ControlServiceUnavailable
308 +     from eovrt_webconsole.experiment.control_backend import (
309 +         ServiceUnavailable as ControlServiceUnavailable,
310 +     )
311 |
    |

I001 [*] Import block is un-sorted or un-formatted
   --> tests/test_runs_router.py:342:5
    |
340 |     media y ese lado falla. El run sigue visible en todo momento hasta que
341 |     ambos lados terminan bien."""
342 |     from eovrt_webconsole.experiment.control_backend import ServiceUnavailable as ControlServiceUnavailable
    |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
343 |
344 |     control_state.runs_index = [
    |
help: Organize imports
    |
341 |     ambos lados terminan bien."""
    -     from eovrt_webconsole.experiment.control_backend import ServiceUnavailable as ControlServiceUnavailable
342 +     from eovrt_webconsole.experiment.control_backend import (
343 +         ServiceUnavailable as ControlServiceUnavailable,
344 +     )
345 |
    |

SIM117 [*] Use a single `with` statement with multiple contexts instead of nested `with` statements
  --> tests/test_stream_proxy.py:24:5
   |
22 |       settings_dead = dataclasses.replace(settings, service_url="http://127.0.0.1:9")
23 |       app = create_app(settings_dead)
24 | /     with TestClient(app) as client:
25 | |         with client.websocket_connect("/api/runs/run_x/stream") as ws:
   | |______________________________________________________________________^
26 |               # El upstream nunca conecta: el handler debe cerrar con 4503 sin
27 |               # propagar ProtocolError/WebSocketException al ASGI.
   |
help: Combine `with` statements
   |
23 |     app = create_app(settings_dead)
   -     with TestClient(app) as client:
   -         with client.websocket_connect("/api/runs/run_x/stream") as ws:
   -             # El upstream nunca conecta: el handler debe cerrar con 4503 sin
   -             # propagar ProtocolError/WebSocketException al ASGI.
   -             try:
   -                 ws.receive()
   -             except Exception:  # noqa: BLE001 — el cierre del WS corta el loop
   -                 pass
24 +     with TestClient(app) as client, client.websocket_connect("/api/runs/run_x/stream") as ws:
25 +         # El upstream nunca conecta: el handler debe cerrar con 4503 sin
26 +         # propagar ProtocolError/WebSocketException al ASGI.
27 +         try:
28 +             ws.receive()
29 +         except Exception:  # noqa: BLE001 — el cierre del WS corta el loop
30 +             pass
31 |     # Si llegamos acá sin excepción no manejada, el fix del handler sostiene.
   |

S110 `try`-`except`-`pass` detected, consider logging the exception
  --> tests/test_stream_proxy.py:30:13
   |
28 |               try:
29 |                   ws.receive()
30 | /             except Exception:  # noqa: BLE001 — el cierre del WS corta el loop
31 | |                 pass
   | |____________________^
32 |       # Si llegamos acá sin excepción no manejada, el fix del handler sostiene.
   |

S110 `try`-`except`-`pass` detected, consider logging the exception
  --> tests/test_stream_proxy.py:57:9
   |
55 |               while True:
56 |                   received.append(ws.receive_json())
57 | /         except Exception:  # noqa: BLE001 — el cierre del WS corta el loop
58 | |             pass
   | |________________^
59 |       types = [e["type"] for e in received]
60 |       assert "state" in types
   |

S110 `try`-`except`-`pass` detected, consider logging the exception
  --> tests/test_stream_proxy.py:77:9
   |
75 |               while True:
76 |                   received.append(ws.receive_json())
77 | /         except Exception:  # noqa: BLE001 — el cierre del WS corta el loop
78 | |             pass
   | |________________^
79 |       types = [e["type"] for e in received]
80 |       # Si el frame malformado hubiera matado el pump, no llegaría ningún evento.
   |

S110 `try`-`except`-`pass` detected, consider logging the exception
   --> tests/test_stream_proxy.py:106:9
    |
104 |               while True:
105 |                   ws.receive_json()
106 | /         except Exception:  # noqa: BLE001
107 | |             pass
    | |________________^
108 |       # el cierre llegó sin eventos: el fake cerró 4404 y el proxy lo reenvió
    |

SIM117 [*] Use a single `with` statement with multiple contexts instead of nested `with` statements
   --> tests/test_stream_proxy.py:129:5
    |
127 |       settings_dead = dataclasses.replace(settings, service_url="http://127.0.0.1:9")
128 |       app = create_app(settings_dead)
129 | /     with TestClient(app) as client:
130 | |         with client.websocket_connect("/api/preview/stream") as ws:
    | |___________________________________________________________________^
131 |               try:
132 |                   ws.receive()
    |
help: Combine `with` statements
    |
128 |     app = create_app(settings_dead)
    -     with TestClient(app) as client:
    -         with client.websocket_connect("/api/preview/stream") as ws:
    -             try:
    -                 ws.receive()
    -             except Exception:  # noqa: BLE001 — el cierre del WS corta el loop
    -                 pass
129 +     with TestClient(app) as client, client.websocket_connect("/api/preview/stream") as ws:
130 +         try:
131 +             ws.receive()
132 +         except Exception:  # noqa: BLE001 — el cierre del WS corta el loop
133 +             pass
134 |
    |

S110 `try`-`except`-`pass` detected, consider logging the exception
   --> tests/test_stream_proxy.py:133:13
    |
131 |               try:
132 |                   ws.receive()
133 | /             except Exception:  # noqa: BLE001 — el cierre del WS corta el loop
134 | |                 pass
    | |____________________^

Found 36 errors.
[*] 23 fixable with the `--fix` option (3 hidden fixes can be enabled with the `--unsafe-fixes` option).
```

### Comparación de Ruff

```text
$ Multiconjunto por archivo, código y mensaje contra la línea de base de 36
Línea de base Ruff: 36
Diagnósticos actuales: 36
Diagnósticos nuevos: 0
Diagnósticos eliminados: 0
```

### Lint del script A.4

```text
$ webconsole/backend/.venv/bin/ruff check webconsole/tools/classify_evidence.py
All checks passed!
```

### Contraste independiente con el dato crudo

```text
$ Lectura directa de los cuatro pares summary.json y cruce contra CSV
exp_20260813T051644827375Z_talert_admission-1
  media/summary.json: run_20260813_051644_dbe_grounding_dino_3399b8
  control/summary.json: control_talert_integrated_a_p1_c08_20260813T051644Z_275fb5
  CSV: []
exp_20260813T051703399915Z_talert_repetition-1
  media/summary.json: run_20260813_051703_dbe_grounding_dino_1d5e83
  control/summary.json: control_talert_integrated_a_p1_c08_20260813T051703Z_21e369
  CSV: ['realtime/t_alert_notification']
exp_20260813T051718284240Z_talert_repetition-2
  media/summary.json: run_20260813_051718_dbe_grounding_dino_5135ac
  control/summary.json: control_talert_integrated_a_p1_c08_20260813T051718Z_362334
  CSV: ['realtime/t_alert_notification']
exp_20260813T051736306649Z_talert_repetition-3
  media/summary.json: run_20260813_051736_dbe_grounding_dino_6fac85
  control/summary.json: control_talert_integrated_a_p1_c08_20260813T051736Z_200a27
  CSV: ['realtime/t_alert_notification']
Contraste independiente: admisión excluida; tres repeticiones incluidas.
```

### Contraste de la regla con el resultado esperado

```text
$ Clasificador recursivo contra 11 paraguas reales
Tiempo de clasificación: 1.35 s
diag_riesgo_activo 5 0
ebe_oakd_live 0 0
ebe_p1_live 0 0
ebe_p2_live 0 0
ebe_p3_live 0 0
rt-01 0 0
talert_camera_smoke 0 0
talert_integrated_video 4 3
exp_20260813T051644827375Z_talert_admission-1 False []
run_ids: ['control_talert_integrated_a_p1_c08_20260813T051644Z_275fb5', 'run_20260813_051644_dbe_grounding_dino_3399b8']
exp_20260813T051703399915Z_talert_repetition-1 True ['realtime/t_alert_notification']
run_ids: ['control_talert_integrated_a_p1_c08_20260813T051703Z_21e369', 'run_20260813_051703_dbe_grounding_dino_1d5e83']
exp_20260813T051718284240Z_talert_repetition-2 True ['realtime/t_alert_notification']
run_ids: ['control_talert_integrated_a_p1_c08_20260813T051718Z_362334', 'run_20260813_051718_dbe_grounding_dino_5135ac']
exp_20260813T051736306649Z_talert_repetition-3 True ['realtime/t_alert_notification']
run_ids: ['control_talert_integrated_a_p1_c08_20260813T051736Z_200a27', 'run_20260813_051736_dbe_grounding_dino_6fac85']
yoloe_p1_live 0 0
yoloe_p2_live 0 0
yoloe_p3_live 0 0
CONTRASTE ESPERADO: correcto
```

### Paridad de campos y partición de API real

```text
$ Comparación del BFF anterior 8090 con el final 8091
GET /api/experiments/manifests sin vista y vista=todas: idénticos.
Campos preexistentes frente al BFF anterior: idénticos; 11 filas.
Partición real: evidencia=1, archivadas=10, todas=11; sin solapamiento.
n_runs histórico de talert: 0
n_executions del clasificador: 4
Enlaces de evidencia: 3
```

### Navegador final

```text
$ node /tmp/eovrt-tramo6-cierre/capture.mjs
{
  "viewport": {
    "width": 1440,
    "height": 1000
  },
  "records": [
    {
      "surface": "corridas",
      "vista": "evidencia",
      "widths": {
        "viewport": 1440,
        "current": 1444,
        "withoutBadges": 1444
      },
      "rows": 25,
      "control": "Evidencia\nArchivadas\nTodas\n52 corridas archivadas"
    },
    {
      "surface": "corridas",
      "vista": "archivadas",
      "widths": {
        "viewport": 1440,
        "current": 1484,
        "withoutBadges": 1484
      },
      "rows": 25,
      "control": "Evidencia\nArchivadas\nTodas"
    },
    {
      "surface": "corridas",
      "vista": "todas",
      "widths": {
        "viewport": 1440,
        "current": 1444,
        "withoutBadges": 1444
      },
      "rows": 25,
      "control": "Evidencia\nArchivadas\nTodas"
    },
    {
      "surface": "experimentos",
      "vista": "evidencia",
      "widths": {
        "viewport": 1440,
        "current": 1440,
        "withoutBadges": 1440
      },
      "rows": 1,
      "control": "Evidencia\nArchivadas\nTodas\n426 ejecuciones archivadas"
    },
    {
      "surface": "experimentos",
      "vista": "archivadas",
      "widths": {
        "viewport": 1440,
        "current": 1440,
        "withoutBadges": 1440
      },
      "rows": 10,
      "control": "Evidencia\nArchivadas\nTodas"
    },
    {
      "surface": "experimentos",
      "vista": "todas",
      "widths": {
        "viewport": 1440,
        "current": 1473,
        "withoutBadges": 1473
      },
      "rows": 11,
      "control": "Evidencia\nArchivadas\nTodas"
    }
  ],
  "opened": [
    {
      "id": "exp_20260813T051736306649Z_talert_repetition-3",
      "status": {
        "/detail": 200,
        "/report": 200,
        "/alerts": 200
      },
      "heading": "talert_integrated_video"
    },
    {
      "id": "exp_20260813T051718284240Z_talert_repetition-2",
      "status": {
        "/detail": 200,
        "/report": 200,
        "/alerts": 200
      },
      "heading": "talert_integrated_video"
    },
    {
      "id": "exp_20260813T051703399915Z_talert_repetition-1",
      "status": {
        "/detail": 200,
        "/report": 200,
        "/alerts": 200
      },
      "heading": "talert_integrated_video"
    }
  ],
  "persistence": "ambas pantallas",
  "errors": []
}
```

### Consola principal reiniciada

```text
$ Comprobación HTTP en 127.0.0.1:8090
GET /api/experiments/manifests: HTTP 200, 11 manifiestos
GET /api/experiments/manifests?vista=todas: HTTP 200, 11 manifiestos
GET /api/experiments/manifests?vista=evidencia: HTTP 200, 1 manifiestos
GET /api/experiments/manifests?vista=archivadas: HTTP 200, 10 manifiestos
Evidencia: talert_integrated_video; 4 ejecuciones, 3 enlaces. Default: todas.
```

### Integridad

```text
$ Hashes protegidos, función del listado y worktree de paridad
Tests preexistentes, contrato, nav.ts, tramo-7 y cambios ajenos: hashes idénticos.
_ejecuciones_por_slug: función idéntica al inicio.
/tmp/paridad: 50b666b intacto y worktree conservado.
$ git diff --check
exit=0
$ git diff --cached --check
exit=0
```

### Backend focal

```text
$ cd webconsole/backend && ./.venv/bin/python -m pytest -q tests/test_evidence_recursive.py tests/test_evidence.py tests/test_experiment_history.py tests/test_experiments_listing_fields.py
.......................................                                  [100%]
39 passed in 2.23s
```

### Frontend focal

```text
$ cd webconsole/frontend && npx vitest run src/__tests__/ExperimentsEvidence.test.tsx src/__tests__/ExperimentsPage.test.tsx src/__tests__/contrato

 RUN  v2.1.9 /home/simonll4/projects/e-ovrt_experimental-setup/webconsole/frontend

stderr | src/__tests__/ExperimentsPage.test.tsx > ExperimentsPage > lista manifiestos y dispara un experimento con preflight verde
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ExperimentsEvidence.test.tsx > pide evidencia, conserva el conteo histórico y ofrece los tres enlaces de consolidaciones
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

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

 ✓ src/__tests__/ExperimentsPage.test.tsx (5 tests) 460ms
 ✓ src/__tests__/ExperimentsEvidence.test.tsx (3 tests) 448ms
 ✓ src/__tests__/contrato/detalle-traza-evaluacion.contrato.test.tsx (1 test) 393ms
   ✓ Contrato: detalle, traza y evaluación > lee detalle y traza, permite inspeccionar cuadros y evaluar contra BENCH 392ms
 ✓ src/__tests__/contrato/corrida-viva.contrato.test.tsx (2 tests) 426ms
 ✓ src/__tests__/contrato/experimentos-distribucion.contrato.test.tsx (4 tests) 728ms
   ✓ Contrato: experimentos y distribución > lista y abre un experimento con outcomes vinculados a cada alerta 334ms
 ✓ src/__tests__/contrato/nueva-corrida.contrato.test.tsx (3 tests) 848ms
   ✓ Contrato: nueva corrida > consulta preflight, compone fuente y prompts, lanza y abre el detalle real 563ms

 Test Files  6 passed (6)
      Tests  18 passed (18)
   Start at  03:44:46
   Duration  3.18s (transform 1.20s, setup 0ms, collect 4.97s, tests 3.30s, environment 5.09s, prepare 1.13s)

```

## Intentos intermedios conservados

El primer backend completo detectó la dependencia indebida del lifespan en el
listado tras derivar; se corrigió la inicialización de la app. La ejecución
siguiente encontró `CancelledError` al salir del contexto de un WebSocket.
El archivo completo de streaming pasó después sus doce pruebas y la última
suite completa pasó 800 sin cambios en streaming ni en sus tests. Se deja
constancia del fallo intermitente observado; no se afirma una causa raíz probada.

La prueba nueva de alternancia de Experimentos detectó que el estado de carga
retiraba el control mientras cambiaba la consulta. Se conserva la página anterior
con `placeholderData`, igual que en Corridas; pasó sin cambiar sus aserciones.
Los primeros lint del código nuevo señalaron SIM102, F401 e ISC004; se corrigieron.
Se acotó el ancho de los enlaces largos tras inspeccionar la primera captura.
Una variante del distintivo agregó un span y rompió la aserción preexistente
sobre `title`; se retiró esa variante y se mantuvo la estructura original,
aplicando el recorte visual sólo mediante CSS; el texto completo queda en el DOM.
La variante con texto acortado tampoco pasó la prueba nueva y fue retirada. El test se conservó intacto.

### Backend: fallo de inicialización

```text
........................................................................ [  9%]
........................................................................ [ 18%]
........................................................................ [ 27%]
.........................................................F.............. [ 36%]
........................................................................ [ 45%]
........................................................................ [ 54%]
........................................................................ [ 63%]
........................................................................ [ 72%]
........................................................................ [ 81%]
........................................................................ [ 90%]
........................................................................ [ 99%]
........                                                                 [100%]
=================================== FAILURES ===================================
__________________________ test_aparece_en_el_listado __________________________

self = <starlette.datastructures.State object at 0x761fa21868a0>
key = 'evidence'

    def __getattr__(self, key: Any) -> Any:
        try:
>           return self._state[key]
                   ^^^^^^^^^^^^^^^^
E           KeyError: 'evidence'

.venv/lib/python3.14/site-packages/starlette/datastructures.py:683: KeyError

During handling of the above exception, another exception occurred:

client = <starlette.testclient.TestClient object at 0x761fa20b2cf0>

    def test_aparece_en_el_listado(client):
        _derive(client, {"new_slug": "nuevo", "overrides": {}})
>       slugs = [m["slug"] for m in client.get("/api/experiments/manifests").json()]
                                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

tests/test_experiments_derive_route.py:96:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
.venv/lib/python3.14/site-packages/starlette/testclient.py:483: in get
    return super().get(
.venv/lib/python3.14/site-packages/httpx2/_client.py:1120: in get
    return self.request(
.venv/lib/python3.14/site-packages/starlette/testclient.py:455: in request
    return super().request(
.venv/lib/python3.14/site-packages/httpx2/_client.py:804: in request
    return self.send(request, auth=auth, follow_redirects=follow_redirects)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.venv/lib/python3.14/site-packages/httpx2/_client.py:987: in send
    response = self._send_handling_auth(
.venv/lib/python3.14/site-packages/httpx2/_client.py:1015: in _send_handling_auth
    response = self._send_handling_redirects(
.venv/lib/python3.14/site-packages/httpx2/_client.py:1050: in _send_handling_redirects
    response = self._send_single_request(request)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.venv/lib/python3.14/site-packages/httpx2/_client.py:1083: in _send_single_request
    response = transport.handle_request(request)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.venv/lib/python3.14/site-packages/starlette/testclient.py:354: in handle_request
    raise exc
.venv/lib/python3.14/site-packages/starlette/testclient.py:351: in handle_request
    portal.call(self.app, scope, receive, send)
.venv/lib/python3.14/site-packages/anyio/from_thread.py:338: in call
    return cast(T_Retval, self.start_task_soon(func, *args).result())
                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
/usr/lib/python3.14/concurrent/futures/_base.py:450: in result
    return self.__get_result()
           ^^^^^^^^^^^^^^^^^^^
/usr/lib/python3.14/concurrent/futures/_base.py:395: in __get_result
    raise self._exception
.venv/lib/python3.14/site-packages/anyio/from_thread.py:263: in _call_func
    retval = await retval_or_awaitable
             ^^^^^^^^^^^^^^^^^^^^^^^^^
.venv/lib/python3.14/site-packages/fastapi/applications.py:1163: in __call__
    await super().__call__(scope, receive, send)
.venv/lib/python3.14/site-packages/starlette/applications.py:96: in __call__
    await self.middleware_stack(scope, receive, send)
.venv/lib/python3.14/site-packages/starlette/middleware/errors.py:186: in __call__
    raise exc
.venv/lib/python3.14/site-packages/starlette/middleware/errors.py:164: in __call__
    await self.app(scope, receive, _send)
.venv/lib/python3.14/site-packages/starlette/middleware/exceptions.py:63: in __call__
    await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
.venv/lib/python3.14/site-packages/starlette/_exception_handler.py:53: in wrapped_app
    raise exc
.venv/lib/python3.14/site-packages/starlette/_exception_handler.py:42: in wrapped_app
    await app(scope, receive, sender)
.venv/lib/python3.14/site-packages/fastapi/middleware/asyncexitstack.py:18: in __call__
    await self.app(scope, receive, send)
.venv/lib/python3.14/site-packages/starlette/routing.py:670: in __call__
    await self.middleware_stack(scope, receive, send)
.venv/lib/python3.14/site-packages/fastapi/routing.py:2734: in app
    await route.handle(scope, receive, send)
.venv/lib/python3.14/site-packages/fastapi/routing.py:1780: in handle
    await self.original_router.handle(scope, receive, send)
.venv/lib/python3.14/site-packages/fastapi/routing.py:2789: in handle
    await included_router._handle_selected(scope, receive, send)
.venv/lib/python3.14/site-packages/fastapi/routing.py:1800: in _handle_selected
    await original_route.handle(scope, receive, send)
.venv/lib/python3.14/site-packages/fastapi/routing.py:1279: in handle
    await app(scope, receive, send)
.venv/lib/python3.14/site-packages/fastapi/routing.py:158: in app
    await wrap_app_handling_exceptions(app, request)(scope, receive, send)
.venv/lib/python3.14/site-packages/starlette/_exception_handler.py:53: in wrapped_app
    raise exc
.venv/lib/python3.14/site-packages/starlette/_exception_handler.py:42: in wrapped_app
    await app(scope, receive, sender)
.venv/lib/python3.14/site-packages/fastapi/routing.py:144: in app
    response = await f(request)
               ^^^^^^^^^^^^^^^^
.venv/lib/python3.14/site-packages/fastapi/routing.py:706: in app
    raw_response = await run_endpoint_function(
.venv/lib/python3.14/site-packages/fastapi/routing.py:352: in run_endpoint_function
    return await dependant.call(**values)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
src/eovrt_webconsole/routers/experiments.py:130: in list_manifests
    registry = request.app.state.evidence
               ^^^^^^^^^^^^^^^^^^^^^^^^^^
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

self = <starlette.datastructures.State object at 0x761fa21868a0>
key = 'evidence'

    def __getattr__(self, key: Any) -> Any:
        try:
            return self._state[key]
        except KeyError:
            message = "'{}' object has no attribute '{}'"
>           raise AttributeError(message.format(self.__class__.__name__, key))
E           AttributeError: 'State' object has no attribute 'evidence'

.venv/lib/python3.14/site-packages/starlette/datastructures.py:686: AttributeError
=========================== short test summary info ============================
FAILED tests/test_experiments_derive_route.py::test_aparece_en_el_listado - A...
1 failed, 799 passed in 114.00s (0:01:54)
```

### Backend: cancelación WebSocket

```text
........................................................................ [  9%]
........................................................................ [ 18%]
........................................................................ [ 27%]
........................................................................ [ 36%]
........................................................................ [ 45%]
........................................................................ [ 54%]
........................................................................ [ 63%]
........................................................................ [ 72%]
........................................................................ [ 81%]
.....................................................................F.. [ 90%]
........................................................................ [ 99%]
........                                                                 [100%]
=================================== FAILURES ===================================
_______________________ test_ws_preview_reenvia_binario ________________________

live_client = <starlette.testclient.TestClient object at 0x7d82f4d7a470>

    def test_ws_preview_reenvia_binario(live_client):
        import json
        import struct

>       with live_client.websocket_connect("/api/preview/stream") as ws:
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

tests/test_stream_proxy.py:115:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
.venv/lib/python3.14/site-packages/starlette/testclient.py:131: in __exit__
    return self.exit_stack.__exit__(*args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
/usr/lib/python3.14/contextlib.py:619: in __exit__
    raise exc
/usr/lib/python3.14/contextlib.py:604: in __exit__
    if cb(*exc_details):
       ^^^^^^^^^^^^^^^^
/usr/lib/python3.14/contextlib.py:482: in _exit_wrapper
    callback(*args, **kwds)
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

self = None, timeout = None

    def result(self, timeout=None):
        """Return the result of the call that the future represents.

        Args:
            timeout: The number of seconds to wait for the result if the future
                isn't done. If None, then there is no limit on the wait time.

        Returns:
            The result of the call that the future represents.

        Raises:
            CancelledError: If the future was cancelled.
            TimeoutError: If the future didn't finish executing before the given
                timeout.
            Exception: If the call raised then that exception will be raised.
        """
        try:
            with self._condition:
                if self._state in [CANCELLED, CANCELLED_AND_NOTIFIED]:
                    raise CancelledError()
                elif self._state == FINISHED:
                    return self.__get_result()

                self._condition.wait(timeout)

                if self._state in [CANCELLED, CANCELLED_AND_NOTIFIED]:
>                   raise CancelledError()
E                   concurrent.futures._base.CancelledError

/usr/lib/python3.14/concurrent/futures/_base.py:448: CancelledError
------------------------------ Captured log setup ------------------------------
WARNING  eovrt_webconsole.evidence:evidence.py:33 Registro de evidencia ausente o incompleto: /tmp/pytest-of-simonll4/pytest-9/test_ws_preview_reenvia_binari0/results/evidence-runs/collections
WARNING  eovrt_webconsole.app:app.py:91 Rama OAK-D no disponible: intérprete para la rama OAK-D inexistente: /tmp/pytest-of-simonll4/pytest-9/e-ovrt_media-plane/.venv/bin/python. Definí EOVRT_CONSOLE_OAKD_PYTHON apuntando a un Python con depthai.
=========================== short test summary info ============================
FAILED tests/test_stream_proxy.py::test_ws_preview_reenvia_binario - concurre...
1 failed, 799 passed in 86.65s (0:01:26)
```

### Streaming: verificación posterior

```text
............                                                             [100%]
12 passed in 25.00s
```

### Frontend: fallo de alternancia

```text

 RUN  v2.1.9 /home/simonll4/projects/e-ovrt_experimental-setup/webconsole/frontend

stderr | src/__tests__/ExperimentsPage.test.tsx > ExperimentsPage > lista manifiestos y dispara un experimento con preflight verde
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ExperimentsEvidence.test.tsx > pide evidencia, conserva el conteo histórico y ofrece los tres enlaces de consolidaciones
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

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

 ✓ src/__tests__/ExperimentsPage.test.tsx (5 tests) 513ms
 ✓ src/__tests__/contrato/detalle-traza-evaluacion.contrato.test.tsx (1 test) 412ms
   ✓ Contrato: detalle, traza y evaluación > lee detalle y traza, permite inspeccionar cuadros y evaluar contra BENCH 410ms
 ✓ src/__tests__/contrato/corrida-viva.contrato.test.tsx (2 tests) 475ms
 ✓ src/__tests__/contrato/experimentos-distribucion.contrato.test.tsx (4 tests) 808ms
   ✓ Contrato: experimentos y distribución > lista y abre un experimento con outcomes vinculados a cada alerta 358ms
   ✓ Contrato: experimentos y distribución > deriva un manifiesto con overrides y lanza la derivación seleccionada 339ms
 ✓ src/__tests__/contrato/nueva-corrida.contrato.test.tsx (3 tests) 907ms
   ✓ Contrato: nueva corrida > consulta preflight, compone fuente y prompts, lanza y abre el detalle real 594ms
 ❯ src/__tests__/ExperimentsEvidence.test.tsx (3 tests | 1 failed) 1472ms
   × alterna Archivadas y Todas, persiste y vuelve a evidencia sin cruzar cachés 1206ms
     → expected <span class="eo-mono"></span> to be null

Ignored nodes: comments, script, style
<html>
  <head />
  <body>
    <div />
    <div>
      <header
        class="eo-pageheader"
      >
        <div>
          <h1>
            Experimentos
          </h1>
          <div
            class="eo-pageheader__meta"
          >
            2 manifiestos
          </div>
        </div>
      </header>
      <div
        aria-label="Vista de evidencia"
        class="eo-toolbar"
        role="group"
      >
        <div
          class="eo-segmented"
        >
          <button
            aria-pressed="false"
            type="button"
          >
            Evidencia
          </button>
          <button
            aria-pressed="false"
            type="button"
          >
            Archivadas
          </button>
          <button
            aria-pressed="true"
            type="button"
          >
            Todas
          </button>
        </div>
      </div>
      <section
        class="eo-card"
      >
        <h3
          class="eo-card__title"
        >
          Antes de ejecutar
          <span
            class="eo-card__meta"
          >
            Todo listo
          </span>
        </h3>
        <div
          class="eo-card__body"
        >
          <p
            class="eo-note"
          >
            <span
              style="display: inline-flex; gap: var(--space-2); align-items: center;"
            >
              <span
                class="eo-badge eo-badge--ok"
              >
                Motor de detección
                operativo
              </span>
              <span
                class="eo-badge eo-badge--ok"
              >
                Motor de reglas
                operativo
              </span>
            </span>
             Los dos motores responden y no hay ningún experimento en curso.
          </p>
        </div>
      </section>
      <div
        class="eo-toolbar"
      >
        <div
          class="eo-search"
        >
          <span
            aria-hidden="true"
            class="eo-search__icon"
          >
            <svg
              aria-hidden="true"
              fill="none"
              height="16"
              stroke="currentColor"
              stroke-width="1.6"
              viewBox="0 0 16 16"
              width="16"
            >
              <circle
                cx="7"
                cy="7"
                r="4.6"
              />
              <path
                d="M10.4 10.4L14 14"
              />
            </svg>
          </span>
          <input
            aria-label="Buscar manifiestos por nombre o grupo"
            class="eo-search__input"
            placeholder="Buscar por manifiesto o grupo"
            type="search"
            value=""
          />
        </div>
        <span
          class="eo-toolbar__count eo-mono"
        >
          2
           de
          2
        </span>
      </div>
      <section
        class="eo-card"
      >
        <h3
          class="eo-card__title"
        >
          Manifiestos
          <span
            class="eo-card__meta"
          >
            2
          </span>
        </h3>
        <table
          class="eo-table eo-table--dense"
        >
          <thead>
            <tr>
              <th>
                Manifiesto
              </th>
              <th>
                Grupo
              </th>
              <th>
                Última ejecución
              </th>
              <th>
                Estado
              </th>
              <th
                class="eo-th--numeric"
              >
                Corridas
              </th>
              <th>
                Cuándo
              </th>
              <th
                aria-label="Acciones"
              />
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>
                <span
                  class="eo-rowname"
                >
                  <b>
                    <span
                      class="eo-mono"
                    >
                      talert_integrated_video
                    </span>
                  </b>
                  <span
                    class="eo-mono"
                  >

                    <span
                      title="realtime/t_alert_notification"
                    >
                      <span
                        class="eo-badge eo-badge--neutral"
                      >
                        realtime/t_alert_notification
                      </span>
                    </span>
                  </span>
                </span>
              </td>
              <td>
                —
              </td>
              <td
                class="eo-mono"
              >
                <div>
                  <span
                    class="eo-cell--muted"
                  >
                    3
                     ejecuciones de evidencia
                  </span>
                  <div>
                    <a
                      href="/experiments/exp_rep3"
                    >
                      exp_rep3
                    </a>
                  </div>
                  <div>
                    <a
                      href="/experiments/exp_rep2"
                    >
                      exp_rep2
                    </a>
                  </div>
                  <div>
                    <a
                      href="/experiments/exp_rep1"
                    >
                      exp_rep1
                    </a>
                  </div>
                </div>
              </td>
              <td>
                <span
                  class="eo-badge eo-badge--neutral"
                >
                  Con evidencia
                </span>
              </td>
              <td
                class="eo-num"
              >
                —
              </td>
              <td
                class="eo-cell--muted"
              >
                —
              </td>
              <td
                class="eo-cell--actions"
              >
                <button
                  class="eo-btn eo-btn--secondary"
                  type="button"
                >
                  Partir de este
                </button>

                <button
                  class="eo-btn eo-btn--primary"
                  type="button"
                >
                  Ejecutar
                </button>
              </td>
            </tr>
            <tr>
              <td>
                <span
                  class="eo-rowname"
                >
                  <b>
                    <span
                      class="eo-mono"
                    >
                      recipe
                    </span>
                  </b>
                  <span
                    class="eo-mono"
                  >

                  </span>
                </span>
              </td>
              <td>
                —
              </td>
              <td
                class="eo-mono"
              >
                <span
                  class="eo-cell--muted"
                  title="Todavía no se ejecutó, no hay resultado que ver"
                >
                  Nunca se ejecutó
                </span>
              </td>
              <td>
                <span
                  class="eo-badge eo-badge--neutral"
                >
                  Sin ejecutar
                </span>
              </td>
              <td
                class="eo-num"
              >
                —
              </td>
              <td
                class="eo-cell--muted"
              >
                —
              </td>
              <td
                class="eo-cell--actions"
              >
                <button
                  class="eo-btn eo-btn--secondary"
                  type="button"
                >
                  Partir de este
                </button>

                <button
                  class="eo-btn eo-btn--primary"
                  type="button"
                >
                  Ejecutar
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </section>
    </div>
  </body>
</html>

⎯⎯⎯⎯⎯⎯⎯ Failed Tests 1 ⎯⎯⎯⎯⎯⎯⎯

 FAIL  src/__tests__/ExperimentsEvidence.test.tsx > alterna Archivadas y Todas, persiste y vuelve a evidencia sin cruzar cachés
AssertionError: expected <span class="eo-mono"></span> to be null

Ignored nodes: comments, script, style
<html>
  <head />
  <body>
    <div />
    <div>
      <header
        class="eo-pageheader"
      >
        <div>
          <h1>
            Experimentos
          </h1>
          <div
            class="eo-pageheader__meta"
          >
            2 manifiestos
          </div>
        </div>
      </header>
      <div
        aria-label="Vista de evidencia"
        class="eo-toolbar"
        role="group"
      >
        <div
          class="eo-segmented"
        >
          <button
            aria-pressed="false"
            type="button"
          >
            Evidencia
          </button>
          <button
            aria-pressed="false"
            type="button"
          >
            Archivadas
          </button>
          <button
            aria-pressed="true"
            type="button"
          >
            Todas
          </button>
        </div>
      </div>
      <section
        class="eo-card"
      >
        <h3
          class="eo-card__title"
        >
          Antes de ejecutar
          <span
            class="eo-card__meta"
          >
            Todo listo
          </span>
        </h3>
        <div
          class="eo-card__body"
        >
          <p
            class="eo-note"
          >
            <span
              style="display: inline-flex; gap: var(--space-2); align-items: center;"
            >
              <span
                class="eo-badge eo-badge--ok"
              >
                Motor de detección
                operativo
              </span>
              <span
                class="eo-badge eo-badge--ok"
              >
                Motor de reglas
                operativo
              </span>
            </span>
             Los dos motores responden y no hay ningún experimento en curso.
          </p>
        </div>
      </section>
      <div
        class="eo-toolbar"
      >
        <div
          class="eo-search"
        >
          <span
            aria-hidden="true"
            class="eo-search__icon"
          >
            <svg
              aria-hidden="true"
              fill="none"
              height="16"
              stroke="currentColor"
              stroke-width="1.6"
              viewBox="0 0 16 16"
              width="16"
            >
              <circle
                cx="7"
                cy="7"
                r="4.6"
              />
              <path
                d="M10.4 10.4L14 14"
              />
            </svg>
          </span>
          <input
            aria-label="Buscar manifiestos por nombre o grupo"
            class="eo-search__input"
            placeholder="Buscar por manifiesto o grupo"
            type="search"
            value=""
          />
        </div>
        <span
          class="eo-toolbar__count eo-mono"
        >
          2
           de
          2
        </span>
      </div>
      <section
        class="eo-card"
      >
        <h3
          class="eo-card__title"
        >
          Manifiestos
          <span
            class="eo-card__meta"
          >
            2
          </span>
        </h3>
        <table
          class="eo-table eo-table--dense"
        >
          <thead>
            <tr>
              <th>
                Manifiesto
              </th>
              <th>
                Grupo
              </th>
              <th>
                Última ejecución
              </th>
              <th>
                Estado
              </th>
              <th
                class="eo-th--numeric"
              >
                Corridas
              </th>
              <th>
                Cuándo
              </th>
              <th
                aria-label="Acciones"
              />
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>
                <span
                  class="eo-rowname"
                >
                  <b>
                    <span
                      class="eo-mono"
                    >
                      talert_integrated_video
                    </span>
                  </b>
                  <span
                    class="eo-mono"
                  >

                    <span
                      title="realtime/t_alert_notification"
                    >
                      <span
                        class="eo-badge eo-badge--neutral"
                      >
                        realtime/t_alert_notification
                      </span>
                    </span>
                  </span>
                </span>
              </td>
              <td>
                —
              </td>
              <td
                class="eo-mono"
              >
                <div>
                  <span
                    class="eo-cell--muted"
                  >
                    3
                     ejecuciones de evidencia
                  </span>
                  <div>
                    <a
                      href="/experiments/exp_rep3"
                    >
                      exp_rep3
                    </a>
                  </div>
                  <div>
                    <a
                      href="/experiments/exp_rep2"
                    >
                      exp_rep2
                    </a>
                  </div>
                  <div>
                    <a
                      href="/experiments/exp_rep1"
                    >
                      exp_rep1
                    </a>
                  </div>
                </div>
              </td>
              <td>
                <span
                  class="eo-badge eo-badge--neutral"
                >
                  Con evidencia
                </span>
              </td>
              <td
                class="eo-num"
              >
                —
              </td>
              <td
                class="eo-cell--muted"
              >
                —
              </td>
              <td
                class="eo-cell--actions"
              >
                <button
                  class="eo-btn eo-btn--secondary"
                  type="button"
                >
                  Partir de este
                </button>

                <button
                  class="eo-btn eo-btn--primary"
                  type="button"
                >
                  Ejecutar
                </button>
              </td>
            </tr>
            <tr>
              <td>
                <span
                  class="eo-rowname"
                >
                  <b>
                    <span
                      class="eo-mono"
                    >
                      recipe
                    </span>
                  </b>
                  <span
                    class="eo-mono"
                  >

                  </span>
                </span>
              </td>
              <td>
                —
              </td>
              <td
                class="eo-mono"
              >
                <span
                  class="eo-cell--muted"
                  title="Todavía no se ejecutó, no hay resultado que ver"
                >
                  Nunca se ejecutó
                </span>
              </td>
              <td>
                <span
                  class="eo-badge eo-badge--neutral"
                >
                  Sin ejecutar
                </span>
              </td>
              <td
                class="eo-num"
              >
                —
              </td>
              <td
                class="eo-cell--muted"
              >
                —
              </td>
              <td
                class="eo-cell--actions"
              >
                <button
                  class="eo-btn eo-btn--secondary"
                  type="button"
                >
                  Partir de este
                </button>

                <button
                  class="eo-btn eo-btn--primary"
                  type="button"
                >
                  Ejecutar
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </section>
    </div>
  </body>
</html>

- Expected:
null

+ Received:
<span
  class="eo-mono"
>
  recipe
</span>

 ❯ src/__tests__/ExperimentsEvidence.test.tsx:69:60
     67|   expect(screen.getByText('recipe')).toBeTruthy()
     68|   fireEvent.click(control.getByRole('button', { name: 'Evidencia' }))
     69|   await waitFor(() => expect(screen.queryByText('recipe')).toBeNull())
       |                                                            ^
     70|   expect(screen.getByText('talert_integrated_video')).toBeTruthy()
     71| })
 ❯ runWithExpensiveErrorDiagnosticsDisabled node_modules/@testing-library/dom/dist/config.js:47:12
 ❯ checkCallback node_modules/@testing-library/dom/dist/wait-for.js:124:77
 ❯ Timeout.checkRealTimersCallback node_modules/@testing-library/dom/dist/wait-for.js:118:16

⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯[1/1]⎯

 Test Files  1 failed | 5 passed (6)
      Tests  1 failed | 17 passed (18)
   Start at  03:43:38
   Duration  3.80s (transform 1.40s, setup 0ms, collect 5.16s, tests 4.59s, environment 5.33s, prepare 1.19s)

```

### Frontend: title del distintivo

```text

> eovrt-webconsole-frontend@0.1.0 test
> vitest run


 RUN  v2.1.9 /home/simonll4/projects/e-ovrt_experimental-setup/webconsole/frontend

 ✓ src/__tests__/api.test.ts (15 tests) 217ms
stderr | src/__tests__/ExperimentDetailPageRiskBanner.test.tsx > ExperimentDetailPage — banner de riesgo activo > muestra el banner con el condition_id cuando patterns no esta vacio y el experimento corre
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ExperimentDetailPage.test.tsx > ExperimentDetailPage > muestra las alertas y avisa que el conjunto no es temporal
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ExperimentsPage.test.tsx > ExperimentsPage > lista manifiestos y dispara un experimento con preflight verde
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/RunsPage.test.tsx > RunsPage > lista corridas y marca la que está en curso
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/TrimDialog.test.tsx (9 tests) 473ms
stderr | src/__tests__/contrato/experimentos-distribucion.contrato.test.tsx > Contrato: experimentos y distribución > lista y abre un experimento con outcomes vinculados a cada alerta
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/CamerasPage.test.tsx > CamerasPage > lista los presets de cámara
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ComposePage.test.tsx > ComposePage prefill > conserva active_ids del manifiesto y no lo pisan los defaults del set
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/ExperimentDetailPageRiskBanner.test.tsx (7 tests) 602ms
stderr | src/__tests__/RunDetailPage.test.tsx > RunDetailPage > muestra el estado de la corrida con el glosario, no con el código crudo
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/ExperimentsPage.test.tsx (5 tests) 1443ms
   ✓ ExperimentsPage > lista manifiestos y dispara un experimento con preflight verde 638ms
 ✓ src/__tests__/PromptSetsPage.test.tsx (7 tests) 1612ms
   ✓ PromptSetsPage > lista los sets con badge de estado 392ms
   ✓ PromptSetsPage > un conjunto congelado no ofrece editar, sino ver 310ms
 ✓ src/__tests__/ExperimentDetailPage.test.tsx (15 tests) 1612ms
stderr | src/__tests__/ComposePage.test.tsx > ComposePage prefill de source.type video > conserva el source.type original en la composición (round-trip sin colapso a video_file)
No routes matched location "/runs/r1"

 ✓ src/__tests__/DeriveExperimentForm.test.tsx (13 tests) 1855ms
   ✓ DeriveExperimentForm > precarga los valores del manifiesto fuente 320ms
 ✓ src/__tests__/ComparePage.test.tsx (14 tests) 2141ms
   ✓ ComparePage > lista las corridas por nombre, no por identificador crudo 360ms
   ✓ ComparePage > compara al elegir dos y nombra las métricas en español 426ms
   ✓ ComparePage > no avisa cuando comparten conjunto de evaluación 316ms
 ✓ src/__tests__/RunDetailPage.test.tsx (10 tests) 2184ms
   ✓ RunDetailPage > muestra el estado de la corrida con el glosario, no con el código crudo 380ms
   ✓ RunDetailPage > las pestañas separan traza, resumen, evaluación y archivos 536ms
   ✓ RunDetailPage > borrado parcial muestra el detalle de los planos que fallaron y persiste (no navega) 369ms
 ✓ src/__tests__/contrato/experimentos-distribucion.contrato.test.tsx (4 tests) 2572ms
   ✓ Contrato: experimentos y distribución > lista y abre un experimento con outcomes vinculados a cada alerta 1039ms
   ✓ Contrato: experimentos y distribución > deriva un manifiesto con overrides y lanza la derivación seleccionada 989ms
   ✓ Contrato: experimentos y distribución > seleccionar dos corridas evaluadas pide su comparación por HTTP 342ms
stderr | src/__tests__/Shell.test.tsx > Shell > renderiza los tres títulos de grupo
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/CamerasPage.test.tsx (14 tests) 2938ms
   ✓ CamerasPage > muestra banner y deshabilita conectar ante 409 run_active 551ms
   ✓ CamerasPage > activa por defecto las clases sin enabled_by_default declarado en el YAML 319ms
 ✓ src/__tests__/RecordPanel.test.tsx (13 tests) 3435ms
   ✓ RecordPanel > mientras graba, consulta el backend periodicamente y muestra elapsed_ms/size_bytes de ahi 1104ms
   ✓ RecordPanel > si el backend informa error, deja de contar y muestra el motivo 1162ms
stderr | src/__tests__/ComposePage.test.tsx > ComposePage nombre opcional de la corrida > manda run.name cuando se completa, null cuando se deja vacío
No routes matched location "/runs/r1"

 ✓ src/__tests__/Shell.test.tsx (17 tests) 3125ms
   ✓ Shell > muestra el contador de corridas en curso cuando es mayor a 0 308ms
stderr | src/__tests__/ComposePage.test.tsx > ComposePage nombre opcional de la corrida > deja run.name en null si el campo queda vacío (usa el id autogenerado)
No routes matched location "/runs/r2"

stderr | src/__tests__/ExperimentsPage.new.test.tsx > ExperimentsPage - crear nuevo experimento (/experiments/new) > abre el formulario con un selector "basado en" precargado con el primer manifiesto
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/labels.test.ts (13 tests) 40ms
stderr | src/__tests__/contrato/nueva-corrida.contrato.test.tsx > Contrato: nueva corrida > consulta preflight, compone fuente y prompts, lanza y abre el detalle real
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/TraceSection.test.tsx (10 tests) 3056ms
   ✓ TraceSection > no vuelca todos los cuadros: la lista se acota y dice el total 1514ms
stderr | src/__tests__/ExperimentsEvidence.test.tsx > pide evidencia, conserva el conteo histórico y ofrece los tres enlaces de consolidaciones
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/LiveViewer.test.tsx (5 tests) 180ms
 ✓ src/__tests__/ExperimentsPage.new.test.tsx (4 tests) 1864ms
   ✓ ExperimentsPage - crear nuevo experimento (/experiments/new) > abre el formulario con un selector "basado en" precargado con el primer manifiesto 706ms
   ✓ ExperimentsPage - crear nuevo experimento (/experiments/new) > al cambiar la fuente en el selector, vuelve a pedir los defaults y reprecarga los campos (bug central) 503ms
   ✓ ExperimentsPage - crear nuevo experimento (/experiments/new) > en modo nuevo la card dice "Nuevo experimento" y el botón "Crear" (no "Derivar de...") 389ms
 ✓ src/__tests__/traceview.test.ts (12 tests) 23ms
 ✓ src/__tests__/PlatformPage.test.tsx (6 tests) 909ms
   ✓ PlatformPage > lista el fleet y activa una instancia 510ms
 ✓ src/__tests__/PreviewWithBoxes.test.tsx (8 tests) 277ms
 ✓ src/__tests__/RunsPage.test.tsx (22 tests) 6405ms
   ✓ RunsPage > lista corridas y marca la que está en curso 504ms
   ✓ RunsPage > el pedido de la página lleva el filtro, el orden y la página al servidor 1609ms
   ✓ RunsPage > el buscador manda `q` al servidor en vez de filtrar en el cliente 908ms
   ✓ RunsPage > el segmentado manda `estado` al servidor 373ms
   ✓ RunsPage > ordenar cambia `orden` y `direccion`, y el tercer click vuelve al orden por fecha 422ms
 ✓ src/__tests__/PromptSetEditor.test.tsx (5 tests) 963ms
   ✓ PromptSetEditor > exploratory: permite editar y guardar via updatePromptSet 420ms
stderr | src/__tests__/spec44c_gate.test.tsx > spec44c gate: flujo de experimentos por la UI > ExperimentsPage: lista un manifiesto y dispara runExperiment al hacer click en "Ejecutar experimento"
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/ExperimentsEvidence.test.tsx (3 tests) 1271ms
   ✓ pide evidencia, conserva el conteo histórico y ofrece los tres enlaces de consolidaciones 563ms
   ✓ alterna Archivadas y Todas, persiste y vuelve a evidencia sin cruzar cachés 567ms
 ✓ src/__tests__/contrato/nueva-corrida.contrato.test.tsx (3 tests) 2444ms
   ✓ Contrato: nueva corrida > consulta preflight, compone fuente y prompts, lanza y abre el detalle real 1246ms
   ✓ Contrato: nueva corrida > impide lanzar con el formulario completo si el target aún no está listo 447ms
   ✓ Contrato: nueva corrida > muestra los bloqueos del preflight y permite lanzar sólo medios con target listo 748ms
 ✓ src/__tests__/charts/ActivityTimeline.test.tsx (7 tests) 467ms
stderr | src/__tests__/EvidenceView.test.tsx > pide evidencia y alterna los tres estados sin filtrar en el cliente
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/experimentview.test.ts (15 tests) 48ms
 ✓ src/__tests__/spec44c_gate.test.tsx (3 tests) 946ms
   ✓ spec44c gate: flujo de experimentos por la UI > ExperimentsPage: lista un manifiesto y dispara runExperiment al hacer click en "Ejecutar experimento" 655ms
 ✓ src/__tests__/runview.test.ts (17 tests) 19ms
 ✓ src/__tests__/useServiceHealth.test.ts (5 tests) 405ms
stderr | src/__tests__/ComposePage.test.tsx > ComposePage fuente RTSP > al elegir rtsp muestra el campo de dirección y arma config { url }
No routes matched location "/runs/r1"

 ❯ src/__tests__/EvidenceView.test.tsx (3 tests | 1 failed) 1377ms
   ✓ pide evidencia y alterna los tres estados sin filtrar en el cliente 963ms
   × persiste la elección al remontar y muestra un solo distintivo con ambos resultados en title 170ms
     → expected '' to be 'clip_bench/a\nrealtime/b' // Object.is equality
 ✓ src/__tests__/runseries.test.ts (12 tests) 20ms
 ✓ src/__tests__/charts/GroupedBars.test.tsx (8 tests) 317ms
stderr | src/__tests__/ComposePage.test.tsx > ComposePage cámara guardada (oak_d) > lanza con la config de la cámara guardada elegida
No routes matched location "/runs/r1"

 ✓ src/__tests__/ComposePage.test.tsx (18 tests) 8792ms
   ✓ ComposePage prefill > conserva active_ids del manifiesto y no lo pisan los defaults del set 957ms
   ✓ ComposePage prefill de source.type video > conserva el source.type original en la composición (round-trip sin colapso a video_file) 684ms
   ✓ ComposePage prefill survives catalog re-fetch (no clobber) > no reaplica el manifiesto cuando `experiments` cambia de referencia tras un re-fetch 663ms
   ✓ ComposePage nombre opcional de la corrida > manda run.name cuando se completa, null cuando se deja vacío 707ms
   ✓ ComposePage nombre opcional de la corrida > deja run.name en null si el campo queda vacío (usa el id autogenerado) 800ms
   ✓ ComposePage aviso de 409 al lanzar > muestra aviso de prueba de cámara activa ante 409 preview_active 517ms
   ✓ ComposePage aviso de 409 al lanzar > muestra aviso de corrida activa ante 409 con active_run_id 461ms
   ✓ ComposePage panel «Antes de lanzar» > los requisitos se van cumpliendo y el botón se habilita al final 548ms
   ✓ ComposePage panel «Antes de lanzar» > desactivar todas las clases vuelve a bloquear, diciendo qué falta 569ms
   ✓ ComposePage rejilla de fuentes > la fuente elegida queda marcada con aria-pressed 376ms
   ✓ ComposePage fuente RTSP > bloquea el lanzamiento si la dirección RTSP trae credenciales censuradas (***) 549ms
   ✓ ComposePage fuente RTSP > al elegir rtsp muestra el campo de dirección y arma config { url } 436ms
   ✓ ComposePage cámara guardada (oak_d) > lanza con la config de la cámara guardada elegida 495ms
 ✓ src/__tests__/RunKpiStrip.test.tsx (7 tests) 562ms
 ✓ src/__tests__/charts/timeline.test.ts (9 tests) 85ms
stderr | src/__tests__/RunDetailArtifacts.test.tsx > expone el inventario limitado del servicio anterior con descargas verificadas
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/ClipsPage.test.tsx (5 tests) 637ms
 ✓ src/__tests__/ui/Table.test.tsx (6 tests) 423ms
 ✓ src/__tests__/TraceQueries.final.test.tsx (1 test) 120ms
stderr | src/__tests__/Shell.live.test.tsx > seguir la corrida viva cierra el cajón de navegación móvil
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/ui/primitives.test.tsx (10 tests) 403ms
 ✓ src/__tests__/charts/layout.test.ts (9 tests) 17ms
 ✓ src/__tests__/RunDetailArtifacts.test.tsx (3 tests) 1543ms
   ✓ expone el inventario limitado del servicio anterior con descargas verificadas 807ms
   ✓ actualiza los archivos después de evaluar sin recargar el detalle 519ms
stderr | src/__tests__/ComposePage.preflight.test.tsx > ComposePage: bloqueos de preflight > informa los motivos con ready=false sin bloquear DBE y los actualiza por polling
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/Shell.live.test.tsx (2 tests) 1952ms
   ✓ seguir la corrida viva cierra el cajón de navegación móvil 881ms
   ✓ lanzar desde el formulario invalida la lista vacía y muestra la corrida global 1069ms
 ✓ src/__tests__/EvalSection.test.tsx (4 tests) 283ms
 ✓ src/__tests__/ui/Select.test.tsx (5 tests) 538ms
 ✓ src/__tests__/ExperimentQueries.final.test.tsx (1 test) 86ms
stderr | src/__tests__/contrato/detalle-traza-evaluacion.contrato.test.tsx > Contrato: detalle, traza y evaluación > lee detalle y traza, permite inspeccionar cuadros y evaluar contra BENCH
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/contrato/corrida-viva.contrato.test.tsx > Contrato: corrida viva > permite alcanzar la corrida activa desde una ruta distinta del listado
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/useSidebarCounts.test.ts (3 tests) 238ms
 ✓ src/__tests__/ComposePage.preflight.test.tsx (2 tests) 1545ms
   ✓ ComposePage: bloqueos de preflight > informa los motivos con ready=false sin bloquear DBE y los actualiza por polling 983ms
   ✓ ComposePage: bloqueos de preflight > informa los motivos con ready=true sin bloquear DBE y los actualiza por polling 560ms
stderr | src/__tests__/Shell.distribution.test.tsx > Salud del distribuidor en la barra lateral > informa healthy=true y conserva los dos motores
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/nav.test.ts (10 tests) 23ms
 ✓ src/__tests__/contrato/corrida-viva.contrato.test.tsx (2 tests) 975ms
   ✓ Contrato: corrida viva > permite alcanzar la corrida activa desde una ruta distinta del listado 570ms
   ✓ Contrato: corrida viva > consulta mientras corre, permite detener y cesa el polling del detalle al terminar 402ms
 ✓ src/__tests__/Shell.distribution.test.tsx (3 tests) 770ms
   ✓ Salud del distribuidor en la barra lateral > informa healthy=true y conserva los dos motores 337ms
 ✓ src/__tests__/api.endpoints.test.ts (4 tests) 17ms
 ✓ src/__tests__/queryClient.test.ts (4 tests) 9ms
 ✓ src/__tests__/contrato/detalle-traza-evaluacion.contrato.test.tsx (1 test) 1236ms
   ✓ Contrato: detalle, traza y evaluación > lee detalle y traza, permite inspeccionar cuadros y evaluar contra BENCH 1233ms
 ✓ src/__tests__/charts/Meter.test.tsx (5 tests) 333ms
stderr | src/__tests__/LiveRunPill.test.tsx > LiveRunPill > no renderiza nada si no hay corrida viva
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/LiveRunPill.test.tsx (3 tests) 282ms
 ✓ src/__tests__/experiment-api.test.ts (4 tests) 22ms
stderr | src/__tests__/App.test.tsx > App > renderiza el título de la consola
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/App.test.tsx (2 tests) 467ms
   ✓ App > renderiza el título de la consola 345ms
 ✓ src/__tests__/stream.test.ts (3 tests) 10ms
 ✓ src/__tests__/preview.test.ts (2 tests) 11ms
 ✓ src/__tests__/ui/Button.test.tsx (5 tests) 438ms
 ✓ src/__tests__/ui/Banner.test.tsx (3 tests) 375ms
   ✓ Banner > tono warn con boton de cerrar 326ms
 ✓ src/__tests__/ui/Badge.test.tsx (4 tests) 99ms
 ✓ src/__tests__/ui/Select.field.test.tsx (1 test) 290ms
 ✓ src/__tests__/ui/ConditionName.test.tsx (3 tests) 88ms
 ✓ src/__tests__/ui/InlineDeleteConfirm.test.tsx (2 tests) 413ms
   ✓ InlineDeleteConfirm > "Si, borrar" dispara onConfirm; "No" dispara onCancel 344ms
 ✓ src/__tests__/ui/SegmentedControl.test.tsx (2 tests) 347ms
 ✓ src/__tests__/ui/PageHeader.test.tsx (2 tests) 304ms
 ✓ src/__tests__/ui/SearchInput.test.tsx (1 test) 112ms
stderr | src/__tests__/CamerasPage.preview-error.test.tsx > muestra el fallo del sondeo de preview sin rechazar una promesa sin manejar
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/promptview.test.ts (3 tests) 5ms
 ✓ src/__tests__/CamerasPage.preview-error.test.tsx (1 test) 345ms
   ✓ muestra el fallo del sondeo de preview sin rechazar una promesa sin manejar 340ms
 ✓ src/__tests__/ui/icons.test.tsx (1 test) 59ms

⎯⎯⎯⎯⎯⎯⎯ Failed Tests 1 ⎯⎯⎯⎯⎯⎯⎯

 FAIL  src/__tests__/EvidenceView.test.tsx > persiste la elección al remontar y muestra un solo distintivo con ambos resultados en title
AssertionError: expected '' to be 'clip_bench/a\nrealtime/b' // Object.is equality

- Expected
+ Received

- clip_bench/a
- realtime/b

 ❯ src/__tests__/EvidenceView.test.tsx:60:38
     58|   await screen.findByText('clip_bench/a')
     59|   const badge = screen.getByText('clip_bench/a')
     60|   expect(badge.parentElement?.title).toBe('clip_bench/a\nrealtime/b')
       |                                      ^
     61|   expect(screen.queryByText('realtime/b')).toBeNull()
     62|   fireEvent.click(within(screen.getByRole('group', { name: 'Vista de e…

⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯[1/1]⎯

 Test Files  1 failed | 70 passed (71)
      Tests  1 failed | 459 passed (460)
   Start at  04:02:47
   Duration  22.01s (transform 9.71s, setup 0ms, collect 64.34s, tests 69.50s, environment 122.99s, prepare 17.05s)

```

### Frontend: texto del distintivo

```text

> eovrt-webconsole-frontend@0.1.0 test
> vitest run


 RUN  v2.1.9 /home/simonll4/projects/e-ovrt_experimental-setup/webconsole/frontend

 ✓ src/__tests__/api.test.ts (15 tests) 167ms
stderr | src/__tests__/ExperimentDetailPageRiskBanner.test.tsx > ExperimentDetailPage — banner de riesgo activo > muestra el banner con el condition_id cuando patterns no esta vacio y el experimento corre
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ExperimentDetailPage.test.tsx > ExperimentDetailPage > muestra las alertas y avisa que el conjunto no es temporal
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ExperimentsPage.test.tsx > ExperimentsPage > lista manifiestos y dispara un experimento con preflight verde
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/RunsPage.test.tsx > RunsPage > lista corridas y marca la que está en curso
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/TrimDialog.test.tsx (9 tests) 440ms
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

 ✓ src/__tests__/ExperimentDetailPageRiskBanner.test.tsx (7 tests) 600ms
 ✓ src/__tests__/ExperimentsPage.test.tsx (5 tests) 1109ms
   ✓ ExperimentsPage > lista manifiestos y dispara un experimento con preflight verde 505ms
 ✓ src/__tests__/PromptSetsPage.test.tsx (7 tests) 1242ms
   ✓ PromptSetsPage > lista los sets con badge de estado 419ms
 ✓ src/__tests__/ExperimentDetailPage.test.tsx (15 tests) 1258ms
stderr | src/__tests__/ComposePage.test.tsx > ComposePage prefill de source.type video > conserva el source.type original en la composición (round-trip sin colapso a video_file)
No routes matched location "/runs/r1"

 ✓ src/__tests__/DeriveExperimentForm.test.tsx (13 tests) 1412ms
 ✓ src/__tests__/ComparePage.test.tsx (14 tests) 1781ms
 ✓ src/__tests__/RunDetailPage.test.tsx (10 tests) 1550ms
   ✓ RunDetailPage > las pestañas separan traza, resumen, evaluación y archivos 302ms
 ✓ src/__tests__/contrato/experimentos-distribucion.contrato.test.tsx (4 tests) 1878ms
   ✓ Contrato: experimentos y distribución > lista y abre un experimento con outcomes vinculados a cada alerta 760ms
   ✓ Contrato: experimentos y distribución > deriva un manifiesto con overrides y lanza la derivación seleccionada 733ms
stderr | src/__tests__/Shell.test.tsx > Shell > renderiza los tres títulos de grupo
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/RecordPanel.test.tsx (13 tests) 2895ms
   ✓ RecordPanel > mientras graba, consulta el backend periodicamente y muestra elapsed_ms/size_bytes de ahi 1081ms
   ✓ RecordPanel > si el backend informa error, deja de contar y muestra el motivo 1097ms
stderr | src/__tests__/ComposePage.test.tsx > ComposePage nombre opcional de la corrida > manda run.name cuando se completa, null cuando se deja vacío
No routes matched location "/runs/r1"

 ✓ src/__tests__/Shell.test.tsx (17 tests) 2475ms
 ✓ src/__tests__/CamerasPage.test.tsx (14 tests) 2559ms
   ✓ CamerasPage > muestra banner y deshabilita conectar ante 409 run_active 381ms
   ✓ CamerasPage > activa por defecto las clases sin enabled_by_default declarado en el YAML 332ms
stderr | src/__tests__/ComposePage.test.tsx > ComposePage nombre opcional de la corrida > deja run.name en null si el campo queda vacío (usa el id autogenerado)
No routes matched location "/runs/r2"

stderr | src/__tests__/ExperimentsPage.new.test.tsx > ExperimentsPage - crear nuevo experimento (/experiments/new) > abre el formulario con un selector "basado en" precargado con el primer manifiesto
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/labels.test.ts (13 tests) 36ms
stderr | src/__tests__/contrato/nueva-corrida.contrato.test.tsx > Contrato: nueva corrida > consulta preflight, compone fuente y prompts, lanza y abre el detalle real
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/TraceSection.test.tsx (10 tests) 2657ms
   ✓ TraceSection > no vuelca todos los cuadros: la lista se acota y dice el total 1385ms
stderr | src/__tests__/ExperimentsEvidence.test.tsx > pide evidencia, conserva el conteo histórico y ofrece los tres enlaces de consolidaciones
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/ExperimentsPage.new.test.tsx (4 tests) 1587ms
   ✓ ExperimentsPage - crear nuevo experimento (/experiments/new) > abre el formulario con un selector "basado en" precargado con el primer manifiesto 643ms
   ✓ ExperimentsPage - crear nuevo experimento (/experiments/new) > al cambiar la fuente en el selector, vuelve a pedir los defaults y reprecarga los campos (bug central) 389ms
   ✓ ExperimentsPage - crear nuevo experimento (/experiments/new) > en modo nuevo la card dice "Nuevo experimento" y el botón "Crear" (no "Derivar de...") 325ms
 ✓ src/__tests__/LiveViewer.test.tsx (5 tests) 264ms
 ✓ src/__tests__/PromptSetEditor.test.tsx (5 tests) 768ms
 ✓ src/__tests__/traceview.test.ts (12 tests) 42ms
 ✓ src/__tests__/PlatformPage.test.tsx (6 tests) 869ms
   ✓ PlatformPage > lista el fleet y activa una instancia 480ms
 ✓ src/__tests__/PreviewWithBoxes.test.tsx (8 tests) 249ms
stderr | src/__tests__/spec44c_gate.test.tsx > spec44c gate: flujo de experimentos por la UI > ExperimentsPage: lista un manifiesto y dispara runExperiment al hacer click en "Ejecutar experimento"
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/RunsPage.test.tsx (22 tests) 5547ms
   ✓ RunsPage > lista corridas y marca la que está en curso 452ms
   ✓ RunsPage > el pedido de la página lleva el filtro, el orden y la página al servidor 1241ms
   ✓ RunsPage > el buscador manda `q` al servidor en vez de filtrar en el cliente 849ms
   ✓ RunsPage > el segmentado manda `estado` al servidor 345ms
   ✓ RunsPage > el total es el del servidor, no la cantidad de filas de la página 342ms
 ❯ src/__tests__/ExperimentsEvidence.test.tsx (3 tests | 1 failed) 1306ms
   × pide evidencia, conserva el conteo histórico y ofrece los tres enlaces de consolidaciones 611ms
     → Unable to find an element with the text: realtime/t_alert_notification. This could be because the text is broken up by multiple elements. In this case, you can provide a function for your text matcher to make your matcher more flexible.

Ignored nodes: comments, script, style
<body>
  <div>
    <header
      class="eo-pageheader"
    >
      <div>
        <h1>
          Experimentos
        </h1>
        <div
          class="eo-pageheader__meta"
        >
          1 manifiestos
        </div>
      </div>
    </header>
    <div
      aria-label="Vista de evidencia"
      class="eo-toolbar"
      role="group"
    >
      <div
        class="eo-segmented"
      >
        <button
          aria-pressed="true"
          type="button"
        >
          Evidencia
        </button>
        <button
          aria-pressed="false"
          type="button"
        >
          Archivadas
        </button>
        <button
          aria-pressed="false"
          type="button"
        >
          Todas
        </button>
      </div>
      <span
        class="eo-note"
      >
        406

        ejecuciones
         archivadas
      </span>
    </div>
    <section
      class="eo-card"
    >
      <h3
        class="eo-card__title"
      >
        Antes de ejecutar
        <span
          class="eo-card__meta"
        >
          Todo listo
        </span>
      </h3>
      <div
        class="eo-card__body"
      >
        <p
          class="eo-note"
        >
          <span
            style="display: inline-flex; gap: var(--space-2); align-items: center;"
          >
            <span
              class="eo-badge eo-badge--ok"
            >
              Motor de detección
              operativo
            </span>
            <span
              class="eo-badge eo-badge--ok"
            >
              Motor de reglas
              operativo
            </span>
          </span>
           Los dos motores responden y no hay ningún experimento en curso.
        </p>
      </div>
    </section>
    <div
      class="eo-toolbar"
    >
      <div
        class="eo-search"
      >
        <span
          aria-hidden="true"
          class="eo-search__icon"
        >
          <svg
            aria-hidden="true"
            fill="none"
            height="16"
            stroke="currentColor"
            stroke-width="1.6"
            viewBox="0 0 16 16"
            width="16"
          >
            <circle
              cx="7"
              cy="7"
              r="4.6"
            />
            <path
              d="M10.4 10.4L14 14"
            />
          </svg>
        </span>
        <input
          aria-label="Buscar manifiestos por nombre o grupo"
          class="eo-search__input"
          placeholder="Buscar por manifiesto o grupo"
          type="search"
          value=""
        />
      </div>
      <span
        class="eo-toolbar__count eo-mono"
      >
        1
         de
        1
      </span>
    </div>
    <section
      class="eo-card"
    >
      <h3
        class="eo-card__title"
      >
        Manifiestos
        <span
          class="eo-card__meta"
        >
          1
        </span>
      </h3>
      <table
        class="eo-table eo-table--dense"
      >
        <thead>
          <tr>
            <th>
              Manifiesto
            </th>
            <th>
              Grupo
            </th>
            <th>
              Última ejecución
            </th>
            <th>
              Estado
            </th>
            <th
              class="eo-th--numeric"
            >
              Corridas
            </th>
            <th>
              Cuándo
            </th>
            <th
              aria-label="Acciones"
            />
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>
              <span
                class="eo-rowname"
              >
                <b>
                  <span
                    class="eo-mono"
                  >
                    talert_integrated_video
                  </span>
                </b>
                <span
                  class="eo-mono"
                >

                  <span
                    title="realtime/t_alert_notification"
                  >
                    <span
                      class="eo-badge eo-badge--neutral"
                    >
                      realtime/t_alert_…
                    </span>
                  </span>
                </span>
              </span>
            </td>
            <td>
              —
            </td>
            <td
              class="eo-mono"
            >
              <div
                style="max-width: 36ch;"
              >
                <span
                  class="eo-cell--muted"
                >
                  3
                   ejecuciones de evidencia
                </span>
                <div>
                  <a
                    href="/experiments/exp_rep3"
                    style="overflow-wrap: anywhere;"
                  >
                    exp_rep3
                  </a>
                </div>
                <div>
                  <a
                    href="/experiments/exp_rep2"
                    style="overflow-wrap: anywhere;"
                  >
                    exp_rep2
                  </a>
                </div>
                <div>
                  <a
                    href="/experiments/exp_rep1"
                    style="overflow-wrap: anywhere;"
                  >
                    exp_rep1
                  </a>
                </div>
              </div>
            </td>
            <td>
              <span
                class="eo-badge eo-badge--neutral"
              >
                Con evidencia
              </span>
            </td>
            <td
              class="eo-num"
            >
              —
            </td>
            <td
              class="eo-cell--muted"
            >
              —
            </td>
            <td
              class="eo-cell--actions"
            >
              <button
                class="eo-btn eo-btn--secondary"
                type="button"
              >
                Partir de este
              </button>

              <button
                class="eo-btn eo-btn--primary"
                type="button"
              >
                Ejecutar
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </section>
  </div>
</body>
   ✓ alterna Archivadas y Todas, persiste y vuelve a evidencia sin cruzar cachés 535ms
 ✓ src/__tests__/charts/ActivityTimeline.test.tsx (7 tests) 538ms
 ✓ src/__tests__/experimentview.test.ts (15 tests) 17ms
 ✓ src/__tests__/spec44c_gate.test.tsx (3 tests) 703ms
   ✓ spec44c gate: flujo de experimentos por la UI > ExperimentsPage: lista un manifiesto y dispara runExperiment al hacer click en "Ejecutar experimento" 501ms
stderr | src/__tests__/EvidenceView.test.tsx > pide evidencia y alterna los tres estados sin filtrar en el cliente
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/contrato/nueva-corrida.contrato.test.tsx (3 tests) 2465ms
   ✓ Contrato: nueva corrida > consulta preflight, compone fuente y prompts, lanza y abre el detalle real 1219ms
   ✓ Contrato: nueva corrida > impide lanzar con el formulario completo si el target aún no está listo 593ms
   ✓ Contrato: nueva corrida > muestra los bloqueos del preflight y permite lanzar sólo medios con target listo 635ms
 ✓ src/__tests__/runview.test.ts (17 tests) 24ms
stderr | src/__tests__/ComposePage.test.tsx > ComposePage fuente RTSP > al elegir rtsp muestra el campo de dirección y arma config { url }
No routes matched location "/runs/r1"

 ✓ src/__tests__/EvidenceView.test.tsx (3 tests) 1483ms
   ✓ pide evidencia y alterna los tres estados sin filtrar en el cliente 880ms
   ✓ persiste la elección al remontar y muestra un solo distintivo con ambos resultados en title 424ms
 ✓ src/__tests__/runseries.test.ts (12 tests) 19ms
 ✓ src/__tests__/useServiceHealth.test.ts (5 tests) 386ms
stderr | src/__tests__/ComposePage.test.tsx > ComposePage cámara guardada (oak_d) > lanza con la config de la cámara guardada elegida
No routes matched location "/runs/r1"

 ✓ src/__tests__/ComposePage.test.tsx (18 tests) 7937ms
   ✓ ComposePage prefill > conserva active_ids del manifiesto y no lo pisan los defaults del set 858ms
   ✓ ComposePage prefill de source.type video > conserva el source.type original en la composición (round-trip sin colapso a video_file) 452ms
   ✓ ComposePage prefill survives catalog re-fetch (no clobber) > no reaplica el manifiesto cuando `experiments` cambia de referencia tras un re-fetch 589ms
   ✓ ComposePage nombre opcional de la corrida > manda run.name cuando se completa, null cuando se deja vacío 549ms
   ✓ ComposePage nombre opcional de la corrida > deja run.name en null si el campo queda vacío (usa el id autogenerado) 583ms
   ✓ ComposePage aviso de 409 al lanzar > muestra aviso de prueba de cámara activa ante 409 preview_active 480ms
   ✓ ComposePage aviso de 409 al lanzar > muestra aviso de corrida activa ante 409 con active_run_id 539ms
   ✓ ComposePage panel «Antes de lanzar» > los requisitos se van cumpliendo y el botón se habilita al final 542ms
   ✓ ComposePage panel «Antes de lanzar» > desactivar todas las clases vuelve a bloquear, diciendo qué falta 510ms
   ✓ ComposePage rejilla de fuentes > la fuente elegida queda marcada con aria-pressed 400ms
   ✓ ComposePage fuente RTSP > bloquea el lanzamiento si la dirección RTSP trae credenciales censuradas (***) 478ms
   ✓ ComposePage fuente RTSP > al elegir rtsp muestra el campo de dirección y arma config { url } 439ms
   ✓ ComposePage cámara guardada (oak_d) > lanza con la config de la cámara guardada elegida 499ms
 ✓ src/__tests__/charts/GroupedBars.test.tsx (8 tests) 279ms
 ✓ src/__tests__/charts/timeline.test.ts (9 tests) 55ms
stderr | src/__tests__/RunDetailArtifacts.test.tsx > expone el inventario limitado del servicio anterior con descargas verificadas
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/RunKpiStrip.test.tsx (7 tests) 483ms
 ✓ src/__tests__/TraceQueries.final.test.tsx (1 test) 108ms
 ✓ src/__tests__/ui/Table.test.tsx (6 tests) 297ms
 ✓ src/__tests__/ClipsPage.test.tsx (5 tests) 620ms
   ✓ ClipsPage > lista masters y clips 349ms
stderr | src/__tests__/Shell.live.test.tsx > seguir la corrida viva cierra el cajón de navegación móvil
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ComposePage.preflight.test.tsx > ComposePage: bloqueos de preflight > informa los motivos con ready=false sin bloquear DBE y los actualiza por polling
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/RunDetailArtifacts.test.tsx (3 tests) 1356ms
   ✓ expone el inventario limitado del servicio anterior con descargas verificadas 672ms
   ✓ actualiza los archivos después de evaluar sin recargar el detalle 480ms
 ✓ src/__tests__/ui/primitives.test.tsx (10 tests) 361ms
 ✓ src/__tests__/charts/layout.test.ts (9 tests) 31ms
 ✓ src/__tests__/Shell.live.test.tsx (2 tests) 1920ms
   ✓ seguir la corrida viva cierra el cajón de navegación móvil 744ms
   ✓ lanzar desde el formulario invalida la lista vacía y muestra la corrida global 1174ms
 ✓ src/__tests__/ComposePage.preflight.test.tsx (2 tests) 1704ms
   ✓ ComposePage: bloqueos de preflight > informa los motivos con ready=false sin bloquear DBE y los actualiza por polling 1070ms
   ✓ ComposePage: bloqueos de preflight > informa los motivos con ready=true sin bloquear DBE y los actualiza por polling 632ms
 ✓ src/__tests__/EvalSection.test.tsx (4 tests) 353ms
 ✓ src/__tests__/ui/Select.test.tsx (5 tests) 568ms
 ✓ src/__tests__/useSidebarCounts.test.ts (3 tests) 264ms
 ✓ src/__tests__/nav.test.ts (10 tests) 25ms
 ✓ src/__tests__/ExperimentQueries.final.test.tsx (1 test) 104ms
stderr | src/__tests__/contrato/corrida-viva.contrato.test.tsx > Contrato: corrida viva > permite alcanzar la corrida activa desde una ruta distinta del listado
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/Shell.distribution.test.tsx > Salud del distribuidor en la barra lateral > informa healthy=true y conserva los dos motores
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/contrato/detalle-traza-evaluacion.contrato.test.tsx > Contrato: detalle, traza y evaluación > lee detalle y traza, permite inspeccionar cuadros y evaluar contra BENCH
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/contrato/corrida-viva.contrato.test.tsx (2 tests) 1316ms
   ✓ Contrato: corrida viva > permite alcanzar la corrida activa desde una ruta distinta del listado 757ms
   ✓ Contrato: corrida viva > consulta mientras corre, permite detener y cesa el polling del detalle al terminar 555ms
 ✓ src/__tests__/queryClient.test.ts (4 tests) 14ms
 ✓ src/__tests__/Shell.distribution.test.tsx (3 tests) 942ms
   ✓ Salud del distribuidor en la barra lateral > informa healthy=true y conserva los dos motores 328ms
   ✓ Salud del distribuidor en la barra lateral > informa healthy=false y conserva los dos motores 345ms
 ✓ src/__tests__/charts/Meter.test.tsx (5 tests) 326ms
 ✓ src/__tests__/api.endpoints.test.ts (4 tests) 25ms
stderr | src/__tests__/LiveRunPill.test.tsx > LiveRunPill > no renderiza nada si no hay corrida viva
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/contrato/detalle-traza-evaluacion.contrato.test.tsx (1 test) 1451ms
   ✓ Contrato: detalle, traza y evaluación > lee detalle y traza, permite inspeccionar cuadros y evaluar contra BENCH 1445ms
 ✓ src/__tests__/LiveRunPill.test.tsx (3 tests) 410ms
 ✓ src/__tests__/experiment-api.test.ts (4 tests) 39ms
stderr | src/__tests__/App.test.tsx > App > renderiza el título de la consola
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/App.test.tsx (2 tests) 524ms
   ✓ App > renderiza el título de la consola 354ms
 ✓ src/__tests__/stream.test.ts (3 tests) 29ms
 ✓ src/__tests__/preview.test.ts (2 tests) 13ms
 ✓ src/__tests__/ui/Badge.test.tsx (4 tests) 118ms
 ✓ src/__tests__/ui/Button.test.tsx (5 tests) 350ms
 ✓ src/__tests__/ui/Banner.test.tsx (3 tests) 270ms
 ✓ src/__tests__/ui/Select.field.test.tsx (1 test) 274ms
 ✓ src/__tests__/ui/SegmentedControl.test.tsx (2 tests) 217ms
 ✓ src/__tests__/ui/InlineDeleteConfirm.test.tsx (2 tests) 185ms
 ✓ src/__tests__/ui/PageHeader.test.tsx (2 tests) 212ms
 ✓ src/__tests__/ui/ConditionName.test.tsx (3 tests) 64ms
 ✓ src/__tests__/promptview.test.ts (3 tests) 3ms
stderr | src/__tests__/CamerasPage.preview-error.test.tsx > muestra el fallo del sondeo de preview sin rechazar una promesa sin manejar
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/ui/icons.test.tsx (1 test) 30ms
 ✓ src/__tests__/ui/SearchInput.test.tsx (1 test) 45ms
 ✓ src/__tests__/CamerasPage.preview-error.test.tsx (1 test) 179ms

⎯⎯⎯⎯⎯⎯⎯ Failed Tests 1 ⎯⎯⎯⎯⎯⎯⎯

 FAIL  src/__tests__/ExperimentsEvidence.test.tsx > pide evidencia, conserva el conteo histórico y ofrece los tres enlaces de consolidaciones
TestingLibraryElementError: Unable to find an element with the text: realtime/t_alert_notification. This could be because the text is broken up by multiple elements. In this case, you can provide a function for your text matcher to make your matcher more flexible.

Ignored nodes: comments, script, style
<body>
  <div>
    <header
      class="eo-pageheader"
    >
      <div>
        <h1>
          Experimentos
        </h1>
        <div
          class="eo-pageheader__meta"
        >
          1 manifiestos
        </div>
      </div>
    </header>
    <div
      aria-label="Vista de evidencia"
      class="eo-toolbar"
      role="group"
    >
      <div
        class="eo-segmented"
      >
        <button
          aria-pressed="true"
          type="button"
        >
          Evidencia
        </button>
        <button
          aria-pressed="false"
          type="button"
        >
          Archivadas
        </button>
        <button
          aria-pressed="false"
          type="button"
        >
          Todas
        </button>
      </div>
      <span
        class="eo-note"
      >
        406

        ejecuciones
         archivadas
      </span>
    </div>
    <section
      class="eo-card"
    >
      <h3
        class="eo-card__title"
      >
        Antes de ejecutar
        <span
          class="eo-card__meta"
        >
          Todo listo
        </span>
      </h3>
      <div
        class="eo-card__body"
      >
        <p
          class="eo-note"
        >
          <span
            style="display: inline-flex; gap: var(--space-2); align-items: center;"
          >
            <span
              class="eo-badge eo-badge--ok"
            >
              Motor de detección
              operativo
            </span>
            <span
              class="eo-badge eo-badge--ok"
            >
              Motor de reglas
              operativo
            </span>
          </span>
           Los dos motores responden y no hay ningún experimento en curso.
        </p>
      </div>
    </section>
    <div
      class="eo-toolbar"
    >
      <div
        class="eo-search"
      >
        <span
          aria-hidden="true"
          class="eo-search__icon"
        >
          <svg
            aria-hidden="true"
            fill="none"
            height="16"
            stroke="currentColor"
            stroke-width="1.6"
            viewBox="0 0 16 16"
            width="16"
          >
            <circle
              cx="7"
              cy="7"
              r="4.6"
            />
            <path
              d="M10.4 10.4L14 14"
            />
          </svg>
        </span>
        <input
          aria-label="Buscar manifiestos por nombre o grupo"
          class="eo-search__input"
          placeholder="Buscar por manifiesto o grupo"
          type="search"
          value=""
        />
      </div>
      <span
        class="eo-toolbar__count eo-mono"
      >
        1
         de
        1
      </span>
    </div>
    <section
      class="eo-card"
    >
      <h3
        class="eo-card__title"
      >
        Manifiestos
        <span
          class="eo-card__meta"
        >
          1
        </span>
      </h3>
      <table
        class="eo-table eo-table--dense"
      >
        <thead>
          <tr>
            <th>
              Manifiesto
            </th>
            <th>
              Grupo
            </th>
            <th>
              Última ejecución
            </th>
            <th>
              Estado
            </th>
            <th
              class="eo-th--numeric"
            >
              Corridas
            </th>
            <th>
              Cuándo
            </th>
            <th
              aria-label="Acciones"
            />
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>
              <span
                class="eo-rowname"
              >
                <b>
                  <span
                    class="eo-mono"
                  >
                    talert_integrated_video
                  </span>
                </b>
                <span
                  class="eo-mono"
                >

                  <span
                    title="realtime/t_alert_notification"
                  >
                    <span
                      class="eo-badge eo-badge--neutral"
                    >
                      realtime/t_alert_…
                    </span>
                  </span>
                </span>
              </span>
            </td>
            <td>
              —
            </td>
            <td
              class="eo-mono"
            >
              <div
                style="max-width: 36ch;"
              >
                <span
                  class="eo-cell--muted"
                >
                  3
                   ejecuciones de evidencia
                </span>
                <div>
                  <a
                    href="/experiments/exp_rep3"
                    style="overflow-wrap: anywhere;"
                  >
                    exp_rep3
                  </a>
                </div>
                <div>
                  <a
                    href="/experiments/exp_rep2"
                    style="overflow-wrap: anywhere;"
                  >
                    exp_rep2
                  </a>
                </div>
                <div>
                  <a
                    href="/experiments/exp_rep1"
                    style="overflow-wrap: anywhere;"
                  >
                    exp_rep1
                  </a>
                </div>
              </div>
            </td>
            <td>
              <span
                class="eo-badge eo-badge--neutral"
              >
                Con evidencia
              </span>
            </td>
            <td
              class="eo-num"
            >
              —
            </td>
            <td
              class="eo-cell--muted"
            >
              —
            </td>
            <td
              class="eo-cell--actions"
            >
              <button
                class="eo-btn eo-btn--secondary"
                type="button"
              >
                Partir de este
              </button>

              <button
                class="eo-btn eo-btn--primary"
                type="button"
              >
                Ejecutar
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </section>
  </div>
</body>
 ❯ Object.getElementError node_modules/@testing-library/dom/dist/config.js:37:19
 ❯ node_modules/@testing-library/dom/dist/query-helpers.js:76:38
 ❯ node_modules/@testing-library/dom/dist/query-helpers.js:109:15
 ❯ src/__tests__/ExperimentsEvidence.test.tsx:50:17
     48|   }
     49|   expect(urls.some(url => url.searchParams.get('vista') === 'evidencia…
     50|   expect(screen.getAllByText('realtime/t_alert_notification')).toHaveL…
       |                 ^
     51| })
     52|

⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯[1/1]⎯

 Test Files  1 failed | 70 passed (71)
      Tests  1 failed | 459 passed (460)
   Start at  04:03:59
   Duration  19.18s (transform 6.72s, setup 0ms, collect 53.08s, tests 61.83s, environment 105.81s, prepare 16.97s)

```
