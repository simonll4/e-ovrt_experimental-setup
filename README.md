# e-ovrt_experimental-setup

Home de la **declaración de experimentos** de la plataforma **E-OVRT-VDP** (Experimental
Open-Vocabulary Real-Time Video Detection Platform — detección asistiva de riesgos de seguridad en
obra). Contiene los *prompt sets* y los *manifiestos de corrida* que definen **qué se estudia**, y
que antes vivían dentro de `e-ovrt_media-plane/configs/`.

---

## 1. Idea del repo — por qué existe

Un **experimento** en esta plataforma no es solo una corrida del plano de medios: es la
configuración de *qué se mide* (prompts, modelo, dataset, umbrales) y —a futuro— de los planos de
control y alertas. Esa declaración es **transversal a la plataforma** y no pertenece a ningún plano
en particular.

Por eso se separa en este repo:

- **Este repo (`experimental-setup`)** = *qué se estudia*. Fuente canónica de prompt sets y
  manifiestos. Es declarativo: no ejecuta nada por sí mismo.
- **`e-ovrt_media-plane`** = *cómo corre el plano*. Conserva el **contrato** (schemas Pydantic,
  `PromptPlan`, adaptadores, binding) y las **capacidades** (catálogos `configs/models/` y
  `configs/datasets/`), que los manifiestos referencian por id.
- **`e-ovrt_datasets`** = los datos (imágenes/videos) que el media-plane consume.

**Principio rector:** el contrato lo define el consumidor (el media-plane); este repo produce
*instancias* que se conforman a él. Así el media-plane sigue siendo ejecutable y testeable de forma
self-contained, y este repo es la única fuente de verdad de los experimentos.

> Diseño completo: `e-ovrt_media-plane/docs/superpowers/specs/2026-06-27-experimental-setup-config-design.md`
> y el rediseño de la capa de prompts en `…/specs/2026-06-25-prompt-layer-design.md`.

## 2. Layout

```
prompts/                         # prompt sets — el vocabulario open-vocabulary del experimento
  cr01_cr02_v2_short.yaml         # congelado: 3 clases (person/helmet/vest)
  cr01_cr02_bench_v2.yaml         # congelado BENCH v2: 4 clases (+ bare_head)
  ppe_v2_descriptive.yaml         # NO congelado: fraseo descriptivo por backend (A/B)
experiments/                     # manifiestos de corrida (un experimento por archivo)
  mock.yaml  mock_chv.yaml         # smoke / dev (detector mock, sin pesos)
  gdino.yaml  yoloe.yaml  yoloe_video.yaml   # corridas de muestra DBE (single-host)
  bench_v2/                       # matriz de evaluación BENCH v2 (6 modelos × 2 splits = 12)
docs/
  prompt-sets.md                  # formato de prompt sets + los 3 sets actuales + cómo agregar
  experiments.md                  # formato de manifiesto + naming bench_v2 + cómo correr/agregar
README.md
```

- `webconsole/` — consola web (BFF FastAPI + SPA React), cliente del servicio media-plane. Ver `webconsole/README.md`.

Detalle profundo de cada pieza en [`docs/prompt-sets.md`](docs/prompt-sets.md) y
[`docs/experiments.md`](docs/experiments.md).

## 3. Cómo funciona — resolución de dos raíces

Un manifiesto compone tres referencias que se resuelven contra **dos raíces distintas** (lógica en
`e-ovrt_media-plane/src/eovrt_media/config/loader.py`):

| Referencia | Raíz | Cómo se descubre |
|---|---|---|
| `prompts.ref` | **raíz del experimento** (este repo) | sube desde el manifiesto hasta el dir que contiene `prompts/` |
| `model.ref` | **catálogo del plano** (`configs/models/`) | repo-relative del media-plane; override `--catalog-root` / `EOVRT_MEDIA_CATALOG_ROOT` |
| `source.ref` | **catálogo del plano** (`configs/datasets/`) | igual que `model.ref` |

Los campos inline en el manifiesto pisan los del catálogo (p.ej. `model: {ref: …, device: cuda}`).
El binding de detecciones a la clase canónica lo hace el adaptador del media-plane por construcción
(no hay heurísticos): cada detección sale con `label` (canónico) + `prompt_id` + `source_prompt` +
`strategy`/`condition_id`.

**Supuesto de disposición:** `e-ovrt_media-plane`, `e-ovrt_experimental-setup` y `e-ovrt_datasets`
viven como **repos hermanos** en el mismo directorio.

## 4. Quickstart

**El media-plane ya no es un CLI**: es un servicio HTTP/WS (`POST /api/runs` dispara una
corrida contra el modelo cargado al arrancar). La vía principal para componer, lanzar y
observar corridas es la **webconsole**; para evaluar/comparar/inspeccionar resultados se
usan las utilidades `eovrt_media.tools.*` del media-plane.

```bash
# 1) levantar el servicio media-plane (una vez, en su propia terminal)
cd ../e-ovrt_media-plane
source .venv/bin/activate
EOVRT_MODEL_REF=mock make serve          # uvicorn en :8080 (ver su CLAUDE.md para model refs reales)

# 2) levantar la webconsole (cliente del servicio) y componer/lanzar corridas desde ahí
cd ../e-ovrt_experimental-setup/webconsole
make install                             # primera vez: venv backend + npm install
make serve                               # build SPA + BFF en :8090
```

Desde la webconsole se elige el plugin de ingesta, el prompt set (`prompts/`) y los
parámetros de la corrida, se lanza, y se sigue el progreso en vivo. Ver
`webconsole/README.md` para el detalle de targets del Makefile.

Para evaluar/comparar/inspeccionar una corrida ya generada (sin pasar por la webconsole),
desde la raíz del media-plane:

```bash
cd ../e-ovrt_media-plane && source .venv/bin/activate

python -m eovrt_media.tools.evaluate --run runs/<run_id_generado>
python -m eovrt_media.tools.inspect_runs inspect runs/<run_id_generado>
python -m eovrt_media.tools.inspect_runs compare runs/
```

Las salidas (`detections.jsonl`, `summary.json`, `metrics.jsonl`, previews) se escriben en
`e-ovrt_media-plane/runs/<run_id>/`, **no** en este repo.

## 5. Qué hay desarrollado actualmente

**Prompt sets (3)** — ver [`docs/prompt-sets.md`](docs/prompt-sets.md):
- `cr01_cr02_v2_short` y `cr01_cr02_bench_v2`: **congelados** (reproducibilidad del BENCH), etiquetas
  cortas para canonical_v2.
- `ppe_v2_descriptive`: **no congelado**, con fraseo descriptivo por backend (GDINO sinónimos cortos,
  YOLOE nominales) para A/B contra los congelados.

**Experimentos** — ver [`docs/experiments.md`](docs/experiments.md):
- 3 corridas de muestra single-host (`gdino`, `yoloe`, `yoloe_video`) sobre CHV demo v2.
- 2 smoke con detector mock (`mock`, `mock_chv`).
- Matriz **`bench_v2/`**: 6 modelos (GDINO t/b, MM-GDINO t/b, YOLOE 26s/26l) × 2 splits (val/test)
  = 12 manifiestos, para evaluación contra el BENCH v2.

Estado validado (2026-06-30): corridas reales two-node con YOLOE-26s (1330 imgs) y GDINO-tiny,
0 errores, binding canónico correcto.

## 6. Agregar un experimento o un prompt set

- **Prompt set nuevo:** copiá un set existente en `prompts/`, ajustá `classes`/`phrasings`, y
  referencialo con `prompts.ref: <nombre>`. Formato y reglas en [`docs/prompt-sets.md`](docs/prompt-sets.md).
- **Experimento nuevo:** copiá un manifiesto de `experiments/`, ajustá `source.ref`/`model.ref`/
  `prompts.ref`. Convención de naming del bench y campos en [`docs/experiments.md`](docs/experiments.md).

## 7. Puntos de extensión (futuro)

Cuando existan los planos de **control** (reglas de riesgo) y **alertas** (umbrales/notificaciones),
el manifiesto los compondrá con el mismo patrón "ref por id" (`control_plane.ref`, `alerts.ref`),
resolviendo cada uno contra el catálogo de su plano. Hoy **no** existen y **no** se declaran (YAGNI).

## 8. Versionado

Se commitean prompt sets, manifiestos y documentación (texto). **No** se commitean salidas de
corridas (`runs/`, que viven en el media-plane). Los prompt sets congelados (`cr01_cr02_*`) **no se
modifican** — su byte-equivalencia garantiza la reproducibilidad del BENCH.
