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
  status: exploratory       # exploratory | frozen_pending_review | frozen (ver docs/prompt-strategy.md)
  track: core               # core | demo | comparative | retention (ver §2.1)
  derives_from: <id>        # opcional: set del que deriva (lineage)
  changes: "..."            # opcional: qué cambió respecto de derives_from y por qué
  frozen_sha256: "<hex>"    # solo en frozen: sha256 del bloque classes (lo calcula la webconsole al congelar; ver §2.1)
  classes:
    - id: helmet                # clave estable → Detection.prompt_id; la referencian manifiestos y patterns
      canonical: helmet         # clase de evaluación (canonical_v2); opcional, default = id
      role: ppe                 # solo documentación (entity | ppe | visual_risk_indicator); NO se propaga
      strategy: canonical_positive   # provenance → Detection.strategy (taxonomía de ejes, ver §"Reglas")
      condition_id: CR-01       # provenance → Detection.condition_id (trazabilidad de riesgo, etiqueta libre)
      enabled_by_default: true  # entra por default si el manifiesto no trae active_ids
      phrasings:                # dict backend → lista de frases
        default: ["helmet"]      #   fallback para cualquier backend sin entrada propia
        gdino:   ["hard hat", "safety helmet"]   # sinónimos descriptivos cortos
        yoloe:   ["helmet"]      #   nominal corto (varias frases = ensembling)
```

### 2.1 Vocabulario de `track`

| `track` | Qué agrupa |
|---|---|
| `core` | Carril núcleo del protocolo (E-IND): vocabulario positivo canónico de CR-01/CR-02. |
| `demo` | Carril demostrativo, fuera del protocolo comparativo. |
| `comparative` | Carril E-DIR: un prompt por eje pre-registrado, para comparar formulaciones. |
| `retention` | Conjuntos para medir retención de vocabulario abierto en fine-tuning (arnés T2, ADR-017); **no** son prompts de riesgo CR-01/CR-02. |

Los sets `retention` los **genera y congela el arnés de fine-tuning**
(`finetuning/scripts/build_coco_retention_harness.py`), no la webconsole: su freeze se
ancla por sha256 del **archivo** en `finetuning/manifests/*.json` y por eso son los únicos
`frozen` sin `frozen_sha256` (el hash del bloque `classes` que calcula la consola).

### Reglas de resolución
- `id`: único en el set. Es la **clave estable** de la clase — no cambia aunque cambie el fraseo.
  Se propaga a `Detection.prompt_id`. Además es lo que referencian por fuera del prompt set:
  el `active_ids` de un manifiesto de experimento, y del lado del control-plane los patterns
  (`subject_class: person`, `required_absent_class: helmet` en `configs/patterns/*.yaml`)
  esperan encontrar exactamente estos ids en las detecciones que les llegan. Por eso `id` y
  `phrasings` son campos separados a propósito: podés cambiar el fraseo (iterar frases,
  agregar sinónimos, correr un A/B) sin romper nada río abajo, porque lo que ancla al resto de
  la plataforma es el `id`, no el texto que se le manda al modelo.
- `canonical`: clase del vocabulario de evaluación (canonical_v2: `person`/`helmet`/`vest`/`bare_head`).
  Default = `id`. Se propaga a `Detection.label`. **Alinea las detecciones con el BENCH de forma
  determinista** (binding por construcción, sin heurísticos).
- `phrasings`: cadena de fallback `phrasings[backend]` → `phrasings["default"]`. Si falta toda entrada
  para una clase activa, es **error de validación**. Una entrada presente pero **vacía** (`gdino: []`)
  también es error (no cae silenciosamente a `default`).
- `role`: **solo documentación** — clasifica la clase (`entity`/`ppe`/`visual_risk_indicator`) para
  quien lee el YAML. A diferencia de `strategy`/`condition_id`, **no se propaga** a
  `detections.jsonl` ni a ningún contrato — no busques `role` río abajo, no está.
- `strategy` / `condition_id`: **provenance activo** — sí se propagan a `detections.jsonl`
  (`Detection.strategy`/`Detection.condition_id`), pero el media-plane **no ramifica lógica**
  sobre ellos (eso es del plano de control, y hoy tampoco lo consume — quedan como campo de
  trazabilidad para el informe). Los valores de `strategy` son la taxonomía de ejes de
  [`docs/prompt-strategy.md`](prompt-strategy.md): `canonical_positive`, `syntactic_negation`,
  `specificity`, `observable_state`, `presence_template`. No hay valores históricos tolerados.
  `condition_id` es una etiqueta libre que traza a CR-01..06 (no valida contra una lista cerrada).
- `enabled_by_default`: decide si la clase entra **cuando el manifiesto no especifica
  `active_ids`** (`prompts: {ref: <set>}` sin más). Si el manifiesto sí trae `active_ids: [...]`,
  esa lista manda tal cual y `enabled_by_default` se ignora — podés activar ahí incluso una clase
  con `enabled_by_default: false`.

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

Catálogo **activo** (`prompts/*.yaml`) — lo que la consola lista y los manifiestos pueden
referenciar por `ref`:

| Set | Estado | Clases | Notas |
|---|---|---|---|
| `cr01_cr02_v2_short` | **`frozen`** | person, helmet, vest | Etiquetas cortas v2 (mejor activación de YOLOE/CLIP que las frases compuestas de v1). Solo `phrasings.default`. `frozen_sha256: df81fd48…`. Set del rodaje y del bench. |
| `cr01_cr02_bench_v2` | `exploratory` | person, helmet, vest, **bare_head** | Set de evaluación BENCH v2. `bare_head` (`role: visual_risk_indicator`) para cabeza sin casco. Recreado 2026-07-18 con `strategy` por clase; pendiente de pedir congelamiento. |
| `eind_v1` | **`frozen`** | person, helmet, vest | Carril 1 (núcleo E-IND): vocabulario positivo canónico, `canonical_positive`, phrasings idénticos ambos backends. Deriva de `cr01_cr02_v2_short`. Congelado 2026-07-29 por acta (`docs/operacion/76` del repo docs); `frozen_sha256: 7a0126f4…`. |
| `edir_v1` | **`frozen`** | 8 formulaciones (4 por condición) | Carril E-DIR (`track: comparative`): un prompt por eje pre-registrado (negación sintáctica, especificidad, estado observable, template diagnóstico `enabled_by_default: false`) para CR-01 y CR-02, literal de doc 12 §2.2. Congelado 2026-07-29 por la misma acta (doc 76); `frozen_sha256: a1278d0c…`. Nada se reformula post-freeze. |
| `cr01_cr02_v2_safety_vest` | `exploratory` | person, helmet, vest | A/B del phrasing de `vest` → "safety vest" (hipótesis anti sobre-marca F-G2.1, docs/operacion/67). Deriva de `cr01_cr02_v2_short`; solo cambia vest. |
| `coco_val2017_80` | **`frozen`** | 80 categorías COCO | `track: retention` (§2.1): arnés de retención de vocabulario abierto del tier T2 (T-FT-062 / D-FT-04). Generado por `finetuning/scripts/build_coco_retention_harness.py` — **no editar a mano**; el `id` de cada clase es el nombre COCO exacto. Congelado por archivo: `sha256: 074558773ae3…` en `finetuning/manifests/t2_coco_retention_protocol.json` y en el brazo base congelado, así que no lleva `frozen_sha256`. |

**Archivados** (2026-07-18, `prompts/_archive/`) — candidatos exploratorios del Carril 2
(E-DIR) previos al set congelado `edir_v1`; fuera del catálogo activo (ver
`prompts/_archive/README.md`): `ppe_v2_descriptive`, `edir_exp_cr01_candidates`,
`edir_exp_cr02_candidates`, `edir_exp_weak_classes`.

> Tabla actualizada 2026-07-29 (acta de congelamiento `edir_v1`+`eind_v1`, doc 76 del
> repo docs). Fuente de verdad siempre: `prompts/*.yaml`.

### Congelado vs experimental

Detalle del ciclo de vida (estados, `frozen_sha256`, lineage, regla de promoción, programa de
estudios en tres carriles): [`docs/prompt-strategy.md`](prompt-strategy.md). En síntesis: un
`frozen` es byte-equivalente y no se toca — cualquier cambio rompería la comparabilidad
histórica del BENCH; si un set frozen necesita metadata nueva, se borra y se recrea (no se
edita in place). En los `exploratory` se itera el fraseo; para A/B, correr el mismo
modelo/split con un set congelado y con el exploratorio, y comparar con
`python -m eovrt_media.tools.inspect_runs compare runs/` (desde el media-plane) / el
`evaluate_bench.py` del repo `e-ovrt_datasets`.

## 5. Guía de fraseo (respaldada por investigación)

Resumen de `e-ovrt_media-plane/docs/research/prompt_module_research.md` (y §11 del spec de la capa de
prompts):

- **Sesgo afirmativo**: los OVD ignoran la negación. Detectar **evidencia positiva** (`bare_head` como
  indicador visible de "sin casco", eje `observable_state`) rinde mejor que prompts negados
  ("person without helmet", eje `syntactic_negation`). La negación queda como variante
  **diagnóstica**, no primaria.
- **Longitud de caption (GDINO)**: acotar el nº de frases activas; no agregar sinónimos ilimitados.
  Por eso `cr01_cr02_v2_short`/`cr01_cr02_bench_v2` no llevan sinónimos (solo
  `phrasings.default`, una frase por clase).
- **Atributos finos + hard negatives**: el desempeño cae con distractores semánticamente cercanos
  (FG-OVD). No es un problema del set sino de la **evaluación**: medir con/sin negativos.

## 6. Crear un prompt set — de punta a punta desde la webconsole

La vía recomendada es la **webconsole** (vista `/prompts`): valida el schema al guardar y aplica
el ciclo de vida declarativo (transiciones de `status` solo por acción explícita, `frozen_sha256`
calculado al congelar, `derives_from` auto-completado al derivar). El editor **no es texto
libre**: es un formulario estructurado sobre el mismo formato de §2 — clases, phrasings por
backend, `strategy` como lista cerrada. Contrato de API completo (endpoints, garantías del BFF):
[`docs/prompt-strategy.md`](prompt-strategy.md) §5.

### 6.1 Alta (set nuevo, `status: exploratory`)

1. **"Nuevo set"** en `/prompts` → se abre el editor vacío. Único momento en que se pide el
   **id**: minúsculas/números/`_`, va a ser el nombre del archivo (`prompts/<id>.yaml`) y la
   clave que después usa `prompts: {ref: <id>}` en un manifiesto.
2. Completá **descripción** (para qué es este set, de qué se deriva conceptualmente).
3. **"Agregar clase"** por cada clase a detectar. Por clase:
   - **clase id** — el identificador estable (`person`, `helmet`, `bare_head`...). Ver §"Reglas
     de resolución" arriba: esto es lo que otros componentes (manifiestos, patterns del
     control-plane) van a referenciar, así que elegilo pensando en eso, no en el fraseo.
   - **strategy** — el eje de formulación de la Tabla C.1 (`docs/prompt-strategy.md` §2):
     `canonical_positive` para vocabulario positivo directo (la mayoría de las clases),
     `observable_state`/`syntactic_negation`/`specificity`/`presence_template` para las
     variantes de E-DIR. Metadato de trazabilidad — no cambia cómo se detecta, pero sí queda
     registrado en cada detección para poder analizar después qué eje rindió mejor.
   - **phrasings.\<backend\>** — las frases candidatas, separadas por `;` (`person; worker;
     obrero`). Al menos `phrasings.default`; agregá `gdino`/`yoloe` si necesitás fraseo
     distinto por backend (§1: GDINO tolera frases descriptivas, YOLOE rinde mejor con
     etiquetas cortas).
4. **Guardar** — el set queda escrito en `prompts/<id>.yaml` con `status: exploratory`. Desde
   acá podés seguir iterando: reabrir, cambiar phrasings, agregar/sacar clases, guardar de
   nuevo. Es la **única** ventana en la que el set es editable.

### 6.2 Congelamiento (cuando el fraseo ya es finalista)

Un set se congela cuando va a anclar una corrida cuyo resultado se va a citar (regla de
promoción, `docs/prompt-strategy.md` §3.3) — no antes. Mientras estés iterando frases, dejalo en
`exploratory`.

5. **"Pedir congelamiento"** → pasa a `frozen_pending_review`. El set deja de ser editable acá
   (es el checkpoint: revisar antes de comprometerse a algo inmutable, mitiga el sesgo de elegir
   la frase que más te gusta después de ver el resultado).
6. Revisión humana fuera de la consola (no hay un paso de UI para esto — es vos leyendo el set
   y decidiendo si el fraseo elegido es el que querés citar).
7. **"Confirmar freeze"** → pasa a `frozen`. El backend calcula `frozen_sha256` sobre el bloque
   `classes` y lo persiste en el propio YAML. A partir de acá el set es inmutable: ni editar ni
   borrar. Es el único estado citable en resultados/informe.

### 6.3 Iterar sobre un set frozen: derivar, nunca editar

8. Sobre un set `frozen`, la única acción disponible es **"Derivar set nuevo"**: pedís un id
   nuevo y un campo **"cambios"** obligatorio (qué cambia y por qué — el backend rechaza el
   derive si viene vacío). Esto copia todas las clases del origen, arranca en `exploratory` de
   nuevo, y guarda `derives_from: <id origen>` — así se reconstruye la genealogía completa del
   fraseo desde los YAML solos (§3.2 de `prompt-strategy.md`).
9. Si un set frozen resulta tener un error real (no un cambio de fraseo, sino algo mal puesto:
   falta `strategy`, `role` mal clasificado, etc.) **no se edita in place** — se borra y se
   recrea desde cero. La inmutabilidad de un frozen es una garantía dura, no hay excepción de
   "solo esta vez".

### 6.4 Usarlo en un experimento

10. Referencialo desde un manifiesto de `experiments/`: `prompts: {ref: <id>, active_ids:
    [...]}`. `active_ids` es opcional — si lo omitís, entran las clases con
    `enabled_by_default: true` (ver §"Reglas de resolución").
11. No hay validación standalone por CLI: el servicio media-plane valida el manifiesto completo
    al lanzarlo (`POST /api/runs` rechaza con `422` si el prompt set referenciado es inválido).

### 6.5 Alternativa: editar el YAML a mano

Sigue siendo válido para sets `exploratory` — copiá un set existente a `prompts/<nuevo>.yaml`,
ajustá `id` (== nombre de archivo) y `classes`, seguí los mismos campos de §2. Mantené los
`canonical` dentro de canonical_v2 si vas a evaluar contra el BENCH. La consola es la vía
recomendada porque valida el schema al guardar (a mano, el primer error lo tira recién
`POST /api/runs`); a mano es más rápido para prototipar algo que ni siquiera vas a correr
todavía.
