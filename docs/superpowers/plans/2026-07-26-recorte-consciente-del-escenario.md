# Recorte consciente del escenario — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** hacer que el recorte de clips de la consola (`webconsole/backend/.../clips/`)
use el escenario del master para decidir cola, chequeo de piso de censura, número de
marcas y fórmula de ventana — en vez de tratar a los 9 escenarios casi igual.

**Architecture:** tres cambios secuenciales, cada uno testeable y commiteable por
separado: (1) piso de censura universal + cola por escenario dentro de
`compute_window()`, sin tocar la forma de `TrimWindow`; (2) reshape de `TrimWindow` a
una lista de episodios + `compute_window_multi()` para P6/P8, alcanzable solo por
`generate_clip()`/API en este punto; (3) migración del contrato del endpoint a
`marks: list[float]` y UI dinámica en `TrimDialog.tsx`.

**Tech Stack:** Python 3.11 (FastAPI, pydantic, pyyaml) en el backend; React+TypeScript
+ Vitest en el frontend. Sin dependencias nuevas.

## Global Constraints

- **Ningún test nuevo o modificado lee ni escribe los masters reales del rodaje.** Los
  tests de `window.py`/`generate.py`/`clip_yaml.py` ya mockean `measure()` y
  `run_prepare_clip()` (ver `tests/test_clip_generate.py`) — seguí ese mismo patrón,
  no generes ni necesites video real ahí. Los tests que sí tocan ffmpeg real
  (`tests/test_clips_router.py`, `tests/test_clip_trim.py`) generan su propio video
  descartable con `ffmpeg -f lavfi -i testsrc=...` en `tmp_path` y están marcados
  `skipif` cuando ffmpeg/e-ovrt_datasets no están disponibles — no cambies ese patrón,
  solo actualizá las aserciones que dependan de la forma nueva de `episode_draft`.
- **No hace falta worktree.** Se trabaja directo en el checkout principal de
  `e-ovrt_experimental-setup`. No toques ni hagas `git add` de nada fuera de los
  archivos que listan las tareas de este plan (el repo tiene otro trabajo sin
  commitear en curso).
- **Nunca commitear salvo que el paso de la tarea lo pida explícitamente** — cada
  tarea tiene su propio paso de commit; no hay commit fuera de esos pasos.
- Backend tests: `cd webconsole/backend && .venv/bin/python -m pytest -q <path> -v`.
  Frontend tests: `cd webconsole/frontend && npx vitest run <path>`.
- Los valores de `DIMENSIONING_MS` (t_alert_upper_ms/resolve_ms por condición) son un
  espejo exacto de `e-ovrt_datasets/datasets/scripts/videogt/derive_clip_gt.py` —
  mantené el comentario de sincronía cuando los toques.
- Formato de escenario: `P1`..`P9` (regex ya existente `SCENARIO_RE` en
  `clips/naming.py`). Condición: `"CR-01"` o `"CR-02"` (strings exactos, ya usados en
  `derive_clip_gt.py` y en el resto del laboratorio).

---

### Task 1: Piso universal + cola por escenario en `compute_window()`

**Files:**
- Modify: `webconsole/backend/src/eovrt_webconsole/clips/window.py`
- Test: `webconsole/backend/tests/test_clip_window.py`

**Interfaces:**
- Produces: `SCENARIO_TAIL_S: dict[str, float]`, `DEFAULT_TAIL_S: float`,
  `SCENARIO_CONDITION: dict[str, str | None]`, `DIMENSIONING_MS: dict[str, dict]`,
  `DIMENSIONING_TAIL_S: float`, `piso_s(scenario: str) -> float | None`.
  `compute_window()` mantiene su firma y forma de retorno actuales en esta tarea
  (`TrimWindow` con `onset_ms`/`end_ms` planos) — el reshape a `episodes` es la Tarea 2.

- [ ] **Step 1: Escribir los tests que fallan**

Reemplazar `test_escenario_sin_objetivo_no_inventa_advertencia` (los valores viejos
asumían cola fija de 3 s; P4 ahora tiene cola de 10 s) y agregar los casos nuevos.
Editar `webconsole/backend/tests/test_clip_window.py`: reemplazar el test existente
`test_escenario_sin_objetivo_no_inventa_advertencia` por este bloque y agregar las
funciones nuevas al final del archivo:

```python
def test_escenario_sin_objetivo_no_inventa_advertencia_de_guion():
    # P4 no tiene "objetivo de guion" en SCENARIO_TARGET_S, pero SÍ tiene cola de
    # 10 s y piso de censura (CR-01, 17.5 s) — con margen, ningún warning.
    w = compute_window(10.0, 20.0, 60.0, "P4")
    assert w.ss == 6.5                 # 10.0 - 3.5
    assert w.duration == 23.5          # (20.0 + 10.0) - 6.5
    assert w.warnings == []


def test_piso_s_por_condicion():
    from eovrt_webconsole.clips.window import piso_s
    assert piso_s("P1") == 17.5   # CR-01: 3.5 + 10.0 + 2.0 + 2.0
    assert piso_s("P2") == 28.5   # CR-02: 3.5 + 20.0 + 3.0 + 2.0
    assert piso_s("P4") == 17.5   # CR-01, misma condición que P1
    assert piso_s("P7") == 17.5   # CR-01
    assert piso_s("P9") == 17.5   # CR-01
    assert piso_s("P3") is None   # sin episodio: sub-umbral
    assert piso_s("P5") is None   # sin episodio: negativo


def test_p1_por_debajo_del_piso_avisa_censura():
    # Evento de 8 s: D = 8 + 6.5 = 14.5 s, por debajo del piso de 17.5 s.
    w = compute_window(10.0, 18.0, 60.0, "P1")
    assert any("piso" in msg and "censur" in msg for msg in w.warnings)


def test_p1_sobre_el_piso_pero_bajo_el_objetivo_solo_avisa_objetivo():
    # D = 18.5 s: por encima del piso (17.5) pero por debajo del objetivo (20).
    w = compute_window(10.0, 22.0, 60.0, "P1")
    assert not any("piso" in msg and "censur" in msg for msg in w.warnings)
    assert any("20" in msg for msg in w.warnings)


def test_p1_sobre_ambos_no_avisa_nada():
    w = compute_window(10.5, 24.5, 33.0, "P1")
    assert w.warnings == []


def test_p3_p5_nunca_avisan_censura_aunque_el_clip_sea_muy_corto():
    # Sin condición (P3, P5) no hay piso: solo puede avisar el objetivo de guion.
    w3 = compute_window(5.0, 6.0, 60.0, "P3")
    assert not any("censur" in msg for msg in w3.warnings)
    w5 = compute_window(5.0, 6.0, 60.0, "P5")
    assert not any("censur" in msg for msg in w5.warnings)


def test_p2_usa_cola_de_cinco_segundos():
    w = compute_window(10.0, 20.0, 60.0, "P2")
    assert w.duration == 16.5   # (20.0 + 5.0) - 6.5, no (20.0 + 3.0) - 6.5


def test_p7_y_p9_tambien_avisan_censura_sin_objetivo_cargado():
    # P7/P9 no tienen "objetivo de guion" en SCENARIO_TARGET_S salvo P9 (18 s);
    # ambos SÍ tienen que avisar el piso si el clip queda corto.
    w7 = compute_window(10.0, 15.0, 60.0, "P7")   # D = 5+6.5 = 11.5 < 17.5
    assert any("piso" in msg and "censur" in msg for msg in w7.warnings)
    w9 = compute_window(10.0, 15.0, 60.0, "P9")   # D = 5+6.5 = 11.5 < 17.5
    assert any("piso" in msg and "censur" in msg for msg in w9.warnings)
```

- [ ] **Step 2: Correr los tests para verificar que fallan**

Run: `cd webconsole/backend && .venv/bin/python -m pytest tests/test_clip_window.py -v`
Expected: FAIL — `piso_s` no existe, y `test_escenario_sin_objetivo_no_inventa_advertencia_de_guion`
da una duración distinta a la esperada (todavía usa cola fija de 3 s).

- [ ] **Step 3: Implementar en `window.py`**

Reemplazar las líneas 17-19 (`PRE_ROLL_S`/`TAIL_S`) por:

```python
# Constantes del guion de rodaje (segundos)
PRE_ROLL_S = 3.5

# Cola por escenario (segundos). Default 3,0; los que necesitan cola larga
# están acá (doc operacion/72 §4.2 P2, §4.4 P4).
SCENARIO_TAIL_S: dict[str, float] = {
    "P2": 5.0,
    "P4": 10.0,
}
DEFAULT_TAIL_S = 3.0

# Condición de cada escenario de 1 episodio, o None si no hay episodio
# (P3 = transitorio sub-umbral, P5 = negativo). Usado para calcular el piso
# de censura (doc operacion/72 §1).
SCENARIO_CONDITION: dict[str, str | None] = {
    "P1": "CR-01",
    "P2": "CR-02",
    "P3": None,
    "P4": "CR-01",
    "P5": None,
    "P7": "CR-01",
    "P9": "CR-01",
}

# Espejo de DIMENSIONING_MS en
# e-ovrt_datasets/datasets/scripts/videogt/derive_clip_gt.py (verificado
# 2026-07-26). Si esos valores cambian ahí, tienen que cambiar acá — no hay
# import cross-repo posible entre los dos servicios en runtime.
DIMENSIONING_MS = {
    "CR-01": {"t_alert_upper_ms": 10000, "resolve_ms": 2000},
    "CR-02": {"t_alert_upper_ms": 20000, "resolve_ms": 3000},
}
DIMENSIONING_TAIL_S = 2.0
```

Agregar la función `piso_s`, después de la clase `TrimWindow` y antes de
`compute_window`:

```python
def piso_s(scenario: str) -> float | None:
    """Piso A1 (segundos de duración mínima) para un escenario de 1 episodio.

    None si el escenario no tiene episodio (P3, P5) — no hay piso que censurar.
    Asume onset_rel == PRE_ROLL_S, válido para los 7 escenarios de 1 episodio
    (ss siempre se calcula como marca_evento - PRE_ROLL_S, salvo pre-roll
    degradado, que ya de por sí hace el clip más corto que el piso nominal).
    """
    condition = SCENARIO_CONDITION.get(scenario)
    if condition is None:
        return None
    dim = DIMENSIONING_MS[condition]
    return (
        PRE_ROLL_S
        + dim["t_alert_upper_ms"] / 1000
        + dim["resolve_ms"] / 1000
        + DIMENSIONING_TAIL_S
    )
```

Dentro de `compute_window`, reemplazar:

```python
    # Cálculo del fin: end más tail
    end_clip = t_end + TAIL_S
    if end_clip > master_duration:
        cola = max(master_duration - t_end, 0.0)
        warnings.append(f"solo {cola:.1f} s de cola, se necesitan {TAIL_S:g}")
        end_clip = master_duration
```

por:

```python
    # Cálculo del fin: end más cola (por escenario, default 3,0 s)
    tail = SCENARIO_TAIL_S.get(scenario, DEFAULT_TAIL_S)
    end_clip = t_end + tail
    if end_clip > master_duration:
        cola = max(master_duration - t_end, 0.0)
        warnings.append(f"solo {cola:.1f} s de cola, se necesitan {tail:g}")
        end_clip = master_duration
```

Y, inmediatamente después del bloque existente de `SCENARIO_TARGET_S` (el que
genera el warning "el guion pide ~X s"), agregar el chequeo de piso:

```python
    # Piso de censura (gate A1): universal para todo escenario con condición,
    # no solo los 5 que tenían objetivo de guion cargado.
    floor = piso_s(scenario)
    if floor is not None and duration < floor:
        warnings.append(
            f"clip de {duration:.1f} s, el piso de censura pide {floor:g} s "
            f"para este episodio — por debajo, t_alert-system/recall quedan "
            f"censurados (doc 57 §6.7)"
        )
```

- [ ] **Step 4: Correr los tests para verificar que pasan**

Run: `cd webconsole/backend && .venv/bin/python -m pytest tests/test_clip_window.py -v`
Expected: PASS (todos, incluidos los ya existentes que no se tocaron:
`test_caso_nominal_p1`, `test_pre_roll_corto_arranca_en_cero_y_avisa`,
`test_cola_corta_recorta_al_master_y_avisa`, `test_clip_bajo_el_objetivo_del_escenario_avisa`,
`test_fin_antes_del_evento_se_rechaza`, `test_fin_igual_al_evento_se_rechaza`,
`test_marcas_fuera_del_master_se_rechazan`).

- [ ] **Step 5: Commit**

```bash
git add webconsole/backend/src/eovrt_webconsole/clips/window.py \
        webconsole/backend/tests/test_clip_window.py
git commit -m "feat: piso de censura universal y cola por escenario en compute_window"
```

---

### Task 2: Reshape de `TrimWindow` a lista de episodios

**Files:**
- Modify: `webconsole/backend/src/eovrt_webconsole/clips/window.py`
- Modify: `webconsole/backend/src/eovrt_webconsole/clips/clip_yaml.py`
- Test: `webconsole/backend/tests/test_clip_window.py`
- Test: `webconsole/backend/tests/test_clip_yaml.py`
- Test: `webconsole/backend/tests/test_clip_generate.py` (solo la aserción de forma)
- Test: `webconsole/backend/tests/test_clips_router.py` (solo la aserción de forma)

**Interfaces:**
- Consumes: `compute_window()` de la Tarea 1 (misma lógica interna, cambia solo qué
  campos expone `TrimWindow`).
- Produces: `EpisodeDraft` (dataclass: `onset_ms: int`, `end_ms: int`,
  `condition: str`), `TrimWindow.episodes: list[EpisodeDraft]` (reemplaza
  `onset_ms`/`end_ms` planos). `write_clip_yaml()` escribe
  `episode_draft` como **lista** de dicts (antes: un único dict).

Este es un cambio de forma puro — ninguna lógica de `compute_window` cambia, solo
cómo empaqueta su resultado.

- [ ] **Step 1: Escribir los tests que fallan**

En `test_clip_window.py`, todos los tests que acceden a `w.onset_ms`/`w.end_ms`
pasan a acceder a `w.episodes[0].onset_ms`/`w.episodes[0].end_ms`. Reemplazar esas
líneas en los tests existentes:

```python
# en test_caso_nominal_p1:
    assert w.episodes[0].onset_ms == 3500
    assert w.episodes[0].end_ms == 17500
    assert w.episodes[0].condition == "CR-01"

# en test_pre_roll_corto_arranca_en_cero_y_avisa:
    assert w.episodes[0].onset_ms == 2000
```

Y agregar, al final del archivo:

```python
def test_episodes_de_un_escenario_sin_condicion_llevan_none():
    w = compute_window(5.0, 6.0, 60.0, "P3")
    assert w.episodes[0].condition is None
```

En `test_clip_yaml.py`, reemplazar la fixture `VENTANA` y los tests que la usan:

```python
from eovrt_webconsole.clips.window import EpisodeDraft, TrimWindow

VENTANA = TrimWindow(
    ss=7.0, duration=20.5,
    episodes=[EpisodeDraft(onset_ms=3500, end_ms=17500, condition="CR-01")],
    warnings=[],
)


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
    assert data["episode_draft"] == [
        {"onset_ms": 3500, "end_ms": 17500, "condition": "CR-01"},
    ]


def test_las_advertencias_quedan_registradas(tmp_path):
    ventana = TrimWindow(
        ss=0.0, duration=18.0,
        episodes=[EpisodeDraft(onset_ms=2000, end_ms=15000, condition="CR-01")],
        warnings=["solo 2.0 s de pre-roll, se necesitan 3.5 — el TTFD va a salir degradado"],
    )
    path = write_clip_yaml(tmp_path, "a_p1_c02", "P1", "P1-a-take3.mp4", ventana)
    data = yaml.safe_load(path.read_text())
    assert data["warnings"] == ventana.warnings


def test_regenerar_sobrescribe(tmp_path):
    write_clip_yaml(tmp_path, "a_p1_c01", "P1", "P1-a-take2.mp4", VENTANA)
    nueva = TrimWindow(
        ss=8.0, duration=19.0,
        episodes=[EpisodeDraft(onset_ms=3500, end_ms=16000, condition="CR-01")],
        warnings=[],
    )
    write_clip_yaml(tmp_path, "a_p1_c01", "P1", "P1-a-take2.mp4", nueva)
    data = yaml.safe_load((tmp_path / "a_p1_c01.clip.yaml").read_text())
    assert data["episode_draft"][0]["end_ms"] == 16000


def test_dos_episodios_se_escriben_como_lista_de_dos(tmp_path):
    ventana = TrimWindow(
        ss=3.0, duration=32.5,
        episodes=[
            EpisodeDraft(onset_ms=3500, end_ms=6500, condition="CR-01"),
            EpisodeDraft(onset_ms=6500, end_ms=29500, condition="CR-02"),
        ],
        warnings=[],
    )
    path = write_clip_yaml(tmp_path, "a_p6_c01", "P6", "P6-a-take2.mp4", ventana)
    data = yaml.safe_load(path.read_text())
    assert len(data["episode_draft"]) == 2
    assert data["episode_draft"][1]["condition"] == "CR-02"
```

(El test `test_el_yaml_pasa_la_validacion_real_de_derive_clip_gt` no necesita cambios:
solo verifica `clip_id`/`block`/`scenario`, que no cambian de forma — `VENTANA` ya
actualizada arriba lo cubre igual.)

En `test_clip_generate.py`, en `test_flujo_nominal`, cambiar la última aserción:

```python
    assert data["episode_draft"][0]["onset_ms"] == 3500
```

En `test_clips_router.py`, en `test_generar_clip_de_punta_a_punta`, cambiar:

```python
    assert data["episode_draft"][0]["onset_ms"] == 3500
```

- [ ] **Step 2: Correr los tests para verificar que fallan**

Run: `cd webconsole/backend && .venv/bin/python -m pytest tests/test_clip_window.py tests/test_clip_yaml.py tests/test_clip_generate.py -v`
Expected: FAIL — `TrimWindow` no tiene el campo `episodes` ni existe `EpisodeDraft`
todavía; `write_clip_yaml` sigue escribiendo un dict único.

- [ ] **Step 3: Implementar el reshape**

En `window.py`, reemplazar la clase `TrimWindow` completa por:

```python
@dataclass(frozen=True)
class EpisodeDraft:
    """Un episodio (onset, fin, condición) dentro del clip recortado."""

    onset_ms: int
    end_ms: int
    condition: str | None


@dataclass(frozen=True)
class TrimWindow:
    """Resultado de la computación de ventana de recorte.

    Attributes:
        ss: inicio del corte en el master (segundos)
        duration: duración del recorte (lo que se pasa como --to a prepare_clip.sh)
        episodes: episodios dentro del clip (1 para compute_window, 2 para
            compute_window_multi)
        warnings: lista de advertencias del guion de rodaje
    """

    ss: float
    duration: float
    episodes: list[EpisodeDraft]
    warnings: list[str]
```

Y, al final de `compute_window` (antes tenía `onset_ms=round(...)`, `end_ms=round(...)`
como campos del `return`), cambiar el `return` final a:

```python
    return TrimWindow(
        ss=round(start, 3),
        duration=round(duration, 3),
        episodes=[
            EpisodeDraft(
                onset_ms=round((t_event - start) * 1000),
                end_ms=round((t_end - start) * 1000),
                condition=SCENARIO_CONDITION.get(scenario),
            )
        ],
        warnings=warnings,
    )
```

En `clip_yaml.py`, reemplazar el bloque `"episode_draft": {...}` dentro de
`write_clip_yaml` por:

```python
    payload = {
        "clip_id": clip_id,
        "block": "A",
        "scenario": scenario,
        "source_id": clip_id,
        "level": "scene",
        "master": f"raw/{master_name}",
        "episode_draft": [
            {"onset_ms": ep.onset_ms, "end_ms": ep.end_ms, "condition": ep.condition}
            for ep in window.episodes
        ],
        "warnings": list(window.warnings),
    }
```

(Antes `marked_by`/`warnings` vivían adentro de `episode_draft`; `warnings` sube a
nivel del payload porque ahora `episode_draft` es una lista y no tiene un único lugar
natural para colgar la lista de warnings del clip entero. `marked_by: "consola"` se
elimina — no lo usa ningún consumidor, verificado en `derive_clip_gt.load_clip_meta`,
que solo exige `clip_id`/`block`/`scenario` y tolera cualquier clave extra.)

- [ ] **Step 4: Correr los tests para verificar que pasan**

Run: `cd webconsole/backend && .venv/bin/python -m pytest tests/test_clip_window.py tests/test_clip_yaml.py tests/test_clip_generate.py -v`
Expected: PASS, todos.

- [ ] **Step 5: Commit**

```bash
git add webconsole/backend/src/eovrt_webconsole/clips/window.py \
        webconsole/backend/src/eovrt_webconsole/clips/clip_yaml.py \
        webconsole/backend/tests/test_clip_window.py \
        webconsole/backend/tests/test_clip_yaml.py \
        webconsole/backend/tests/test_clip_generate.py
git commit -m "refactor: TrimWindow.episodes como lista, episode_draft como lista en el yaml"
```

**Nota:** `test_clips_router.py` queda con su aserción actualizada pero SIN correr
en este paso (requiere ffmpeg real + repo `e-ovrt_datasets` — se corre y valida
recién en la Tarea 4, cuando el router también cambia). No lo agregues a este commit
todavía: quedaría con un cambio a medio camino sin un commit propio. Dejalo
modificado en el working tree; la Tarea 4 lo vuelve a tocar y lo commitea con el
resto de sus cambios.

---

### Task 3: `compute_window_multi` para P6/P8 + branching en `generate_clip`

**Files:**
- Modify: `webconsole/backend/src/eovrt_webconsole/clips/window.py`
- Modify: `webconsole/backend/src/eovrt_webconsole/clips/generate.py`
- Test: `webconsole/backend/tests/test_clip_window.py`
- Test: `webconsole/backend/tests/test_clip_generate.py`

**Interfaces:**
- Consumes: `EpisodeDraft`, `TrimWindow`, `PRE_ROLL_S`, `DEFAULT_TAIL_S`,
  `DIMENSIONING_MS`, `DIMENSIONING_TAIL_S`, `InvalidMarks` (Tareas 1-2).
- Produces: `MULTI_EPISODE_CONDITIONS: dict[str, list[str]]`,
  `compute_window_multi(marks: list[float], master_duration: float, scenario: str) -> TrimWindow`.
  `generate_clip()` cambia su firma: los parámetros `t_event: float, t_end: float`
  se reemplazan por `marks: list[float]` (rompe a los llamadores actuales — se
  actualizan en este mismo task los tests que llaman a `generate_clip` directamente;
  el router se actualiza en la Tarea 4).

- [ ] **Step 1: Escribir los tests que fallan**

Agregar al final de `test_clip_window.py`:

```python
from eovrt_webconsole.clips.window import compute_window_multi


def test_p6_nominal_con_los_tiempos_guionados():
    # t1=10 (casco fuera), t2=13 (chaleco fuera, +3), t3=23 (chaleco puesto),
    # t4=33 (casco puesto). El episodio CR-02 (chaleco) queda ANIDADO dentro
    # del CR-01 (casco): [t1,t4] vs [t2,t3] — doc operacion/72 §4.6.
    w = compute_window_multi([10.0, 13.0, 23.0, 33.0], master_duration=90.0, scenario="P6")
    assert w.ss == 6.5   # 10.0 - 3.5
    assert len(w.episodes) == 2
    assert w.episodes[0].condition == "CR-01"
    assert w.episodes[0].onset_ms == 3500        # t1 - ss = 3.5s
    assert w.episodes[0].end_ms == 26500         # t4 - ss = 26.5s
    assert w.episodes[1].condition == "CR-02"
    assert w.episodes[1].onset_ms == 6500        # t2 - ss = 6.5s
    assert w.episodes[1].end_ms == 16500         # t3 - ss = 16.5s
    # cobertura = (33-10) + 6.5 = 29.5 ; piso CR-02 = 6.5 + 25 + 1 = 32.5 ; D = 32.5
    assert w.duration == pytest.approx(32.5)


def test_p8_nominal_con_los_tiempos_guionados():
    # t1=10 (casco fuera), t2=15 (sale de cuadro), t3=23 (vuelve, t3-t1=13),
    # t4=31 (casco puesto, t4-t1=21).
    w = compute_window_multi([10.0, 15.0, 23.0, 31.0], master_duration=90.0, scenario="P8")
    assert w.ss == 6.5
    assert w.episodes[0].condition == "CR-01"
    assert w.episodes[1].condition == "CR-01"
    assert w.episodes[1].onset_ms == 16500   # 3.5 + (23-10)
    # cobertura = (31-10)+6.5 = 27.5 ; piso ep2 = 16.5+14+1 = 31.5 ; D = 31.5
    assert w.duration == pytest.approx(31.5)


def test_multi_requiere_exactamente_cuatro_marcas():
    with pytest.raises(InvalidMarks):
        compute_window_multi([10.0, 20.0, 30.0], master_duration=90.0, scenario="P6")


def test_multi_rechaza_marcas_no_crecientes():
    with pytest.raises(InvalidMarks):
        compute_window_multi([10.0, 9.0, 20.0, 30.0], master_duration=90.0, scenario="P6")


def test_multi_rechaza_marcas_repetidas():
    with pytest.raises(InvalidMarks):
        compute_window_multi([10.0, 10.0, 20.0, 30.0], master_duration=90.0, scenario="P6")


def test_multi_rechaza_escenario_de_un_episodio():
    with pytest.raises(InvalidMarks):
        compute_window_multi([10.0, 13.0, 23.0, 33.0], master_duration=90.0, scenario="P1")


def test_multi_marcas_fuera_del_master_se_rechazan():
    with pytest.raises(InvalidMarks):
        compute_window_multi([10.0, 13.0, 23.0, 100.0], master_duration=90.0, scenario="P6")


def test_multi_clampea_si_el_master_no_alcanza_y_avisa():
    # El piso pide 32.5 s de duración, pero el master solo tiene 28.5 s desde ss.
    w = compute_window_multi([10.0, 13.0, 23.0, 33.0], master_duration=35.0, scenario="P6")
    assert w.duration == pytest.approx(28.5)   # 35.0 - 6.5
    assert any("no tiene" in msg for msg in w.warnings)
```

- [ ] **Step 2: Correr los tests para verificar que fallan**

Run: `cd webconsole/backend && .venv/bin/python -m pytest tests/test_clip_window.py -v -k multi or p6 or p8`
Expected: FAIL — `compute_window_multi` no existe.

- [ ] **Step 3: Implementar `compute_window_multi` en `window.py`**

Agregar, después de `compute_window`:

```python
# Condición de cada episodio, en orden, para los escenarios de 2 episodios.
# Dato del guion (doc operacion/72 §4.6/§4.8), no derivable de las marcas.
MULTI_EPISODE_CONDITIONS: dict[str, list[str]] = {
    "P6": ["CR-01", "CR-02"],
    "P8": ["CR-01", "CR-01"],
}

# Qué par de marcas (índices 0-based en `marks`) delimita cada episodio.
# P6 ANIDA el episodio de chaleco (CR-02) dentro del de casco (CR-01):
# episodio 0 = [t1,t4] (casco fuera -> puesto), episodio 1 = [t2,t3]
# (chaleco fuera -> puesto), con t1<t2<t3<t4. P8 son dos tramos SECUENCIALES
# separados por una ausencia de cuadro: episodio 0 = [t1,t2] (casco fuera ->
# sale de cuadro), episodio 1 = [t3,t4] (vuelve a entrar -> casco puesto).
# Doc operacion/72 §4.6 (P6) / §4.8 (P8).
MULTI_EPISODE_MARK_INDICES: dict[str, list[tuple[int, int]]] = {
    "P6": [(0, 3), (1, 2)],
    "P8": [(0, 1), (2, 3)],
}


def compute_window_multi(
    marks: list[float], master_duration: float, scenario: str
) -> TrimWindow:
    """Convierte 4 marcas (2 episodios) en ventana de recorte, para P6/P8.

    marks: [t1, t2, t3, t4] en segundos sobre el master, estrictamente
    crecientes. Ver doc operacion/72 §4.6 (P6) / §4.8 (P8) para el
    significado de cada marca — P6 anida sus dos episodios, P8 los separa
    en dos tramos secuenciales (ver `MULTI_EPISODE_MARK_INDICES`).

    Raises:
        InvalidMarks: si no son 4, no son estrictamente crecientes, quedan
            fuera del master, o el escenario no es de 2 episodios.
    """
    if len(marks) != 4:
        raise InvalidMarks(f"P6/P8 requieren 4 marcas, recibidas {len(marks)}")
    if list(marks) != sorted(marks) or len(set(marks)) != 4:
        raise InvalidMarks(f"las marcas tienen que ser estrictamente crecientes: {marks}")
    conditions = MULTI_EPISODE_CONDITIONS.get(scenario)
    mark_indices = MULTI_EPISODE_MARK_INDICES.get(scenario)
    if conditions is None or mark_indices is None:
        raise InvalidMarks(f"{scenario} no es un escenario de 2 episodios (P6/P8)")
    t1, t4 = marks[0], marks[-1]
    if t1 < 0 or t4 > master_duration:
        raise InvalidMarks(
            f"marcas fuera del master (primera={t1:.1f} s, última={t4:.1f} s, "
            f"master de {master_duration:.1f} s)"
        )

    warnings: list[str] = []

    start = t1 - PRE_ROLL_S
    if start < 0:
        warnings.append(
            f"solo {t1:.1f} s de pre-roll, se necesitan {PRE_ROLL_S} — "
            "el TTFD va a salir degradado"
        )
        start = 0.0

    # onset/end relativos a `start` (ya clampeado a 0 si hizo falta), no
    # asumiendo PRE_ROLL_S exacto — así el piso sigue siendo correcto incluso
    # con pre-roll degradado.
    onset_rel = [marks[i] - start for i, _ in mark_indices]
    end_rel = [marks[j] - start for _, j in mark_indices]

    cobertura = (t4 - start) + DEFAULT_TAIL_S
    floors = [
        onset_rel[i]
        + DIMENSIONING_MS[conditions[i]]["t_alert_upper_ms"] / 1000
        + DIMENSIONING_MS[conditions[i]]["resolve_ms"] / 1000
        + DIMENSIONING_TAIL_S
        + 1.0  # margen explícito (doc operacion/72 §4.6/§4.8)
        for i in range(2)
    ]
    duration = max(cobertura, *floors)

    if duration > master_duration - start:
        warnings.append(
            f"el master no tiene los {duration:.1f} s que pide el piso/cobertura "
            f"(quedan {master_duration - start:.1f} s) — clip corto, revisar toma"
        )
        duration = master_duration - start

    episodes = [
        EpisodeDraft(
            onset_ms=round(onset_rel[i] * 1000),
            end_ms=round(end_rel[i] * 1000),
            condition=conditions[i],
        )
        for i in range(2)
    ]
    return TrimWindow(
        ss=round(start, 3), duration=round(duration, 3),
        episodes=episodes, warnings=warnings,
    )
```

- [ ] **Step 4: Correr los tests para verificar que pasan**

Run: `cd webconsole/backend && .venv/bin/python -m pytest tests/test_clip_window.py -v`
Expected: PASS, todos (los de esta tarea y los de las Tareas 1-2).

- [ ] **Step 5: Escribir el test que falla para el branching en `generate.py`**

Agregar al final de `test_clip_generate.py`:

```python
def test_flujo_con_cuatro_marcas_usa_compute_window_multi(dv, stubs, tmp_path):
    (dv / "raw" / "P6-a-take2.mp4").write_bytes(b"master")
    result = generate_clip(
        raw_dir=dv / "raw", videos_dir=dv, script=tmp_path / "s.sh",
        master_name="P6-a-take2.mp4", marks=[10.0, 13.0, 23.0, 33.0],
    )
    assert result["clip_id"] == "a_p6_c01"
    import yaml
    data = yaml.safe_load((dv / "a_p6_c01.clip.yaml").read_text())
    assert len(data["episode_draft"]) == 2


def test_numero_de_marcas_invalido_se_rechaza(dv, stubs, tmp_path):
    with pytest.raises(InvalidRequest):
        generate_clip(
            raw_dir=dv / "raw", videos_dir=dv, script=tmp_path / "s.sh",
            master_name="P1-a-take1.mp4", marks=[10.0, 20.0, 30.0],
        )
```

Y actualizar TODAS las llamadas existentes a `generate_clip(...)` en el archivo,
reemplazando `t_event=X, t_end=Y` por `marks=[X, Y]` (son 9 llamadas: en
`test_flujo_nominal`, `test_autoincremento_si_ya_hay_clips`,
`test_regenerar_invalida_la_preann_vieja`, `test_regenerar_dos_veces_pisa_el_stale`,
`test_material_ajeno_requiere_escenario` (2 llamadas), `test_master_inexistente`,
`test_path_traversal_rechazado`, `test_master_ilegible_propaga_probe_error`,
`test_marcas_invalidas_propagan`). Ejemplo del primero:

```python
def test_flujo_nominal(dv, stubs, tmp_path):
    result = generate_clip(
        raw_dir=dv / "raw", videos_dir=dv, script=tmp_path / "s.sh",
        master_name="P1-a-take1.mp4", marks=[10.5, 24.5],
    )
```

- [ ] **Step 6: Correr los tests para verificar que fallan**

Run: `cd webconsole/backend && .venv/bin/python -m pytest tests/test_clip_generate.py -v`
Expected: FAIL — `generate_clip()` todavía espera `t_event`/`t_end`.

- [ ] **Step 7: Implementar el branching en `generate.py`**

Reemplazar la firma y el cuerpo relevante de `generate_clip`:

```python
def generate_clip(
    *,
    raw_dir: Path,
    videos_dir: Path,
    script: Path,
    master_name: str,
    marks: list[float],
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
    master_duration_s = measured.duration_ms / 1000.0
    if len(marks) == 2:
        window = compute_window(marks[0], marks[1], master_duration_s, scenario)
    elif len(marks) == 4:
        window = compute_window_multi(marks, master_duration_s, scenario)
    else:
        raise InvalidRequest(f"se esperan 2 o 4 marcas, recibidas {len(marks)}")

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

Y actualizar el import al tope del archivo:

```python
from eovrt_webconsole.clips.window import compute_window, compute_window_multi
```

- [ ] **Step 8: Correr los tests para verificar que pasan**

Run: `cd webconsole/backend && .venv/bin/python -m pytest tests/test_clip_window.py tests/test_clip_yaml.py tests/test_clip_generate.py -v`
Expected: PASS, todos.

- [ ] **Step 9: Commit**

```bash
git add webconsole/backend/src/eovrt_webconsole/clips/window.py \
        webconsole/backend/src/eovrt_webconsole/clips/generate.py \
        webconsole/backend/tests/test_clip_window.py \
        webconsole/backend/tests/test_clip_generate.py
git commit -m "feat: compute_window_multi para P6/P8 y branching por numero de marcas en generate_clip"
```

---

### Task 4: Contrato de API `marks: list[float]` + UI dinámica en `TrimDialog`

**Files:**
- Modify: `webconsole/backend/src/eovrt_webconsole/routers/clips.py`
- Test: `webconsole/backend/tests/test_clips_router.py`
- Modify: `webconsole/frontend/src/types.ts`
- Modify: `webconsole/frontend/src/components/TrimDialog.tsx`
- Test: `webconsole/frontend/src/__tests__/TrimDialog.test.tsx`

**Interfaces:**
- Consumes: `generate_clip(marks=..., ...)` (Tarea 3), `GenerateClipResult` (sin
  cambios: `clip_id`, `info`, `warnings`, `regenerated`, `invalidated`).
- Produces: `GenerateClipBody = {master: string, marks: number[], scenario?: string,
  clip_id?: string}` (frontend y backend). Es un breaking change del contrato del
  endpoint: `TrimDialog.tsx` es el único consumidor y se migra en esta misma tarea.

- [ ] **Step 1: Backend — escribir los tests que fallan**

En `test_clips_router.py`, reemplazar `"t_event_s": X, "t_end_s": Y` por
`"marks": [X, Y]` en las 5 llamadas existentes (`test_generar_clip_de_punta_a_punta`,
`test_fin_antes_del_evento_da_422`, `test_master_ilegible_da_422_con_motivo`,
`test_media_clip_tras_generar`). Ejemplo:

```python
def test_generar_clip_de_punta_a_punta(clips_client, master):
    creado = clips_client.post(
        "/api/clips",
        json={"master": "P1-a-take1.mp4", "marks": [6.0, 12.0]},
    )
```

Y agregar, al final del archivo:

```python
def test_marcas_con_longitud_invalida_da_422(clips_client, master):
    r = clips_client.post(
        "/api/clips",
        json={"master": "P1-a-take1.mp4", "marks": [6.0, 12.0, 20.0]},
    )
    assert r.status_code == 422
```

- [ ] **Step 2: Backend — correr los tests para verificar que fallan**

Run: `cd webconsole/backend && .venv/bin/python -m pytest tests/test_clips_router.py -v`
Expected: FAIL (si ffmpeg/e-ovrt_datasets están disponibles; si no, el archivo entero
se salta con `skipif` y este paso se documenta como "SKIPPED, no ejecutable en este
entorno" — igual dejá el código escrito, la Tarea sigue siendo correcta).

- [ ] **Step 3: Backend — implementar en `routers/clips.py`**

Reemplazar la clase `GenerateClipBody` y el cuerpo de `create_clip`:

```python
class GenerateClipBody(BaseModel):
    master: str
    marks: list[float]
    scenario: str | None = None
    clip_id: str | None = None


@router.post("", status_code=201)
def create_clip(request: Request, body: GenerateClipBody) -> dict:
    settings = _settings(request)
    try:
        return generate_clip(
            raw_dir=settings.raw_dir,
            videos_dir=settings.videos_dir,
            script=settings.prepare_clip_script,
            master_name=body.master,
            marks=body.marks,
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
        raise HTTPException(status_code=502, detail=str(exc)) from exc
```

- [ ] **Step 4: Backend — correr los tests para verificar que pasan**

Run: `cd webconsole/backend && .venv/bin/python -m pytest tests/test_clips_router.py -v`
Expected: PASS (o SKIPPED según disponibilidad de ffmpeg, igual que el Step 2).

- [ ] **Step 5: Frontend — escribir los tests que fallan**

En `types.ts`, cambiar:

```typescript
export interface GenerateClipBody {
  master: string
  marks: number[]
  scenario?: string
  clip_id?: string
}
```

En `TrimDialog.test.tsx`, reemplazar la aserción de body en
`'las marcas salen del currentTime del video y se postean'`:

```typescript
    expect(vi.mocked(generateClip).mock.calls[0][0]).toEqual({
      master: 'P1-a-take1.mp4',
      marks: [10.5, 24.5],
    })
```

Y agregar, al final del `describe`:

```typescript
  it('P6 pide cuatro marcas y las postea en orden', async () => {
    vi.mocked(generateClip).mockResolvedValue({
      clip_id: 'a_p6_c01',
      info: { fps: 30, duration_ms: 42500, n_frames: 1275, resolution: '1920x1080' },
      warnings: [],
      regenerated: false,
      invalidated: [],
    })
    render(
      <TrimDialog
        master={{ ...MASTER, name: 'P6-a-take2.mp4', scenario: 'P6' }}
        onClose={() => {}}
        onGenerated={() => {}}
      />,
    )
    const video = screen.getByTestId('trim-video') as HTMLVideoElement
    const boton = screen.getByText('Generar clip') as HTMLButtonElement
    expect(boton.disabled).toBe(true)
    for (const [label, t] of [
      ['casco_fuera', 10], ['chaleco_fuera', 13], ['chaleco_puesto', 23], ['casco_puesto', 33],
    ] as const) {
      Object.defineProperty(video, 'currentTime', { value: t, writable: true })
      fireEvent.click(screen.getByText(label))
    }
    expect(boton.disabled).toBe(false)
    fireEvent.click(boton)
    await waitFor(() => expect(generateClip).toHaveBeenCalled())
    expect(vi.mocked(generateClip).mock.calls[0][0]).toEqual({
      master: 'P6-a-take2.mp4',
      marks: [10, 13, 23, 33],
    })
  })

  it('P6: el segundo boton esta deshabilitado hasta marcar el primero', () => {
    render(
      <TrimDialog
        master={{ ...MASTER, name: 'P6-a-take2.mp4', scenario: 'P6' }}
        onClose={() => {}}
        onGenerated={() => {}}
      />,
    )
    const segundo = screen.getByText('chaleco_fuera') as HTMLButtonElement
    expect(segundo.disabled).toBe(true)
    const video = screen.getByTestId('trim-video') as HTMLVideoElement
    Object.defineProperty(video, 'currentTime', { value: 10, writable: true })
    fireEvent.click(screen.getByText('casco_fuera'))
    expect(segundo.disabled).toBe(false)
  })
```

- [ ] **Step 6: Frontend — correr los tests para verificar que fallan**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/TrimDialog.test.tsx`
Expected: FAIL — `TrimDialog` todavía solo tiene los botones fijos "Marcar
evento"/"Marcar fin" y postea `t_event_s`/`t_end_s`.

- [ ] **Step 7: Frontend — implementar la UI dinámica en `TrimDialog.tsx`**

Reemplazar el archivo completo:

```tsx
import { useRef, useState } from 'react'

import { ApiError, generateClip, masterMediaUrl } from '../api'
import type { GenerateClipResult, MasterEntry } from '../types'
import Card from './ui/Card'
import ErrorBanner from './ui/ErrorBanner'
import Field from './ui/Field'

const SCENARIOS = ['P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7', 'P8', 'P9']

// Labels de cada marca por escenario, en orden cronológico (doc operacion/72
// §4 y §5.3). 2 marcas para los escenarios de 1 episodio, 4 para P6/P8.
const MARK_LABELS: Record<string, string[]> = {
  P1: ['casco_fuera', 'casco_puesto'],
  P2: ['chaleco_fuera', 'chaleco_puesto'],
  P3: ['casco_fuera', 'casco_puesto'],
  P4: ['casco_fuera', 'casco_puesto'],
  P5: ['tramo_inicio', 'tramo_fin'],
  P6: ['casco_fuera', 'chaleco_fuera', 'chaleco_puesto', 'casco_puesto'],
  P7: ['casco_fuera', 'casco_puesto'],
  P8: ['casco_fuera', 'sale_de_cuadro', 'vuelve_a_entrar', 'casco_puesto'],
  P9: ['entra_en_cuadro', 'sale_o_termina'],
}
const DEFAULT_LABELS = ['Marcar evento', 'Marcar fin']

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
  const labels = MARK_LABELS[master.scenario ?? ''] ?? DEFAULT_LABELS
  const [marks, setMarks] = useState<(number | null)[]>(labels.map(() => null))
  const [scenario, setScenario] = useState(master.scenario ?? '')
  const [regenerate, setRegenerate] = useState('')
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<GenerateClipResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  const marcar = (i: number) => {
    const t = videoRef.current?.currentTime ?? 0
    setMarks((prev) => prev.map((v, idx) => (idx === i ? t : v)))
  }

  const listo = marks.every((m) => m != null) && scenario !== '' && !busy

  const generar = async () => {
    if (!marks.every((m): m is number => m != null)) return
    setBusy(true)
    setError(null)
    setResult(null)
    try {
      const body = {
        master: master.name,
        marks,
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
    <Card title={`Recortar ${master.name}`}>
      <video
        ref={videoRef}
        controls
        src={masterMediaUrl(master.name)}
        data-testid="trim-video"
        className="eo-trim__video eo-video"
      />

      <div className="eo-trim__marks">
        {labels.map((label, i) => (
          <span key={label}>
            <button
              type="button"
              disabled={i > 0 && marks[i - 1] == null}
              onClick={() => marcar(i)}
            >
              {label}
            </button>
            <span>{marks[i] != null ? `${marks[i]!.toFixed(1)} s` : 'sin marcar'}</span>
          </span>
        ))}
      </div>

      <div className="eo-trim__fields">
        {master.scenario == null ? (
          <Field label="Escenario">
            <select value={scenario} onChange={(e) => setScenario(e.target.value)}>
              <option value="">elegir…</option>
              {SCENARIOS.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </Field>
        ) : (
          <p className="eo-note">Escenario {master.scenario} (heredado del master)</p>
        )}

        {master.clips.length > 0 && (
          <Field label="Regenerar">
            <select value={regenerate} onChange={(e) => setRegenerate(e.target.value)}>
              <option value="">(nuevo)</option>
              {master.clips.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </Field>
        )}
      </div>
      {regenerate !== '' && (
        <p className="eo-trim__warn">Regenerar invalida la pre-anotación vieja de ese clip.</p>
      )}

      <div className="eo-actions">
        <button type="button" className="eo-btn--primary" onClick={generar} disabled={!listo}>
          {busy ? 'Generando…' : 'Generar clip'}
        </button>
        <button type="button" onClick={onClose}>Cerrar</button>
      </div>

      {result && (
        <div className="eo-trim__result">
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

      {error && <ErrorBanner>{error}</ErrorBanner>}
    </Card>
  )
}
```

Nota sobre `labels`: cuando `master.scenario` es `null` (material ajeno), `labels`
cae a `DEFAULT_LABELS` (2 marcas genéricas) hasta que el operador elige un escenario
en el `<select>`. Si el escenario elegido es P6/P8, el número de marcas pedidas NO
se actualiza dinámicamente en este caso (el `<select>` no dispara un remount de
`labels`) — es una limitación conocida y aceptable: el material "ajeno" (fuera del
patrón `P1-a-take2.mp4`) no incluye tomas P6/P8 en el rodaje real (ambas tienen
un solo master cada una, `P6-a-take2.mp4`/`P8-a-take1.mp4`, que sí siguen el
patrón y traen `scenario` no-nulo desde el backend). No se cubre con un test
porque no es un caso alcanzable con los datos reales del rodaje.

- [ ] **Step 8: Frontend — correr los tests para verificar que pasan**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/TrimDialog.test.tsx`
Expected: PASS, todos (los 5 tests preexistentes + los 2 nuevos de P6).

- [ ] **Step 9: Correr toda la suite de frontend para descartar regresiones**

Run: `cd webconsole/frontend && npx vitest run`
Expected: PASS, todos (ningún otro componente consume `GenerateClipBody` directo
más que `TrimDialog`/`api.ts` — verificado con
`grep -rn "GenerateClipBody\|t_event_s\|t_end_s" webconsole/frontend/src` antes de
dar la tarea por cerrada; no debería haber más resultados que `types.ts`, `api.ts`
y `TrimDialog.tsx`/`TrimDialog.test.tsx`).

- [ ] **Step 10: Commit**

```bash
git add webconsole/backend/src/eovrt_webconsole/routers/clips.py \
        webconsole/backend/tests/test_clips_router.py \
        webconsole/frontend/src/types.ts \
        webconsole/frontend/src/components/TrimDialog.tsx \
        webconsole/frontend/src/__tests__/TrimDialog.test.tsx
git commit -m "feat: contrato marks:list[float] y dialogo de recorte con marcas dinamicas para P6/P8"
```

---

## Self-Review Notes (already applied above)

- **Cobertura del spec:** Fase 1 → Task 1. Fase 2 (reshape + compute_window_multi) →
  Tasks 2-3. Fase 3 (API + UI) → Task 4. Testing constraint (fixtures descartables,
  nunca masters reales) → Global Constraints + reutilización explícita del patrón
  de `test_clip_trim.py`/`test_clips_router.py` en vez de inventar uno nuevo.
- **Placeholders:** ninguno — cada paso trae el código completo, no hay "TBD" ni
  "agregar tests similares" sin el cuerpo real.
- **Consistencia de tipos:** `EpisodeDraft`/`TrimWindow.episodes` se define en la
  Tarea 2 y se usa sin cambios en las Tareas 3-4; `compute_window_multi` (Tarea 3)
  devuelve el mismo `TrimWindow` que `compute_window`; `GenerateClipBody.marks`
  (Tarea 4) es consumido por `generate_clip(marks=...)` (Tarea 3) sin fricción de
  nombres. `piso_s`/`SCENARIO_CONDITION`/`SCENARIO_TAIL_S`/`DIMENSIONING_MS`
  (Tarea 1) se reutilizan textualmente en `compute_window_multi` (Tarea 3).
