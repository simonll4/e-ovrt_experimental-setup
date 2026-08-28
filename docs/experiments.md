# Experimentos (manifiestos de corrida)

Un **manifiesto** declara un experimento ejecutable: qué fuente, qué modelo, qué prompts y con qué
mecánica de runtime. Viven en `experiments/`. El media-plane ya no es un CLI: los manifiestos se
componen y lanzan desde la **webconsole**, o directamente vía `POST /api/runs` contra el servicio
media-plane (ver §4).

## 1. Formato

```yaml
run:
  scenario: DBE | EBE          # DBE = un host; EBE = dos nodos (edge + GPU)
  name: <nombre_corrida>
  description: "..."
  # max_units: 50              # opcional: acota el nº de unidades (útil para smoke)
experiment:                    # opcional — provenance; se serializa a summary.json
  id: <id_experimento>
source:
  ref: <dataset>               # → e-ovrt_media-plane/configs/datasets/<dataset>.yaml
model:
  ref: <familia>/<variante>    # → e-ovrt_media-plane/configs/models/<...>.yaml
  device: cuda                 # override inline (pisa el catálogo)
prompts:
  ref: <prompt_set>            # → e-ovrt_experimental-setup/prompts/<prompt_set>.yaml
  active_ids: [person, helmet, vest, bare_head]
# Mecánica de runtime del media-plane (inline, opcional): topology, transport,
# rate_control, postprocess, outputs, logging, debug.
```

Solo `run`, `source`, `model`, `prompts` son obligatorios; el resto toma defaults del media-plane.
`model.ref` y `source.ref` resuelven contra el catálogo del plano; `prompts.ref` contra este repo
(ver §3 del README). Los campos inline pisan los del catálogo.

## 2. Experimentos de muestra (single-host, `experiments/`)

| Manifiesto | Modelo | Dataset | Prompts | Uso |
|---|---|---|---|---|
| `mock.yaml` | mock | demo_v2 | cr01_cr02_v2_short | smoke sin pesos (valida el pipeline) |
| `mock_chv.yaml` | mock | chv | cr01_cr02_v2_short | smoke sobre CHV completo |
| `gdino.yaml` | grounding-dino/gdino-tiny | demo_v2 | cr01_cr02_v2_short | muestra GDINO (CPU) |
| `yoloe.yaml` | yoloe/yoloe-26s | demo_v2 | cr01_cr02_v2_short | muestra YOLOE |
| `yoloe_video.yaml` | yoloe/yoloe-26s | demo_v2 (stride 5) | cr01_cr02_v2_short | muestra con muestreo por stride |
| `video_annotated.yaml` | yoloe/yoloe-26s | video_sample (stride 3) | cr01_cr02_v2_short | DBE sobre video local (`recorte-1.mp4`) con salida de video anotado |
| `video_annotated_gdino.yaml` | grounding-dino/gdino-tiny (cuda) | video_sample (stride 3) | cr01_cr02_v2_short | DBE sobre video local (`recorte-1.mp4`) con GDINO-tiny y salida de video anotado |

Además de estos manifiestos sueltos, la mayor parte de los directorios de `experiments/`
son **tripletas `experiment.manifest.v1`** que componen varios servicios — ver §2 bis.

> `realt-time-safety_vest.yaml` (formato viejo de un solo plano, IP de cámara hardcodeada)
> fue archivado el 2026-08-19 en `experiments/_archive/`.

## 2 bis. Tripletas `experiment.manifest.v1` (multi-servicio)

10 de los 11 directorios de `experiments/` usan el formato **`experiment.manifest.v1`**
(ADR-004 / spec 44 §2): un manifiesto "paraguas" que compone los servicios de la corrida
— el único que no lo usa es `bench_v2/` (manifiestos planos de catálogo, §3).

```yaml
schema_version: experiment.manifest.v1
slug: <slug>                     # = nombre del directorio
experiment_id: <id> | null       # provenance opcional
runs:
  media:
    service: media-plane
    config: /ruta/absoluta/al/media.yaml      # payload de run (ingesta + prompts inline + run)
    mode: run                                  # el runner hace POST /api/runs al servicio
  control:
    service: control-plane
    config: /ruta/absoluta/al/control.yaml
    mode: live                                 # consume el bus de detecciones (:5557)
  distribution:                  # opcional — sólo la campaña t_alert_notification lo declara
    service: alert-distribution
    config: /ruta/absoluta/a/distribution-live.yaml
    mode: live                                 # consume el bus de alertas (:5558)
    endpoint: tcp://127.0.0.1:5558
    idle_timeout_ms: 30000
sequencing: control_first
report: {}                       # se completa al cerrar la corrida
frozen: {}
clip_id: <clip> | null           # provenance de GT temporal (opcional)
ground_truth: <ruta> | null
derives_from: <slug origen>      # linaje entre experimentos (opcional)
changes: "<qué cambia respecto del origen>"
```

Reglas del formato, verificadas contra los manifiestos reales:

- **Rutas absolutas** en `runs.*.config` (ADR-009): los servicios reciben el payload por
  referencia de archivo, sin supuestos de CWD.
- **`mode`**: `run` = disparo de una corrida del media-plane (`POST /api/runs`);
  `live` = el servicio consume su bus ZeroMQ en vivo; `replay` = camino offline (relee
  artefactos JSONL, p.ej. `distribution-replay.yaml` de la campaña t_alert).
- **`sequencing: control_first` NO es opcional**: PUB/SUB pierde todo lo publicado antes
  de la suscripción. El runner dispara primero los consumidores (si hay distribución,
  primero `POST :8082/api/runs`; después el control con `mode: live`, cuyo OK implica
  `subscribed=True`) y **recién al final** el media con `bus.enabled: true`.
  ✎ **2026-08-28 (`docs/operacion/130`, R-01): el paréntesis anterior está vencido.** El
  orden que ejecuta el runner (`runner.py:1095-1149`) es **control → distribución →
  media**: primero el control con `mode: live`, `alert_bus.enabled: true` y
  `wait_for_subscriber_ms ≥ 10 s`; después la distribución (`POST :8082/api/runs`, que
  necesita el `control_run_id` recién creado); al final el media. La no-pérdida de alertas
  en `:5558` la garantiza el handshake XPUB del publicador (el control espera al suscriptor
  antes de publicar), no la secuencia literal. Lo invariante es "control antes que media"
  (bus de detecciones `:5557`).
- **Dos buses ZeroMQ**: detecciones en `:5557` (media XPUB → control SUB) y alertas en
  `:5558` (control XPUB → distribución SUB). Ojo: `alert_bus.enabled` del control-plane
  es `False` por default — sin habilitarlo, la distribución lee 0 alertas.
- **El runner inyecta solo** `control.input: {type: bus}` y `media.bus: {enabled: true}`
  — no declararlos en los payloads.
- El `media.yaml` de una tripleta es un **payload de run** (plugin de ingesta, prompt set
  inline, `run`), no un manifiesto de catálogo: el **modelo** es el que cargó la instancia
  del servicio media-plane (`EOVRT_MODEL_REF`), no se declara en el payload.

### Inventario de tripletas

| Directorio | Compone | Propósito |
|---|---|---|
| `ebe_oakd_live/` | media + control | corrida EBE live 1:1 con la OAK-D — base de la familia (las demás derivan de ella) |
| `ebe_p1_live/` | media + control | P1 toma B live — CR-01, 14 s sin casco |
| `ebe_p2_live/` | media + control | P2 toma B live — CR-02, 22 s sin chaleco fuera de cuadro |
| `ebe_p3_live/` | media + control | P3 toma B live — transitorio 2 s, NO debe alertar |
| `yoloe_p1_live/` … `yoloe_p3_live/` | media + control | mismas tomas P1–P3 con yoloe-26x (comparación vs gdino-tiny-560) |
| `rt-01/` | media + control | variante de `cr01_cr02_v2_short` con un solo cambio de phrasing, sobre la toma live |
| `diag_riesgo_activo/` | media + control | DIAGNÓSTICO (no es material de tesis): verifica el bloque `patterns` de `/api/runs/current` con el clip P1 grabado |
| `t_alert_notification/` | media + control + **distribución** | campaña `t_alert` (2026-08-13): templates `video/` y `camera/` + `campaign.yaml` (broker MQTT amqtt 0.11.3, QoS 1, bus `:5558`) |

## 3. Matriz BENCH v2 (`experiments/bench_v2/`)

12 manifiestos = **6 modelos × 2 splits** (val/test), todos sobre el set congelado
`cr01_cr02_bench_v2` (4 clases) y device `cuda`. Sirven para evaluar percepción contra el BENCH v2.
✎ 2026-08-28: `cr01_cr02_bench_v2` tiene `status: exploratory` en su YAML — **no está
congelado**; y los 4 manifiestos `b2_g_e{5,6}_mmgdino_*` ya no resuelven (MM-GDINO archivado
en el media-plane el 2026-08-19). Esta matriz es **registro histórico** del Sprint 2, no una
matriz ejecutable hoy (`docs/operacion/130`).

### Convención de naming

```
b2_<arch>_e<N>_<modelo>_<split>.yaml
└┬┘ └─┬─┘ └┬┘ └──┬──┘ └─┬─┘
 │    │    │     │      └ split:  val | test
 │    │    │     └ token de modelo: gdino_t/gdino_b, mmgdino_t/mmgdino_b, yoloe_26s/yoloe_26l
 │    │    └ experimento: e1..e6 (un nº estable por modelo)
 │    └ familia: g = grounding (GDINO/MM-GDINO), y = YOLOE
 └ b2 = BENCH v2
```

| Exp | Modelo (`model.ref`) | Manifiestos |
|---|---|---|
| E1 | grounding-dino/gdino-tiny | `b2_g_e1_gdino_t_{val,test}` |
| E2 | grounding-dino/gdino-base | `b2_g_e2_gdino_b_{val,test}` |
| E3 | yoloe/yoloe-26l | `b2_y_e3_yoloe_26l_{val,test}` |
| E4 | yoloe/yoloe-26s | `b2_y_e4_yoloe_26s_{val,test}` |
| E5 | mm-grounding-dino/…-tiny | `b2_g_e5_mmgdino_t_{val,test}` |
| E6 | mm-grounding-dino/…-base | `b2_g_e6_mmgdino_b_{val,test}` |

> Las familias GDINO y MM-GDINO comparten el adaptador `grounding_dino` del media-plane (backend de
> prompts `gdino`); YOLOE usa su propio adaptador (backend `yoloe`). El BENCH v2 total son 196 imgs
> repartidas en val/test (el split `test` ≈ 82 imgs según la descripción de los manifiestos); los
> tamaños exactos los define el repo `e-ovrt_datasets`.

## 4. Correr y evaluar

El media-plane ya no es un CLI: es un servicio HTTP/WS de un run activo (`POST /api/runs`).
La vía principal para correr un manifiesto (incluida la matriz BENCH v2) es la
**webconsole**, que lo compone y lanza contra el servicio; para evaluar/comparar corridas
ya generadas se usan las utilidades `eovrt_media.tools.*` desde el media-plane.

```bash
# 1) servicio media-plane (una terminal, una vez)
cd ../e-ovrt_media-plane && source .venv/bin/activate
EOVRT_MODEL_REF=<model_ref> make serve          # p.ej. grounding-dino/gdino-tiny, yoloe/yoloe-26s

# 2) webconsole (otra terminal): compone el manifiesto y lanza la corrida → runs/<run_id>/
cd ../e-ovrt_experimental-setup/webconsole && make serve
```

```bash
# 3) evaluar la percepción contra el BENCH (AP@0.5 por clase, recall CR-01)
cd ../e-ovrt_media-plane && source .venv/bin/activate
python -m eovrt_media.tools.evaluate --run runs/<run_id_generado>

# comparar varias corridas
python -m eovrt_media.tools.inspect_runs compare runs/
```

La evaluación detallada (NMS-AP, hard negatives) vive en el repo `e-ovrt_datasets`
(`evaluate_bench.py`); este repo y el media-plane solo emiten provenance trazable.

### Topología dos nodos (EBE)
La topología distribuida edge+GPU se invoca en proceso (`runtime/two_node.py:run_node_a()`/
`run_node_b()`), no vía CLI ni desde la webconsole (que en Fase 1 solo apunta a una
instancia local de un solo nodo del servicio). Ver `e-ovrt_media-plane/CLAUDE.md` — la ruta
`run_two_node_local` de `debug_run` no funciona post-eliminación del CLI; queda pendiente de
decisión en Fase 2 (docker-compose de dos nodos).

## 5. Agregar un experimento

1. Copiá un manifiesto existente a `experiments/<nombre>.yaml` (o `experiments/bench_v2/` siguiendo
   el naming).
2. Ajustá `source.ref` (debe existir en `configs/datasets/` del media-plane), `model.ref` (en
   `configs/models/`) y `prompts.ref` (en `prompts/` de este repo) + `active_ids`.
3. No hay validación standalone por CLI: el servicio media-plane valida el manifiesto al
   lanzarlo (`POST /api/runs` rechaza con `422` si es inválido), tanto si lo componés desde
   la webconsole como si lo mandás directo contra el servicio.
4. (Opcional) agregá `experiment: {id: <id>}` para que la provenance del run lo registre en
   `summary.json` (`experiment_id`).

### Catálogos disponibles (en el media-plane)
- **Modelos** (`configs/models/`): `grounding-dino/{gdino-tiny,gdino-base}`,
  `mm-grounding-dino/*`, `yoloe/{yoloe-26s,-26m,-26l,-26x}`, `mock`.
- **Datasets** (`configs/datasets/`): `demo_v2`, `chv`, `bench_v2_val`, `bench_v2_test`,
  `video_sample`. (Apuntan a `../e-ovrt_datasets/...`; correr desde la raíz del media-plane.)

> ✎ **2026-08-28 — catálogo vigente vs manifiestos huérfanos (`docs/operacion/130`).**
> Hoy el media-plane tiene en `configs/models/` `grounding-dino/{gdino-tiny,gdino-base,
> gdino-tiny-560,gdino-base-560}`, `yoloe/*` y `mock`; **`mm-grounding-dino/*` está
> archivado** (`configs/_archive/`, 2026-08-19). En `configs/datasets/` sólo quedan
> `bench_v2_test`, `bench_v2_val` y `demo_v2`: **`chv` y `video_sample` ya no existen**.
> Por eso los manifiestos `experiments/mock_chv.yaml` (`source.ref: chv`),
> `experiments/video_annotated.yaml` y `video_annotated_gdino.yaml` (`video_sample`) y los
> 4 `experiments/bench_v2/b2_g_e{5,6}_mmgdino_*.yaml` **no resuelven contra el catálogo**:
> son registro histórico de sus corridas, no manifiestos ejecutables.
