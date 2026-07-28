# Recorte consciente del escenario en la consola — Design

**Fecha:** 2026-07-26. **Contexto:** doc `operacion/72` (recorte de clips y ficha de
eventos) mide que la consola de recorte trata a los nueve escenarios del rodaje casi
igual (pre-roll 3,5 s fijo, cola 3,0 s fija, target de duración cargado solo para 5 de
9 escenarios), y que eso produce recortes cortos sin aviso para P4/P6/P7/P8, y deja a
P6/P8 (dos episodios, cuatro marcas) completamente fuera de la consola.

**Repo/archivos:** todos en `e-ovrt_experimental-setup/webconsole/backend/src/
eovrt_webconsole/clips/` (`window.py`, `naming.py`, `clip_yaml.py`, `generate.py`) y
`routers/clips.py`, más `frontend/src/components/TrimDialog.tsx`.

## 1. Problema

`compute_window()` (`clips/window.py`) hoy:
- usa `TAIL_S = 3.0` fijo para los 9 escenarios, cuando P2 necesita 5,0 s, P4 necesita
  10,0 s, y P6/P8 necesitan una cola calculada contra el piso del último episodio;
- solo valida duración objetivo (`SCENARIO_TARGET_S`) para P1/P2/P3/P5/P9 — P4, P6, P7,
  P8 no tienen entrada y la consola recorta corto **sin avisar nada**;
- nunca valida el piso real de censura (gate A1 de `derive_clip_gt.py`), que es
  distinto y más estricto que el "objetivo de guion" — hoy no existe ese chequeo en
  absoluto, para ningún escenario;
- solo acepta 2 marcas (`t_event_s`/`t_end_s`), por lo que P6 y P8 (4 marcas, 2
  episodios) no se pueden recortar desde la consola.

`scenario_from_master()` (`clips/naming.py`) ya deriva el escenario del nombre del
master (`P1-a-take2.mp4` → `"P1"`) — hoy solo se usa para el `clip_id`; esta spec lo
reutiliza para decidir cuántas marcas pedir y qué fórmula aplicar.

## 2. Principio de diseño

> El escenario (leído del nombre del master) determina el contrato de marcado:
> cuántas marcas pide el diálogo, qué significa cada una, y qué fórmula de `ss`/`D`
> se aplica. El operador nunca calcula pre-roll ni cola a mano — sigue marcando solo
> instantes reales de la escena, igual que hoy.

## 3. Alcance: las tres fases, todas en este plan

Se implementan las tres fases descritas en doc 72 §2.1/§4, en orden (cada una es
testeable y commiteable de forma independiente):

1. **Piso universal + cola por escenario**, para los 7 escenarios de 1 episodio
   (P1, P2, P3, P4, P5, P7, P9). Cero cambio de UI.
2. **`compute_window_multi`** para P6/P8 (2 episodios, 4 marcas) — habilitado en el
   backend, generable por request directo al endpoint, sin tocar el diálogo todavía.
3. **UI dinámica** en `TrimDialog.tsx`: botones de marcado según el escenario (2 o 4),
   contrato del endpoint migrado a `marks: list[float]`.

## 4. Fase 1 — piso universal + cola por escenario

### 4.1 Constantes nuevas en `clips/window.py`

```python
# Cola por escenario (segundos). Default 3,0; los escenarios con cola larga
# están en el dict (doc 72 §4.4 P4, §4.2 P2).
SCENARIO_TAIL_S: dict[str, float] = {
    "P2": 5.0,
    "P4": 10.0,
}
DEFAULT_TAIL_S = 3.0

# Condición de cada escenario de 1 episodio, o None si no hay episodio
# (P3 = transitorio sub-umbral, P5 = negativo). Usado para calcular el piso.
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

### 4.2 Función `piso_s(scenario)`

```python
def piso_s(scenario: str) -> float | None:
    """Piso A1 (segundos de duración mínima) para un escenario de 1 episodio.

    None si el escenario no tiene episodio (P3, P5) — no hay piso que censurar.
    Asume onset_rel == PRE_ROLL_S, válido para los 7 escenarios de 1 episodio
    (ss siempre se calcula como marca_evento - PRE_ROLL_S).
    """
    condition = SCENARIO_CONDITION.get(scenario)
    if condition is None:
        return None
    dim = DIMENSIONING_MS[condition]
    return PRE_ROLL_S + dim["t_alert_upper_ms"] / 1000 + dim["resolve_ms"] / 1000 + DIMENSIONING_TAIL_S
```

Con `PRE_ROLL_S = 3.5`: `piso_s("CR-01") == 17.5`, `piso_s("CR-02") == 28.5` —
verificado contra doc 72 §1 y §4.10.

### 4.3 Cambios en `compute_window()`

- `end_clip = t_end + SCENARIO_TAIL_S.get(scenario, DEFAULT_TAIL_S)` (reemplaza el uso
  de `TAIL_S`).
- Después del chequeo de `SCENARIO_TARGET_S` existente (sin tocarlo), agregar:
  ```python
  floor = piso_s(scenario)
  if floor is not None and duration < floor:
      warnings.append(
          f"clip de {duration:.1f} s, el piso de censura pide {floor:g} s "
          f"para este episodio — por debajo, t_alert-system/recall quedan "
          f"censurados (doc 57 §6.7)"
      )
  ```
  Dos warnings distintos y con mensajes distinguibles: el de piso dice
  explícitamente "censurado"; el de objetivo (ya existente) dice "el guion pide".
- `SCENARIO_TARGET_S` no gana filas nuevas — doc 72 solo define objetivo de guion
  para P1/P2/P3/P5/P9 (las que ya están). P4 y P7 quedan piso-only, tal como dice el
  documento (§4.4, §4.7): no hay una "duración de guion" declarada para ellos, solo
  el piso.

## 5. Fase 2 — P6/P8 (dos episodios), sin UI todavía

### 5.1 `MULTI_EPISODE_CONDITIONS`

```python
# Condición de cada episodio, en orden, para los escenarios de 2 episodios.
# Dato del guion (doc 72 §4.6/§4.8), no derivable de las marcas.
MULTI_EPISODE_CONDITIONS: dict[str, list[str]] = {
    "P6": ["CR-01", "CR-02"],
    "P8": ["CR-01", "CR-01"],
}
```

### 5.2 `EpisodeDraft` y cambio de forma de `TrimWindow`

```python
@dataclass(frozen=True)
class EpisodeDraft:
    onset_ms: int
    end_ms: int
    condition: str

@dataclass(frozen=True)
class TrimWindow:
    ss: float
    duration: float
    episodes: list[EpisodeDraft]   # 1 elemento en compute_window, 2 en compute_window_multi
    warnings: list[str]
```

`compute_window()` pasa a devolver `episodes=[EpisodeDraft(onset_ms, end_ms,
SCENARIO_CONDITION.get(scenario) or "none")]` en vez de los campos sueltos
`onset_ms`/`end_ms` — es un cambio de forma interno, sin consumidores fuera de
`clip_yaml.py` (que se actualiza en el mismo commit).

### 5.3 `compute_window_multi`

```python
def compute_window_multi(
    marks: list[float], master_duration: float, scenario: str
) -> TrimWindow:
    """Convierte 4 marcas (2 episodios) en ventana de recorte, para P6/P8.

    marks: [t1, t2, t3, t4] en segundos sobre el master, en orden cronológico
    estricto. Ver doc 72 §4.6 (P6) / §4.8 (P8) para el significado de cada marca.
    """
    if len(marks) != 4:
        raise InvalidMarks(f"P6/P8 requieren 4 marcas, recibidas {len(marks)}")
    if list(marks) != sorted(marks) or len(set(marks)) != 4:
        raise InvalidMarks(f"las marcas tienen que ser estrictamente crecientes: {marks}")
    if marks[0] < 0 or marks[-1] > master_duration:
        raise InvalidMarks(
            f"marcas fuera del master (primera={marks[0]:.1f} s, "
            f"última={marks[-1]:.1f} s, master de {master_duration:.1f} s)"
        )
    conditions = MULTI_EPISODE_CONDITIONS.get(scenario)
    if conditions is None:
        raise InvalidMarks(f"{scenario} no es un escenario de 2 episodios (P6/P8)")

    warnings: list[str] = []
    t1, t2, t3, t4 = marks

    start = t1 - PRE_ROLL_S
    if start < 0:
        warnings.append(
            f"solo {t1:.1f} s de pre-roll, se necesitan {PRE_ROLL_S} — "
            "el TTFD va a salir degradado"
        )
        start = 0.0

    # onset_rel se calcula contra `start` (ya clampeado a 0 si hizo falta), no
    # asumiendo PRE_ROLL_S exacto — así el piso sigue siendo correcto incluso
    # con pre-roll degradado.
    onset_rel = [t1 - start, t3 - start]

    tail_default = DEFAULT_TAIL_S
    cobertura = (t4 - start) + tail_default

    floors = [
        onset_rel[i] + DIMENSIONING_MS[conditions[i]]["t_alert_upper_ms"] / 1000
        + DIMENSIONING_MS[conditions[i]]["resolve_ms"] / 1000 + DIMENSIONING_TAIL_S
        + 1.0  # margen explícito (doc 72 §4.6/§4.8)
        for i in range(2)
    ]
    duration = max(cobertura, *floors)

    if duration > master_duration - start:
        warnings.append(
            f"el master no tiene los {duration:.1f} s que pide el piso/cobertura "
            f"(quedan {master_duration - start:.1f} s) — clip corto, revisar toma"
        )
        duration = master_duration - start

    end_clip = start + duration
    episodes = [
        EpisodeDraft(
            onset_ms=round(onset_rel[0] * 1000),
            end_ms=round((t2 - start) * 1000),
            condition=conditions[0],
        ),
        EpisodeDraft(
            onset_ms=round(onset_rel[1] * 1000),
            end_ms=round((t4 - start) * 1000),
            condition=conditions[1],
        ),
    ]
    return TrimWindow(
        ss=round(start, 3), duration=round(duration, 3),
        episodes=episodes, warnings=warnings,
    )
```

Nota: `floors` itera **los dos episodios**, no asume que el segundo domina — refleja
cómo `dimensioning_warnings()` realmente valida en `derive_clip_gt.py` (itera
episodio por episodio), aunque en la práctica el segundo suele ser el más exigente.

### 5.4 `clips/clip_yaml.py`

`write_clip_yaml()` recibe `window: TrimWindow` con `window.episodes` (lista) y
escribe:

```python
"episode_draft": [
    {"onset_ms": ep.onset_ms, "end_ms": ep.end_ms, "condition": ep.condition}
    for ep in window.episodes
],
```

(1 elemento para los 7 escenarios de siempre, 2 para P6/P8 — mismo campo tolerado por
`derive_clip_gt.load_clip_meta`, ahora como lista en vez de un dict único.)

### 5.5 `clips/generate.py`

`generate_clip()` cambia su firma de `t_event: float, t_end: float` a
`marks: list[float]`, y branchea:

```python
if len(marks) == 2:
    window = compute_window(marks[0], marks[1], measured.duration_ms / 1000.0, scenario)
elif len(marks) == 4:
    window = compute_window_multi(marks, measured.duration_ms / 1000.0, scenario)
else:
    raise InvalidRequest(f"se esperan 2 o 4 marcas, recibidas {len(marks)}")
```

Resto del pipeline (`next_clip_id`, `_invalidate_preann`, `run_prepare_clip`,
`write_clip_yaml`) sin cambios de comportamiento.

## 6. Fase 3 — contrato API + UI dinámica

### 6.1 `routers/clips.py`

```python
class GenerateClipBody(BaseModel):
    master: str
    marks: list[float]
    scenario: str | None = None
    clip_id: str | None = None
```

`create_clip()` pasa `marks=body.marks` a `generate_clip()`; el resto del manejo de
excepciones (`InvalidRequest`, `InvalidMarks`, `InvalidScenario`, `ProbeError`,
`TrimFailed`) no cambia.

### 6.2 `TrimDialog.tsx`

- Tabla de contratos de marcado por escenario (labels reales, en el mismo archivo o
  en un `naming.ts`/`scenarios.ts` nuevo compartido con el backend solo en
  documentación, no en código):
  ```ts
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
  ```
- `marks: (number | null)[]` en vez de `tEvent`/`tEnd` sueltos, largo determinado por
  `MARK_LABELS[scenario].length` (2 o 4).
- Un botón por marca, en orden; el botón `i` está `disabled` hasta que
  `marks[i-1] != null` (fuerza el orden cronológico que pide doc 72 §5.3/§4).
- `generar()` valida `marks.every(m => m != null)` (reemplaza el chequeo actual de
  `tEvent != null && tEnd != null`) y manda `marks` (filtradas, no null) al backend.
- El escenario tiene que estar elegido ANTES de poder marcar (ya lo está: si
  `master.scenario == null` el `<select>` va primero) porque el número de botones
  depende de él.

## 7. Testing

- Fixtures de video: generadas en el test (ffmpeg sintético, ya es el patrón de
  `test_clip_generate.py`) en un directorio temporal — **nunca se leen ni escriben
  los masters reales del rodaje**. Cualquier test nuevo sigue esa misma convención.
- `test_clip_window.py`: casos nuevos para `piso_s()` (cada condición + `None` para
  P3/P5), warnings duales (piso vs objetivo) para P1/P2, `SCENARIO_TAIL_S` aplicado
  para P2/P4 y default para el resto, y toda la superficie de `compute_window_multi`
  (orden estricto, marcas fuera de rango, fórmula de cobertura vs. piso para P6 y
  P8 con los números guionados de doc 72 §4.6/§4.8, clamp cuando el master no
  alcanza).
- `test_clip_yaml.py`: `episode_draft` como lista de 1 y de 2.
- `test_clip_generate.py`: `generate_clip()` con `marks` de largo 2 y de largo 4,
  branch a `compute_window`/`compute_window_multi`, error con largo inválido (ej. 3).
- Frontend: `TrimDialog.test.tsx` — botones dinámicos según escenario, orden
  cronológico forzado (botón N deshabilitado sin marca N-1), envío de `marks` al
  backend.

## 8. Fuera de alcance

- El transitorio de P3 (doc 72 §4.11 caso 3) sigue siendo un chequeo manual con la
  tira de miniaturas — automatizarlo es trabajo de visión, no de esta herramienta.
- No cambia el criterio de selección de toma (§3.1) ni el flujo de CVAT.
- El subset DVR (verificación de bitrate) sigue siendo manual (§3.3).
- P9 no se toca en Fase 2/3 (sigue siendo 1 episodio, 2 marcas) — solo gana el
  piso universal de Fase 1, igual que P1/P4/P7.
