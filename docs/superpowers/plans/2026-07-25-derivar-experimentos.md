# Derivar experimentos con configuración propia — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permitir crear experimentos nuevos desde la consola derivando uno existente y ajustando captura, prompts, límites de corrida y patrones — sin editar YAML a mano y sin romper la reproducibilidad del slug.

**Architecture:** Espejo del patrón `derive` que ya usan los prompt sets (`prompt_store.derive_set`). Un módulo puro (`experiment_deriver.py`) transforma los tres payloads del manifiesto fuente aplicando overrides y reescribiendo identidad y rutas; un escritor atómico a nivel directorio los persiste; un endpoint los ata resolviendo catálogos; el frontend agrega un botón **Derivar** con formulario precargado.

**Tech Stack:** Python 3.11 + FastAPI + pydantic v2 + PyYAML (backend BFF); React + TypeScript + Vite + vitest (frontend).

## Global Constraints

- **Nunca crear un commit.** Regla del workspace (`projects/CLAUDE.md`): no se commitea salvo pedido explícito del usuario en ese turno. Los pasos de este plan terminan con los cambios escritos y los tests en verde, **sin commitear**. No agregar `Co-Authored-By`.
- **TDD estricto**: el test se escribe primero, se corre y se lo ve fallar, recién después la implementación.
- Backend: `cd webconsole/backend && .venv/bin/python -m pytest -q`
- Frontend: `cd webconsole/frontend && npm test` (vitest run)
- Los YAML derivados usan rutas **absolutas** en `runs.*.config` y `patterns.file` (ADR-009).
- El slug válido es `^[a-z0-9][a-z0-9_-]*$` (`manifest_writer._NAME_RE`, ya existe — reusarlo, no redefinirlo).
- `LIVE_SOURCE_TYPES = ("rtsp", "oak_d")` — valor copiado de `e-ovrt_media-plane/src/eovrt_media/config/schemas.py:145`.
- Spec de referencia: `docs/superpowers/specs/2026-07-25-derivar-experimentos-design.md`.
- Hay 1 test que **ya falla antes de empezar** y no es responsabilidad de este plan: `tests/test_prompt_store.py::test_repo_frozen_sets_integrity` (revienta con `prompts/edir_v1.yaml`, que declara `track: comparative` y `strategy: direct_absence`, valores que el schema no acepta). Baseline: **489 passed, 1 failed**. No intentar arreglarlo acá.

---

## File Structure

**Backend** (`webconsole/backend/`):

| Archivo | Responsabilidad |
|---|---|
| `src/eovrt_webconsole/experiment/manifest.py` | *(modificar)* agregar `derives_from` y `changes` al modelo |
| `src/eovrt_webconsole/experiment_deriver.py` | *(crear)* transformación pura: overrides + reescritura de identidad. Sin I/O, sin FastAPI |
| `src/eovrt_webconsole/manifest_writer.py` | *(modificar)* agregar `write_manifest_dir`: escritura atómica a nivel directorio |
| `src/eovrt_webconsole/routers/experiments.py` | *(modificar)* endpoint `POST /manifests/{slug}/derive`: resuelve catálogos, valida, escribe |
| `tests/test_experiment_deriver.py` | *(crear)* tests de la transformación pura |
| `tests/test_manifest_writer_dir.py` | *(crear)* tests de atomicidad del directorio |
| `tests/test_experiments_derive_route.py` | *(crear)* tests del endpoint |

**Frontend** (`webconsole/frontend/src/`):

| Archivo | Responsabilidad |
|---|---|
| `api.ts` | *(modificar)* `deriveExperimentManifest` |
| `components/DeriveExperimentForm.tsx` | *(crear)* formulario de derivación |
| `pages/ExperimentsPage.tsx` | *(modificar)* botón **Derivar** por fila + montaje del formulario |
| `components/DeriveExperimentForm.test.tsx` | *(crear)* tests del formulario |

La transformación vive separada del router a propósito: es la lógica con reglas sutiles (semántica del `null`, reescritura de rutas) y se testea sin levantar FastAPI ni tocar disco.

---

### Task 1: Procedencia en el modelo del manifiesto

**Files:**
- Modify: `webconsole/backend/src/eovrt_webconsole/experiment/manifest.py`
- Test: `webconsole/backend/tests/test_experiment_manifest_provenance.py` (crear)

**Interfaces:**
- Consumes: nada (primera tarea)
- Produces: `ExperimentManifest` acepta `derives_from: str | None` y `changes: str | None`, ambos default `None`

`ExperimentManifest` declara `model_config = ConfigDict(extra="forbid")`, así que sin este cambio cualquier manifiesto derivado con procedencia **falla al validar**.

- [ ] **Step 1: Escribir el test que falla**

Crear `webconsole/backend/tests/test_experiment_manifest_provenance.py`:

```python
"""Procedencia del manifiesto derivado (spec 2026-07-25 §Procedencia)."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from eovrt_webconsole.experiment.manifest import ExperimentManifest

BASE = {
    "schema_version": "experiment.manifest.v1",
    "slug": "d1",
    "runs": {
        "media": {"service": "media-plane", "config": "/tmp/media.yaml", "mode": "run"},
        "control": {"service": "control-plane", "config": "/tmp/control.yaml", "mode": "live"},
    },
    "sequencing": "control_first",
    "report": {},
    "frozen": {},
}


def test_acepta_procedencia():
    m = ExperimentManifest.model_validate(
        {**BASE, "derives_from": "ebe_oakd_live", "changes": "warmup 20 -> 30"}
    )
    assert m.derives_from == "ebe_oakd_live"
    assert m.changes == "warmup 20 -> 30"


def test_procedencia_es_opcional():
    """Los manifiestos existentes (sin procedencia) siguen validando."""
    m = ExperimentManifest.model_validate(BASE)
    assert m.derives_from is None
    assert m.changes is None


def test_sigue_rechazando_campos_desconocidos():
    """extra='forbid' no se relaja: solo se suman estos dos campos."""
    with pytest.raises(ValidationError):
        ExperimentManifest.model_validate({**BASE, "campo_inventado": 1})
```

- [ ] **Step 2: Correr el test y verlo fallar**

Run: `cd webconsole/backend && .venv/bin/python -m pytest tests/test_experiment_manifest_provenance.py -v`
Expected: FAIL — `test_acepta_procedencia` con `ValidationError: Extra inputs are not permitted` en `derives_from`.

- [ ] **Step 3: Implementar**

En `src/eovrt_webconsole/experiment/manifest.py`, dentro de `class ExperimentManifest`, agregar después de `ground_truth`:

```python
    # Procedencia de la derivación (espejo de prompt_store.derive_set): de qué
    # manifiesto salió este y por qué. Opcionales — los manifiestos escritos a
    # mano no los declaran.
    derives_from: str | None = None
    changes: str | None = None
```

- [ ] **Step 4: Correr los tests y verlos pasar**

Run: `.venv/bin/python -m pytest tests/test_experiment_manifest_provenance.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Verificar que no rompí nada**

Run: `.venv/bin/python -m pytest -q`
Expected: `492 passed, 1 failed` — baseline (489) + los 3 nuevos. El único fallo permitido es `test_repo_frozen_sets_integrity`, documentado en Global Constraints. Si aparece cualquier otro, es tuyo: arreglalo antes de seguir.

**NO commitear.**

---

### Task 2: Transformación pura de payloads

**Files:**
- Create: `webconsole/backend/src/eovrt_webconsole/experiment_deriver.py`
- Test: `webconsole/backend/tests/test_experiment_deriver.py` (crear)

**Interfaces:**
- Consumes: `ExperimentManifest` con `derives_from`/`changes` (Task 1)
- Produces:
  - `class DeriveError(ValueError)`
  - `LIVE_PLUGINS: tuple[str, ...] = ("rtsp", "oak_d")`
  - `SOURCE_CONFIG_FIELDS: frozenset[str]`
  - `derive_payloads(*, source_manifest: dict, source_media: dict, source_control: dict, new_slug: str, changes: str | None, overrides: dict, target_dir: Path, camera: dict | None, prompt_set: dict | None) -> tuple[dict, dict, dict]` → `(manifest, media, control)`

`camera` y `prompt_set` llegan **ya resueltos** por el llamador. Este módulo no lee catálogos ni toca disco: así se testea sin fixtures de FastAPI.

- [ ] **Step 1: Escribir el test que falla**

Crear `webconsole/backend/tests/test_experiment_deriver.py`:

```python
"""Transformación pura de derivación (spec 2026-07-25 §Mapa de overrides,
§Reescritura de identidad y rutas)."""
from __future__ import annotations

from pathlib import Path

import pytest

from eovrt_webconsole.experiment_deriver import DeriveError, derive_payloads

TARGET = Path("/repo/experiments/nuevo")

SRC_MANIFEST = {
    "schema_version": "experiment.manifest.v1",
    "slug": "ebe_oakd_live",
    "experiment_id": "exp_vieja_corrida",
    "runs": {
        "media": {
            "service": "media-plane",
            "config": "/repo/experiments/ebe_oakd_live/media.yaml",
            "mode": "run",
        },
        "control": {
            "service": "control-plane",
            "config": "/repo/experiments/ebe_oakd_live/control.yaml",
            "mode": "live",
        },
    },
    "sequencing": "control_first",
    "report": {},
    "frozen": {},
}

SRC_MEDIA = {
    "ingest": {"plugin": "oak_d", "config": {"url": "169.254.31.137", "fps": 30, "warmup_frames": 20}},
    "prompts": {"set_inline": {"id": "viejo", "classes": []}, "active_ids": ["person"]},
    "run": {"name": "ebe_oakd_live", "save_previews": True, "stride": 2},
}

SRC_CONTROL = {
    "run": {"id": None, "scenario": "EBE", "name": "control_ebe_oakd_live"},
    "patterns": {"file": "/patterns/cr01_cr02_v2.yaml", "active_ids": ["CR-01", "CR-02"]},
    "input": {"bus": {"endpoint": "tcp://127.0.0.1:5557"}},
}


def _derive(overrides, **kw):
    return derive_payloads(
        source_manifest=SRC_MANIFEST,
        source_media=SRC_MEDIA,
        source_control=SRC_CONTROL,
        new_slug="nuevo",
        changes="prueba",
        overrides=overrides,
        target_dir=TARGET,
        camera=kw.get("camera"),
        prompt_set=kw.get("prompt_set"),
    )


def test_reescribe_identidad_y_rutas():
    """El fallo silencioso que este test previene: si runs.*.config no se
    reapunta, el manifiesto derivado carga los payloads del ORIGINAL y corre
    con la config vieja sin avisar."""
    manifest, media, control = _derive({})
    assert manifest["slug"] == "nuevo"
    assert manifest["runs"]["media"]["config"] == "/repo/experiments/nuevo/media.yaml"
    assert manifest["runs"]["control"]["config"] == "/repo/experiments/nuevo/control.yaml"
    assert media["run"]["name"] == "nuevo"
    assert control["run"]["name"] == "control_nuevo"


def test_registra_procedencia_y_limpia_experiment_id():
    manifest, _, _ = _derive({})
    assert manifest["derives_from"] == "ebe_oakd_live"
    assert manifest["changes"] == "prueba"
    # el derivado nunca hereda la corrida del fuente
    assert manifest["experiment_id"] is None


def test_no_muta_los_payloads_fuente():
    _derive({"warmup_frames": 99})
    assert SRC_MEDIA["ingest"]["config"]["warmup_frames"] == 20


def test_override_captura():
    _, media, _ = _derive({"warmup_frames": 30, "fps": 15})
    assert media["ingest"]["config"]["warmup_frames"] == 30
    assert media["ingest"]["config"]["fps"] == 15


def test_override_limites():
    _, media, _ = _derive({"max_units": 600})
    assert media["run"]["max_units"] == 600
    assert media["run"]["stride"] == 2  # ausente => conserva


def test_null_borra_el_campo():
    """Sin esta semántica no habría forma de volver un campo a su default."""
    _, media, _ = _derive({"stride": None})
    assert "stride" not in media["run"]


def test_override_patrones():
    _, _, control = _derive(
        {"pattern_set_file": "/patterns/otro.yaml", "pattern_active_ids": ["CR-01"]}
    )
    assert control["patterns"]["file"] == "/patterns/otro.yaml"
    assert control["patterns"]["active_ids"] == ["CR-01"]


def test_override_camara_reconstruye_ingest():
    camera = {"id": "rtsp_dvr_1", "plugin": "rtsp", "config": {"url": "rtsp://x@1.2.3.4:554/s"}}
    _, media, _ = _derive({"camera_id": "rtsp_dvr_1"}, camera=camera)
    assert media["ingest"]["plugin"] == "rtsp"
    assert media["ingest"]["config"]["url"] == "rtsp://x@1.2.3.4:554/s"
    # warmup_frames sobrevive al cambio de cámara (no está en el preset)
    assert media["ingest"]["config"]["warmup_frames"] == 20
    # fps era de la OAK-D, no del preset nuevo: no se arrastra
    assert "fps" not in media["ingest"]["config"]


def test_override_prompts_expande_inline():
    ps = {"id": "cr01_cr02_v2_short", "classes": [{"id": "person", "phrasings": {"default": ["person"]}}]}
    _, media, _ = _derive({"prompt_set_id": "cr01_cr02_v2_short"}, prompt_set=ps)
    assert media["prompts"]["set_inline"] == ps
    assert media["prompts"]["set_inline"]["id"] == "cr01_cr02_v2_short"


def test_campo_desconocido_en_ingest_config_falla():
    with pytest.raises(DeriveError, match="ingest.config"):
        _derive({"camera_id": "x"}, camera={"id": "x", "plugin": "oak_d",
                                            "config": {"url": "1.2.3.4", "inventado": 1}})


def test_warmup_frames_en_fuente_no_viva_falla():
    """schemas.py:239 del media-plane lo rechaza; queremos fallar acá, no con un
    422 en medio de una toma."""
    camera = {"id": "arch", "plugin": "video_file", "config": {"path": "/v.mp4"}}
    with pytest.raises(DeriveError, match="warmup_frames"):
        _derive({"camera_id": "arch"}, camera=camera)


def test_override_desconocido_falla():
    with pytest.raises(DeriveError, match="override"):
        _derive({"parametro_que_no_existe": 1})
```

- [ ] **Step 2: Correr el test y verlo fallar**

Run: `cd webconsole/backend && .venv/bin/python -m pytest tests/test_experiment_deriver.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'eovrt_webconsole.experiment_deriver'`

- [ ] **Step 3: Implementar**

Crear `src/eovrt_webconsole/experiment_deriver.py`:

```python
"""Derivación de manifiestos paraguas: transformación pura de los tres payloads.

Espejo de `prompt_store.derive_set` para experimentos (spec
docs/superpowers/specs/2026-07-25-derivar-experimentos-design.md).

Sin I/O y sin FastAPI a propósito: las reglas sutiles viven acá (semántica del
`null`, reescritura de rutas absolutas) y se testean en aislamiento. El llamador
resuelve los catálogos y persiste el resultado.
"""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

# Copiado de e-ovrt_media-plane/src/eovrt_media/config/schemas.py:145. El
# warm-up de lente solo tiene sentido en fuentes vivas.
LIVE_PLUGINS: tuple[str, ...] = ("rtsp", "oak_d")

# Campos válidos de `ingest.config`, copiados de SourceSection.model_fields
# (e-ovrt_media-plane/src/eovrt_media/config/schemas.py) + "dataset", que
# run_request.py:93 acepta y traduce a source.ref.
#
# Se hardcodean a propósito: `eovrt_media` NO es importable desde el venv del
# BFF (repos y venvs separados), así que importarlo para leer el schema en vivo
# degradaría siempre a "no validar" y el guard sería letra muerta. Si el
# media-plane suma un campo de fuente, hay que actualizar esta tupla.
SOURCE_CONFIG_FIELDS: frozenset[str] = frozenset({
    "dataset", "dataset_id", "description", "extensions", "fps", "isp_scale",
    "kind", "orientation", "path", "prefilter", "reconnect_delay_ms",
    "reconnect_retries", "ref", "resolution", "source_id", "split", "type",
    "url", "view", "vocabulary", "warmup_frames", "xlink_chunk_size",
})

# Claves aceptadas en `overrides`. Lista cerrada: un typo es un error explícito,
# no un campo que se ignora en silencio.
_MEDIA_INGEST_KEYS = frozenset({"warmup_frames", "fps"})
_MEDIA_RUN_KEYS = frozenset({"stride", "max_units"})
_OTHER_KEYS = frozenset({"camera_id", "prompt_set_id", "pattern_set_file", "pattern_active_ids"})
_ALLOWED = _MEDIA_INGEST_KEYS | _MEDIA_RUN_KEYS | _OTHER_KEYS

_SENTINEL = object()


class DeriveError(ValueError):
    """Override inválido o payload derivado inconsistente."""


def _apply(target: dict, key: str, value: Any) -> None:
    """Semántica de overrides: `None` explícito borra, cualquier otro valor asigna."""
    if value is None:
        target.pop(key, None)
    else:
        target[key] = value


def derive_payloads(
    *,
    source_manifest: dict,
    source_media: dict,
    source_control: dict,
    new_slug: str,
    changes: str | None,
    overrides: dict,
    target_dir: Path,
    camera: dict | None = None,
    prompt_set: dict | None = None,
) -> tuple[dict, dict, dict]:
    """Devuelve (manifest, media, control) derivados. No muta los originales."""
    unknown = set(overrides) - _ALLOWED
    if unknown:
        raise DeriveError(f"override desconocido: {sorted(unknown)}")

    manifest = copy.deepcopy(source_manifest)
    media = copy.deepcopy(source_media)
    control = copy.deepcopy(source_control)

    ingest = media.setdefault("ingest", {})
    config = dict(ingest.get("config") or {})

    # Cámara: reconstruye plugin+config desde el preset. `warmup_frames` no vive
    # en el preset, así que se preserva del fuente; el resto de la config vieja
    # (p. ej. `fps` de la OAK-D) NO se arrastra a una cámara distinta.
    if "camera_id" in overrides:
        if camera is None:
            raise DeriveError(f"cámara no resuelta: {overrides['camera_id']!r}")
        previous_warmup = config.get("warmup_frames", _SENTINEL)
        ingest["plugin"] = camera["plugin"]
        config = dict(camera.get("config") or {})
        if previous_warmup is not _SENTINEL:
            config["warmup_frames"] = previous_warmup

    for key in _MEDIA_INGEST_KEYS:
        if key in overrides:
            _apply(config, key, overrides[key])

    plugin = ingest.get("plugin")
    if config.get("warmup_frames", 0) and plugin not in LIVE_PLUGINS:
        raise DeriveError(
            f"warmup_frames solo aplica a fuentes vivas ({', '.join(LIVE_PLUGINS)}); "
            f"plugin={plugin!r}"
        )

    unknown_config = set(config) - SOURCE_CONFIG_FIELDS
    if unknown_config:
        raise DeriveError(f"campo desconocido en ingest.config: {sorted(unknown_config)}")

    ingest["config"] = config

    if "prompt_set_id" in overrides:
        if prompt_set is None:
            raise DeriveError(f"prompt set no resuelto: {overrides['prompt_set_id']!r}")
        media.setdefault("prompts", {})["set_inline"] = copy.deepcopy(prompt_set)

    run = media.setdefault("run", {})
    for key in _MEDIA_RUN_KEYS:
        if key in overrides:
            _apply(run, key, overrides[key])

    patterns = control.setdefault("patterns", {})
    if "pattern_set_file" in overrides:
        _apply(patterns, "file", overrides["pattern_set_file"])
    if "pattern_active_ids" in overrides:
        _apply(patterns, "active_ids", overrides["pattern_active_ids"])

    # Identidad y rutas. Sin esto el derivado apunta a los payloads del fuente.
    manifest["slug"] = new_slug
    manifest["experiment_id"] = None
    manifest["derives_from"] = source_manifest.get("slug")
    manifest["changes"] = changes
    manifest["runs"]["media"]["config"] = str(target_dir / "media.yaml")
    manifest["runs"]["control"]["config"] = str(target_dir / "control.yaml")
    run["name"] = new_slug
    control.setdefault("run", {})["name"] = f"control_{new_slug}"

    return manifest, media, control
```

- [ ] **Step 4: Correr los tests y verlos pasar**

Run: `.venv/bin/python -m pytest tests/test_experiment_deriver.py -v`
Expected: PASS (12 tests)

- [ ] **Step 5: Verificar la suite**

Run: `.venv/bin/python -m pytest -q`
Expected: `504 passed, 1 failed` (492 + los 12 nuevos)

**NO commitear.**

---

### Task 3: Escritura atómica a nivel directorio

**Files:**
- Modify: `webconsole/backend/src/eovrt_webconsole/manifest_writer.py`
- Test: `webconsole/backend/tests/test_manifest_writer_dir.py` (crear)

**Interfaces:**
- Consumes: nada de tareas previas
- Produces: `write_manifest_dir(experiments_dir: Path, name: str, files: dict[str, dict], *, protected_groups: frozenset[str] = frozenset()) -> Path`, y las excepciones ya existentes `ManifestExistsError` / `ProtectedManifestError`

`write_manifest` escribe **un** archivo atómicamente. Acá van tres, y tres escrituras atómicas no son atómicas como conjunto: si falla la segunda queda un `manifest.yaml` válido apuntando a un `media.yaml` inexistente. La unidad atómica pasa a ser el directorio.

- [ ] **Step 1: Escribir el test que falla**

Crear `webconsole/backend/tests/test_manifest_writer_dir.py`:

```python
"""Escritura atómica del directorio derivado (spec 2026-07-25 §Escritura)."""
from __future__ import annotations

import pytest
import yaml

from eovrt_webconsole.manifest_writer import (
    ManifestExistsError,
    write_manifest_dir,
)

FILES = {
    "manifest.yaml": {"schema_version": "experiment.manifest.v1", "slug": "nuevo"},
    "media.yaml": {"ingest": {"plugin": "oak_d"}},
    "control.yaml": {"patterns": {"file": "/p.yaml"}},
}


def test_escribe_los_tres_archivos(tmp_path):
    target = write_manifest_dir(tmp_path, "nuevo", FILES)
    assert target == tmp_path / "nuevo"
    for name, payload in FILES.items():
        assert yaml.safe_load((target / name).read_text()) == payload


def test_no_deja_temporal(tmp_path):
    write_manifest_dir(tmp_path, "nuevo", FILES)
    assert list(tmp_path.glob(".*.tmp")) == []


def test_rechaza_slug_existente(tmp_path):
    write_manifest_dir(tmp_path, "nuevo", FILES)
    otros = {**FILES, "media.yaml": {"ingest": {"plugin": "rtsp"}}}
    with pytest.raises(ManifestExistsError):
        write_manifest_dir(tmp_path, "nuevo", otros)
    # el original queda intacto
    assert yaml.safe_load((tmp_path / "nuevo" / "media.yaml").read_text()) == FILES["media.yaml"]


def test_rechaza_nombre_invalido(tmp_path):
    for malo in ["Mayus", "../fuga", "", "-arranca-con-guion"]:
        with pytest.raises(ValueError):
            write_manifest_dir(tmp_path, malo, FILES)
    assert list(tmp_path.iterdir()) == []


def test_fallo_a_mitad_no_deja_nada(tmp_path, monkeypatch):
    """Si la segunda escritura revienta, no queda ni destino ni temporal."""
    import eovrt_webconsole.manifest_writer as mw

    original = mw.yaml.safe_dump
    llamadas = {"n": 0}

    def explota(*args, **kwargs):
        llamadas["n"] += 1
        if llamadas["n"] == 2:
            raise OSError("disco lleno simulado")
        return original(*args, **kwargs)

    monkeypatch.setattr(mw.yaml, "safe_dump", explota)

    with pytest.raises(OSError):
        write_manifest_dir(tmp_path, "nuevo", FILES)

    assert not (tmp_path / "nuevo").exists()
    assert list(tmp_path.glob(".*.tmp")) == []
```

- [ ] **Step 2: Correr el test y verlo fallar**

Run: `cd webconsole/backend && .venv/bin/python -m pytest tests/test_manifest_writer_dir.py -v`
Expected: FAIL — `ImportError: cannot import name 'write_manifest_dir'`

- [ ] **Step 3: Implementar**

En `src/eovrt_webconsole/manifest_writer.py`, agregar al final (reusa `_NAME_RE`, `ManifestExistsError` y `ProtectedManifestError`, que ya existen en el módulo):

```python
def write_manifest_dir(
    experiments_dir: Path,
    name: str,
    files: dict[str, dict],
    *,
    protected_groups: frozenset[str] = frozenset(),
) -> Path:
    """Escribe un manifiesto paraguas multi-archivo de forma atómica.

    La unidad atómica es el DIRECTORIO, no el archivo: tres escrituras atómicas
    no son atómicas como conjunto, y un directorio a medio construir deja un
    manifest.yaml válido apuntando a payloads inexistentes. Se arma todo en un
    temporal hermano y se publica con un único os.replace; `os.replace` sobre un
    destino inexistente es atómico dentro del mismo filesystem.
    """
    if not _NAME_RE.match(name or ""):
        raise ValueError(f"Nombre de manifiesto inválido: {name!r} (usar [a-z0-9_-])")

    target = experiments_dir / name
    if name in protected_groups and target.exists():
        raise ProtectedManifestError(
            f"manifiesto curado en grupo protegido {name!r}; renombrá o escribí en otro grupo"
        )
    if target.exists():
        raise ManifestExistsError(str(target))

    experiments_dir.mkdir(parents=True, exist_ok=True)
    tmp = experiments_dir / f".{name}.tmp"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir()
    try:
        for filename, payload in files.items():
            (tmp / filename).write_text(
                yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )
        os.replace(tmp, target)
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    return target
```

Agregar `import shutil` al bloque de imports del módulo (ya tiene `os`, `re`, `Path` y `yaml`).

- [ ] **Step 4: Correr los tests y verlos pasar**

Run: `.venv/bin/python -m pytest tests/test_manifest_writer_dir.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Verificar la suite**

Run: `.venv/bin/python -m pytest -q`
Expected: `509 passed, 1 failed` (504 + los 5 nuevos)

**NO commitear.**

---

### Task 4: Endpoint de derivación

**Files:**
- Modify: `webconsole/backend/src/eovrt_webconsole/routers/experiments.py`
- Test: `webconsole/backend/tests/test_experiments_derive_route.py` (crear)

**Interfaces:**
- Consumes: `derive_payloads` + `DeriveError` (Task 2), `write_manifest_dir` (Task 3), `derives_from`/`changes` (Task 1)
- Produces: `POST /api/experiments/manifests/{slug}/derive` → `201 {"slug": "<new_slug>"}`

Resuelve los catálogos y ata todo. `get_prompt_set` (de `repo_catalog`) es el mismo helper que usa `translation.composition_to_run_request` para expandir prompts — se reusa, no se duplica.

- [ ] **Step 1: Escribir el test que falla**

Crear `webconsole/backend/tests/test_experiments_derive_route.py`:

```python
"""Endpoint POST /api/experiments/manifests/{slug}/derive."""
from __future__ import annotations

import pytest
import yaml
from fastapi.testclient import TestClient

from eovrt_webconsole.app import create_app
from eovrt_webconsole.experiment.manifest import load_manifest


@pytest.fixture
def repo(tmp_path):
    """Repo mínimo: experiments/ con un paraguas, prompts/ y cameras/."""
    (tmp_path / "prompts").mkdir()
    (tmp_path / "cameras").mkdir()
    exp = tmp_path / "experiments" / "base"
    exp.mkdir(parents=True)

    (exp / "manifest.yaml").write_text(yaml.safe_dump({
        "schema_version": "experiment.manifest.v1",
        "slug": "base",
        "runs": {
            "media": {"service": "media-plane", "config": str(exp / "media.yaml"), "mode": "run"},
            "control": {"service": "control-plane", "config": str(exp / "control.yaml"), "mode": "live"},
        },
        "sequencing": "control_first",
        "report": {},
        "frozen": {},
    }))
    (exp / "media.yaml").write_text(yaml.safe_dump({
        "ingest": {"plugin": "oak_d", "config": {"url": "169.254.31.137", "warmup_frames": 20}},
        "prompts": {"set_inline": {"id": "viejo", "classes": []}},
        "run": {"name": "base"},
    }))
    (exp / "control.yaml").write_text(yaml.safe_dump({
        "run": {"name": "control_base"},
        "patterns": {"file": "/p/v2.yaml", "active_ids": ["CR-01", "CR-02"]},
    }))

    (tmp_path / "prompts" / "corto.yaml").write_text(yaml.safe_dump({
        "prompt_set": {
            "id": "corto",
            "classes": [{"id": "person", "phrasings": {"default": ["person"]}}],
        }
    }))
    (tmp_path / "cameras" / "dvr.yaml").write_text(yaml.safe_dump({
        "camera": {"id": "dvr", "name": "DVR", "plugin": "rtsp",
                   "config": {"url": "rtsp://u:p@1.2.3.4:554/s"}}
    }))
    return tmp_path


@pytest.fixture
def client(repo, monkeypatch):
    monkeypatch.setenv("EOVRT_WEBCONSOLE_REPO_ROOT", str(repo))
    return TestClient(create_app())


def _derive(client, body):
    return client.post("/api/experiments/manifests/base/derive", json=body)


def test_deriva_y_reapunta_rutas(client, repo):
    r = _derive(client, {"new_slug": "nuevo", "changes": "warmup 30",
                         "overrides": {"warmup_frames": 30}})
    assert r.status_code == 201, r.text
    assert r.json() == {"slug": "nuevo"}

    nuevo = repo / "experiments" / "nuevo"
    manifest = load_manifest(nuevo / "manifest.yaml")
    assert manifest.slug == "nuevo"
    assert manifest.derives_from == "base"
    assert manifest.changes == "warmup 30"

    # GUARD ANTI-FALLO-SILENCIOSO: los paths del derivado resuelven dentro de su
    # propio directorio, y el valor leído es el override — no el del fuente.
    media_path = Path(manifest.runs["media"].config)
    assert media_path.parent == nuevo
    assert yaml.safe_load(media_path.read_text())["ingest"]["config"]["warmup_frames"] == 30
    # el fuente quedó intacto
    base_media = repo / "experiments" / "base" / "media.yaml"
    assert yaml.safe_load(base_media.read_text())["ingest"]["config"]["warmup_frames"] == 20


def test_aparece_en_el_listado(client):
    _derive(client, {"new_slug": "nuevo", "overrides": {}})
    slugs = [m["slug"] for m in client.get("/api/experiments/manifests").json()]
    assert "nuevo" in slugs


def test_expande_prompt_set(client, repo):
    _derive(client, {"new_slug": "nuevo", "overrides": {"prompt_set_id": "corto"}})
    media = yaml.safe_load((repo / "experiments" / "nuevo" / "media.yaml").read_text())
    assert media["prompts"]["set_inline"]["id"] == "corto"
    assert media["prompts"]["set_inline"]["classes"][0]["id"] == "person"


def test_cambia_camara(client, repo):
    _derive(client, {"new_slug": "nuevo", "overrides": {"camera_id": "dvr"}})
    media = yaml.safe_load((repo / "experiments" / "nuevo" / "media.yaml").read_text())
    assert media["ingest"]["plugin"] == "rtsp"
    assert media["ingest"]["config"]["url"] == "rtsp://u:p@1.2.3.4:554/s"


def test_slug_repetido_409(client):
    _derive(client, {"new_slug": "nuevo", "overrides": {}})
    r = _derive(client, {"new_slug": "nuevo", "overrides": {}})
    assert r.status_code == 409


def test_slug_invalido_400(client, repo):
    r = _derive(client, {"new_slug": "Mayus", "overrides": {}})
    assert r.status_code == 400
    assert not (repo / "experiments" / "Mayus").exists()


def test_fuente_desconocida_404(client):
    r = client.post("/api/experiments/manifests/noexiste/derive",
                    json={"new_slug": "n", "overrides": {}})
    assert r.status_code == 404


def test_camara_inexistente_400(client, repo):
    r = _derive(client, {"new_slug": "nuevo", "overrides": {"camera_id": "fantasma"}})
    assert r.status_code == 400
    assert not (repo / "experiments" / "nuevo").exists()


def test_prompt_set_inexistente_400(client, repo):
    r = _derive(client, {"new_slug": "nuevo", "overrides": {"prompt_set_id": "fantasma"}})
    assert r.status_code == 400
    assert not (repo / "experiments" / "nuevo").exists()


def test_override_desconocido_400(client, repo):
    r = _derive(client, {"new_slug": "nuevo", "overrides": {"inventado": 1}})
    assert r.status_code == 400
    assert not (repo / "experiments" / "nuevo").exists()
```

Agregar `from pathlib import Path` al principio del archivo de test.

- [ ] **Step 2: Correr el test y verlo fallar**

Run: `cd webconsole/backend && .venv/bin/python -m pytest tests/test_experiments_derive_route.py -v`
Expected: FAIL — todos con `404` (la ruta no existe todavía).

Si en cambio fallan por la fixture (`EOVRT_WEBCONSOLE_REPO_ROOT` no reconocida), mirá cómo arman el repo temporal los tests que ya existen — `tests/test_spec44b_gate.py` y `tests/test_experiment_orchestration.py` — y copiá ese mecanismo en vez de inventar otro.

- [ ] **Step 3: Implementar**

En `src/eovrt_webconsole/routers/experiments.py`:

Agregar a los imports:

```python
from eovrt_webconsole.experiment_deriver import DeriveError, derive_payloads
from eovrt_webconsole.manifest_writer import write_manifest_dir
from eovrt_webconsole.repo_catalog import get_prompt_set
from eovrt_webconsole import camera_store as cs
```

Agregar la ruta después de `get_manifest`:

```python
@router.post("/manifests/{slug}/derive", status_code=201)
async def derive_manifest(slug: str, body: dict, request: Request) -> dict:
    """Crea un manifiesto paraguas nuevo a partir de otro, con overrides.

    El manifiesto fuente no se toca: el slug sigue siendo la unidad reproducible
    (spec 2026-07-25 §Decisión de fondo).
    """
    settings = request.app.state.settings

    source = None
    for manifest in _iter_umbrella_manifests(settings.experiments_dir):
        if manifest.slug == slug:
            source = manifest
            break
    if source is None:
        raise HTTPException(status_code=404, detail=f"Manifiesto paraguas desconocido: {slug}")

    new_slug = (body.get("new_slug") or "").strip()
    overrides = body.get("overrides") or {}
    changes = body.get("changes")

    for plane in ("media", "control"):
        if plane not in source.runs:
            raise HTTPException(
                status_code=422, detail=f"El manifiesto {slug!r} no declara runs.{plane}"
            )

    try:
        source_media = yaml.safe_load(Path(source.runs["media"].config).read_text(encoding="utf-8"))
        source_control = yaml.safe_load(
            Path(source.runs["control"].config).read_text(encoding="utf-8")
        )
    except OSError as exc:
        raise HTTPException(
            status_code=422, detail=f"No se pudieron leer los payloads de {slug!r}: {exc}"
        ) from exc

    camera = None
    if "camera_id" in overrides:
        try:
            camera = cs.get_camera(settings.cameras_dir, overrides["camera_id"])
        except cs.CameraStoreError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    prompt_set = None
    if "prompt_set_id" in overrides:
        prompt_set = get_prompt_set(settings.prompts_dir, overrides["prompt_set_id"])
        if prompt_set is None:
            raise HTTPException(
                status_code=400,
                detail=f"Prompt set desconocido: {overrides['prompt_set_id']!r}",
            )

    pattern_file = overrides.get("pattern_set_file")
    if pattern_file and not Path(pattern_file).is_file():
        raise HTTPException(status_code=400, detail=f"pattern_set_file no existe: {pattern_file}")

    try:
        manifest_doc, media_doc, control_doc = derive_payloads(
            source_manifest=source.model_dump(mode="json"),
            source_media=source_media,
            source_control=source_control,
            new_slug=new_slug,
            changes=changes,
            overrides=overrides,
            target_dir=settings.experiments_dir / new_slug,
            camera=camera,
            prompt_set=prompt_set,
        )
    except DeriveError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        ExperimentManifest.model_validate(manifest_doc)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc

    try:
        write_manifest_dir(
            settings.experiments_dir,
            new_slug,
            {
                "manifest.yaml": manifest_doc,
                "media.yaml": media_doc,
                "control.yaml": control_doc,
            },
            protected_groups=settings.protected_groups,
        )
    except ProtectedManifestError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ManifestExistsError as exc:
        raise HTTPException(status_code=409, detail=f"Ya existe: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    logger.info("derive_manifest: %s -> %s (overrides=%s)", slug, new_slug, sorted(overrides))
    return {"slug": new_slug}
```

- [ ] **Step 4: Correr los tests y verlos pasar**

Run: `.venv/bin/python -m pytest tests/test_experiments_derive_route.py -v`
Expected: PASS (10 tests)

- [ ] **Step 5: Verificar la suite y el lint**

Run: `.venv/bin/python -m pytest -q`
Expected: `519 passed, 1 failed` (509 + los 10 nuevos)

- [ ] **Step 6: Humo contra el BFF real**

Levantar el BFF y derivar de verdad, sin lanzar nada:

```bash
cd webconsole/backend
.venv/bin/python .venv/bin/uvicorn eovrt_webconsole.app:create_app --factory --port 8090 &
sleep 5
curl -s -X POST localhost:8090/api/experiments/manifests/ebe_oakd_live/derive \
  -H 'content-type: application/json' \
  -d '{"new_slug":"ebe_oakd_live_w30","changes":"warmup 20->30","overrides":{"warmup_frames":30}}'
curl -s localhost:8090/api/experiments/manifests
```

Expected: `{"slug":"ebe_oakd_live_w30"}` y el slug nuevo en el listado. Verificar a mano que `experiments/ebe_oakd_live_w30/manifest.yaml` tiene `runs.media.config` apuntando **dentro de su propio directorio** y que `media.yaml` dice `warmup_frames: 30`.

Borrar el directorio derivado de prueba al terminar (`rm -rf experiments/ebe_oakd_live_w30`) si no lo vas a usar.

**NO commitear.**

---

### Task 5: Botón Derivar en la consola

**Files:**
- Modify: `webconsole/frontend/src/api.ts`
- Create: `webconsole/frontend/src/components/DeriveExperimentForm.tsx`
- Modify: `webconsole/frontend/src/pages/ExperimentsPage.tsx`
- Test: `webconsole/frontend/src/components/DeriveExperimentForm.test.tsx` (crear)

**Interfaces:**
- Consumes: `POST /api/experiments/manifests/{slug}/derive` (Task 4)
- Produces: `deriveExperimentManifest(slug, body)` en `api.ts`; componente `<DeriveExperimentForm source={slug} onDone={(newSlug) => void} onCancel={() => void} />`

- [ ] **Step 1: Escribir el test que falla**

Crear `webconsole/frontend/src/components/DeriveExperimentForm.test.tsx`:

```tsx
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { DeriveExperimentForm } from './DeriveExperimentForm'

const derive = vi.fn()
vi.mock('../api', () => ({
  deriveExperimentManifest: (...args: unknown[]) => derive(...args),
  getCameras: async () => [{ id: 'oak_d_lab', name: 'OAK-D', plugin: 'oak_d', config: {} }],
  getPromptSets: async () => [{ id: 'cr01_cr02_v2_short' }],
}))

beforeEach(() => derive.mockReset())

describe('DeriveExperimentForm', () => {
  it('manda el body esperado y avisa el slug nuevo', async () => {
    derive.mockResolvedValue({ slug: 'nuevo' })
    const onDone = vi.fn()
    render(<DeriveExperimentForm source="base" onDone={onDone} onCancel={() => {}} />)

    fireEvent.change(screen.getByLabelText('nombre nuevo'), { target: { value: 'nuevo' } })
    fireEvent.change(screen.getByLabelText('warmup_frames'), { target: { value: '30' } })
    fireEvent.click(screen.getByText('Derivar'))

    await waitFor(() => expect(onDone).toHaveBeenCalledWith('nuevo'))
    expect(derive).toHaveBeenCalledWith('base', expect.objectContaining({
      new_slug: 'nuevo',
      overrides: expect.objectContaining({ warmup_frames: 30 }),
    }))
  })

  it('muestra el error del backend sin romper la pantalla', async () => {
    derive.mockRejectedValue(new Error('Ya existe'))
    render(<DeriveExperimentForm source="base" onDone={() => {}} onCancel={() => {}} />)

    fireEvent.change(screen.getByLabelText('nombre nuevo'), { target: { value: 'nuevo' } })
    fireEvent.click(screen.getByText('Derivar'))

    await waitFor(() => expect(screen.getByText(/Ya existe/)).toBeTruthy())
  })

  it('no deja derivar sin nombre', () => {
    render(<DeriveExperimentForm source="base" onDone={() => {}} onCancel={() => {}} />)
    expect(screen.getByText('Derivar')).toHaveProperty('disabled', true)
  })
})
```

- [ ] **Step 2: Correr el test y verlo fallar**

Run: `cd webconsole/frontend && npm test -- DeriveExperimentForm`
Expected: FAIL — no existe `./DeriveExperimentForm`.

- [ ] **Step 3: Agregar el cliente de API**

En `src/api.ts`, junto a `runExperiment` (que hoy está cerca de la línea 100):

```ts
export const deriveExperimentManifest = (
  slug: string,
  body: { new_slug: string; changes?: string; overrides: Record<string, unknown> },
) =>
  request<{ slug: string }>(`/api/experiments/manifests/${slug}/derive`, {
    method: 'POST',
    body: JSON.stringify(body),
  })
```

Seguí la forma exacta de las llamadas vecinas (`request<T>(path, init)`); no inventes un wrapper nuevo.

- [ ] **Step 4: Implementar el formulario**

Crear `src/components/DeriveExperimentForm.tsx`. Requisitos concretos:

- Campos, todos con `<label>` asociado (los tests los buscan por texto de label): `nombre nuevo`, `changes`, `warmup_frames`, `fps`, `cámara`, `prompt set`, `stride`, `max_units`, `pattern set`.
- `cámara` y `prompt set` son `<select>` poblados con `getCameras()` y `getPromptSets()`.
- Solo se mandan en `overrides` los campos que el usuario tocó; los vacíos se omiten (semántica "clave ausente conserva el valor del fuente", spec §Endpoint).
- Los numéricos se mandan como número, no string: `Number(valor)`.
- Botón `Derivar`, deshabilitado si `nombre nuevo` está vacío o si hay un submit en curso.
- Botón `Cancelar` → `onCancel()`.
- En éxito: `onDone(slug)`. En error: mostrar el mensaje, no relanzar.
- Usá los componentes `Field` / `Card` que ya usa `ComposePage.tsx` para que la pantalla no desentone.

- [ ] **Step 5: Correr los tests y verlos pasar**

Run: `npm test -- DeriveExperimentForm`
Expected: PASS (3 tests)

- [ ] **Step 6: Montar el botón en ExperimentsPage**

En `src/pages/ExperimentsPage.tsx`:

- Estado `const [deriving, setDeriving] = useState<string | null>(null)`.
- En la tabla de manifiestos, agregar una columna con un botón **`Derivar`** por fila que hace `setDeriving(r.slug)`.
- Cuando `deriving !== null`, renderizar `<DeriveExperimentForm source={deriving} onDone={...} onCancel={() => setDeriving(null)} />`.
- En `onDone(newSlug)`: recargar la lista de manifiestos (la misma llamada que usa el `useEffect` de la página), hacer `setSlug(newSlug)` para dejarlo seleccionado en el desplegable, y `setDeriving(null)`.
- **Derivar no lanza nada.** El usuario aprieta después `Lanzar experimento`.

- [ ] **Step 7: Verificar la suite del frontend**

Run: `npm test`
Expected: todos los tests en verde, incluidos los que ya existían.

- [ ] **Step 8: Humo manual en la consola**

Con el BFF y ambos planos arriba, abrir Experimentos, derivar `ebe_oakd_live` a `ebe_oakd_live_w30` con `warmup_frames: 30`, y confirmar que el slug nuevo aparece en el desplegable y queda seleccionado. **No hace falta lanzarlo.**

**NO commitear.**

---

## Notas de cierre

Al terminar las 5 tareas, avisarle al usuario que los cambios están escritos y sin commitear, y que el working tree de `e-ovrt_experimental-setup` ya venía con trabajo previo sin commitear (`runner.py`, `oakd_recorder.py`, `test_runner_live.py`, `experiments/ebe_oakd_live/`, `prompts/edir_v1.yaml`) — no mezclarlos en un commit sin que el usuario lo pida.
