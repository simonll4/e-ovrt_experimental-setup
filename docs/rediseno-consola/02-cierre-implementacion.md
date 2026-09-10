# Cierre de implementación — tramos 0 a 5

## Cierre vigente del punch-list — 2026-09-10

P-2, P-1, P-3 y P-5 cerrados. Las **dos ampliaciones de P-4 fueron aprobadas
por el usuario el 10 de septiembre de 2026**, con los motivos registrados abajo.
El punch-list se ejecutó en ese orden; no incluyó los tramos 6 ni 7.

Rama: `feature/webconsole-adopcion-front-design`. El punch-list produjo **seis commits**, uno por
tramo desde `50b666b`, con los mensajes establecidos. El último incorpora esta
actualización documental. No hubo merge ni push; `main`, la rama operativa y
los cambios ajenos en `defensa/README.md` y `results/bench_imagenes/index.md`
permanecen intactos. Los documentos futuros `04-evidencia-diseno.md`, `tramo-6.md`
y `tramo-7.md` no forman parte de estos commits.

### Verificación vigente

| Verificación | Resultado |
| --- | --- |
| Contrato contra `50b666b` sin tocar | **10/10**, cuatro archivos |
| Contrato contra el árbol final | **10/10**, cuatro archivos |
| Backend final | **784/784**, sin fallos ni skips |
| Frontend final | **454/454**, 69 archivos |
| `tsc && vite build` | Correcto en los seis cortes y en el árbol final |
| Compilación Python | Correcta en los seis cortes |
| Ruff | **36** diagnósticos, **0 nuevos** frente a `3500923`; no se declara verde |

Las [salidas completas de cada verificación](punch-list-verificaciones.md) están
pegadas en texto versionado, con los intentos intermedios identificados y los
resultados finales. Los valores 772/454 y los recorridos de navegador que siguen
más abajo son la foto del 9 de septiembre, no una segunda verificación del estado
actual. No se repitieron recorridos con hardware durante este punch-list.

### P-2 y D-8: paridad de lanzamiento DBE

Se quitaron de `ComposePage.missingReason` los bloqueos del preflight agregado.
Con formulario completo y target listo se puede lanzar una corrida de sólo
medios aunque control esté caído. `PlatformStatus` sigue informando la salud del
servicio. El gate del target y los gates por manifiesto de Experimentos permanecen.

Precisión observada al ejecutar: `PlatformStatus` no imprime los mensajes
arbitrarios de `blockers`; representa la salud mediante etiquetas. La fixture
del contrato informa control caído y exige **«Motor de reglas sin respuesta»**,
el botón habilitado y un POST de lanzamiento en ambas interfaces. No se simuló
un target caído para obtener un bloqueo por una causa distinta.

El primer caso conserva íntegramente su aserción del payload de `POST /api/runs`.
El caso del target no listo permanece idéntico. Se adaptaron controles nativos,
botones y el selector global de Experimentos a ambas interfaces. El helper
`soporte.tsx`, los contratos de corrida viva y detalle/traza, la prueba D-5 y
la igualdad exacta de `test_report_generator.py` no se modificaron.

Los dos casos adicionales de `ComposePage.preflight.test.tsx`, introducidos por
este trabajo y ausentes en `50b666b`, ahora protegen D-8: con `ready=false/true`
el aviso cambia por polling y lanzar DBE sigue enviando el POST. No se conservaron
como especificación deseada las expectativas del gateo revertido.

El contrato vuelve a quedar **congelado**. `/tmp/paridad` se conserva registrado
en `50b666b`, con el contrato actualizado y `node_modules` enlazado. Se comprobó
que ningún archivo versionado de esa base cambió; puede reutilizarse para las
próximas tareas sin ejecutar de nuevo `git worktree add`.

### P-1: cortes verificables

| Tramo | Frontend del corte | Dependencias y separación |
| --- | --- | --- |
| 0 | 397/397 | Sólo los cinco archivos del contrato; producción idéntica a `50b666b`. |
| 1 | 397/397 | Backend 761/761; `routers/experiments.py` y `run_backend.py` desde `3500923`, sin las ampliaciones P-4 todavía. |
| 2 | 401/401 | Pantallas y CSS intactos. Se retira `api.ts` para resolver el índice modular; quedan los seis hooks anteriores. |
| 3 | 439/439 | Compare y Cámaras se adelantan por los componentes compartidos; Select y su regresión entran juntos. TargetBadge y useLiveRun se difieren al tramo 4. App.test sólo adelanta el import del proveedor. |
| 4 | 451/451 | Completa el armazón y las pantallas restantes; retira los hooks antiguos. Shell aún muestra dos servicios. |
| 5 | 454/454 | Tercer servicio, pruebas D-5 y las dos ampliaciones P-4 conservadas para revisión. Backend final 784/784. |

Cada mensaje de commit explica las dependencias que obligaron a mover archivos
entre cortes. Los módulos compartidos de queries, tipos, gráficos y CSS entran
completos donde corresponde, sin inventar versiones intermedias. Las pruebas
se ejecutaron contra cada árbol preparado, no contra el directorio final usado
para reconstruirlo. El backend del corte 1 usó `PYTHONPATH` hacia ese árbol y
repos hermanos enlazados; el primer intento con 15 skips por rutas ausentes se
reemplazó por la ejecución final de 761/761.

Para obtener los seis SHA y mensajes del punch-list:

```bash
git log --reverse --format='%h %s' 50b666b..22a4021
```

### P-4: ampliaciones APROBADAS por el usuario — 2026-09-10

| Capacidad | Evidencia técnica | Decisión y motivo |
| --- | --- | --- |
| Índice de artefactos mediante sondeo de archivos conocidos | `test_artifacts_legacy_service.py`: 404/307/308, sondeo y aviso de inventario parcial. | **APROBADA.** El servicio media-plane sólo expone `/runs/{run_id}/artifacts/{artifact_path:path}` y no expone índice de artefactos: ninguna versión lo hace. El endpoint del BFF `GET /api/runs/{id}/artifacts` introducido por `d042ad1` asumía un upstream inexistente. El sondeo es la ruta primaria que funciona contra el servicio real; sin él, la pestaña de artefactos está siempre rota. No es un respaldo defensivo ni compatibilidad con versiones anteriores. |
| Navegación de evidencia de experimentos tras reiniciar la consola | `test_experiment_history.py`: identidad, reporte y alertas persistidas; errores y contención de rutas. | **APROBADA.** El código anterior resolvía detalle y alertas desde el `experiment_manager` en memoria. Reiniciar la consola volvía inaccesible un experimento terminado. La lectura persistida es precondición de la vitrina de evidencia. |

Ambas implementaciones y sus pruebas quedaron en el commit del tramo 5. Esta
aprobación posterior y la precisión del comentario de `run_backend.list_artifacts`
se registran en un commit propio, sin alterar su comportamiento.
La lectura histórica del 10 de septiembre agregó doce tests y explica el paso
del backend de **772 a 784** después del cierre anterior.

### P-5: reportes resguardados

Los textos [tramo 2](tramo-2-reporte.md) y
[tramos 3–5](tramos-3-5-reporte.md) se movieron desde `webconsole/tools/captures/`
a este directorio y se versionan. Se ajustaron los enlaces relativos; los PNG,
logs históricos y datos de prueba permanecen donde estaban, ignorados por Git.
Los títulos y resultados de esos reportes se conservan como historia y están
marcados explícitamente como tales.

### Hallazgos registrados sin ampliar el alcance

- La visibilidad literal de `blockers` que suponía la auditoría no existía en
  `PlatformStatus`; se comprobó la etiqueta real de salud en ambas versiones.
- Los 36 diagnósticos Ruff heredados siguen presentes; no se modificó código
  ajeno para eliminarlos.
- Los títulos de `titulos.yaml`, la clasificación de los 19 manifiestos y las
  entregas de los tramos 6/7 corresponden a tareas posteriores. No se editaron.

---

## Registro histórico del 2026-09-09 — cierre anterior, sustituido por el vigente

> Las afirmaciones de gateo global, 772 pruebas de backend y ausencia de commits
> de esta sección describen ese momento. D-8 revierte el gateo global; P-1 crea
> la historia por tramos. Las dos ampliaciones de P-4 fueron aprobadas después,
> el 10 de septiembre, según el registro vigente de arriba.

Fecha: 2026-09-09. Rama: `feature/webconsole-adopcion-front-design`.
Base de trabajo: `50b666b`. Referencia conservada: `.worktrees/front-design`, commit `3500923`.

## Resultado

Implementación de los seis tramos terminada y verificada. Contrato: **10/10**.
Suite frontend: **454/454**. Suite backend: **772/772**. Build de producción correcto.
Los cuatro flujos troncales se recorrieron mediante acciones de navegador contra
servicios reales aislados, sin interceptar HTTP. Se inspeccionaron sus capturas.

Este documento sustituye el estado de cierre pendiente del
[reporte anterior](tramos-3-5-reporte.md);
aquel se conserva como registro histórico. No hubo staging, commits, merge ni push.
Los cambios previos en `defensa/README.md` y `results/bench_imagenes/index.md`
se preservaron. No se modificó código de los otros componentes.

| Tramo | Entrega |
| --- | --- |
| 0 | Cuatro contratos de comportamiento sobre fetch, con 10 casos y rechazo de peticiones inesperadas. |
| 1 | BFF, inventarios, filtros y paginación, índice de traza, comparación, umbrales y pruebas de la referencia. |
| 2 | API modular, TanStack Query, claves de caché, proveedores, utilidades y captura reproducible. |
| 3 | Composición, detalle, traza, métricas, gráficos y CSS nuevos; preflight y píldora preservados. |
| 4 | Listados server-side, experimentos, prompts, cámaras, clips, plataforma, navegación y 404. |
| 5 | Salud informativa del tercer servicio, outcomes visibles y validación completa de integración. |

## Desviaciones y correcciones registradas

Se copiaron los archivos previstos desde la referencia; no se hizo cherry-pick.
La comparación de todos sus archivos de webconsole no detectó archivos faltantes.
Además de las excepciones del diseño, el cierre incorporó correcciones acotadas
a fallos del flujo real:

1. **D-3:** se mantienen el componente global de corrida viva y sus reglas CSS.
   El aviso usa `useRunsEnCurso`. Se ve fuera del detalle, en escritorio colapsado
   y en móvil; seguirlo cierra el cajón.
2. **D-4:** el test existente del reporte espera los tres campos aditivos
   `passed`, `threshold`, `threshold_direction`. No se cambian cifras.
3. **D-5:** cliente HTTP persistente de distribución, sondeo paralelo y tercer
   indicador. Sin manifiesto, su caída no agrega blockers. Los gates específicos
   de distribución de los manifiestos permanecen intactos.
4. **D-7:** Vite conserva 5173 y adopta `strictPort: true`.
5. **Cierre de dependencias:** ComparePage y su test se adelantaron del tramo 4
   al 3 por SERIES_COLORS; GroupedBars.test importa la paleta desde su módulo
   nuevo, conservando las assertions.
6. **Preflight:** Compose bloquea tanto por ready=false como por blockers no
   vacíos, incluso antes de enviar el POST. Conserva los motivos y recuperación.
7. **Contrato:** tras el pedido de completar el trabajo, se adaptaron únicamente
   los selectores a los controles nuevos y las fixtures de las tres lecturas
   adicionales: trace/index, artifacts y comparison. Se conservaron las
   comprobaciones de payload, bloqueo, polling, parada, evaluación y outcomes,
   y la detección estricta de HTTP inesperado. No hay skips ni expectativas
   debilitadas. Los archivos de contrato de corrida viva y detalle no se editaron
   en esta adaptación.
8. **Select dentro de Field:** el click en una opción activaba nuevamente el
   botón por el comportamiento nativo del label y reabría la lista. Se cancela
   esa activación; regresión nueva para el evento nativo.
9. **Datos finales:** la traza usa fases live/final para pedir el último índice
   y página antes de detener polling. Reporte y alertas de experimento se
   refrescan al terminar, incluso después de un 404 mientras consolidaban.
   Se mantiene la carga paralela inicial. Regresiones nuevas verifican
   actualización y cese del polling.
10. **Invalidación tras lanzar/evaluar:** Compose usa la mutación compartida,
    actualiza la lista previamente vacía y deshabilita el botón durante el POST.
    Evaluar invalida el inventario para mostrar eval_perception.json sin recarga.
    Ambos caminos tienen regresiones sobre HTTP.
11. **Inventario con el media-plane instalado:** el servicio real sólo expone
    archivos individuales, no el índice que esperaba la referencia. El BFF
    conserva el índice nativo cuando existe; ante 404/307/308 verifica la corrida
    y sondea archivos estándar mediante Range, con concurrencia limitada y cierre
    de streams. No sigue redirecciones externas ni inventa tamaños. Devuelve
    `complete: false` y un aviso visible; una caída se muestra como error y no
    como ausencia de archivos. Se agregaron seis pruebas de backend.
12. **Cámaras:** un fallo del sondeo inicial de preview producía una promesa sin
    manejar. Ahora muestra un mensaje recuperable; regresión nueva.
13. **Móvil:** el cajón se abre con ancho completo aunque la preferencia de
    escritorio sea colapsada. La preferencia se conserva al cerrarlo; test y
    captura con ancho real de 390 px.
14. **Infraestructura de pruebas:** el QueryClient del wrapper se crea una vez
    por montaje, no nuevamente al rerender. Se limpiaron siete líneas con
    espacios finales heredadas de ComposePage; cambio exclusivamente de formato.

## Verificación: salida real

### Backend

`cd webconsole/backend && ./.venv/bin/python -m pytest -q`

```text
........................................................................ [  9%]
........................................................................ [ 18%]
........................................................................ [ 27%]
........................................................................ [ 37%]
........................................................................ [ 46%]
........................................................................ [ 55%]
........................................................................ [ 65%]
........................................................................ [ 74%]
........................................................................ [ 83%]
........................................................................ [ 93%]
....................................................                     [100%]
772 passed in 199.88s (0:03:19)
```

### Frontend

`cd webconsole/frontend && npm test`

[Salida íntegra](../../webconsole/tools/captures/cierre-frontend.log).

```text
Test Files  69 passed (69)
      Tests  454 passed (454)
   Start at  13:47:51
   Duration  25.31s (transform 8.71s, setup 0ms, collect 67.51s, tests 76.93s, environment 144.96s, prepare 22.04s)
```

### Contrato, ejecución dedicada

`cd webconsole/frontend && npm test -- --run src/__tests__/contrato`

También incluido en la suite completa final.
[Salida íntegra](../../webconsole/tools/captures/cierre-contrato.log).

```text
Test Files  4 passed (4)
      Tests  10 passed (10)
   Start at  13:42:39
   Duration  3.84s (transform 1.40s, setup 0ms, collect 4.30s, tests 3.15s, environment 3.51s, prepare 782ms)
```

### Build

`cd webconsole/frontend && npm run build`

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
dist/assets/index-CAsfT6Fb.js   396.88 kB │ gzip: 120.41 kB
✓ built in 3.05s
```

### Higiene y lint

`git diff --check`: salida vacía, exit 0.

Ruff focal sobre app.py, preflight.py, run_backend.py y sus dos archivos de
tests nuevos:

```text
All checks passed!
```

Ruff global **no es verde**: conserva 36 diagnósticos. Se ejecutó el mismo
comando `ruff check src tests --output-format json` sobre el árbol actual y
`3500923`; los 36 coinciden por archivo, código y mensaje, sin diagnósticos
adicionales. No se alteró código ajeno al alcance para ocultarlos.
[Actual](../../webconsole/tools/captures/cierre-ruff.json) ·
[Referencia](../../webconsole/tools/captures/cierre-ruff-referencia.json).

Vitest conserva avisos de futuras opciones de React Router y fixtures sin
ruta de destino; no son fallos de los flujos reales.

## Recorrido de los cuatro flujos, paso a paso

Entorno aislado en
[tools/captures/cierre-e2e.rSpqLP](../../webconsole/tools/captures/cierre-e2e.rSpqLP):
BFF 18090, media 18080, control 18081, distribución 18082, MQTT 18883 y RTSP 18554.
Modelo mock CPU. Datos de ejecución, manifiestos derivados y broker sólo en
ese directorio gitignorado. Los puertos 8080/8081/8082 de la interfaz son los
rótulos previstos por el diseño, no los puertos temporales de este ensayo.

### 1. Nueva corrida y gateo

1. Abrí Nueva corrida, elegí bench_v2_test y console_validation.
2. Desactivé helmet, indiqué nombre y máximo de cinco unidades.
3. Confirmé formulario completo y botón habilitado.
4. Lancé: POST /api/runs respondió 201 y abrió el detalle correcto.
5. En un segundo recorrido sin lanzar, detuve sólo el distribuidor temporal:
   indicador rojo, ready=true, blockers=[] y botón habilitado.
6. Lo restauré y detuve sólo control: indicador rojo, motivo explícito y botón
   deshabilitado. Al restaurarlo se habilitó por polling. Cero POST en esta prueba.

[Formulario](../../webconsole/tools/captures/cierre-e2e.rSpqLP/01-composicion-bench.png) ·
[Tres arriba](../../webconsole/tools/captures/cierre-e2e.rSpqLP/14-tres-servicios.png) ·
[Distribuidor caído](../../webconsole/tools/captures/cierre-e2e.rSpqLP/15-distribuidor-caido.png) ·
[Control bloqueado](../../webconsole/tools/captures/cierre-e2e.rSpqLP/16-control-bloqueado.png) ·
[Recuperación](../../webconsole/tools/captures/cierre-e2e.rSpqLP/17-servicios-recuperados.png).

### 2. Corrida viva

1. Elegí Cámara RTSP e ingresé un stream sintético local en bucle.
2. Lancé desde el formulario. El servicio confirmó status=running y live=true;
   crecieron las lecturas del detalle y aparecieron cuadros de traza.
3. Navegué a Conjuntos: la píldora permaneció visible y enlazó a la corrida.
4. Colapsé la barra: permaneció el indicador accesible.
5. Pasé a 390 × 844, abrí el menú y comprobé ancho completo del cajón.
   Seguí la píldora: volvió al detalle y cerró el menú.
6. Detuve: un único POST /stop respondió 202. El estado pasó a stopped.
   Tras estabilizarse la última lectura, no hubo nuevas consultas de estado
   durante 20 segundos.

Corrida: `run_20260909_134701_dbe_mock_a8ac02`.
[En curso](../../webconsole/tools/captures/cierre-e2e.rSpqLP/07-corrida-viva.png) ·
[Global](../../webconsole/tools/captures/cierre-e2e.rSpqLP/08-aviso-global.png) ·
[Colapsada](../../webconsole/tools/captures/cierre-e2e.rSpqLP/09-aviso-colapsado.png) ·
[Móvil](../../webconsole/tools/captures/cierre-e2e.rSpqLP/10-aviso-movil.png) ·
[Detenida](../../webconsole/tools/captures/cierre-e2e.rSpqLP/11-corrida-detenida.png).

### 3. Detalle, traza y evaluación

1. La corrida de cinco imágenes terminó con éxito.
2. La traza final apareció sin recargar; elegí otro cuadro y volví con Cuadro
   anterior. Se veían detecciones y la imagen asociada.
3. Abrí Evaluación y ejecuté Evaluar contra BENCH. POST respondió 200; se
   mostraron métricas por clase con GT positivo.
4. Abrí Archivos en la misma navegación: apareció eval_perception.json,
   verificando la invalidación posterior a evaluar.
5. Descargué summary.json desde su enlace y verifiqué units_processed=5.
   El aviso de inventario parcial permanece explícito.
6. En Comparar elegí dos corridas evaluadas: respuesta 200 con dos resultados,
   tabla y gráfico visibles. Los empates en cero del mock no tienen ganador.

Última corrida: `run_20260909_134843_dbe_mock_52a3ca`.
[Traza](../../webconsole/tools/captures/cierre-e2e.rSpqLP/02-detalle-traza.png) ·
[Evaluación](../../webconsole/tools/captures/cierre-e2e.rSpqLP/03-evaluacion-bench.png) ·
[Archivos](../../webconsole/tools/captures/cierre-e2e.rSpqLP/12-archivos.png) ·
[Comparación](../../webconsole/tools/captures/cierre-e2e.rSpqLP/13-comparacion.png).

### 4. Derivación, experimento y distribución

1. Abrí Experimentos y Partir de este sobre console_validation.
2. Comprobé máximo inicial 120, di un nombre nuevo y cambié el máximo a 60.
3. Derivé: POST respondió 201 y apareció el manifiesto nuevo.
4. Ejecuté desde esa fila: POST respondió 202 y abrió el experimento.
5. Media procesó el video, control confirmó una alerta CR-01 y el distribuidor
   entregó una notificación al broker local en modo live, MQTT QoS 1.
6. Sin recargar la página apareció el reporte final, la fila de alerta con
   «entregada» y la tarjeta de distribución con entregada: 1.
7. La latencia de distribución figura como no interpretable por reloj de prueba;
   no se presenta el replay como medición temporal operacional.

Experimento:
`exp_20260909T133945Z_console_validation_cierre_1788961183307`.
Media: `run_20260909_133945_dbe_mock_de6210`.
Control: `control_console_validation_cierre_1788961183307_20260909T133946Z_0a8be8`.

[Derivación](../../webconsole/tools/captures/cierre-e2e.rSpqLP/04-derivacion.png) ·
[Outcomes](../../webconsole/tools/captures/cierre-e2e.rSpqLP/05-experimento-outcomes.png) ·
[Detalle](../../webconsole/tools/captures/cierre-e2e.rSpqLP/06-outcomes-detalle.png).

## Evidencia y reproducción

Los scripts de estos recorridos y sus respuestas completas están junto a las
capturas: bench.mjs, live.mjs, experiment.mjs, files-compare.mjs y health.mjs,
con sus respectivos *-evidence.json. Usan navegador real, sin page.route.
health.mjs contiene los PID exactos verificados de esta ejecución: para repetirlo
hay que levantar nuevos servicios aislados y resolver sus PID; no se deben
reutilizar números de procesos ciegamente.

El harness bff.py sólo adapta directorios del entorno aislado y recarga el estado
real guardado de un experimento para conservarlo entre reinicios. La lógica y
las rutas HTTP usadas son las de producción. La emisión sintética RTSP sigue
[la publicación con FFmpeg documentada por MediaMTX](https://mediamtx.org/docs/publish/ffmpeg);
el binario temporal se obtuvo de su distribución oficial.

[Manifest final de 13 rutas](../../webconsole/tools/captures/cierre-rutas/manifest.json):
todas con título, captura y cero errores JavaScript. Viewport 1440 × 1000.
Las capturas de los cambios anteriores siguen disponibles:
[tramo 2 antes](../../webconsole/tools/captures/tramo-2-antes/manifest.json),
[tramo 2 después](../../webconsole/tools/captures/tramo-2-despues/manifest.json),
[tramo 3 antes](../../webconsole/tools/captures/tramo-3-antes/manifest.json),
[tramo 3 después](../../webconsole/tools/captures/tramo-3-despues/manifest.json),
[tramo 4 después](../../webconsole/tools/captures/tramo-4-despues/manifest.json).

## Límites observados, no ocultados

- No se validó hardware OAK-D ni cámaras externas. El RTSP es sintético.
- BENCH usa el split legacy bench_v2_test que admite el servicio instalado.
  El mock produce AP=0: es una prueba técnica de UI/API, no evidencia científica
  nueva ni una evaluación de bench_v3 o de modelos reales.
- El servicio media instalado no publica inventario completo; la compatibilidad
  enumera únicamente archivos estándar confirmados. No enumera previews como
  directorio ni afirma completitud.
- Control no publica /api/conditions en esta versión: se conserva el fallback
  existente del catálogo. No se modificaron los servicios hermanos.
- Reiniciar el BFF pierde el estado en memoria del manager de experimentos,
  aunque los reportes persisten. Es una limitación previa, fuera de este rediseño.
- Persisten los 36 diagnósticos Ruff de la referencia. En lo visual, los IDs
  largos se abrevian en espacios pequeños y la tabla de métricas conserva sus
  nombres técnicos; no se amplió el alcance con otra remaquetación.
- Durante la preparación se corrigieron fixtures locales (región del patrón,
  URL del distribuidor y selectores del harness). Esos intentos no se cuentan
  como flujos aprobados; sólo se enlaza la evidencia de los recorridos completos.
- Las capturas, datos sembrados, logs y binarios temporales son gitignorados.
  Se conservaron; no se borró ningún dato. Se detuvieron los servicios temporales
  al terminar, comprobando antes que no quedaran corridas activas.

## Inventario completo de archivos de implementación

Estado relativo a HEAD, incluyendo altas y bajas; 144 archivos bajo webconsole.
Este inventario excluye los dos cambios previos del usuario y los artefactos
gitignorados. El presente reporte es el único documento nuevo de cierre.

```text
 M webconsole/.gitignore
 M webconsole/backend/src/eovrt_webconsole/app.py
 M webconsole/backend/src/eovrt_webconsole/clips/inventory.py
 M webconsole/backend/src/eovrt_webconsole/clips/trim.py
 M webconsole/backend/src/eovrt_webconsole/experiment/applicability.py
 M webconsole/backend/src/eovrt_webconsole/experiment/control_backend.py
 M webconsole/backend/src/eovrt_webconsole/experiment/report.py
 M webconsole/backend/src/eovrt_webconsole/preflight.py
 M webconsole/backend/src/eovrt_webconsole/prompt_store.py
 M webconsole/backend/src/eovrt_webconsole/repo_catalog.py
 M webconsole/backend/src/eovrt_webconsole/routers/catalog.py
 M webconsole/backend/src/eovrt_webconsole/routers/experiments.py
 M webconsole/backend/src/eovrt_webconsole/routers/prompts.py
 M webconsole/backend/src/eovrt_webconsole/routers/runs.py
 M webconsole/backend/src/eovrt_webconsole/run_backend.py
 M webconsole/backend/src/eovrt_webconsole/trace.py
 M webconsole/backend/tests/fake_control_service.py
 M webconsole/backend/tests/fake_service.py
 M webconsole/backend/tests/test_report_generator.py
 M webconsole/frontend/package-lock.json
 M webconsole/frontend/package.json
 M webconsole/frontend/src/App.tsx
 M webconsole/frontend/src/__tests__/App.test.tsx
 M webconsole/frontend/src/__tests__/CamerasPage.test.tsx
 M webconsole/frontend/src/__tests__/ClipsPage.test.tsx
 M webconsole/frontend/src/__tests__/ComparePage.test.tsx
 M webconsole/frontend/src/__tests__/ComposePage.test.tsx
 M webconsole/frontend/src/__tests__/DeriveExperimentForm.test.tsx
 M webconsole/frontend/src/__tests__/EvalSection.test.tsx
 M webconsole/frontend/src/__tests__/ExperimentDetailPage.test.tsx
 M webconsole/frontend/src/__tests__/ExperimentDetailPageRiskBanner.test.tsx
 M webconsole/frontend/src/__tests__/ExperimentsPage.new.test.tsx
 M webconsole/frontend/src/__tests__/ExperimentsPage.test.tsx
 M webconsole/frontend/src/__tests__/LiveRunPill.test.tsx
 M webconsole/frontend/src/__tests__/LiveViewer.test.tsx
 M webconsole/frontend/src/__tests__/PlatformPage.test.tsx
 M webconsole/frontend/src/__tests__/PreviewWithBoxes.test.tsx
 M webconsole/frontend/src/__tests__/PromptSetEditor.test.tsx
 M webconsole/frontend/src/__tests__/PromptSetsPage.test.tsx
 M webconsole/frontend/src/__tests__/RecordPanel.test.tsx
 M webconsole/frontend/src/__tests__/RunDetailPage.test.tsx
 M webconsole/frontend/src/__tests__/RunKpiStrip.test.tsx
 M webconsole/frontend/src/__tests__/RunsPage.test.tsx
 M webconsole/frontend/src/__tests__/Shell.test.tsx
 M webconsole/frontend/src/__tests__/TraceSection.test.tsx
 M webconsole/frontend/src/__tests__/TrimDialog.test.tsx
 M webconsole/frontend/src/__tests__/api.test.ts
 M webconsole/frontend/src/__tests__/charts/GroupedBars.test.tsx
 M webconsole/frontend/src/__tests__/spec44c_gate.test.tsx
 M webconsole/frontend/src/__tests__/traceview.test.ts
 M webconsole/frontend/src/__tests__/useServiceHealth.test.ts
 M webconsole/frontend/src/__tests__/useSidebarCounts.test.ts
 D webconsole/frontend/src/api.test.ts
 D webconsole/frontend/src/api.ts
 M webconsole/frontend/src/components/DeriveExperimentForm.tsx
 M webconsole/frontend/src/components/EvalSection.tsx
 M webconsole/frontend/src/components/LivePromptPanel.tsx
 M webconsole/frontend/src/components/LiveRunPill.tsx
 M webconsole/frontend/src/components/LiveViewer.tsx
 M webconsole/frontend/src/components/RecordPanel.tsx
 M webconsole/frontend/src/components/RunKpiStrip.tsx
 M webconsole/frontend/src/components/RunTimeline.tsx
 M webconsole/frontend/src/components/Shell.tsx
 M webconsole/frontend/src/components/TargetBadge.tsx
 M webconsole/frontend/src/components/TraceSection.tsx
 M webconsole/frontend/src/components/charts/ActivityTimeline.tsx
 M webconsole/frontend/src/components/charts/GroupedBars.tsx
 M webconsole/frontend/src/components/charts/Meter.tsx
 M webconsole/frontend/src/components/charts/Sparkline.tsx
 M webconsole/frontend/src/components/ui/Select.tsx
 M webconsole/frontend/src/components/ui/Table.tsx
 M webconsole/frontend/src/components/ui/icons.tsx
 M webconsole/frontend/src/components/ui/index.ts
 M webconsole/frontend/src/experimentview.ts
 M webconsole/frontend/src/main.tsx
 M webconsole/frontend/src/pages/CamerasPage.tsx
 M webconsole/frontend/src/pages/CatalogPage.tsx
 M webconsole/frontend/src/pages/ClipsPage.tsx
 M webconsole/frontend/src/pages/ComparePage.tsx
 M webconsole/frontend/src/pages/ComposePage.tsx
 M webconsole/frontend/src/pages/ExperimentDetailPage.tsx
 M webconsole/frontend/src/pages/ExperimentsPage.tsx
 M webconsole/frontend/src/pages/PlatformPage.tsx
 M webconsole/frontend/src/pages/PromptSetsPage.tsx
 M webconsole/frontend/src/pages/RunDetailPage.tsx
 M webconsole/frontend/src/pages/RunsPage.tsx
 M webconsole/frontend/src/runview.ts
 M webconsole/frontend/src/styles/ui.css
 M webconsole/frontend/src/traceview.ts
 M webconsole/frontend/src/types.ts
 D webconsole/frontend/src/useFullTrace.ts
 D webconsole/frontend/src/useLiveRun.ts
 D webconsole/frontend/src/usePreflight.ts
 D webconsole/frontend/src/useServiceHealth.ts
 D webconsole/frontend/src/useSidebarCounts.ts
 D webconsole/frontend/src/useTarget.ts
 M webconsole/frontend/vite.config.ts
?? webconsole/backend/tests/test_artifacts_index.py
?? webconsole/backend/tests/test_artifacts_legacy_service.py
?? webconsole/backend/tests/test_conditions_catalog.py
?? webconsole/backend/tests/test_experiments_listing_fields.py
?? webconsole/backend/tests/test_metric_thresholds.py
?? webconsole/backend/tests/test_plugin_disabled_reason.py
?? webconsole/backend/tests/test_preflight_distribution_health.py
?? webconsole/backend/tests/test_prompt_set_diff.py
?? webconsole/backend/tests/test_run_comparison.py
?? webconsole/backend/tests/test_run_created_at.py
?? webconsole/backend/tests/test_runs_listing_server_side.py
?? webconsole/backend/tests/test_trace_filter.py
?? webconsole/backend/tests/test_trace_index.py
?? webconsole/frontend/src/__tests__/CamerasPage.preview-error.test.tsx
?? webconsole/frontend/src/__tests__/ComposePage.preflight.test.tsx
?? webconsole/frontend/src/__tests__/ExperimentQueries.final.test.tsx
?? webconsole/frontend/src/__tests__/RunDetailArtifacts.test.tsx
?? webconsole/frontend/src/__tests__/Shell.distribution.test.tsx
?? webconsole/frontend/src/__tests__/Shell.live.test.tsx
?? webconsole/frontend/src/__tests__/TraceQueries.final.test.tsx
?? webconsole/frontend/src/__tests__/api.endpoints.test.ts
?? webconsole/frontend/src/__tests__/charts/ActivityTimeline.test.tsx
?? webconsole/frontend/src/__tests__/contrato/corrida-viva.contrato.test.tsx
?? webconsole/frontend/src/__tests__/contrato/detalle-traza-evaluacion.contrato.test.tsx
?? webconsole/frontend/src/__tests__/contrato/experimentos-distribucion.contrato.test.tsx
?? webconsole/frontend/src/__tests__/contrato/nueva-corrida.contrato.test.tsx
?? webconsole/frontend/src/__tests__/contrato/soporte.tsx
?? webconsole/frontend/src/__tests__/queryClient.test.ts
?? webconsole/frontend/src/__tests__/ui/Select.field.test.tsx
?? webconsole/frontend/src/api/endpoints.ts
?? webconsole/frontend/src/api/index.ts
?? webconsole/frontend/src/api/keys.ts
?? webconsole/frontend/src/api/queries/cameras.ts
?? webconsole/frontend/src/api/queries/catalog.ts
?? webconsole/frontend/src/api/queries/clips.ts
?? webconsole/frontend/src/api/queries/experiments.ts
?? webconsole/frontend/src/api/queries/platform.ts
?? webconsole/frontend/src/api/queries/promptSets.ts
?? webconsole/frontend/src/api/queries/runs.ts
?? webconsole/frontend/src/api/queries/sidebar.ts
?? webconsole/frontend/src/api/queryClient.ts
?? webconsole/frontend/src/pages/NotFoundPage.tsx
?? webconsole/frontend/src/palette.ts
?? webconsole/frontend/src/test-utils.tsx
?? webconsole/tools/capture_console.mjs
?? webconsole/tools/capture_fixtures.mjs
?? webconsole/tools/seed_dev_data.py
```
