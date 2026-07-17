# Estrategia y gestión de prompts — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar el spec `docs/superpowers/specs/2026-07-17-prompt-strategy-design.md`: ciclo de vida declarativo de prompt sets en los YAML, sets del programa (eind_v1 + exploratorios), documentación de metodología, y gestión de prompt sets desde la webconsole (BFF CRUD con garantías + editor estructurado en la SPA).

**Architecture:** Los YAML de `prompts/` siguen siendo la única fuente de verdad. Parte A (Tasks 1–4) es puramente declarativa: campos de ciclo de vida en los sets existentes, sets nuevos, docs. Parte B (Tasks 5–9) agrega en el BFF un módulo `prompt_store.py` (validación con espejo Pydantic, hash de congelamiento, transiciones de estado) + router `/api/prompt-sets`, y en la SPA una página de gestión con editor estructurado. La consola nunca commitea.

**Tech Stack:** YAML (pyyaml), FastAPI + Pydantic v2 (BFF, `webconsole/backend`), React + TypeScript + vitest (SPA, `webconsole/frontend`), pytest.

## Global Constraints

- **NUNCA hacer `git commit`** — regla del workspace (`projects/CLAUDE.md`) que anula los pasos de commit de cualquier skill. Se editan archivos y se informa; el usuario commitea.
- Repos hermanos: este plan toca SOLO `e-ovrt_experimental-setup`. El media-plane no cambia (loader/binding intactos, spec §5 fuera de alcance).
- Los sets `status: frozen` son inmutables en su bloque `classes`. Los dos históricos (`cr01_cr02_v2_short`, `cr01_cr02_bench_v2`) NO se les toca ninguna frase — solo se agregan campos de metadata (spec §2.1 precisa que la inmutabilidad cubre el payload semántico).
- Hash de congelamiento (convención única, spec §2.1): `sha256` sobre `json.dumps(classes_raw, sort_keys=True, ensure_ascii=True, separators=(",", ":"))` donde `classes_raw` es la lista `classes` tal como la parsea `yaml.safe_load` del archivo (NO un model_dump — los defaults de Pydantic alterarían el payload).
- Taxonomía `strategy` (spec §1): `canonical_positive | syntactic_negation | specificity | observable_state | presence_template`. Valores históricos tolerados solo en sets frozen retro-etiquetados: `positive_evidence`, `direct_absence`.
- Estados: `exploratory → frozen_pending_review → frozen`, un solo sentido, transiciones solo por acciones explícitas (nunca editando `status` en un PUT).
- Docs y strings de UI en español; código/identificadores en inglés (patrón del repo).
- Backend tests: `cd webconsole/backend && .venv/bin/python -m pytest -q` (venv propio ya existente). Lint: `.venv/bin/python -m ruff check src tests`. Frontend: `cd webconsole/frontend && npx vitest run`.

---

## Parte A — Capa declarativa

### Task 1: Retro-etiquetado de los sets existentes

**Files:**
- Modify: `prompts/cr01_cr02_v2_short.yaml`
- Modify: `prompts/cr01_cr02_bench_v2.yaml`
- Modify: `prompts/ppe_v2_descriptive.yaml`

**Interfaces:**
- Produces: los tres YAML con campos `status`/`track` (+ `frozen_sha256` en los frozen, `derives_from`/`changes` en el exploratorio). El test de integridad de Task 5 leerá estos archivos reales y verificará los hashes.

- [ ] **Step 1: Calcular los hashes de los dos sets frozen**

```bash
cd /home/simonll4/projects/e-ovrt_experimental-setup
python3 - <<'EOF'
import hashlib, json, yaml
for name in ("cr01_cr02_v2_short", "cr01_cr02_bench_v2"):
    classes = yaml.safe_load(open(f"prompts/{name}.yaml"))["prompt_set"]["classes"]
    payload = json.dumps(classes, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    print(name, hashlib.sha256(payload.encode()).hexdigest())
EOF
```

Anotar los dos hashes impresos; se usan en el Step 2.

- [ ] **Step 2: Agregar metadata a los dos sets frozen (sin tocar `classes`)**

En `prompts/cr01_cr02_v2_short.yaml` y `prompts/cr01_cr02_bench_v2.yaml`, insertar inmediatamente después de la línea `language: en` (en ambos):

```yaml
  status: frozen            # retro-etiquetado 2026-07-17 (spec prompt-strategy §2.1)
  track: core
  frozen_sha256: "<hash del Step 1 para ESTE archivo>"
```

No modificar ninguna otra línea (la garantía de byte-equivalencia cubre el bloque `classes`).

- [ ] **Step 3: Migrar `ppe_v2_descriptive.yaml` a exploratory + taxonomía nueva**

En `prompts/ppe_v2_descriptive.yaml`, insertar después de `language: en`:

```yaml
  status: exploratory
  track: core
  derives_from: cr01_cr02_bench_v2
  changes: >
    Fraseo descriptivo por backend para A/B contra el set congelado del BENCH
    (mismas 4 clases canónicas). Migrado a la taxonomía de ejes del informe
    (spec 2026-07-17 §1): strategy por rol de la clase.
```

Y migrar los valores `strategy` por rol (spec §1, migración): en las clases `helmet` y `vest` (rol ppe, vocabulario positivo) cambiar `strategy: positive_evidence` → `strategy: canonical_positive`; en la clase `bare_head` (rol visual_risk_indicator) cambiar `strategy: positive_evidence` → `strategy: observable_state`. La clase `person` no tiene `strategy`; agregar `strategy: canonical_positive`.

- [ ] **Step 4: Verificar**

```bash
python3 - <<'EOF'
import hashlib, json, yaml
for name in ("cr01_cr02_v2_short", "cr01_cr02_bench_v2"):
    ps = yaml.safe_load(open(f"prompts/{name}.yaml"))["prompt_set"]
    payload = json.dumps(ps["classes"], sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    computed = hashlib.sha256(payload.encode()).hexdigest()
    assert ps["status"] == "frozen" and ps["frozen_sha256"] == computed, name
ps = yaml.safe_load(open("prompts/ppe_v2_descriptive.yaml"))["prompt_set"]
assert ps["status"] == "exploratory" and ps["derives_from"] == "cr01_cr02_bench_v2"
strategies = {c["id"]: c.get("strategy") for c in ps["classes"]}
assert strategies == {"person": "canonical_positive", "helmet": "canonical_positive",
                      "vest": "canonical_positive", "bare_head": "observable_state"}, strategies
print("OK")
EOF
```

Expected: `OK`

### Task 2: Set del núcleo `eind_v1`

**Files:**
- Create: `prompts/eind_v1.yaml`

**Interfaces:**
- Produces: `prompts/eind_v1.yaml` con `status: frozen_pending_review` (el usuario lo pasa a frozen tras su revisión — acta requerida por spec 44). Lo referencia el spec 44 (`experiments/` del núcleo) y el doc 12 §2.1.

- [ ] **Step 1: Crear el set**

```yaml
prompt_set:
  id: eind_v1
  description: >
    Set del núcleo E-IND (ADR-001, doc 12 §2.1): vocabulario positivo canónico
    (canonical_v2 sin bare_head), etiquetas nominales, phrasings idénticos para
    ambos backends (pista doble GDINO-tiny/YOLOE-26s, enmienda doc 12 §3).
    La Fase 1 de E-IND se puntúa sin re-inferir (reusa Sprint 2).
  language: en
  status: frozen_pending_review
  track: core
  derives_from: cr01_cr02_v2_short
  changes: >
    Mismo vocabulario de 3 clases que cr01_cr02_v2_short; explicita
    strategy canonical_positive, condition_id y phrasings por backend.
  classes:
    - id: person
      role: entity
      strategy: canonical_positive
      phrasings: { default: ["person"], gdino: ["person"], yoloe: ["person"] }
    - id: helmet
      role: ppe
      strategy: canonical_positive
      condition_id: CR-01
      phrasings: { default: ["helmet"], gdino: ["helmet"], yoloe: ["helmet"] }
    - id: vest
      role: ppe
      strategy: canonical_positive
      condition_id: CR-02
      phrasings: { default: ["vest"], gdino: ["vest"], yoloe: ["vest"] }
```

- [ ] **Step 2: Verificar que el media-plane lo parsea**

```bash
cd /home/simonll4/projects/e-ovrt_media-plane && .venv/bin/python - <<'EOF'
import yaml
from eovrt_media.config.schemas import PromptsFile
data = yaml.safe_load(open("../e-ovrt_experimental-setup/prompts/eind_v1.yaml"))
pf = PromptsFile(prompt_set=data["prompt_set"])
plan_g = pf.build_plan("gdino"); plan_y = pf.build_plan("yoloe")
assert plan_g.texts() == ["person", "helmet", "vest"] == plan_y.texts()
print("OK", pf.resolved_set_id())
EOF
```

Expected: `OK eind_v1`. (Si el venv del media-plane no existe, correr el snippet con `python3` + `pip install pydantic pyyaml` no sirve — usar el venv del media-plane; existe según su CLAUDE.md.)

### Task 3: Sets exploratorios del carril 2

**Files:**
- Create: `prompts/edir_exp_cr01_candidates.yaml`
- Create: `prompts/edir_exp_cr02_candidates.yaml`
- Create: `prompts/edir_exp_weak_classes.yaml`

**Interfaces:**
- Produces: tres sets `status: exploratory` con 2–3 candidatas por eje de la Tabla C.1 (doc 12 §2.2). De acá salen las finalistas de `edir_v1` (corridas sobre mitad calib + revisión del usuario — trabajo operativo posterior, fuera de este plan).

- [ ] **Step 1: Crear `prompts/edir_exp_cr01_candidates.yaml`**

Nota de diseño: en las formulaciones persona-céntricas `canonical: person` (la detección es una persona en el estado descripto; el scoring de Fase 1 usa `prompt_id`, no `canonical`); en los templates de presencia `canonical: helmet`. Cada candidata = una clase con `prompt_id` propio y estable.

```yaml
prompt_set:
  id: edir_exp_cr01_candidates
  description: >
    Candidatas E-DIR para CR-01 (sin casco), 2-3 por eje de la Tabla C.1
    (doc 12 §2.2). Exploratorio: corridas rápidas sobre la mitad calib del
    BENCH; las finalistas (una por eje, por datos + revisión del usuario)
    alimentan edir_v1. Los templates son de presencia: solo diagnóstico
    sintáctico, nunca evidencia de ausencia.
  language: en
  status: exploratory
  track: core
  changes: "Set inicial de candidatas; fuente literal Tabla C.1 + variantes."
  classes:
    - id: cr01_neg_without_hard_hat
      canonical: person
      strategy: syntactic_negation
      condition_id: CR-01
      phrasings: { default: ["person without hard hat"] }
    - id: cr01_neg_not_wearing_helmet
      canonical: person
      strategy: syntactic_negation
      condition_id: CR-01
      phrasings: { default: ["person not wearing a helmet"] }
    - id: cr01_spec_construction_worker
      canonical: person
      strategy: specificity
      condition_id: CR-01
      phrasings: { default: ["construction worker without safety helmet"] }
    - id: cr01_spec_worker_site
      canonical: person
      strategy: specificity
      condition_id: CR-01
      phrasings: { default: ["worker on construction site without hard hat"] }
    - id: cr01_state_bare_head_site
      canonical: person
      strategy: observable_state
      condition_id: CR-01
      phrasings: { default: ["person with bare head on construction site"] }
    - id: cr01_state_uncovered_head
      canonical: person
      strategy: observable_state
      condition_id: CR-01
      phrasings: { default: ["worker with uncovered head"] }
    - id: cr01_tmpl_hard_hat
      canonical: helmet
      strategy: presence_template
      condition_id: CR-01
      phrasings: { default: ["a photo of a hard hat"] }
    - id: cr01_tmpl_safety_helmet
      canonical: helmet
      strategy: presence_template
      condition_id: CR-01
      phrasings: { default: ["a photo of a safety helmet"] }
```

- [ ] **Step 2: Crear `prompts/edir_exp_cr02_candidates.yaml`** (análogo CR-02, doc 12 §2.2)

```yaml
prompt_set:
  id: edir_exp_cr02_candidates
  description: >
    Candidatas E-DIR para CR-02 (sin chaleco), 2-3 por eje de la Tabla C.1
    (doc 12 §2.2), análogas a las de CR-01. Exploratorio (ver
    edir_exp_cr01_candidates para el flujo hacia edir_v1).
  language: en
  status: exploratory
  track: core
  changes: "Set inicial de candidatas; análogo CR-02 de la Tabla C.1."
  classes:
    - id: cr02_neg_without_vest
      canonical: person
      strategy: syntactic_negation
      condition_id: CR-02
      phrasings: { default: ["person without safety vest"] }
    - id: cr02_neg_not_wearing_vest
      canonical: person
      strategy: syntactic_negation
      condition_id: CR-02
      phrasings: { default: ["person not wearing a reflective vest"] }
    - id: cr02_spec_construction_worker
      canonical: person
      strategy: specificity
      condition_id: CR-02
      phrasings: { default: ["construction worker without reflective vest"] }
    - id: cr02_spec_worker_site
      canonical: person
      strategy: specificity
      condition_id: CR-02
      phrasings: { default: ["worker on construction site without high-visibility vest"] }
    - id: cr02_state_no_bright_clothing
      canonical: person
      strategy: observable_state
      condition_id: CR-02
      phrasings: { default: ["person without bright colored safety clothing"] }
    - id: cr02_state_dark_clothing
      canonical: person
      strategy: observable_state
      condition_id: CR-02
      phrasings: { default: ["worker in plain dark clothing"] }
    - id: cr02_tmpl_safety_vest
      canonical: vest
      strategy: presence_template
      condition_id: CR-02
      phrasings: { default: ["a photo of a safety vest"] }
    - id: cr02_tmpl_hivis_vest
      canonical: vest
      strategy: presence_template
      condition_id: CR-02
      phrasings: { default: ["a photo of a high-visibility vest"] }
```

- [ ] **Step 3: Crear `prompts/edir_exp_weak_classes.yaml`** (rescate de clases débiles, spec §4 carril 2)

```yaml
prompt_set:
  id: edir_exp_weak_classes
  description: >
    Rescate de clases débiles (Sprint 2: bare_head débil en todos los modelos;
    vest débil en YOLOE). Sinónimos dentro de los ejes observable_state /
    specificity, con fraseo por backend. Exploratorio: A/B contra
    cr01_cr02_bench_v2 sobre la mitad calib; las frases ganadoras informan
    edir_v1 y quedan registradas en el lineage.
  language: en
  status: exploratory
  track: core
  derives_from: cr01_cr02_bench_v2
  changes: "Variantes de fraseo SOLO para bare_head y vest; person/helmet nominales como ancla."
  classes:
    - id: person
      role: entity
      strategy: canonical_positive
      phrasings: { default: ["person"] }
    - id: helmet
      role: ppe
      strategy: canonical_positive
      condition_id: CR-01
      phrasings: { default: ["helmet"] }
    - id: bare_head
      role: visual_risk_indicator
      strategy: observable_state
      condition_id: CR-01
      phrasings:
        default: ["bare head"]
        gdino: ["bare head", "uncovered head", "exposed head without helmet"]
        yoloe: ["bare head", "uncovered head"]
    - id: vest
      role: ppe
      strategy: canonical_positive
      condition_id: CR-02
      phrasings:
        default: ["vest"]
        gdino: ["safety vest", "reflective vest"]
        yoloe: ["vest", "safety vest", "hi-vis vest"]
```

- [ ] **Step 4: Verificar que los tres parsean con el schema del media-plane**

```bash
cd /home/simonll4/projects/e-ovrt_media-plane && .venv/bin/python - <<'EOF'
import yaml
from eovrt_media.config.schemas import PromptsFile
for name in ("edir_exp_cr01_candidates", "edir_exp_cr02_candidates", "edir_exp_weak_classes"):
    data = yaml.safe_load(open(f"../e-ovrt_experimental-setup/prompts/{name}.yaml"))
    pf = PromptsFile(prompt_set=data["prompt_set"])
    for backend in ("gdino", "yoloe"):
        assert pf.build_plan(backend).texts(), (name, backend)
    print("OK", pf.resolved_set_id())
EOF
```

Expected: tres líneas `OK <id>`.

### Task 4: Documentación de la metodología

**Files:**
- Create: `docs/prompt-strategy.md`
- Modify: `docs/prompt-sets.md` (sección 2 "Formato" + nueva sección de ciclo de vida)
- Modify: `README.md` (sección 5 y layout de la sección 2)

**Interfaces:**
- Consumes: spec `docs/superpowers/specs/2026-07-17-prompt-strategy-design.md` (fuente; no repetir — resumir y referenciar).

- [ ] **Step 1: Crear `docs/prompt-strategy.md`**

Contenido (en español, mismo tono que `prompt-sets.md`); secciones:

1. **Qué es este documento**: metodología y programa de estudios de prompts; se subordina al doc núcleo 12 del repo `docs` (enmendado 2026-07-17: pista doble GDINO-tiny primaria + YOLOE-26s réplica) y al spec `docs/superpowers/specs/2026-07-17-prompt-strategy-design.md`. `prompt-sets.md` queda como referencia de formato.
2. **Taxonomía**: la tabla de ejes del spec §1 (copiar la tabla completa: `canonical_positive`/`syntactic_negation`/`specificity`/`observable_state`/`presence_template`, con ejemplos CR-01 y rol), + las 3 reglas transversales (sinónimos solo pre-freeze; presupuesto de caption medido con aislado-vs-completo; fraseo por backend se conserva) + la migración por rol de los valores históricos.
3. **Ciclo de vida**: estados y transiciones (spec §2.1), alcance de la inmutabilidad y `frozen_sha256` (fórmula exacta del hash, la de Global Constraints), lineage/naming (spec §2.2), regla de promoción (§2.3), trazabilidad (§2.4).
4. **Programa de estudios**: las tres tablas de carriles del spec §4 (núcleo / exploración pre-freeze / demo) + el mapa a la narrativa de tesis.
5. **Gestión desde la webconsole**: resumen del spec §3 (YAML fuente de verdad, editor estructurado, tres garantías, la consola nunca commitea).

- [ ] **Step 2: Actualizar `docs/prompt-sets.md`**

(a) En el bloque de formato de la sección 2, agregar después de `language: en`:

```yaml
  status: exploratory       # exploratory | frozen_pending_review | frozen (ver docs/prompt-strategy.md)
  track: core               # core | demo (demo = carril demostrativo, fuera del protocolo comparativo)
  derives_from: <id>        # opcional: set del que deriva (lineage)
  changes: "..."            # opcional: qué cambió respecto de derives_from y por qué
  frozen_sha256: "<hex>"    # solo en frozen: sha256 del bloque classes (lo calcula la webconsole al congelar)
```

(b) En las "Reglas de resolución", actualizar la línea de `strategy`: los valores son la taxonomía de ejes de `docs/prompt-strategy.md` (`canonical_positive`, `syntactic_negation`, `specificity`, `observable_state`, `presence_template`; `positive_evidence`/`direct_absence` son históricos, solo en sets frozen retro-etiquetados).

(c) En la sección 4 "Sets actuales", actualizar la tabla: los 2 congelados con `status: frozen`; `ppe_v2_descriptive` → `exploratory`; agregar filas para `eind_v1` (frozen_pending_review), `edir_exp_cr01_candidates`, `edir_exp_cr02_candidates`, `edir_exp_weak_classes` (exploratory). En "Congelado vs experimental", remitir el detalle del ciclo de vida a `docs/prompt-strategy.md`.

(d) En la sección 6 "Agregar un prompt set", agregar que la vía recomendada es la webconsole (valida schema y aplica el ciclo de vida) y que editar a mano sigue siendo válido para sets `exploratory`.

- [ ] **Step 3: Actualizar `README.md`**

En el layout (§2): agregar `docs/prompt-strategy.md` con una línea ("metodología, taxonomía de ejes, ciclo de vida y programa de estudios"). En §5, actualizar la lista de prompt sets (7 sets: 2 frozen, 1 frozen_pending_review, 4 exploratory) remitiendo a `docs/prompt-sets.md` §4.

- [ ] **Step 4: Verificación cruzada**

Releer los tres documentos y verificar: (a) la fórmula del hash aparece idéntica en `prompt-strategy.md` y en este plan; (b) los nombres de estados y de ejes son idénticos en `prompt-strategy.md`, `prompt-sets.md` y los YAML de Tasks 1–3; (c) ningún doc dice que la consola commitea.

---

## Parte B — Gestión desde la webconsole

### Task 5: Módulo `prompt_store` del BFF (validación, hash, transiciones)

**Files:**
- Create: `webconsole/backend/src/eovrt_webconsole/prompt_store.py`
- Test: `webconsole/backend/tests/test_prompt_store.py`

**Interfaces:**
- Consumes: `settings.prompts_dir: Path` (existente en `ConsoleSettings`).
- Produces (los usa Task 6):
  - `class PromptStoreError(Exception)` y subclases `PromptSetNotFound`, `PromptSetExists`, `FrozenSetImmutable`, `InvalidTransition`, `PromptSetInvalid` (esta última envuelve `pydantic.ValidationError`; atributo `.errors: list`)
  - `classes_sha256(classes_raw: list) -> str`
  - `PromptSetModel` (Pydantic; campos: `id, description, language, status, track, derives_from, changes, frozen_sha256, classes: list[PromptClassModel]`)
  - `list_sets(prompts_dir: Path) -> list[dict]` (resúmenes: `id, description, status, track, derives_from, n_classes, n_phrases`)
  - `get_set(prompts_dir, set_id) -> dict` (el mapping `prompt_set` crudo; raise `PromptSetNotFound`)
  - `create_set(prompts_dir, payload: dict) -> dict` (valida; fuerza requisito `status == "exploratory"`; raise `PromptSetExists`)
  - `update_set(prompts_dir, set_id, payload: dict) -> dict` (solo sobre `exploratory`; el `status` del payload debe ser `exploratory`; `id` del payload == `set_id`)
  - `delete_set(prompts_dir, set_id) -> None` (solo `exploratory`)
  - `request_freeze(prompts_dir, set_id) -> dict` (`exploratory → frozen_pending_review`)
  - `confirm_freeze(prompts_dir, set_id) -> dict` (`frozen_pending_review → frozen`; calcula y escribe `frozen_sha256`)
  - `derive_set(prompts_dir, source_id, new_id, changes: str) -> dict` (copia cualquier set → nuevo `exploratory` con `derives_from`/`changes`, sin `frozen_sha256`)

- [ ] **Step 1: Escribir los tests que fallan**

`webconsole/backend/tests/test_prompt_store.py`:

```python
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from eovrt_webconsole import prompt_store as ps

EXPLORATORY = {
    "id": "exp_set",
    "description": "set exploratorio",
    "language": "en",
    "status": "exploratory",
    "track": "core",
    "classes": [
        {"id": "person", "strategy": "canonical_positive",
         "phrasings": {"default": ["person"]}},
    ],
}


@pytest.fixture
def prompts_dir(tmp_path: Path) -> Path:
    d = tmp_path / "prompts"
    d.mkdir()
    return d


def _write(prompts_dir: Path, payload: dict) -> Path:
    path = prompts_dir / f"{payload['id']}.yaml"
    path.write_text(yaml.safe_dump({"prompt_set": payload}, sort_keys=False, allow_unicode=True))
    return path


def test_classes_sha256_matches_convention():
    classes = EXPLORATORY["classes"]
    expected = hashlib.sha256(
        json.dumps(classes, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode()
    ).hexdigest()
    assert ps.classes_sha256(classes) == expected


def test_create_get_list_roundtrip(prompts_dir: Path):
    created = ps.create_set(prompts_dir, EXPLORATORY)
    assert created["id"] == "exp_set"
    assert ps.get_set(prompts_dir, "exp_set")["status"] == "exploratory"
    summaries = ps.list_sets(prompts_dir)
    assert [s["id"] for s in summaries] == ["exp_set"]
    assert summaries[0]["n_classes"] == 1 and summaries[0]["n_phrases"] == 1


def test_create_rejects_existing_and_non_exploratory(prompts_dir: Path):
    ps.create_set(prompts_dir, EXPLORATORY)
    with pytest.raises(ps.PromptSetExists):
        ps.create_set(prompts_dir, EXPLORATORY)
    frozen_payload = {**EXPLORATORY, "id": "otro", "status": "frozen"}
    with pytest.raises(ps.PromptSetInvalid):
        ps.create_set(prompts_dir, frozen_payload)


def test_create_rejects_bad_strategy_and_empty_phrasings(prompts_dir: Path):
    bad = {**EXPLORATORY, "classes": [
        {"id": "x", "strategy": "inventada", "phrasings": {"default": ["x"]}}]}
    with pytest.raises(ps.PromptSetInvalid):
        ps.create_set(prompts_dir, bad)
    empty = {**EXPLORATORY, "classes": [{"id": "x", "phrasings": {"gdino": []}}]}
    with pytest.raises(ps.PromptSetInvalid):
        ps.create_set(prompts_dir, empty)


def test_update_only_exploratory_and_no_status_change(prompts_dir: Path):
    ps.create_set(prompts_dir, EXPLORATORY)
    updated = ps.update_set(prompts_dir, "exp_set", {**EXPLORATORY, "description": "v2"})
    assert updated["description"] == "v2"
    with pytest.raises(ps.PromptSetInvalid):
        ps.update_set(prompts_dir, "exp_set", {**EXPLORATORY, "status": "frozen"})
    _write(prompts_dir, {**EXPLORATORY, "id": "congelado", "status": "frozen",
                         "frozen_sha256": ps.classes_sha256(EXPLORATORY["classes"])})
    with pytest.raises(ps.FrozenSetImmutable):
        ps.update_set(prompts_dir, "congelado", {**EXPLORATORY, "id": "congelado"})


def test_freeze_flow(prompts_dir: Path):
    ps.create_set(prompts_dir, EXPLORATORY)
    pending = ps.request_freeze(prompts_dir, "exp_set")
    assert pending["status"] == "frozen_pending_review"
    with pytest.raises(ps.InvalidTransition):
        ps.request_freeze(prompts_dir, "exp_set")
    frozen = ps.confirm_freeze(prompts_dir, "exp_set")
    assert frozen["status"] == "frozen"
    assert frozen["frozen_sha256"] == ps.classes_sha256(frozen["classes"])
    with pytest.raises(ps.InvalidTransition):
        ps.confirm_freeze(prompts_dir, "exp_set")
    with pytest.raises(ps.FrozenSetImmutable):
        ps.delete_set(prompts_dir, "exp_set")


def test_confirm_freeze_requires_pending(prompts_dir: Path):
    ps.create_set(prompts_dir, EXPLORATORY)
    with pytest.raises(ps.InvalidTransition):
        ps.confirm_freeze(prompts_dir, "exp_set")


def test_derive_from_frozen(prompts_dir: Path):
    ps.create_set(prompts_dir, EXPLORATORY)
    ps.request_freeze(prompts_dir, "exp_set")
    ps.confirm_freeze(prompts_dir, "exp_set")
    derived = ps.derive_set(prompts_dir, "exp_set", "exp_set_v2", changes="prueba de derivación")
    assert derived["status"] == "exploratory"
    assert derived["derives_from"] == "exp_set"
    assert derived["changes"] == "prueba de derivación"
    assert "frozen_sha256" not in derived
    assert (prompts_dir / "exp_set_v2.yaml").is_file()


def test_delete_exploratory(prompts_dir: Path):
    ps.create_set(prompts_dir, EXPLORATORY)
    ps.delete_set(prompts_dir, "exp_set")
    with pytest.raises(ps.PromptSetNotFound):
        ps.get_set(prompts_dir, "exp_set")


def test_repo_frozen_sets_integrity():
    """Contrato sobre los sets REALES del repo: todo frozen tiene hash válido."""
    repo_prompts = Path(__file__).resolve().parents[3] / "prompts"
    frozen = 0
    for path in sorted(repo_prompts.glob("*.yaml")):
        data = yaml.safe_load(path.read_text())["prompt_set"]
        ps.PromptSetModel.model_validate(data)  # el espejo acepta todos los sets reales
        if data.get("status") == "frozen":
            frozen += 1
            assert data["frozen_sha256"] == ps.classes_sha256(data["classes"]), path.name
    assert frozen >= 2  # cr01_cr02_v2_short + cr01_cr02_bench_v2 (Task 1)
```

- [ ] **Step 2: Correr y verificar que fallan**

Run: `cd webconsole/backend && .venv/bin/python -m pytest tests/test_prompt_store.py -q`
Expected: FAIL/ERROR con `ModuleNotFoundError: ... prompt_store` (o ImportError).

- [ ] **Step 3: Implementar `prompt_store.py`**

```python
"""Almacén de prompt sets sobre prompts/ — los YAML son la fuente de verdad.

Spec: docs/superpowers/specs/2026-07-17-prompt-strategy-design.md §2/§3.
PromptSetModel es un ESPEJO MÍNIMO de eovrt_media.config.schemas.PromptSet
(+ campos de ciclo de vida): la consola no depende de eovrt_media; el
validador final sigue siendo el media-plane en POST /api/runs.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ValidationError, model_validator

STRATEGY_VALUES = frozenset({
    "canonical_positive", "syntactic_negation", "specificity",
    "observable_state", "presence_template",
    # históricos: solo en sets frozen retro-etiquetados, no usar en sets nuevos
    "positive_evidence", "direct_absence",
})

Status = Literal["exploratory", "frozen_pending_review", "frozen"]


class PromptStoreError(Exception):
    pass


class PromptSetNotFound(PromptStoreError):
    pass


class PromptSetExists(PromptStoreError):
    pass


class FrozenSetImmutable(PromptStoreError):
    pass


class InvalidTransition(PromptStoreError):
    pass


class PromptSetInvalid(PromptStoreError):
    def __init__(self, errors: list):
        self.errors = errors
        super().__init__(f"Prompt set inválido: {errors}")


class PromptClassModel(BaseModel):
    id: str
    canonical: str | None = None
    role: str | None = None
    strategy: str | None = None
    condition_id: str | None = None
    enabled_by_default: bool = True
    phrasings: dict[str, list[str]]

    @model_validator(mode="after")
    def _check(self) -> PromptClassModel:
        if self.strategy is not None and self.strategy not in STRATEGY_VALUES:
            raise ValueError(
                f"strategy desconocida: {self.strategy!r} (taxonomía: docs/prompt-strategy.md)"
            )
        if not self.phrasings:
            raise ValueError(f"clase {self.id!r} sin phrasings")
        for backend, phrases in self.phrasings.items():
            if not phrases:
                raise ValueError(f"clase {self.id!r}: phrasings[{backend!r}] vacío")
        return self


class PromptSetModel(BaseModel):
    id: str
    description: str | None = None
    language: str | None = None
    status: Status = "exploratory"
    track: Literal["core", "demo"] | None = None
    derives_from: str | None = None
    changes: str | None = None
    frozen_sha256: str | None = None
    classes: list[PromptClassModel]

    @model_validator(mode="after")
    def _check(self) -> PromptSetModel:
        ids = [c.id for c in self.classes]
        if len(ids) != len(set(ids)):
            raise ValueError("ids de clase duplicados")
        if self.status == "frozen" and not self.frozen_sha256:
            raise ValueError("un set frozen requiere frozen_sha256")
        return self


def classes_sha256(classes_raw: list) -> str:
    """Convención única de hash (spec §2.1): sobre el bloque classes CRUDO del YAML."""
    payload = json.dumps(classes_raw, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def _path(prompts_dir: Path, set_id: str) -> Path:
    return prompts_dir / f"{set_id}.yaml"


def _validate(payload: dict) -> dict:
    try:
        PromptSetModel.model_validate(payload)
    except ValidationError as exc:
        raise PromptSetInvalid(exc.errors()) from exc
    return payload


def _read(prompts_dir: Path, set_id: str) -> dict:
    path = _path(prompts_dir, set_id)
    if not path.is_file():
        raise PromptSetNotFound(set_id)
    data = yaml.safe_load(path.read_text())
    prompt_set = (data or {}).get("prompt_set")
    if not isinstance(prompt_set, dict):
        raise PromptSetNotFound(set_id)
    return prompt_set


def _write(prompts_dir: Path, prompt_set: dict) -> None:
    text = yaml.safe_dump({"prompt_set": prompt_set}, sort_keys=False, allow_unicode=True)
    _path(prompts_dir, prompt_set["id"]).write_text(text)


def list_sets(prompts_dir: Path) -> list[dict]:
    out: list[dict] = []
    if not prompts_dir.is_dir():
        return out
    for path in sorted(prompts_dir.glob("*.yaml")):
        data = yaml.safe_load(path.read_text()) if path.is_file() else None
        prompt_set = (data or {}).get("prompt_set") if isinstance(data, dict) else None
        if not isinstance(prompt_set, dict) or "id" not in prompt_set:
            continue
        classes = prompt_set.get("classes", [])
        out.append({
            "id": prompt_set["id"],
            "description": prompt_set.get("description"),
            "status": prompt_set.get("status", "exploratory"),
            "track": prompt_set.get("track"),
            "derives_from": prompt_set.get("derives_from"),
            "n_classes": len(classes),
            "n_phrases": sum(
                len(p) for c in classes for p in (c.get("phrasings") or {}).values()
            ),
        })
    return out


def get_set(prompts_dir: Path, set_id: str) -> dict:
    return _read(prompts_dir, set_id)


def create_set(prompts_dir: Path, payload: dict) -> dict:
    _validate(payload)
    if payload.get("status", "exploratory") != "exploratory":
        raise PromptSetInvalid([{"msg": "un set nuevo nace exploratory"}])
    if _path(prompts_dir, payload["id"]).exists():
        raise PromptSetExists(payload["id"])
    payload = {**payload, "status": "exploratory"}
    _write(prompts_dir, payload)
    return payload


def update_set(prompts_dir: Path, set_id: str, payload: dict) -> dict:
    current = _read(prompts_dir, set_id)
    if current.get("status", "exploratory") != "exploratory":
        raise FrozenSetImmutable(set_id)
    if payload.get("id") != set_id:
        raise PromptSetInvalid([{"msg": "el id no coincide con el set"}])
    if payload.get("status", "exploratory") != "exploratory":
        raise PromptSetInvalid([{"msg": "status solo cambia por acciones explícitas"}])
    _validate(payload)
    _write(prompts_dir, payload)
    return payload


def delete_set(prompts_dir: Path, set_id: str) -> None:
    current = _read(prompts_dir, set_id)
    if current.get("status", "exploratory") != "exploratory":
        raise FrozenSetImmutable(set_id)
    _path(prompts_dir, set_id).unlink()


def request_freeze(prompts_dir: Path, set_id: str) -> dict:
    current = _read(prompts_dir, set_id)
    if current.get("status", "exploratory") != "exploratory":
        raise InvalidTransition(f"{set_id}: {current.get('status')} → frozen_pending_review")
    current["status"] = "frozen_pending_review"
    _write(prompts_dir, current)
    return current


def confirm_freeze(prompts_dir: Path, set_id: str) -> dict:
    current = _read(prompts_dir, set_id)
    if current.get("status") != "frozen_pending_review":
        raise InvalidTransition(f"{set_id}: {current.get('status')} → frozen")
    current["status"] = "frozen"
    current["frozen_sha256"] = classes_sha256(current["classes"])
    _write(prompts_dir, current)
    return current


def derive_set(prompts_dir: Path, source_id: str, new_id: str, changes: str) -> dict:
    source = _read(prompts_dir, source_id)
    if _path(prompts_dir, new_id).exists():
        raise PromptSetExists(new_id)
    if not changes or not changes.strip():
        raise PromptSetInvalid([{"msg": "derivar requiere changes (qué cambia y por qué)"}])
    derived = {k: v for k, v in source.items() if k != "frozen_sha256"}
    derived.update(id=new_id, status="exploratory", derives_from=source_id, changes=changes)
    _validate(derived)
    _write(prompts_dir, derived)
    return derived
```

- [ ] **Step 4: Correr los tests**

Run: `cd webconsole/backend && .venv/bin/python -m pytest tests/test_prompt_store.py -q`
Expected: todos PASS (incluido `test_repo_frozen_sets_integrity`, que valida los YAML reales retro-etiquetados en Task 1 — si falla, el hash o el retro-etiquetado están mal: arreglar el YAML, no el test).

- [ ] **Step 5: Lint**

Run: `cd webconsole/backend && .venv/bin/python -m ruff check src tests`
Expected: sin errores.

### Task 6: Router `/api/prompt-sets` + integración con el catálogo

**Files:**
- Create: `webconsole/backend/src/eovrt_webconsole/routers/prompts.py`
- Modify: `webconsole/backend/src/eovrt_webconsole/app.py` (agregar `app.include_router(prompts.router)` junto a los demás includes, y el import correspondiente en la línea de imports de routers)
- Modify: `webconsole/backend/src/eovrt_webconsole/repo_catalog.py:17-43` (`list_prompt_sets`: exponer `status`/`track` y derivar `frozen` también del YAML)
- Test: `webconsole/backend/tests/test_prompts_router.py`

**Interfaces:**
- Consumes: `prompt_store` completo (Task 5); `request.app.state.settings.prompts_dir` (patrón de `routers/catalog.py`); fixtures `repo`/`settings`/`client` de `tests/conftest.py` (el fixture `repo` ya crea `prompts/demo_set.yaml` exploratory-por-default y `prompts/frozen_set.yaml`).
- Produces: endpoints REST:
  - `GET /api/prompt-sets` → `list_sets` (resúmenes con status/track)
  - `GET /api/prompt-sets/{set_id}` → set completo | 404
  - `POST /api/prompt-sets` (body = mapping `prompt_set`) → 201 | 409 existe | 422 inválido
  - `PUT /api/prompt-sets/{set_id}` → 200 | 404 | 409 frozen | 422
  - `DELETE /api/prompt-sets/{set_id}` → 204 | 404 | 409 frozen
  - `POST /api/prompt-sets/{set_id}/freeze-request` → 200 | 409 transición inválida
  - `POST /api/prompt-sets/{set_id}/freeze` → 200 (calcula hash) | 409
  - `POST /api/prompt-sets/{set_id}/derive` (body `{"new_id": str, "changes": str}`) → 201 | 409 | 422
- Nota de compatibilidad: `GET /api/catalog/prompt-sets` (existente, lo consume ComposePage) no cambia de shape — solo agrega claves `status`/`track` y su `frozen` pasa a ser `status=="frozen" OR id in frozen_set_ids` (el env `EOVRT_CONSOLE_FROZEN_SETS` queda como override legacy).

- [ ] **Step 1: Escribir los tests que fallan**

`webconsole/backend/tests/test_prompts_router.py`:

```python
from __future__ import annotations

NEW_SET = {
    "id": "nuevo_set",
    "description": "creado por test",
    "status": "exploratory",
    "classes": [
        {"id": "person", "strategy": "canonical_positive",
         "phrasings": {"default": ["person"]}},
    ],
}


def test_list_and_get(client):
    sets = client.get("/api/prompt-sets").json()
    ids = {s["id"] for s in sets}
    assert {"demo_set", "frozen_set"} <= ids
    detail = client.get("/api/prompt-sets/demo_set")
    assert detail.status_code == 200
    assert detail.json()["classes"]
    assert client.get("/api/prompt-sets/inexistente").status_code == 404


def test_create_update_delete_cycle(client):
    assert client.post("/api/prompt-sets", json=NEW_SET).status_code == 201
    assert client.post("/api/prompt-sets", json=NEW_SET).status_code == 409
    updated = {**NEW_SET, "description": "v2"}
    assert client.put("/api/prompt-sets/nuevo_set", json=updated).status_code == 200
    assert client.get("/api/prompt-sets/nuevo_set").json()["description"] == "v2"
    assert client.delete("/api/prompt-sets/nuevo_set").status_code == 204
    assert client.get("/api/prompt-sets/nuevo_set").status_code == 404


def test_invalid_payload_is_422(client):
    bad = {**NEW_SET, "id": "malo",
           "classes": [{"id": "x", "strategy": "inventada",
                        "phrasings": {"default": ["x"]}}]}
    response = client.post("/api/prompt-sets", json=bad)
    assert response.status_code == 422
    assert response.json()["detail"]


def test_freeze_flow_and_immutability(client):
    client.post("/api/prompt-sets", json=NEW_SET)
    assert client.post("/api/prompt-sets/nuevo_set/freeze-request").status_code == 200
    assert client.put("/api/prompt-sets/nuevo_set",
                      json={**NEW_SET, "description": "tarde"}).status_code == 409
    frozen = client.post("/api/prompt-sets/nuevo_set/freeze")
    assert frozen.status_code == 200
    assert frozen.json()["frozen_sha256"]
    assert client.put("/api/prompt-sets/nuevo_set", json=NEW_SET).status_code == 409
    assert client.delete("/api/prompt-sets/nuevo_set").status_code == 409
    assert client.post("/api/prompt-sets/nuevo_set/freeze").status_code == 409


def test_derive(client):
    body = {"new_id": "demo_set_v2", "changes": "prueba"}
    created = client.post("/api/prompt-sets/demo_set/derive", json=body)
    assert created.status_code == 201
    data = created.json()
    assert data["derives_from"] == "demo_set" and data["status"] == "exploratory"
    assert client.post("/api/prompt-sets/demo_set/derive", json=body).status_code == 409
    sin_changes = {"new_id": "otro", "changes": "  "}
    assert client.post("/api/prompt-sets/demo_set/derive", json=sin_changes).status_code == 422


def test_catalog_exposes_status_and_yaml_frozen(client):
    sets = {s["id"]: s for s in client.get("/api/catalog/prompt-sets").json()}
    # frozen_set viene del env de settings (legacy override) sin status en el YAML
    assert sets["frozen_set"]["frozen"] is True
    assert sets["demo_set"]["frozen"] is False
    assert sets["demo_set"]["status"] == "exploratory"
    # un set con status frozen en el YAML queda frozen aunque no esté en el env
    client.post("/api/prompt-sets", json=NEW_SET)
    client.post("/api/prompt-sets/nuevo_set/freeze-request")
    client.post("/api/prompt-sets/nuevo_set/freeze")
    sets = {s["id"]: s for s in client.get("/api/catalog/prompt-sets").json()}
    assert sets["nuevo_set"]["frozen"] is True and sets["nuevo_set"]["status"] == "frozen"
```

- [ ] **Step 2: Correr y verificar que fallan**

Run: `cd webconsole/backend && .venv/bin/python -m pytest tests/test_prompts_router.py -q`
Expected: FAIL — 404 en todos los `/api/prompt-sets` (router inexistente) y KeyError `status` en el test de catálogo.

- [ ] **Step 3: Implementar el router**

`webconsole/backend/src/eovrt_webconsole/routers/prompts.py`:

```python
"""Gestión de prompt sets (spec 2026-07-17 §3): CRUD + ciclo de vida sobre prompts/."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from eovrt_webconsole import prompt_store as ps

router = APIRouter(prefix="/api/prompt-sets")


def _prompts_dir(request: Request):
    return request.app.state.settings.prompts_dir


def _raise(exc: ps.PromptStoreError) -> None:
    if isinstance(exc, ps.PromptSetNotFound):
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if isinstance(exc, (ps.PromptSetExists, ps.FrozenSetImmutable, ps.InvalidTransition)):
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if isinstance(exc, ps.PromptSetInvalid):
        raise HTTPException(status_code=422, detail=exc.errors) from exc
    raise exc


@router.get("")
def list_prompt_sets(request: Request) -> list[dict]:
    return ps.list_sets(_prompts_dir(request))


@router.get("/{set_id}")
def get_prompt_set(request: Request, set_id: str) -> dict:
    try:
        return ps.get_set(_prompts_dir(request), set_id)
    except ps.PromptStoreError as exc:
        _raise(exc)


@router.post("", status_code=201)
def create_prompt_set(request: Request, payload: dict) -> dict:
    try:
        return ps.create_set(_prompts_dir(request), payload)
    except ps.PromptStoreError as exc:
        _raise(exc)


@router.put("/{set_id}")
def update_prompt_set(request: Request, set_id: str, payload: dict) -> dict:
    try:
        return ps.update_set(_prompts_dir(request), set_id, payload)
    except ps.PromptStoreError as exc:
        _raise(exc)


@router.delete("/{set_id}", status_code=204)
def delete_prompt_set(request: Request, set_id: str) -> Response:
    try:
        ps.delete_set(_prompts_dir(request), set_id)
    except ps.PromptStoreError as exc:
        _raise(exc)
    return Response(status_code=204)


@router.post("/{set_id}/freeze-request")
def freeze_request(request: Request, set_id: str) -> dict:
    try:
        return ps.request_freeze(_prompts_dir(request), set_id)
    except ps.PromptStoreError as exc:
        _raise(exc)


@router.post("/{set_id}/freeze")
def freeze(request: Request, set_id: str) -> dict:
    try:
        return ps.confirm_freeze(_prompts_dir(request), set_id)
    except ps.PromptStoreError as exc:
        _raise(exc)


class DeriveBody(BaseModel):
    new_id: str
    changes: str


@router.post("/{set_id}/derive", status_code=201)
def derive(request: Request, set_id: str, body: DeriveBody) -> dict:
    try:
        return ps.derive_set(_prompts_dir(request), set_id, body.new_id, body.changes)
    except ps.PromptStoreError as exc:
        _raise(exc)
```

En `app.py`: agregar `prompts` al import de routers existente y `app.include_router(prompts.router)` junto a los demás (después de `catalog`).

En `repo_catalog.py`, dentro del dict que arma `list_prompt_sets`, reemplazar la línea `"frozen": prompt_set["id"] in frozen_ids,` por:

```python
                "status": prompt_set.get("status", "exploratory"),
                "track": prompt_set.get("track"),
                "frozen": (
                    prompt_set.get("status") == "frozen" or prompt_set["id"] in frozen_ids
                ),
```

- [ ] **Step 4: Correr los tests nuevos y TODA la suite (regresión)**

Run: `cd webconsole/backend && .venv/bin/python -m pytest -q`
Expected: PASS completo (los tests existentes de catálogo/compose no deben romperse: el shape solo ganó claves).

- [ ] **Step 5: Lint**

Run: `cd webconsole/backend && .venv/bin/python -m ruff check src tests`
Expected: sin errores.

### Task 7: SPA — API client, tipos y página de listado/detalle

**Files:**
- Modify: `webconsole/frontend/src/types.ts` (extender `PromptSet` + tipos nuevos)
- Modify: `webconsole/frontend/src/api.ts` (funciones nuevas)
- Create: `webconsole/frontend/src/pages/PromptSetsPage.tsx`
- Modify: `webconsole/frontend/src/App.tsx` (ruta + entrada de navegación "Prompts", siguiendo el patrón de las rutas existentes)
- Test: `webconsole/frontend/src/__tests__/PromptSetsPage.test.tsx`

**Interfaces:**
- Consumes: endpoints de Task 6; `request<T>` y `ApiError` de `api.ts`.
- Produces (los usa Task 8): tipos `PromptSetDetail`, `PromptClassSpec`, `PromptSetSummary`; funciones `listPromptSets()`, `getPromptSetDetail(id)`, `createPromptSet(set)`, `updatePromptSet(id, set)`, `deletePromptSet(id)`, `requestFreeze(id)`, `confirmFreeze(id)`, `derivePromptSet(id, newId, changes)`; página `PromptSetsPage` con estado `selected` y callback interno `refresh()`.

- [ ] **Step 1: Tipos** — en `types.ts` agregar (sin tocar el `PromptSet` existente que usa ComposePage, solo extenderlo con `status?: string; track?: string | null`):

```typescript
export interface PromptClassSpec {
  id: string
  canonical?: string | null
  role?: string | null
  strategy?: string | null
  condition_id?: string | null
  enabled_by_default?: boolean
  phrasings: Record<string, string[]>
}

export interface PromptSetSummary {
  id: string
  description?: string | null
  status: string
  track?: string | null
  derives_from?: string | null
  n_classes: number
  n_phrases: number
}

export interface PromptSetDetail {
  id: string
  description?: string | null
  language?: string | null
  status?: string
  track?: string | null
  derives_from?: string | null
  changes?: string | null
  frozen_sha256?: string | null
  classes: PromptClassSpec[]
}
```

- [ ] **Step 2: API client** — en `api.ts` (mismo estilo que las existentes):

```typescript
export const listPromptSets = () => request<PromptSetSummary[]>('/api/prompt-sets')
export const getPromptSetDetail = (id: string) =>
  request<PromptSetDetail>(`/api/prompt-sets/${id}`)
export const createPromptSet = (set: PromptSetDetail) =>
  request<PromptSetDetail>('/api/prompt-sets', { method: 'POST', body: JSON.stringify(set) })
export const updatePromptSet = (id: string, set: PromptSetDetail) =>
  request<PromptSetDetail>(`/api/prompt-sets/${id}`, { method: 'PUT', body: JSON.stringify(set) })
export const deletePromptSet = (id: string) =>
  request<void>(`/api/prompt-sets/${id}`, { method: 'DELETE' })
export const requestFreeze = (id: string) =>
  request<PromptSetDetail>(`/api/prompt-sets/${id}/freeze-request`, { method: 'POST' })
export const confirmFreeze = (id: string) =>
  request<PromptSetDetail>(`/api/prompt-sets/${id}/freeze`, { method: 'POST' })
export const derivePromptSet = (id: string, newId: string, changes: string) =>
  request<PromptSetDetail>(`/api/prompt-sets/${id}/derive`, {
    method: 'POST',
    body: JSON.stringify({ new_id: newId, changes }),
  })
```

(Agregar los imports de tipos correspondientes al bloque `import type` — y tener en cuenta que `deletePromptSet` responde 204 sin body: si `request<T>` hace `response.json()` incondicional, ajustarlo para devolver `undefined` cuando `response.status === 204`.)

- [ ] **Step 3: Test de la página (falla primero)**

`__tests__/PromptSetsPage.test.tsx`, siguiendo el patrón de mocks de `ComposePage.test.tsx` (mock de `api.ts` con `vi.mock`):

Nota de tooling (verificado 2026-07-17): el frontend NO tiene `@testing-library/user-event`; el patrón del repo es `fireEvent` (ver `ComposePage.test.tsx`). Usarlo en todos los tests nuevos.

```tsx
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import PromptSetsPage from '../pages/PromptSetsPage'
import * as api from '../api'

vi.mock('../api')

const SUMMARIES = [
  { id: 'eind_v1', description: 'núcleo', status: 'frozen_pending_review',
    track: 'core', derives_from: 'cr01_cr02_v2_short', n_classes: 3, n_phrases: 9 },
  { id: 'cr01_cr02_bench_v2', description: 'BENCH', status: 'frozen',
    track: 'core', derives_from: null, n_classes: 4, n_phrases: 4 },
]

const FROZEN_DETAIL = {
  id: 'cr01_cr02_bench_v2', status: 'frozen', frozen_sha256: 'abc123',
  classes: [{ id: 'person', phrasings: { default: ['person'] } }],
}

describe('PromptSetsPage', () => {
  it('lista los sets con badge de estado', async () => {
    vi.mocked(api.listPromptSets).mockResolvedValue(SUMMARIES)
    render(<PromptSetsPage />)
    await waitFor(() => expect(screen.getByText('eind_v1')).toBeInTheDocument())
    expect(screen.getByText('frozen_pending_review')).toBeInTheDocument()
    expect(screen.getByText('frozen')).toBeInTheDocument()
  })

  it('un set frozen se muestra read-only con acción Derivar', async () => {
    vi.mocked(api.listPromptSets).mockResolvedValue(SUMMARIES)
    vi.mocked(api.getPromptSetDetail).mockResolvedValue(FROZEN_DETAIL)
    render(<PromptSetsPage />)
    await waitFor(() => screen.getByText('cr01_cr02_bench_v2'))
    fireEvent.click(screen.getByText('cr01_cr02_bench_v2'))
    await waitFor(() => expect(screen.getByText(/inmutable/i)).toBeInTheDocument())
    expect(screen.queryByRole('button', { name: /guardar/i })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /derivar/i })).toBeInTheDocument()
  })
})
```

Run: `cd webconsole/frontend && npx vitest run src/__tests__/PromptSetsPage.test.tsx`
Expected: FAIL (módulo `../pages/PromptSetsPage` inexistente).

- [ ] **Step 4: Implementar `PromptSetsPage.tsx`** (listado + panel de detalle; la edición llega en Task 8 — acá el detalle es read-only para todos los estados, con el editor enchufable):

```tsx
import { useCallback, useEffect, useState } from 'react'
import {
  getPromptSetDetail, listPromptSets,
} from '../api'
import type { PromptSetDetail, PromptSetSummary } from '../types'
import PromptSetEditor from '../components/PromptSetEditor'

const STATUS_LABEL: Record<string, string> = {
  exploratory: 'exploratory',
  frozen_pending_review: 'frozen_pending_review',
  frozen: 'frozen',
}

export default function PromptSetsPage() {
  const [sets, setSets] = useState<PromptSetSummary[]>([])
  const [selected, setSelected] = useState<PromptSetDetail | null>(null)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    try {
      setSets(await listPromptSets())
    } catch {
      setError('No se pudieron cargar los prompt sets')
    }
  }, [])

  useEffect(() => { void refresh() }, [refresh])

  const open = async (id: string) => {
    setSelected(await getPromptSetDetail(id))
  }

  return (
    <div className="prompt-sets-page">
      <h2>Prompt sets</h2>
      {error && <p role="alert">{error}</p>}
      <table>
        <thead>
          <tr><th>id</th><th>estado</th><th>track</th><th>clases</th><th>frases</th><th>deriva de</th></tr>
        </thead>
        <tbody>
          {sets.map((s) => (
            <tr key={s.id} onClick={() => void open(s.id)} style={{ cursor: 'pointer' }}>
              <td>{s.id}</td>
              <td><span className={`badge badge-${s.status}`}>{STATUS_LABEL[s.status] ?? s.status}</span></td>
              <td>{s.track ?? ''}</td>
              <td>{s.n_classes}</td>
              <td>{s.n_phrases}</td>
              <td>{s.derives_from ?? ''}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {selected && (
        <PromptSetEditor
          key={selected.id}
          initial={selected}
          onChanged={async () => { await refresh(); setSelected(null) }}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  )
}
```

Nota: `PromptSetEditor` se crea en Task 8; para que ESTE task cierre en verde, crear en este task una versión mínima read-only de `components/PromptSetEditor.tsx` que Task 8 reemplaza:

```tsx
import type { PromptSetDetail } from '../types'

interface Props {
  initial: PromptSetDetail
  onChanged: () => Promise<void> | void
  onClose: () => void
}

export default function PromptSetEditor({ initial, onClose }: Props) {
  const frozen = initial.status === 'frozen'
  return (
    <section className="prompt-set-editor">
      <h3>{initial.id}</h3>
      {frozen && <p>Set congelado — inmutable (sha256: {initial.frozen_sha256}).</p>}
      <ul>
        {initial.classes.map((c) => (
          <li key={c.id}>
            <strong>{c.id}</strong> {c.strategy ?? ''} — {JSON.stringify(c.phrasings)}
          </li>
        ))}
      </ul>
      {frozen && <button type="button">Derivar set nuevo</button>}
      <button type="button" onClick={onClose}>Cerrar</button>
    </section>
  )
}
```

En `App.tsx` (patrón verificado: react-router-dom v6, `<Link>` en el `<nav>` y `<Route>` en `<Routes>`): agregar `<Link to="/prompts">Prompts</Link>` al nav y `<Route path="/prompts" element={<PromptSetsPage />} />` a las rutas, con su import.

- [ ] **Step 5: Correr tests del frontend**

Run: `cd webconsole/frontend && npx vitest run`
Expected: PASS completo (los nuevos y los existentes).

### Task 8: SPA — editor estructurado con ciclo de vida

**Files:**
- Modify: `webconsole/frontend/src/components/PromptSetEditor.tsx` (reemplaza el mínimo de Task 7)
- Modify: `webconsole/frontend/src/pages/PromptSetsPage.tsx` (botón "Nuevo set")
- Test: `webconsole/frontend/src/__tests__/PromptSetEditor.test.tsx`

**Interfaces:**
- Consumes: `updatePromptSet`, `createPromptSet`, `requestFreeze`, `confirmFreeze`, `derivePromptSet`, `deletePromptSet` (Task 7); tipos `PromptSetDetail`/`PromptClassSpec`; props `{ initial, onChanged, onClose }` (mismas de Task 7; para "Nuevo set" se pasa `initial` con `id: ''`, `status: 'exploratory'`, `classes: []` y prop extra `isNew?: boolean`).
- Produces: editor con las reglas de la spec §3: exploratory editable; frozen_pending_review solo permite confirmar freeze o nada; frozen read-only + derivar; `strategy` como `<select>` con los 5 valores de la taxonomía; `status` jamás editable como campo.

- [ ] **Step 1: Test que falla**

`__tests__/PromptSetEditor.test.tsx`:

```tsx
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import PromptSetEditor from '../components/PromptSetEditor'
import * as api from '../api'

vi.mock('../api')

const EXPLORATORY = {
  id: 'exp_set', status: 'exploratory', track: 'core',
  classes: [{ id: 'person', strategy: 'canonical_positive', phrasings: { default: ['person'] } }],
}

describe('PromptSetEditor', () => {
  it('exploratory: permite editar y guardar via updatePromptSet', async () => {
    vi.mocked(api.updatePromptSet).mockResolvedValue({ ...EXPLORATORY })
    const onChanged = vi.fn()
    render(<PromptSetEditor initial={EXPLORATORY} onChanged={onChanged} onClose={() => {}} />)
    fireEvent.click(screen.getByRole('button', { name: /guardar/i }))
    await waitFor(() => expect(api.updatePromptSet).toHaveBeenCalledWith('exp_set', expect.anything()))
    expect(onChanged).toHaveBeenCalled()
  })

  it('exploratory: strategy es un select con la taxonomía, sin campo status editable', () => {
    render(<PromptSetEditor initial={EXPLORATORY} onChanged={() => {}} onClose={() => {}} />)
    const select = screen.getByLabelText(/strategy/i)
    expect(select.tagName).toBe('SELECT')
    expect(screen.queryByLabelText(/^status$/i)).not.toBeInTheDocument()
  })

  it('freeze flow: pedir congelamiento y confirmar', async () => {
    vi.mocked(api.requestFreeze).mockResolvedValue({ ...EXPLORATORY, status: 'frozen_pending_review' })
    const onChanged = vi.fn()
    render(<PromptSetEditor initial={EXPLORATORY} onChanged={onChanged} onClose={() => {}} />)
    fireEvent.click(screen.getByRole('button', { name: /pedir congelamiento/i }))
    await waitFor(() => expect(api.requestFreeze).toHaveBeenCalledWith('exp_set'))

    vi.mocked(api.confirmFreeze).mockResolvedValue({ ...EXPLORATORY, status: 'frozen', frozen_sha256: 'x' })
    render(<PromptSetEditor
      initial={{ ...EXPLORATORY, status: 'frozen_pending_review' }}
      onChanged={onChanged} onClose={() => {}} />)
    fireEvent.click(screen.getByRole('button', { name: /confirmar freeze/i }))
    await waitFor(() => expect(api.confirmFreeze).toHaveBeenCalledWith('exp_set'))
  })

  it('frozen: sin guardar, con derivar', async () => {
    vi.mocked(api.derivePromptSet).mockResolvedValue({ ...EXPLORATORY, id: 'exp_set_v2' })
    render(<PromptSetEditor
      initial={{ ...EXPLORATORY, status: 'frozen', frozen_sha256: 'x' }}
      onChanged={() => {}} onClose={() => {}} />)
    expect(screen.queryByRole('button', { name: /guardar/i })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /derivar/i }))
    fireEvent.change(screen.getByLabelText(/nuevo id/i), { target: { value: 'exp_set_v2' } })
    fireEvent.change(screen.getByLabelText(/cambios/i), { target: { value: 'ajuste de fraseo' } })
    fireEvent.click(screen.getByRole('button', { name: /crear derivado/i }))
    await waitFor(() =>
      expect(api.derivePromptSet).toHaveBeenCalledWith('exp_set', 'exp_set_v2', 'ajuste de fraseo'))
  })
})
```

Run: `cd webconsole/frontend && npx vitest run src/__tests__/PromptSetEditor.test.tsx`
Expected: FAIL (el editor mínimo de Task 7 no tiene estas acciones).

- [ ] **Step 2: Implementar el editor completo**

Reemplazar `components/PromptSetEditor.tsx`. Puntos obligatorios (el implementador tiene libertad de layout, no de comportamiento):

```tsx
import { useState } from 'react'
import {
  confirmFreeze, createPromptSet, deletePromptSet, derivePromptSet,
  requestFreeze, updatePromptSet,
} from '../api'
import type { PromptClassSpec, PromptSetDetail } from '../types'

const STRATEGIES = [
  'canonical_positive', 'syntactic_negation', 'specificity',
  'observable_state', 'presence_template',
]

interface Props {
  initial: PromptSetDetail
  onChanged: () => Promise<void> | void
  onClose: () => void
  isNew?: boolean
}

export default function PromptSetEditor({ initial, onChanged, onClose, isNew }: Props) {
  const [draft, setDraft] = useState<PromptSetDetail>(initial)
  const [deriveOpen, setDeriveOpen] = useState(false)
  const [newId, setNewId] = useState('')
  const [changes, setChanges] = useState('')
  const [error, setError] = useState<string | null>(null)

  const status = initial.status ?? 'exploratory'
  const editable = isNew || status === 'exploratory'

  const run = async (action: () => Promise<unknown>) => {
    try {
      setError(null)
      await action()
      await onChanged()
    } catch (e) {
      setError(String((e as { payload?: { detail?: unknown } }).payload?.detail ?? e))
    }
  }

  const setClass = (i: number, patch: Partial<PromptClassSpec>) =>
    setDraft((d) => ({
      ...d,
      classes: d.classes.map((c, j) => (j === i ? { ...c, ...patch } : c)),
    }))

  return (
    <section className="prompt-set-editor">
      <h3>{isNew ? 'Nuevo prompt set' : draft.id}</h3>
      {error && <p role="alert">{error}</p>}
      {status === 'frozen' && (
        <p>Set congelado — inmutable (sha256: {initial.frozen_sha256}).</p>
      )}
      {status === 'frozen_pending_review' && (
        <p>Pendiente de revisión del usuario — confirmar freeze cuando la revisión esté hecha.</p>
      )}

      {/* metadata editable solo en exploratory / nuevo */}
      {editable && (
        <>
          {isNew && (
            <label>id
              <input value={draft.id}
                onChange={(e) => setDraft({ ...draft, id: e.target.value })} />
            </label>
          )}
          <label>descripción
            <textarea value={draft.description ?? ''}
              onChange={(e) => setDraft({ ...draft, description: e.target.value })} />
          </label>
        </>
      )}

      <h4>Clases</h4>
      {draft.classes.map((c, i) => (
        <fieldset key={i} disabled={!editable}>
          <label>clase id
            <input value={c.id} onChange={(e) => setClass(i, { id: e.target.value })} />
          </label>
          <label>strategy
            <select value={c.strategy ?? ''}
              onChange={(e) => setClass(i, { strategy: e.target.value || null })}>
              <option value="">(sin strategy)</option>
              {STRATEGIES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </label>
          {Object.entries(c.phrasings).map(([backend, phrases]) => (
            <label key={backend}>{`phrasings.${backend}`}
              <input value={phrases.join('; ')}
                onChange={(e) => setClass(i, {
                  phrasings: {
                    ...c.phrasings,
                    [backend]: e.target.value.split(';').map((p) => p.trim()).filter(Boolean),
                  },
                })} />
            </label>
          ))}
        </fieldset>
      ))}
      {editable && (
        <button type="button"
          onClick={() => setDraft({
            ...draft,
            classes: [...draft.classes, { id: '', phrasings: { default: [] } }],
          })}>
          Agregar clase
        </button>
      )}

      {/* acciones por estado — status NUNCA es un campo editable */}
      {editable && (
        <button type="button"
          onClick={() => void run(() =>
            isNew ? createPromptSet(draft) : updatePromptSet(draft.id, draft))}>
          Guardar
        </button>
      )}
      {status === 'exploratory' && !isNew && (
        <>
          <button type="button" onClick={() => void run(() => requestFreeze(draft.id))}>
            Pedir congelamiento
          </button>
          <button type="button" onClick={() => void run(() => deletePromptSet(draft.id))}>
            Eliminar
          </button>
        </>
      )}
      {status === 'frozen_pending_review' && (
        <button type="button" onClick={() => void run(() => confirmFreeze(draft.id))}>
          Confirmar freeze
        </button>
      )}
      {status === 'frozen' && !deriveOpen && (
        <button type="button" onClick={() => setDeriveOpen(true)}>Derivar set nuevo</button>
      )}
      {deriveOpen && (
        <div>
          <label>nuevo id
            <input value={newId} onChange={(e) => setNewId(e.target.value)} />
          </label>
          <label>cambios
            <input value={changes} onChange={(e) => setChanges(e.target.value)} />
          </label>
          <button type="button"
            onClick={() => void run(() => derivePromptSet(draft.id, newId, changes))}>
            Crear derivado
          </button>
        </div>
      )}
      <button type="button" onClick={onClose}>Cerrar</button>
    </section>
  )
}
```

En `PromptSetsPage.tsx`, agregar un botón "Nuevo set" que abre el editor con
`initial={{ id: '', status: 'exploratory', classes: [] }}` e `isNew`.

- [ ] **Step 3: Correr toda la suite frontend**

Run: `cd webconsole/frontend && npx vitest run`
Expected: PASS completo (incluidos los tests de Task 7, que deben seguir pasando con el editor completo — verifican estados frozen read-only y botón derivar, ambos conservados).

### Task 9: Gate final — regresión completa y cierre documental

**Files:**
- Modify: `webconsole/README.md` (documentar la vista Prompts y los endpoints `/api/prompt-sets`)
- Modify: `docs/prompt-strategy.md` (marcar la sección de webconsole como implementada, con la lista final de endpoints)

**Interfaces:**
- Consumes: todo lo anterior.

- [ ] **Step 1: Suite backend completa** — `cd webconsole/backend && .venv/bin/python -m pytest -q` → PASS; `.venv/bin/python -m ruff check src tests` → limpio.
- [ ] **Step 2: Suite frontend completa + build** — `cd webconsole/frontend && npx vitest run` → PASS; `npm run build` → build OK (la SPA compila con la página nueva).
- [ ] **Step 3: Smoke manual E2E** — levantar el BFF contra el repo real (`make serve` en `webconsole/` o `uvicorn` del backend) y verificar con `python3 -c "import urllib.request, json; print(json.load(urllib.request.urlopen('http://localhost:8090/api/prompt-sets')))"` que lista los 7 sets con sus estados (los 2 frozen con hash, `eind_v1` pending, 4 exploratory). **No usar `curl`** (bloqueado en este entorno).
- [ ] **Step 4: Actualizar `webconsole/README.md`** — sección nueva "Gestión de prompt sets": vista, endpoints, las tres garantías (schema, inmutabilidad por hash, transiciones solo por acciones), y la regla "la consola nunca commitea — los cambios quedan como working tree del repo para revisión y commit del usuario".
- [ ] **Step 5: Actualizar `docs/prompt-strategy.md` §5** con los endpoints implementados.
- [ ] **Step 6: Informar al usuario** el estado final (tests, archivos tocados) y recordar que los cambios están sin commitear en `e-ovrt_experimental-setup` (y el doc 12 en el repo `docs`). No commitear.

---

## Trabajo operativo posterior (fuera de este plan, registrado para no perderlo)

1. Corridas de calibración del carril 2 (mitad calib del BENCH) para elegir finalistas → crear `edir_v1` (vía "derivar" en la consola) → revisión del usuario → freeze con acta (spec 44 checkbox).
2. Mini-piloto de clase nueva sobre imágenes MOCS (elegir entre excavadora/camión/mixer) → `demo_new_class_machinery_v1` y `demo_limits_harness_v1` (`track: demo`).
3. Enmienda doc 12 ya aplicada (2026-07-17); el freeze del doc 12+04 sigue su curso normal antes de correr el núcleo.

### Decisiones abiertas del análisis GT↔prompts (2026-07-17, requieren decisión del usuario)

Del análisis integral de alineación entre la estrategia de anotación de video-GT y la de prompts
(verificado contra `derive_clip_gt.py` y `cvat_labels.json`):

1. **Carril 3 sin camino de GT**: el laboratorio solo expresa `person` + `has_helmet`/`has_vest`
   (CR-01/CR-02); la clase nueva (maquinaria-presencia) no es derivable a `clip_gt.v2`. Decidir:
   medición cualitativa declarada desde ya, o extensión del lab (label nueva + derivación de
   presencia + patrón de presencia en el motor).
2. **Provenance anti-anclaje**: con pista doble GDINO/YOLOE, registrar en el GT qué tracks nacieron
   de la preanotación GDINO-base y cuáles de la pasada ciega — defiende que el GT no está anclado
   a la familia del modelo evaluado.
3. **Huecos `unknown`**: hoy `violation_intervals` corta episodios con cualquier `None` (la regla
   §7.1 de etiquetado-cvat.md lo compensa con disciplina humana). Decidir si el deriver puentea
   huecos unknown bajo una tolerancia declarada en provenance, o si queda solo en el protocolo.
4. **Presupuesto de composición del clip bench**: fijar mínimo de episodios por celda
   (CR-01 / CR-02 / ambos / clips negativos) ANTES de grabar A+C — hoy el banco tiene 1 episodio
   (CR-01, cb_b01_p7) y la comparación de estrategias de Fase 2 necesita n suficiente + negativos.
