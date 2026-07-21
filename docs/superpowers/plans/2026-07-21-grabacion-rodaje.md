# Grabación de rodaje (OAK-D / RTSP) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Grabar tomas de rodaje desde la ventana Cámaras de la consola, con cámara RTSP u OAK-D Pro PoE, dejando un master crudo en `e-ovrt_datasets/datasets-videos/raw/` listo para `prepare_clip.sh`.

**Architecture:** Todo vive en el backend del webconsole. Las dos ramas son subprocesos que escriben a disco (`ffmpeg -c copy` para RTSP; un script standalone con DepthAI para OAK-D); el backend arranca, vigila, corta y muxea, sin decodificar ni encodear nada. El media-plane no se toca: solo se le pide estado para la exclusión mutua y se le toma prestado el intérprete de su venv, que tiene `depthai`.

**Tech Stack:** Python 3.14 (backend), FastAPI, pydantic v2, pytest; ffmpeg/ffprobe del sistema; DepthAI 2.32 vía intérprete externo (Python 3.12); React + TypeScript + vitest (frontend).

**Spec:** `docs/superpowers/specs/2026-07-21-grabacion-rodaje-design.md`

## Global Constraints

- **Repo de trabajo:** `e-ovrt_experimental-setup`. `e-ovrt_media-plane` y `e-ovrt_datasets` **no se modifican**.
- **MODO SIN COMMITS.** Regla de `projects/CLAUDE.md` y convención establecida de este repo (ver `.superpowers/sdd/progress.md`): **no se commitea nada**. Los pasos "Commit" de cada tarea se ejecutan como `git add -N <paths exactos del task>` y nada más; el trabajo queda en el working tree para que el usuario lo revise y commitee. **Nunca `git commit`. Nunca `git add <dir>`** (arrastra `.venv`).
- Backend: `.venv/bin/python -m pytest tests/<archivo> -v` desde `webconsole/backend/`. **`pytest` a secas falla** (`ModuleNotFoundError: No module named 'tests'`, por `from tests.fake_service import`): siempre `python -m pytest`.
- Frontend: `npx vitest run <archivo>` desde `webconsole/frontend/`.
- **El frontend no tiene `jest-dom`**: usar `toBeTruthy()`, nunca `toBeInTheDocument()`/`toBeDisabled()`. `afterEach(() => cleanup())` explícito. `fireEvent`, nunca `userEvent`.
- Puede haber fallos preexistentes ajenos a este trabajo; no arreglarlos ni tocarlos, solo reportarlos.
- Lint: `./.venv/bin/python -m ruff check src tests` (backend).
- Código y comentarios en español, como el resto del repo. Docstrings de módulo en una línea.
- El intérprete de la rama OAK-D es Python 3.12; el backend es 3.14. `tools/record_oakd.py` **no puede importar nada de `eovrt_webconsole`** ni usar sintaxis posterior a 3.12.
- Nombres de toma: `^P[1-9]-[a-z]-take[0-9]+$`. Escenario `^P[1-9]$`, variante `^[a-z]$`.
- Ninguna falla se silencia: una toma degradada se marca (`truncated: true`) y se conserva; nunca se borra material.

---

## File Structure

**Backend — nuevo paquete `recording/`** (`webconsole/backend/src/eovrt_webconsole/recording/`):

| Archivo | Responsabilidad |
|---|---|
| `types.py` | `RecordingSpec`, `RecordingResult`, `RecordingStatus`, protocolo `Recorder` |
| `naming.py` | Escenario + variante → próximo basename libre |
| `guards.py` | Gates de arranque: destino válido, no `/mnt/c`, espacio libre |
| `probe.py` | Medición con `ffprobe` del archivo cerrado |
| `ffmpeg_recorder.py` | Rama RTSP |
| `oakd_recorder.py` | Rama OAK-D: lanza y vigila el script externo |
| `sidecar.py` | Escritura de `<basename>.rec.json` + sha256 |
| `manager.py` | Ciclo de vida, lock, reserva `O_EXCL`, corte automático, huérfanas |

**Backend — modificados:** `settings.py` (dos settings nuevos), `app.py` (wiring), `routers/recordings.py` (nuevo).

**Script standalone:** `webconsole/tools/record_oakd.py`.

**Frontend:** `components/RecordPanel.tsx` (nuevo), `api.ts` y `types.ts` (modificados), `pages/CamerasPage.tsx` (monta el panel).

---

### Task 1: Settings de grabación

**Files:**
- Modify: `webconsole/backend/src/eovrt_webconsole/settings.py`
- Test: `webconsole/backend/tests/test_recording_settings.py`

**Interfaces:**
- Consumes: `ConsoleSettings` existente.
- Produces: `ConsoleSettings.recordings_dir: Path | None`, `ConsoleSettings.oakd_python: Path | None`, y las propiedades `ConsoleSettings.raw_dir -> Path` y `ConsoleSettings.oakd_interpreter -> Path`. Envs `EOVRT_CONSOLE_RECORDINGS_DIR` y `EOVRT_CONSOLE_OAKD_PYTHON`.

- [ ] **Step 1: Write the failing test**

Crear `webconsole/backend/tests/test_recording_settings.py`:

```python
from pathlib import Path

from eovrt_webconsole.settings import ConsoleSettings


def _settings(repo: Path, **kwargs) -> ConsoleSettings:
    return ConsoleSettings(
        service_url="http://service.fake",
        repo_root=repo,
        frozen_set_ids=frozenset(),
        **kwargs,
    )


def test_raw_dir_default_es_el_repo_hermano_de_datasets(repo):
    s = _settings(repo)
    assert s.raw_dir == repo.parent / "e-ovrt_datasets" / "datasets-videos" / "raw"


def test_raw_dir_respeta_el_override(repo, tmp_path):
    s = _settings(repo, recordings_dir=tmp_path / "otro")
    assert s.raw_dir == tmp_path / "otro"


def test_oakd_interpreter_default_es_el_venv_del_media_plane(repo):
    s = _settings(repo)
    assert s.oakd_interpreter == repo.parent / "e-ovrt_media-plane" / ".venv" / "bin" / "python"


def test_oakd_interpreter_respeta_el_override(repo, tmp_path):
    s = _settings(repo, oakd_python=tmp_path / "py")
    assert s.oakd_interpreter == tmp_path / "py"


def test_from_env_lee_las_dos_variables(repo):
    s = ConsoleSettings.from_env(
        {
            "EOVRT_CONSOLE_REPO_ROOT": str(repo),
            "EOVRT_CONSOLE_RECORDINGS_DIR": "/data/raw",
            "EOVRT_CONSOLE_OAKD_PYTHON": "/opt/py312/bin/python",
        }
    )
    assert s.raw_dir == Path("/data/raw")
    assert s.oakd_interpreter == Path("/opt/py312/bin/python")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd webconsole/backend && ./.venv/bin/python -m pytest tests/test_recording_settings.py -v`
Expected: FAIL con `TypeError: ConsoleSettings.__init__() got an unexpected keyword argument 'recordings_dir'`.

- [ ] **Step 3: Write minimal implementation**

En `settings.py`, agregar los dos campos al final del `@dataclass` `ConsoleSettings` (después de `spa_dist`):

```python
    # Destino de los masters de rodaje. None = repo hermano e-ovrt_datasets.
    recordings_dir: Path | None = None
    # Intérprete con el SDK DepthAI para la rama OAK-D (el backend corre 3.14 y
    # depthai no tiene wheels para 3.14). None = venv del media-plane.
    oakd_python: Path | None = None
```

Agregar las dos propiedades junto a `cameras_dir`:

```python
    @property
    def raw_dir(self) -> Path:
        if self.recordings_dir is not None:
            return self.recordings_dir
        return self.repo_root.parent / "e-ovrt_datasets" / "datasets-videos" / "raw"

    @property
    def oakd_interpreter(self) -> Path:
        if self.oakd_python is not None:
            return self.oakd_python
        return self.repo_root.parent / "e-ovrt_media-plane" / ".venv" / "bin" / "python"
```

En `from_env`, agregar al `return cls(...)`:

```python
            recordings_dir=(
                Path(env["EOVRT_CONSOLE_RECORDINGS_DIR"])
                if env.get("EOVRT_CONSOLE_RECORDINGS_DIR")
                else None
            ),
            oakd_python=(
                Path(env["EOVRT_CONSOLE_OAKD_PYTHON"])
                if env.get("EOVRT_CONSOLE_OAKD_PYTHON")
                else None
            ),
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd webconsole/backend && ./.venv/bin/python -m pytest tests/test_recording_settings.py tests/test_settings.py -v`
Expected: PASS (5 nuevos + los existentes de `test_settings.py` sin romper).

- [ ] **Step 5: Commit**

```bash
git add webconsole/backend/src/eovrt_webconsole/settings.py webconsole/backend/tests/test_recording_settings.py
git commit -m "feat(webconsole): settings de grabacion (recordings_dir, oakd_python)"
```

---

### Task 2: Nombrado de tomas

**Files:**
- Create: `webconsole/backend/src/eovrt_webconsole/recording/__init__.py`
- Create: `webconsole/backend/src/eovrt_webconsole/recording/naming.py`
- Test: `webconsole/backend/tests/test_recording_naming.py`

**Interfaces:**
- Consumes: nada.
- Produces: `next_basename(raw_dir: Path, scenario: str, variant: str) -> str` y `InvalidTakeId(ValueError)`. También `BASENAME_RE: re.Pattern` para que otros módulos validen un basename ya armado.

- [ ] **Step 1: Write the failing test**

Crear `webconsole/backend/tests/test_recording_naming.py`:

```python
import pytest

from eovrt_webconsole.recording.naming import InvalidTakeId, next_basename


def test_primer_take_cuando_no_hay_nada(tmp_path):
    assert next_basename(tmp_path, "P1", "a") == "P1-a-take1"


def test_directorio_inexistente_devuelve_primer_take(tmp_path):
    assert next_basename(tmp_path / "no-existe", "P1", "a") == "P1-a-take1"


def test_autoincrementa_sobre_lo_existente(tmp_path):
    (tmp_path / "P1-a-take1.mp4").touch()
    (tmp_path / "P1-a-take2.mp4").touch()
    assert next_basename(tmp_path, "P1", "a") == "P1-a-take3"


def test_huecos_en_la_numeracion_no_reusan_numeros(tmp_path):
    (tmp_path / "P1-a-take1.mp4").touch()
    (tmp_path / "P1-a-take7.mp4").touch()
    assert next_basename(tmp_path, "P1", "a") == "P1-a-take8"


def test_no_se_mezclan_escenarios_ni_variantes(tmp_path):
    (tmp_path / "P1-a-take5.mp4").touch()
    (tmp_path / "P2-a-take9.mp4").touch()
    (tmp_path / "P1-b-take3.mp4").touch()
    assert next_basename(tmp_path, "P1", "a") == "P1-a-take6"
    assert next_basename(tmp_path, "P1", "b") == "P1-b-take4"
    assert next_basename(tmp_path, "P3", "a") == "P3-a-take1"


def test_ignora_archivos_ajenos(tmp_path):
    (tmp_path / "4.1.mp4").touch()
    (tmp_path / "P1-a-notatake.mp4").touch()
    assert next_basename(tmp_path, "P1", "a") == "P1-a-take1"


@pytest.mark.parametrize("scenario", ["P0", "P10", "x", "P", "P1a", ""])
def test_escenario_invalido(tmp_path, scenario):
    with pytest.raises(InvalidTakeId):
        next_basename(tmp_path, scenario, "a")


@pytest.mark.parametrize("variant", ["A", "ab", "1", ""])
def test_variante_invalida(tmp_path, variant):
    with pytest.raises(InvalidTakeId):
        next_basename(tmp_path, "P1", variant)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd webconsole/backend && ./.venv/bin/python -m pytest tests/test_recording_naming.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'eovrt_webconsole.recording'`.

- [ ] **Step 3: Write minimal implementation**

Crear `webconsole/backend/src/eovrt_webconsole/recording/__init__.py` vacío:

```python
"""Grabación de tomas de rodaje desde la consola (spec 2026-07-21)."""
```

Crear `webconsole/backend/src/eovrt_webconsole/recording/naming.py`:

```python
"""Nombrado de tomas: escenario + variante -> próximo basename libre."""

from __future__ import annotations

import re
from pathlib import Path

SCENARIO_RE = re.compile(r"^P[1-9]$")
VARIANT_RE = re.compile(r"^[a-z]$")
BASENAME_RE = re.compile(r"^P[1-9]-[a-z]-take[0-9]+$")


class InvalidTakeId(ValueError):
    pass


def next_basename(raw_dir: Path, scenario: str, variant: str) -> str:
    if not SCENARIO_RE.match(scenario):
        raise InvalidTakeId(f"escenario inválido: {scenario!r} (esperado P1..P9)")
    if not VARIANT_RE.match(variant):
        raise InvalidTakeId(f"variante inválida: {variant!r} (esperada una letra a-z)")
    take_re = re.compile(rf"^{scenario}-{variant}-take([0-9]+)\.mp4$")
    highest = 0
    if raw_dir.is_dir():
        for path in raw_dir.iterdir():
            match = take_re.match(path.name)
            if match is not None:
                highest = max(highest, int(match.group(1)))
    return f"{scenario}-{variant}-take{highest + 1}"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd webconsole/backend && ./.venv/bin/python -m pytest tests/test_recording_naming.py -v`
Expected: PASS, 16 tests (incluyendo los parametrizados).

- [ ] **Step 5: Commit**

```bash
git add webconsole/backend/src/eovrt_webconsole/recording/ webconsole/backend/tests/test_recording_naming.py
git commit -m "feat(webconsole): nombrado autoincremental de tomas de rodaje"
```

---

### Task 3: Tipos compartidos y gates de arranque

**Files:**
- Create: `webconsole/backend/src/eovrt_webconsole/recording/types.py`
- Create: `webconsole/backend/src/eovrt_webconsole/recording/guards.py`
- Test: `webconsole/backend/tests/test_recording_guards.py`

**Interfaces:**
- Consumes: `naming.BASENAME_RE`.
- Produces:
  - `CaptureSpec` (pydantic): `fps: int = 60`, `resolution: str = "1080p"`, `bitrate_bps: int = 25_000_000`, `keyframe_hz: float = 1.0`.
  - `RecordingSpec` (pydantic): `plugin: str`, `config: dict`, `basename: str`, `label: str | None`, `capture: CaptureSpec | None`, `max_duration_s: int = 600`.
  - `RecordingResult` (dataclass): `path: Path`, `started_wallclock_ms: int`, `duration_ms: int`, `size_bytes: int`, `truncated: bool`, `error: str | None`.
  - `RecordingStatus` (dataclass): `state: str` (`"recording" | "finished" | "error"`), `elapsed_ms: int`, `size_bytes: int`, `error: str | None`.
  - `Recorder` (Protocol): `start()`, `stop() -> RecordingResult`, `poll() -> RecordingStatus`.
  - `GateError(ValueError)`, `check_destination(raw_dir: Path) -> None`, `check_free_space(raw_dir: Path, min_gb: float = 5.0) -> None`.

- [ ] **Step 1: Write the failing test**

Crear `webconsole/backend/tests/test_recording_guards.py`:

```python
import pytest
from pydantic import ValidationError

from eovrt_webconsole.recording.guards import GateError, check_destination, check_free_space
from eovrt_webconsole.recording.types import CaptureSpec, RecordingSpec


def test_destino_valido(tmp_path):
    check_destination(tmp_path)  # no levanta


def test_destino_bajo_mnt_c_se_rechaza(tmp_path, monkeypatch):
    fake = tmp_path / "mnt" / "c" / "raw"
    fake.mkdir(parents=True)
    monkeypatch.setattr(
        "eovrt_webconsole.recording.guards._FORBIDDEN_PREFIXES", (str(tmp_path / "mnt" / "c"),)
    )
    with pytest.raises(GateError, match="/mnt/c"):
        check_destination(fake)


def test_destino_se_crea_si_no_existe(tmp_path):
    destino = tmp_path / "nuevo" / "raw"
    check_destination(destino)
    assert destino.is_dir()


def test_destino_que_es_un_archivo_se_rechaza(tmp_path):
    archivo = tmp_path / "soy-un-archivo"
    archivo.touch()
    with pytest.raises(GateError, match="no es un directorio"):
        check_destination(archivo)


def test_espacio_suficiente(tmp_path):
    check_free_space(tmp_path, min_gb=0.0)  # no levanta


def test_espacio_insuficiente(tmp_path):
    with pytest.raises(GateError, match="espacio"):
        check_free_space(tmp_path, min_gb=10_000_000.0)


def test_spec_rtsp_con_capture_es_invalida():
    with pytest.raises(ValidationError, match="capture"):
        RecordingSpec(
            plugin="rtsp",
            config={"url": "rtsp://cam/live"},
            basename="P1-a-take1",
            capture=CaptureSpec(),
        )


def test_spec_rtsp_sin_capture_es_valida():
    spec = RecordingSpec(plugin="rtsp", config={"url": "rtsp://cam/live"}, basename="P1-a-take1")
    assert spec.capture is None
    assert spec.max_duration_s == 600


def test_spec_oakd_completa_por_default():
    spec = RecordingSpec(plugin="oak_d", config={"url": "192.168.1.50"}, basename="P1-a-take1")
    assert spec.capture is not None
    assert spec.capture.fps == 60
    assert spec.capture.bitrate_bps == 25_000_000


def test_spec_rechaza_plugin_desconocido():
    with pytest.raises(ValidationError):
        RecordingSpec(plugin="image_folder", config={}, basename="P1-a-take1")


def test_spec_rechaza_basename_invalido():
    with pytest.raises(ValidationError):
        RecordingSpec(plugin="rtsp", config={"url": "x"}, basename="../../etc/passwd")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd webconsole/backend && ./.venv/bin/python -m pytest tests/test_recording_guards.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'eovrt_webconsole.recording.guards'`.

- [ ] **Step 3: Write minimal implementation**

Crear `webconsole/backend/src/eovrt_webconsole/recording/types.py`:

```python
"""Contratos de la grabación: request, resultado, estado e interfaz de recorder."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from eovrt_webconsole.recording.naming import BASENAME_RE

RECORDABLE_PLUGINS = frozenset({"rtsp", "oak_d"})
OAK_D_RESOLUTIONS = frozenset({"720p", "1080p", "4k"})


class CaptureSpec(BaseModel):
    """Parámetros de captura. Solo aplican a oak_d (en rtsp manda el DVR)."""

    model_config = ConfigDict(extra="forbid")

    fps: int = 60
    resolution: str = "1080p"
    bitrate_bps: int = 25_000_000
    keyframe_hz: float = 1.0

    @field_validator("resolution")
    @classmethod
    def _resolucion_soportada(cls, v: str) -> str:
        if v not in OAK_D_RESOLUTIONS:
            raise ValueError(f"resolution debe ser una de {sorted(OAK_D_RESOLUTIONS)}")
        return v

    @field_validator("fps")
    @classmethod
    def _fps_positivo(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("fps debe ser > 0")
        return v


class RecordingSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plugin: str
    config: dict
    basename: str
    label: str | None = None
    capture: CaptureSpec | None = None
    max_duration_s: int = 600

    @field_validator("plugin")
    @classmethod
    def _plugin_grabable(cls, v: str) -> str:
        if v not in RECORDABLE_PLUGINS:
            raise ValueError(f"plugin no grabable: {v!r} (esperado rtsp u oak_d)")
        return v

    @field_validator("basename")
    @classmethod
    def _basename_valido(cls, v: str) -> str:
        if not BASENAME_RE.match(v):
            raise ValueError(f"basename inválido: {v!r} (esperado P<n>-<x>-take<n>)")
        return v

    @model_validator(mode="after")
    def _capture_solo_para_oakd(self) -> "RecordingSpec":
        if self.plugin == "rtsp" and self.capture is not None:
            raise ValueError(
                "capture no aplica a plugin rtsp: se graba lo que emite el DVR"
            )
        if self.plugin == "oak_d" and self.capture is None:
            object.__setattr__(self, "capture", CaptureSpec())
        return self


@dataclass(frozen=True)
class RecordingResult:
    path: Path
    started_wallclock_ms: int
    duration_ms: int
    size_bytes: int
    truncated: bool
    error: str | None = None


@dataclass(frozen=True)
class RecordingStatus:
    state: Literal["recording", "finished", "error"]
    elapsed_ms: int
    size_bytes: int
    error: str | None = None


class Recorder(Protocol):
    def start(self) -> None: ...

    def stop(self) -> RecordingResult: ...

    def poll(self) -> RecordingStatus: ...
```

Crear `webconsole/backend/src/eovrt_webconsole/recording/guards.py`:

```python
"""Gates de arranque de una grabación: destino y espacio libre."""

from __future__ import annotations

import shutil
from pathlib import Path

# El filesystem cruzado de WSL es lo bastante lento como para perder frames por
# I/O durante una toma; se rechaza antes de grabar, no después.
_FORBIDDEN_PREFIXES = ("/mnt/c", "/mnt/d", "/mnt/e")


class GateError(ValueError):
    pass


def check_destination(raw_dir: Path) -> None:
    resolved = raw_dir.expanduser().resolve()
    for prefix in _FORBIDDEN_PREFIXES:
        if str(resolved) == prefix or str(resolved).startswith(prefix + "/"):
            raise GateError(
                f"destino bajo {prefix}: el filesystem cruzado de WSL es demasiado "
                "lento para grabar sin perder frames"
            )
    if resolved.exists() and not resolved.is_dir():
        raise GateError(f"el destino no es un directorio: {resolved}")
    resolved.mkdir(parents=True, exist_ok=True)


def check_free_space(raw_dir: Path, min_gb: float = 5.0) -> None:
    target = raw_dir if raw_dir.exists() else raw_dir.parent
    free_gb = shutil.disk_usage(target).free / (1024**3)
    if free_gb < min_gb:
        raise GateError(
            f"espacio insuficiente en {target}: {free_gb:.1f} GB libres, "
            f"se requieren {min_gb:.1f} GB"
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd webconsole/backend && ./.venv/bin/python -m pytest tests/test_recording_guards.py -v`
Expected: PASS, 11 tests.

- [ ] **Step 5: Commit**

```bash
git add webconsole/backend/src/eovrt_webconsole/recording/types.py webconsole/backend/src/eovrt_webconsole/recording/guards.py webconsole/backend/tests/test_recording_guards.py
git commit -m "feat(webconsole): contratos y gates de la grabacion de rodaje"
```

---

### Task 4: Medición del archivo cerrado (ffprobe)

**Files:**
- Create: `webconsole/backend/src/eovrt_webconsole/recording/probe.py`
- Test: `webconsole/backend/tests/test_recording_probe.py`

**Interfaces:**
- Consumes: nada.
- Produces: `measure(path: Path) -> Measured` con `Measured` dataclass: `width: int`, `height: int`, `fps: float`, `duration_ms: int`. Levanta `ProbeError(RuntimeError)` si ffprobe falla o el archivo no tiene stream de video.

**Nota para quien implemente:** no se usa `-count_frames` (recorre el archivo entero y en una toma de 6 minutos tarda demasiado). `avg_frame_rate` y `format=duration` alcanzan y son O(1).

- [ ] **Step 1: Write the failing test**

Crear `webconsole/backend/tests/test_recording_probe.py`:

```python
import shutil
import subprocess

import pytest

from eovrt_webconsole.recording.probe import ProbeError, measure

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="requiere ffmpeg y ffprobe en el sistema",
)


@pytest.fixture
def video_2s(tmp_path):
    """2 segundos de barras de color a 25 fps, 320x240."""
    out = tmp_path / "muestra.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", "testsrc=size=320x240:rate=25:duration=2",
            "-c:v", "libx264", "-preset", "ultrafast", str(out),
        ],
        check=True,
    )
    return out


def test_mide_dimensiones_fps_y_duracion(video_2s):
    m = measure(video_2s)
    assert (m.width, m.height) == (320, 240)
    assert m.fps == pytest.approx(25.0, abs=0.1)
    assert m.duration_ms == pytest.approx(2000, abs=100)


def test_archivo_inexistente(tmp_path):
    with pytest.raises(ProbeError):
        measure(tmp_path / "no-existe.mp4")


def test_archivo_vacio_no_es_video(tmp_path):
    vacio = tmp_path / "vacio.mp4"
    vacio.touch()
    with pytest.raises(ProbeError):
        measure(vacio)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd webconsole/backend && ./.venv/bin/python -m pytest tests/test_recording_probe.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'eovrt_webconsole.recording.probe'`.

- [ ] **Step 3: Write minimal implementation**

Crear `webconsole/backend/src/eovrt_webconsole/recording/probe.py`:

```python
"""Medición del master ya cerrado con ffprobe (sin recorrer el archivo)."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


class ProbeError(RuntimeError):
    pass


@dataclass(frozen=True)
class Measured:
    width: int
    height: int
    fps: float
    duration_ms: int


def _parse_rate(raw: str) -> float:
    if not raw or raw in {"0/0", "N/A"}:
        return 0.0
    if "/" in raw:
        num, den = raw.split("/", 1)
        return float(num) / float(den) if float(den) else 0.0
    return float(raw)


def measure(path: Path) -> Measured:
    try:
        completed = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height,avg_frame_rate:format=duration",
                "-of", "json",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ProbeError(f"ffprobe falló sobre {path}: {exc}") from exc
    if completed.returncode != 0:
        raise ProbeError(f"ffprobe devolvió {completed.returncode} sobre {path}: {completed.stderr.strip()}")
    try:
        data = json.loads(completed.stdout)
        stream = data["streams"][0]
    except (json.JSONDecodeError, KeyError, IndexError) as exc:
        raise ProbeError(f"{path} no tiene stream de video legible") from exc
    duration_raw = data.get("format", {}).get("duration")
    return Measured(
        width=int(stream["width"]),
        height=int(stream["height"]),
        fps=_parse_rate(str(stream.get("avg_frame_rate", "0/0"))),
        duration_ms=int(round(float(duration_raw) * 1000)) if duration_raw else 0,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd webconsole/backend && ./.venv/bin/python -m pytest tests/test_recording_probe.py -v`
Expected: PASS, 3 tests.

- [ ] **Step 5: Commit**

```bash
git add webconsole/backend/src/eovrt_webconsole/recording/probe.py webconsole/backend/tests/test_recording_probe.py
git commit -m "feat(webconsole): medicion del master con ffprobe"
```

---

### Task 5: Sidecar de procedencia

**Files:**
- Create: `webconsole/backend/src/eovrt_webconsole/recording/sidecar.py`
- Test: `webconsole/backend/tests/test_recording_sidecar.py`

**Interfaces:**
- Consumes: `types.RecordingSpec`, `types.RecordingResult`, `probe.Measured`.
- Produces: `write_sidecar(spec: RecordingSpec, result: RecordingResult, measured: Measured | None) -> Path` y `sha256_of(path: Path) -> str`. El sidecar se escribe junto al master, con extensión `.rec.json`.

- [ ] **Step 1: Write the failing test**

Crear `webconsole/backend/tests/test_recording_sidecar.py`:

```python
import hashlib
import json

from eovrt_webconsole.recording.probe import Measured
from eovrt_webconsole.recording.sidecar import sha256_of, write_sidecar
from eovrt_webconsole.recording.types import RecordingResult, RecordingSpec


def _result(path, **kwargs):
    base = dict(
        path=path,
        started_wallclock_ms=1784646000000,
        duration_ms=33150,
        size_bytes=path.stat().st_size,
        truncated=False,
        error=None,
    )
    base.update(kwargs)
    return RecordingResult(**base)


def test_sha256_coincide_con_hashlib(tmp_path):
    archivo = tmp_path / "x.mp4"
    archivo.write_bytes(b"contenido de prueba")
    assert sha256_of(archivo) == hashlib.sha256(b"contenido de prueba").hexdigest()


def test_sidecar_oakd_tiene_requested_y_measured(tmp_path):
    master = tmp_path / "P1-a-take2.mp4"
    master.write_bytes(b"\x00" * 1024)
    spec = RecordingSpec(
        plugin="oak_d", config={"url": "192.168.1.50"}, basename="P1-a-take2", label="oak_d_lab"
    )
    path = write_sidecar(spec, _result(master), Measured(1920, 1080, 59.94, 33150))

    assert path == tmp_path / "P1-a-take2.rec.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["basename"] == "P1-a-take2"
    assert data["camera_id"] == "oak_d_lab"
    assert data["plugin"] == "oak_d"
    assert data["requested"] == {
        "fps": 60,
        "resolution": "1080p",
        "codec": "h264",
        "bitrate_bps": 25_000_000,
    }
    assert data["measured"]["resolution"] == "1920x1080"
    assert data["measured"]["fps"] == 59.94
    assert data["truncated"] is False
    assert data["sha256"] == sha256_of(master)


def test_sidecar_rtsp_tiene_requested_vacio(tmp_path):
    master = tmp_path / "P2-a-take1.mp4"
    master.write_bytes(b"\x00" * 16)
    spec = RecordingSpec(plugin="rtsp", config={"url": "rtsp://cam/live"}, basename="P2-a-take1")
    data = json.loads(
        write_sidecar(spec, _result(master), Measured(1280, 720, 15.0, 20000)).read_text()
    )
    assert data["requested"] == {}
    assert data["camera_id"] is None


def test_sidecar_de_toma_truncada_sin_medicion(tmp_path):
    master = tmp_path / "P1-a-take3.mp4"
    master.write_bytes(b"\x00" * 8)
    spec = RecordingSpec(plugin="rtsp", config={"url": "rtsp://cam/live"}, basename="P1-a-take3")
    data = json.loads(
        write_sidecar(
            spec, _result(master, truncated=True, error="ffmpeg murió con rc=1"), None
        ).read_text()
    )
    assert data["truncated"] is True
    assert data["error"] == "ffmpeg murió con rc=1"
    assert data["measured"]["resolution"] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd webconsole/backend && ./.venv/bin/python -m pytest tests/test_recording_sidecar.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'eovrt_webconsole.recording.sidecar'`.

- [ ] **Step 3: Write minimal implementation**

Crear `webconsole/backend/src/eovrt_webconsole/recording/sidecar.py`:

```python
"""Sidecar <basename>.rec.json: procedencia técnica del master grabado."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from eovrt_webconsole.recording.probe import Measured
from eovrt_webconsole.recording.types import RecordingResult, RecordingSpec

_CHUNK = 1024 * 1024


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(_CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def write_sidecar(
    spec: RecordingSpec, result: RecordingResult, measured: Measured | None
) -> Path:
    # `requested` sale vacío en rtsp: no se pidió nada, manda el DVR. La asimetría
    # con `measured` es deliberada -- si el DVR entregó 12 fps cuando se esperaban
    # 60, tiene que quedar registrado y no descubrirse meses después.
    requested: dict = {}
    if spec.capture is not None:
        requested = {
            "fps": spec.capture.fps,
            "resolution": spec.capture.resolution,
            "codec": "h264",
            "bitrate_bps": spec.capture.bitrate_bps,
        }
    payload = {
        "basename": spec.basename,
        "file": f"raw/{result.path.name}",
        "camera_id": spec.label,
        "plugin": spec.plugin,
        "requested": requested,
        "measured": {
            "fps": measured.fps if measured else None,
            "resolution": f"{measured.width}x{measured.height}" if measured else None,
            "duration_ms": measured.duration_ms if measured else result.duration_ms,
            "size_bytes": result.size_bytes,
        },
        "started_wallclock_ms": result.started_wallclock_ms,
        "truncated": result.truncated,
        "error": result.error,
        "sha256": sha256_of(result.path),
    }
    out = result.path.with_suffix(".rec.json")
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd webconsole/backend && ./.venv/bin/python -m pytest tests/test_recording_sidecar.py -v`
Expected: PASS, 4 tests.

- [ ] **Step 5: Commit**

```bash
git add webconsole/backend/src/eovrt_webconsole/recording/sidecar.py webconsole/backend/tests/test_recording_sidecar.py
git commit -m "feat(webconsole): sidecar de procedencia del master grabado"
```

---

### Task 6: Rama RTSP (FfmpegCopyRecorder)

**Files:**
- Create: `webconsole/backend/src/eovrt_webconsole/recording/ffmpeg_recorder.py`
- Test: `webconsole/backend/tests/test_ffmpeg_recorder.py`

**Interfaces:**
- Consumes: `types.Recorder`, `types.RecordingSpec`, `types.RecordingResult`, `types.RecordingStatus`.
- Produces: `FfmpegCopyRecorder(spec: RecordingSpec, out_path: Path)` que implementa `Recorder`, y `build_ffmpeg_args(url: str, out_path: Path) -> list[str]`.

**Notas para quien implemente:**
- El corte limpio es `SIGINT`: ffmpeg finaliza el átomo `moov` y el mp4 queda reproducible. Un `SIGKILL` deja un archivo corrupto.
- `-rtsp_transport tcp` es obligatorio: sobre UDP el DVR pierde paquetes y aparecen macrobloques irreversibles en el master.
- La URL puede traer credenciales en claro; nunca loguearla sin redactar.
- El test usa `file://` en vez de RTSP: ejercita el mismo camino (spawn, corte, remux, medición) sin red ni cámara.

- [ ] **Step 1: Write the failing test**

Crear `webconsole/backend/tests/test_ffmpeg_recorder.py`:

```python
import shutil
import subprocess
import time

import pytest

from eovrt_webconsole.recording.ffmpeg_recorder import FfmpegCopyRecorder, build_ffmpeg_args
from eovrt_webconsole.recording.probe import measure
from eovrt_webconsole.recording.types import RecordingSpec

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="requiere ffmpeg y ffprobe en el sistema",
)


@pytest.fixture
def fuente_larga(tmp_path):
    """10 s de video a 25 fps: alcanza para arrancar, esperar y cortar."""
    out = tmp_path / "fuente.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", "testsrc=size=320x240:rate=25:duration=10",
            "-c:v", "libx264", "-preset", "ultrafast", "-g", "25", str(out),
        ],
        check=True,
    )
    return out


def _spec(url: str) -> RecordingSpec:
    return RecordingSpec(plugin="rtsp", config={"url": url}, basename="P1-a-take1")


def test_args_fuerzan_tcp_y_copy():
    args = build_ffmpeg_args("rtsp://cam/live", "/tmp/x.mp4")
    assert "-rtsp_transport" in args and args[args.index("-rtsp_transport") + 1] == "tcp"
    assert "-c" in args and args[args.index("-c") + 1] == "copy"
    assert args[-1] == "/tmp/x.mp4"


def test_graba_y_corta_produciendo_un_mp4_reproducible(tmp_path, fuente_larga):
    destino = tmp_path / "P1-a-take1.mp4"
    recorder = FfmpegCopyRecorder(_spec(f"file://{fuente_larga}"), destino)
    recorder.start()
    time.sleep(2.0)
    estado = recorder.poll()
    assert estado.state == "recording"
    result = recorder.stop()

    assert result.path == destino
    assert destino.exists() and result.size_bytes > 0
    assert result.truncated is False
    assert measure(destino).width == 320


def test_poll_reporta_error_si_la_fuente_no_existe(tmp_path):
    destino = tmp_path / "P1-a-take1.mp4"
    recorder = FfmpegCopyRecorder(_spec("file:///no/existe/nada.mp4"), destino)
    recorder.start()
    deadline = time.monotonic() + 10
    while recorder.poll().state == "recording" and time.monotonic() < deadline:
        time.sleep(0.1)
    assert recorder.poll().state == "error"
    result = recorder.stop()
    assert result.truncated is True
    assert result.error is not None


def test_stop_sin_start_es_error_explicito(tmp_path):
    recorder = FfmpegCopyRecorder(_spec("file:///x"), tmp_path / "P1-a-take1.mp4")
    with pytest.raises(RuntimeError, match="sin arrancar"):
        recorder.stop()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd webconsole/backend && ./.venv/bin/python -m pytest tests/test_ffmpeg_recorder.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'eovrt_webconsole.recording.ffmpeg_recorder'`.

- [ ] **Step 3: Write minimal implementation**

Crear `webconsole/backend/src/eovrt_webconsole/recording/ffmpeg_recorder.py`:

```python
"""Rama RTSP: ffmpeg -c copy, sin transcodificar. El host no toca los píxeles."""

from __future__ import annotations

import logging
import signal
import subprocess
import time
from pathlib import Path

from eovrt_webconsole.recording.types import RecordingResult, RecordingSpec, RecordingStatus

logger = logging.getLogger(__name__)

_STOP_TIMEOUT_S = 15.0


def build_ffmpeg_args(url: str, out_path: str | Path) -> list[str]:
    # -rtsp_transport tcp NO es opcional: sobre UDP el DVR pierde paquetes y el
    # master queda con macrobloques, daño que ningún paso posterior repara.
    return [
        "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
        "-rtsp_transport", "tcp",
        "-i", str(url),
        "-c", "copy",
        "-movflags", "+faststart",
        "-y",
        str(out_path),
    ]


class FfmpegCopyRecorder:
    def __init__(self, spec: RecordingSpec, out_path: Path) -> None:
        self._spec = spec
        self._path = out_path
        self._proc: subprocess.Popen | None = None
        self._started_ms: int = 0
        self._started_monotonic: float = 0.0
        self._stderr: str = ""

    def start(self) -> None:
        args = build_ffmpeg_args(str(self._spec.config.get("url", "")), self._path)
        self._started_ms = int(time.time() * 1000)
        self._started_monotonic = time.monotonic()
        self._proc = subprocess.Popen(
            args, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True
        )
        logger.info("Grabación RTSP arrancada -> %s", self._path.name)

    def poll(self) -> RecordingStatus:
        if self._proc is None:
            return RecordingStatus("error", 0, 0, "grabación sin arrancar")
        elapsed = int((time.monotonic() - self._started_monotonic) * 1000)
        size = self._path.stat().st_size if self._path.exists() else 0
        rc = self._proc.poll()
        if rc is None:
            return RecordingStatus("recording", elapsed, size)
        if rc == 0:
            return RecordingStatus("finished", elapsed, size)
        return RecordingStatus("error", elapsed, size, self._read_stderr() or f"ffmpeg rc={rc}")

    def stop(self) -> RecordingResult:
        if self._proc is None:
            raise RuntimeError("no se puede detener una grabación sin arrancar")
        rc = self._proc.poll()
        murio_solo = rc is not None
        if not murio_solo:
            # SIGINT y no SIGKILL: ffmpeg finaliza el átomo moov y el mp4 queda
            # reproducible. Matarlo a lo bruto deja un archivo corrupto.
            self._proc.send_signal(signal.SIGINT)
            try:
                self._proc.wait(timeout=_STOP_TIMEOUT_S)
            except subprocess.TimeoutExpired:
                logger.warning("ffmpeg no cerró en %ss, se mata", _STOP_TIMEOUT_S)
                self._proc.kill()
                self._proc.wait(timeout=5)
            rc = self._proc.returncode
        error = self._read_stderr() if murio_solo and rc not in (0, None) else None
        if murio_solo and error is None and rc not in (0, None):
            error = f"ffmpeg terminó solo con rc={rc}"
        return RecordingResult(
            path=self._path,
            started_wallclock_ms=self._started_ms,
            duration_ms=int((time.monotonic() - self._started_monotonic) * 1000),
            size_bytes=self._path.stat().st_size if self._path.exists() else 0,
            truncated=murio_solo,
            error=error,
        )

    def _read_stderr(self) -> str:
        if self._stderr:
            return self._stderr
        if self._proc is not None and self._proc.stderr is not None:
            try:
                self._stderr = self._proc.stderr.read().strip()
            except (ValueError, OSError):
                self._stderr = ""
        return self._stderr
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd webconsole/backend && ./.venv/bin/python -m pytest tests/test_ffmpeg_recorder.py -v`
Expected: PASS, 4 tests.

- [ ] **Step 5: Commit**

```bash
git add webconsole/backend/src/eovrt_webconsole/recording/ffmpeg_recorder.py webconsole/backend/tests/test_ffmpeg_recorder.py
git commit -m "feat(webconsole): grabacion RTSP por copia de bitstream"
```

---

### Task 7: Script standalone `record_oakd.py`

**Files:**
- Create: `webconsole/tools/record_oakd.py`
- Create: `webconsole/backend/tests/stubs/depthai.py`
- Test: `webconsole/backend/tests/test_record_oakd_script.py`

**Interfaces:**
- Consumes: nada del repo. Solo argv y el SDK DepthAI.
- Produces: contrato de línea de comandos y de stdout, que consume `OakDSubprocessRecorder` (Task 8):
  - Invocación: `python record_oakd.py --device <ip> --out <path> --fps <n> --resolution <720p|1080p|4k> --bitrate <bps> --keyframe-hz <f>`
  - stdout, una línea JSON por evento: `{"event": "started"}` al abrir el dispositivo, `{"event": "finished", "bytes_written": <n>}` al cerrar.
  - Códigos de salida: `0` ok, `2` argumentos inválidos, `3` SDK DepthAI ausente, `4` fallo del dispositivo.
  - `SIGTERM`/`SIGINT` = corte limpio: drena lo pendiente, cierra el archivo y emite `finished`.

**Notas para quien implemente:**
- Este archivo corre con **Python 3.12** (el venv del media-plane). No usar sintaxis de 3.13+ ni importar nada de `eovrt_webconsole`.
- Escribe H.264 **crudo** (elementary stream). El muxeo a mp4 lo hace `OakDSubprocessRecorder` con ffmpeg al cerrar (Task 8).
- `_load_sdk()` aislado es la costura que permite testear con el stub, igual que hace `oak_d_source.py` en el media-plane.

- [ ] **Step 1: Write the failing test**

Crear el stub `webconsole/backend/tests/stubs/depthai.py`:

```python
"""Stub mínimo de DepthAI para testear record_oakd.py sin hardware ni SDK real."""


class _Node:
    def __init__(self):
        self.out = self
        self.bitstream = self
        self.video = self
        self.input = self

    def link(self, other):
        return None

    def __getattr__(self, name):
        # Todos los setters del SDK (setFps, setResolution, setBitrate, ...) son no-op.
        return lambda *args, **kwargs: None


class _Queue:
    def __init__(self):
        self._emitted = 0

    def get(self):
        self._emitted += 1
        return _Packet(b"\x00\x00\x00\x01" + b"\xaa" * 256)

    def tryGet(self):
        return self.get()


class _Packet:
    def __init__(self, payload):
        self._payload = payload

    def getData(self):
        return self._payload


class Device:
    def __init__(self, pipeline, device_info=None, *args, **kwargs):
        self.pipeline = pipeline

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def getOutputQueue(self, name, maxSize=30, blocking=True):
        return _Queue()

    def close(self):
        return None


class DeviceInfo:
    def __init__(self, ip):
        self.ip = ip


class Pipeline:
    def create(self, node_cls):
        return _Node()


class _NodeNamespace:
    ColorCamera = object
    VideoEncoder = object
    XLinkOut = object


node = _NodeNamespace()


class CameraBoardSocket:
    CAM_A = "CAM_A"


class _SensorResolution:
    THE_720_P = "720p"
    THE_1080_P = "1080p"
    THE_4_K = "4k"


class ColorCameraProperties:
    SensorResolution = _SensorResolution


class _Profile:
    H264_MAIN = "h264_main"


class VideoEncoderProperties:
    Profile = _Profile
```

Crear `webconsole/backend/tests/test_record_oakd_script.py`:

```python
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

SCRIPT = (
    Path(__file__).resolve().parents[2] / "tools" / "record_oakd.py"
)
STUBS = Path(__file__).resolve().parent / "stubs"


def _run(args, env_extra=None, timeout=20):
    env = {**os.environ, **(env_extra or {})}
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True, timeout=timeout, env=env,
    )


def test_el_script_existe():
    assert SCRIPT.is_file()


def test_argumentos_invalidos_salen_con_2(tmp_path):
    completed = _run(["--device", "192.168.1.50", "--out", str(tmp_path / "x.h264"),
                      "--resolution", "8k"])
    assert completed.returncode == 2


def test_sin_sdk_sale_con_3(tmp_path):
    completed = _run(
        ["--device", "192.168.1.50", "--out", str(tmp_path / "x.h264")],
        env_extra={"PYTHONPATH": "/ruta/que/no/tiene/depthai"},
    )
    assert completed.returncode == 3
    assert "depthai" in (completed.stdout + completed.stderr).lower()


def test_graba_contra_el_stub_y_corta_con_sigterm(tmp_path):
    salida = tmp_path / "toma.h264"
    proc = subprocess.Popen(
        [sys.executable, str(SCRIPT), "--device", "192.168.1.50", "--out", str(salida),
         "--fps", "60", "--resolution", "1080p", "--bitrate", "25000000"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        env={**os.environ, "PYTHONPATH": str(STUBS)},
    )
    primera = proc.stdout.readline()
    assert json.loads(primera)["event"] == "started"

    time.sleep(1.0)
    proc.send_signal(signal.SIGTERM)
    stdout, _ = proc.communicate(timeout=15)

    assert proc.returncode == 0
    ultima = json.loads([line for line in stdout.splitlines() if line.strip()][-1])
    assert ultima["event"] == "finished"
    assert ultima["bytes_written"] > 0
    assert salida.stat().st_size == ultima["bytes_written"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd webconsole/backend && ./.venv/bin/python -m pytest tests/test_record_oakd_script.py -v`
Expected: FAIL en `test_el_script_existe` con `assert False` (el script todavía no existe).

- [ ] **Step 3: Write minimal implementation**

Crear `webconsole/tools/record_oakd.py`:

```python
#!/usr/bin/env python3
"""Graba la OAK-D a H.264 crudo usando el encoder por hardware del dispositivo.

Standalone a propósito: NO importa nada del webconsole y corre con el intérprete
que tenga el SDK DepthAI (el backend de la consola es 3.14 y depthai no publica
wheels para 3.14). Se puede correr a mano desde una terminal, que es el plan B
si la consola falla en obra:

    python record_oakd.py --device 192.168.1.50 --out toma.h264 --fps 60

Contrato con el proceso padre: una línea JSON por evento en stdout
({"event": "started"} / {"event": "finished", "bytes_written": N}) y corte
limpio con SIGTERM o SIGINT. Códigos de salida: 0 ok, 2 argumentos inválidos,
3 SDK ausente, 4 fallo del dispositivo.
"""

from __future__ import annotations

import argparse
import json
import signal
import sys

RESOLUTIONS = {"720p": "THE_720_P", "1080p": "THE_1080_P", "4k": "THE_4_K"}

_stop = False


def _emit(**payload) -> None:
    sys.stdout.write(json.dumps(payload) + "\n")
    sys.stdout.flush()


def _handle_stop(signum, frame) -> None:
    global _stop
    _stop = True


def _load_sdk():
    """Costura de import: permite inyectar un stub por PYTHONPATH en los tests."""
    import depthai

    return depthai


def _parse_args(argv):
    parser = argparse.ArgumentParser(description="Grabador OAK-D por hardware")
    parser.add_argument("--device", required=True, help="IP fija de la OAK-D PoE")
    parser.add_argument("--out", required=True, help="Archivo de salida (.h264 crudo)")
    parser.add_argument("--fps", type=int, default=60)
    parser.add_argument("--resolution", choices=sorted(RESOLUTIONS), default="1080p")
    parser.add_argument("--bitrate", type=int, default=25_000_000)
    parser.add_argument("--keyframe-hz", type=float, default=1.0, dest="keyframe_hz")
    args = parser.parse_args(argv)
    if args.fps <= 0:
        parser.error("--fps debe ser > 0")
    if args.bitrate <= 0:
        parser.error("--bitrate debe ser > 0")
    return args


def _build_pipeline(dai, args):
    pipeline = dai.Pipeline()
    cam = pipeline.create(dai.node.ColorCamera)
    cam.setBoardSocket(dai.CameraBoardSocket.CAM_A)
    cam.setResolution(
        getattr(dai.ColorCameraProperties.SensorResolution, RESOLUTIONS[args.resolution])
    )
    cam.setFps(args.fps)

    encoder = pipeline.create(dai.node.VideoEncoder)
    # Keyframes ~1 s: el re-ventaneo de la etapa 0 con --ss/--to es exacto y barato
    # si hay keyframes cerca; con GOP largo ffmpeg corta mal o re-encodea.
    encoder.setDefaultProfilePreset(args.fps, dai.VideoEncoderProperties.Profile.H264_MAIN)
    encoder.setBitrate(args.bitrate)
    encoder.setKeyframeFrequency(max(1, int(round(args.fps / max(args.keyframe_hz, 0.01)))))
    cam.video.link(encoder.input)

    xout = pipeline.create(dai.node.XLinkOut)
    xout.setStreamName("h264")
    encoder.bitstream.link(xout.input)
    return pipeline


def main(argv=None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)

    try:
        dai = _load_sdk()
    except ImportError as exc:
        _emit(event="error", reason=f"SDK depthai no disponible: {exc}")
        return 3

    signal.signal(signal.SIGTERM, _handle_stop)
    signal.signal(signal.SIGINT, _handle_stop)

    written = 0
    try:
        pipeline = _build_pipeline(dai, args)
        device_info = dai.DeviceInfo(args.device)
        with dai.Device(pipeline, device_info) as device:
            queue = device.getOutputQueue("h264", maxSize=30, blocking=True)
            with open(args.out, "wb") as handle:
                _emit(event="started")
                while not _stop:
                    packet = queue.get()
                    if packet is None:
                        continue
                    data = packet.getData()
                    handle.write(data)
                    written += len(data)
                handle.flush()
    except Exception as exc:  # noqa: BLE001 - cualquier fallo del dispositivo
        _emit(event="error", reason=str(exc), bytes_written=written)
        return 4

    _emit(event="finished", bytes_written=written)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd webconsole/backend && ./.venv/bin/python -m pytest tests/test_record_oakd_script.py -v`
Expected: PASS, 4 tests.

- [ ] **Step 5: Commit**

```bash
git add webconsole/tools/record_oakd.py webconsole/backend/tests/stubs/depthai.py webconsole/backend/tests/test_record_oakd_script.py
git commit -m "feat(webconsole): script standalone de grabacion OAK-D por hardware"
```

---

### Task 8: Rama OAK-D (OakDSubprocessRecorder)

**Files:**
- Create: `webconsole/backend/src/eovrt_webconsole/recording/oakd_recorder.py`
- Test: `webconsole/backend/tests/test_oakd_recorder.py`

**Interfaces:**
- Consumes: el contrato de `tools/record_oakd.py` (Task 7); `types.RecordingSpec`, `types.RecordingResult`, `types.RecordingStatus`.
- Produces: `OakDSubprocessRecorder(spec, out_path, interpreter: Path, script: Path)` que implementa `Recorder`, y `check_interpreter(interpreter: Path) -> None` que levanta `InterpreterUnavailable(RuntimeError)`.

**Notas para quien implemente:**
- El script escribe H.264 crudo a `<out_path>.h264`; al cerrar, este recorder **muxea a mp4** con `ffmpeg -f h264 -r <fps> -i <raw> -c copy <out.mp4>` y borra el crudo. Si el muxeo falla, se conserva el `.h264` y el resultado sale `truncated=True` — nunca se borra material.
- `check_interpreter` se llama **al arrancar el backend** (Task 11), no al apretar grabar.

- [ ] **Step 1: Write the failing test**

Crear `webconsole/backend/tests/test_oakd_recorder.py`:

```python
import shutil
import sys
import time
from pathlib import Path

import pytest

from eovrt_webconsole.recording.oakd_recorder import (
    InterpreterUnavailable,
    OakDSubprocessRecorder,
    check_interpreter,
)
from eovrt_webconsole.recording.types import RecordingSpec

SCRIPT_REAL = Path(__file__).resolve().parents[2] / "tools" / "record_oakd.py"
STUBS = Path(__file__).resolve().parent / "stubs"

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None, reason="requiere ffmpeg en el sistema"
)


def _spec() -> RecordingSpec:
    return RecordingSpec(
        plugin="oak_d", config={"url": "192.168.1.50"}, basename="P1-a-take1", label="oak_d_lab"
    )


def test_check_interpreter_acepta_el_interprete_actual():
    check_interpreter(Path(sys.executable))  # no levanta (no valida depthai acá)


def test_check_interpreter_rechaza_una_ruta_inexistente():
    with pytest.raises(InterpreterUnavailable):
        check_interpreter(Path("/no/existe/python"))


def test_graba_contra_el_stub_y_muxea_a_mp4(tmp_path, monkeypatch):
    monkeypatch.setenv("PYTHONPATH", str(STUBS))
    destino = tmp_path / "P1-a-take1.mp4"
    recorder = OakDSubprocessRecorder(
        _spec(), destino, interpreter=Path(sys.executable), script=SCRIPT_REAL
    )
    recorder.start()
    time.sleep(1.5)
    assert recorder.poll().state == "recording"
    result = recorder.stop()

    assert destino.exists()
    assert result.size_bytes > 0
    assert result.truncated is False
    assert not destino.with_suffix(".h264").exists()  # el crudo se limpia tras muxear


def test_script_inexistente_deja_la_toma_en_error(tmp_path):
    destino = tmp_path / "P1-a-take1.mp4"
    recorder = OakDSubprocessRecorder(
        _spec(), destino, interpreter=Path(sys.executable), script=tmp_path / "no-existe.py"
    )
    recorder.start()
    deadline = time.monotonic() + 10
    while recorder.poll().state == "recording" and time.monotonic() < deadline:
        time.sleep(0.1)
    assert recorder.poll().state == "error"
    result = recorder.stop()
    assert result.truncated is True
    assert result.error is not None


def test_stop_sin_start_es_error_explicito(tmp_path):
    recorder = OakDSubprocessRecorder(
        _spec(), tmp_path / "P1-a-take1.mp4", interpreter=Path(sys.executable), script=SCRIPT_REAL
    )
    with pytest.raises(RuntimeError, match="sin arrancar"):
        recorder.stop()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd webconsole/backend && ./.venv/bin/python -m pytest tests/test_oakd_recorder.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'eovrt_webconsole.recording.oakd_recorder'`.

- [ ] **Step 3: Write minimal implementation**

Crear `webconsole/backend/src/eovrt_webconsole/recording/oakd_recorder.py`:

```python
"""Rama OAK-D: lanza tools/record_oakd.py con el intérprete que tiene depthai."""

from __future__ import annotations

import logging
import signal
import subprocess
import time
from pathlib import Path

from eovrt_webconsole.recording.types import RecordingResult, RecordingSpec, RecordingStatus

logger = logging.getLogger(__name__)

_STOP_TIMEOUT_S = 20.0


class InterpreterUnavailable(RuntimeError):
    pass


def check_interpreter(interpreter: Path) -> None:
    """Se llama al arrancar el backend: el fallo se descubre ahí, no en el rodaje."""
    if not Path(interpreter).is_file():
        raise InterpreterUnavailable(
            f"intérprete para la rama OAK-D inexistente: {interpreter}. "
            "Definí EOVRT_CONSOLE_OAKD_PYTHON apuntando a un Python con depthai."
        )


class OakDSubprocessRecorder:
    def __init__(
        self, spec: RecordingSpec, out_path: Path, interpreter: Path, script: Path
    ) -> None:
        self._spec = spec
        self._path = out_path
        self._raw = out_path.with_suffix(".h264")
        self._interpreter = Path(interpreter)
        self._script = Path(script)
        self._proc: subprocess.Popen | None = None
        self._started_ms: int = 0
        self._started_monotonic: float = 0.0
        self._stderr: str = ""

    def start(self) -> None:
        capture = self._spec.capture
        assert capture is not None  # RecordingSpec lo garantiza para oak_d
        args = [
            str(self._interpreter), str(self._script),
            "--device", str(self._spec.config.get("url", "")),
            "--out", str(self._raw),
            "--fps", str(capture.fps),
            "--resolution", capture.resolution,
            "--bitrate", str(capture.bitrate_bps),
            "--keyframe-hz", str(capture.keyframe_hz),
        ]
        self._started_ms = int(time.time() * 1000)
        self._started_monotonic = time.monotonic()
        self._proc = subprocess.Popen(
            args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        logger.info("Grabación OAK-D arrancada -> %s", self._path.name)

    def poll(self) -> RecordingStatus:
        if self._proc is None:
            return RecordingStatus("error", 0, 0, "grabación sin arrancar")
        elapsed = int((time.monotonic() - self._started_monotonic) * 1000)
        size = self._raw.stat().st_size if self._raw.exists() else 0
        rc = self._proc.poll()
        if rc is None:
            return RecordingStatus("recording", elapsed, size)
        if rc == 0:
            return RecordingStatus("finished", elapsed, size)
        return RecordingStatus("error", elapsed, size, self._read_stderr() or f"record_oakd rc={rc}")

    def stop(self) -> RecordingResult:
        if self._proc is None:
            raise RuntimeError("no se puede detener una grabación sin arrancar")
        rc = self._proc.poll()
        murio_solo = rc is not None
        if not murio_solo:
            self._proc.send_signal(signal.SIGTERM)
            try:
                self._proc.wait(timeout=_STOP_TIMEOUT_S)
            except subprocess.TimeoutExpired:
                logger.warning("record_oakd no cerró en %ss, se mata", _STOP_TIMEOUT_S)
                self._proc.kill()
                self._proc.wait(timeout=5)
            rc = self._proc.returncode

        error = None
        if murio_solo or rc != 0:
            error = self._read_stderr() or f"record_oakd terminó con rc={rc}"
        truncated = murio_solo or rc != 0

        if self._raw.exists() and self._raw.stat().st_size > 0:
            mux_error = self._mux_to_mp4()
            if mux_error is not None:
                # Se conserva el .h264: nunca se borra material que no se pudo remuxear.
                truncated = True
                error = error or mux_error

        return RecordingResult(
            path=self._path,
            started_wallclock_ms=self._started_ms,
            duration_ms=int((time.monotonic() - self._started_monotonic) * 1000),
            size_bytes=self._path.stat().st_size if self._path.exists() else 0,
            truncated=truncated,
            error=error,
        )

    def _mux_to_mp4(self) -> str | None:
        capture = self._spec.capture
        fps = capture.fps if capture is not None else 60
        completed = subprocess.run(
            [
                "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
                "-f", "h264", "-r", str(fps), "-i", str(self._raw),
                "-c", "copy", str(self._path),
            ],
            capture_output=True, text=True,
        )
        if completed.returncode != 0:
            return f"muxeo a mp4 falló (rc={completed.returncode}): {completed.stderr.strip()}"
        self._raw.unlink(missing_ok=True)
        return None

    def _read_stderr(self) -> str:
        if self._stderr:
            return self._stderr
        if self._proc is not None and self._proc.stderr is not None:
            try:
                self._stderr = self._proc.stderr.read().strip()
            except (ValueError, OSError):
                self._stderr = ""
        return self._stderr
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd webconsole/backend && ./.venv/bin/python -m pytest tests/test_oakd_recorder.py -v`
Expected: PASS, 5 tests.

- [ ] **Step 5: Commit**

```bash
git add webconsole/backend/src/eovrt_webconsole/recording/oakd_recorder.py webconsole/backend/tests/test_oakd_recorder.py
git commit -m "feat(webconsole): rama OAK-D via subproceso con interprete depthai"
```

---

### Task 9: RecordingManager

**Files:**
- Create: `webconsole/backend/src/eovrt_webconsole/recording/manager.py`
- Test: `webconsole/backend/tests/test_recording_manager.py`

**Interfaces:**
- Consumes: todo lo anterior.
- Produces: `RecordingManager(raw_dir, oakd_interpreter, oakd_script, min_free_gb=5.0, clock=time.monotonic)` con:
  - `start(spec: RecordingSpec) -> dict` — reserva el archivo con `O_EXCL`, corre gates, arranca el recorder.
  - `status() -> dict` — `{state, basename, elapsed_ms, size_bytes, error}`; aplica el corte automático.
  - `stop() -> dict` — corta, mide, escribe el sidecar y devuelve el resumen.
  - `recover_orphans() -> list[str]` — al arrancar el backend.
  - Excepciones: `RecordingBusy`, `BasenameTaken`.

- [ ] **Step 1: Write the failing test**

Crear `webconsole/backend/tests/test_recording_manager.py`:

```python
import json
import shutil
import sys
import time
from pathlib import Path

import pytest

from eovrt_webconsole.recording.guards import GateError
from eovrt_webconsole.recording.manager import (
    BasenameTaken,
    RecordingBusy,
    RecordingManager,
)
from eovrt_webconsole.recording.types import RecordingSpec

SCRIPT_REAL = Path(__file__).resolve().parents[2] / "tools" / "record_oakd.py"

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="requiere ffmpeg y ffprobe en el sistema",
)


@pytest.fixture
def fuente(tmp_path):
    import subprocess

    out = tmp_path / "fuente.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
         "-f", "lavfi", "-i", "testsrc=size=320x240:rate=25:duration=20",
         "-c:v", "libx264", "-preset", "ultrafast", "-g", "25", str(out)],
        check=True,
    )
    return out


@pytest.fixture
def raw_dir(tmp_path):
    d = tmp_path / "raw"
    d.mkdir()
    return d


def _manager(raw_dir, **kwargs):
    return RecordingManager(
        raw_dir=raw_dir,
        oakd_interpreter=Path(sys.executable),
        oakd_script=SCRIPT_REAL,
        **kwargs,
    )


def _spec(fuente, basename="P1-a-take1", **kwargs):
    return RecordingSpec(
        plugin="rtsp", config={"url": f"file://{fuente}"}, basename=basename, **kwargs
    )


def test_start_stop_deja_master_y_sidecar(raw_dir, fuente):
    manager = _manager(raw_dir)
    manager.start(_spec(fuente))
    time.sleep(2.0)
    resumen = manager.stop()

    master = raw_dir / "P1-a-take1.mp4"
    sidecar = raw_dir / "P1-a-take1.rec.json"
    assert master.exists() and sidecar.exists()
    assert resumen["basename"] == "P1-a-take1"
    assert resumen["truncated"] is False
    data = json.loads(sidecar.read_text())
    assert data["measured"]["resolution"] == "320x240"
    assert data["sha256"]


def test_una_sola_grabacion_activa(raw_dir, fuente):
    manager = _manager(raw_dir)
    manager.start(_spec(fuente))
    try:
        with pytest.raises(RecordingBusy):
            manager.start(_spec(fuente, basename="P1-a-take2"))
    finally:
        manager.stop()


def test_basename_existente_se_rechaza(raw_dir, fuente):
    (raw_dir / "P1-a-take1.mp4").touch()
    manager = _manager(raw_dir)
    with pytest.raises(BasenameTaken):
        manager.start(_spec(fuente))


def test_espacio_insuficiente_se_rechaza_antes_de_grabar(raw_dir, fuente):
    manager = _manager(raw_dir, min_free_gb=10_000_000.0)
    with pytest.raises(GateError):
        manager.start(_spec(fuente))
    assert not (raw_dir / "P1-a-take1.mp4").exists()


def test_status_sin_grabacion_es_idle(raw_dir):
    assert _manager(raw_dir).status()["state"] == "idle"


def test_stop_sin_grabacion_es_error(raw_dir):
    with pytest.raises(RecordingBusy):
        _manager(raw_dir).stop()


def test_corte_automatico_por_max_duration(raw_dir, fuente):
    reloj = {"t": 0.0}
    manager = _manager(raw_dir, clock=lambda: reloj["t"])
    manager.start(_spec(fuente, max_duration_s=5))
    time.sleep(1.0)
    reloj["t"] = 6.0
    estado = manager.status()
    assert estado["state"] == "finished"
    assert estado["truncated"] is True
    assert (raw_dir / "P1-a-take1.mp4").exists()


def test_recover_orphans_muxea_y_marca(raw_dir):
    huerfana = raw_dir / "P9-a-take1.mp4"
    huerfana.write_bytes(b"\x00" * 32)
    recuperadas = _manager(raw_dir).recover_orphans()
    assert recuperadas == ["P9-a-take1"]
    data = json.loads((raw_dir / "P9-a-take1.rec.json").read_text())
    assert data["truncated"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd webconsole/backend && ./.venv/bin/python -m pytest tests/test_recording_manager.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'eovrt_webconsole.recording.manager'`.

- [ ] **Step 3: Write minimal implementation**

Crear `webconsole/backend/src/eovrt_webconsole/recording/manager.py`:

```python
"""Ciclo de vida de la grabación: una activa por consola, con corte de seguridad."""

from __future__ import annotations

import logging
import os
import threading
import time
from collections.abc import Callable
from pathlib import Path

from eovrt_webconsole.recording.ffmpeg_recorder import FfmpegCopyRecorder
from eovrt_webconsole.recording.guards import check_destination, check_free_space
from eovrt_webconsole.recording.naming import BASENAME_RE
from eovrt_webconsole.recording.oakd_recorder import OakDSubprocessRecorder
from eovrt_webconsole.recording.probe import ProbeError, measure
from eovrt_webconsole.recording.sidecar import write_sidecar
from eovrt_webconsole.recording.types import Recorder, RecordingResult, RecordingSpec

logger = logging.getLogger(__name__)


class RecordingBusy(RuntimeError):
    pass


class BasenameTaken(RuntimeError):
    pass


class RecordingManager:
    def __init__(
        self,
        raw_dir: Path,
        oakd_interpreter: Path,
        oakd_script: Path,
        min_free_gb: float = 5.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._raw_dir = Path(raw_dir)
        self._oakd_interpreter = Path(oakd_interpreter)
        self._oakd_script = Path(oakd_script)
        self._min_free_gb = min_free_gb
        self._clock = clock
        self._lock = threading.Lock()
        self._recorder: Recorder | None = None
        self._spec: RecordingSpec | None = None
        self._path: Path | None = None
        self._deadline: float | None = None
        self._last: dict | None = None

    # -- API pública -----------------------------------------------------

    def start(self, spec: RecordingSpec) -> dict:
        with self._lock:
            if self._recorder is not None:
                raise RecordingBusy(
                    f"ya hay una grabación activa: {self._spec.basename if self._spec else '?'}"
                )
            check_destination(self._raw_dir)
            check_free_space(self._raw_dir, self._min_free_gb)
            path = self._reserve(spec.basename)
            recorder = self._build_recorder(spec, path)
            recorder.start()
            self._recorder = recorder
            self._spec = spec
            self._path = path
            self._deadline = self._clock() + spec.max_duration_s
            self._last = None
        return self.status()

    def status(self) -> dict:
        with self._lock:
            if self._recorder is None:
                return self._last or {"state": "idle"}
            vencido = self._deadline is not None and self._clock() >= self._deadline
            estado = self._recorder.poll()
        if vencido:
            logger.warning("Corte automático por max_duration_s")
            return self.stop(truncar=True)
        return {
            "state": estado.state,
            "basename": self._spec.basename if self._spec else None,
            "elapsed_ms": estado.elapsed_ms,
            "size_bytes": estado.size_bytes,
            "error": estado.error,
        }

    def stop(self, truncar: bool = False) -> dict:
        with self._lock:
            if self._recorder is None:
                raise RecordingBusy("no hay ninguna grabación activa")
            recorder, spec = self._recorder, self._spec
            self._recorder = self._spec = self._path = self._deadline = None
        result = recorder.stop()
        if truncar:
            result = RecordingResult(
                path=result.path,
                started_wallclock_ms=result.started_wallclock_ms,
                duration_ms=result.duration_ms,
                size_bytes=result.size_bytes,
                truncated=True,
                error=result.error or "corte automático por max_duration_s",
            )
        resumen = self._finalize(spec, result)
        with self._lock:
            self._last = resumen
        return resumen

    def recover_orphans(self) -> list[str]:
        """Masters sin sidecar = el backend cayó grabando. Se cierran y se marcan."""
        if not self._raw_dir.is_dir():
            return []
        recuperadas: list[str] = []
        for master in sorted(self._raw_dir.glob("*.mp4")):
            basename = master.stem
            if not BASENAME_RE.match(basename):
                continue  # material ajeno (lote de internet), no se toca
            if master.with_suffix(".rec.json").exists():
                continue
            spec = RecordingSpec(
                plugin="rtsp", config={}, basename=basename
            )
            result = RecordingResult(
                path=master,
                started_wallclock_ms=int(master.stat().st_mtime * 1000),
                duration_ms=0,
                size_bytes=master.stat().st_size,
                truncated=True,
                error="grabación huérfana: el backend cayó durante la toma",
            )
            self._finalize(spec, result)
            recuperadas.append(basename)
            logger.warning("Grabación huérfana recuperada: %s", basename)
        return recuperadas

    # -- Internos --------------------------------------------------------

    def _reserve(self, basename: str) -> Path:
        """Reserva atómica: O_EXCL falla si el archivo ya existe. Nunca se pisa una toma."""
        path = self._raw_dir / f"{basename}.mp4"
        try:
            handle = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError as exc:
            raise BasenameTaken(f"ya existe una toma con ese nombre: {basename}") from exc
        os.close(handle)
        return path

    def _build_recorder(self, spec: RecordingSpec, path: Path) -> Recorder:
        if spec.plugin == "oak_d":
            return OakDSubprocessRecorder(
                spec, path, interpreter=self._oakd_interpreter, script=self._oakd_script
            )
        return FfmpegCopyRecorder(spec, path)

    def _finalize(self, spec: RecordingSpec | None, result: RecordingResult) -> dict:
        assert spec is not None
        try:
            measured = measure(result.path)
        except ProbeError as exc:
            logger.warning("No se pudo medir %s: %s", result.path.name, exc)
            measured = None
        sidecar = write_sidecar(spec, result, measured)
        # El substream de un DVR pasa desapercibido si nadie lo mira: se marca.
        substream = measured is not None and measured.width < 1280
        return {
            "state": "finished",
            "basename": spec.basename,
            "file": str(result.path),
            "sidecar": str(sidecar),
            "duration_ms": measured.duration_ms if measured else result.duration_ms,
            "size_bytes": result.size_bytes,
            "fps": measured.fps if measured else None,
            "resolution": f"{measured.width}x{measured.height}" if measured else None,
            "truncated": result.truncated,
            "suspected_substream": substream,
            "error": result.error,
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd webconsole/backend && ./.venv/bin/python -m pytest tests/test_recording_manager.py -v`
Expected: PASS, 8 tests.

- [ ] **Step 5: Commit**

```bash
git add webconsole/backend/src/eovrt_webconsole/recording/manager.py webconsole/backend/tests/test_recording_manager.py
git commit -m "feat(webconsole): RecordingManager con reserva atomica y corte de seguridad"
```

---

### Task 10: Exclusión mutua contra el media-plane

**Files:**
- Create: `webconsole/backend/src/eovrt_webconsole/recording/occupancy.py`
- Test: `webconsole/backend/tests/test_recording_occupancy.py`

**Interfaces:**
- Consumes: `RunBackend` (`app.state.backend`) para consultar preview y runs.
- Produces: `async check_media_plane_free(backend) -> str | None`. Devuelve `None` si el media-plane está libre; el id del ocupante (`"preview:pv_ab12"` / `"run:r_991"`) si está ocupado; y `None` **con warning logueado** si el media-plane no responde — un plano de inferencia caído no puede costar tomas.

- [ ] **Step 1: Write the failing test**

Crear `webconsole/backend/tests/test_recording_occupancy.py`:

```python
import pytest

from eovrt_webconsole.recording.occupancy import check_media_plane_free
from eovrt_webconsole.run_backend import ServiceUnavailable


class _Backend:
    def __init__(self, preview=None, runs=None, falla=False):
        self._preview = preview or {"status": "idle", "preview_id": None}
        self._runs = runs or []
        self._falla = falla

    async def preview_status(self):
        if self._falla:
            raise ServiceUnavailable("media-plane caído")
        return self._preview

    async def list_runs(self):
        if self._falla:
            raise ServiceUnavailable("media-plane caído")
        return self._runs


@pytest.mark.asyncio
async def test_media_plane_libre():
    assert await check_media_plane_free(_Backend()) is None


@pytest.mark.asyncio
async def test_preview_activo_ocupa():
    backend = _Backend(preview={"status": "streaming", "preview_id": "pv_ab12"})
    assert await check_media_plane_free(backend) == "preview:pv_ab12"


@pytest.mark.asyncio
async def test_run_activo_ocupa():
    backend = _Backend(runs=[{"run_id": "r_991", "status": "running"}])
    assert await check_media_plane_free(backend) == "run:r_991"


@pytest.mark.asyncio
async def test_run_terminado_no_ocupa():
    backend = _Backend(runs=[{"run_id": "r_990", "status": "finished"}])
    assert await check_media_plane_free(backend) is None


@pytest.mark.asyncio
async def test_media_plane_caido_no_bloquea(caplog):
    assert await check_media_plane_free(_Backend(falla=True)) is None
    assert "media-plane" in caplog.text.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd webconsole/backend && ./.venv/bin/python -m pytest tests/test_recording_occupancy.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'eovrt_webconsole.recording.occupancy'`.

- [ ] **Step 3: Write minimal implementation**

Crear `webconsole/backend/src/eovrt_webconsole/recording/occupancy.py`:

```python
"""Chequeo de ocupación del media-plane antes de grabar (doble toma, doc 59 §7)."""

from __future__ import annotations

import logging

from eovrt_webconsole.run_backend import ServiceUnavailable

logger = logging.getLogger(__name__)

_RUN_ACTIVO = {"running", "starting", "pending"}


async def check_media_plane_free(backend) -> str | None:
    """None = libre. Un id de ocupante = ocupado. Media-plane caído = libre + warning.

    Grabar no necesita el media-plane: si está caído, el chequeo se degrada a
    advertencia en vez de costar una toma. La exclusividad física de la OAK-D es
    el backstop real si alguien saltea la consola.
    """
    try:
        preview = await backend.preview_status()
        if preview.get("status") == "streaming":
            return f"preview:{preview.get('preview_id')}"
        for run in await backend.list_runs():
            if str(run.get("status")) in _RUN_ACTIVO:
                return f"run:{run.get('run_id')}"
    except ServiceUnavailable as exc:
        logger.warning(
            "No se pudo consultar el media-plane (%s): se graba igual, sin chequeo "
            "de doble toma",
            exc,
        )
        return None
    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd webconsole/backend && ./.venv/bin/python -m pytest tests/test_recording_occupancy.py -v`
Expected: PASS, 5 tests.

**Si falla** con `AttributeError: 'RunBackend' object has no attribute 'list_runs'`, abrir `src/eovrt_webconsole/run_backend.py`, buscar el método real que lista corridas y ajustar tanto `occupancy.py` como el doble del test para usar ese nombre.

- [ ] **Step 5: Commit**

```bash
git add webconsole/backend/src/eovrt_webconsole/recording/occupancy.py webconsole/backend/tests/test_recording_occupancy.py
git commit -m "feat(webconsole): chequeo de ocupacion del media-plane antes de grabar"
```

---

### Task 11: Router REST y wiring

**Files:**
- Create: `webconsole/backend/src/eovrt_webconsole/routers/recordings.py`
- Modify: `webconsole/backend/src/eovrt_webconsole/app.py`
- Test: `webconsole/backend/tests/test_recordings_router.py`

**Interfaces:**
- Consumes: `RecordingManager`, `check_media_plane_free`, `next_basename`, `check_interpreter`.
- Produces:
  - `GET /api/recordings/next?scenario=P1&variant=a` → `{"basename": "P1-a-take2"}`
  - `POST /api/recordings` (201) → resumen de estado. Body: `{camera_id, scenario, variant, max_duration_s?}` **o** `{plugin, config, basename, ...}`.
  - `GET /api/recordings` → estado actual.
  - `DELETE /api/recordings` (200) → resumen final.
  - `app.state.recording_manager` disponible tras el lifespan.

- [ ] **Step 1: Write the failing test**

Crear `webconsole/backend/tests/test_recordings_router.py`:

```python
import shutil
import subprocess
import time
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from eovrt_webconsole.app import create_app
from eovrt_webconsole.settings import ConsoleSettings
from tests.fake_service import FakeState, make_fake_service

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="requiere ffmpeg y ffprobe en el sistema",
)


@pytest.fixture
def fuente(tmp_path):
    out = tmp_path / "fuente.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
         "-f", "lavfi", "-i", "testsrc=size=320x240:rate=25:duration=20",
         "-c:v", "libx264", "-preset", "ultrafast", "-g", "25", str(out)],
        check=True,
    )
    return out


@pytest.fixture
def rec_client(repo: Path, tmp_path: Path, fake_state: FakeState, fuente):
    raw = tmp_path / "raw"
    raw.mkdir()
    (repo / "cameras").mkdir(exist_ok=True)
    (repo / "cameras" / "dvr_test.yaml").write_text(
        "camera:\n"
        "  id: dvr_test\n"
        "  name: DVR de prueba\n"
        "  plugin: rtsp\n"
        f"  config: {{ url: 'file://{fuente}' }}\n"
    )
    settings = ConsoleSettings(
        service_url="http://service.fake",
        repo_root=repo,
        frozen_set_ids=frozenset(),
        recordings_dir=raw,
    )
    transport = httpx.ASGITransport(app=make_fake_service(fake_state))
    with TestClient(create_app(settings, service_transport=transport)) as client:
        client.raw_dir = raw
        yield client


def test_next_propone_el_primer_take(rec_client):
    body = rec_client.get("/api/recordings/next?scenario=P1&variant=a").json()
    assert body["basename"] == "P1-a-take1"


def test_next_rechaza_escenario_invalido(rec_client):
    assert rec_client.get("/api/recordings/next?scenario=P0&variant=a").status_code == 422


def test_estado_inicial_es_idle(rec_client):
    assert rec_client.get("/api/recordings").json()["state"] == "idle"


def test_ciclo_completo_por_camera_id(rec_client):
    creado = rec_client.post(
        "/api/recordings", json={"camera_id": "dvr_test", "scenario": "P1", "variant": "a"}
    )
    assert creado.status_code == 201
    assert creado.json()["basename"] == "P1-a-take1"

    time.sleep(2.0)
    assert rec_client.get("/api/recordings").json()["state"] == "recording"

    final = rec_client.delete("/api/recordings")
    assert final.status_code == 200
    assert final.json()["truncated"] is False
    assert (rec_client.raw_dir / "P1-a-take1.mp4").exists()
    assert (rec_client.raw_dir / "P1-a-take1.rec.json").exists()


def test_segunda_grabacion_da_409(rec_client):
    rec_client.post(
        "/api/recordings", json={"camera_id": "dvr_test", "scenario": "P1", "variant": "a"}
    )
    try:
        conflicto = rec_client.post(
            "/api/recordings", json={"camera_id": "dvr_test", "scenario": "P1", "variant": "b"}
        )
        assert conflicto.status_code == 409
    finally:
        rec_client.delete("/api/recordings")


def test_camera_inexistente_da_404(rec_client):
    respuesta = rec_client.post(
        "/api/recordings", json={"camera_id": "no-existe", "scenario": "P1", "variant": "a"}
    )
    assert respuesta.status_code == 404


def test_preview_activo_en_el_media_plane_da_409(rec_client, fake_state):
    fake_state.preview = {"status": "streaming", "preview_id": "pv_ab12", "mode": "raw"}
    respuesta = rec_client.post(
        "/api/recordings", json={"camera_id": "dvr_test", "scenario": "P1", "variant": "a"}
    )
    assert respuesta.status_code == 409
    assert "preview" in respuesta.json()["detail"]


def test_delete_sin_grabacion_da_409(rec_client):
    assert rec_client.delete("/api/recordings").status_code == 409
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd webconsole/backend && ./.venv/bin/python -m pytest tests/test_recordings_router.py -v`
Expected: FAIL — 404 en todas las rutas `/api/recordings` (el router no existe).

**Si falla** en el fixture con `AttributeError: 'FakeState' object has no attribute 'preview'`, abrir `tests/fake_service.py`, ver cómo modela el estado del preview y ajustar el test para usar ese atributo.

- [ ] **Step 3: Write minimal implementation**

Crear `webconsole/backend/src/eovrt_webconsole/routers/recordings.py`:

```python
"""Grabación de tomas de rodaje: una activa por consola (spec 2026-07-21)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from eovrt_webconsole import camera_store as cs
from eovrt_webconsole.recording.guards import GateError
from eovrt_webconsole.recording.manager import BasenameTaken, RecordingBusy
from eovrt_webconsole.recording.naming import InvalidTakeId, next_basename
from eovrt_webconsole.recording.occupancy import check_media_plane_free
from eovrt_webconsole.recording.types import RecordingSpec

router = APIRouter(prefix="/api/recordings")


def _manager(request: Request):
    return request.app.state.recording_manager


@router.get("/next")
def next_take(request: Request, scenario: str, variant: str) -> dict:
    try:
        basename = next_basename(
            request.app.state.settings.raw_dir, scenario, variant
        )
    except InvalidTakeId as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"basename": basename}


@router.get("")
def recording_status(request: Request) -> dict:
    return _manager(request).status()


@router.post("", status_code=201)
async def start_recording(request: Request, payload: dict) -> dict:
    settings = request.app.state.settings
    body = dict(payload)

    camera_id = body.pop("camera_id", None)
    if camera_id is not None:
        try:
            preset = cs.get_camera(settings.cameras_dir, camera_id)
        except cs.CameraNotFound as exc:
            raise HTTPException(status_code=404, detail=f"cámara desconocida: {camera_id}") from exc
        body.setdefault("plugin", preset.get("plugin"))
        body.setdefault("config", preset.get("config", {}))
        body.setdefault("label", camera_id)

    scenario = body.pop("scenario", None)
    variant = body.pop("variant", None)
    if scenario is not None and variant is not None:
        try:
            body["basename"] = next_basename(settings.raw_dir, scenario, variant)
        except InvalidTakeId as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        spec = RecordingSpec(**body)
    except Exception as exc:  # noqa: BLE001 - ValidationError de pydantic y kwargs sobrantes
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    ocupante = await check_media_plane_free(request.app.state.backend)
    if ocupante is not None:
        raise HTTPException(
            status_code=409,
            detail=f"el media-plane está ocupado por {ocupante}: grabar y correr son secuenciales",
        )

    try:
        return _manager(request).start(spec)
    except RecordingBusy as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except BasenameTaken as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except GateError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete("")
def stop_recording(request: Request) -> dict:
    try:
        return _manager(request).stop()
    except RecordingBusy as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
```

En `app.py`, agregar el import del router a la lista existente (orden alfabético: entre `prompts` y `runs`):

```python
    prompts,
    recordings,
    runs,
```

Agregar al bloque de imports de arriba:

```python
from eovrt_webconsole.recording.manager import RecordingManager
from eovrt_webconsole.recording.oakd_recorder import InterpreterUnavailable, check_interpreter
```

Dentro de `_lifespan`, después de crear `app.state.experiment_manager`:

```python
        # Grabación de rodaje: vive en la consola, no depende del media-plane
        # (spec 2026-07-21). El chequeo del intérprete se hace acá y no al
        # apretar grabar: el fallo se descubre ahora, no en medio del rodaje.
        oakd_script = settings.repo_root / "webconsole" / "tools" / "record_oakd.py"
        app.state.recording_manager = RecordingManager(
            raw_dir=settings.raw_dir,
            oakd_interpreter=settings.oakd_interpreter,
            oakd_script=oakd_script,
        )
        try:
            check_interpreter(settings.oakd_interpreter)
        except InterpreterUnavailable as exc:
            logging.getLogger(__name__).warning("Rama OAK-D no disponible: %s", exc)
        for basename in app.state.recording_manager.recover_orphans():
            logging.getLogger(__name__).warning("Grabación huérfana cerrada: %s", basename)
```

Agregar `import logging` arriba del todo en `app.py` si no está.

Y registrar el router junto a los demás:

```python
    app.include_router(recordings.router)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd webconsole/backend && ./.venv/bin/python -m pytest tests/test_recordings_router.py -v && ./.venv/bin/python -m pytest tests -q && ./.venv/bin/python -m ruff check src tests`
Expected: los 8 tests del router en PASS, la suite completa en PASS y ruff sin hallazgos.

- [ ] **Step 5: Commit**

```bash
git add webconsole/backend/src/eovrt_webconsole/routers/recordings.py webconsole/backend/src/eovrt_webconsole/app.py webconsole/backend/tests/test_recordings_router.py
git commit -m "feat(webconsole): API REST de grabacion de rodaje"
```

---

### Task 12: Panel de grabación en la ventana Cámaras

**Files:**
- Create: `webconsole/frontend/src/components/RecordPanel.tsx`
- Modify: `webconsole/frontend/src/api.ts`
- Modify: `webconsole/frontend/src/types.ts`
- Modify: `webconsole/frontend/src/pages/CamerasPage.tsx`
- Test: `webconsole/frontend/src/__tests__/RecordPanel.test.tsx`

**Interfaces:**
- Consumes: los endpoints de la Task 11.
- Produces: componente `<RecordPanel cameraId={string | null} />`.

**Nota para quien implemente:** la marca de los 30 s no es decorativa — es la regla de oro 3 de doc 59 (se filma 30–35 s aunque el clip final sea de 20 s, porque el recorte fino se hace después). Antes de los 30 s el cronómetro va en ámbar; a partir de ahí, en verde.

- [ ] **Step 1: Write the failing test**

Crear `webconsole/frontend/src/__tests__/RecordPanel.test.tsx`:

**Convenciones de test del frontend de este repo (no negociables):** no hay
`jest-dom` — se usa `toBeTruthy()`, nunca `toBeInTheDocument()`/`toBeDisabled()`.
`afterEach(() => cleanup())` explícito. `fireEvent`, nunca `userEvent`.

```tsx
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import RecordPanel from '../components/RecordPanel'
import * as api from '../api'

describe('RecordPanel', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(api, 'nextTake').mockResolvedValue({ basename: 'P1-a-take3' })
    vi.spyOn(api, 'getRecording').mockResolvedValue({ state: 'idle' })
  })

  afterEach(() => cleanup())

  it('muestra el proximo basename propuesto', async () => {
    render(<RecordPanel cameraId="dvr_test" />)
    expect(await screen.findByText(/P1-a-take3/)).toBeTruthy()
  })

  it('deshabilita grabar si no hay camara elegida', async () => {
    render(<RecordPanel cameraId={null} />)
    const boton = await screen.findByRole('button', { name: /grabar/i })
    expect((boton as HTMLButtonElement).disabled).toBe(true)
  })

  it('arranca la grabacion con la camara, escenario y variante elegidos', async () => {
    const start = vi
      .spyOn(api, 'startRecording')
      .mockResolvedValue({ state: 'recording', basename: 'P1-a-take3', elapsed_ms: 0, size_bytes: 0 })
    render(<RecordPanel cameraId="dvr_test" />)
    expect(await screen.findByText(/P1-a-take3/)).toBeTruthy()

    fireEvent.change(screen.getByLabelText(/escenario/i), { target: { value: 'P2' } })
    fireEvent.click(screen.getByRole('button', { name: /grabar/i }))

    await waitFor(() =>
      expect(start).toHaveBeenCalledWith({
        camera_id: 'dvr_test',
        scenario: 'P2',
        variant: 'a',
      }),
    )
  })

  it('muestra el error del backend sin romper el panel', async () => {
    vi.spyOn(api, 'startRecording').mockRejectedValue(
      new Error('el media-plane está ocupado por preview:pv_ab12'),
    )
    render(<RecordPanel cameraId="dvr_test" />)
    expect(await screen.findByText(/P1-a-take3/)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /grabar/i }))
    expect(await screen.findByText(/ocupado por preview/)).toBeTruthy()
    expect(screen.getByRole('button', { name: /grabar/i })).toBeTruthy()
  })

  it('avisa cuando la toma se corto antes de los 30 s', async () => {
    vi.spyOn(api, 'startRecording').mockResolvedValue({
      state: 'recording', basename: 'P1-a-take3', elapsed_ms: 0, size_bytes: 0,
    })
    vi.spyOn(api, 'stopRecording').mockResolvedValue({
      state: 'finished', basename: 'P1-a-take3', duration_ms: 12000,
      size_bytes: 1024, truncated: false, suspected_substream: false,
      fps: 25, resolution: '320x240', error: null,
    })
    render(<RecordPanel cameraId="dvr_test" />)
    expect(await screen.findByText(/P1-a-take3/)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /grabar/i }))
    expect(await screen.findByRole('button', { name: /detener/i })).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /detener/i }))
    expect(await screen.findByText(/menos de 30 s/i)).toBeTruthy()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd webconsole/frontend && npm test -- RecordPanel`
Expected: FAIL con `Failed to resolve import "../components/RecordPanel"`.

- [ ] **Step 3: Write minimal implementation**

En `types.ts`, agregar:

```ts
export interface RecordingStatus {
  state: 'idle' | 'recording' | 'finished' | 'error'
  basename?: string | null
  elapsed_ms?: number
  size_bytes?: number
  duration_ms?: number
  fps?: number | null
  resolution?: string | null
  truncated?: boolean
  suspected_substream?: boolean
  error?: string | null
}

export interface StartRecordingBody {
  camera_id: string
  scenario: string
  variant: string
  max_duration_s?: number
}
```

En `api.ts`, agregar `RecordingStatus` y `StartRecordingBody` al import de `./types` y al final del archivo:

```ts
export const nextTake = (scenario: string, variant: string) =>
  request<{ basename: string }>(
    `/api/recordings/next?scenario=${encodeURIComponent(scenario)}&variant=${encodeURIComponent(variant)}`,
  )
export const getRecording = () => request<RecordingStatus>('/api/recordings')
export const startRecording = (body: StartRecordingBody) =>
  request<RecordingStatus>('/api/recordings', { method: 'POST', body: JSON.stringify(body) })
export const stopRecording = () =>
  request<RecordingStatus>('/api/recordings', { method: 'DELETE' })
```

Crear `webconsole/frontend/src/components/RecordPanel.tsx`:

```tsx
import { useCallback, useEffect, useRef, useState } from 'react'

import { getRecording, nextTake, startRecording, stopRecording } from '../api'
import type { RecordingStatus } from '../types'

const SCENARIOS = ['P1', 'P2', 'P3', 'P5', 'P9']
const VARIANTS = ['a', 'b', 'c']
// Regla de oro 3 de doc 59: se filma 30-35 s aunque el clip final sea de 20 s,
// porque el re-ventaneo con onset en t~3-4 s se hace despues.
const MIN_TAKE_MS = 30_000

export default function RecordPanel({ cameraId }: { cameraId: string | null }) {
  const [scenario, setScenario] = useState('P1')
  const [variant, setVariant] = useState('a')
  const [basename, setBasename] = useState<string | null>(null)
  const [status, setStatus] = useState<RecordingStatus>({ state: 'idle' })
  const [error, setError] = useState<string | null>(null)
  const [last, setLast] = useState<RecordingStatus | null>(null)
  const [elapsed, setElapsed] = useState(0)
  const startedAt = useRef<number>(0)

  useEffect(() => {
    nextTake(scenario, variant)
      .then((r) => setBasename(r.basename))
      .catch((e: Error) => setError(e.message))
  }, [scenario, variant])

  useEffect(() => {
    getRecording()
      .then(setStatus)
      .catch(() => undefined)
  }, [])

  useEffect(() => {
    if (status.state !== 'recording') return
    const id = window.setInterval(() => setElapsed(Date.now() - startedAt.current), 200)
    return () => window.clearInterval(id)
  }, [status.state])

  const onStart = useCallback(async () => {
    if (!cameraId) return
    setError(null)
    setLast(null)
    try {
      startedAt.current = Date.now()
      setElapsed(0)
      setStatus(await startRecording({ camera_id: cameraId, scenario, variant }))
    } catch (e) {
      setError((e as Error).message)
      setStatus({ state: 'idle' })
    }
  }, [cameraId, scenario, variant])

  const onStop = useCallback(async () => {
    setError(null)
    try {
      const final = await stopRecording()
      setLast(final)
      setStatus({ state: 'idle' })
      const r = await nextTake(scenario, variant)
      setBasename(r.basename)
    } catch (e) {
      setError((e as Error).message)
    }
  }, [scenario, variant])

  const recording = status.state === 'recording'
  const seconds = Math.floor(elapsed / 1000)

  return (
    <section className="record-panel">
      <h3>Grabar toma</h3>

      <label htmlFor="rec-scenario">Escenario</label>
      <select
        id="rec-scenario"
        value={scenario}
        disabled={recording}
        onChange={(e) => setScenario(e.target.value)}
      >
        {SCENARIOS.map((s) => (
          <option key={s} value={s}>{s}</option>
        ))}
      </select>

      <label htmlFor="rec-variant">Variante</label>
      <select
        id="rec-variant"
        value={variant}
        disabled={recording}
        onChange={(e) => setVariant(e.target.value)}
      >
        {VARIANTS.map((v) => (
          <option key={v} value={v}>{v}</option>
        ))}
      </select>

      <p className="record-basename">Próxima toma: <strong>{basename ?? '—'}</strong></p>

      {recording ? (
        <>
          <p className={elapsed >= MIN_TAKE_MS ? 'rec-ok' : 'rec-corta'}>
            ● REC {seconds}s {elapsed >= MIN_TAKE_MS ? '' : '(no cortar antes de 30 s)'}
          </p>
          <button type="button" onClick={onStop}>Detener</button>
        </>
      ) : (
        <button type="button" onClick={onStart} disabled={!cameraId}>
          Grabar
        </button>
      )}

      {error && <p className="record-error">{error}</p>}

      {last && (
        <div className="record-summary">
          <p>
            {last.basename}: {Math.round((last.duration_ms ?? 0) / 1000)}s, {last.resolution ?? '?'},{' '}
            {last.fps ? `${last.fps.toFixed(2)} fps` : 'fps desconocido'}
          </p>
          {(last.duration_ms ?? 0) < MIN_TAKE_MS && (
            <p className="rec-corta">Toma de menos de 30 s: revisá si sirve (regla de oro 3).</p>
          )}
          {last.truncated && <p className="record-error">Toma truncada: {last.error}</p>}
          {last.suspected_substream && (
            <p className="record-error">
              Resolución baja: puede que el preset apunte al substream del DVR.
            </p>
          )}
        </div>
      )}
    </section>
  )
}
```

En `pages/CamerasPage.tsx`, importar el panel y montarlo junto al preview. Agregar arriba:

```tsx
import RecordPanel from '../components/RecordPanel'
```

Y renderizarlo debajo del bloque del player, pasándole el id de la cámara seleccionada (el estado que la página ya usa para arrancar el preview; si se llama distinto, usar ese nombre):

```tsx
      <RecordPanel cameraId={selectedId} />
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd webconsole/frontend && npm test -- RecordPanel && npm test`
Expected: los 5 tests de `RecordPanel` en PASS y la suite completa del frontend sin regresiones.

- [ ] **Step 5: Commit**

```bash
git add webconsole/frontend/src/components/RecordPanel.tsx webconsole/frontend/src/api.ts webconsole/frontend/src/types.ts webconsole/frontend/src/pages/CamerasPage.tsx webconsole/frontend/src/__tests__/RecordPanel.test.tsx
git commit -m "feat(webconsole): panel de grabacion de tomas en la ventana Camaras"
```

---

### Task 13: Verificación de punta a punta contra el pipeline real

**Files:**
- Create: `webconsole/backend/tests/test_recording_pipeline_e2e.py`

**Interfaces:**
- Consumes: `RecordingManager` y `prepare_clip.sh` del repo `e-ovrt_datasets`.
- Produces: nada nuevo. Es el criterio de aceptación del spec §8.

**Por qué existe esta tarea:** todo lo anterior puede pasar y la herramienta no servir igual. Lo único que importa es que `prepare_clip.sh` consuma un master grabado y emita un `info.json` con `n_frames` coherente. Este test lo comprueba.

- [ ] **Step 1: Write the failing test**

Crear `webconsole/backend/tests/test_recording_pipeline_e2e.py`:

```python
"""Criterio de aceptación del spec §8: el master grabado entra a la etapa 0."""

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

from eovrt_webconsole.recording.manager import RecordingManager
from eovrt_webconsole.recording.types import RecordingSpec

PREPARE_CLIP = (
    Path(__file__).resolve().parents[4]
    / "e-ovrt_datasets" / "datasets" / "scripts" / "videogt" / "prepare_clip.sh"
)

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None
    or shutil.which("ffprobe") is None
    or not PREPARE_CLIP.is_file(),
    reason="requiere ffmpeg/ffprobe y el repo e-ovrt_datasets como hermano",
)


def test_el_master_grabado_pasa_por_prepare_clip(tmp_path):
    fuente = tmp_path / "fuente.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
         "-f", "lavfi", "-i", "testsrc=size=640x480:rate=30:duration=15",
         "-c:v", "libx264", "-preset", "ultrafast", "-g", "30", str(fuente)],
        check=True,
    )
    raw = tmp_path / "raw"
    raw.mkdir()

    manager = RecordingManager(
        raw_dir=raw,
        oakd_interpreter=Path(sys.executable),
        oakd_script=Path(__file__).resolve().parents[2] / "tools" / "record_oakd.py",
    )
    manager.start(
        RecordingSpec(
            plugin="rtsp", config={"url": f"file://{fuente}"}, basename="P1-a-take1"
        )
    )
    time.sleep(6.0)
    resumen = manager.stop()
    assert resumen["truncated"] is False

    # Etapa 0 real, con el script del repo de datasets sin modificar.
    salida = tmp_path / "clips"
    subprocess.run(
        ["bash", str(PREPARE_CLIP), str(raw / "P1-a-take1.mp4"), "v99_c01",
         "--ss", "1", "--to", "4", "--fps", "30"],
        check=True,
        cwd=tmp_path,
        env={"PATH": "/usr/bin:/bin:/usr/local/bin", "HOME": str(tmp_path)},
    )

    # prepare_clip.sh escribe en <repo>/datasets-videos/clips; se localiza el info.json.
    infos = list(PREPARE_CLIP.parents[3].glob("datasets-videos/clips/v99_c01.info.json"))
    assert infos, "prepare_clip.sh no emitió el info.json"
    info = json.loads(infos[0].read_text())
    try:
        assert info["fps"] == 30
        assert info["n_frames"] == pytest.approx(90, abs=3)
        assert info["duration_ms"] == pytest.approx(3000, abs=150)
    finally:
        infos[0].unlink(missing_ok=True)
        (infos[0].parent / "v99_c01.mp4").unlink(missing_ok=True)
```

- [ ] **Step 2: Run test to verify it fails or is skipped**

Run: `cd webconsole/backend && ./.venv/bin/python -m pytest tests/test_recording_pipeline_e2e.py -v`
Expected: PASS si el repo `e-ovrt_datasets` está como hermano y hay ffmpeg; SKIPPED si no. **Si sale FAIL**, la causa más probable es que `prepare_clip.sh` escriba en una ruta distinta a la asumida — verificar `OUT_DIR` en el script y ajustar el glob del test, no el script (el repo de datasets no se toca).

- [ ] **Step 3: Ajustar si el test revela un problema real**

Si el `info.json` sale con `n_frames` incoherente, el problema está en el master (por ejemplo, un mp4 sin `moov` bien cerrado). Revisar el corte con `SIGINT` de `FfmpegCopyRecorder` (Task 6) antes de tocar cualquier otra cosa.

- [ ] **Step 4: Correr la suite completa**

Run: `cd webconsole/backend && ./.venv/bin/python -m pytest tests -q && ./.venv/bin/python -m ruff check src tests`
Expected: todo en PASS, ruff sin hallazgos.

- [ ] **Step 5: Commit**

```bash
git add webconsole/backend/tests/test_recording_pipeline_e2e.py
git commit -m "test(webconsole): el master grabado entra a la etapa 0 del video-gt-lab"
```

---

### Task 14: Documentación operativa

**Files:**
- Create: `webconsole/tools/README.md`
- Modify: `docs/operacion/59-guion-grabacion-bloque-a.md` (repo `docs`, **otro repositorio git**)

**Interfaces:** ninguna. Cierra el spec §9.

**Atención:** `docs/` es un repo git propio. Hay que `cd` a él para commitear, y solo si el usuario lo pide.

- [ ] **Step 1: Escribir el README del script standalone**

Crear `webconsole/tools/README.md`:

```markdown
# Herramientas standalone del webconsole

## `record_oakd.py`

Graba la OAK-D a H.264 crudo con el encoder por hardware del dispositivo. Lo
invoca la consola (`POST /api/recordings` con una cámara `oak_d`), pero es
**standalone a propósito**: corre a mano desde una terminal y es el plan B si la
consola falla en obra.

Requiere un intérprete con el SDK DepthAI. El backend de la consola corre Python
3.14 y `depthai` no publica wheels para 3.14, así que se usa otro intérprete —
por default el venv del media-plane:

```bash
../../e-ovrt_media-plane/.venv/bin/python tools/record_oakd.py \
    --device 192.168.1.50 \
    --out /tmp/toma.h264 \
    --fps 60 --resolution 1080p --bitrate 25000000
# cortar con Ctrl-C; despues muxear a mp4:
ffmpeg -f h264 -r 60 -i /tmp/toma.h264 -c copy /tmp/toma.mp4
```

Se puede apuntar a otro intérprete con `EOVRT_CONSOLE_OAKD_PYTHON`.

Códigos de salida: `0` ok, `2` argumentos inválidos, `3` SDK ausente, `4` fallo
del dispositivo.
```

- [ ] **Step 2: Agregar la verificación de grabación al dry-run de doc 59**

En `docs/operacion/59-guion-grabacion-bloque-a.md`, sección §7, dentro del bloque
**"El día ANTES (dry-run obligatorio)"**, agregar estos ítems después del que
verifica el encuadre en la ventana Cámaras:

```markdown
- [ ] **Grabación verificada con las dos cámaras**: una toma de 60 s con la RTSP y
      otra con la OAK-D desde la ventana Cámaras. Chequear en el sidecar
      `.rec.json`: `measured.fps` cercano al pedido, `measured.resolution` la
      esperada (si sale < 1280 de ancho, el preset apunta al substream del DVR),
      `truncated: false`.
- [ ] **Etapa 0 sobre un master grabado**: `prepare_clip.sh` sobre la toma de
      prueba emite un `info.json` con `n_frames` coherente. Si esto no cierra, el
      material del rodaje no entra al banco.
- [ ] **Espacio en disco**: ≥ 5 GB libres (la consola lo exige) y destino en el
      filesystem nativo de WSL, nunca bajo `/mnt/c`.
```

- [ ] **Step 3: Verificar que no se rompió nada**

Run: `cd webconsole/backend && ./.venv/bin/python -m pytest tests -q`
Expected: PASS.

- [ ] **Step 4: Commit (dos repos separados)**

```bash
git add webconsole/tools/README.md
git commit -m "docs(webconsole): uso standalone de record_oakd.py"

cd ../docs && git add operacion/59-guion-grabacion-bloque-a.md
git commit -m "docs: verificacion de grabacion en el dry-run del rodaje"
```
