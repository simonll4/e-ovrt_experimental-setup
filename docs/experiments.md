# Experimentos (manifiestos de corrida)

Un **manifiesto** declara un experimento ejecutable: qué fuente, qué modelo, qué prompts y con qué
mecánica de runtime. Viven en `experiments/`. El media-plane los consume con
`eovrt-media run --config <manifiesto>`.

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
| `yoloe_video.yaml` | yoloe/yoloe-26s | (video, stride 5) | cr01_cr02_v2_short | muestra con muestreo por stride |

## 3. Matriz BENCH v2 (`experiments/bench_v2/`)

12 manifiestos = **6 modelos × 2 splits** (val/test), todos sobre el set congelado
`cr01_cr02_bench_v2` (4 clases) y device `cuda`. Sirven para evaluar percepción contra el BENCH v2.

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
3. Validá sin correr:
   `cd ../e-ovrt_media-plane && eovrt-media validate-config --config ../e-ovrt_experimental-setup/experiments/<nombre>.yaml`.
4. (Opcional) agregá `experiment: {id: <id>}` para que la provenance del run lo registre en
   `summary.json` (`experiment_id`).

### Catálogos disponibles (en el media-plane)
- **Modelos** (`configs/models/`): `grounding-dino/{gdino-tiny,gdino-base}`,
  `mm-grounding-dino/*`, `yoloe/{yoloe-26s,-26m,-26l,-26x}`, `mock`.
- **Datasets** (`configs/datasets/`): `demo_v2`, `chv`, `bench_v2_val`, `bench_v2_test`,
  `video_sample`. (Apuntan a `../e-ovrt_datasets/...`; correr desde la raíz del media-plane.)
