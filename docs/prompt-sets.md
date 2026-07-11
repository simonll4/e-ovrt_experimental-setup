# Prompt sets

Un **prompt set** declara el vocabulario open-vocabulary de un experimento: las **clases** a detectar
y, por cada clase, el **fraseo por backend** que se le alimenta al modelo. Viven en `prompts/`.

## 1. Por qué fraseo por backend

Las dos familias de detectores open-vocabulary procesan los prompts distinto, y rinden mejor con
fraseos distintos:

- **GDINO / MM-GDINO** (grounding por *caption*): se les arma un caption `"hard hat. safety vest. person."`
  y hacen matching de sub-spans. Admiten frases descriptivas y sinónimos, pero son **sensibles a la
  longitud del caption** (captions largos diluyen el grounding).
- **YOLOE** (embedding de texto tipo CLIP): `set_classes([...])` tokeniza y calcula *prompt embeddings*;
  rinden mejor con **etiquetas cortas/nominales**. El `class_id` devuelto es el índice en la lista.

Por eso una clase declara `phrasings` por backend: el mismo experimento sirve óptimamente a ambas
arquitecturas sin duplicar archivos.

## 2. Formato

```yaml
prompt_set:
  id: <nombre>                  # == nombre de archivo (sin .yaml); lo referencia prompts.ref
  description: "..."
  language: en
  classes:
    - id: helmet                # identidad estable del prompt → Detection.prompt_id
      canonical: helmet         # clase de evaluación (canonical_v2); opcional, default = id
      role: ppe                 # metadato semántico (entity | ppe | visual_risk_indicator)
      strategy: positive_evidence   # metadato/provenance opcional (etiqueta, no lógica)
      condition_id: CR-01       # metadato/provenance opcional (trazabilidad de riesgo)
      enabled_by_default: true  # si entra cuando active_ids no lo lista explícitamente
      phrasings:                # dict backend → lista de frases
        default: ["helmet"]      #   fallback para cualquier backend sin entrada propia
        gdino:   ["hard hat", "safety helmet"]   # sinónimos descriptivos cortos
        yoloe:   ["helmet"]      #   nominal corto (varias frases = ensembling)
```

### Reglas de resolución
- `id`: único en el set. Se propaga a `Detection.prompt_id`.
- `canonical`: clase del vocabulario de evaluación (canonical_v2: `person`/`helmet`/`vest`/`bare_head`).
  Default = `id`. Se propaga a `Detection.label`. **Alinea las detecciones con el BENCH de forma
  determinista** (binding por construcción, sin heurísticos).
- `phrasings`: cadena de fallback `phrasings[backend]` → `phrasings["default"]`. Si falta toda entrada
  para una clase activa, es **error de validación**. Una entrada presente pero **vacía** (`gdino: []`)
  también es error (no cae silenciosamente a `default`).
- `strategy` / `condition_id`: **solo provenance** — se propagan a `detections.jsonl` pero el
  media-plane **no** ramifica lógica sobre ellos (eso es del plano de control). `strategy` etiqueta la
  estrategia de fraseo (`positive_evidence`, `direct_absence`, …); `condition_id` traza a CR-01..06.

## 3. Cómo se consumen (en el media-plane)

El loader resuelve `prompts.ref` a un archivo de este repo y construye un `PromptPlan` para el backend
del adaptador instanciado (`config.build_prompt_plan(adapter.PROMPT_BACKEND)`):

1. Toma las clases activas (`active_ids` del manifiesto, o las `enabled_by_default`).
2. Aplana las `phrasings` del backend en una lista ordenada de frases (`PromptPhrase`), cada una con
   `prompt_id` + `canonical` + `strategy`/`condition_id`.
3. **YOLOE**: `set_classes(plan.texts())`; el `class_id` devuelto indexa directo el plan → binding exacto.
   Varias frases de la misma clase = varios índices que colapsan al mismo `canonical` (ensembling).
4. **GDINO**: caption = `". ".join(plan.texts()) + "."`; el span devuelto se resuelve contra el plan
   (exacto → substring → solapamiento); si no resuelve, la detección se descarta (no binding nulo).

Resultado: cada detección sale ligada por construcción (`label` canónico + `prompt_id`).

## 4. Sets actuales

| Set | Estado | Clases | Notas |
|---|---|---|---|
| `cr01_cr02_v2_short` | **congelado** | person, helmet, vest | Etiquetas cortas v2 (mejor activación de YOLOE/CLIP que las frases compuestas de v1). Solo `phrasings.default`. |
| `cr01_cr02_bench_v2` | **congelado** | person, helmet, vest, **bare_head** | Set de evaluación BENCH v2. `bare_head` (`role: visual_risk_indicator`) para cabeza sin casco. **NO modificar** — reproducibilidad del BENCH. |
| `ppe_v2_descriptive` | **no congelado** | person, helmet, vest, bare_head | Fraseo descriptivo por backend para A/B contra los congelados: `gdino` con sinónimos cortos (`hard hat`/`safety helmet`, `reflective vest`/`high-visibility vest`, `bare head`/`uncovered head`), `yoloe` nominal. `strategy: positive_evidence`, `condition_id` CR-01/CR-02. |

### Congelado vs experimental
- **Congelados (`cr01_cr02_*`)**: sus frases son byte-equivalentes a las del protocolo v2. No se
  tocan; cualquier cambio rompería la comparabilidad histórica del BENCH.
- **Experimentales (`ppe_v2_descriptive`, nuevos)**: acá se itera el fraseo. Para A/B, correr el mismo
  modelo/split con el set congelado y con el experimental, y comparar con
  `python -m eovrt_media.tools.inspect_runs compare runs/` (desde el media-plane) / el
  `evaluate_bench.py` del repo `e-ovrt_datasets`.

## 5. Guía de fraseo (respaldada por investigación)

Resumen de `e-ovrt_media-plane/docs/research/prompt_module_research.md` (y §11 del spec de la capa de
prompts):

- **Sesgo afirmativo**: los OVD ignoran la negación. Detectar **evidencia positiva** (`bare_head` como
  indicador visible de "sin casco") rinde mejor que prompts negados ("person without helmet"). El
  `direct_absence` queda como variante **diagnóstica**, no primaria.
- **Longitud de caption (GDINO)**: acotar el nº de frases activas; no agregar sinónimos ilimitados.
  Los sets congelados del BENCH **no** llevan sinónimos por esto.
- **Atributos finos + hard negatives**: el desempeño cae con distractores semánticamente cercanos
  (FG-OVD). No es un problema del set sino de la **evaluación**: medir con/sin negativos.

## 6. Agregar un prompt set

1. Copiá un set existente en `prompts/<nuevo>.yaml`, ajustá `id` (== nombre de archivo) y `classes`.
2. Mantené los `canonical` dentro de canonical_v2 si vas a evaluar contra el BENCH; usá otros `id`/
   `canonical` si querés un modo exploración (esas corridas no se evalúan contra el BENCH).
3. Referencialo desde un manifiesto: `prompts: {ref: <nuevo>, active_ids: [...]}`.
4. No hay validación standalone por CLI: el servicio media-plane valida el manifiesto al
   lanzarlo (`POST /api/runs` rechaza con `422` si es inválido).
