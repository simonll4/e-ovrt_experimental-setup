# Generación de clips desde la consola — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Desde la ventana Clips de la consola, abrir un master de `raw/`, marcar el evento y su fin sobre el video, y que la consola corra `prepare_clip.sh` y escriba el `.clip.yaml` sin pedir un solo campo.

**Architecture:** Todo vive en el webconsole (`e-ovrt_experimental-setup`). Backend: paquete nuevo `eovrt_webconsole/clips/` con unidades chicas (ventana pura, nombrado, inventario, invocación del script, escritura del YAML, orquestación) + router `routers/clips.py` que sirve video con HTTP Range vía `FileResponse` de Starlette (1.3.1 soporta Range nativo). Frontend: `ClipsPage` con dos listas + `TrimDialog` con el player y las dos marcas. `e-ovrt_datasets` y `e-ovrt_media-plane` **no se tocan**: `prepare_clip.sh` se invoca tal cual está.

**Tech Stack:** FastAPI/Starlette, pytest, PyYAML, ffmpeg/ffprobe (ya requeridos por la feature de grabación); React + vitest en el frontend.

**Spec:** `docs/superpowers/specs/2026-07-21-generacion-clips-consola-design.md`

## Global Constraints

- **NUNCA commitear**: regla del workspace (`projects/CLAUDE.md`). Este plan NO tiene pasos de commit; cada tarea cierra con `git add -N` (intent-to-add) de los archivos nuevos. El usuario decide cuándo commitear.
- Código y comentarios **en español**, estilo del archivo circundante.
- Backend: correr tests con `.venv/bin/python -m pytest` desde `webconsole/backend/` (**`pytest` a secas falla** por `from tests.fake_service import`). Lint: `.venv/bin/python -m ruff check src tests`.
- Frontend: `npx vitest run` desde `webconsole/frontend/`. **No hay `jest-dom`**: usar `toBeTruthy()`, nunca `toBeInTheDocument()`/`toBeDisabled()`. `afterEach(() => cleanup())` explícito. `fireEvent`, nunca `userEvent`.
- **`prepare_clip.sh --to` es DURACIÓN**, no instante absoluto (verificado empíricamente, ffmpeg 8.0.1). Siempre se pasa duración (D3 del spec).
- El master en `raw/` **nunca se modifica ni borra** (D8).
- Pre-roll = **3,5 s**, cola = **3 s** (doc 59 §1). Objetivos de duración: P1≈20 s, P2≈30 s, P3≈15 s, P5=15–20 s, P9=18–20 s; P4/P6/P7/P8 **sin objetivo** (no se inventa).
- `clip_id` = `a_<escenario_minúscula>_c<NN>` (D4), p.ej. `a_p1_c01`.
- El `.clip.yaml` se genera sin campos a mano (D5); no se piden `distance_band_m`/`lighting`/`occlusion` (D6).
- Advertencias del guion: **avisan fuerte y se genera igual** (D7); quedan en `episode_draft.warnings`.
- Regenerar sobrescribe el mismo `clip_id` e **invalida la pre-anotación vieja** (D9): `preann/<clip_id>.xml` y `preann/<clip_id>.preview.mp4` se renombran con sufijo `.stale`.
- No usar `TMPDIR` ni depender de espacio en `/tmp` para que pasen tests.
- Estado verde de partida: backend 421 passed, frontend 165 passed, ruff y tsc limpios. Ninguna tarea puede dejar menos que eso.

## Estructura de archivos

| Archivo | Responsabilidad |
|---|---|
| `webconsole/backend/src/eovrt_webconsole/settings.py` (modificar) | Rutas de `datasets-videos/` (clips, preann, script) |
| `webconsole/backend/src/eovrt_webconsole/clips/__init__.py` (crear) | Paquete |
| `webconsole/backend/src/eovrt_webconsole/clips/window.py` (crear) | Marcas → ventana + advertencias. **Pura** |
| `webconsole/backend/src/eovrt_webconsole/clips/naming.py` (crear) | Próximo `clip_id` libre por escenario |
| `webconsole/backend/src/eovrt_webconsole/clips/inventory.py` (crear) | Estado de masters y clips |
| `webconsole/backend/src/eovrt_webconsole/clips/trim.py` (crear) | Invoca `prepare_clip.sh`, reporta salida real |
| `webconsole/backend/src/eovrt_webconsole/clips/clip_yaml.py` (crear) | Escribe el `.clip.yaml` |
| `webconsole/backend/src/eovrt_webconsole/clips/generate.py` (crear) | Orquestación: ventana→id→trim→yaml + D9 |
| `webconsole/backend/src/eovrt_webconsole/routers/clips.py` (crear) | REST + servido de video con Range |
| `webconsole/backend/src/eovrt_webconsole/app.py` (modificar) | Registrar el router |
| `webconsole/frontend/src/types.ts`, `src/api.ts` (modificar) | Tipos y cliente |
| `webconsole/frontend/src/pages/ClipsPage.tsx` (crear) | Las dos listas |
| `webconsole/frontend/src/components/TrimDialog.tsx` (crear) | Player con las dos marcas |
| `webconsole/frontend/src/App.tsx`, `src/nav.ts` (modificar) | Ruta y nav |

Datos de contexto que las tareas dan por sabidos:

- `settings.raw_dir` ya existe (masters). Default: `repo_root.parent / "e-ovrt_datasets" / "datasets-videos" / "raw"`, override `EOVRT_CONSOLE_RECORDINGS_DIR`.
- `prepare_clip.sh` vive en `e-ovrt_datasets/datasets/scripts/videogt/prepare_clip.sh`, calcula su repo root desde su propia ubicación (`dirname $BASH_SOURCE/../../..`) y escribe SIEMPRE en `<su repo>/datasets-videos/clips/<clip_id>.mp4` + `<clip_id>.info.json`. Requiere `ffmpeg`, `ffprobe` y `python3` en PATH. Valida `clip_id` contra `[A-Za-z0-9_-]+`.
- `derive_clip_gt.py` (mismo repo, `datasets/scripts/videogt/`) exige solo `clip_id`/`block`/`scenario` en el `.clip.yaml`, valida `level` ∈ {scene, subject} y que `recording`/`annotation` sean dicts si están; **tolera claves extra** (verificado leyendo `load_clip_meta`).
- Los `.clip.yaml` viven en la **raíz** de `datasets-videos/` (ej. `cb_b01_p7.clip.yaml`), no en `clips/`.
- `eovrt_webconsole.recording.probe.measure(path) -> Measured(width, height, fps, duration_ms)` ya existe y lanza `ProbeError` si el archivo no es video legible. Se reusa.
- Fixtures de conftest backend: `repo` (repo_root temporal con `prompts/` y `experiments/`), `fake_state` + `make_fake_service` (media-plane fake), patrón `rec_client` en `tests/test_recordings_router.py`.

---

### Task 1: Settings — rutas de `datasets-videos`

**Files:**
- Modify: `webconsole/backend/src/eovrt_webconsole/settings.py`
- Test: `webconsole/backend/tests/test_settings.py` (agregar tests al final)

**Interfaces:**
- Produces: `ConsoleSettings.datasets_videos_dir: Path | None` (campo, default `None`), y propiedades `videos_dir: Path`, `clips_dir: Path`, `preann_dir: Path`, `prepare_clip_script: Path`. Env var `EOVRT_CONSOLE_DATASETS_VIDEOS_DIR`.

- [ ] **Step 1: Tests que fallan**

Agregar al final de `webconsole/backend/tests/test_settings.py`:

```python
def test_videos_dir_default_apunta_al_repo_hermano(tmp_path):
    settings = _settings(tmp_path)
    esperado = tmp_path.parent / "e-ovrt_datasets" / "datasets-videos"
    assert settings.videos_dir == esperado
    assert settings.clips_dir == esperado / "clips"
    assert settings.preann_dir == esperado / "preann"
    assert settings.prepare_clip_script == (
        tmp_path.parent / "e-ovrt_datasets" / "datasets" / "scripts" / "videogt" / "prepare_clip.sh"
    )


def test_videos_dir_por_env(tmp_path, monkeypatch):
    _crear_repo(tmp_path)
    dv = tmp_path / "dv"
    env = {
        "EOVRT_CONSOLE_REPO_ROOT": str(tmp_path),
        "EOVRT_CONSOLE_DATASETS_VIDEOS_DIR": str(dv),
    }
    settings = ConsoleSettings.from_env(env)
    assert settings.videos_dir == dv
    assert settings.clips_dir == dv / "clips"
    # El script se resuelve contra el padre de datasets-videos (la raíz del repo datasets)
    assert settings.prepare_clip_script == dv.parent / "datasets" / "scripts" / "videogt" / "prepare_clip.sh"
```

Nota para el implementador: `test_settings.py` ya tiene helpers para armar un repo_root válido — si se llaman distinto a `_settings`/`_crear_repo`, usar los existentes (leer el archivo primero y adaptar los tests a sus helpers reales; lo que importa son las aserciones).

- [ ] **Step 2: Verificar que fallan**

```bash
cd /home/simonll4/projects/e-ovrt_experimental-setup/webconsole/backend
.venv/bin/python -m pytest tests/test_settings.py -q
```
Esperado: FAIL con `AttributeError: ... 'videos_dir'`.

- [ ] **Step 3: Implementación mínima**

En `settings.py`, dentro de `ConsoleSettings`, después del campo `oakd_python`:

```python
    # Raíz de datasets-videos del repo hermano e-ovrt_datasets (masters, clips,
    # preann y los .clip.yaml). None = repo hermano. La generación de clips
    # (spec 2026-07-21) resuelve todo contra esta ruta.
    datasets_videos_dir: Path | None = None
```

Después de la property `raw_dir`:

```python
    @property
    def videos_dir(self) -> Path:
        if self.datasets_videos_dir is not None:
            return self.datasets_videos_dir
        return self.repo_root.parent / "e-ovrt_datasets" / "datasets-videos"

    @property
    def clips_dir(self) -> Path:
        return self.videos_dir / "clips"

    @property
    def preann_dir(self) -> Path:
        return self.videos_dir / "preann"

    @property
    def prepare_clip_script(self) -> Path:
        # El script calcula su repo root desde su propia ubicación y escribe
        # SIEMPRE en <su repo>/datasets-videos/clips: por eso se resuelve
        # contra el padre de videos_dir y no contra una ruta independiente.
        return self.videos_dir.parent / "datasets" / "scripts" / "videogt" / "prepare_clip.sh"
```

En `from_env(...)`, junto a `recordings_dir`:

```python
            datasets_videos_dir=(
                Path(env["EOVRT_CONSOLE_DATASETS_VIDEOS_DIR"])
                if env.get("EOVRT_CONSOLE_DATASETS_VIDEOS_DIR")
                else None
            ),
```

- [ ] **Step 4: Verificar que pasan + regresión**

```bash
.venv/bin/python -m pytest tests/test_settings.py -q && .venv/bin/python -m ruff check src tests
```
Esperado: PASS, ruff limpio.

- [ ] **Step 5: Stage**

```bash
git -C /home/simonll4/projects/e-ovrt_experimental-setup add webconsole/backend/src/eovrt_webconsole/settings.py webconsole/backend/tests/test_settings.py
```

---

### Task 2: `clips/window.py` — marcas → ventana (función pura)

**Files:**
- Create: `webconsole/backend/src/eovrt_webconsole/clips/__init__.py` (vacío)
- Create: `webconsole/backend/src/eovrt_webconsole/clips/window.py`
- Test: `webconsole/backend/tests/test_clip_window.py`

**Interfaces:**
- Produces:
  - `compute_window(t_event: float, t_end: float, master_duration: float, scenario: str) -> TrimWindow` — tiempos en **segundos** sobre el master.
  - `TrimWindow(ss: float, duration: float, onset_ms: int, end_ms: int, warnings: list[str])` — `ss`/`duration` son lo que se pasa a `prepare_clip.sh` (`--ss`, `--to`); `onset_ms`/`end_ms` son relativos **al clip**.
  - `InvalidMarks(ValueError)` — fin ≤ evento o marcas fuera del master.
  - Constantes: `PRE_ROLL_S = 3.5`, `TAIL_S = 3.0`, `SCENARIO_TARGET_S = {"P1": 20.0, "P2": 30.0, "P3": 15.0, "P5": 15.0, "P9": 18.0}`.

- [ ] **Step 1: Tests que fallan**

Crear `webconsole/backend/tests/test_clip_window.py`:

```python
import pytest

from eovrt_webconsole.clips.window import InvalidMarks, compute_window


def test_caso_nominal_p1():
    # Evento a los 10.5 s, fin a los 24.5 s de un master de 33 s (plantilla P1).
    w = compute_window(10.5, 24.5, 33.0, "P1")
    assert w.ss == 7.0                # 10.5 - 3.5
    assert w.duration == 20.5         # (24.5 + 3) - 7
    assert w.onset_ms == 3500
    assert w.end_ms == 17500
    assert w.warnings == []


def test_pre_roll_corto_arranca_en_cero_y_avisa():
    # Evento a los 2 s: no se puede retroceder 3.5, el corte arranca en 0
    # y el onset queda en t_evento (spec §5.2).
    w = compute_window(2.0, 15.0, 33.0, "P1")
    assert w.ss == 0.0
    assert w.onset_ms == 2000
    assert any("pre-roll" in msg for msg in w.warnings)


def test_cola_corta_recorta_al_master_y_avisa():
    # Fin a 1 s del final del master: no entran los 3 s de cola.
    w = compute_window(10.5, 32.0, 33.0, "P1")
    assert w.duration == pytest.approx(33.0 - 7.0)
    assert any("cola" in msg for msg in w.warnings)


def test_clip_bajo_el_objetivo_del_escenario_avisa():
    # P2 pide ~30 s; esta ventana da ~16.5 s.
    w = compute_window(5.0, 15.0, 60.0, "P2")
    assert any("30" in msg for msg in w.warnings)


def test_escenario_sin_objetivo_no_inventa_advertencia():
    # P4 no está cuantificado en el guion: clip corto pero sin advertencia
    # de duración (las de pre-roll/cola sí aplican, acá no se disparan).
    w = compute_window(10.0, 14.0, 60.0, "P4")
    assert w.warnings == []


def test_fin_antes_del_evento_se_rechaza():
    with pytest.raises(InvalidMarks):
        compute_window(20.0, 10.0, 33.0, "P1")


def test_fin_igual_al_evento_se_rechaza():
    with pytest.raises(InvalidMarks):
        compute_window(20.0, 20.0, 33.0, "P1")


def test_marcas_fuera_del_master_se_rechazan():
    with pytest.raises(InvalidMarks):
        compute_window(-1.0, 10.0, 33.0, "P1")
    with pytest.raises(InvalidMarks):
        compute_window(10.0, 40.0, 33.0, "P1")
```

- [ ] **Step 2: Verificar que fallan**

```bash
.venv/bin/python -m pytest tests/test_clip_window.py -q
```
Esperado: FAIL con `ModuleNotFoundError: No module named 'eovrt_webconsole.clips'`.

- [ ] **Step 3: Implementación**

Crear `webconsole/backend/src/eovrt_webconsole/clips/__init__.py` vacío y `window.py`:

```python
"""Marcas del operador -> ventana de recorte + advertencias del guion.

Función PURA (spec §8): sin ffmpeg ni archivos. Los números salen de las
reglas de oro del guion (docs/operacion/59 §1-§4): onset en t~3-4 s, cola
>=3 s tras corregir la infracción, y objetivos de duración por escenario.
"""

from __future__ import annotations

from dataclasses import dataclass

PRE_ROLL_S = 3.5
TAIL_S = 3.0
# Objetivos de duración por escenario (doc 59 §2-§4). Los escenarios que el
# guion no cuantifica (P4/P6/P7/P8) NO figuran: no se inventa un objetivo.
SCENARIO_TARGET_S = {"P1": 20.0, "P2": 30.0, "P3": 15.0, "P5": 15.0, "P9": 18.0}


class InvalidMarks(ValueError):
    pass


@dataclass(frozen=True)
class TrimWindow:
    ss: float            # inicio del corte en el master (s)
    duration: float      # lo que se pasa como --to: DURACIÓN, nunca instante (D3)
    onset_ms: int        # evento relativo AL CLIP
    end_ms: int          # fin relativo AL CLIP
    warnings: list[str]


def compute_window(
    t_event: float, t_end: float, master_duration: float, scenario: str
) -> TrimWindow:
    if t_end <= t_event:
        raise InvalidMarks(
            f"el fin ({t_end:.1f} s) tiene que ser posterior al evento ({t_event:.1f} s)"
        )
    if t_event < 0 or t_end > master_duration:
        raise InvalidMarks(
            f"marcas fuera del master (evento={t_event:.1f} s, fin={t_end:.1f} s, "
            f"master de {master_duration:.1f} s)"
        )

    warnings: list[str] = []

    start = t_event - PRE_ROLL_S
    if start < 0:
        # No se puede retroceder más: el corte arranca en 0 y el onset queda
        # en t_evento (<3500 ms). Esa asimetría es la señal de TTFD degradado.
        warnings.append(
            f"solo {t_event:.1f} s de pre-roll, se necesitan {PRE_ROLL_S} — "
            "el TTFD va a salir degradado"
        )
        start = 0.0

    end_clip = t_end + TAIL_S
    if end_clip > master_duration:
        cola = max(master_duration - t_end, 0.0)
        warnings.append(f"solo {cola:.1f} s de cola, se necesitan {TAIL_S:g}")
        end_clip = master_duration

    duration = end_clip - start
    target = SCENARIO_TARGET_S.get(scenario)
    if target is not None and duration < target:
        warnings.append(
            f"clip de {duration:.1f} s, el guion pide ~{target:g} s para este escenario"
        )

    return TrimWindow(
        ss=round(start, 3),
        duration=round(duration, 3),
        onset_ms=round((t_event - start) * 1000),
        end_ms=round((t_end - start) * 1000),
        warnings=warnings,
    )
```

- [ ] **Step 4: Verificar que pasan**

```bash
.venv/bin/python -m pytest tests/test_clip_window.py -q && .venv/bin/python -m ruff check src tests
```
Esperado: 8 passed, ruff limpio.

- [ ] **Step 5: Stage**

```bash
git -C /home/simonll4/projects/e-ovrt_experimental-setup add -N webconsole/backend/src/eovrt_webconsole/clips/ && git -C /home/simonll4/projects/e-ovrt_experimental-setup add webconsole/backend/tests/test_clip_window.py
```

---

### Task 3: `clips/naming.py` — próximo `clip_id` libre

**Files:**
- Create: `webconsole/backend/src/eovrt_webconsole/clips/naming.py`
- Test: `webconsole/backend/tests/test_clip_naming.py`

**Interfaces:**
- Produces:
  - `next_clip_id(videos_dir: Path, scenario: str) -> str` — p.ej. `"a_p1_c01"`. Escanea `*.clip.yaml` en `videos_dir` **y** `*.mp4` en `videos_dir/clips/` (cualquiera de los dos reserva el número). `videos_dir` inexistente → arranca en `c01`.
  - `InvalidScenario(ValueError)` — escenario fuera de `P1..P9`.
  - `scenario_from_master(name: str) -> str | None` — `"P1-a-take2.mp4"` → `"P1"`; material ajeno (`"4.1.mp4"`) → `None`.

- [ ] **Step 1: Tests que fallan**

Crear `webconsole/backend/tests/test_clip_naming.py`:

```python
import pytest

from eovrt_webconsole.clips.naming import (
    InvalidScenario,
    next_clip_id,
    scenario_from_master,
)


def test_primer_clip_del_escenario(tmp_path):
    assert next_clip_id(tmp_path, "P1") == "a_p1_c01"


def test_autoincremento_por_yaml(tmp_path):
    (tmp_path / "a_p1_c01.clip.yaml").write_text("clip_id: a_p1_c01\n")
    (tmp_path / "a_p1_c02.clip.yaml").write_text("clip_id: a_p1_c02\n")
    assert next_clip_id(tmp_path, "P1") == "a_p1_c03"


def test_mp4_sin_yaml_tambien_reserva_el_numero(tmp_path):
    # Un clip recortado cuyo yaml se borró no debe ser pisado.
    (tmp_path / "clips").mkdir()
    (tmp_path / "clips" / "a_p2_c05.mp4").write_bytes(b"")
    assert next_clip_id(tmp_path, "P2") == "a_p2_c06"


def test_huecos_no_se_rellenan(tmp_path):
    # c01 y c03: el próximo es c04, no c02 (regenerar c02 sería ambiguo).
    (tmp_path / "a_p1_c01.clip.yaml").write_text("x: 1\n")
    (tmp_path / "a_p1_c03.clip.yaml").write_text("x: 1\n")
    assert next_clip_id(tmp_path, "P1") == "a_p1_c04"


def test_material_ajeno_no_interfiere(tmp_path):
    (tmp_path / "cb_b01_p7.clip.yaml").write_text("x: 1\n")
    (tmp_path / "clips").mkdir()
    (tmp_path / "clips" / "v01_c01.mp4").write_bytes(b"")
    assert next_clip_id(tmp_path, "P1") == "a_p1_c01"


def test_escenarios_independientes(tmp_path):
    (tmp_path / "a_p1_c01.clip.yaml").write_text("x: 1\n")
    assert next_clip_id(tmp_path, "P2") == "a_p2_c01"


def test_directorio_inexistente_arranca_en_c01(tmp_path):
    assert next_clip_id(tmp_path / "no-existe", "P1") == "a_p1_c01"


def test_escenario_invalido(tmp_path):
    with pytest.raises(InvalidScenario):
        next_clip_id(tmp_path, "P0")
    with pytest.raises(InvalidScenario):
        next_clip_id(tmp_path, "x")


def test_scenario_from_master():
    assert scenario_from_master("P1-a-take2.mp4") == "P1"
    assert scenario_from_master("P9-c-take11.mp4") == "P9"
    assert scenario_from_master("4.1.mp4") is None
    assert scenario_from_master("cb_b01_p7.mp4") is None
```

- [ ] **Step 2: Verificar que fallan**

```bash
.venv/bin/python -m pytest tests/test_clip_naming.py -q
```
Esperado: FAIL con `ModuleNotFoundError` / `ImportError`.

- [ ] **Step 3: Implementación**

Crear `webconsole/backend/src/eovrt_webconsole/clips/naming.py`:

```python
"""Nombrado de clips: clip_id = a_<escenario>_c<NN> (D4 del spec)."""

from __future__ import annotations

import re
from pathlib import Path

SCENARIO_RE = re.compile(r"^P[1-9]$")
# Mismo formato de toma que recording/naming.py: P1-a-take2.mp4
MASTER_RE = re.compile(r"^(P[1-9])-[a-z]-take[0-9]+\.mp4$")


class InvalidScenario(ValueError):
    pass


def scenario_from_master(name: str) -> str | None:
    """Escenario heredado del master (se eligió al grabar); None si es material ajeno."""
    match = MASTER_RE.match(name)
    return match.group(1) if match else None


def next_clip_id(videos_dir: Path, scenario: str) -> str:
    if not SCENARIO_RE.match(scenario):
        raise InvalidScenario(f"escenario inválido: {scenario!r} (esperado P1..P9)")
    prefix = f"a_{scenario.lower()}_c"
    yaml_re = re.compile(rf"^{re.escape(prefix)}([0-9]+)\.clip\.yaml$")
    mp4_re = re.compile(rf"^{re.escape(prefix)}([0-9]+)\.mp4$")
    highest = 0
    if videos_dir.is_dir():
        for path in videos_dir.iterdir():
            match = yaml_re.match(path.name)
            if match is not None:
                highest = max(highest, int(match.group(1)))
    clips_dir = videos_dir / "clips"
    if clips_dir.is_dir():
        # Un mp4 huérfano (sin yaml) también reserva el número: pisarlo sería
        # perder un clip ya recortado.
        for path in clips_dir.iterdir():
            match = mp4_re.match(path.name)
            if match is not None:
                highest = max(highest, int(match.group(1)))
    return f"{prefix}{highest + 1:02d}"
```

- [ ] **Step 4: Verificar que pasan**

```bash
.venv/bin/python -m pytest tests/test_clip_naming.py -q && .venv/bin/python -m ruff check src tests
```
Esperado: 9 passed, ruff limpio.

- [ ] **Step 5: Stage**

```bash
git -C /home/simonll4/projects/e-ovrt_experimental-setup add webconsole/backend/src/eovrt_webconsole/clips/naming.py webconsole/backend/tests/test_clip_naming.py
```

---

### Task 4: `clips/clip_yaml.py` — escritura del `.clip.yaml` + contrato con `derive_clip_gt`

**Files:**
- Create: `webconsole/backend/src/eovrt_webconsole/clips/clip_yaml.py`
- Test: `webconsole/backend/tests/test_clip_yaml.py`

**Interfaces:**
- Consumes: `TrimWindow` (Task 2).
- Produces: `write_clip_yaml(videos_dir: Path, clip_id: str, scenario: str, master_name: str, window: TrimWindow) -> Path` — escribe `videos_dir/<clip_id>.clip.yaml` y devuelve la ruta. El campo `master` (clave extra tolerada por `derive_clip_gt`) es lo que después usa el inventario (Task 5) para mapear master→clips.

- [ ] **Step 1: Tests que fallan**

Crear `webconsole/backend/tests/test_clip_yaml.py`:

```python
import importlib.util
from pathlib import Path

import pytest
import yaml

from eovrt_webconsole.clips.clip_yaml import write_clip_yaml
from eovrt_webconsole.clips.window import TrimWindow

# Contrato real (spec §8): el YAML generado se valida con la MISMA función
# del script consumidor, no con lo que este repo suponga.
DERIVE_GT = (
    Path(__file__).resolve().parents[4]
    / "e-ovrt_datasets" / "datasets" / "scripts" / "videogt" / "derive_clip_gt.py"
)

VENTANA = TrimWindow(ss=7.0, duration=20.5, onset_ms=3500, end_ms=17500, warnings=[])


def test_contenido_del_yaml(tmp_path):
    path = write_clip_yaml(tmp_path, "a_p1_c01", "P1", "P1-a-take2.mp4", VENTANA)
    assert path == tmp_path / "a_p1_c01.clip.yaml"
    data = yaml.safe_load(path.read_text())
    assert data["clip_id"] == "a_p1_c01"
    assert data["block"] == "A"
    assert data["scenario"] == "P1"
    assert data["source_id"] == "a_p1_c01"
    assert data["level"] == "scene"
    assert data["master"] == "raw/P1-a-take2.mp4"
    assert data["episode_draft"] == {
        "onset_ms": 3500,
        "end_ms": 17500,
        "marked_by": "consola",
        "warnings": [],
    }


def test_las_advertencias_quedan_registradas(tmp_path):
    ventana = TrimWindow(
        ss=0.0, duration=18.0, onset_ms=2000, end_ms=15000,
        warnings=["solo 2.0 s de pre-roll, se necesitan 3.5 — el TTFD va a salir degradado"],
    )
    path = write_clip_yaml(tmp_path, "a_p1_c02", "P1", "P1-a-take3.mp4", ventana)
    data = yaml.safe_load(path.read_text())
    assert data["episode_draft"]["warnings"] == ventana.warnings


def test_regenerar_sobrescribe(tmp_path):
    write_clip_yaml(tmp_path, "a_p1_c01", "P1", "P1-a-take2.mp4", VENTANA)
    nueva = TrimWindow(ss=8.0, duration=19.0, onset_ms=3500, end_ms=16000, warnings=[])
    write_clip_yaml(tmp_path, "a_p1_c01", "P1", "P1-a-take2.mp4", nueva)
    data = yaml.safe_load((tmp_path / "a_p1_c01.clip.yaml").read_text())
    assert data["episode_draft"]["end_ms"] == 16000


@pytest.mark.skipif(not DERIVE_GT.exists(), reason="repo e-ovrt_datasets no disponible")
def test_el_yaml_pasa_la_validacion_real_de_derive_clip_gt(tmp_path):
    spec = importlib.util.spec_from_file_location("derive_clip_gt", DERIVE_GT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    path = write_clip_yaml(tmp_path, "a_p1_c01", "P1", "P1-a-take2.mp4", VENTANA)
    meta = mod.load_clip_meta(path)   # levanta ValueError si el contrato se rompe
    assert meta["clip_id"] == "a_p1_c01"
    assert meta["block"] == "A"
    assert meta["scenario"] == "P1"
```

- [ ] **Step 2: Verificar que fallan**

```bash
.venv/bin/python -m pytest tests/test_clip_yaml.py -q
```
Esperado: FAIL con `ImportError` (`write_clip_yaml` no existe).

- [ ] **Step 3: Implementación**

Crear `webconsole/backend/src/eovrt_webconsole/clips/clip_yaml.py`:

```python
"""Escritura del <clip_id>.clip.yaml (spec §5.2): cero campos a mano (D5).

derive_clip_gt.load_clip_meta exige solo clip_id/block/scenario y tolera
claves extra (verificado leyendo el script): `master` y `episode_draft` son
seguras y no se filtran al GT. `episode_draft` es un BORRADOR: la verdad
sale de CVAT.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from eovrt_webconsole.clips.window import TrimWindow


def write_clip_yaml(
    videos_dir: Path,
    clip_id: str,
    scenario: str,
    master_name: str,
    window: TrimWindow,
) -> Path:
    payload = {
        "clip_id": clip_id,
        "block": "A",                 # rodaje propio guionado
        "scenario": scenario,
        # El evaluador matchea alert.source_id == episode.source_id; la corrida
        # del bench configura su fuente con el clip_id.
        "source_id": clip_id,
        "level": "scene",
        # Clave extra tolerada: mapea el clip a su master para el inventario
        # de la consola y para rehacer el corte sin volver a filmar (D8).
        "master": f"raw/{master_name}",
        "episode_draft": {
            "onset_ms": window.onset_ms,
            "end_ms": window.end_ms,
            "marked_by": "consola",
            "warnings": list(window.warnings),
        },
    }
    path = videos_dir / f"{clip_id}.clip.yaml"
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return path
```

- [ ] **Step 4: Verificar que pasan**

```bash
.venv/bin/python -m pytest tests/test_clip_yaml.py -q && .venv/bin/python -m ruff check src tests
```
Esperado: 4 passed (el test de contrato NO debe saltearse en esta máquina: el repo hermano existe), ruff limpio.

- [ ] **Step 5: Stage**

```bash
git -C /home/simonll4/projects/e-ovrt_experimental-setup add webconsole/backend/src/eovrt_webconsole/clips/clip_yaml.py webconsole/backend/tests/test_clip_yaml.py
```

---

### Task 5: `clips/inventory.py` — estado de masters y clips

**Files:**
- Create: `webconsole/backend/src/eovrt_webconsole/clips/inventory.py`
- Test: `webconsole/backend/tests/test_clip_inventory.py`

**Interfaces:**
- Consumes: `scenario_from_master` (Task 3), `recording.probe.measure`/`ProbeError` (existente).
- Produces:
  - `list_masters(raw_dir: Path, videos_dir: Path) -> list[dict]` — un dict por `*.mp4` de `raw/`, ordenado por nombre: `{"name", "scenario", "size_bytes", "duration_ms", "readable", "clips"}`. `clips` = clip_ids cuyos `.clip.yaml` declaran `master: raw/<name>`. `duration_ms=None`/`readable=False` si ffprobe falla (no rompe la vista). `raw_dir` inexistente → `[]`.
  - `list_clips(videos_dir: Path) -> list[dict]` — un dict por `clips/*.info.json`, ordenado por clip_id: `{"clip_id", "fps", "duration_ms", "n_frames", "resolution", "has_yaml", "master", "warnings"}` (`master`/`warnings` desde el `.clip.yaml` si existe, sino `None`/`[]`). `clips/` inexistente → `[]`.

- [ ] **Step 1: Tests que fallan**

Crear `webconsole/backend/tests/test_clip_inventory.py`:

```python
import json

from eovrt_webconsole.clips.inventory import list_clips, list_masters
from eovrt_webconsole.recording.probe import Measured


def _dv(tmp_path):
    dv = tmp_path / "datasets-videos"
    (dv / "raw").mkdir(parents=True)
    (dv / "clips").mkdir()
    return dv


def _measure_fake(monkeypatch, duration_ms=33000):
    import eovrt_webconsole.clips.inventory as inv

    monkeypatch.setattr(
        inv, "measure",
        lambda path: Measured(width=1920, height=1080, fps=30.0, duration_ms=duration_ms),
    )


def test_master_sin_recortar(tmp_path, monkeypatch):
    dv = _dv(tmp_path)
    _measure_fake(monkeypatch)
    (dv / "raw" / "P1-a-take1.mp4").write_bytes(b"x" * 10)
    [m] = list_masters(dv / "raw", dv)
    assert m["name"] == "P1-a-take1.mp4"
    assert m["scenario"] == "P1"
    assert m["duration_ms"] == 33000
    assert m["readable"] is True
    assert m["clips"] == []


def test_master_con_clip_generado(tmp_path, monkeypatch):
    dv = _dv(tmp_path)
    _measure_fake(monkeypatch)
    (dv / "raw" / "P1-a-take1.mp4").write_bytes(b"x")
    (dv / "a_p1_c01.clip.yaml").write_text(
        "clip_id: a_p1_c01\nblock: A\nscenario: P1\nmaster: raw/P1-a-take1.mp4\n"
    )
    [m] = list_masters(dv / "raw", dv)
    assert m["clips"] == ["a_p1_c01"]


def test_master_ilegible_se_marca_sin_romper(tmp_path, monkeypatch):
    import eovrt_webconsole.clips.inventory as inv
    from eovrt_webconsole.recording.probe import ProbeError

    dv = _dv(tmp_path)

    def _explota(path):
        raise ProbeError("no es un video")

    monkeypatch.setattr(inv, "measure", _explota)
    (dv / "raw" / "P1-a-take1.mp4").write_bytes(b"basura")
    [m] = list_masters(dv / "raw", dv)
    assert m["readable"] is False
    assert m["duration_ms"] is None


def test_raw_inexistente_lista_vacia(tmp_path):
    assert list_masters(tmp_path / "no", tmp_path) == []


def test_solo_mp4_y_ordenado(tmp_path, monkeypatch):
    dv = _dv(tmp_path)
    _measure_fake(monkeypatch)
    (dv / "raw" / "P2-a-take1.mp4").write_bytes(b"x")
    (dv / "raw" / "P1-a-take1.mp4").write_bytes(b"x")
    (dv / "raw" / "P1-a-take1.rec.json").write_text("{}")
    nombres = [m["name"] for m in list_masters(dv / "raw", dv)]
    assert nombres == ["P1-a-take1.mp4", "P2-a-take1.mp4"]


def test_list_clips(tmp_path):
    dv = _dv(tmp_path)
    info = {
        "clip_id": "a_p1_c01", "file": "clips/a_p1_c01.mp4", "fps": 30,
        "duration_ms": 20500, "n_frames": 615, "resolution": "1920x1080",
        "sha256": "0" * 64,
    }
    (dv / "clips" / "a_p1_c01.info.json").write_text(json.dumps(info))
    (dv / "clips" / "a_p1_c01.mp4").write_bytes(b"x")
    (dv / "a_p1_c01.clip.yaml").write_text(
        "clip_id: a_p1_c01\nblock: A\nscenario: P1\nmaster: raw/P1-a-take1.mp4\n"
        "episode_draft:\n  onset_ms: 3500\n  end_ms: 17500\n  marked_by: consola\n"
        "  warnings: ['solo 2.0 s de cola, se necesitan 3']\n"
    )
    [c] = list_clips(dv)
    assert c["clip_id"] == "a_p1_c01"
    assert c["n_frames"] == 615
    assert c["has_yaml"] is True
    assert c["master"] == "raw/P1-a-take1.mp4"
    assert c["warnings"] == ["solo 2.0 s de cola, se necesitan 3"]


def test_clip_ajeno_sin_yaml(tmp_path):
    dv = _dv(tmp_path)
    info = {
        "clip_id": "v01_c01", "file": "clips/v01_c01.mp4", "fps": 30,
        "duration_ms": 15000, "n_frames": 450, "resolution": "1280x720",
        "sha256": "0" * 64,
    }
    (dv / "clips" / "v01_c01.info.json").write_text(json.dumps(info))
    [c] = list_clips(dv)
    assert c["has_yaml"] is False
    assert c["master"] is None
    assert c["warnings"] == []


def test_clips_inexistente_lista_vacia(tmp_path):
    assert list_clips(tmp_path) == []
```

- [ ] **Step 2: Verificar que fallan**

```bash
.venv/bin/python -m pytest tests/test_clip_inventory.py -q
```
Esperado: FAIL con `ImportError`.

- [ ] **Step 3: Implementación**

Crear `webconsole/backend/src/eovrt_webconsole/clips/inventory.py`:

```python
"""Inventario: lee raw/ y clips/ y deriva el estado de cada toma.

Solo lectura. Un master ilegible se marca (readable=False), no rompe la
vista; raw/ o clips/ inexistentes dan lista vacía (spec §7).
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from eovrt_webconsole.clips.naming import scenario_from_master
from eovrt_webconsole.recording.probe import ProbeError, measure


def _clips_por_master(videos_dir: Path) -> dict[str, list[str]]:
    """master ("raw/<name>") -> clip_ids, según el campo `master` de los .clip.yaml."""
    por_master: dict[str, list[str]] = {}
    if not videos_dir.is_dir():
        return por_master
    for path in sorted(videos_dir.glob("*.clip.yaml")):
        try:
            data = yaml.safe_load(path.read_text())
        except yaml.YAMLError:
            continue
        if not isinstance(data, dict):
            continue
        master = data.get("master")
        clip_id = data.get("clip_id")
        if isinstance(master, str) and isinstance(clip_id, str):
            por_master.setdefault(master, []).append(clip_id)
    return por_master


def list_masters(raw_dir: Path, videos_dir: Path) -> list[dict]:
    if not raw_dir.is_dir():
        return []
    por_master = _clips_por_master(videos_dir)
    masters = []
    for path in sorted(raw_dir.glob("*.mp4")):
        try:
            measured = measure(path)
            duration_ms: int | None = measured.duration_ms
            readable = True
        except ProbeError:
            duration_ms = None
            readable = False
        masters.append(
            {
                "name": path.name,
                "scenario": scenario_from_master(path.name),
                "size_bytes": path.stat().st_size,
                "duration_ms": duration_ms,
                "readable": readable,
                "clips": sorted(por_master.get(f"raw/{path.name}", [])),
            }
        )
    return masters


def list_clips(videos_dir: Path) -> list[dict]:
    clips_dir = videos_dir / "clips"
    if not clips_dir.is_dir():
        return []
    clips = []
    for info_path in sorted(clips_dir.glob("*.info.json")):
        try:
            info = json.loads(info_path.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        clip_id = info.get("clip_id", info_path.name.removesuffix(".info.json"))
        yaml_path = videos_dir / f"{clip_id}.clip.yaml"
        master = None
        warnings: list = []
        has_yaml = yaml_path.is_file()
        if has_yaml:
            try:
                meta = yaml.safe_load(yaml_path.read_text()) or {}
            except yaml.YAMLError:
                meta = {}
            master = meta.get("master")
            draft = meta.get("episode_draft") or {}
            if isinstance(draft, dict):
                warnings = draft.get("warnings") or []
        clips.append(
            {
                "clip_id": clip_id,
                "fps": info.get("fps"),
                "duration_ms": info.get("duration_ms"),
                "n_frames": info.get("n_frames"),
                "resolution": info.get("resolution"),
                "has_yaml": has_yaml,
                "master": master,
                "warnings": warnings,
            }
        )
    return clips
```

- [ ] **Step 4: Verificar que pasan**

```bash
.venv/bin/python -m pytest tests/test_clip_inventory.py -q && .venv/bin/python -m ruff check src tests
```
Esperado: 8 passed, ruff limpio.

- [ ] **Step 5: Stage**

```bash
git -C /home/simonll4/projects/e-ovrt_experimental-setup add webconsole/backend/src/eovrt_webconsole/clips/inventory.py webconsole/backend/tests/test_clip_inventory.py
```

---

### Task 6: `clips/trim.py` — invocación real de `prepare_clip.sh`

**Files:**
- Create: `webconsole/backend/src/eovrt_webconsole/clips/trim.py`
- Test: `webconsole/backend/tests/test_clip_trim.py`

**Interfaces:**
- Produces:
  - `run_prepare_clip(script: Path, clips_dir: Path, master: Path, clip_id: str, ss: float, duration: float, fps: int = 30) -> dict` — corre el script, y devuelve el contenido de `clips_dir/<clip_id>.info.json`. Bloqueante (el endpoint que lo usa será `def` sincrónico: FastAPI lo corre en threadpool).
  - `TrimFailed(RuntimeError)` — `returncode != 0`; `str(exc)` contiene stdout+stderr **reales** del script (spec §7: nunca un error genérico).

**Nota para el implementador:** `prepare_clip.sh` calcula su repo root desde su PROPIA ubicación y escribe en `<su repo>/datasets-videos/clips/`. El test copia el script real a una estructura temporal que replica esa forma (`<tmp>/datasets/scripts/videogt/prepare_clip.sh` + `<tmp>/datasets-videos/clips/`), así el test nunca escribe en el repo real. Requiere `ffmpeg`, `ffprobe` y `python3` (ya requeridos por los tests de grabación).

- [ ] **Step 1: Tests que fallan**

Crear `webconsole/backend/tests/test_clip_trim.py`:

```python
import shutil
import subprocess
from pathlib import Path

import pytest

from eovrt_webconsole.clips.trim import TrimFailed, run_prepare_clip

REAL_SCRIPT = (
    Path(__file__).resolve().parents[4]
    / "e-ovrt_datasets" / "datasets" / "scripts" / "videogt" / "prepare_clip.sh"
)

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None
    or shutil.which("ffprobe") is None
    or not REAL_SCRIPT.exists(),
    reason="requiere ffmpeg/ffprobe y el repo e-ovrt_datasets",
)


@pytest.fixture
def fake_repo(tmp_path):
    """Réplica de la forma del repo datasets: el script escribe SIEMPRE en
    <su repo>/datasets-videos/clips, así que se lo copia a un repo falso."""
    script = tmp_path / "datasets" / "scripts" / "videogt" / "prepare_clip.sh"
    script.parent.mkdir(parents=True)
    shutil.copy(REAL_SCRIPT, script)
    clips = tmp_path / "datasets-videos" / "clips"
    clips.mkdir(parents=True)
    return script, clips


@pytest.fixture
def master(tmp_path):
    out = tmp_path / "P1-a-take1.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
         "-f", "lavfi", "-i", "testsrc=size=320x240:rate=30:duration=20",
         "-c:v", "libx264", "-preset", "ultrafast", str(out)],
        check=True,
    )
    return out


def test_recorte_nominal(fake_repo, master):
    script, clips_dir = fake_repo
    # Criterio de aceptación del spec §8: n_frames coherente con la ventana.
    info = run_prepare_clip(script, clips_dir, master, "a_p1_c01", ss=5.0, duration=8.0)
    assert info["clip_id"] == "a_p1_c01"
    assert info["fps"] == 30
    # 8 s a 30 fps = 240 frames (tolerancia 1 por el borde del corte)
    assert abs(info["n_frames"] - 240) <= 1
    assert (clips_dir / "a_p1_c01.mp4").exists()
    # D3: --to fue duración. Si prepare_clip lo hubiera tratado como instante
    # absoluto el clip tendría ~90 frames (3 s); la trampa quedaría atrapada acá.


def test_master_intacto_tras_recortar(fake_repo, master):
    script, clips_dir = fake_repo
    antes = master.read_bytes()
    run_prepare_clip(script, clips_dir, master, "a_p1_c02", ss=0.0, duration=5.0)
    assert master.read_bytes() == antes  # D8


def test_falla_reporta_salida_real(fake_repo, tmp_path):
    script, clips_dir = fake_repo
    inexistente = tmp_path / "no-existe.mp4"
    with pytest.raises(TrimFailed) as excinfo:
        run_prepare_clip(script, clips_dir, inexistente, "a_p1_c03", ss=0.0, duration=5.0)
    # La salida real de ffmpeg, no un genérico:
    assert "no-existe.mp4" in str(excinfo.value)


def test_clip_id_invalido_lo_rechaza_el_script(fake_repo, master):
    script, clips_dir = fake_repo
    with pytest.raises(TrimFailed) as excinfo:
        run_prepare_clip(script, clips_dir, master, "a p1 c01", ss=0.0, duration=5.0)
    assert "clip_id" in str(excinfo.value)
```

- [ ] **Step 2: Verificar que fallan**

```bash
.venv/bin/python -m pytest tests/test_clip_trim.py -q
```
Esperado: FAIL con `ImportError`.

- [ ] **Step 3: Implementación**

Crear `webconsole/backend/src/eovrt_webconsole/clips/trim.py`:

```python
"""Invocación de prepare_clip.sh del repo datasets, tal cual está (spec §4).

D3: `duration` se pasa como --to, que en ese script es RELATIVO al punto de
corte (funciona como duración; verificado empíricamente con ffmpeg 8.0.1).
Nunca pasar acá un instante absoluto: no falla, produce en silencio un clip
más largo con el evento descolocado respecto del GT.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

_TIMEOUT_S = 600  # re-encode x264 de ~30 s de master: minutos, no horas


class TrimFailed(RuntimeError):
    """El script falló; str(exc) es su salida real (spec §7)."""


def run_prepare_clip(
    script: Path,
    clips_dir: Path,
    master: Path,
    clip_id: str,
    ss: float,
    duration: float,
    fps: int = 30,
) -> dict:
    if not script.is_file():
        raise TrimFailed(f"prepare_clip.sh no encontrado en {script}")
    cmd = [
        "bash", str(script), str(master), clip_id,
        "--ss", f"{ss:.3f}",
        "--to", f"{duration:.3f}",   # DURACIÓN (D3)
        "--fps", str(fps),
    ]
    try:
        completed = subprocess.run(
            cmd, capture_output=True, text=True, timeout=_TIMEOUT_S
        )
    except subprocess.TimeoutExpired as exc:
        raise TrimFailed(f"prepare_clip.sh superó los {_TIMEOUT_S} s: {exc}") from exc
    if completed.returncode != 0:
        salida = (completed.stdout + "\n" + completed.stderr).strip()
        raise TrimFailed(salida or f"prepare_clip.sh devolvió {completed.returncode}")
    info_path = clips_dir / f"{clip_id}.info.json"
    try:
        return json.loads(info_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise TrimFailed(
            f"prepare_clip.sh terminó bien pero no dejó {info_path} legible: {exc}"
        ) from exc
```

- [ ] **Step 4: Verificar que pasan**

```bash
.venv/bin/python -m pytest tests/test_clip_trim.py -q && .venv/bin/python -m ruff check src tests
```
Esperado: 4 passed (NO skipped en esta máquina), ruff limpio.

- [ ] **Step 5: Stage**

```bash
git -C /home/simonll4/projects/e-ovrt_experimental-setup add webconsole/backend/src/eovrt_webconsole/clips/trim.py webconsole/backend/tests/test_clip_trim.py
```

---

### Task 7: `clips/generate.py` — orquestación + regeneración (D9)

**Files:**
- Create: `webconsole/backend/src/eovrt_webconsole/clips/generate.py`
- Test: `webconsole/backend/tests/test_clip_generate.py`

**Interfaces:**
- Consumes: `compute_window`/`InvalidMarks` (T2), `next_clip_id`/`scenario_from_master`/`InvalidScenario` (T3), `write_clip_yaml` (T4), `run_prepare_clip`/`TrimFailed` (T6), `probe.measure`/`ProbeError` (existente).
- Produces:
  - `generate_clip(*, raw_dir: Path, videos_dir: Path, script: Path, master_name: str, t_event: float, t_end: float, scenario: str | None = None, clip_id: str | None = None) -> dict` — dict con `{"clip_id", "info", "warnings", "regenerated", "invalidated"}`.
  - `InvalidRequest(ValueError)` — master con path traversal, inexistente, o material ajeno sin `scenario` explícito.
  - Regeneración = `clip_id` explícito: sobrescribe y renombra `preann/<clip_id>.xml` / `.preview.mp4` a `*.stale` (pisando un `.stale` previo); `invalidated` lista los renombrados.

- [ ] **Step 1: Tests que fallan**

Crear `webconsole/backend/tests/test_clip_generate.py`. Para no repetir el costo de ffmpeg real (eso ya lo cubre Task 6), acá se stubbean `measure` y `run_prepare_clip` con monkeypatch:

```python
import pytest

from eovrt_webconsole.clips.generate import InvalidRequest, generate_clip
from eovrt_webconsole.clips.window import InvalidMarks
from eovrt_webconsole.recording.probe import Measured, ProbeError


@pytest.fixture
def dv(tmp_path):
    dv = tmp_path / "datasets-videos"
    (dv / "raw").mkdir(parents=True)
    (dv / "clips").mkdir()
    (dv / "preann").mkdir()
    (dv / "raw" / "P1-a-take1.mp4").write_bytes(b"master")
    return dv


@pytest.fixture
def stubs(monkeypatch):
    import eovrt_webconsole.clips.generate as gen

    llamadas = {}

    def _measure(path):
        return Measured(width=1920, height=1080, fps=30.0, duration_ms=33000)

    def _run(script, clips_dir, master, clip_id, ss, duration, fps=30):
        llamadas["trim"] = {
            "master": master, "clip_id": clip_id, "ss": ss, "duration": duration,
        }
        info = {
            "clip_id": clip_id, "file": f"clips/{clip_id}.mp4", "fps": fps,
            "duration_ms": round(duration * 1000),
            "n_frames": round(duration * fps), "resolution": "1920x1080",
            "sha256": "0" * 64,
        }
        (clips_dir / f"{clip_id}.mp4").write_bytes(b"clip")
        import json
        (clips_dir / f"{clip_id}.info.json").write_text(json.dumps(info))
        return info

    monkeypatch.setattr(gen, "measure", _measure)
    monkeypatch.setattr(gen, "run_prepare_clip", _run)
    return llamadas


def test_flujo_nominal(dv, stubs, tmp_path):
    result = generate_clip(
        raw_dir=dv / "raw", videos_dir=dv, script=tmp_path / "s.sh",
        master_name="P1-a-take1.mp4", t_event=10.5, t_end=24.5,
    )
    assert result["clip_id"] == "a_p1_c01"
    assert result["regenerated"] is False
    assert result["invalidated"] == []
    assert result["warnings"] == []
    assert stubs["trim"]["ss"] == 7.0
    assert stubs["trim"]["duration"] == 20.5
    # El yaml quedó escrito con el borrador del episodio:
    import yaml
    data = yaml.safe_load((dv / "a_p1_c01.clip.yaml").read_text())
    assert data["episode_draft"]["onset_ms"] == 3500


def test_autoincremento_si_ya_hay_clips(dv, stubs, tmp_path):
    (dv / "a_p1_c01.clip.yaml").write_text("clip_id: a_p1_c01\nmaster: raw/x.mp4\n")
    result = generate_clip(
        raw_dir=dv / "raw", videos_dir=dv, script=tmp_path / "s.sh",
        master_name="P1-a-take1.mp4", t_event=10.5, t_end=24.5,
    )
    assert result["clip_id"] == "a_p1_c02"


def test_regenerar_invalida_la_preann_vieja(dv, stubs, tmp_path):
    (dv / "preann" / "a_p1_c01.xml").write_text("<annotations/>")
    (dv / "preann" / "a_p1_c01.preview.mp4").write_bytes(b"v")
    result = generate_clip(
        raw_dir=dv / "raw", videos_dir=dv, script=tmp_path / "s.sh",
        master_name="P1-a-take1.mp4", t_event=11.0, t_end=25.0,
        clip_id="a_p1_c01",
    )
    assert result["regenerated"] is True
    assert sorted(result["invalidated"]) == [
        "preann/a_p1_c01.preview.mp4", "preann/a_p1_c01.xml",
    ]
    # D9: el XML viejo son cajas de un video que ya no existe.
    assert not (dv / "preann" / "a_p1_c01.xml").exists()
    assert (dv / "preann" / "a_p1_c01.xml.stale").exists()


def test_regenerar_dos_veces_pisa_el_stale(dv, stubs, tmp_path):
    (dv / "preann" / "a_p1_c01.xml").write_text("v1")
    (dv / "preann" / "a_p1_c01.xml.stale").write_text("v0")
    generate_clip(
        raw_dir=dv / "raw", videos_dir=dv, script=tmp_path / "s.sh",
        master_name="P1-a-take1.mp4", t_event=11.0, t_end=25.0,
        clip_id="a_p1_c01",
    )
    assert (dv / "preann" / "a_p1_c01.xml.stale").read_text() == "v1"


def test_material_ajeno_requiere_escenario(dv, stubs, tmp_path):
    (dv / "raw" / "4.1.mp4").write_bytes(b"m")
    with pytest.raises(InvalidRequest):
        generate_clip(
            raw_dir=dv / "raw", videos_dir=dv, script=tmp_path / "s.sh",
            master_name="4.1.mp4", t_event=5.0, t_end=10.0,
        )
    result = generate_clip(
        raw_dir=dv / "raw", videos_dir=dv, script=tmp_path / "s.sh",
        master_name="4.1.mp4", t_event=5.0, t_end=10.0, scenario="P2",
    )
    assert result["clip_id"] == "a_p2_c01"


def test_master_inexistente(dv, stubs, tmp_path):
    with pytest.raises(InvalidRequest):
        generate_clip(
            raw_dir=dv / "raw", videos_dir=dv, script=tmp_path / "s.sh",
            master_name="no-esta.mp4", t_event=5.0, t_end=10.0,
        )


def test_path_traversal_rechazado(dv, stubs, tmp_path):
    with pytest.raises(InvalidRequest):
        generate_clip(
            raw_dir=dv / "raw", videos_dir=dv, script=tmp_path / "s.sh",
            master_name="../../../etc/passwd", t_event=5.0, t_end=10.0,
        )


def test_master_ilegible_propaga_probe_error(dv, stubs, monkeypatch, tmp_path):
    import eovrt_webconsole.clips.generate as gen

    def _explota(path):
        raise ProbeError("no es un video")

    monkeypatch.setattr(gen, "measure", _explota)
    with pytest.raises(ProbeError):
        generate_clip(
            raw_dir=dv / "raw", videos_dir=dv, script=tmp_path / "s.sh",
            master_name="P1-a-take1.mp4", t_event=5.0, t_end=10.0,
        )


def test_marcas_invalidas_propagan(dv, stubs, tmp_path):
    with pytest.raises(InvalidMarks):
        generate_clip(
            raw_dir=dv / "raw", videos_dir=dv, script=tmp_path / "s.sh",
            master_name="P1-a-take1.mp4", t_event=20.0, t_end=10.0,
        )
```

- [ ] **Step 2: Verificar que fallan**

```bash
.venv/bin/python -m pytest tests/test_clip_generate.py -q
```
Esperado: FAIL con `ImportError`.

- [ ] **Step 3: Implementación**

Crear `webconsole/backend/src/eovrt_webconsole/clips/generate.py`:

```python
"""Orquestación: marcas -> ventana -> clip_id -> prepare_clip.sh -> clip.yaml.

Reglas del spec §7 que se implementan acá:
- clip_id explícito = REGENERACIÓN: sobrescribe e invalida la pre-anotación
  vieja (D9) renombrándola a *.stale — el XML viejo son cajas de un video
  que ya no existe.
- Sin clip_id: se toma el siguiente libre (nunca pisa por accidente).
- El master nunca se toca (D8): prepare_clip.sh solo lo lee.
"""

from __future__ import annotations

from pathlib import Path

from eovrt_webconsole.clips.clip_yaml import write_clip_yaml
from eovrt_webconsole.clips.naming import next_clip_id, scenario_from_master
from eovrt_webconsole.clips.trim import run_prepare_clip
from eovrt_webconsole.clips.window import compute_window
from eovrt_webconsole.recording.probe import measure


class InvalidRequest(ValueError):
    pass


def _invalidate_preann(preann_dir: Path, clip_id: str) -> list[str]:
    invalidated = []
    for name in (f"{clip_id}.xml", f"{clip_id}.preview.mp4"):
        path = preann_dir / name
        if path.is_file():
            path.replace(path.with_name(name + ".stale"))
            invalidated.append(f"preann/{name}")
    return invalidated


def generate_clip(
    *,
    raw_dir: Path,
    videos_dir: Path,
    script: Path,
    master_name: str,
    t_event: float,
    t_end: float,
    scenario: str | None = None,
    clip_id: str | None = None,
) -> dict:
    if Path(master_name).name != master_name:
        raise InvalidRequest(f"nombre de master inválido: {master_name!r}")
    master = raw_dir / master_name
    if not master.is_file():
        raise InvalidRequest(f"master inexistente: {master_name}")

    scenario = scenario or scenario_from_master(master_name)
    if scenario is None:
        raise InvalidRequest(
            f"{master_name} no sigue el patrón de toma (P1-a-take2.mp4): "
            "indicá el escenario a mano"
        )

    measured = measure(master)  # ProbeError si el master no es video legible
    window = compute_window(t_event, t_end, measured.duration_ms / 1000.0, scenario)

    regenerated = clip_id is not None
    if clip_id is None:
        clip_id = next_clip_id(videos_dir, scenario)
    invalidated = _invalidate_preann(videos_dir / "preann", clip_id) if regenerated else []

    info = run_prepare_clip(
        script, videos_dir / "clips", master, clip_id,
        ss=window.ss, duration=window.duration,
    )
    write_clip_yaml(videos_dir, clip_id, scenario, master_name, window)

    return {
        "clip_id": clip_id,
        "info": info,
        "warnings": list(window.warnings),
        "regenerated": regenerated,
        "invalidated": invalidated,
    }
```

- [ ] **Step 4: Verificar que pasan**

```bash
.venv/bin/python -m pytest tests/test_clip_generate.py -q && .venv/bin/python -m ruff check src tests
```
Esperado: 9 passed, ruff limpio.

- [ ] **Step 5: Stage**

```bash
git -C /home/simonll4/projects/e-ovrt_experimental-setup add webconsole/backend/src/eovrt_webconsole/clips/generate.py webconsole/backend/tests/test_clip_generate.py
```

---

### Task 8: `routers/clips.py` — REST + video con Range, registro en `app.py`

**Files:**
- Create: `webconsole/backend/src/eovrt_webconsole/routers/clips.py`
- Modify: `webconsole/backend/src/eovrt_webconsole/app.py` (import + `include_router`)
- Test: `webconsole/backend/tests/test_clips_router.py`

**Interfaces:**
- Consumes: todo el paquete `clips/` (T2–T7), `settings.raw_dir`/`videos_dir`/`clips_dir`/`prepare_clip_script` (T1).
- Produces (contrato consumido por el frontend, T9–T11):
  - `GET /api/clips/masters` → `{"masters": [...]}` (shape de `list_masters`).
  - `GET /api/clips` → `{"clips": [...]}` (shape de `list_clips`).
  - `POST /api/clips` body `{"master": str, "t_event_s": float, "t_end_s": float, "scenario"?: str, "clip_id"?: str}` → 201 con el dict de `generate_clip`. Errores: 422 (marcas/escenario/master inválidos, master ilegible), 502 con la salida real del script (`TrimFailed`).
  - `GET /api/clips/media/master/{name}` y `GET /api/clips/media/clip/{clip_id}` → `FileResponse` mp4 (Starlette 1.3 responde 206 a Range nativamente); 404 si no existe o el nombre trae separadores.

- [ ] **Step 1: Tests que fallan**

Crear `webconsole/backend/tests/test_clips_router.py`:

```python
import json
import shutil
import subprocess
from pathlib import Path

import httpx
import pytest
import yaml
from fastapi.testclient import TestClient

from eovrt_webconsole.app import create_app
from eovrt_webconsole.settings import ConsoleSettings
from tests.fake_service import FakeState, make_fake_service

REAL_SCRIPT = (
    Path(__file__).resolve().parents[4]
    / "e-ovrt_datasets" / "datasets" / "scripts" / "videogt" / "prepare_clip.sh"
)

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None
    or shutil.which("ffprobe") is None
    or not REAL_SCRIPT.exists(),
    reason="requiere ffmpeg/ffprobe y el repo e-ovrt_datasets",
)


@pytest.fixture
def dv(tmp_path):
    """Repo datasets falso con la forma que prepare_clip.sh espera."""
    root = tmp_path / "dsrepo"
    dv = root / "datasets-videos"
    (dv / "raw").mkdir(parents=True)
    (dv / "clips").mkdir()
    (dv / "preann").mkdir()
    script = root / "datasets" / "scripts" / "videogt" / "prepare_clip.sh"
    script.parent.mkdir(parents=True)
    shutil.copy(REAL_SCRIPT, script)
    return dv


@pytest.fixture
def master(dv):
    out = dv / "raw" / "P1-a-take1.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
         "-f", "lavfi", "-i", "testsrc=size=320x240:rate=30:duration=20",
         "-c:v", "libx264", "-preset", "ultrafast", str(out)],
        check=True,
    )
    return out


@pytest.fixture
def clips_client(repo: Path, dv, fake_state: FakeState):
    settings = ConsoleSettings(
        service_url="http://service.fake",
        repo_root=repo,
        frozen_set_ids=frozenset(),
        recordings_dir=dv / "raw",
        datasets_videos_dir=dv,
    )
    transport = httpx.ASGITransport(app=make_fake_service(fake_state))
    with TestClient(create_app(settings, service_transport=transport)) as client:
        client.dv = dv
        yield client


def test_lista_de_masters(clips_client, master):
    body = clips_client.get("/api/clips/masters").json()
    [m] = body["masters"]
    assert m["name"] == "P1-a-take1.mp4"
    assert m["scenario"] == "P1"
    assert m["readable"] is True
    assert m["clips"] == []


def test_generar_clip_de_punta_a_punta(clips_client, master):
    creado = clips_client.post(
        "/api/clips",
        json={"master": "P1-a-take1.mp4", "t_event_s": 6.0, "t_end_s": 12.0},
    )
    assert creado.status_code == 201, creado.text
    body = creado.json()
    assert body["clip_id"] == "a_p1_c01"
    # ventana: ss=2.5, duración=(12+3)-2.5=12.5 s a 30 fps
    assert abs(body["info"]["n_frames"] - 375) <= 1
    # advertencia de duración P1 (<20 s), generado igual (D7)
    assert any("20" in w for w in body["warnings"])
    assert (clips_client.dv / "clips" / "a_p1_c01.mp4").exists()
    data = yaml.safe_load((clips_client.dv / "a_p1_c01.clip.yaml").read_text())
    assert data["episode_draft"]["onset_ms"] == 3500
    # y ahora el master figura recortado y el clip listado:
    [m] = clips_client.get("/api/clips/masters").json()["masters"]
    assert m["clips"] == ["a_p1_c01"]
    [c] = clips_client.get("/api/clips").json()["clips"]
    assert c["clip_id"] == "a_p1_c01"


def test_fin_antes_del_evento_da_422(clips_client, master):
    r = clips_client.post(
        "/api/clips",
        json={"master": "P1-a-take1.mp4", "t_event_s": 12.0, "t_end_s": 6.0},
    )
    assert r.status_code == 422
    assert "posterior" in r.json()["detail"]


def test_master_ilegible_da_422_con_motivo(clips_client, dv):
    (dv / "raw" / "P2-a-take1.mp4").write_bytes(b"esto no es un mp4")
    r = clips_client.post(
        "/api/clips",
        json={"master": "P2-a-take1.mp4", "t_event_s": 5.0, "t_end_s": 8.0},
    )
    assert r.status_code == 422


def test_media_master_soporta_range(clips_client, master):
    r = clips_client.get(
        "/api/clips/media/master/P1-a-take1.mp4", headers={"Range": "bytes=0-99"}
    )
    assert r.status_code == 206
    assert len(r.content) == 100
    assert r.headers["content-range"].startswith("bytes 0-99/")


def test_media_clip_tras_generar(clips_client, master):
    clips_client.post(
        "/api/clips",
        json={"master": "P1-a-take1.mp4", "t_event_s": 6.0, "t_end_s": 12.0},
    )
    r = clips_client.get("/api/clips/media/clip/a_p1_c01")
    assert r.status_code == 200
    assert r.headers["content-type"] == "video/mp4"


def test_media_inexistente_y_traversal_dan_404(clips_client):
    assert clips_client.get("/api/clips/media/master/no-esta.mp4").status_code == 404
    assert (
        clips_client.get("/api/clips/media/master/..%2F..%2Fetc%2Fpasswd").status_code
        == 404
    )


def test_payload_invalido_da_422(clips_client, master):
    r = clips_client.post("/api/clips", json={"master": "P1-a-take1.mp4"})
    assert r.status_code == 422
```

Nota: la fixture `repo` viene del conftest existente.

- [ ] **Step 2: Verificar que fallan**

```bash
.venv/bin/python -m pytest tests/test_clips_router.py -q
```
Esperado: FAIL (404 en las rutas — el router no existe).

- [ ] **Step 3: Implementación**

Crear `webconsole/backend/src/eovrt_webconsole/routers/clips.py`:

```python
"""Generación de clips desde la consola (spec 2026-07-21): listas, recorte
y servido de video con HTTP Range para poder arrastrar la línea de tiempo."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel

from eovrt_webconsole.clips import inventory
from eovrt_webconsole.clips.generate import InvalidRequest, generate_clip
from eovrt_webconsole.clips.naming import InvalidScenario
from eovrt_webconsole.clips.trim import TrimFailed
from eovrt_webconsole.clips.window import InvalidMarks
from eovrt_webconsole.recording.probe import ProbeError

router = APIRouter(prefix="/api/clips")


class GenerateClipBody(BaseModel):
    master: str
    t_event_s: float
    t_end_s: float
    scenario: str | None = None
    clip_id: str | None = None


def _settings(request: Request):
    return request.app.state.settings


@router.get("/masters")
def masters(request: Request) -> dict:
    settings = _settings(request)
    return {"masters": inventory.list_masters(settings.raw_dir, settings.videos_dir)}


@router.get("")
def clips(request: Request) -> dict:
    return {"clips": inventory.list_clips(_settings(request).videos_dir)}


@router.post("", status_code=201)
def create_clip(request: Request, body: GenerateClipBody) -> dict:
    settings = _settings(request)
    try:
        return generate_clip(
            raw_dir=settings.raw_dir,
            videos_dir=settings.videos_dir,
            script=settings.prepare_clip_script,
            master_name=body.master,
            t_event=body.t_event_s,
            t_end=body.t_end_s,
            scenario=body.scenario,
            clip_id=body.clip_id,
        )
    except (InvalidRequest, InvalidMarks, InvalidScenario) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ProbeError as exc:
        raise HTTPException(
            status_code=422, detail=f"el master no se puede leer: {exc}"
        ) from exc
    except TrimFailed as exc:
        # La salida REAL de prepare_clip.sh, no un error genérico (spec §7).
        # El master queda intacto: recortar solo lo lee.
        raise HTTPException(status_code=502, detail=str(exc)) from exc


def _serve(base: Path, filename: str) -> FileResponse:
    # El nombre no puede traer separadores: cualquier intento de salirse del
    # directorio es un 404, igual que un archivo inexistente.
    if Path(filename).name != filename:
        raise HTTPException(status_code=404, detail="no encontrado")
    path = base / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="no encontrado")
    # FileResponse (Starlette >=1.x) responde 206 a Range por sí solo: es lo
    # que permite arrastrar la línea de tiempo sin bajar el master entero.
    return FileResponse(path, media_type="video/mp4")


@router.get("/media/master/{name}")
def media_master(request: Request, name: str) -> FileResponse:
    return _serve(_settings(request).raw_dir, name)


@router.get("/media/clip/{clip_id}")
def media_clip(request: Request, clip_id: str) -> FileResponse:
    return _serve(_settings(request).clips_dir, f"{clip_id}.mp4")
```

En `app.py`: agregar `clips` al import de `eovrt_webconsole.routers` (lista alfabética: entre `catalog` y `compare`... queda `cameras, catalog, clips, compare, ...`) y registrar `app.include_router(clips.router)` junto a los demás (después de `cameras.router`).

- [ ] **Step 4: Verificar que pasan + regresión completa**

```bash
.venv/bin/python -m pytest tests/test_clips_router.py -q
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check src tests
```
Esperado: 8 passed en el router; suite completa ≥ 421+38 passed, 0 failed; ruff limpio.

- [ ] **Step 5: Stage**

```bash
git -C /home/simonll4/projects/e-ovrt_experimental-setup add webconsole/backend/src/eovrt_webconsole/routers/clips.py webconsole/backend/src/eovrt_webconsole/app.py webconsole/backend/tests/test_clips_router.py
```

---

### Task 9: Frontend — tipos y cliente API

**Files:**
- Modify: `webconsole/frontend/src/types.ts` (agregar al final)
- Modify: `webconsole/frontend/src/api.ts` (agregar al final)
- Test: `webconsole/frontend/src/api.test.ts` (agregar tests)

**Interfaces:**
- Produces (consumido por T10/T11):

```ts
// types.ts
export interface MasterEntry {
  name: string
  scenario: string | null
  size_bytes: number
  duration_ms: number | null
  readable: boolean
  clips: string[]
}

export interface ClipEntry {
  clip_id: string
  fps: number | null
  duration_ms: number | null
  n_frames: number | null
  resolution: string | null
  has_yaml: boolean
  master: string | null
  warnings: string[]
}

export interface GenerateClipBody {
  master: string
  t_event_s: number
  t_end_s: number
  scenario?: string
  clip_id?: string
}

export interface GenerateClipResult {
  clip_id: string
  info: { fps: number; duration_ms: number; n_frames: number; resolution: string }
  warnings: string[]
  regenerated: boolean
  invalidated: string[]
}
```

```ts
// api.ts
export const getMasters = () => request<{ masters: MasterEntry[] }>('/api/clips/masters')
export const getClips = () => request<{ clips: ClipEntry[] }>('/api/clips')
export const generateClip = (body: GenerateClipBody) =>
  request<GenerateClipResult>('/api/clips', { method: 'POST', body: JSON.stringify(body) })
export const masterMediaUrl = (name: string) =>
  `/api/clips/media/master/${encodeURIComponent(name)}`
export const clipMediaUrl = (clipId: string) =>
  `/api/clips/media/clip/${encodeURIComponent(clipId)}`
```

- [ ] **Step 1: Tests que fallan**

En `webconsole/frontend/src/api.test.ts`, agregar (siguiendo el patrón de mock de `fetch` que ya usa el archivo — leerlo primero y calcar el estilo de sus tests existentes):

```ts
describe('clips api', () => {
  it('getMasters pega al endpoint correcto', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ masters: [] }),
    })
    vi.stubGlobal('fetch', fetchMock)
    await getMasters()
    expect(fetchMock.mock.calls[0][0]).toBe('/api/clips/masters')
  })

  it('generateClip postea las marcas', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ clip_id: 'a_p1_c01', warnings: [] }),
    })
    vi.stubGlobal('fetch', fetchMock)
    await generateClip({ master: 'P1-a-take1.mp4', t_event_s: 6, t_end_s: 12 })
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/clips')
    expect(init.method).toBe('POST')
    expect(JSON.parse(init.body).t_event_s).toBe(6)
  })

  it('media urls escapan el nombre', () => {
    expect(masterMediaUrl('P1-a-take1.mp4')).toBe('/api/clips/media/master/P1-a-take1.mp4')
    expect(clipMediaUrl('a_p1_c01')).toBe('/api/clips/media/clip/a_p1_c01')
  })
})
```

- [ ] **Step 2: Verificar que fallan**

```bash
cd /home/simonll4/projects/e-ovrt_experimental-setup/webconsole/frontend
npx vitest run src/api.test.ts
```
Esperado: FAIL (imports inexistentes).

- [ ] **Step 3: Implementar** los bloques de `types.ts` y `api.ts` de arriba (imports de tipos en `api.ts` según el estilo del archivo).

- [ ] **Step 4: Verificar**

```bash
npx vitest run src/api.test.ts && npx tsc --noEmit
```
Esperado: PASS, tsc limpio.

- [ ] **Step 5: Stage**

```bash
git -C /home/simonll4/projects/e-ovrt_experimental-setup add webconsole/frontend/src/types.ts webconsole/frontend/src/api.ts webconsole/frontend/src/api.test.ts
```

---

### Task 10: `TrimDialog.tsx` — player con las dos marcas

**Files:**
- Create: `webconsole/frontend/src/components/TrimDialog.tsx`
- Test: `webconsole/frontend/src/__tests__/TrimDialog.test.tsx`

**Interfaces:**
- Consumes: `generateClip`, `masterMediaUrl`, tipos (T9); `ApiError` y el patrón `mensajeDeError` de `RecordPanel.tsx`.
- Produces: `export default function TrimDialog({ master, onClose, onGenerated }: { master: MasterEntry; onClose: () => void; onGenerated: () => void })`.

Comportamiento:
- `<video controls src={masterMediaUrl(master.name)} data-testid="trim-video">` con ref.
- Botones **"Marcar evento"** y **"Marcar fin"**: toman `videoRef.current.currentTime` y lo guardan en estado (`tEvent`, `tEnd`); se muestran los valores marcados en segundos con un decimal.
- Si `master.scenario` es `null`, un `<select>` de escenarios `P1..P9` (obligatorio para generar); si no, se muestra el escenario heredado del master.
- Si `master.clips.length > 0`, un `<select>` "Regenerar" con opciones `(nuevo)` + los clip_ids existentes; elegir un clip_id existente manda `clip_id` en el body (regeneración D9) y muestra el aviso fijo: *"Regenerar invalida la pre-anotación vieja de ese clip"*.
- **"Generar clip"**: deshabilitado (prop `disabled`) hasta tener ambas marcas; al click llama `generateClip({...})`; mientras corre muestra "Generando…"; al éxito muestra `clip_id` y las `warnings` devueltas (una lista visible, D7) y llama `onGenerated()`; el diálogo queda abierto mostrando el resultado (el operador decide cerrar).
- Errores: mismo patrón `mensajeDeError` de `RecordPanel.tsx` (el `detail` del backend — p.ej. la salida real de `prepare_clip.sh` — tiene que ser visible, copiar la función tal cual con su comentario).

- [ ] **Step 1: Tests que fallan**

Crear `webconsole/frontend/src/__tests__/TrimDialog.test.tsx`:

```tsx
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import TrimDialog from '../components/TrimDialog'
import type { MasterEntry } from '../types'

vi.mock('../api', async () => {
  const real = await vi.importActual<typeof import('../api')>('../api')
  return { ...real, generateClip: vi.fn() }
})

import { generateClip } from '../api'

const MASTER: MasterEntry = {
  name: 'P1-a-take1.mp4',
  scenario: 'P1',
  size_bytes: 1000,
  duration_ms: 33000,
  readable: true,
  clips: [],
}

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

function marcar(video: HTMLVideoElement, evento: number, fin: number) {
  Object.defineProperty(video, 'currentTime', { value: evento, writable: true })
  fireEvent.click(screen.getByText('Marcar evento'))
  video.currentTime = fin
  fireEvent.click(screen.getByText('Marcar fin'))
}

describe('TrimDialog', () => {
  it('generar queda deshabilitado hasta tener las dos marcas', () => {
    render(<TrimDialog master={MASTER} onClose={() => {}} onGenerated={() => {}} />)
    const boton = screen.getByText('Generar clip') as HTMLButtonElement
    expect(boton.disabled).toBe(true)
  })

  it('las marcas salen del currentTime del video y se postean', async () => {
    vi.mocked(generateClip).mockResolvedValue({
      clip_id: 'a_p1_c01',
      info: { fps: 30, duration_ms: 20500, n_frames: 615, resolution: '1920x1080' },
      warnings: [],
      regenerated: false,
      invalidated: [],
    })
    const onGenerated = vi.fn()
    render(<TrimDialog master={MASTER} onClose={() => {}} onGenerated={onGenerated} />)
    const video = screen.getByTestId('trim-video') as HTMLVideoElement
    marcar(video, 10.5, 24.5)
    fireEvent.click(screen.getByText('Generar clip'))
    await waitFor(() => expect(onGenerated).toHaveBeenCalled())
    expect(vi.mocked(generateClip).mock.calls[0][0]).toEqual({
      master: 'P1-a-take1.mp4',
      t_event_s: 10.5,
      t_end_s: 24.5,
    })
    expect(screen.getByText(/a_p1_c01/)).toBeTruthy()
  })

  it('muestra las advertencias devueltas (D7: avisa fuerte, genera igual)', async () => {
    vi.mocked(generateClip).mockResolvedValue({
      clip_id: 'a_p1_c01',
      info: { fps: 30, duration_ms: 15000, n_frames: 450, resolution: '1920x1080' },
      warnings: ['clip de 15.0 s, el guion pide ~20 s para este escenario'],
      regenerated: false,
      invalidated: [],
    })
    render(<TrimDialog master={MASTER} onClose={() => {}} onGenerated={() => {}} />)
    marcar(screen.getByTestId('trim-video') as HTMLVideoElement, 5, 12)
    fireEvent.click(screen.getByText('Generar clip'))
    await waitFor(() =>
      expect(screen.getByText(/el guion pide ~20 s/)).toBeTruthy(),
    )
  })

  it('muestra el detail real del backend cuando falla', async () => {
    const { ApiError } = await vi.importActual<typeof import('../api')>('../api')
    vi.mocked(generateClip).mockRejectedValue(
      new ApiError(502, { detail: 'ffmpeg: fuente.mp4: No such file or directory' }),
    )
    render(<TrimDialog master={MASTER} onClose={() => {}} onGenerated={() => {}} />)
    marcar(screen.getByTestId('trim-video') as HTMLVideoElement, 5, 12)
    fireEvent.click(screen.getByText('Generar clip'))
    await waitFor(() =>
      expect(screen.getByText(/No such file or directory/)).toBeTruthy(),
    )
  })

  it('material ajeno exige elegir escenario', () => {
    render(
      <TrimDialog
        master={{ ...MASTER, name: '4.1.mp4', scenario: null }}
        onClose={() => {}}
        onGenerated={() => {}}
      />,
    )
    expect(screen.getByLabelText('Escenario')).toBeTruthy()
  })

  it('un master con clips ofrece regenerar y avisa por la pre-anotación', () => {
    render(
      <TrimDialog
        master={{ ...MASTER, clips: ['a_p1_c01'] }}
        onClose={() => {}}
        onGenerated={() => {}}
      />,
    )
    const select = screen.getByLabelText('Regenerar') as HTMLSelectElement
    fireEvent.change(select, { target: { value: 'a_p1_c01' } })
    expect(screen.getByText(/invalida la pre-anotación/)).toBeTruthy()
  })
})
```

Nota sobre la firma de `ApiError`: verificar en `api.ts` (líneas ~8-15) si el constructor es `new ApiError(status, payload)`; si difiere, ajustar el test al constructor real.

- [ ] **Step 2: Verificar que fallan**

```bash
npx vitest run src/__tests__/TrimDialog.test.tsx
```
Esperado: FAIL (el componente no existe).

- [ ] **Step 3: Implementar `TrimDialog.tsx`**

```tsx
import { useRef, useState } from 'react'

import { ApiError, generateClip, masterMediaUrl } from '../api'
import type { GenerateClipResult, MasterEntry } from '../types'

const SCENARIOS = ['P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7', 'P8', 'P9']

/** Mismo patrón que RecordPanel: el motivo real del backend viaja en
 * payload.detail (p. ej. la salida completa de prepare_clip.sh). */
function mensajeDeError(e: unknown): string {
  if (e instanceof ApiError) {
    const payload = (e.payload ?? {}) as { detail?: unknown }
    if (typeof payload.detail === 'string') return payload.detail
    if (payload.detail != null) return JSON.stringify(payload.detail)
    return e.message
  }
  return e instanceof Error ? e.message : String(e)
}

export default function TrimDialog({
  master,
  onClose,
  onGenerated,
}: {
  master: MasterEntry
  onClose: () => void
  onGenerated: () => void
}) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const [tEvent, setTEvent] = useState<number | null>(null)
  const [tEnd, setTEnd] = useState<number | null>(null)
  const [scenario, setScenario] = useState(master.scenario ?? '')
  const [regenerate, setRegenerate] = useState('')
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<GenerateClipResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  const listo = tEvent != null && tEnd != null && scenario !== '' && !busy

  const generar = async () => {
    if (tEvent == null || tEnd == null) return
    setBusy(true)
    setError(null)
    setResult(null)
    try {
      const body = {
        master: master.name,
        t_event_s: tEvent,
        t_end_s: tEnd,
        ...(master.scenario == null ? { scenario } : {}),
        ...(regenerate !== '' ? { clip_id: regenerate } : {}),
      }
      const r = await generateClip(body)
      setResult(r)
      onGenerated()
    } catch (e: unknown) {
      setError(mensajeDeError(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      <h3>Recortar {master.name}</h3>
      <video
        ref={videoRef}
        controls
        src={masterMediaUrl(master.name)}
        data-testid="trim-video"
        style={{ maxWidth: '100%' }}
      />
      <div>
        <button onClick={() => setTEvent(videoRef.current?.currentTime ?? 0)}>
          Marcar evento
        </button>
        <span>{tEvent != null ? `${tEvent.toFixed(1)} s` : 'sin marcar'}</span>
        <button onClick={() => setTEnd(videoRef.current?.currentTime ?? 0)}>
          Marcar fin
        </button>
        <span>{tEnd != null ? `${tEnd.toFixed(1)} s` : 'sin marcar'}</span>
      </div>
      {master.scenario == null ? (
        <label>
          Escenario
          <select value={scenario} onChange={(e) => setScenario(e.target.value)}>
            <option value="">elegir…</option>
            {SCENARIOS.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </label>
      ) : (
        <p>Escenario {master.scenario} (heredado del master)</p>
      )}
      {master.clips.length > 0 && (
        <label>
          Regenerar
          <select value={regenerate} onChange={(e) => setRegenerate(e.target.value)}>
            <option value="">(nuevo)</option>
            {master.clips.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </label>
      )}
      {regenerate !== '' && (
        <p>Regenerar invalida la pre-anotación vieja de ese clip.</p>
      )}
      <button onClick={generar} disabled={!listo}>
        {busy ? 'Generando…' : 'Generar clip'}
      </button>
      <button onClick={onClose}>Cerrar</button>
      {result && (
        <div>
          <p>✓ {result.clip_id} generado ({result.info.n_frames} frames)</p>
          {result.warnings.length > 0 && (
            <ul>
              {result.warnings.map((w) => (
                <li key={w}>⚠ {w}</li>
              ))}
            </ul>
          )}
        </div>
      )}
      {error && <p role="alert">{error}</p>}
    </div>
  )
}
```

Ajustar presentación al estilo/las clases de los componentes vecinos (`RecordPanel.tsx`, `ui/Card.tsx`, `ui/ErrorBanner.tsx`) — la estructura y los textos de los tests son el contrato, el estilo es libre.

- [ ] **Step 4: Verificar**

```bash
npx vitest run src/__tests__/TrimDialog.test.tsx && npx tsc --noEmit
```
Esperado: 6 passed, tsc limpio.

- [ ] **Step 5: Stage**

```bash
git -C /home/simonll4/projects/e-ovrt_experimental-setup add webconsole/frontend/src/components/TrimDialog.tsx webconsole/frontend/src/__tests__/TrimDialog.test.tsx
```

---

### Task 11: `ClipsPage.tsx` — listas, ruta y nav

**Files:**
- Create: `webconsole/frontend/src/pages/ClipsPage.tsx`
- Modify: `webconsole/frontend/src/App.tsx` (ruta `/clips`)
- Modify: `webconsole/frontend/src/nav.ts` (item en grupo Sistema)
- Test: `webconsole/frontend/src/__tests__/ClipsPage.test.tsx`

**Interfaces:**
- Consumes: `getMasters`, `getClips`, `clipMediaUrl` (T9), `TrimDialog` (T10).

Comportamiento:
- Carga masters y clips al montar; recarga ambas listas cuando `TrimDialog` dispara `onGenerated`.
- **Masters**: nombre, escenario (o "—"), duración en s, estado: "sin recortar" / los clip_ids generados / "ilegible" si `readable === false`. Botón "Recortar" abre `TrimDialog` (deshabilitado si ilegible).
- **Clips generados**: clip_id, duración, resolución, ⚠ si `warnings.length > 0`. Click en un clip muestra `<video controls src={clipMediaUrl(id)}>` para verificarlo.
- Listas vacías → mensaje simple (usar `ui/EmptyState` si el patrón de las otras páginas lo usa).

- [ ] **Step 1: Tests que fallan**

Crear `webconsole/frontend/src/__tests__/ClipsPage.test.tsx`:

```tsx
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import ClipsPage from '../pages/ClipsPage'

vi.mock('../api', async () => {
  const real = await vi.importActual<typeof import('../api')>('../api')
  return { ...real, getMasters: vi.fn(), getClips: vi.fn() }
})

import { getClips, getMasters } from '../api'

const MASTERS = [
  {
    name: 'P1-a-take1.mp4', scenario: 'P1', size_bytes: 1000,
    duration_ms: 33000, readable: true, clips: [],
  },
  {
    name: 'P2-a-take1.mp4', scenario: 'P2', size_bytes: 1000,
    duration_ms: null, readable: false, clips: [],
  },
]
const CLIPS = [
  {
    clip_id: 'a_p1_c01', fps: 30, duration_ms: 20500, n_frames: 615,
    resolution: '1920x1080', has_yaml: true, master: 'raw/P1-a-take1.mp4',
    warnings: ['solo 2.0 s de cola, se necesitan 3'],
  },
]

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe('ClipsPage', () => {
  it('lista masters y clips', async () => {
    vi.mocked(getMasters).mockResolvedValue({ masters: MASTERS })
    vi.mocked(getClips).mockResolvedValue({ clips: CLIPS })
    render(<ClipsPage />)
    await waitFor(() => expect(screen.getByText('P1-a-take1.mp4')).toBeTruthy())
    expect(screen.getByText('a_p1_c01')).toBeTruthy()
  })

  it('el master ilegible queda marcado y sin botón de recorte habilitado', async () => {
    vi.mocked(getMasters).mockResolvedValue({ masters: MASTERS })
    vi.mocked(getClips).mockResolvedValue({ clips: [] })
    render(<ClipsPage />)
    await waitFor(() => expect(screen.getByText(/ilegible/)).toBeTruthy())
    const botones = screen.getAllByText('Recortar') as HTMLButtonElement[]
    expect(botones[1].disabled).toBe(true)
  })

  it('recortar abre el TrimDialog con el master elegido', async () => {
    vi.mocked(getMasters).mockResolvedValue({ masters: MASTERS })
    vi.mocked(getClips).mockResolvedValue({ clips: [] })
    render(<ClipsPage />)
    await waitFor(() => expect(screen.getByText('P1-a-take1.mp4')).toBeTruthy())
    fireEvent.click((screen.getAllByText('Recortar') as HTMLButtonElement[])[0])
    expect(screen.getByText(/Recortar P1-a-take1.mp4/)).toBeTruthy()
  })

  it('un clip con advertencias las señala', async () => {
    vi.mocked(getMasters).mockResolvedValue({ masters: [] })
    vi.mocked(getClips).mockResolvedValue({ clips: CLIPS })
    render(<ClipsPage />)
    await waitFor(() => expect(screen.getByText('a_p1_c01')).toBeTruthy())
    expect(screen.getByText(/solo 2.0 s de cola/)).toBeTruthy()
  })

  it('listas vacías no rompen', async () => {
    vi.mocked(getMasters).mockResolvedValue({ masters: [] })
    vi.mocked(getClips).mockResolvedValue({ clips: [] })
    render(<ClipsPage />)
    await waitFor(() => expect(getMasters).toHaveBeenCalled())
  })
})
```

- [ ] **Step 2: Verificar que fallan**

```bash
npx vitest run src/__tests__/ClipsPage.test.tsx
```
Esperado: FAIL (la página no existe).

- [ ] **Step 3: Implementar**

`ClipsPage.tsx` (estructura; estilo según las páginas vecinas):

```tsx
import { useCallback, useEffect, useState } from 'react'

import { clipMediaUrl, getClips, getMasters } from '../api'
import TrimDialog from '../components/TrimDialog'
import type { ClipEntry, MasterEntry } from '../types'

export default function ClipsPage() {
  const [masters, setMasters] = useState<MasterEntry[]>([])
  const [clips, setClips] = useState<ClipEntry[]>([])
  const [abierto, setAbierto] = useState<MasterEntry | null>(null)
  const [reproduciendo, setReproduciendo] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const recargar = useCallback(() => {
    getMasters()
      .then((r) => setMasters(r.masters))
      .catch((e: unknown) => setError(e instanceof Error ? e.message : String(e)))
    getClips()
      .then((r) => setClips(r.clips))
      .catch((e: unknown) => setError(e instanceof Error ? e.message : String(e)))
  }, [])

  useEffect(() => {
    recargar()
  }, [recargar])

  return (
    <div>
      <h2>Clips</h2>
      <section>
        <h3>Masters</h3>
        {masters.length === 0 && <p>No hay masters en raw/.</p>}
        <ul>
          {masters.map((m) => (
            <li key={m.name}>
              <span>{m.name}</span>
              <span>{m.scenario ?? '—'}</span>
              <span>{m.duration_ms != null ? `${(m.duration_ms / 1000).toFixed(1)} s` : ''}</span>
              <span>
                {!m.readable
                  ? 'ilegible'
                  : m.clips.length > 0
                    ? m.clips.join(', ')
                    : 'sin recortar'}
              </span>
              <button disabled={!m.readable} onClick={() => setAbierto(m)}>
                Recortar
              </button>
            </li>
          ))}
        </ul>
      </section>
      <section>
        <h3>Clips generados</h3>
        {clips.length === 0 && <p>Todavía no hay clips.</p>}
        <ul>
          {clips.map((c) => (
            <li key={c.clip_id}>
              <button onClick={() => setReproduciendo(c.clip_id)}>{c.clip_id}</button>
              <span>{c.duration_ms != null ? `${(c.duration_ms / 1000).toFixed(1)} s` : ''}</span>
              <span>{c.resolution}</span>
              {c.warnings.map((w) => (
                <span key={w}>⚠ {w}</span>
              ))}
            </li>
          ))}
        </ul>
        {reproduciendo && (
          <video controls src={clipMediaUrl(reproduciendo)} style={{ maxWidth: '100%' }} />
        )}
      </section>
      {abierto && (
        <TrimDialog
          master={abierto}
          onClose={() => setAbierto(null)}
          onGenerated={recargar}
        />
      )}
      {error && <p role="alert">{error}</p>}
    </div>
  )
}
```

`App.tsx`: import de `ClipsPage` + `<Route path="/clips" element={<ClipsPage />} />` después de `/cameras`.

`nav.ts`: en el grupo `Sistema`, después de Cámaras:

```ts
      { to: '/clips', label: 'Clips' },
```

- [ ] **Step 4: Verificar + suite frontend completa**

```bash
npx vitest run && npx tsc --noEmit && npm run build
```
Esperado: suite completa ≥ 165+14 passed, 0 failed; tsc limpio; build OK.

- [ ] **Step 5: Stage**

```bash
git -C /home/simonll4/projects/e-ovrt_experimental-setup add webconsole/frontend/src/pages/ClipsPage.tsx webconsole/frontend/src/__tests__/ClipsPage.test.tsx webconsole/frontend/src/App.tsx webconsole/frontend/src/nav.ts
```

---

### Task 12: Validación final integrada

**Files:** ninguno nuevo (solo verificación; arreglos si algo falla).

- [ ] **Step 1: Backend completo**

```bash
cd /home/simonll4/projects/e-ovrt_experimental-setup/webconsole/backend
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check src tests
```
Esperado: 0 failed (≈460+ passed), ruff limpio.

- [ ] **Step 2: Frontend completo**

```bash
cd /home/simonll4/projects/e-ovrt_experimental-setup/webconsole/frontend
npx vitest run && npx tsc --noEmit && npm run build
```
Esperado: 0 failed (≈180 passed), tsc limpio, build OK.

- [ ] **Step 3: Humo manual del criterio de aceptación (spec §8)**

Con un master sintético en un datasets-videos temporal, ejercitar el camino REAL de punta a punta (sin stubs), imitando `test_generar_clip_de_punta_a_punta` pero a mano contra el server levantado:

```bash
# en un shell: levantar el backend apuntando a un dv temporal
cd /home/simonll4/projects/e-ovrt_experimental-setup/webconsole/backend
DV=$(mktemp -d)/dsrepo
mkdir -p "$DV/datasets-videos/raw" "$DV/datasets-videos/clips" "$DV/datasets/scripts/videogt"
cp /home/simonll4/projects/e-ovrt_datasets/datasets/scripts/videogt/prepare_clip.sh "$DV/datasets/scripts/videogt/"
ffmpeg -y -hide_banner -loglevel error -f lavfi -i testsrc=size=640x360:rate=30:duration=33 \
  -c:v libx264 -preset ultrafast "$DV/datasets-videos/raw/P1-a-take1.mp4"
EOVRT_CONSOLE_REPO_ROOT=/home/simonll4/projects/e-ovrt_experimental-setup \
EOVRT_CONSOLE_RECORDINGS_DIR="$DV/datasets-videos/raw" \
EOVRT_CONSOLE_DATASETS_VIDEOS_DIR="$DV/datasets-videos" \
.venv/bin/python -m uvicorn --factory eovrt_webconsole.app:create_app --port 8090 &
sleep 3
curl -s -X POST localhost:8090/api/clips \
  -H 'Content-Type: application/json' \
  -d '{"master":"P1-a-take1.mp4","t_event_s":10.5,"t_end_s":24.5}' | python3 -m json.tool
# esperado: clip_id a_p1_c01, n_frames ≈ 615 (20.5 s × 30 fps), warnings []
curl -s -o /dev/null -w '%{http_code}\n' -H 'Range: bytes=0-99' \
  localhost:8090/api/clips/media/clip/a_p1_c01     # esperado: 206
cat "$DV/datasets-videos/a_p1_c01.clip.yaml"        # esperado: onset_ms 3500
kill %1
```

- [ ] **Step 4: Reportar** el estado final (tests, humo) al usuario. **No commitear** — avisar que el trabajo queda staged/intent-to-add y listo para revisión.

---

## Self-review (hecho al escribir el plan)

- **Cobertura del spec**: §2 alcance (solo listas+recorte+visualización — sin pre-anotación ni colas: no hay tareas para eso, deliberado); §4.1 unidades → Tasks 2–8 (window/naming/inventory/trim/clip_yaml/generate/router), §4.2 Range → Task 8 (FileResponse nativo, test 206); §5.1 cálculo → Task 2; §5.2 YAML → Task 4 (contrato real contra `load_clip_meta`); §5.3 advertencias → Tasks 2/4/8/10; §7 errores → fila por fila: fin<evento (T2/T8), fallo del script con salida real (T6/T8/T10), master ilegible (T5/T7/T8), id ocupado→siguiente libre (T3), regeneración invalida preann (T7), dirs inexistentes→lista vacía (T5). D1–D9 todas mapeadas; D8 verificado con test explícito (master intacto, T6).
- **Decisión de diseño no explícita en el spec**: el mapeo master→clip se persiste en el campo extra `master:` del `.clip.yaml` (tolerado por `derive_clip_gt`, verificado). Sin eso el inventario no puede derivar "sin recortar".
- **Fuera del spec, anotado para el Tramo 3**: el refuerzo del guion (cantar el evento en voz alta) es un cambio en `docs/`, no de esta implementación.
- **Tipos consistentes**: `TrimWindow` (T2) fluye a T4/T7; shapes de `list_masters`/`list_clips` (T5) = respuesta del router (T8) = tipos TS (T9) = props (T10/T11). `t_event_s`/`t_end_s` en el body REST en todos lados.
- **Sin placeholders**: cada paso tiene código o comando completo; los dos puntos donde el implementador debe adaptar (helpers reales de `test_settings.py`, firma real de `ApiError`) están señalados explícitamente como verificación, no como TBD.
