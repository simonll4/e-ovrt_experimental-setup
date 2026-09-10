# Tramo 7 — cierre: vista de evidencia

Fecha: 2026-09-10. Rama: `feature/webconsole-adopcion-front-design`.
Base: `ee5a834` (tramo 6 aceptado). **Tramo 7 cerrado.** El usuario aceptó
las dos condiciones de cierre y autorizó el commit. La corrección final da a
Evidencia un ícono propio: documento con marca de comprobación, SVG 16 × 16,
trazo 1.4 y `currentColor`, coherente con los demás destinos.

## Resultado implementado

La sección `/evidencia` tiene índice, resultado con corridas paginadas por rol y
summary congelado. `/` sigue siendo Corridas: no se cambió el aterrizaje.
Evidencia es el primer destino de Trabajo; los otros ocho conservan su orden.

La API y la pantalla agrupan **por el prefijo de `result_id`**. El contraste
independiente de los CSV da **4 índices, 35 resultados, 1.760 filas y 1.436
corridas únicas**. No aparece un grupo `shared`; las relaciones compartidas
permanecen en todos sus resultados.

- `/api/evidencia`: grupos y resultados, con conteos calculados del registro.
- `/api/evidencia/resultado?id=...&page=1&page_size=25`: relaciones ordenadas por
  rol y paginadas; el id con barra viaja por query. Máximo 200 filas por página.
- `/api/evidencia/run?plane=...&run_id=...`: summary preservado y procedencia.
  Ninguna ruta de esta sección llama a los servicios.
- Los CSV siguen siendo la fuente de selección y conteos. `resolved-runs.json`
  agrega motivos; del YAML canónico sólo se toman documentos de procedencia.
  Los metadatos se cargan al crear la app. Las lecturas de artefactos quedan
  contenidas dentro del archivo, también ante symlinks.
- Se leyeron **las 1.436 corridas**: 1.402 conservan summary (1.392 en archivo
  individual y 10 dentro de sustitutos); 34 conservan sólo evaluación derivada.
  No se inventan summaries para esas 34. Todos los 44 `archived_only` muestran
  el motivo registrado y nunca ofrecen un enlace vivo.
- `titulos.yaml` tiene las **35 entradas y los 35 `titulo:` vacíos**. Las
  etiquetas se derivan mecánicamente; el usuario escribe los títulos finales.
  La vista admite títulos presentes y ausentes. No se redactó ninguno.
- En las rutas de Evidencia, `Shell` no monta la píldora viva ni la insignia del
  target y desactiva las queries globales. Conserva todos los destinos. Dice
  «Archivo local · servicios no consultados»; no finge conocer la salud actual.

## Excepción de test autorizada y congelada

Se editó únicamente el caso de `nav.test.ts` autorizado por el usuario: nombre
«9 destinos» y `/evidencia` primero en el array esperado. La exclusión de
`/compose` está intacta, igual que los otros casos originales. Se agregó el
caso nuevo de migas para `/evidencia`, resuelto por `NAV_GROUPS`, sin entrada en
`STANDALONE`. Se tomó un hash después de esos cambios y se verificó al terminar.
Los demás tests preexistentes y el contrato permanecen idénticos.

## Decisiones aceptadas por el usuario

1. **Control sin enlace vivo.** De las 1.436 corridas, 996 son de control;
   esta consola no tiene una vista viva de control. Se indica que el original
   existe cuando corresponde (16 directorios locales), sin ofrecer un enlace
   roto a `/runs/:id`, y se conserva el summary curado. Tratamiento aceptado.
2. **Independencia de servicios y GPU.** El usuario verificó que el router de
   evidencia no llama a `state.http`, `control_http` ni al backend de los planos:
   E-2 queda probado por código. Aceptó además la captura con los tres servicios
   detenidos y el BFF sin dispositivos GPU accesibles en WSL2 (`bwrap`, sin
   `/dev/dxg` ni NVIDIA, `CUDA_VISIBLE_DEVICES=-1`). No se afirma haber apagado
   físicamente la GPU del host Windows; esa condición no queda pendiente.

## Capturas y comprobación visual

Viewport 1440 × 1000. Archivos fuera de Git, en
`/tmp/eovrt-tramo7/captures/`:

- `indice-servicios-apagados.png`: cuatro índices y 35 enlaces.
- `resultado.png`: resultado `realtime/t_alert_notification`, seis corridas.
- `corrida-media.png` y `corrida-control.png`: summaries congelados.
- `paginacion-544.png`: página 2 de 22 de `realtime/decimado_empirico`.
- `archived-only.png`: summary histórico preservado dentro del sustituto,
  motivo registrado y ausencia del enlace vivo.
- `estado-vacio.png`: ausencia real del directorio, con explicación del backup.
- `indice-icono-final.png` e `icono-final-colapsado.png`: ícono propio de Evidencia,
  comprobado frente al de Catálogos en ambas variantes de la barra lateral.

Se renombró temporalmente `results/evidence-runs/` para la captura vacía y se
restauró en un `finally`. Los servicios también fueron restituidos después de
las capturas. No se borró ni modificó ningún artefacto. El navegador sólo pidió
`/api/evidencia` y sus dos endpoints de detalle, sin errores JavaScript.

La consola principal quedó actualizada en `http://127.0.0.1:8090/#/evidencia`.
El BFF aislado de revisión escucha en `127.0.0.1:8092`.

## Límites conservados

- En la barra colapsada, el texto del pie «Archivo local · servicios no
  consultados» se parte y excede el ancho lateral. Queda anotado para una
  corrección posterior; el ajuste final autorizado sólo cambia el ícono.
- Los desbordes horizontales del tramo 6 quedan como tarea posterior; no se
  modificaron `RunsPage`, `ExperimentsPage` ni el CSS global. El CSS nuevo se
  limita a `.eo-evidence`.
- No se trajeron archivos de 3500923: este tramo es la sección nueva autorizada.
  Los cambios en hooks globales y `Shell` son necesarios para que las rutas de
  Evidencia no consulten servicios indirectamente.
- Los títulos no se completaron. La prueba física de apagado de GPU tampoco se
  presenta como realizada; se declara exactamente el aislamiento usado.
- No hubo merge, push ni cambios a main. Los cambios ajenos en
  `defensa/README.md` y `results/bench_imagenes/index.md` se preservaron.
- El primer intento de captura vacía usó un selector exacto que no contemplaba
  el texto de ayuda dentro de `EmptyState`; se corrigió el script de captura,
  sin cambiar la UI ni sus tests. Una comprobación TCP sin timeout se interrumpió
  en WSL; el `finally` restituyó los servicios y se repitió con timeout acotado.

## Los 35 resultados y sus conteos

# Tramo 7 — contraste independiente del registro y la API

Los conteos siguientes se calcularon leyendo los cuatro CSV directamente y se compararon con `/api/evidencia`. Se agrupa por prefijo de `result_id`.

| Índice | Resultados | Filas |
| --- | ---: | ---: |
| bench_imagenes | 5 | 41 |
| bench_nivel_a | 4 | 84 |
| clip_bench | 14 | 928 |
| realtime | 12 | 707 |

| Resultado | Corridas únicas dentro del resultado | Filas |
| --- | ---: | ---: |
| `bench_imagenes/clase_nueva` | 5 | 5 |
| `bench_imagenes/confirmacion_b5` | 6 | 6 |
| `bench_imagenes/gdino560` | 2 | 4 |
| `bench_imagenes/modelos_crudos` | 6 | 6 |
| `bench_imagenes/seleccion_s1` | 20 | 20 |
| `bench_nivel_a/d1_gdinotiny560_edir_vs_eind` | 18 | 18 |
| `bench_nivel_a/edir_vs_eind` | 18 | 18 |
| `bench_nivel_a/na1_gdinotiny560_v2short_video` | 17 | 30 |
| `bench_nivel_a/replica_base560` | 18 | 18 |
| `clip_bench/b1_gdinobase560_barehead_scene` | 68 | 68 |
| `clip_bench/d1_gdinotiny560_edirpair_scene` | 68 | 68 |
| `clip_bench/g1_gdinotiny560_v2short_subject` | 68 | 68 |
| `clip_bench/h1_gdinotiny560_hybor_scene` | 102 | 102 |
| `clip_bench/i1_gdinotiny560_v2short_scene_internet` | 26 | 39 |
| `clip_bench/i2_gdinotiny560_v2short_subject_internet` | 26 | 39 |
| `clip_bench/r1_gdinotiny560_v2short_scene_s7` | 68 | 68 |
| `clip_bench/r2_gdinotiny560_v2short_subject_s7` | 68 | 68 |
| `clip_bench/r3_gdinotiny560_v2short_scene_s15` | 68 | 68 |
| `clip_bench/r4_gdinotiny560_v2short_subject_s15` | 68 | 68 |
| `clip_bench/r5_gdinotiny560_v2short_scene_s26` | 68 | 68 |
| `clip_bench/r6_gdinotiny560_v2short_subject_s26` | 68 | 68 |
| `clip_bench/t1_gdinotiny560_v2short_scene` | 68 | 68 |
| `clip_bench/t2_gdinobase560_v2short_scene` | 68 | 68 |
| `realtime/bus_live_paridad` | 3 | 3 |
| `realtime/claqueta_reloj_externo` | 8 | 8 |
| `realtime/decimado_empirico` | 544 | 544 |
| `realtime/descarte_irregular` | 76 | 76 |
| `realtime/frt5_roundtrip_pil` | 23 | 23 |
| `realtime/g2a_single_host` | 1 | 1 |
| `realtime/gdino560` | 2 | 4 |
| `realtime/l0` | 2 | 2 |
| `realtime/matriz_modelo_fuente` | 24 | 24 |
| `realtime/regresion_g1_live` | 4 | 4 |
| `realtime/rodaje_seis_corridas` | 12 | 12 |
| `realtime/t_alert_notification` | 6 | 6 |

Total: 35 resultados; 1760 filas; 1436 corridas únicas globales.
Los conjuntos compartidos se conservan en cada resultado; `shared` no aparece como índice.
`titulos.yaml`: 35 entradas exactas; 35 títulos vacíos.

## Archivos del tramo

- `.gitignore`
- `docs/rediseno-consola/tramo-7-conteos.md`
- `docs/rediseno-consola/tramo-7-reporte.md`
- `docs/rediseno-consola/tramo-7.md`
- `results/evidence-runs/titulos.yaml`
- `webconsole/README.md`
- `webconsole/backend/src/eovrt_webconsole/app.py`
- `webconsole/backend/src/eovrt_webconsole/evidence.py`
- `webconsole/backend/src/eovrt_webconsole/evidence_archive.py`
- `webconsole/backend/src/eovrt_webconsole/routers/evidencia.py`
- `webconsole/backend/tests/test_evidence_archive.py`
- `webconsole/frontend/src/App.tsx`
- `webconsole/frontend/src/__tests__/EvidencePage.test.tsx`
- `webconsole/frontend/src/__tests__/nav.test.ts`
- `webconsole/frontend/src/api/endpoints.ts`
- `webconsole/frontend/src/api/queries/platform.ts`
- `webconsole/frontend/src/api/queries/runs.ts`
- `webconsole/frontend/src/api/queries/sidebar.ts`
- `webconsole/frontend/src/components/Breadcrumbs.tsx`
- `webconsole/frontend/src/components/Shell.tsx`
- `webconsole/frontend/src/components/ui/icons.tsx`
- `webconsole/frontend/src/nav.ts`
- `webconsole/frontend/src/pages/EvidencePage.css`
- `webconsole/frontend/src/pages/EvidencePage.tsx`
- `webconsole/frontend/src/types.ts`

## Salidas reales completas

Se retiran únicamente códigos ANSI y espacios al final de línea.

### Backend

```text
$ cd webconsole/backend && ./.venv/bin/python -m pytest -q
........................................................................ [  8%]
........................................................................ [ 17%]
........................................................................ [ 26%]
........................................................................ [ 35%]
........................................................................ [ 44%]
........................................................................ [ 53%]
........................................................................ [ 61%]
........................................................................ [ 70%]
........................................................................ [ 79%]
........................................................................ [ 88%]
........................................................................ [ 97%]
.....................                                                    [100%]
813 passed in 98.63s (0:01:38)
```

### Frontend

```text
$ cd webconsole/frontend && npm test

> eovrt-webconsole-frontend@0.1.0 test
> vitest run


 RUN  v2.1.9 /home/simonll4/projects/e-ovrt_experimental-setup/webconsole/frontend

 ✓ src/__tests__/api.test.ts (15 tests) 524ms
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

stderr | src/__tests__/contrato/experimentos-distribucion.contrato.test.tsx > Contrato: experimentos y distribución > lista y abre un experimento con outcomes vinculados a cada alerta
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/TrimDialog.test.tsx (9 tests) 1033ms
stderr | src/__tests__/CamerasPage.test.tsx > CamerasPage > lista los presets de cámara
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ComposePage.test.tsx > ComposePage prefill > conserva active_ids del manifiesto y no lo pisan los defaults del set
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/RunDetailPage.test.tsx > RunDetailPage > muestra el estado de la corrida con el glosario, no con el código crudo
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/ExperimentDetailPageRiskBanner.test.tsx (7 tests) 1163ms
   ✓ ExperimentDetailPage — banner de riesgo activo > muestra el banner con el condition_id cuando patterns no esta vacio y el experimento corre 422ms
   ✓ ExperimentDetailPage — banner de riesgo activo > el banner desaparece cuando el patron ya no esta en la respuesta (el motor lo resolvio) 315ms
 ✓ src/__tests__/ExperimentsPage.test.tsx (5 tests) 2082ms
   ✓ ExperimentsPage > lista manifiestos y dispara un experimento con preflight verde 1059ms
   ✓ ExperimentsPage > derivar recarga los manifiestos, y cada fila lanza el suyo 379ms
 ✓ src/__tests__/ExperimentDetailPage.test.tsx (15 tests) 2231ms
   ✓ ExperimentDetailPage > muestra las alertas y avisa que el conjunto no es temporal 392ms
   ✓ ExperimentDetailPage > nombra la condición de la alerta además del código 350ms
 ✓ src/__tests__/PromptSetsPage.test.tsx (7 tests) 2367ms
   ✓ PromptSetsPage > lista los sets con badge de estado 933ms
   ✓ PromptSetsPage > un conjunto congelado no ofrece editar, sino ver 448ms
   ✓ PromptSetsPage > abre el editor en la columna derecha, sin perder la lista 349ms
 ✓ src/__tests__/DeriveExperimentForm.test.tsx (13 tests) 2553ms
   ✓ DeriveExperimentForm > precarga los valores del manifiesto fuente 673ms
   ✓ DeriveExperimentForm > mode "derive" (default): título "Derivar de <source>" y botón "Derivar" 406ms
stderr | src/__tests__/ComposePage.test.tsx > ComposePage prefill de source.type video > conserva el source.type original en la composición (round-trip sin colapso a video_file)
No routes matched location "/runs/r1"

 ✓ src/__tests__/ComparePage.test.tsx (14 tests) 3203ms
   ✓ ComparePage > lista las corridas por nombre, no por identificador crudo 944ms
   ✓ ComparePage > compara al elegir dos y nombra las métricas en español 561ms
   ✓ ComparePage > resalta el mejor valor de cada fila 483ms
 ✓ src/__tests__/contrato/experimentos-distribucion.contrato.test.tsx (4 tests) 3047ms
   ✓ Contrato: experimentos y distribución > lista y abre un experimento con outcomes vinculados a cada alerta 1686ms
   ✓ Contrato: experimentos y distribución > deriva un manifiesto con overrides y lanza la derivación seleccionada 968ms
 ✓ src/__tests__/RunDetailPage.test.tsx (10 tests) 2637ms
   ✓ RunDetailPage > muestra el estado de la corrida con el glosario, no con el código crudo 405ms
   ✓ RunDetailPage > las pestañas separan traza, resumen, evaluación y archivos 391ms
   ✓ RunDetailPage > confirmar borra la corrida y vuelve al listado 313ms
   ✓ RunDetailPage > borrado parcial muestra el detalle de los planos que fallaron y persiste (no navega) 466ms
 ✓ src/__tests__/RecordPanel.test.tsx (13 tests) 4161ms
   ✓ RecordPanel > deshabilita grabar y explica por que cuando no hay camara elegida 315ms
   ✓ RecordPanel > arranca la grabacion con la camara, escenario y variante elegidos 388ms
   ✓ RecordPanel > mientras graba, consulta el backend periodicamente y muestra elapsed_ms/size_bytes de ahi 1157ms
   ✓ RecordPanel > si el backend informa error, deja de contar y muestra el motivo 1196ms
stderr | src/__tests__/Shell.test.tsx > Shell > renderiza los tres títulos de grupo
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/Shell.test.tsx (17 tests) 3929ms
   ✓ Shell > renderiza los tres títulos de grupo 697ms
   ✓ Shell > acorta la etiqueta que no entra, sin perder el nombre completo 419ms
stderr | src/__tests__/ComposePage.test.tsx > ComposePage nombre opcional de la corrida > manda run.name cuando se completa, null cuando se deja vacío
No routes matched location "/runs/r1"

 ✓ src/__tests__/CamerasPage.test.tsx (14 tests) 4051ms
   ✓ CamerasPage > lista los presets de cámara 655ms
   ✓ CamerasPage > muestra banner y deshabilita conectar ante 409 run_active 642ms
   ✓ CamerasPage > muestra banner ante 409 preview_active (sesión de preview ya activa) 376ms
   ✓ CamerasPage > activa por defecto las clases sin enabled_by_default declarado en el YAML 494ms
   ✓ CamerasPage > deshabilita Probar en modo detect sin conjunto de prompts cargado 314ms
stderr | src/__tests__/ComposePage.test.tsx > ComposePage nombre opcional de la corrida > deja run.name en null si el campo queda vacío (usa el id autogenerado)
No routes matched location "/runs/r2"

stderr | src/__tests__/EvidencePage.test.tsx > navega los tres niveles por query y no consulta servicios desde el Shell
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/labels.test.ts (13 tests) 23ms
stderr | src/__tests__/ExperimentsPage.new.test.tsx > ExperimentsPage - crear nuevo experimento (/experiments/new) > abre el formulario con un selector "basado en" precargado con el primer manifiesto
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ExperimentsEvidence.test.tsx > pide evidencia, conserva el conteo histórico y ofrece los tres enlaces de consolidaciones
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/LiveViewer.test.tsx (5 tests) 342ms
 ✓ src/__tests__/traceview.test.ts (12 tests) 80ms
stderr | src/__tests__/contrato/nueva-corrida.contrato.test.tsx > Contrato: nueva corrida > consulta preflight, compone fuente y prompts, lanza y abre el detalle real
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/PlatformPage.test.tsx (6 tests) 1249ms
   ✓ PlatformPage > lista el fleet y activa una instancia 592ms
 ✓ src/__tests__/PreviewWithBoxes.test.tsx (8 tests) 336ms
 ✓ src/__tests__/EvidencePage.test.tsx (6 tests) 2496ms
   ✓ navega los tres niveles por query y no consulta servicios desde el Shell 986ms
   ✓ pagina corridas preservando el result_id con barra y el rol 724ms
   ✓ usa el título del usuario cuando está y la etiqueta derivada cuando falta 301ms
 ✓ src/__tests__/PromptSetEditor.test.tsx (5 tests) 1344ms
   ✓ PromptSetEditor > exploratory: permite editar y guardar via updatePromptSet 718ms
 ✓ src/__tests__/ExperimentsEvidence.test.tsx (3 tests) 1592ms
   ✓ pide evidencia, conserva el conteo histórico y ofrece los tres enlaces de consolidaciones 576ms
   ✓ alterna Archivadas y Todas, persiste y vuelve a evidencia sin cruzar cachés 819ms
stderr | src/__tests__/spec44c_gate.test.tsx > spec44c gate: flujo de experimentos por la UI > ExperimentsPage: lista un manifiesto y dispara runExperiment al hacer click en "Ejecutar experimento"
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/RunsPage.test.tsx (22 tests) 7479ms
   ✓ RunsPage > lista corridas y marca la que está en curso 1124ms
   ✓ RunsPage > el pedido de la página lleva el filtro, el orden y la página al servidor 1543ms
   ✓ RunsPage > el buscador manda `q` al servidor en vez de filtrar en el cliente 889ms
   ✓ RunsPage > el segmentado manda `estado` al servidor 319ms
   ✓ RunsPage > borrar no navega al detalle de la corrida 449ms
   ✓ RunsPage > borrado parcial muestra los planos que fallaron, y persiste tras el refresh 302ms
 ✓ src/__tests__/ExperimentsPage.new.test.tsx (4 tests) 2315ms
   ✓ ExperimentsPage - crear nuevo experimento (/experiments/new) > abre el formulario con un selector "basado en" precargado con el primer manifiesto 1008ms
   ✓ ExperimentsPage - crear nuevo experimento (/experiments/new) > al cambiar la fuente en el selector, vuelve a pedir los defaults y reprecarga los campos (bug central) 576ms
   ✓ ExperimentsPage - crear nuevo experimento (/experiments/new) > en modo nuevo la card dice "Nuevo experimento" y el botón "Crear" (no "Derivar de...") 393ms
   ✓ ExperimentsPage - crear nuevo experimento (/experiments/new) > el "Derivar" de una fila NO muestra el selector "basado en" (fuente fija, igual que antes) 336ms
 ✓ src/__tests__/spec44c_gate.test.tsx (3 tests) 988ms
   ✓ spec44c gate: flujo de experimentos por la UI > ExperimentsPage: lista un manifiesto y dispara runExperiment al hacer click en "Ejecutar experimento" 683ms
 ✓ src/__tests__/charts/ActivityTimeline.test.tsx (7 tests) 748ms
   ✓ ActivityTimeline > separa las marcas de entrega de las de alerta, cada una en su carril 331ms
 ✓ src/__tests__/TraceSection.test.tsx (10 tests) 3211ms
   ✓ TraceSection > no vuelca todos los cuadros: la lista se acota y dice el total 1678ms
stderr | src/__tests__/ComposePage.test.tsx > ComposePage fuente RTSP > al elegir rtsp muestra el campo de dirección y arma config { url }
No routes matched location "/runs/r1"

 ✓ src/__tests__/contrato/nueva-corrida.contrato.test.tsx (3 tests) 3620ms
   ✓ Contrato: nueva corrida > consulta preflight, compone fuente y prompts, lanza y abre el detalle real 2160ms
   ✓ Contrato: nueva corrida > impide lanzar con el formulario completo si el target aún no está listo 815ms
   ✓ Contrato: nueva corrida > muestra los bloqueos del preflight y permite lanzar sólo medios con target listo 640ms
 ✓ src/__tests__/experimentview.test.ts (15 tests) 30ms
 ✓ src/__tests__/runview.test.ts (17 tests) 16ms
stderr | src/__tests__/EvidenceView.test.tsx > pide evidencia y alterna los tres estados sin filtrar en el cliente
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/ComposePage.test.tsx > ComposePage cámara guardada (oak_d) > lanza con la config de la cámara guardada elegida
No routes matched location "/runs/r1"

 ✓ src/__tests__/ComposePage.test.tsx (18 tests) 10248ms
   ✓ ComposePage prefill > conserva active_ids del manifiesto y no lo pisan los defaults del set 1742ms
   ✓ ComposePage prefill de source.type video > conserva el source.type original en la composición (round-trip sin colapso a video_file) 858ms
   ✓ ComposePage prefill survives catalog re-fetch (no clobber) > no reaplica el manifiesto cuando `experiments` cambia de referencia tras un re-fetch 837ms
   ✓ ComposePage nombre opcional de la corrida > manda run.name cuando se completa, null cuando se deja vacío 568ms
   ✓ ComposePage nombre opcional de la corrida > deja run.name en null si el campo queda vacío (usa el id autogenerado) 444ms
   ✓ ComposePage aviso de 409 al lanzar > muestra aviso de prueba de cámara activa ante 409 preview_active 516ms
   ✓ ComposePage aviso de 409 al lanzar > muestra aviso de corrida activa ante 409 con active_run_id 498ms
   ✓ ComposePage panel «Antes de lanzar» > los requisitos se van cumpliendo y el botón se habilita al final 766ms
   ✓ ComposePage panel «Antes de lanzar» > desactivar todas las clases vuelve a bloquear, diciendo qué falta 688ms
   ✓ ComposePage rejilla de fuentes > muestra el nombre legible de cada fuente, no su identificador 376ms
   ✓ ComposePage rejilla de fuentes > una fuente deshabilitada explica el motivo que manda el backend 393ms
   ✓ ComposePage rejilla de fuentes > la fuente elegida queda marcada con aria-pressed 334ms
   ✓ ComposePage fuente RTSP > bloquea el lanzamiento si la dirección RTSP trae credenciales censuradas (***) 592ms
   ✓ ComposePage fuente RTSP > al elegir rtsp muestra el campo de dirección y arma config { url } 452ms
   ✓ ComposePage cámara guardada (oak_d) > lanza con la config de la cámara guardada elegida 595ms
 ✓ src/__tests__/runseries.test.ts (12 tests) 32ms
 ✓ src/__tests__/charts/GroupedBars.test.tsx (8 tests) 241ms
 ✓ src/__tests__/charts/timeline.test.ts (9 tests) 54ms
 ✓ src/__tests__/useServiceHealth.test.ts (5 tests) 396ms
stderr | src/__tests__/RunDetailArtifacts.test.tsx > expone el inventario limitado del servicio anterior con descargas verificadas
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/RunKpiStrip.test.tsx (7 tests) 688ms
   ✓ RunKpiStrip > rotula con el glosario, nunca con la clave cruda del sumario 328ms
 ✓ src/__tests__/ClipsPage.test.tsx (5 tests) 577ms
 ✓ src/__tests__/TraceQueries.final.test.tsx (1 test) 100ms
 ✓ src/__tests__/EvidenceView.test.tsx (3 tests) 1651ms
   ✓ pide evidencia y alterna los tres estados sin filtrar en el cliente 882ms
   ✓ persiste la elección al remontar y muestra un solo distintivo con ambos resultados en title 474ms
 ✓ src/__tests__/ui/Table.test.tsx (6 tests) 578ms
   ✓ SortableHeader > muestra la flecha solo en la columna activa, en la direccion correcta 310ms
stderr | src/__tests__/Shell.live.test.tsx > seguir la corrida viva cierra el cajón de navegación móvil
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/RunDetailArtifacts.test.tsx (3 tests) 1562ms
   ✓ expone el inventario limitado del servicio anterior con descargas verificadas 669ms
   ✓ actualiza los archivos después de evaluar sin recargar el detalle 710ms
 ✓ src/__tests__/charts/layout.test.ts (9 tests) 26ms
 ✓ src/__tests__/nav.test.ts (11 tests) 32ms
stderr | src/__tests__/ComposePage.preflight.test.tsx > ComposePage: bloqueos de preflight > informa los motivos con ready=false sin bloquear DBE y los actualiza por polling
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/Shell.live.test.tsx (2 tests) 1968ms
   ✓ seguir la corrida viva cierra el cajón de navegación móvil 835ms
   ✓ lanzar desde el formulario invalida la lista vacía y muestra la corrida global 1131ms
 ✓ src/__tests__/ui/primitives.test.tsx (10 tests) 317ms
 ✓ src/__tests__/EvalSection.test.tsx (4 tests) 253ms
 ✓ src/__tests__/useSidebarCounts.test.ts (3 tests) 288ms
stderr | src/__tests__/contrato/corrida-viva.contrato.test.tsx > Contrato: corrida viva > permite alcanzar la corrida activa desde una ruta distinta del listado
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

stderr | src/__tests__/contrato/detalle-traza-evaluacion.contrato.test.tsx > Contrato: detalle, traza y evaluación > lee detalle y traza, permite inspeccionar cuadros y evaluar contra BENCH
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/ComposePage.preflight.test.tsx (2 tests) 1773ms
   ✓ ComposePage: bloqueos de preflight > informa los motivos con ready=false sin bloquear DBE y los actualiza por polling 1182ms
   ✓ ComposePage: bloqueos de preflight > informa los motivos con ready=true sin bloquear DBE y los actualiza por polling 588ms
 ✓ src/__tests__/ui/Select.test.tsx (5 tests) 515ms
 ✓ src/__tests__/ExperimentQueries.final.test.tsx (1 test) 98ms
 ✓ src/__tests__/charts/Meter.test.tsx (5 tests) 251ms
 ✓ src/__tests__/queryClient.test.ts (4 tests) 15ms
 ✓ src/__tests__/contrato/corrida-viva.contrato.test.tsx (2 tests) 1218ms
   ✓ Contrato: corrida viva > permite alcanzar la corrida activa desde una ruta distinta del listado 760ms
   ✓ Contrato: corrida viva > consulta mientras corre, permite detener y cesa el polling del detalle al terminar 455ms
 ✓ src/__tests__/api.endpoints.test.ts (4 tests) 39ms
stderr | src/__tests__/Shell.distribution.test.tsx > Salud del distribuidor en la barra lateral > informa healthy=true y conserva los dos motores
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/contrato/detalle-traza-evaluacion.contrato.test.tsx (1 test) 1091ms
   ✓ Contrato: detalle, traza y evaluación > lee detalle y traza, permite inspeccionar cuadros y evaluar contra BENCH 1089ms
 ✓ src/__tests__/experiment-api.test.ts (4 tests) 59ms
 ✓ src/__tests__/Shell.distribution.test.tsx (3 tests) 921ms
   ✓ Salud del distribuidor en la barra lateral > informa healthy=true y conserva los dos motores 502ms
stderr | src/__tests__/LiveRunPill.test.tsx > LiveRunPill > no renderiza nada si no hay corrida viva
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/LiveRunPill.test.tsx (3 tests) 315ms
stderr | src/__tests__/App.test.tsx > App > renderiza el título de la consola
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/App.test.tsx (2 tests) 761ms
   ✓ App > renderiza el título de la consola 592ms
 ✓ src/__tests__/ui/Button.test.tsx (5 tests) 363ms
 ✓ src/__tests__/stream.test.ts (3 tests) 15ms
 ✓ src/__tests__/preview.test.ts (2 tests) 20ms
 ✓ src/__tests__/ui/Banner.test.tsx (3 tests) 276ms
 ✓ src/__tests__/ui/Badge.test.tsx (4 tests) 145ms
 ✓ src/__tests__/ui/Select.field.test.tsx (1 test) 429ms
   ✓ Select dentro de Field > cancela la activación del label al elegir, sin reabrir el control 427ms
 ✓ src/__tests__/ui/InlineDeleteConfirm.test.tsx (2 tests) 349ms
 ✓ src/__tests__/ui/ConditionName.test.tsx (3 tests) 142ms
 ✓ src/__tests__/ui/SegmentedControl.test.tsx (2 tests) 432ms
   ✓ SegmentedControl > marca la opcion activa con aria-pressed 379ms
 ✓ src/__tests__/ui/SearchInput.test.tsx (1 test) 86ms
 ✓ src/__tests__/ui/PageHeader.test.tsx (2 tests) 278ms
 ✓ src/__tests__/promptview.test.ts (3 tests) 7ms
stderr | src/__tests__/CamerasPage.preview-error.test.tsx > muestra el fallo del sondeo de preview sin rechazar una promesa sin manejar
⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.
⚠️ React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7. You can use the `v7_relativeSplatPath` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_relativesplatpath.

 ✓ src/__tests__/ui/icons.test.tsx (1 test) 60ms
 ✓ src/__tests__/CamerasPage.preview-error.test.tsx (1 test) 265ms

 Test Files  72 passed (72)
      Tests  467 passed (467)
   Start at  04:48:45
   Duration  24.22s (transform 8.81s, setup 0ms, collect 72.02s, tests 87.78s, environment 119.75s, prepare 20.24s)

```

### Build

```text
$ cd webconsole/frontend && npm run build

> eovrt-webconsole-frontend@0.1.0 build
> tsc && vite build

vite v5.4.21 building for production...
transforming...
✓ 165 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.40 kB │ gzip:   0.27 kB
dist/assets/index-naqAaFT8.css   35.99 kB │ gzip:   7.20 kB
dist/assets/index-BqKuWijI.js   408.00 kB │ gzip: 123.60 kB
✓ built in 2.09s
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

 ✓ src/__tests__/contrato/corrida-viva.contrato.test.tsx (2 tests) 298ms
 ✓ src/__tests__/contrato/detalle-traza-evaluacion.contrato.test.tsx (1 test) 313ms
   ✓ Contrato: detalle, traza y evaluación > lee detalle y traza, permite inspeccionar cuadros y evaluar contra BENCH 312ms
 ✓ src/__tests__/contrato/experimentos-distribucion.contrato.test.tsx (4 tests) 641ms
 ✓ src/__tests__/contrato/nueva-corrida.contrato.test.tsx (3 tests) 746ms
   ✓ Contrato: nueva corrida > consulta preflight, compone fuente y prompts, lanza y abre el detalle real 481ms

 Test Files  4 passed (4)
      Tests  10 passed (10)
   Start at  04:30:55
   Duration  3.30s (transform 1.04s, setup 0ms, collect 3.15s, tests 2.00s, environment 3.73s, prepare 850ms)

```

### Contrato contra el árbol actual

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

 ✓ src/__tests__/contrato/detalle-traza-evaluacion.contrato.test.tsx (1 test) 446ms
   ✓ Contrato: detalle, traza y evaluación > lee detalle y traza, permite inspeccionar cuadros y evaluar contra BENCH 445ms
 ✓ src/__tests__/contrato/corrida-viva.contrato.test.tsx (2 tests) 483ms
 ✓ src/__tests__/contrato/experimentos-distribucion.contrato.test.tsx (4 tests) 745ms
   ✓ Contrato: experimentos y distribución > lista y abre un experimento con outcomes vinculados a cada alerta 351ms
 ✓ src/__tests__/contrato/nueva-corrida.contrato.test.tsx (3 tests) 852ms
   ✓ Contrato: nueva corrida > consulta preflight, compone fuente y prompts, lanza y abre el detalle real 557ms

 Test Files  4 passed (4)
      Tests  10 passed (10)
   Start at  04:49:51
   Duration  3.19s (transform 942ms, setup 0ms, collect 2.71s, tests 2.53s, environment 3.54s, prepare 922ms)

```

### Ruff (exit 1 heredado)

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

### Comparación Ruff

```text
$ Multiconjunto por archivo, código y mensaje
Línea de base Ruff: 36
Diagnósticos actuales: 36
Diagnósticos nuevos: 0
Diagnósticos eliminados: 0
```

### Contraste de inventario

```text
$ Lectura independiente CSV y comparación con API
CSV vs API: mismos35 resultados y mismos conteos, sin faltantes ni extras.
Índices: {'bench_imagenes': 5, 'bench_nivel_a': 4, 'clip_bench': 14, 'realtime': 12}
Filas: 1760 Corridas únicas: 1436
titulos.yaml: 35 entradas;35 títulos vacíos.
```

### Lectura completa de artefactos

```text
$ Lectura local de las 1436 corridas
Corridas leídas del archivo: 1436
Summary preservado: 1402
Sólo sustitutos, sin inventar summary: 34
Original presente en runs/ del plano: {'media-plane': 420, 'control-plane': 16}
archived_only: motivos presentes; ningún enlace vivo.
```

### Servicios detenidos y aislamiento GPU

```text
$ Prueba de puertos y dispositivos del namespace del BFF
{
  "ports_closed": {
    "8080": true,
    "8081": true,
    "8082": true
  },
  "gpu_isolation": {
    "gpu_devices": [],
    "dxg": false,
    "CUDA_VISIBLE_DEVICES": "-1"
  }
}
```

### Navegador: tres niveles

```text
$ node /tmp/eovrt-tramo7/capture.mjs
{
  "mode": "full",
  "viewport": {
    "width": 1440,
    "height": 1000
  },
  "captures": [
    "indice-servicios-apagados",
    "resultado",
    "corrida-media",
    "corrida-control",
    "paginacion-544",
    "archived-only"
  ],
  "requests": [
    "/api/evidencia",
    "/api/evidencia/resultado?id=realtime%2Ft_alert_notification&page=1&page_size=25",
    "/api/evidencia/run?plane=media-plane&run_id=run_20260813_051703_dbe_grounding_dino_1d5e83",
    "/api/evidencia/run?plane=control-plane&run_id=control_talert_integrated_a_p1_c08_20260813T051703Z_21e369",
    "/api/evidencia/resultado?id=realtime%2Fdecimado_empirico&page=1&page_size=25",
    "/api/evidencia/resultado?id=realtime%2Fdecimado_empirico&page=2&page_size=25",
    "/api/evidencia/resultado?id=bench_imagenes%2Fmodelos_crudos&page=1&page_size=25",
    "/api/evidencia/run?plane=media-plane&run_id=run_20260709_163954_dbe_grounding_dino_051ede"
  ],
  "errors": []
}
```

### Navegador: archivo ausente

```text
$ node /tmp/eovrt-tramo7/capture.mjs empty
{
  "mode": "empty",
  "viewport": {
    "width": 1440,
    "height": 1000
  },
  "captures": [
    "estado-vacio"
  ],
  "requests": [
    "/api/evidencia"
  ],
  "errors": []
}
```

### Integridad

```text
$ Hashes protegidos y diff de paridad
Tests preexistentes: hashes idénticos salvo la excepción autorizada de nav.
nav.test.ts: congelado tras esa edición y la prueba nueva.
Cambios ajenos y especificación del usuario: hashes idénticos.
/tmp/paridad: 50b666b intacto; diff versionado vacío.
git diff --check: exit=0.
```

### Ícono final en navegador

```text
{
  "iconoEvidencia": {
    "width": "16",
    "height": "16",
    "strokeWidth": "1.4",
    "ariaHidden": "true"
  },
  "distintoDeCatalogos": true,
  "visibleConBarraColapsada": true,
  "resultados": 35
}
```
