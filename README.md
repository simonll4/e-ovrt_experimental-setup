# e-ovrt_experimental-setup

Home de la **declaración y preparación reproducible de experimentos** de la plataforma **E-OVRT-VDP** (Experimental
Open-Vocabulary Real-Time Video Detection Platform — detección asistiva de riesgos de seguridad en
obra). Contiene los *prompt sets* y los *manifiestos de corrida* que definen **qué se estudia**, y
que antes vivían dentro de `e-ovrt_media-plane/configs/`. El proceso de entrenamiento remoto se
encapsula en `finetuning/` con sus recetas, manifiestos y artefactos locales ignorados.

---

## 1. Idea del repo — por qué existe

Un **experimento** en esta plataforma no es solo una corrida del plano de medios: es la
configuración de *qué se mide* (prompts, modelo, dataset, umbrales) y —a futuro— de los planos de
control y alertas. Esa declaración es **transversal a la plataforma** y no pertenece a ningún plano
en particular.

Por eso se separa en este repo:

- **Este repo (`experimental-setup`)** = *qué se estudia*. Fuente canónica de prompt sets y
  manifiestos. El flujo habitual es declarativo; la excepción explícita es `finetuning/`, que
  contiene tooling reproducible para preparar y ejecutar entrenamientos experimentales.
- **`e-ovrt_media-plane`** = *cómo corre el plano*. Conserva el **contrato** (schemas Pydantic,
  `PromptPlan`, adaptadores, binding) y las **capacidades** (catálogos `configs/models/` y
  `configs/datasets/`), que los manifiestos referencian por id.
- **`e-ovrt_datasets`** = los datos (imágenes/videos) que el media-plane consume.

**Principio rector:** el contrato lo define el consumidor (el media-plane); este repo produce
*instancias* que se conforman a él. Así el media-plane sigue siendo ejecutable y testeable de forma
self-contained, y este repo es la única fuente de verdad de los experimentos.

> Diseño completo: `e-ovrt_media-plane/docs/_archive/superpowers/specs/2026-06-27-experimental-setup-config-design.md`
> y el rediseño de la capa de prompts en `…/specs/2026-06-25-prompt-layer-design.md`.

## 2. Layout

```
prompts/                         # prompt sets — el vocabulario open-vocabulary del experimento
  cr01_cr02_v2_short.yaml         # exploratory: 3 clases (person/helmet/vest)
  cr01_cr02_bench_v2.yaml         # exploratory BENCH v2: 4 clases (+ bare_head)
  eind_v1.yaml                    # frozen_pending_review: núcleo E-IND, deriva de v2_short
  _archive/                       # sets exploratorios sin manifiesto activo (ver README propio)
experiments/                     # manifiestos de corrida (un experimento por archivo o carpeta)
  mock.yaml  mock_chv.yaml         # smoke / dev (detector mock, sin pesos)
  gdino.yaml  yoloe.yaml  yoloe_video.yaml   # corridas de muestra DBE (single-host)
  bench_v2/                       # matriz de evaluación BENCH v2 (6 modelos × 2 splits = 12)
  <slug>/                         # tripletas experiment.manifest.v1 (media+control[+distribución])
                                   # — ver docs/experiments.md §2 bis
  _archive/                       # manifiestos archivados (ver README propio)
docs/
  prompt-strategy.md              # metodología, taxonomía de ejes, ciclo de vida y programa de estudios
  prompt-sets.md                  # formato de prompt sets + los sets actuales + cómo agregar
  experiments.md                  # formato de manifiesto + naming bench_v2 + cómo correr/agregar
infra/
  platform/                       # deploy integral de la plataforma (consola + fleet media-plane +
                                   # control + distribución + mosquitto). Fuente de verdad:
                                   # infra/platform/README.md.
  console/                        # Dockerfile de la consola — lo construye el compose de platform.
                                   # El compose standalone de 2026-07-05 quedó en infra/_archive/.
finetuning/                       # configs, scripts, Apptainer, Slurm y manifiestos de training
  weights/  data/payloads/  runs/ # artefactos locales pesados, ignorados por Git
tools/                           # orquestación y campañas (p.ej. talert_campaign, 2026-08-13)
tests/                           # suite transversal del repo (88 tests; corre en .venv, ver §3 bis)
results/                         # índices de resultados citables + evidence-runs/ (copia curada)
defensa/                         # renderer de videos de defensa (videos derivados gitignorados)
cameras/                         # presets RTSP/OAK-D — gitignorado (credenciales en claro)
requirements-dev.txt             # entorno canónico del repo (ver §3 bis)
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

## 3 bis. Entorno de desarrollo y tests (✎ 2026-08-15, cierra F-119.1)

Este repo **no es un paquete instalable** —es el dueño de la configuración experimental,
la orquestación, el fine-tuning y la webconsole—, así que no tiene `pyproject.toml`
propio. Su entorno se declara en **`requirements-dev.txt`**:

```bash
python3.11 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
```

**Python 3.11, no 3.14.** `e-ovrt_alert-distribution` declara
`requires-python = ">=3.11,<3.12"`; su código importa bien en 3.14, pero el pin es su
contrato y no se toca desde otro repo. **3.11 es el único denominador común** que
satisface a los tres hermanos a la vez, y por eso permite correr la suite entera en **un
solo intérprete** — que era justamente lo que faltaba:

```bash
.venv/bin/python -m pytest tests/                            #  88 passed
.venv/bin/python -m pytest finetuning/tests/                 #  46 passed
cd webconsole/backend && ../../.venv/bin/python -m pytest    # 643 passed
```

`requirements-dev.txt` instala **en editable**: `e-ovrt_alert-distribution` (extra
`mqtt`), `e-ovrt_control-plane` y el backend de la webconsole
(`./webconsole/backend[dev]`), más `pytest` y `Pillow` como dependencias directas de la
suite. El **media-plane NO se instala** en este venv: se consume como servicio HTTP y por
sus artefactos, no por import. Así la suite ejercita el código vivo de cada módulo
instalado, no una copia. Asume el layout de repos hermanos en disco (ver el `CLAUDE.md`
del workspace).

> **Por qué esto era un problema.** Los seis módulos `tests/test_talert_*` necesitan
> `eovrt_distribution` + `eovrt_control` + `httpx` + `paho` + `msgpack` **en el mismo
> entorno**, y ningún venv de los repos hermanos los tiene juntos. Hoy ese entorno es
> `.venv/`, el venv canónico del repo — declarado en `requirements-dev.txt` y
> reproducible; la campaña `t_alert` corre ahí, como el resto de la suite.

## 4. Quickstart

La plataforma son **tres servicios HTTP config-driven** (ADR-019): media-plane en `:8080`,
control-plane en `:8081` y distribución de alertas en `:8082`, más un **broker MQTT**
(mosquitto) para la entrega de alertas. La webconsole es cliente HTTP de los tres. La vía
principal para componer, lanzar y observar corridas es la **webconsole**; para
evaluar/comparar/inspeccionar resultados se usan las utilidades `eovrt_media.tools.*` del
media-plane.

**Camino integrado**: el compose de `infra/platform/` levanta la plataforma completa
(consola + fleet media-plane + control + distribución + mosquitto). Fuente de verdad:
`infra/platform/README.md`.

**Camino dev** (servicios por repo, cada uno en su terminal):

```bash
# 1) servicio media-plane (:8080)
cd ../e-ovrt_media-plane
source .venv/bin/activate
EOVRT_MODEL_REF=mock make serve          # uvicorn en :8080 (ver su CLAUDE.md para model refs reales)

# 2) servicio control-plane (:8081)
cd ../e-ovrt_control-plane
.venv/bin/eovrt-control serve --port 8081

# 3) servicio de distribución de alertas (:8082) — requiere un broker MQTT arriba
#    (mosquitto; la campaña t_alert usó amqtt 0.11.3 en 127.0.0.1:1883)
cd ../e-ovrt_alert-distribution
.venv/bin/eovrt-distribute serve --port 8082

# 4) webconsole (cliente de los tres) — componer/lanzar corridas desde ahí
cd ../e-ovrt_experimental-setup/webconsole
make install                             # primera vez: venv backend + npm install
make serve                               # build SPA + BFF en :8090
```

Desde la webconsole se elige el plugin de ingesta, el prompt set (`prompts/`) y los
parámetros de la corrida, se lanza, y se sigue el progreso en vivo. Ver
`webconsole/README.md` para el detalle de targets del Makefile y las env vars que apuntan
a cada servicio. Para corridas sólo de percepción (DBE, sin alertas) basta con el
media-plane + la webconsole.

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

**Prompt sets — catálogo activo (5)** — metodología, taxonomía de ejes y ciclo de vida en
[`docs/prompt-strategy.md`](docs/prompt-strategy.md); formato y detalle de cada set en
[`docs/prompt-sets.md`](docs/prompt-sets.md) §4 (actualizado 2026-07-29):
- **`cr01_cr02_v2_short`: `frozen`** (set del rodaje y del bench, `frozen_sha256` en el YAML).
- **`eind_v1` y `edir_v1`: `frozen`** desde 2026-07-29 por acta (`docs/operacion/76` del repo
  docs) — carril E-IND del núcleo y carril comparativo E-DIR (8 formulaciones por eje).
- `cr01_cr02_bench_v2` (evaluación BENCH) y `cr01_cr02_v2_safety_vest` (A/B del phrasing de
  vest, F-G2.1): `exploratory`.

4 candidatos exploratorios previos a `edir_v1` están archivados en `prompts/_archive/`
(ver su README) — fuera del catálogo. Los manifiestos de experimento viven en
`experiments/` (definiciones sueltas legacy + matriz `bench_v2/` + tripletas
`experiment.manifest.v1`; el conteo exacto lo da el catálogo de la consola).

**Experimentos** — ver [`docs/experiments.md`](docs/experiments.md) para la lista completa y
actualizada; resumen:
- Corridas de muestra single-host (`gdino`, `yoloe`, `yoloe_video`) sobre CHV demo v2.
- 2 smoke con detector mock (`mock`, `mock_chv`).
- 2 corridas sobre video local con salida de video anotado (`video_annotated` con YOLOE-26s,
  `video_annotated_gdino` con GDINO-tiny).
- Matriz **`bench_v2/`**: 6 modelos (GDINO t/b, MM-GDINO t/b, YOLOE 26s/26l) × 2 splits (val/test)
  = 12 manifiestos, para evaluación contra el BENCH v2.

Estado validado (2026-06-30): corridas reales two-node con YOLOE-26s (1330 imgs) y GDINO-tiny,
0 errores, binding canónico correcto.

## 6. Agregar un experimento o un prompt set

- **Prompt set nuevo:** copiá un set existente en `prompts/`, ajustá `classes`/`phrasings`, y
  referencialo con `prompts.ref: <nombre>`. Formato y reglas en [`docs/prompt-sets.md`](docs/prompt-sets.md).
- **Experimento nuevo:** copiá un manifiesto de `experiments/`, ajustá `source.ref`/`model.ref`/
  `prompts.ref`. Convención de naming del bench y campos en [`docs/experiments.md`](docs/experiments.md).

## 7. Fine-tuning

La jornada E-04 se organiza en [`finetuning/`](finetuning/README.md). Esa carpeta concentra
configuraciones, herramientas, recetas Apptainer, jobs Slurm, manifiestos y los pesos de trabajo.
Los datos canónicos siguen en `e-ovrt_datasets`; un peso sólo se copia al catálogo del media-plane
después del gate de integración. Plan y decisiones: `docs/operacion/116` y `117` del repo hermano.

## 8. Puntos de extensión

Los planos de **control** (reglas de riesgo, `:8081`) y de **distribución de alertas**
(`:8082`) **ya existen** como servicios HTTP config-driven (ADR-019), y este repo ya los
compone: 10 de los directorios de `experiments/` son tripletas `experiment.manifest.v1`
que declaran `runs.media` / `runs.control` (y, en la campaña `t_alert_notification`,
también `runs.distribution`) — ver `docs/experiments.md` §2 bis.

Los puntos de extensión de hoy son otros: dashboards/analítica sobre los índices de
`results/`, más canales de entrega en el distribuidor (además de MQTT QoS 1), y más
patrones de riesgo en el control-plane (hoy CR-01/CR-02, set `cr01_cr02_v2`).

## 9. Versionado

Se commitean prompt sets, manifiestos y documentación (texto). **No** se commitean los directorios
originales de corridas (`runs/`, que viven en los planos hermanos). La única excepción es el
archivo generado [`results/evidence-runs/`](results/evidence-runs/README.md): contiene solo la
copia textual curada de los runs citados por resultados DBE/EBE y excluye imágenes, video,
previews, presets y secretos. Su inventario canónico está en
[`results/evidence-runs.md`](results/evidence-runs.md). Los prompt sets congelados
(`cr01_cr02_*`) **no se modifican** — su byte-equivalencia garantiza la reproducibilidad del
BENCH. Bajo `finetuning/` tampoco se versionan pesos, payloads, imágenes Apptainer ni runs: se
versionan sus recetas, manifiestos, hashes y resúmenes curados.
