# Consola web: visibilidad read-only de runs two-node (Fase 2 EBE)

**Fecha:** 2026-07-06
**Repos afectados:** `e-ovrt_media-plane` (fixes de finalización/listado) + `e-ovrt_experimental-setup/webconsole` (badge de topología)
**Contexto previo:** [[project_webconsole]], [[project_ebe_docker_decision]], [[project_fase2_twonode_done]]

## 1. Problema

La Fase 2 de `media-plane` dockerizó el split EBE de dos nodos en `infra/twonode/`
(commit `b8f180b`, verificado 2026-07-06). Node A (edge) y Node B (GPU) son
contenedores batch — arrancan, corren un run fijo desde una config YAML montada, y
terminan. Ninguno expone HTTP.

La consola web (`webconsole/`) es cliente HTTP del servicio media-plane single-host
vía la costura `RunBackend` (`POST /api/runs`, `GET /api/runs/{id}`, WS de eventos).
Esa costura **no puede hablarle** a los contenedores two-node tal como existen hoy:
no hay servicio HTTP del lado two-node al cual apuntar.

La sección §4 de la Spec B original (`2026-07-01-webconsole-design.md`) asumía una
arquitectura EBE distinta a la construida: un servicio HTTP completo corriendo en
Nodo B que "hace la ingesta" él mismo. Lo que realmente se implementó es Node A
haciendo ingesta/normalización y sirviendo frames por ZeroMQ a Node B, que solo
infiere — sin superficie HTTP en ningún lado. Este documento reemplaza esa sección
para el caso two-node.

**Alcance decidido:** solo visibilidad read-only. La consola no lanza ni detiene runs
two-node (eso sigue siendo `docker compose up` manual en `infra/twonode/`); solo debe
mostrarlos en la lista de runs y en el detalle, igual que un run DBE, incluyendo
mientras están en curso.

## 2. Hallazgo clave: el mecanismo ya existe, a medias

El servicio media-plane (`service/run_manager.py`) ya hace *fallback a disco* para
cualquier `run_id` que no sea su propio run activo en memoria: escanea `runs_dir`
buscando subdirectorios con `summary.json`, sin importar qué proceso los escribió.
Como todas las instancias del fleet (`infra/platform/docker-compose.yml`) y
`infra/twonode/docker-compose*.yml` montan el **mismo** `e-ovrt_media-plane/runs/`
del host, un run two-node terminado *ya aparecería* en `GET /api/runs` de cualquier
instancia del fleet — si no fuera por dos huecos:

**Hueco A — el campo `status` no es del pipeline, es de `RunManager`.** En el camino
single-host, `RunManager._execute()`/`_finalize()` (no el pipeline ni
`RunArtifactWriter`) son quienes envuelven `execute_run()` en try/except, calculan
`status` (`succeeded`/`failed`/`stopped`) y **parchean** `summary.json` en disco
después de que el pipeline ya escribió el resto. `run_node_b()` (entrypoint
two-node, `runtime/two_node.py`) nunca pasa por `RunManager` — por eso su
`summary.json` nunca tiene `status`.

**Hueco B — un run two-node que falla no deja `summary.json` en absoluto.**
Verificado empíricamente 2026-07-06: al matar Node A a mitad de una corrida real,
`run_node_b()` propaga la excepción de timeout fuera de su único `try/finally`
(que solo cierra transporte/adapter/writer) — las líneas que escriben
`summary.json`/`run_manifest.json`/`run_provenance.json` viven *después* de ese
bloque y nunca se alcanzan. El directorio del run queda con `effective_config.yaml`
y artefactos parciales, pero sin ninguno de los tres archivos finales. El
disk-scan de `list_runs()`/`get()` exige `summary.json` para incluir un run — el
run fallido queda invisible hasta el próximo arranque del servicio, momento en
que `reconcile_orphan_runs()` (ver Hueco C) lo estampa como `interrupted` — un
estado semánticamente equivocado (`interrupted` = "el proceso del *servicio*
murió con este run activo") con un mensaje de error que no describe lo que pasó.

**Hueco C — `reconcile_orphan_runs()` no conoce la existencia de two-node.**
`service/app.py` invoca `reconcile_orphan_runs()` en el startup del servicio:
estampa `status: "interrupted"` / `stop_cause: "process_died"` en **cualquier**
directorio de `runs_dir` sin `summary.json`, asumiendo que solo el propio
servicio pudo haberlo creado. Con two-node compartiendo el mismo `runs/`, esa
suposición es falsa en los dos sentidos: (a) etiqueta mal a los runs two-node
genuinamente muertos (ver Hueco B), y (b) —el caso grave— si el servicio arranca
**mientras un run two-node está en vuelo**, le estampa `interrupted` a un run
que está corriendo perfectamente. No es un escenario exótico: el switch de
instancias del fleet desde la consola (`TargetManager.switch()`) para y arranca
contenedores del servicio como operación normal.

## 3. Diseño

Ningún componente nuevo. Dos fixes en `media-plane` + un agregado de UI en la
consola. Sin tocar `RunBackend`, `ComposeOrchestrator`, ni Docker desde la consola.

### 3.1 `runtime/two_node.py::run_node_b()` — finalización siempre completa

Reestructurar para garantizar la misma propiedad que `RunManager._finalize()` ya
garantiza en el camino single-host: **pase lo que pase, al salir del proceso deben
existir `summary.json` (con `status`/`error`), `run_manifest.json` y
`run_provenance.json`.**

- Envolver `adapter.load()` + `run_consumer_loop()` en un try/except que capture
  `status="succeeded"`/`error=None` en el camino feliz y `status="failed"`/
  `error=str(exc)` si algo lanza (incluyendo el `RuntimeError` de timeout de
  transporte ya verificado en el smoke de Fase 2).
- Mover `run_context.finish()` + `write_summary()` + `write_provenance()` +
  `write_manifest()` a un bloque que se ejecute en **ambos** casos (éxito o
  excepción) — hoy solo se ejecutan en el camino feliz.
- `write_summary()` sigue escribiendo el resto de las métricas igual que hoy y
  su firma no cambia; **después** de ese write, `run_node_b()` hace el mismo
  read-modify-write del archivo que hace `RunManager._finalize()`: relee
  `summary.json`, le agrega `status`/`error`, y lo reescribe con
  `atomic_write_json`.
- Tras escribir los artefactos, si hubo excepción, volver a propagarla (el
  proceso debe seguir terminando con exit code != 0 — el criterio de hardening
  de Fase 2 no cambia, solo se le suma que ahora además queda un `summary.json`
  legible).

### 3.2 `service/run_manager.py::list_runs()` / `get()` — runs en curso visibles

Hoy, un directorio sin `summary.json` se omite (`list_runs`) o dispara
`UnknownRunError` (`get`). Cambiar ambos: si el directorio existe (señal:
`effective_config.yaml` presente, que se escribe al arrancar cualquier run,
DBE o two-node) pero no hay `summary.json` todavía, incluirlo/devolverlo con
`status: "running"` en vez de omitirlo/fallar. Con el fix 3.1 aplicado, este
estado ahora es fiable: un run two-node que falla ya deja `summary.json` con
`status: "failed"`, así que "running" deja de significar "running o murió sin
avisar" y pasa a significar "genuinamente en curso" (salvo el límite del §4).

Este cambio es agnóstico de topología — beneficia por igual a cualquier run de
cualquier instancia del fleet cuyo directorio todavía no tenga summary, no solo
a two-node.

Además, la respuesta de `get()` distingue el run activo **propio** del servicio
de un run "running" externo con un campo booleano `live`: `true` solo para el
run activo en memoria de esa instancia (el único suscribible por WS), `false`
para los detectados por disk-scan. Sin este campo, el frontend no puede saber si
el WS de telemetría tiene sentido (ver 3.4).

### 3.3 `service/retention.py::reconcile_orphan_runs()` — respetar la propiedad

Regla de ownership: el servicio solo reconcilia runs que él mismo pudo haber
creado. Antes de estampar `interrupted`, leer `effective_config.yaml` del
directorio huérfano; si declara `topology.mode: two_node`, **saltearlo** (ese
run pertenece a un proceso `run_node_b`, no al servicio — puede estar
perfectamente vivo). Si `effective_config.yaml` falta o es ilegible, se
reconcilia como hoy (no hay forma de atribuirlo, y el comportamiento actual ya
es el fallback correcto para runs del propio servicio).

Consecuencia deliberada: un run two-node muerto por SIGKILL duro ya no es
reconciliado por nadie — queda `running` hasta limpieza manual (ver §4). Es el
trade-off correcto: preferimos un run muerto que se ve `running` (anomalía
visible y diagnosticable) a un run vivo estampado como `interrupted` (dato
falso escrito en disco que además confunde al operador y a `write_summary()`).

### 3.4 Frontend — badge de topología y guarda del WS

- **Badge**: `RunsPage.tsx`/`RunDetailPage.tsx`: cuando
  `summary.run_descriptor.topology` existe, mostrar un badge (`two-node` vs
  `single-host`) junto al estado. Mientras el run está `running` sin `summary`
  todavía, no se conoce la topología — no se muestra badge (aceptable, YAGNI).
- **Guarda del WS**: `RunDetailPage` hoy abre el stream WS cuando
  `status === 'running'`. Para un run externo (two-node), `stream.py` acepta,
  `subscribe()` falla con `UnknownRunError` (no es el run activo en memoria),
  manda `state: running` y cierra — y el `onclose` del frontend reconecta cada
  2s **para siempre**. Fix: abrir el WS solo cuando `status === 'running' &&
  live === true` (campo de 3.2). Para runs externos en curso, la página muestra
  el estado por el polling de `GET /api/runs/{id}` que ya existe, sin
  telemetría en vivo (consistente con el alcance §6). `stream.py` no cambia: su
  degradación actual (state + close) es correcta como defensa ante clientes que
  no respeten la guarda.

## 4. Límite conocido (no resuelto por esta spec)

Si el proceso de `node-b` recibe una señal que lo mata sin darle chance de correr
código Python (`SIGKILL` directo, OOM-kill del host, corte del propio host) —
distinto del caso ya cubierto en 3.1, donde el proceso sigue vivo y puede capturar
la excepción — no hay forma de que escriba `summary.json`. Con la regla de
ownership de 3.3, ningún proceso reconcilia ese directorio: el run queda
`"running"` colgado indefinidamente. Además, **no se puede borrar vía API ni
consola**: `DELETE /api/runs/{id}` rechaza con 409 cualquier run cuyo status sea
`running` (guarda correcta para runs vivos, que aquí bloquea también al colgado).
La limpieza es manual: `rm -rf runs/<run_id>` en el host. Esto no es un caso
nuevo introducido por two-node (una instancia del fleet muerta igual de
violentamente pierde su estado en memoria exactamente igual, y ahí lo repara
`reconcile_orphan_runs()` en el próximo arranque); resolverlo para two-node
requeriría un supervisor externo con heartbeat/TTL, sobredimensionado para el
alcance actual (proyecto académico, sin SLA). Se documenta como deuda aceptada,
no como bug de esta spec.

## 5. Testing

- **media-plane** (`tests/test_two_node.py`): caso éxito → `summary.json` con
  `status: "succeeded"`, `error: null`, y los tres archivos finales presentes;
  caso excepción simulada (mock de transporte que lanza) → `status: "failed"`,
  `error` con el mensaje, y los tres archivos finales **igual presentes**
  (antes: ausentes).
- **media-plane** (`tests/test_run_manager.py`): directorio sintético con
  `effective_config.yaml` y sin `summary.json` → `list_runs()`/`get()` lo
  reportan `status: "running"` con `live: false`; el run activo propio reporta
  `live: true`.
- **media-plane** (tests de retention): directorio huérfano con
  `effective_config.yaml` declarando `topology.mode: two_node` → `reconcile`
  NO lo estampa; huérfano single-host o sin effective_config → estampado
  `interrupted` como hoy.
- **webconsole frontend**: test de render del badge condicionado a
  `run_descriptor.topology` presente/ausente; test de que el WS NO se abre
  cuando `live` es `false` aunque el status sea `running`.
- **Smoke manual** (reutiliza los dos escenarios ya ejecutados en el smoke de
  Fase 2 de media-plane): correr `docker compose up` en `infra/twonode/` y
  observar la consola pasar de `running` a `succeeded`; repetir matando Node A a
  mitad de corrida y observar `running` → `failed` con el mensaje de timeout,
  sin intervención manual en ningún caso.

## 6. Fuera de alcance (explícito)

- Lanzar o detener runs two-node desde la consola (sigue siendo `docker compose`
  manual).
- Telemetría en vivo (eventos por WS) de runs two-node — solo estado final +
  métricas post-run, igual que hoy para cualquier run ya terminado.
- Resolver el límite del §4 (proceso matado sin chance de escribir).
- Cualquier cambio a `RunBackend`, `ComposeOrchestrator`/`TargetManager`, o al
  fleet de `infra/platform/` — quedan exactamente como están.
