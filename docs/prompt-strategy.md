# Estrategia de prompts — metodología, ciclo de vida y programa de estudios

## 1. Qué es este documento

Este documento define la **metodología** con la que se diseñan, versionan y estudian los
prompt sets de esta plataforma, y el **programa de estudios** que los organiza. Se subordina
al **doc núcleo 12** del repo `docs` (`12-diseno-prompts-y-fusion-ehyb.md`, enmendado
2026-07-17 para la **pista doble** GDINO-tiny primaria + YOLOE-26s réplica) — el protocolo
experimental es el del doc 12, no uno nuevo — y al spec de diseño
[`docs/_archive/superpowers/specs/2026-07-17-prompt-strategy-design.md`](superpowers/specs/2026-07-17-prompt-strategy-design.md).

[`docs/prompt-sets.md`](prompt-sets.md) queda como referencia de **formato** (estructura del
YAML, resolución de `phrasings`, cómo los consume el media-plane); este documento cubre lo que
`prompt-sets.md` no cubre: la taxonomía de ejes, el ciclo de vida declarativo, la gestión desde
la webconsole y el programa de estudios en tres carriles.

## 2. Taxonomía: los ejes del informe como vocabulario único

**Para qué sirve `strategy`:** cada clase de un prompt set declara *cómo* fue formulada — no
cambia el comportamiento del detector (el media-plane no ramifica lógica sobre este campo), pero
viaja como provenance hasta `detections.jsonl`. Eso permite, después de correr un experimento,
responder "¿qué eje de fraseo rindió mejor?" agrupando resultados por `strategy` sin tener que
volver a mirar el YAML del prompt set. Es la variable independiente del programa de estudios
de E-DIR (§4).

La taxonomía de estrategias de fraseo **es la del informe de tesis** (§17.1.5.4.2 / Tabla
C.1). No se inventa vocabulario paralelo. Cada formulación declara su eje en el campo
`strategy` del prompt set (campo ya existente, ya propagado a `detections.jsonl` como
provenance):

| Eje (valor de `strategy`) | Qué es | Ejemplo CR-01 | Rol |
|---|---|---|---|
| `canonical_positive` | Vocabulario positivo canónico, etiquetas nominales | `person`, `helmet` | Insumo de E-IND (núcleo) |
| `syntactic_negation` | Negación directa | `person without hard hat` | Eje de E-DIR |
| `specificity` | Mayor especificidad contextual | `construction worker without safety helmet` | Eje de E-DIR |
| `observable_state` | Estado visible que evidencia la condición | `person with bare head on construction site` | Eje de E-DIR; acá viven `bare_head` y el rescate de clases débiles |
| `presence_template` | Template de presencia, solo diagnóstico sintáctico | `a photo of a hard hat` | Eje de E-DIR; **nunca** evidencia de ausencia (doc 12 §2.2.2) |

### Reglas transversales

1. **Sinónimos/ensembling no son un eje**: son variantes dentro de un eje, y solo existen en la
   ventana exploratoria pre-freeze (§3). Tras el freeze, una frase mal elegida es un resultado,
   no un bug (doc 12 §2.2.1).
2. **Presupuesto de caption (GDINO)**: el costo en frases de cada set queda registrado en el
   propio set (nº total de frases activas). La interacción entre prompts se mide una sola vez
   con el sub-experimento aislado-vs-completo del doc 12 §3, restringido a formulaciones
   finalistas (dato que además decide la variante operativa de E-HYB, doc 12 §4.1).
3. **Fraseo por backend se conserva** (formato existente, `docs/prompt-sets.md`): un set = una
   estrategia con `phrasings` por backend. Las formulaciones literales de la Tabla C.1 entran
   como fraseo de ambos backends salvo variante justificada en la exploración pre-freeze,
   registrada antes del congelamiento.

No hay valores `strategy` históricos tolerados: todo set (nuevo o recreado) usa únicamente los
5 ejes de la tabla. El binding del media-plane no cambia: `strategy` es metadata de provenance,
no ramifica lógica.

## 3. Ciclo de vida y gestión declarativa

Convenciones en los YAML + documentación. El loader del media-plane ignora los campos nuevos
(metadata); no hay cambio de código en el media-plane.

### 3.1 Estados

Campo `status` en el YAML del set; transiciones en un solo sentido:

- `exploratory` — única ventana de edición de frases. Candidatas por eje, rescate de clases
  débiles.
- `frozen_pending_review` — formulaciones finalistas elegidas; espera **revisión del usuario**
  (doc 12 §2.2.3, mitigación del sesgo del auditor). No ancla nada reportable.
- `frozen` — congelado tras la revisión. Inmutable: cualquier cambio es un set nuevo con otro
  id. Único estado citable en resultados.

**Alcance de la inmutabilidad:** lo inmutable es el **payload semántico** (el bloque `classes`
completo: ids, canonical, phrasings, strategy). Al congelar se calcula `frozen_sha256`, y se
guarda en el propio set. No se retro-etiqueta: un set frozen que necesita metadata nueva se
recrea desde cero (borrar + crear) o se deriva (§4) — nunca se edita in place.

**Fórmula del hash** (única convención, usarla siempre igual):

```
sha256 de json.dumps(classes, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
```

sobre el bloque `classes` **crudo** del YAML (tal como lo parsea `yaml.safe_load`, no un
`model_dump` de Pydantic — los defaults del modelo alterarían el payload).

### 3.2 Lineage y naming

- `derives_from: <id>` + `changes: "<qué cambió y por qué>"` en cada set derivado. La
  genealogía completa de los fraseos se reconstruye desde los YAML solos — material directo
  para la sección de sensibilidad al prompt del informe.
- Naming: `<estrategia>_v<n>` para sets del núcleo (`eind_v1`, `edir_v1`, como los nombra el
  doc 12); `<estrategia>_exp_<tema>` para exploratorios (p. ej. `edir_exp_weak_classes`);
  prefijo `demo_` para el carril demostrativo. El `id` sigue siendo == nombre de archivo.
- Carril demostrativo: campo `track: demo` — explicita que el set no participa del protocolo
  comparativo ni del time-box del núcleo.

### 3.3 Regla de promoción

Un set se congela cuando (y solo cuando) va a anclar una corrida cuyo resultado se cita — en el
núcleo, en el BENCH o en un video de la defensa. Los exploratorios nunca se citan directamente:
se cita el frozen que produjeron.

### 3.4 Trazabilidad (ya resuelta; se declara como garantía)

`prompt_set_id` viaja en `effective_config` de cada corrida; cada detección lleva `prompt_id` +
`source_prompt` + `strategy`. La cadena alerta → frase exacta es reconstruible hoy (doc 12
§6.4).

## 4. Programa de estudios: tres carriles

### Carril 1 — Núcleo pre-registrado (manda el doc 12; time-box 2 semanas)

| Set | Contenido | Estado final |
|---|---|---|
| `eind_v1` | person/helmet/vest, `canonical_positive`, phrasings idénticos ambos backends | frozen; Fase 1 se puntúa sin re-inferir (reusa Sprint 2, ambas pistas) |
| `edir_v1` | Por condición (CR-01/CR-02), una formulación finalista por eje de la Tabla C.1, cada una con `prompt_id` propio | frozen tras revisión del usuario (acta: fecha + versión, spec 44) |

Corridas: Fase 1 (estado por persona, BENCH mitad test) y Fase 2 (alertas, clip bench, motor
G0, pattern set v2) × **2 pistas** (GDINO-tiny primaria, YOLOE-26s réplica; enmienda doc 12 §3)
× 3 estrategias (E-IND, E-DIR, E-HYB — E-HYB por fusión offline, sin inferencia nueva).
**Regla de comparabilidad:** dentro de cada pista, variable única = estrategia/prompt set;
entre pistas no se comparan prompts, se reporta si el ranking de estrategias se sostiene entre
familias (robustez). **Línea de corte:** la pista YOLOE se sacrifica completa antes que
cualquier fase de la pista GDINO; lo no corrido se reporta "no ejecutada con causa"
(§17.3.13.3).

### Carril 2 — Exploración pre-freeze (única ventana de iteración)

| Set | Pregunta |
|---|---|
| `edir_exp_cr01_candidates`, `edir_exp_cr02_candidates` | Mejor formulación por eje: 2–3 candidatas por eje, corridas rápidas sobre la mitad calib del BENCH; finalista por datos + revisión del usuario |
| `edir_exp_weak_classes` | Rescate de `bare_head` (débil en todos los modelos, Sprint 2) y `vest` en YOLOE: sinónimos dentro de `observable_state`/`specificity` |

Salida: finalistas → `edir_v1`; el resto queda en el lineage como registro de cómo se eligieron
las frases (anti-sesgo del auditor). El carril termina en el freeze.

### Carril 3 — Demostrativo (defensa; `track: demo`, fuera del time-box)

| Set | Contenido | Ancla de medición |
|---|---|---|
| `demo_new_class_machinery_v1` | Clase nueva fuera de PPE (excavadora/camión/mixer; candidata final por mini-piloto sobre imágenes MOCS ya en disco), condición de **presencia** (sin lógica nueva en el motor) | Clip GT vía video-gt-lab (spec 43) + video V2 de la defensa |
| `demo_limits_harness_v1` | Arnés como estudio de límites del lenguaje (resultado honesto aunque rinda mal) | Cualitativo + clip GT si el material lo permite |

### Mapa a la narrativa de tesis

- Carril 1 → argumento central "condiciones en lenguaje, medidas" (A1–A5, doc 09) y sección de
  sensibilidad al prompt (§17.1.5.4).
- Carril 2 → "cómo se eligieron las frases" (mitigación del sesgo del auditor, doc 07 D1.6).
- Carril 3 → video V2 (clase nueva solo con lenguaje) y el límite honesto del enfoque (arnés).

## 5. Gestión desde la webconsole

Walkthrough paso a paso de cómo crear/congelar/derivar un set desde la UI:
[`docs/prompt-sets.md`](prompt-sets.md) §6. Esta sección documenta el contrato (por qué esta
arquitectura, garantías del BFF, API).

Extensión natural del ADR-009 (webconsole = superficie de gestión de la config centralizada).
Decisión: **opción A — el BFF edita los YAML de `prompts/`**; se descartó un almacén propio
(DB) por romper el principio "el repo declarativo es la fuente canónica" y crear un problema de
sincronización DB↔YAML↔git sin retorno.

La UI es un **editor estructurado** (no texto libre): clases, phrasings por backend, `strategy`
como selección cerrada sobre la taxonomía de §2. Tres garantías en el BFF:

1. **Validación de schema al guardar** — con un **espejo mínimo** del modelo Pydantic del
   loader del media-plane (el venv de la consola no depende de `eovrt_media` y no debe hacerlo:
   arrastraría el stack de inferencia). El validador final sigue siendo el media-plane
   (`POST /api/runs` → 422), y el espejo se mantiene alineado con un test de contrato sobre los
   sets reales del repo.
2. **Inmutabilidad de frozen** — el BFF verifica `frozen_sha256` y rechaza escrituras a un set
   frozen; sobre un frozen solo ofrece "derivar set nuevo" (auto-completa `derives_from`).
3. **Transiciones de estado solo vía acciones explícitas** (botón "congelar" →
   `frozen_pending_review` → confirmación de revisión → `frozen`); nunca editando `status` a
   mano.

Git sigue versionando; **la consola nunca commitea** (el usuario commitea). La webconsole ya
descubre y parsea `prompts/` para componer corridas — se extiende esa plomería, no se crea
otra.

**Implementado.** La vista `/prompts` (frontend) y el router `/api/prompt-sets` (backend)
cubren el ciclo de vida completo:

- `GET /api/prompt-sets` — lista con `status`/`track`/conteos.
- `GET /api/prompt-sets/{set_id}` — detalle, incluye `frozen_sha256` si aplica.
- `POST /api/prompt-sets` — alta (`exploratory` por defecto).
- `PUT /api/prompt-sets/{set_id}` — edición de un set no congelado.
- `DELETE /api/prompt-sets/{set_id}` — borrado de un set no congelado.
- `POST /api/prompt-sets/{set_id}/freeze-request` — pasa a `frozen_pending_review`.
- `POST /api/prompt-sets/{set_id}/freeze` — confirma el freeze, calcula y persiste
  `frozen_sha256`.
- `POST /api/prompt-sets/{set_id}/derive` — crea un set nuevo a partir de uno existente,
  con `derives_from` apuntando al origen.

Detalle de uso en `webconsole/README.md` §"Gestión de prompt sets".
