# Campaña de medición de `t_alert-notification` — Implementation Plan

> **Ejecución:** implementar cada tarea en orden y no iniciar una fase de medición mientras su
> gate anterior no esté verde. Este plan no autoriza commits; todos los cambios quedan sin
> commitear hasta indicación expresa del usuario.

**Goal:** Implementar el tooling reproducible, ejecutar la campaña híbrida aprobada y producir una
cifra citable de `t_alert-notification` basada exclusivamente en entregas live confirmadas por
PUBACK.

**Architecture:** Un CLI delgado en `e-ovrt_experimental-setup` selecciona el corpus canónico,
supervisa broker, distribuidor, publisher y suscriptor testigo, conserva cada intento en un árbol
ignorado y genera evidencia curada determinista. El camino cuantitativo republica `AlertEvent`
históricos mediante el `AlertBusPublisher` vigente; el camino integrado reutiliza el runner de la
webconsole para recorrer video/cámara -> media -> control -> distribución -> MQTT -> reporte.

**Tech stack:** Python 3.11, Pytest, PyYAML, pyzmq/msgpack, Paho MQTT 2.1.0, aMQTT 0.11.3,
subprocesos sin shell, servicios FastAPI existentes y artefactos JSON/JSONL/CSV/YAML/Markdown.

**Design:**
`docs/superpowers/specs/2026-08-13-campana-t-alert-notification-design.md`.

---

## Restricciones globales

- El workspace contiene repos Git hermanos; ejecutar Git con `git -C <repo>` o desde cada repo.
- Leer `README.md` y `CLAUDE.md` de cada repo antes de modificarlo.
- No crear commits, no borrar runs y no alterar cambios locales preexistentes.
- No modificar contratos productivos ni la semántica de `AlertBusPublisher`, `Distributor`,
  `NotificationPolicy`, `DeliveryRecord` o el runner.
- Todo output completo vive bajo `e-ovrt_experimental-setup/runs/t-alert-notification/`, ya
  ignorado por la regla `runs/`. Solo se versiona evidencia textual curada.
- La campaña oficial usa Python 3.11, `amqtt==0.11.3` y `paho-mqtt==2.1.0`.
- El broker oficial es aMQTT administrado por el CLI. Si `127.0.0.1:1883` está ocupado, abortar;
  nunca usar silenciosamente un broker ajeno.
- El publisher y el distribuidor se ejecutan uno por run. El broker y el suscriptor testigo pueden
  permanecer activos durante una serie completa.
- Cada intento oficial es inmutable. Si falla un gate, marcarlo `invalid`, conservarlo y crear un
  intento nuevo; no reanudar ni seleccionar solo las muestras favorables.
- Los 544 controles de decimado son suplementarios y nunca se mezclan con el agregado principal.
- Los tiempos `wall_clock_dbe` nunca entran en la cifra live.
- No persistir credenciales, URI RTSP, presets de cámara, imágenes, video, previews ni pesos.

## Línea de base congelada

El comando `inventory` debe rechazar drift respecto de esta matriz antes de medir:

| Serie | Runs copiados | Runs con alertas | Eventos |
|---|---:|---:|---:|
| DBE principal | 400 | 346 | 823 |
| EBE histórica no derivada | 13 | 10 | 13 |
| Decimado suplementario | 544 | 440 | 574 |
| **Total** | **957** | **796** | **1.410** |

Corpus live principal: 413 runs, 356 no vacíos y 836 eventos. Los 1.410 eventos deben validar
contra el contrato actual y tener `alert_id` único.

---

## Mapa de archivos

### Tooling de campaña

- Modify: `.gitignore` — ignorar `.venv-talert/`.
- Create: `tools/t_alert_notification_campaign.py` — CLI delgada.
- Create: `tools/talert_campaign/__init__.py`.
- Create: `tools/talert_campaign/model.py` — modelos, estados y errores.
- Create: `tools/talert_campaign/config.py` — carga estricta del manifiesto.
- Create: `tools/talert_campaign/corpus.py` — selección, validación y staging.
- Create: `tools/talert_campaign/processes.py` — supervisión segura de procesos.
- Create: `tools/talert_campaign/live_bus.py` — publisher y ciclo live por run.
- Create: `tools/talert_campaign/mqtt_witness.py` — readiness y evidencia independiente.
- Create: `tools/talert_campaign/workflows.py` — fases DBE/live/integradas.
- Create: `tools/talert_campaign/aggregate.py` — gates y estadística.
- Create: `tools/talert_campaign/render.py` — evidencia curada determinista.
- Create: `tools/talert_campaign/requirements.txt` — `amqtt==0.11.3` y
  `paho-mqtt==2.1.0`.

### Configuración y manifiestos

- Create: `experiments/t_alert_notification/campaign.yaml`.
- Create: `experiments/t_alert_notification/distribution-replay.yaml`.
- Create: `experiments/t_alert_notification/distribution-live.yaml`.
- Create: `experiments/t_alert_notification/video/manifest.template.yaml`.
- Create: `experiments/t_alert_notification/video/media.template.yaml`.
- Create: `experiments/t_alert_notification/video/control.template.yaml`.
- Create: `experiments/t_alert_notification/camera/manifest.template.yaml`.
- Create: `experiments/t_alert_notification/camera/control.template.yaml`.

### Pruebas

- Create: `tests/test_talert_config.py`.
- Create: `tests/test_talert_corpus.py`.
- Create: `tests/test_talert_processes.py`.
- Create: `tests/test_talert_live_bus.py`.
- Create: `tests/test_talert_mqtt.py`.
- Create: `tests/test_talert_workflows.py`.
- Create: `tests/test_talert_aggregate.py`.
- Create: `tests/test_talert_render.py`.
- Create: `tests/fixtures/talert/` — alertas sintéticas sin material sensible.

### Evidencia final

- Create after successful campaign: `results/realtime/t_alert_notification/README.md`.
- Create after successful campaign: `results/realtime/t_alert_notification/campaign.yaml`.
- Create after successful campaign: `results/realtime/t_alert_notification/corpus.json`.
- Create after successful campaign: `results/realtime/t_alert_notification/provenance.json`.
- Create after successful campaign: `results/realtime/t_alert_notification/metrics.json`.
- Create after successful campaign: `results/realtime/t_alert_notification/outcomes.csv`.
- Create after successful campaign: `results/realtime/t_alert_notification/integrated-runs.json`.
- Create after successful campaign: `results/realtime/t_alert_notification/camera-smoke.json`.
- Modify after successful campaign: `results/realtime/index.md`.
- Modify after successful campaign: `results/index.md`.
- Modify after successful campaign: `results/evidence-runs.yaml` y regenerar su archivo.
- Create after successful campaign: `docs/operacion/118-campana-t-alert-notification.md` en el
  repo hermano `docs`.

---

## Task 1: Congelar configuración, entorno y modelo de dominio

**Files:** `.gitignore`, `experiments/t_alert_notification/campaign.yaml`,
`tools/talert_campaign/{__init__,model,config}.py`, `tools/talert_campaign/requirements.txt`,
`tests/test_talert_config.py`.

**Interfaces:**

- `CampaignConfig.load(path: Path, repo_root: Path) -> CampaignConfig`.
- `AttemptState`, `CorpusRun`, `RunExecution`, `WitnessMessage`, `GateViolation`.
- Estados de intento: `prepared`, `running`, `succeeded`, `invalid`, `aborted`.

- [ ] **Step 1: escribir pruebas fallidas del manifiesto estricto**

Cubrir schema/version, endpoints loopback, QoS 1, versiones fijadas, conteos esperados, rutas
contenidas en el workspace, series `primary`/`supplemental` y rechazo de campos desconocidos.

- [ ] **Step 2: confirmar rojo**

Run: `python3 -m pytest tests/test_talert_config.py -q`  
Expected: FAIL por paquete inexistente.

- [ ] **Step 3: implementar el modelo y el manifiesto**

`campaign.yaml` debe declarar como mínimo:

```yaml
schema_version: talert_notification_campaign.v1
python: "3.11"
broker: {implementation: amqtt, version: "0.11.3", host: 127.0.0.1, port: 1883}
bus: {endpoint: "tcp://127.0.0.1:5558", subscriptions_expected: 2}
mqtt: {topic_prefix: eovrt/alerts, qos: 1}
policy: {cooldown_ms: 30000, key: [condition_id, source_id]}
corpus:
  resolved_runs: results/evidence-runs/resolved-runs.json
  expected: {copied_runs: 957, nonempty_runs: 796, events: 1410}
  primary: {runs: 413, nonempty_runs: 356, events: 836}
  supplemental: {runs: 544, nonempty_runs: 440, events: 574}
```

- [ ] **Step 4: preparar el entorno aislado sin tocar los venv de los planos**

Run:

```bash
python3.11 -m venv .venv-talert
.venv-talert/bin/pip install -r tools/talert_campaign/requirements.txt
.venv-talert/bin/pip install -e '../e-ovrt_control-plane[dev]' \
  -e '../e-ovrt_alert-distribution[mqtt,dev]' \
  -e webconsole/backend
```

Expected: los imports `amqtt`, `eovrt_control`, `eovrt_distribution`, `eovrt_webconsole`, `paho`
y `zmq` funcionan bajo `.venv-talert/bin/python`. Registrar las versiones con
`importlib.metadata.version`, sin depender de una opción `--version` de los CLI.

- [ ] **Step 5: verde y checkpoint**

Run:

```bash
python3 -m pytest tests/test_talert_config.py -q
git diff --check -- .gitignore experiments/t_alert_notification tools/talert_campaign tests/test_talert_config.py
```

Expected: PASS y salida vacía de `git diff --check`.

---

## Task 2: Resolver y validar el corpus canónico

**Files:** `tools/talert_campaign/corpus.py`, `tests/test_talert_corpus.py`,
`tests/fixtures/talert/`.

**Interfaces:**

- `load_corpus(config: CampaignConfig) -> tuple[CorpusRun, ...]`.
- `classify_run(resolved: dict) -> Literal["primary_dbe", "primary_ebe", "supplemental"]`.
- `stage_alerts(run: CorpusRun, temp_root: Path) -> Path`.
- `validate_alerts(path: Path) -> AlertFileStats`.

- [ ] **Step 1: pruebas fallidas de clasificación y seguridad**

Casos: `dbe_video`, `ebe_realtime` no derivado, rol `control_replay_empirico`, estado no copiado,
ruta que escapa del archivo, gzip corrupto, JSON inválido, contrato inválido, ID repetido y grupo
desconocido. Un grupo desconocido debe abortar, nunca caer por default en DBE.

- [ ] **Step 2: implementar selección determinista**

La única entrada es `results/evidence-runs/resolved-runs.json`. Conservar orden estable por
`(serie, run_id)`, exigir `alerts.jsonl.gz` y validar cada evento mediante
`NotificationEnvelope.from_alert`.

- [ ] **Step 3: staging temporal y limpieza recuperable**

Descomprimir a un `TemporaryDirectory` dentro del intento; nunca editar el archivo curado. Cerrar
file descriptors antes de lanzar el distribuidor y conservar SHA-256 del gzip y del JSONL plano.

- [ ] **Step 4: pruebas y auditoría real de solo lectura**

Run:

```bash
python3 -m pytest tests/test_talert_corpus.py -q
.venv-talert/bin/python tools/t_alert_notification_campaign.py inventory \
  --config experiments/t_alert_notification/campaign.yaml
```

Expected: matriz exacta 400/13/544, 1.410 eventos válidos y 1.410 IDs únicos; exit 0.

---

## Task 3: Intentos inmutables y supervisión segura de procesos

**Files:** `tools/talert_campaign/processes.py`, `tools/talert_campaign/model.py`,
`tests/test_talert_processes.py`.

**Interfaces:**

- `create_attempt(root: Path, attempt_id: str, hashes: dict) -> AttemptState`.
- `run_process(argv: Sequence[str], *, cwd: Path, timeout_s: float, log_dir: Path) -> ProcessResult`.
- `ManagedProcess.start(...)`, `wait_ready(...)`, `terminate_cooperatively(...)`.
- Escritura atómica de `attempt.json` y `events.jsonl`.

- [ ] **Step 1: pruebas fallidas**

Cubrir rechazo de intento existente, argumentos sin shell, timeout, captura separada de
stdout/stderr, exit code, terminación, path containment y redacción de variables cuyo nombre
contenga `PASSWORD`, `TOKEN`, `SECRET`, `CREDENTIAL` o `URI`.

- [ ] **Step 2: implementar supervisión**

Usar `asyncio.create_subprocess_exec` o `subprocess.Popen` con listas, nunca `shell=True`. Cada
proceso guarda comando redactado, PID, timestamps UTC, exit code y hashes de sus outputs.

- [ ] **Step 3: fingerprint previo al intento**

Registrar para los cinco repos: commit, branch y `git status --short`; además sistema operativo,
CPU/GPU, Python, `pip freeze --exclude-editable`, hashes de configs, diseño, plan y
`resolved-runs.json`. Un árbol dirty se registra, no se limpia ni se oculta.

- [ ] **Step 4: verificar**

Run: `python3 -m pytest tests/test_talert_processes.py -q`  
Expected: PASS; ningún test deja procesos hijos.

---

## Task 4: Publisher live y ciclo de un run por ZeroMQ

**Files:** `tools/talert_campaign/live_bus.py`, `tests/test_talert_live_bus.py`.

**Interfaces:**

- `publish_run(alerts: Iterable[dict], control_run_id: str, endpoint: str) -> PublishStats`.
- `run_live_distribution(run: CorpusRun, context: RunContext) -> RunExecution`.

- [ ] **Step 1: prueba de integración fallida con distribuidor real en `dry_run`**

El test inicia `eovrt-distribute live`, luego crea `AlertBusPublisher`, espera dos notificaciones
XPUB —topics de alertas y lifecycle—, publica dos alertas sintéticas y `run_finished`.

Assertions:

- `termination_reason == "run_finished"`;
- `source_stats.read == 2`;
- `bus_dropped_events == 0`;
- latencias agrupadas bajo `live`, aunque el canal del test sea `dry_run`;
- `control_run_id` y `experiment_id` preservados.

- [ ] **Step 2: implementar usando el publisher vigente**

Importar `AlertBusPublisher` desde `eovrt_control.transport.alert_bus`; no copiar el encoder. El
orden obligatorio por run es: distribuidor SUB -> publisher XPUB/bind -> readiness de dos
suscripciones -> eventos -> sentinel -> cierre -> espera del distribuidor.

- [ ] **Step 3: gates del publisher**

Rechazar readiness incompleta, `send_failures > 0`, exit no cero, summary ausente, run ID distinto,
timeout o terminación distinta de `run_finished`.

- [ ] **Step 4: verificar**

Run: `.venv-talert/bin/python -m pytest tests/test_talert_live_bus.py -q`  
Expected: PASS repetido tres veces sin puertos o procesos residuales.

---

## Task 5: Broker aMQTT y suscriptor testigo

**Files:** `tools/talert_campaign/mqtt_witness.py`, `tools/talert_campaign/workflows.py`,
`tests/test_talert_mqtt.py`.

**Interfaces:**

- `ManagedBroker.start(config_path: Path) -> ManagedBroker`.
- `MqttWitness.start(topic: str)`, `wait_subscribed()`, `wait_for_ids(ids)`, `snapshot()`.
- `WitnessMessage(notification_id, control_run_id, topic, qos, payload_bytes, received_at)`.

- [ ] **Step 1: tests unitarios del testigo**

Validar payload, ID ausente, JSON inválido, duplicados QoS 1, topic inesperado y espera acotada.

- [ ] **Step 2: administrar el broker exacto**

Antes de arrancar, comprobar que `127.0.0.1:1883` está libre. Lanzar
`.venv-talert/bin/amqtt -c infra/platform/mosquitto/amqtt.yaml`, esperar puerto y conexión MQTT,
y registrar versión/config. El CLI es dueño del proceso y lo cierra al terminar o fallar.

- [ ] **Step 3: smoke real de dos alertas**

Usar canal `live`, QoS 1 y cooldown deshabilitado solo en este fixture. Exigir dos PUBACK, dos IDs
observados al menos una vez y ningún ID inesperado. Los duplicados se cuentan, no invalidan por sí
solos.

- [ ] **Step 4: verificar**

Run: `.venv-talert/bin/python -m pytest tests/test_talert_mqtt.py -m integration -q`  
Expected: PASS; puerto 1883 libre después del test.

---

## Task 6: Fase A — workflow DBE e idempotencia

**Files:** `tools/talert_campaign/workflows.py`,
`experiments/t_alert_notification/distribution-replay.yaml`, `tests/test_talert_workflows.py`.

**Interfaces:**

- CLI: `preflight-dbe --attempt-id <id> [--sample RUN_ID ...]`.
- Output: `<attempt>/preflight-dbe/<run_id>/{pass-1,pass-2}/` y
  `<attempt>/preflight-dbe-summary.json`.

- [ ] **Step 1: tests con tres runs sintéticos**

Uno con dos entregas, uno con cooldown y uno vacío. La segunda pasada reutiliza el ledger de la
primera.

- [ ] **Step 2: implementar primera y segunda pasada**

Usar `distribution-replay.yaml` con canal `dry_run` y la misma policy 30 s de la campaña live. La
segunda pasada no debe producir ningún `delivered`; toda clave entregada en la primera debe aparecer
como `skipped_duplicate`. Las supresiones pueden volver a registrarse porque nunca fueron
entregadas.

- [ ] **Step 3: gates por run y globales**

- `read` igual a líneas válidas;
- `skipped_malformed == 0` y `skipped_invalid_alerts == 0`;
- todo outcome permitido y exhaustivo;
- ningún `live` en esta fase;
- runs vacíos con summary válido;
- totales 957/796/1.410.

- [ ] **Step 4: ensayo acotado**

Run:

```bash
.venv-talert/bin/python tools/t_alert_notification_campaign.py preflight-dbe \
  --config experiments/t_alert_notification/campaign.yaml \
  --attempt-id rehearsal-dbe \
  --sample control_ebe_p1_live_20260725T201020Z_8dc1c2 \
  --sample control_rt_s15_subject_a_p1_c08_20260805T040442Z
```

Expected: exit 0; evidencia bajo `runs/`, sin cambios en `results/`.

---

## Task 7: Fase B — workflow live principal y suplementario

**Files:** `tools/talert_campaign/workflows.py`,
`experiments/t_alert_notification/distribution-live.yaml`, `tests/test_talert_workflows.py`.

**Interfaces:**

- CLI: `run-live --attempt-id <id> --series primary|supplemental [--sample ...]`.
- Un `RunExecution` por run y `series-summary.json`.

- [ ] **Step 1: tests de paridad y fallos**

Casos: run con alertas, run vacío, cooldown, retry seguido de éxito, dead letter, drop de seq,
timeout, witness faltante, witness duplicado y publisher sin readiness.

- [ ] **Step 2: implementar serie secuencial**

Arrancar un broker y un witness por serie. Por cada run crear distribuidor, publisher, ledger y
out-dir nuevos. Publicar los eventos en su orden original y cerrar con sentinel. Esperar que el
testigo observe todas las entregas antes de pasar al run siguiente.

- [ ] **Step 3: comparación contra el preflight**

Si no hubo retry final fallido, los conteos finales `delivered`/`suppressed_cooldown` del live deben
coincidir por run con la primera pasada DBE. Esto prueba que cambiar la fuente y el canal no cambió
la policy.

- [ ] **Step 4: gates de aceptación**

- primary exacto 413/356/836;
- supplemental exacto 544/440/574;
- cero invalid/malformed, drops, timeouts y dead letters;
- todo `failed` intermedio termina en `delivered` y se conserva;
- todas las entregas tienen `latency_mode: live`, valor finito/no negativo y testigo;
- ningún `notification_id` inesperado en MQTT.

- [ ] **Step 5: rehearsal de tres clases**

Ejecutar una muestra DBE, una EBE histórica, una suplementaria y un run vacío. Expected: todos los
gates verdes y árbol de intento marcado `succeeded`.

---

## Task 8: Agregación, percentiles y evidencia curada

**Files:** `tools/talert_campaign/aggregate.py`, `tools/talert_campaign/render.py`,
`tests/test_talert_aggregate.py`, `tests/test_talert_render.py`.

**Interfaces:**

- `aggregate_attempt(attempt_dir: Path) -> CampaignMetrics`.
- `nearest_rank(values: Sequence[float], percentile: float) -> float`.
- CLI: `verify --attempt-id ...` y `render --attempt-id ... [--check]`.

- [ ] **Step 1: tests de percentiles y elegibilidad**

Probar p50/p95/p99 nearest-rank, un solo valor, runs vacíos, primera entrega, steady-state,
separación DBE/EBE, exclusión de `wall_clock_dbe`, retry y rechazo de NaN/negativos.

- [ ] **Step 2: generar `outcomes.csv` a nivel de record**

Columnas mínimas: serie, origen, run ID, alert ID, notification ID, índice de record, intento,
outcome, mode, latency mode, latencia, witness multiplicity, payload bytes y flag primera entrega.
Este CSV debe permitir recomputar todos los agregados sin abrir los runs completos.

- [ ] **Step 3: generar métricas principales y secundarias**

Primaria: todos los `delivered/live` del corpus principal, incluida la primera conexión por run.
Publicar count/min/media/p50/p95/p99/max. Secundaria: steady-state solo si declara cuántas muestras y
runs conserva. Sensibilidad DBE/EBE separada, nunca interpretada como ranking de orígenes.

- [ ] **Step 4: render determinista**

`render` escribe primero en temporal, verifica y publica atómicamente. `--check` no escribe y falla
ante cualquier diferencia. `provenance.json` no incluye secretos ni rutas absolutas innecesarias.

- [ ] **Step 5: verificar**

Run:

```bash
python3 -m pytest tests/test_talert_aggregate.py tests/test_talert_render.py -q
git diff --check -- tools/talert_campaign tests
```

Expected: PASS.

---

## Task 9: Fase C — manifiesto integrado desde video

**Files:** `experiments/t_alert_notification/video/*`,
`tools/talert_campaign/workflows.py`, `tests/test_talert_workflows.py`.

- [ ] **Step 1: templates portables y materialización ignorada**

Los templates usan `${EOVRT_WORKSPACE}` y nunca se ejecutan directamente. El CLI los materializa
bajo el intento, reemplaza el workspace validado y luego carga el manifiesto con
`ExperimentManifest`. El manifiesto declara media, control y distribución `live`.

Configuración congelada:

- modelo del servicio: `grounding-dino/gdino-tiny-560`;
- prompt set `cr01_cr02_v2_short`;
- `stride: 15`;
- `input.track_persons: true`;
- pattern set `cr01_cr02_v2_subject`;
- clip inicial `a_p1_c08`, con GT y source ID explícitos;
- distribución live sobre `:5558` y MQTT `:1883`.

- [ ] **Step 2: test de contrato del manifiesto**

Validar rutas, modos concordantes, bloque distribution y que el runner fuerce `alert_bus.enabled`
sin perder `track_persons`.

- [ ] **Step 3: implementar admisión determinista**

Ejecutar una admisión sobre `a_p1_c08`. Si no produce alerta, registrar el negativo y probar en
orden `a_p7_c02`, luego `a_p6_c01`. Elegido el primer clip con alerta, congelarlo antes de las tres
repeticiones. Nunca elegir por latencia.

- [ ] **Step 4: levantar servicios en terminales separadas**

Media:

```bash
cd ../e-ovrt_media-plane
source .venv/bin/activate
EOVRT_MODEL_REF=grounding-dino/gdino-tiny-560 make serve
```

Control:

```bash
cd ../e-ovrt_control-plane
source .venv/bin/activate
eovrt-control serve --host 127.0.0.1 --port 8081
```

Webconsole:

```bash
cd webconsole
make serve
```

- [ ] **Step 5: ejecutar admisión y tres repeticiones**

El comando `run-integrated-video` administra broker/testigo, hace POST del manifiesto inline al
runner, espera estado terminal y copia evidencia textual. Cada repetición debe producir al menos
una entrega, `run_finished`, cero drops, `distribution_summary` live y `report.json` con
`t_alert-notification: computed`.

Las latencias integradas se publican por separado; no se agregan al p95 principal.

---

## Task 10: Fase D — smoke con cámara sin EPP

**Files:** `experiments/t_alert_notification/camera/*`,
`tools/talert_campaign/workflows.py`, `tests/test_talert_workflows.py`.

- [ ] **Step 1: materialización segura desde cámara disponible**

El operador pasa un preset gitignored o el plugin/config por entrada local. El CLI genera el media
YAML dentro del intento, agrega prompts, warmup, límite de unidades y bus. La procedencia curada
conserva solo plugin, source ID y parámetros no sensibles; nunca URI ni credenciales.

- [ ] **Step 2: validar el protocolo**

- ambiente controlado;
- una persona visible sin casco ni chaleco;
- entrar en cuadro después de readiness;
- permanecer 15–20 s;
- ninguna actividad riesgosa ni afirmación de obra real.

- [ ] **Step 3: ejecutar un smoke**

El CLI administra broker/testigo y usa el runner integrado. Resultado positivo: al menos una alerta
con PUBACK, cero drops y cierre normal. Si no hay alerta, conservarlo como resultado negativo con
causa; no repetir hasta obtener un número favorable y no incorporarlo al p95 principal.

- [ ] **Step 4: sanitización obligatoria**

Antes de curar `camera-smoke.json`, escanear claves y valores sensibles y comprobar que no contiene
`rtsp://`, userinfo, IP/URI de preset ni paths a credenciales.

---

## Task 11: Rehearsal completo antes de la campaña oficial

- [ ] **Step 1: suites de tooling**

Run:

```bash
python3 -m pytest tests/test_talert_config.py tests/test_talert_corpus.py \
  tests/test_talert_processes.py tests/test_talert_aggregate.py tests/test_talert_render.py -q
.venv-talert/bin/python -m pytest tests/test_talert_live_bus.py \
  tests/test_talert_mqtt.py tests/test_talert_workflows.py -q
```

- [ ] **Step 2: suites de contratos participantes**

Run:

```bash
cd ../e-ovrt_alert-distribution && .venv/bin/pytest -q && .venv/bin/ruff check src tests
cd ../e-ovrt_control-plane && .venv/bin/pytest -q --ignore=tests/labs && .venv/bin/ruff check src tests
cd ../e-ovrt_experimental-setup/webconsole/backend && .venv/bin/pytest -q && .venv/bin/ruff check src tests
```

- [ ] **Step 3: integridad del archivo y rehearsal pequeño**

Run:

```bash
python3 tools/evidence_runs.py --check --archive-only
.venv-talert/bin/python tools/t_alert_notification_campaign.py rehearse \
  --config experiments/t_alert_notification/campaign.yaml \
  --attempt-id rehearsal-final
```

Expected: incluye run DBE, EBE, suplementario y vacío; broker/testigo real; todos los gates verdes.

- [ ] **Step 4: decidir GO/NO-GO**

Solo GO si suites, archive-only, limpieza de procesos/puertos y rehearsal están verdes. Registrar el
resultado; no ejecutar la campaña oficial con una salvedad abierta.

---

## Task 12: Ejecutar la campaña oficial paso a paso

- [ ] **Step 1: crear intento y congelar hashes**

Run:

```bash
.venv-talert/bin/python tools/t_alert_notification_campaign.py prepare \
  --config experiments/t_alert_notification/campaign.yaml \
  --attempt-id official-20260813-01
```

Expected: intento nuevo `prepared`, corpus y entorno coinciden con la línea de base.

- [ ] **Step 2: Fase A completa**

Run:

```bash
.venv-talert/bin/python tools/t_alert_notification_campaign.py preflight-dbe \
  --config experiments/t_alert_notification/campaign.yaml \
  --attempt-id official-20260813-01
```

Gate: 957 runs, 1.410 eventos, cero inválidos y cero reentregas en segunda pasada.

- [ ] **Step 3: Fase B principal**

Run:

```bash
.venv-talert/bin/python tools/t_alert_notification_campaign.py run-live \
  --config experiments/t_alert_notification/campaign.yaml \
  --attempt-id official-20260813-01 --series primary
```

Gate: 413 runs/836 eventos, todos por sentinel, cero drops/dead letters/timeouts y correspondencia
completa con witness.

- [ ] **Step 4: Fase B suplementaria**

Run análogo con `--series supplemental`. Gate: 544 runs/574 eventos, rotulados como derivados y
fuera del agregado principal.

- [ ] **Step 5: verificar y calcular candidato primario**

Run: `... t_alert_notification_campaign.py verify --attempt-id official-20260813-01`  
Expected: cifra candidata con count/min/media/p50/p95/p99/max, todavía no publicada.

- [ ] **Step 6: Fase C integrada**

Con servicios listos, ejecutar admisión y tres repeticiones. Gate: tres reportes `computed` y
entregas live observadas.

- [ ] **Step 7: Fase D cámara**

Ejecutar una vez siguiendo el protocolo; guardar resultado positivo o negativo con causa.

- [ ] **Step 8: cierre del intento**

Si todo gate obligatorio está verde, marcar `succeeded`. Si falla uno, marcar `invalid`, no renderizar
en `results/` y abrir un intento nuevo después del diagnóstico.

---

## Task 13: Publicar evidencia curada y actualizar fuentes canónicas

**Repos:** `e-ovrt_experimental-setup` y `docs`.

- [ ] **Step 1: render atómico del resultado**

Run:

```bash
.venv-talert/bin/python tools/t_alert_notification_campaign.py render \
  --attempt-id official-20260813-01
.venv-talert/bin/python tools/t_alert_notification_campaign.py render \
  --attempt-id official-20260813-01 --check
```

Expected: los ocho artefactos de `results/realtime/t_alert_notification/`, sin datos sensibles y
con métricas recomputables desde `outcomes.csv`.

- [ ] **Step 2: actualizar índices sin sobreinterpretar**

Agregar a `results/realtime/index.md` la definición exacta bus -> PUBACK, cifra principal,
condiciones, n, broker y separación de video/cámara. Actualizar `results/index.md` solo con el
hallazgo consolidado. No llamar sensor -> notificación a una métrica que empieza en el bus.

- [ ] **Step 3: incorporar nuevos runs integrados al archivo canónico**

Agregar los media/control run IDs de las tres repeticiones y del smoke de cámara —si es evidencia
usable— a `results/evidence-runs.yaml`; después ejecutar:

```bash
python3 tools/evidence_runs.py sync
python3 tools/evidence_runs.py --check
python3 tools/evidence_runs.py --check --archive-only
```

No agregar como nuevos control runs las 413 republicaciones: reutilizan AlertEvents ya archivados y
su evidencia de distribución vive en `outcomes.csv`.

- [ ] **Step 4: registro operativo 118**

Crear `docs/operacion/118-campana-t-alert-notification.md` con objetivo, comandos, intento aceptado,
gates, cifra, caveats y links al resultado canónico. No duplicar todos los artefactos.

- [ ] **Step 5: regenerar contexto derivado del informe si corresponde**

Actualizar primero las fuentes canónicas y luego usar el generador del project-kit; nunca editar a
mano archivos derivados. Ejecutar sus checks y pruebas según las instrucciones del repo `docs`.

- [ ] **Step 6: verificación final multi-repo**

Run:

```bash
git -C ../e-ovrt_experimental-setup diff --check
git -C ../docs diff --check
python3 tools/evidence_runs.py --check --archive-only
.venv-talert/bin/python tools/t_alert_notification_campaign.py render \
  --attempt-id official-20260813-01 --check
```

Además, repetir suites afectadas de experimental-setup/webconsole y los validadores de índices de
`docs`. Expected: todo verde y ningún archivo sensible/untracked fuera de los paths previstos.

---

## Condición de terminado

El trabajo queda terminado solo si:

1. existe un intento oficial `succeeded` e inmutable;
2. el p95 principal se recompone desde records `delivered/live` testificados por MQTT;
3. no contiene `wall_clock_dbe`, runs derivados ni muestras integradas/cámara;
4. los 413 runs principales y sus 836 eventos tienen destino explícito;
5. tres corridas integradas generan `report.json` con la métrica `computed`;
6. el smoke de cámara está documentado como suplementario;
7. la evidencia curada pasa `render --check`, archive-only y los validadores documentales;
8. no se creó ningún commit ni se alteraron cambios previos del usuario.
