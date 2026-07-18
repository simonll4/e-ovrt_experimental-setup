# Ventana "Cámaras" (preview de fuentes en vivo) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ventana en la webconsole para ver fuentes de video (RTSP, OAK-D) en vivo — modo "solo video" para posicionar cámara y modo "detección" para probar prompt sets — sin crear runs, con exclusión mutua estricta contra los runs del media-plane.

**Architecture:** El media-plane gana una sesión de preview singleton (`PreviewManager` + `POST/GET/DELETE /api/preview` + `WS /api/preview/stream` binario que envía frame JPEG y detecciones juntos), que comparte un slot de actividad único con `RunManager`. La webconsole agrega un proxy REST+WS en el BFF, presets de cámara en YAML (`cameras/*.yaml`, estilo prompt store) y la página `/cameras` que dibuja el frame con overlay de cajas reutilizando `PreviewWithBoxes`.

**Tech Stack:** FastAPI + threading + OpenCV/PIL (media-plane), FastAPI + httpx + websockets (BFF), React + react-router + vitest (frontend).

**Spec:** `docs/superpowers/specs/2026-07-18-camera-preview-design.md` (en este repo).

## Global Constraints

- **NUNCA commitear.** Regla del workspace (`projects/CLAUDE.md`): los pasos de commit de los skills quedan anulados. Al final de cada tarea dejar tests en verde y reportar; el usuario pide los commits explícitamente.
- **Dos repos:** tareas 1–4 en `/home/simonll4/projects/e-ovrt_media-plane/`; tareas 5–10 en `/home/simonll4/projects/e-ovrt_experimental-setup/`.
- **No romper la plataforma experimental:** cero cambios de comportamiento en runs salvo el nuevo 409 `reason: "preview_active"`. Las suites existentes deben pasar intactas: `cd e-ovrt_media-plane && make test`; `cd e-ovrt_experimental-setup/webconsole/backend && .venv/bin/python -m pytest -q && .venv/bin/ruff check src tests`; `cd e-ovrt_experimental-setup/webconsole/frontend && npx vitest run`.
- **Nada se persiste en preview:** sin directorio de run, sin JSONL, sin artefactos, sin bus ZeroMQ.
- **Trampa ZeroMQ/threads:** el stop de fuentes es cooperativo (`source.stop()`), mismo patrón que `RunControl.request_stop()` (`runtime/pipeline.py:397-414`). No cerrar sockets desde otros hilos.
- Código y mensajes de error en español, como el resto del codebase.

---

### Task 1: `PreviewRequest` + traducción a RunConfig (media-plane)

**Files:**
- Create: `src/eovrt_media/service/preview_request.py`
- Test: `tests/test_preview_request.py`

**Interfaces:**
- Consumes: `IngestSpec`, `PromptsSpec` de `eovrt_media/service/run_request.py`; `RunRequest`, `to_raw_run_config`.
- Produces: `PreviewRequest` (pydantic: `mode: Literal["raw","detect"]`, `ingest: IngestSpec`, `prompts: PromptsSpec | None`, `params: PreviewParams` con `score_threshold: float | None`) y `to_run_request(req: PreviewRequest) -> RunRequest` (inyecta prompt set dummy en modo raw, para reutilizar la validación/loader de runs sin cambios).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_preview_request.py
import pytest
from pydantic import ValidationError

from eovrt_media.service.preview_request import PreviewRequest, to_run_request

SET_INLINE = {"id": "t", "classes": [{"id": "p", "phrasings": {"default": ["p"]}}]}


def test_raw_sin_prompts_es_valido():
    req = PreviewRequest(mode="raw", ingest={"plugin": "image_folder", "config": {"path": "x"}})
    assert req.prompts is None
    assert req.params.score_threshold is None


def test_detect_sin_prompts_es_invalido():
    with pytest.raises(ValidationError):
        PreviewRequest(mode="detect", ingest={"plugin": "image_folder", "config": {"path": "x"}})


def test_campo_desconocido_rechazado():
    with pytest.raises(ValidationError):
        PreviewRequest(mode="raw", ingest={"plugin": "image_folder"}, run={"stride": 2})


def test_threshold_fuera_de_rango():
    with pytest.raises(ValidationError):
        PreviewRequest(
            mode="detect",
            ingest={"plugin": "image_folder"},
            prompts={"set_inline": SET_INLINE},
            params={"score_threshold": 1.5},
        )


def test_to_run_request_detect_conserva_prompts():
    req = PreviewRequest(
        mode="detect", ingest={"plugin": "image_folder", "config": {"path": "x"}},
        prompts={"set_inline": SET_INLINE},
    )
    rr = to_run_request(req)
    assert rr.prompts.set_inline == SET_INLINE
    assert rr.ingest.plugin == "image_folder"


def test_to_run_request_raw_usa_set_dummy():
    req = PreviewRequest(mode="raw", ingest={"plugin": "image_folder", "config": {"path": "x"}})
    rr = to_run_request(req)
    assert rr.prompts.set_inline["id"] == "preview_raw"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/simonll4/projects/e-ovrt_media-plane && .venv/bin/python -m pytest tests/test_preview_request.py -q`
Expected: FAIL / ERROR con `ModuleNotFoundError: eovrt_media.service.preview_request`

- [ ] **Step 3: Write the implementation**

```python
# src/eovrt_media/service/preview_request.py
"""Contrato HTTP de la sesión de preview (POST /api/preview)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from eovrt_media.service.run_request import IngestSpec, PromptsSpec, RunRequest

# Set dummy para modo raw: permite reutilizar el loader de runs (que exige prompts)
# sin ejecutar inferencia alguna.
_RAW_DUMMY_SET = {"id": "preview_raw", "classes": [{"id": "x", "phrasings": {"default": ["x"]}}]}


class PreviewParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score_threshold: float | None = Field(default=None, ge=0.0, le=1.0)


class PreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["raw", "detect"]
    ingest: IngestSpec
    prompts: PromptsSpec | None = None
    params: PreviewParams = Field(default_factory=PreviewParams)

    @model_validator(mode="after")
    def _detect_requiere_prompts(self) -> "PreviewRequest":
        if self.mode == "detect" and self.prompts is None:
            raise ValueError("mode=detect requiere 'prompts'")
        return self


def to_run_request(req: PreviewRequest) -> RunRequest:
    prompts = req.prompts or PromptsSpec(set_inline=_RAW_DUMMY_SET)
    return RunRequest(ingest=req.ingest, prompts=prompts)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_preview_request.py -q`
Expected: 6 passed

---

### Task 2: `ActivitySlot` compartido + integración en `RunManager` (media-plane)

**Files:**
- Create: `src/eovrt_media/service/activity_slot.py`
- Modify: `src/eovrt_media/service/run_manager.py` (constructor `:81-96`, `start_run` `:100-125`, `_finalize` `:~305`)
- Modify: `src/eovrt_media/service/routers/runs.py:26-39`
- Test: `tests/test_activity_slot.py`, ampliar `tests/test_runs_api.py`

**Interfaces:**
- Produces: `ActivitySlot` con `acquire(kind: str, owner_id: str | None = None) -> None` (lanza `SlotBusyError`), `release(kind: str) -> None`, propiedad `owner -> tuple[str, str | None] | None`; `SlotBusyError(RuntimeError)` con atributos `owner_kind: str`, `owner_id: str | None`. `RunManager.__init__` gana kwarg `slot: ActivitySlot | None = None`.
- El lock interno del slot es **hoja**: nunca llama hacia afuera, así que adquirirlo bajo el lock de RunManager o PreviewManager no puede generar deadlock AB-BA.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_activity_slot.py
import pytest

from eovrt_media.service.activity_slot import ActivitySlot, SlotBusyError


def test_acquire_release():
    slot = ActivitySlot()
    slot.acquire("run", "run_1")
    assert slot.owner == ("run", "run_1")
    slot.release("run")
    assert slot.owner is None


def test_acquire_ocupado_lanza_busy():
    slot = ActivitySlot()
    slot.acquire("preview", "pv_1")
    with pytest.raises(SlotBusyError) as exc:
        slot.acquire("run", "run_1")
    assert exc.value.owner_kind == "preview"
    assert exc.value.owner_id == "pv_1"


def test_release_de_otro_kind_es_noop():
    slot = ActivitySlot()
    slot.acquire("run", "run_1")
    slot.release("preview")
    assert slot.owner == ("run", "run_1")
```

Y en `tests/test_runs_api.py` (usa los helpers existentes `client`, `_images`, `_body` de ese módulo):

```python
def test_run_409_si_preview_activa(client, tmp_path):
    folder = _images(tmp_path)
    app_state = client.app.state
    app_state.manager._slot.acquire("preview", "pv_1")
    try:
        r = client.post("/api/runs", json=_body(folder))
        assert r.status_code == 409
        assert r.json()["reason"] == "preview_active"
    finally:
        app_state.manager._slot.release("preview")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_activity_slot.py tests/test_runs_api.py -q`
Expected: FAIL (`ModuleNotFoundError` y `AttributeError: _slot`)

- [ ] **Step 3: Write `ActivitySlot`**

```python
# src/eovrt_media/service/activity_slot.py
"""Slot único de actividad del media-plane: un run O una preview, nunca ambos."""

from __future__ import annotations

import threading


class SlotBusyError(RuntimeError):
    def __init__(self, owner_kind: str, owner_id: str | None) -> None:
        detalle = f" ({owner_id})" if owner_id else ""
        super().__init__(f"Slot de actividad ocupado por {owner_kind}{detalle}")
        self.owner_kind = owner_kind
        self.owner_id = owner_id


class ActivitySlot:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._owner: tuple[str, str | None] | None = None

    def acquire(self, kind: str, owner_id: str | None = None) -> None:
        with self._lock:
            if self._owner is not None:
                raise SlotBusyError(*self._owner)
            self._owner = (kind, owner_id)

    def release(self, kind: str) -> None:
        with self._lock:
            if self._owner is not None and self._owner[0] == kind:
                self._owner = None

    @property
    def owner(self) -> tuple[str, str | None] | None:
        with self._lock:
            return self._owner
```

- [ ] **Step 4: Integrar en `RunManager`**

En `run_manager.py`:

1. Import: `from eovrt_media.service.activity_slot import ActivitySlot`.
2. Constructor: agregar kwarg y atributo (después de `self._settings = settings`):

```python
    def __init__(
        self,
        adapter: Any,
        model_section: ModelSection,
        settings: ServiceSettings,
        slot: ActivitySlot | None = None,
    ) -> None:
        ...
        self._slot = slot if slot is not None else ActivitySlot()
```

(default propio para no tocar los tests/usos existentes que construyen `RunManager(adapter, model_section, settings)`).

3. En `start_run`, tras `config.run.id = self._new_run_id(config)` y **antes** de crear el `ActiveRun`:

```python
            self._slot.acquire("run", config.run.id)  # SlotBusyError si preview activa
```

4. En `_finalize`, junto a donde pone `self._active = None`, agregar `self._slot.release("run")`.

- [ ] **Step 5: Mapear `SlotBusyError` a 409 en el router de runs**

En `routers/runs.py`, import `from eovrt_media.service.activity_slot import SlotBusyError` y en `create_run` agregar un except **antes** del de `(ValueError, FileNotFoundError)`:

```python
    except SlotBusyError as exc:
        return JSONResponse(
            status_code=409,
            content={"detail": str(exc), "reason": "preview_active"},
        )
```

(El 409 run-vs-run existente con `active_run_id` no cambia; solo se le agrega `"reason": "run_active"` a su content para uniformidad.)

- [ ] **Step 6: Run tests**

Run: `.venv/bin/python -m pytest tests/test_activity_slot.py tests/test_runs_api.py -q`
Expected: PASS (incluye los tests de runs preexistentes, sin regresión)

---

### Task 3: `PreviewManager` (media-plane)

**Files:**
- Create: `src/eovrt_media/service/preview_manager.py`
- Test: `tests/test_preview_manager.py`

**Interfaces:**
- Consumes: `to_run_request` (Task 1), `ActivitySlot`/`SlotBusyError` (Task 2), `to_raw_run_config` (`run_request.py:61`), `load_run_config_data` + `find_plane_catalog_root` (`config/loader.py`), `create_source` (`sources/registry.py:60`), `adapter.predict(image, plan)` y `adapter.PROMPT_BACKEND` (`models/base.py:41-73`), `config.build_prompt_plan(backend)` (`config/schemas.py:596`).
- Produces: `PreviewManager(adapter, model_section, settings, slot)` con:
  - `start(request: PreviewRequest) -> str` (preview_id; lanza `SlotBusyError` o `ValueError`/`FileNotFoundError`)
  - `stop() -> None` (idempotente, join del hilo)
  - `status() -> dict` → `{"status": "idle"|"streaming"|"error", "preview_id", "mode", "error"}`
  - `is_active() -> bool`
  - `snapshot() -> tuple[str, int, bytes | None, str | None]` → `(status, seq, latest_message, error)` para el WS.
  - Mensaje binario: `struct.pack(">I", len(header_json)) + header_json + jpeg`, header `{"seq","ts","width","height","mode","detections":[{"label","score","bbox_norm_xyxy"}]}`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_preview_manager.py
import json
import struct
import time

import pytest
from PIL import Image

from eovrt_media.config.loader import resolve_model_ref
from eovrt_media.models import create_adapter
from eovrt_media.service.activity_slot import ActivitySlot, SlotBusyError
from eovrt_media.service.preview_manager import PreviewManager
from eovrt_media.service.preview_request import PreviewRequest
from eovrt_media.service.settings import ServiceSettings

SET_INLINE = {"id": "t", "classes": [{"id": "p", "phrasings": {"default": ["p"]}}]}


def _images(tmp_path, n=3):
    folder = tmp_path / "imgs"
    folder.mkdir()
    for i in range(n):
        Image.new("RGB", (64, 48), (i, 2, 3)).save(folder / f"f{i}.png")
    return folder


@pytest.fixture()
def manager(tmp_path):
    settings = ServiceSettings.from_env(
        {"EOVRT_MODEL_REF": "mock", "EOVRT_RUNS_DIR": str(tmp_path / "runs")}
    )
    model_section = resolve_model_ref(settings.model_ref, settings.catalog_root)
    adapter = create_adapter(model_section)
    adapter.load()
    mgr = PreviewManager(adapter, model_section, settings, ActivitySlot())
    yield mgr
    mgr.stop()


def _req(folder, mode="raw", **kw):
    body = {"mode": mode, "ingest": {"plugin": "image_folder", "config": {"path": str(folder)}}}
    if mode == "detect":
        body["prompts"] = {"set_inline": SET_INLINE}
    body.update(kw)
    return PreviewRequest(**body)


def _wait_frame(mgr, timeout=10.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        status, seq, latest, _ = mgr.snapshot()
        if latest is not None:
            return latest
        if status == "error":
            raise AssertionError(mgr.status())
        time.sleep(0.05)
    raise AssertionError("sin frame")


def _parse(msg):
    hlen = struct.unpack(">I", msg[:4])[0]
    header = json.loads(msg[4 : 4 + hlen].decode("utf-8"))
    jpeg = msg[4 + hlen :]
    return header, jpeg


def test_raw_produce_frames_sin_detecciones(manager, tmp_path):
    manager.start(_req(_images(tmp_path)))
    header, jpeg = _parse(_wait_frame(manager))
    assert header["mode"] == "raw"
    assert header["detections"] == []
    assert header["seq"] >= 1 and header["width"] == 64 and header["height"] == 48
    assert jpeg[:2] == b"\xff\xd8"  # magic JPEG


def test_detect_produce_detecciones_normalizadas(manager, tmp_path):
    manager.start(_req(_images(tmp_path), mode="detect"))
    header, _ = _parse(_wait_frame(manager))
    assert header["mode"] == "detect"
    for d in header["detections"]:
        assert set(d) == {"label", "score", "bbox_norm_xyxy"}
        assert all(0.0 <= v <= 1.0 for v in d["bbox_norm_xyxy"])


def test_threshold_filtra(manager, tmp_path):
    manager.start(_req(_images(tmp_path), mode="detect", params={"score_threshold": 1.0}))
    header, _ = _parse(_wait_frame(manager))
    assert header["detections"] == []


def test_ocupa_y_libera_slot(manager, tmp_path):
    manager.start(_req(_images(tmp_path)))
    with pytest.raises(SlotBusyError):
        manager.start(_req(_images(tmp_path / "b")))
    manager.stop()
    assert manager.status()["status"] == "idle"
    assert not manager.is_active()


def test_slot_ocupado_por_run_rechaza(manager, tmp_path):
    manager._slot.acquire("run", "run_1")
    with pytest.raises(SlotBusyError) as exc:
        manager.start(_req(_images(tmp_path)))
    assert exc.value.owner_kind == "run"
    assert exc.value.owner_id == "run_1"


def test_fuente_invalida_da_valueerror_sin_ocupar_slot(manager, tmp_path):
    with pytest.raises((ValueError, FileNotFoundError)):
        manager.start(_req(tmp_path / "no_existe"))
    assert manager._slot.owner is None


def test_fuente_agotada_termina_en_idle(manager, tmp_path):
    manager.start(_req(_images(tmp_path, n=2)))
    deadline = time.monotonic() + 10
    while manager.is_active() and time.monotonic() < deadline:
        time.sleep(0.05)
    assert manager.status()["status"] == "idle"
    assert manager._slot.owner is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_preview_manager.py -q`
Expected: ERROR `ModuleNotFoundError: eovrt_media.service.preview_manager`

- [ ] **Step 3: Write the implementation**

```python
# src/eovrt_media/service/preview_manager.py
"""Sesión de preview singleton: frames en vivo sin persistencia ni bus."""

from __future__ import annotations

import json
import logging
import struct
import threading
import uuid
from dataclasses import dataclass, field
from typing import Any

import cv2
import numpy as np
from PIL import Image

from eovrt_media.config.loader import find_plane_catalog_root, load_run_config_data
from eovrt_media.service.activity_slot import ActivitySlot, SlotBusyError
from eovrt_media.service.preview_request import PreviewRequest, to_run_request
from eovrt_media.service.run_request import to_raw_run_config
from eovrt_media.sources.registry import create_source

logger = logging.getLogger(__name__)

_MAX_WIDTH = 960
_JPEG_QUALITY = 80


@dataclass
class _Session:
    preview_id: str
    mode: str
    score_threshold: float | None
    stop_event: threading.Event = field(default_factory=threading.Event)
    source: Any = None
    thread: threading.Thread | None = None
    status: str = "streaming"
    error: str | None = None
    seq: int = 0
    latest: bytes | None = None


class PreviewManager:
    def __init__(self, adapter, model_section, settings, slot: ActivitySlot) -> None:
        self._adapter = adapter
        self._model_section = model_section
        self._settings = settings
        self._slot = slot
        self._lock = threading.Lock()
        self._frame_lock = threading.Lock()
        self._active: _Session | None = None
        self._last_error: str | None = None

    # -- API pública -----------------------------------------------------

    def start(self, request: PreviewRequest) -> str:
        with self._lock:
            if self._active is not None:
                raise SlotBusyError("preview", self._active.preview_id)
            preview_id = f"pv_{uuid.uuid4().hex[:8]}"
            self._slot.acquire("preview", preview_id)
            try:
                raw = to_raw_run_config(to_run_request(request), self._model_section)
                raw.setdefault("outputs", {})["run_dir"] = str(self._settings.runs_dir)
                config = load_run_config_data(
                    raw,
                    plane_root=find_plane_catalog_root(None, self._settings.catalog_root),
                    datasets_root=self._settings.datasets_root,
                )
                source = create_source(config)
                plan = (
                    config.build_prompt_plan(self._adapter.PROMPT_BACKEND)
                    if request.mode == "detect"
                    else None
                )
            except Exception:
                self._slot.release("preview")
                raise
            session = _Session(
                preview_id=preview_id,
                mode=request.mode,
                score_threshold=request.params.score_threshold,
                source=source,
            )
            self._active = session
            self._last_error = None
        thread = threading.Thread(
            target=self._loop, args=(session, plan), daemon=True, name="preview-loop"
        )
        session.thread = thread
        thread.start()
        return preview_id

    def stop(self) -> None:
        with self._lock:
            session = self._active
        if session is None:
            return
        session.stop_event.set()
        if session.source is not None:
            session.source.stop()  # cooperativo (mismo patrón que RunControl.request_stop)
        if session.thread is not None:
            session.thread.join(timeout=10.0)

    def is_active(self) -> bool:
        return self._active is not None

    def status(self) -> dict:
        with self._lock:
            session = self._active
            if session is not None:
                return {
                    "status": "streaming",
                    "preview_id": session.preview_id,
                    "mode": session.mode,
                    "error": None,
                }
            if self._last_error is not None:
                return {"status": "error", "preview_id": None, "mode": None, "error": self._last_error}
            return {"status": "idle", "preview_id": None, "mode": None, "error": None}

    def snapshot(self) -> tuple[str, int, bytes | None, str | None]:
        with self._frame_lock:
            session = self._active
            if session is None:
                status = "error" if self._last_error is not None else "idle"
                return status, 0, None, self._last_error
            return "streaming", session.seq, session.latest, None

    # -- Loop de captura -------------------------------------------------

    def _loop(self, session: _Session, plan) -> None:
        try:
            for unit in session.source:
                if session.stop_event.is_set():
                    break
                frame = unit.pixel_data
                if frame is None and unit.path:
                    frame = cv2.imread(unit.path)
                if frame is None:
                    continue
                frame = self._resize(frame)
                detections = self._detect(frame, plan, session.score_threshold) if plan else []
                message = self._build_message(session.seq + 1, session.mode, frame, detections, unit)
                with self._frame_lock:
                    session.seq += 1
                    session.latest = message
        except Exception as exc:  # noqa: BLE001
            logger.exception("Preview %s falló", session.preview_id)
            session.status = "error"
            session.error = str(exc)
        finally:
            with self._lock, self._frame_lock:
                if session.status == "error":
                    self._last_error = session.error
                if self._active is session:
                    self._active = None
            self._slot.release("preview")

    def _resize(self, frame: np.ndarray) -> np.ndarray:
        h, w = frame.shape[:2]
        if w <= _MAX_WIDTH:
            return frame
        scale = _MAX_WIDTH / w
        return cv2.resize(frame, (_MAX_WIDTH, int(h * scale)), interpolation=cv2.INTER_AREA)

    def _detect(self, frame_bgr: np.ndarray, plan, threshold: float | None) -> list[dict]:
        h, w = frame_bgr.shape[:2]
        image = Image.fromarray(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))
        raw = self._adapter.predict(image, plan)
        out: list[dict] = []
        for det in raw:
            if threshold is not None and det.score < threshold:
                continue
            x1, y1, x2, y2 = det.box_xyxy
            out.append(
                {
                    "label": det.label,
                    "score": round(float(det.score), 4),
                    "bbox_norm_xyxy": [
                        max(0.0, min(1.0, x1 / w)),
                        max(0.0, min(1.0, y1 / h)),
                        max(0.0, min(1.0, x2 / w)),
                        max(0.0, min(1.0, y2 / h)),
                    ],
                }
            )
        return out

    def _build_message(self, seq: int, mode: str, frame: np.ndarray, detections: list[dict], unit) -> bytes:
        ok, jpeg = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), _JPEG_QUALITY])
        if not ok:
            raise RuntimeError("No se pudo codificar el frame a JPEG")
        h, w = frame.shape[:2]
        header = json.dumps(
            {
                "seq": seq,
                "ts": unit.capture_wallclock_ms,
                "width": w,
                "height": h,
                "mode": mode,
                "detections": detections,
            }
        ).encode("utf-8")
        return struct.pack(">I", len(header)) + header + jpeg.tobytes()
```

Nota: `adapter.predict(image, plan)` recibe PIL en píxeles reales, así que las bboxes de `RawDetection.box_xyxy` se normalizan dividiendo por el tamaño del frame ya re-escalado — no hace falta el transporte/normalizador del pipeline. El adapter no se usa concurrentemente porque el slot único garantiza que no hay run activo.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_preview_manager.py -q`
Expected: 7 passed

---

### Task 4: Endpoints `/api/preview` + WS + registro en la app (media-plane)

**Files:**
- Create: `src/eovrt_media/service/routers/preview.py`
- Modify: `src/eovrt_media/service/app.py` (lifespan `:17-40`, registro de routers `:64-75`, shutdown `:54-61`)
- Test: `tests/test_preview_api.py`

**Interfaces:**
- Consumes: `PreviewManager` (Task 3), `SlotBusyError`, `PreviewRequest`.
- Produces (contrato HTTP para el BFF de la webconsole):
  - `POST /api/preview` → 201 `{"preview_id": str}`; 409 `{"detail", "reason": "run_active"|"preview_active", "active_run_id"?}`; 422; 503 si no ready.
  - `GET /api/preview` → 200 `{"status": "idle"|"streaming"|"error", "preview_id", "mode", "error"}`.
  - `DELETE /api/preview` → 204 (idempotente).
  - `WS /api/preview/stream` → binarios `[uint32 BE len][header JSON][JPEG]`; al terminar la sesión envía texto `{"type":"state","status":"idle"|"error","error":...}` y cierra; 4404 si no hay sesión activa, 4503 si no ready.
- `app.state.preview` = instancia de `PreviewManager`; `app.state.slot` = `ActivitySlot` compartido con `RunManager`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_preview_api.py
import json
import struct
import time

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from eovrt_media.service.app import create_app
from eovrt_media.service.settings import ServiceSettings

SET_INLINE = {"id": "t", "classes": [{"id": "p", "phrasings": {"default": ["p"]}}]}


@pytest.fixture()
def client(tmp_path):
    settings = ServiceSettings.from_env(
        {"EOVRT_MODEL_REF": "mock", "EOVRT_RUNS_DIR": str(tmp_path / "runs")}
    )
    with TestClient(create_app(settings)) as c:
        yield c


def _images(tmp_path, n=5):
    folder = tmp_path / "imgs"
    folder.mkdir(exist_ok=True)
    for i in range(n):
        Image.new("RGB", (64, 48), (i, 2, 3)).save(folder / f"f{i}.png")
    return folder


def _preview_body(folder, mode="raw"):
    body = {"mode": mode, "ingest": {"plugin": "image_folder", "config": {"path": str(folder)}}}
    if mode == "detect":
        body["prompts"] = {"set_inline": SET_INLINE}
    return body


def _run_body(folder):
    return {
        "ingest": {"plugin": "image_folder", "config": {"path": str(folder)}},
        "prompts": {"set_inline": SET_INLINE},
    }


def test_ciclo_basico(client, tmp_path):
    r = client.post("/api/preview", json=_preview_body(_images(tmp_path, n=200)))
    assert r.status_code == 201 and r.json()["preview_id"].startswith("pv_")
    assert client.get("/api/preview").json()["status"] == "streaming"
    assert client.delete("/api/preview").status_code == 204
    assert client.get("/api/preview").json()["status"] == "idle"
    assert client.delete("/api/preview").status_code == 204  # idempotente


def test_preview_409_si_run_activo(client, tmp_path):
    folder = _images(tmp_path, n=300)
    run = client.post("/api/runs", json=_run_body(folder))
    assert run.status_code == 201
    r = client.post("/api/preview", json=_preview_body(folder))
    assert r.status_code == 409
    body = r.json()
    assert body["reason"] == "run_active"
    assert body["active_run_id"] == run.json()["run_id"]
    client.post(f"/api/runs/{run.json()['run_id']}/stop")


def test_run_409_si_preview_activa(client, tmp_path):
    folder = _images(tmp_path, n=300)
    assert client.post("/api/preview", json=_preview_body(folder)).status_code == 201
    r = client.post("/api/runs", json=_run_body(folder))
    assert r.status_code == 409
    assert r.json()["reason"] == "preview_active"
    client.delete("/api/preview")


def test_preview_422_config_invalida(client, tmp_path):
    r = client.post("/api/preview", json=_preview_body(tmp_path / "no_existe"))
    assert r.status_code == 422


def test_ws_emite_frames_binarios(client, tmp_path):
    client.post("/api/preview", json=_preview_body(_images(tmp_path, n=500)))
    with client.websocket_connect("/api/preview/stream") as ws:
        msg = ws.receive_bytes()
        hlen = struct.unpack(">I", msg[:4])[0]
        header = json.loads(msg[4 : 4 + hlen].decode("utf-8"))
        assert header["mode"] == "raw" and header["seq"] >= 1
        assert msg[4 + hlen : 6 + hlen] == b"\xff\xd8"
    client.delete("/api/preview")


def test_ws_sin_sesion_cierra_4404(client):
    with client.websocket_connect("/api/preview/stream") as ws:
        data = ws.receive()
        assert data["type"] == "websocket.close"
        assert data["code"] == 4404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_preview_api.py -q`
Expected: FAIL con 404 en `/api/preview` (router inexistente)

- [ ] **Step 3: Write the router**

```python
# src/eovrt_media/service/routers/preview.py
"""Endpoints de la sesión de preview (sin persistencia)."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from eovrt_media.service.activity_slot import SlotBusyError
from eovrt_media.service.preview_manager import PreviewManager
from eovrt_media.service.preview_request import PreviewRequest

router = APIRouter(prefix="/api")

_POLL_SECONDS = 1 / 15


def _manager(request: Request) -> PreviewManager:
    if not getattr(request.app.state, "ready", False):
        raise HTTPException(status_code=503, detail="Servicio no listo (modelo no cargado)")
    return request.app.state.preview


@router.post("/preview", status_code=201)
def start_preview(body: PreviewRequest, request: Request):
    manager = _manager(request)
    try:
        preview_id = manager.start(body)
    except SlotBusyError as exc:
        content: dict = {"detail": str(exc)}
        if exc.owner_kind == "run":
            content["reason"] = "run_active"
            content["active_run_id"] = exc.owner_id
        else:
            content["reason"] = "preview_active"
        return JSONResponse(status_code=409, content=content)
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"preview_id": preview_id}


@router.get("/preview")
def preview_status(request: Request):
    return _manager(request).status()


@router.delete("/preview", status_code=204)
def stop_preview(request: Request):
    _manager(request).stop()


@router.websocket("/preview/stream")
async def stream_preview(ws: WebSocket) -> None:
    manager: PreviewManager | None = getattr(ws.app.state, "preview", None)
    if manager is None:
        await ws.accept()
        await ws.close(code=4503)
        return
    if not manager.is_active():
        await ws.accept()
        await ws.close(code=4404)
        return
    await ws.accept()
    last_seq = 0
    try:
        while True:
            status, seq, latest, error = manager.snapshot()
            if status != "streaming":
                await ws.send_json({"type": "state", "status": status, "error": error})
                break
            if seq != last_seq and latest is not None:
                await ws.send_bytes(latest)
                last_seq = seq
            await asyncio.sleep(_POLL_SECONDS)
    except WebSocketDisconnect:
        return
    await ws.close()
```

- [ ] **Step 4: Wire en `app.py`**

En `_lifespan`, después de `app.state.manager = RunManager(...)` (línea `:37`), crear el slot compartido y el preview manager. El slot se crea **antes** y se pasa a ambos:

```python
        from eovrt_media.service.activity_slot import ActivitySlot
        from eovrt_media.service.preview_manager import PreviewManager

        slot = ActivitySlot()
        app.state.manager = RunManager(adapter, model_section, settings, slot=slot)
        app.state.preview = PreviewManager(adapter, model_section, settings, slot)
```

En el shutdown del lifespan (junto a `manager.stop_active(...)`, `:54-61`), **antes** de cerrar el adapter:

```python
    preview = getattr(app.state, "preview", None)
    if preview is not None:
        preview.stop()
```

En `create_app` (`:64-75`), registrar el router:

```python
    from eovrt_media.service.routers import preview as preview_router
    app.include_router(preview_router.router)
```

(seguir el estilo de import del módulo: si los routers se importan arriba del archivo como `from eovrt_media.service.routers import health, model, runs, stream, catalog`, agregar `preview` a esa línea y `app.include_router(preview.router)`.)

- [ ] **Step 5: Run tests**

Run: `.venv/bin/python -m pytest tests/test_preview_api.py -q`
Expected: 6 passed

- [ ] **Step 6: Suite completa + lint del media-plane (no-regresión)**

Run: `cd /home/simonll4/projects/e-ovrt_media-plane && make test && make lint`
Expected: todo verde, cero regresiones

---

### Task 5: Presets de cámara — store + router `/api/cameras` (webconsole backend)

**Files:**
- Create: `webconsole/backend/src/eovrt_webconsole/camera_store.py`
- Create: `webconsole/backend/src/eovrt_webconsole/routers/cameras.py`
- Modify: `webconsole/backend/src/eovrt_webconsole/settings.py` (agregar property `cameras_dir`)
- Modify: `webconsole/backend/src/eovrt_webconsole/app.py:73-82` (registrar router)
- Test: `webconsole/backend/tests/test_camera_store.py`, `webconsole/backend/tests/test_cameras_router.py`

**Interfaces:**
- Produces: YAML por preset en `repo_root/cameras/{id}.yaml` con estructura `{"camera": {...}}`. `CameraPresetModel`: `id: str` (regex `^[a-z0-9_-]+$`), `name: str`, `plugin: str`, `config: dict`. Funciones módulo (primer arg `cameras_dir: Path`): `list_cameras -> list[dict]`, `get_camera(dir, id) -> dict`, `create_camera(dir, payload) -> dict`, `update_camera(dir, id, payload) -> dict`, `delete_camera(dir, id) -> None`. Errores: `CameraStoreError` base, `CameraNotFound`, `CameraExists`, `CameraInvalid(errors: list)`.
- Router: `APIRouter(prefix="/api/cameras")` — `GET ""`, `GET /{id}`, `POST "" (201)`, `PUT /{id}`, `DELETE /{id} (204)`. Mapeo: NotFound→404, Exists→409, Invalid→422 (mismo patrón `_raise` que `routers/prompts.py:17-27`).
- `ConsoleSettings.cameras_dir -> Path` = `repo_root / "cameras"` (property junto a `prompts_dir`, `settings.py:52-58`).

- [ ] **Step 1: Write the failing tests**

```python
# webconsole/backend/tests/test_camera_store.py
import pytest

from eovrt_webconsole import camera_store as cs

PRESET = {
    "id": "oak_d_lab",
    "name": "OAK-D laboratorio",
    "plugin": "oak_d",
    "config": {"url": "192.168.1.50"},
}


def test_create_y_get(tmp_path):
    created = cs.create_camera(tmp_path, PRESET)
    assert created["id"] == "oak_d_lab"
    assert (tmp_path / "oak_d_lab.yaml").exists()
    assert cs.get_camera(tmp_path, "oak_d_lab")["config"] == {"url": "192.168.1.50"}


def test_list(tmp_path):
    cs.create_camera(tmp_path, PRESET)
    cs.create_camera(tmp_path, {**PRESET, "id": "rtsp_norte", "plugin": "rtsp"})
    ids = [c["id"] for c in cs.list_cameras(tmp_path)]
    assert ids == ["oak_d_lab", "rtsp_norte"]


def test_create_duplicado(tmp_path):
    cs.create_camera(tmp_path, PRESET)
    with pytest.raises(cs.CameraExists):
        cs.create_camera(tmp_path, PRESET)


def test_update(tmp_path):
    cs.create_camera(tmp_path, PRESET)
    updated = cs.update_camera(tmp_path, "oak_d_lab", {**PRESET, "name": "OAK-D obra"})
    assert updated["name"] == "OAK-D obra"


def test_delete(tmp_path):
    cs.create_camera(tmp_path, PRESET)
    cs.delete_camera(tmp_path, "oak_d_lab")
    with pytest.raises(cs.CameraNotFound):
        cs.get_camera(tmp_path, "oak_d_lab")


def test_id_invalido(tmp_path):
    with pytest.raises(cs.CameraInvalid):
        cs.create_camera(tmp_path, {**PRESET, "id": "Oak D!"})


def test_get_inexistente(tmp_path):
    with pytest.raises(cs.CameraNotFound):
        cs.get_camera(tmp_path, "nada")
```

```python
# webconsole/backend/tests/test_cameras_router.py
PRESET = {
    "id": "oak_d_lab",
    "name": "OAK-D laboratorio",
    "plugin": "oak_d",
    "config": {"url": "192.168.1.50"},
}


async def test_crud_por_http(client):
    r = await client.post("/api/cameras", json=PRESET)
    assert r.status_code == 201
    r = await client.get("/api/cameras")
    assert [c["id"] for c in r.json()] == ["oak_d_lab"]
    r = await client.put("/api/cameras/oak_d_lab", json={**PRESET, "name": "otro"})
    assert r.json()["name"] == "otro"
    assert (await client.delete("/api/cameras/oak_d_lab")).status_code == 204
    assert (await client.get("/api/cameras/oak_d_lab")).status_code == 404


async def test_duplicado_409(client):
    assert (await client.post("/api/cameras", json=PRESET)).status_code == 201
    assert (await client.post("/api/cameras", json=PRESET)).status_code == 409


async def test_invalido_422(client):
    r = await client.post("/api/cameras", json={**PRESET, "id": "Oak D!"})
    assert r.status_code == 422
```

Nota: el fixture `client` existente (`conftest.py:102-107`) construye settings con `repo_root` de tmp; verificar que `cameras_dir` apunte dentro del tmp del test (si el conftest arma un repo_root sintético con `prompts/` y `experiments/`, `cameras/` se crea on-demand ahí — el store hace `mkdir(parents=True, exist_ok=True)` al escribir).

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/simonll4/projects/e-ovrt_experimental-setup/webconsole/backend && .venv/bin/python -m pytest tests/test_camera_store.py tests/test_cameras_router.py -q`
Expected: ERROR `ModuleNotFoundError: eovrt_webconsole.camera_store`

- [ ] **Step 3: Write the store**

```python
# webconsole/backend/src/eovrt_webconsole/camera_store.py
"""Presets de cámara para la ventana de preview. Un YAML por preset en cameras/.

La consola no valida la config de fuente: el media-plane es el validador final
(mismo principio que el prompt store).
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

_ID_RE = re.compile(r"^[a-z0-9_-]+$")


class CameraStoreError(Exception):
    pass


class CameraNotFound(CameraStoreError):
    pass


class CameraExists(CameraStoreError):
    pass


class CameraInvalid(CameraStoreError):
    def __init__(self, errors: list) -> None:
        super().__init__("preset de cámara inválido")
        self.errors = errors


class CameraPresetModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    plugin: str
    config: dict = {}

    @field_validator("id")
    @classmethod
    def _id_valido(cls, v: str) -> str:
        if not _ID_RE.match(v):
            raise ValueError("id debe matchear ^[a-z0-9_-]+$")
        return v


def _path(cameras_dir: Path, camera_id: str) -> Path:
    if not _ID_RE.match(camera_id):
        raise CameraNotFound(camera_id)
    return cameras_dir / f"{camera_id}.yaml"


def _validate(payload: dict) -> CameraPresetModel:
    try:
        return CameraPresetModel.model_validate(payload)
    except ValidationError as exc:
        raise CameraInvalid(exc.errors()) from exc


def _write(path: Path, preset: CameraPresetModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump({"camera": preset.model_dump()}, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def _read(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data.get("camera", {})


def list_cameras(cameras_dir: Path) -> list[dict]:
    if not cameras_dir.is_dir():
        return []
    return [_read(p) for p in sorted(cameras_dir.glob("*.yaml"))]


def get_camera(cameras_dir: Path, camera_id: str) -> dict:
    path = _path(cameras_dir, camera_id)
    if not path.exists():
        raise CameraNotFound(camera_id)
    return _read(path)


def create_camera(cameras_dir: Path, payload: dict) -> dict:
    preset = _validate(payload)
    path = _path(cameras_dir, preset.id)
    if path.exists():
        raise CameraExists(preset.id)
    _write(path, preset)
    return preset.model_dump()


def update_camera(cameras_dir: Path, camera_id: str, payload: dict) -> dict:
    if not _path(cameras_dir, camera_id).exists():
        raise CameraNotFound(camera_id)
    preset = _validate({**payload, "id": camera_id})
    _write(_path(cameras_dir, camera_id), preset)
    return preset.model_dump()


def delete_camera(cameras_dir: Path, camera_id: str) -> None:
    path = _path(cameras_dir, camera_id)
    if not path.exists():
        raise CameraNotFound(camera_id)
    path.unlink()
```

- [ ] **Step 4: Write the router + settings + wiring**

En `settings.py`, junto a `prompts_dir` (`:52-58`):

```python
    @property
    def cameras_dir(self) -> Path:
        return self.repo_root / "cameras"
```

```python
# webconsole/backend/src/eovrt_webconsole/routers/cameras.py
"""CRUD de presets de cámara (cameras/*.yaml)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.encoders import jsonable_encoder

from eovrt_webconsole import camera_store as cs

router = APIRouter(prefix="/api/cameras")


def _cameras_dir(request: Request):
    return request.app.state.settings.cameras_dir


def _raise(exc: cs.CameraStoreError) -> None:
    if isinstance(exc, cs.CameraNotFound):
        raise HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, cs.CameraExists):
        raise HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, cs.CameraInvalid):
        raise HTTPException(status_code=422, detail=jsonable_encoder(exc.errors))
    raise HTTPException(status_code=500, detail=str(exc))


@router.get("")
def list_cameras(request: Request) -> list[dict]:
    return cs.list_cameras(_cameras_dir(request))


@router.get("/{camera_id}")
def get_camera(request: Request, camera_id: str) -> dict:
    try:
        return cs.get_camera(_cameras_dir(request), camera_id)
    except cs.CameraStoreError as exc:
        _raise(exc)


@router.post("", status_code=201)
def create_camera(request: Request, payload: dict) -> dict:
    try:
        return cs.create_camera(_cameras_dir(request), payload)
    except cs.CameraStoreError as exc:
        _raise(exc)


@router.put("/{camera_id}")
def update_camera(request: Request, camera_id: str, payload: dict) -> dict:
    try:
        return cs.update_camera(_cameras_dir(request), camera_id, payload)
    except cs.CameraStoreError as exc:
        _raise(exc)


@router.delete("/{camera_id}", status_code=204)
def delete_camera(request: Request, camera_id: str) -> None:
    try:
        cs.delete_camera(_cameras_dir(request), camera_id)
    except cs.CameraStoreError as exc:
        _raise(exc)
```

En `app.py:73-82`, junto a los demás: `from eovrt_webconsole.routers import cameras` (sumarlo al import existente de routers) y `app.include_router(cameras.router)`.

- [ ] **Step 5: Run tests**

Run: `.venv/bin/python -m pytest tests/test_camera_store.py tests/test_cameras_router.py -q`
Expected: PASS

---

### Task 6: Proxy REST de preview — `RunBackend` + router + fake service (webconsole backend)

**Files:**
- Modify: `webconsole/backend/src/eovrt_webconsole/run_backend.py` (agregar excepción + 3 métodos)
- Create: `webconsole/backend/src/eovrt_webconsole/routers/preview.py`
- Modify: `webconsole/backend/src/eovrt_webconsole/app.py:73-82` (registrar router)
- Modify: `webconsole/backend/tests/fake_service.py` (endpoints de preview + campos en `FakeState`)
- Test: ampliar `webconsole/backend/tests/test_run_backend.py`, crear `webconsole/backend/tests/test_preview_router.py`

**Interfaces:**
- Produces en `run_backend.py`:

```python
class PreviewConflict(Exception):
    """409 del media-plane al iniciar preview; body completo del upstream."""
    def __init__(self, body: dict) -> None:
        super().__init__(body.get("detail", "slot ocupado"))
        self.body = body

async def preview_start(self, body: dict) -> dict   # POST /api/preview → {"preview_id"}
async def preview_status(self) -> dict              # GET /api/preview
async def preview_stop(self) -> None                # DELETE /api/preview
```

- Router BFF: `APIRouter(prefix="/api/preview")` — `POST ""` (201; 409 re-emite `exc.body` tal cual; 422 `ServiceRejected` → detail; `ServiceUnavailable` → 502), `GET ""`, `DELETE "" (204)`.
- `FakeState` gana: `preview_status: str = "idle"`, `preview_started: list[dict]`, `preview_stopped: int = 0`, `preview_conflict: dict | None = None` (si seteado, el fake responde 409 con ese body).

- [ ] **Step 1: Write the failing tests**

En `tests/test_run_backend.py` (sigue el patrón de `test_delete_*`, `:162-175` — los tests existentes construyen un `RunBackend` con transport al fake):

```python
async def test_preview_start_ok(backend, state):
    result = await backend.preview_start({"mode": "raw", "ingest": {"plugin": "rtsp", "config": {}}})
    assert result["preview_id"] == "pv_1"
    assert state.preview_started[0]["mode"] == "raw"


async def test_preview_start_409_run_activo(backend, state):
    state.preview_conflict = {"detail": "ocupado", "reason": "run_active", "active_run_id": "run_9"}
    with pytest.raises(PreviewConflict) as exc:
        await backend.preview_start({"mode": "raw", "ingest": {"plugin": "rtsp", "config": {}}})
    assert exc.value.body["reason"] == "run_active"


async def test_preview_status_y_stop(backend, state):
    state.preview_status = "streaming"
    assert (await backend.preview_status())["status"] == "streaming"
    await backend.preview_stop()
    assert state.preview_stopped == 1
```

(ajustar los nombres de fixtures a los reales del módulo — si el módulo usa un helper `_backend(state)` en vez de fixtures, seguir ese patrón; importar `PreviewConflict` desde `eovrt_webconsole.run_backend`.)

```python
# webconsole/backend/tests/test_preview_router.py
async def test_post_preview_ok(client, state):
    r = await client.post("/api/preview", json={"mode": "raw", "ingest": {"plugin": "rtsp", "config": {}}})
    assert r.status_code == 201
    assert r.json()["preview_id"] == "pv_1"


async def test_post_preview_409_passthrough(client, state):
    state.preview_conflict = {"detail": "ocupado", "reason": "run_active", "active_run_id": "run_9"}
    r = await client.post("/api/preview", json={"mode": "raw", "ingest": {"plugin": "rtsp", "config": {}}})
    assert r.status_code == 409
    assert r.json() == state.preview_conflict


async def test_get_y_delete_preview(client, state):
    state.preview_status = "streaming"
    assert (await client.get("/api/preview")).json()["status"] == "streaming"
    assert (await client.delete("/api/preview")).status_code == 204
    assert state.preview_stopped == 1
```

(el fixture `client` del conftest inyecta el fake service; `state` es la fixture de `FakeState` — usar los nombres reales del conftest, `conftest.py:102-107`.)

- [ ] **Step 2: Extender el fake service**

En `tests/fake_service.py` — campos en `FakeState` (`:88-106`):

```python
    preview_status: str = "idle"
    preview_started: list = field(default_factory=list)
    preview_stopped: int = 0
    preview_conflict: dict | None = None
```

Endpoints en `make_fake_service` (mismo estilo que el DELETE de runs, `:202-211`):

```python
    @app.post("/api/preview", status_code=201)
    def start_preview(body: dict):
        if state.preview_conflict is not None:
            return JSONResponse(status_code=409, content=state.preview_conflict)
        state.preview_started.append(body)
        state.preview_status = "streaming"
        return {"preview_id": "pv_1"}

    @app.get("/api/preview")
    def preview_status():
        return {"status": state.preview_status, "preview_id": None, "mode": None, "error": None}

    @app.delete("/api/preview", status_code=204)
    def stop_preview():
        state.preview_stopped += 1
        state.preview_status = "idle"
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_run_backend.py tests/test_preview_router.py -q`
Expected: FAIL (`ImportError: PreviewConflict`, 404 en `/api/preview` del BFF)

- [ ] **Step 4: Implement `RunBackend` methods + router**

En `run_backend.py`, junto a las demás excepciones (`:12-49`) la clase `PreviewConflict` del bloque Interfaces, y métodos (mismo estilo que `launch`/`delete`):

```python
    async def preview_start(self, body: dict) -> dict:
        try:
            response = await self._client.post("/api/preview", json=body)
        except httpx.HTTPError as exc:
            raise ServiceUnavailable(str(exc)) from exc
        if response.status_code == 409:
            raise PreviewConflict(response.json())
        if response.status_code == 422:
            raise ServiceRejected(response.json().get("detail", "config inválida"))
        if response.status_code >= 500 or response.status_code == 503:
            raise ServiceUnavailable(response.text)
        return response.json()

    async def preview_status(self) -> dict:
        return await self._get_json("/api/preview")

    async def preview_stop(self) -> None:
        try:
            response = await self._client.delete("/api/preview")
        except httpx.HTTPError as exc:
            raise ServiceUnavailable(str(exc)) from exc
        if response.status_code >= 500:
            raise ServiceUnavailable(response.text)
```

```python
# webconsole/backend/src/eovrt_webconsole/routers/preview.py
"""Proxy REST de la sesión de preview del media-plane."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from eovrt_webconsole.run_backend import PreviewConflict, ServiceRejected, ServiceUnavailable

router = APIRouter(prefix="/api/preview")


def _backend(request: Request):
    return request.app.state.backend


@router.post("", status_code=201)
async def start_preview(request: Request, payload: dict):
    try:
        return await _backend(request).preview_start(payload)
    except PreviewConflict as exc:
        return JSONResponse(status_code=409, content=exc.body)
    except ServiceRejected as exc:
        raise HTTPException(status_code=422, detail=exc.detail) from exc
    except ServiceUnavailable as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("")
async def preview_status(request: Request):
    try:
        return await _backend(request).preview_status()
    except ServiceUnavailable as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.delete("", status_code=204)
async def stop_preview(request: Request):
    try:
        await _backend(request).preview_stop()
    except ServiceUnavailable as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
```

Registrar en `app.py` junto a los demás routers: `app.include_router(preview.router)`.

Nota modo orquestado: si `app.state.backend` se resuelve distinto en modo orquestado (`TargetManager`), usar el mismo helper de acceso al backend que usa `routers/runs.py` — copiar su patrón exacto de obtención del backend, no inventar uno.

- [ ] **Step 5: Run tests**

Run: `.venv/bin/python -m pytest tests/test_run_backend.py tests/test_preview_router.py -q`
Expected: PASS

---

### Task 7: Proxy WS binario del preview (webconsole backend)

**Files:**
- Modify: `webconsole/backend/src/eovrt_webconsole/routers/preview.py` (agregar endpoint WS)
- Modify: `webconsole/backend/tests/fake_service.py` (WS fake que emite un frame binario)
- Test: ampliar `webconsole/backend/tests/test_stream_proxy.py` (usa el fixture `live_client` con uvicorn real, `conftest.py:124-150`)

**Interfaces:**
- Produces: `WS /api/preview/stream` en el BFF — pasa mensajes del upstream tal cual (`bytes` → `send_bytes`, `str` → `send_text`), sin coalescing (el media-plane ya pacea enviando solo el último frame). Cierre: upstream caído/inaccesible → close 4503; cliente desconectado → cerrar upstream y salir; usa `_safe_close_code` existente de `routers/stream.py:53-61` (importarlo o replicarlo).

- [ ] **Step 1: Write the failing test**

En `tests/test_stream_proxy.py` (mismo estilo que `test_ws_proxy_reenvia_eventos`; el fixture `live_client` levanta el fake en uvicorn real):

```python
def test_ws_preview_reenvia_binario(live_client):
    import json
    import struct

    with live_client.websocket_connect("/api/preview/stream") as ws:
        msg = ws.receive_bytes()
        hlen = struct.unpack(">I", msg[:4])[0]
        header = json.loads(msg[4 : 4 + hlen].decode("utf-8"))
        assert header["seq"] == 1
        assert msg[4 + hlen :] == b"\xff\xd8fake"


def test_ws_preview_servicio_inaccesible_no_crashea(live_client_sin_upstream):
    with live_client_sin_upstream.websocket_connect("/api/preview/stream") as ws:
        data = ws.receive()
        assert data["type"] == "websocket.close"
```

(si no existe un fixture "sin upstream", seguir el patrón del test existente `test_ws_servicio_inaccesible_no_crashea` de ese archivo — reutilizar su mecánica exacta.)

- [ ] **Step 2: WS fake en `fake_service.py`**

```python
    @app.websocket("/api/preview/stream")
    async def fake_preview_stream(ws: WebSocket):
        await ws.accept()
        header = json.dumps(
            {"seq": 1, "ts": 0.0, "width": 64, "height": 48, "mode": "raw", "detections": []}
        ).encode("utf-8")
        await ws.send_bytes(struct.pack(">I", len(header)) + header + b"\xff\xd8fake")
        await ws.send_json({"type": "state", "status": "idle", "error": None})
        await ws.close()
```

(imports `json`, `struct`, `WebSocket` según ya tenga el módulo.)

- [ ] **Step 3: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_stream_proxy.py -q`
Expected: FAIL — el WS `/api/preview/stream` del BFF no existe (404/close inmediato)

- [ ] **Step 4: Implement el proxy WS**

En `routers/preview.py` (el prefix del router aplica también a websockets):

```python
import asyncio

import websockets
import websockets.exceptions
from fastapi import WebSocket, WebSocketDisconnect

from eovrt_webconsole.routers.stream import _safe_close_code


def _preview_ws_url(service_url: str) -> str:
    base = service_url.replace("http://", "ws://", 1).replace("https://", "wss://", 1)
    return f"{base}/api/preview/stream"


@router.websocket("/stream")
async def preview_stream_ws(websocket: WebSocket) -> None:
    settings = websocket.app.state.settings
    await websocket.accept()
    close_code = 1000
    try:
        async with websockets.connect(_preview_ws_url(settings.service_url)) as upstream:

            async def _pump() -> None:
                async for raw in upstream:
                    if isinstance(raw, bytes):
                        await websocket.send_bytes(raw)
                    else:
                        await websocket.send_text(raw)

            async def _watch_client() -> None:
                while True:
                    await websocket.receive()

            pump = asyncio.create_task(_pump())
            watch = asyncio.create_task(_watch_client())
            done, pending = await asyncio.wait({pump, watch}, return_when=asyncio.FIRST_COMPLETED)
            for task in pending:
                task.cancel()
            if pump in done and pump.exception() is None:
                close_code = _safe_close_code(upstream.close_code)
    except (OSError, websockets.exceptions.WebSocketException):
        close_code = 4503
    except WebSocketDisconnect:
        return
    try:
        await websocket.close(code=close_code)
    except RuntimeError:
        pass
```

(Si `_safe_close_code` no es importable limpio, moverlo a un módulo común `ws_utils.py` o replicarlo — decisión del implementador siguiendo el estilo del repo. `_watch_client` termina con `WebSocketDisconnect` cuando el SPA se va, igual que en `stream.py:107-117`.)

- [ ] **Step 5: Run tests + suite backend completa**

Run: `.venv/bin/python -m pytest tests/test_stream_proxy.py -q && .venv/bin/python -m pytest -q && .venv/bin/ruff check src tests`
Expected: PASS, sin regresiones

---

### Task 8: Frontend — API client + hook `usePreviewStream`

**Files:**
- Modify: `webconsole/frontend/src/api.ts`
- Create: `webconsole/frontend/src/preview.ts`
- Modify: `webconsole/frontend/src/types.ts` (tipos nuevos)
- Test: `webconsole/frontend/src/__tests__/preview.test.ts`

**Interfaces:**
- Produces en `types.ts`:

```ts
export interface CameraPreset { id: string; name: string; plugin: string; config: Record<string, unknown> }
export interface PreviewDetection { label: string; score: number; bbox_norm_xyxy: [number, number, number, number] }
export interface PreviewFrameHeader {
  seq: number; ts: number; width: number; height: number
  mode: 'raw' | 'detect'; detections: PreviewDetection[]
}
export interface PreviewStatus {
  status: 'idle' | 'streaming' | 'error'
  preview_id: string | null; mode: string | null; error: string | null
}
export interface PreviewStartBody {
  mode: 'raw' | 'detect'
  ingest: { plugin: string; config: Record<string, unknown> }
  prompts?: { set_inline: Record<string, unknown>; active_ids?: string[] }
  params?: { score_threshold?: number | null }
}
```

- Produces en `api.ts` (mismo wrapper `request<T>` existente, `api.ts:17-33`):

```ts
export const listCameras = () => request<CameraPreset[]>('/api/cameras')
export const createCamera = (p: CameraPreset) => request<CameraPreset>('/api/cameras', { method: 'POST', body: JSON.stringify(p) })
export const updateCamera = (id: string, p: CameraPreset) => request<CameraPreset>(`/api/cameras/${id}`, { method: 'PUT', body: JSON.stringify(p) })
export const deleteCamera = (id: string) => request<undefined>(`/api/cameras/${id}`, { method: 'DELETE' })
export const startPreview = (body: PreviewStartBody) => request<{ preview_id: string }>('/api/preview', { method: 'POST', body: JSON.stringify(body) })
export const getPreview = () => request<PreviewStatus>('/api/preview')
export const stopPreview = () => request<undefined>('/api/preview', { method: 'DELETE' })
export function previewStreamUrl(): string {
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
  return `${proto}://${window.location.host}/api/preview/stream`
}
```

- Produces en `preview.ts`: `parsePreviewMessage(data: ArrayBuffer): { header: PreviewFrameHeader; jpeg: Blob }` (exportada para test) y hook `usePreviewStream(enabled: boolean): PreviewLive` con

```ts
export interface PreviewLive {
  connected: boolean
  frameUrl: string | null            // object URL del JPEG actual (se revoca el anterior)
  header: PreviewFrameHeader | null
  fps: number                        // medido en cliente (frames del último segundo)
  finalState: { status: string; error: string | null } | null
}
```

- [ ] **Step 1: Write the failing tests**

```ts
// webconsole/frontend/src/__tests__/preview.test.ts
import { describe, expect, it } from 'vitest'
import { parsePreviewMessage } from '../preview'

function buildMessage(header: object, jpeg: Uint8Array): ArrayBuffer {
  const hb = new TextEncoder().encode(JSON.stringify(header))
  const buf = new Uint8Array(4 + hb.length + jpeg.length)
  new DataView(buf.buffer).setUint32(0, hb.length)
  buf.set(hb, 4)
  buf.set(jpeg, 4 + hb.length)
  return buf.buffer
}

describe('parsePreviewMessage', () => {
  it('separa header JSON y payload JPEG', () => {
    const header = { seq: 3, ts: 1.5, width: 64, height: 48, mode: 'raw', detections: [] }
    const { header: parsed, jpeg } = parsePreviewMessage(buildMessage(header, new Uint8Array([0xff, 0xd8, 1])))
    expect(parsed.seq).toBe(3)
    expect(parsed.mode).toBe('raw')
    expect(jpeg.size).toBe(3)
  })

  it('conserva las detecciones', () => {
    const det = { label: 'helmet', score: 0.9, bbox_norm_xyxy: [0.1, 0.1, 0.5, 0.5] }
    const header = { seq: 1, ts: 0, width: 64, height: 48, mode: 'detect', detections: [det] }
    const { header: parsed } = parsePreviewMessage(buildMessage(header, new Uint8Array([0xff, 0xd8])))
    expect(parsed.detections).toEqual([det])
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/simonll4/projects/e-ovrt_experimental-setup/webconsole/frontend && npx vitest run src/__tests__/preview.test.ts`
Expected: FAIL — módulo `../preview` inexistente

- [ ] **Step 3: Implement `preview.ts` + `api.ts` + `types.ts`**

Tipos y funciones de `api.ts` como en el bloque Interfaces. Hook:

```ts
// webconsole/frontend/src/preview.ts
import { useEffect, useRef, useState } from 'react'
import { previewStreamUrl } from './api'
import type { PreviewFrameHeader } from './types'

export interface PreviewLive {
  connected: boolean
  frameUrl: string | null
  header: PreviewFrameHeader | null
  fps: number
  finalState: { status: string; error: string | null } | null
}

export function parsePreviewMessage(data: ArrayBuffer): { header: PreviewFrameHeader; jpeg: Blob } {
  const view = new DataView(data)
  const headerLen = view.getUint32(0)
  const header = JSON.parse(
    new TextDecoder().decode(new Uint8Array(data, 4, headerLen)),
  ) as PreviewFrameHeader
  const jpeg = new Blob([new Uint8Array(data, 4 + headerLen)], { type: 'image/jpeg' })
  return { header, jpeg }
}

const INITIAL: PreviewLive = { connected: false, frameUrl: null, header: null, fps: 0, finalState: null }

export function usePreviewStream(enabled: boolean): PreviewLive {
  const [state, setState] = useState<PreviewLive>(INITIAL)
  const urlRef = useRef<string | null>(null)
  const timesRef = useRef<number[]>([])

  useEffect(() => {
    if (!enabled) {
      setState(INITIAL)
      return
    }
    const ws = new WebSocket(previewStreamUrl())
    ws.binaryType = 'arraybuffer'
    ws.onopen = () => setState((s) => ({ ...s, connected: true }))
    ws.onmessage = (ev) => {
      if (typeof ev.data === 'string') {
        const parsed = JSON.parse(ev.data) as { type: string; status: string; error: string | null }
        if (parsed.type === 'state') {
          setState((s) => ({ ...s, finalState: { status: parsed.status, error: parsed.error } }))
        }
        return
      }
      const { header, jpeg } = parsePreviewMessage(ev.data as ArrayBuffer)
      const url = URL.createObjectURL(jpeg)
      if (urlRef.current) URL.revokeObjectURL(urlRef.current)
      urlRef.current = url
      const now = performance.now()
      timesRef.current = [...timesRef.current.filter((t) => now - t < 1000), now]
      setState((s) => ({ ...s, frameUrl: url, header, fps: timesRef.current.length }))
    }
    ws.onclose = () => setState((s) => ({ ...s, connected: false }))
    return () => {
      ws.close()
      if (urlRef.current) URL.revokeObjectURL(urlRef.current)
      urlRef.current = null
      timesRef.current = []
    }
  }, [enabled])

  return state
}
```

- [ ] **Step 4: Run tests**

Run: `npx vitest run src/__tests__/preview.test.ts`
Expected: PASS

---

### Task 9: Frontend — página `/cameras` + ruta y nav

**Files:**
- Create: `webconsole/frontend/src/pages/CamerasPage.tsx`
- Create: `webconsole/frontend/src/components/CameraPresetForm.tsx`
- Create: `webconsole/frontend/src/components/LivePromptPanel.tsx`
- Modify: `webconsole/frontend/src/App.tsx:17-25` (ruta), `webconsole/frontend/src/nav.ts:4-24` (nav)
- Test: `webconsole/frontend/src/__tests__/CamerasPage.test.tsx`, ampliar `webconsole/frontend/src/__tests__/nav.test.ts`

**Interfaces:**
- Consumes: `listCameras/createCamera/updateCamera/deleteCamera/startPreview/getPreview/stopPreview` y `ApiError` de `api.ts`; `usePreviewStream` de `preview.ts`; `listPromptSets/getPromptSetDetail/createPromptSet` de `api.ts` (existentes); `PreviewWithBoxes` (`components/PreviewWithBoxes.tsx`, props `{src, alt, detections, width}` con `bbox_norm_xyxy`+`label`); kit `Badge, Card, ErrorBanner, EmptyState, Field, DetChip` de `components/ui`.
- Produces: página con layout de 3 columnas (CSS grid con clases `eo-*` del design system):
  1. **Presets**: lista (`listCameras`), botón "Conectar" por preset, `CameraPresetForm` para crear/editar/borrar (campos: id, name, plugin `<select>` con `rtsp`/`oak_d`/`video_file`/`image_folder`, config como textarea JSON con validación de parseo).
  2. **Viewer**: si `frameUrl` → `<PreviewWithBoxes src={frameUrl} alt="preview" detections={header.detections} width={100} />` + fila de estado (`Badge` conectado/desconectado, fps, modo, `DetChip` por label con conteo agregado del frame actual). Si no → `EmptyState`.
  3. **Panel de detección** (`LivePromptPanel`): toggle "Solo video / Detección". En detección: `<select>` de prompt sets (`listPromptSets`), al elegir carga `getPromptSetDetail` a un draft local; por clase: checkbox enabled + textarea por cada clave de `phrasings` (una frase por línea); slider `score_threshold` (0–1, step 0.05); botón **Aplicar** y botón **Guardar como set nuevo** (pide id nuevo con un input, llama `createPromptSet` con el draft — nace `exploratory`).
- Flujo conectar/aplicar: `stopPreview()` (ignorando error si idle) → `startPreview(body)` → `setEnabled(true)` (activa `usePreviewStream`). El body arma `ingest` desde el preset y, en detección, `prompts.set_inline` desde el draft (solo clases enabled en `active_ids`… no: el draft ya excluye/incluye por `enabled_by_default`; enviar el set completo con `active_ids` = ids de clases tildadas).
- Manejo 409: `ApiError.status === 409` → leer `payload.reason`; `run_active` → `ErrorBanner` "Hay un run en ejecución: {active_run_id}. Detenelo para usar la prueba de cámaras." + link `#/runs/{id}`, botones Conectar deshabilitados hasta re-chequear (`getPreview` + reintento manual con botón "Reintentar").
- Al montar la página: `getPreview()` — si ya hay una sesión `streaming`, ofrecer "Retomar stream" (habilita el WS sin POST) o "Detener".
- Badge "modelo: mock" si `GET /api/meta` o el endpoint de modelo existente lo indica (usar `request<...>('/api/model')` si el BFF ya lo proxya vía `RunBackend.model()`; si no hay ruta expuesta en el BFF, omitir el badge — decisión del implementador, no agregar endpoint nuevo solo para esto).
- Nav: en `NAV_GROUPS`, grupo **Sistema**: agregar `{ to: '/cameras', label: 'Cámaras' }`. Ruta en `App.tsx`: `<Route path="/cameras" element={<CamerasPage />} />`.
- Cleanup al desmontar la página: `stopPreview()` best-effort (fire-and-forget) para no dejar la fuente tomada.

- [ ] **Step 1: Write the failing tests**

```tsx
// webconsole/frontend/src/__tests__/CamerasPage.test.tsx
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import CamerasPage from '../pages/CamerasPage'

const mocks = vi.hoisted(() => ({
  listCameras: vi.fn(),
  getPreview: vi.fn(),
  listPromptSets: vi.fn(),
  startPreview: vi.fn(),
  stopPreview: vi.fn(),
}))

vi.mock('../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api')>()),
  ...mocks,
}))

vi.mock('../preview', () => ({
  usePreviewStream: () => ({ connected: false, frameUrl: null, header: null, fps: 0, finalState: null }),
}))

beforeEach(() => {
  vi.clearAllMocks()
  mocks.listCameras.mockResolvedValue([
    { id: 'oak_d_lab', name: 'OAK-D laboratorio', plugin: 'oak_d', config: {} },
  ])
  mocks.getPreview.mockResolvedValue({ status: 'idle', preview_id: null, mode: null, error: null })
  mocks.listPromptSets.mockResolvedValue([])
})

function renderPage() {
  return render(
    <MemoryRouter>
      <CamerasPage />
    </MemoryRouter>,
  )
}

describe('CamerasPage', () => {
  it('lista los presets de cámara', async () => {
    renderPage()
    expect(await screen.findByText('OAK-D laboratorio')).toBeTruthy()
  })

  it('muestra empty state sin stream', async () => {
    renderPage()
    await waitFor(() => expect(mocks.getPreview).toHaveBeenCalled())
    expect(screen.getByText(/sin señal/i)).toBeTruthy()
  })

  it('muestra banner y deshabilita conectar ante 409 run_active', async () => {
    const { ApiError } = await import('../api')
    mocks.startPreview.mockRejectedValue(
      new ApiError(409, { detail: 'ocupado', reason: 'run_active', active_run_id: 'run_7' }),
    )
    renderPage()
    const conectar = await screen.findByRole('button', { name: /conectar/i })
    conectar.click()
    expect(await screen.findByText(/run en ejecución/i)).toBeTruthy()
    expect(screen.getByText(/run_7/)).toBeTruthy()
  })
})
```

Y en `nav.test.ts`, sumar la aserción al test del grupo Sistema (o crear uno):

```ts
it('incluye Cámaras en Sistema', () => {
  const sistema = NAV_GROUPS.find((g) => g.title === 'Sistema')!
  expect(sistema.items.map((i) => i.to)).toContain('/cameras')
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx vitest run src/__tests__/CamerasPage.test.tsx src/__tests__/nav.test.ts`
Expected: FAIL — `CamerasPage` inexistente / nav sin `/cameras`

- [ ] **Step 3: Implement**

`nav.ts`: agregar el item al grupo Sistema. `App.tsx`: import + `<Route path="/cameras" element={<CamerasPage />} />`. `crumbsFor` en `nav.ts` resuelve labels desde `NAV_GROUPS`, así que `/cameras` queda cubierto automáticamente (verificarlo; si usa regexes por ruta, agregar el caso).

`CamerasPage.tsx` — estructura (el implementador completa el JSX con el kit y las clases `eo-*` existentes, siguiendo `ComposePage`/`RunDetailPage` como referencia de estilo):

```tsx
export default function CamerasPage() {
  const [presets, setPresets] = useState<CameraPreset[]>([])
  const [selected, setSelected] = useState<CameraPreset | null>(null)
  const [mode, setMode] = useState<'raw' | 'detect'>('raw')
  const [threshold, setThreshold] = useState<number | null>(null)
  const [promptDraft, setPromptDraft] = useState<PromptSetDetail | null>(null)
  const [activeClassIds, setActiveClassIds] = useState<string[]>([])
  const [streaming, setStreaming] = useState(false)
  const [busy, setBusy] = useState<{ reason: string; runId?: string } | null>(null)
  const [error, setError] = useState<string | null>(null)
  const live = usePreviewStream(streaming)

  useEffect(() => { void listCameras().then(setPresets) }, [])
  useEffect(() => {
    void getPreview().then((s) => { if (s.status === 'streaming') setStreaming(true) })
    return () => { void stopPreview().catch(() => undefined) }
  }, [])

  async function connect(preset: CameraPreset) {
    setError(null); setBusy(null)
    const body: PreviewStartBody = { mode, ingest: { plugin: preset.plugin, config: preset.config } }
    if (mode === 'detect' && promptDraft) {
      body.prompts = { set_inline: draftToSetInline(promptDraft), active_ids: activeClassIds }
      body.params = { score_threshold: threshold }
    }
    try {
      await stopPreview().catch(() => undefined)
      setStreaming(false)
      await startPreview(body)
      setSelected(preset)
      setStreaming(true)
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        const p = (e.payload ?? {}) as { reason?: string; active_run_id?: string }
        setBusy({ reason: p.reason ?? 'run_active', runId: p.active_run_id })
      } else {
        setError(e instanceof Error ? e.message : String(e))
      }
    }
  }
  // ... disconnect() = stopPreview + setStreaming(false)
  // ... render: grid 3 columnas según Interfaces; EmptyState "Sin señal — conectá una cámara"
}
```

`LivePromptPanel.tsx` — props:

```tsx
interface Props {
  mode: 'raw' | 'detect'
  onModeChange: (m: 'raw' | 'detect') => void
  draft: PromptSetDetail | null
  onDraftChange: (d: PromptSetDetail) => void
  activeClassIds: string[]
  onActiveChange: (ids: string[]) => void
  threshold: number | null
  onThresholdChange: (t: number | null) => void
  onApply: () => void
  disabled: boolean
}
```

Carga de sets dentro del panel (`listPromptSets` + `getPromptSetDetail`), edición de frases con un textarea por clave de `phrasings` (split por `\n`, filtrando vacíos), y "Guardar como set nuevo" con `createPromptSet({ ...draft, id: nuevoId, status: undefined })`.

`CameraPresetForm.tsx` — props `{ initial: CameraPreset | null, onSaved: () => void, onClose: () => void }`; usa `Field`, valida el JSON de `config` con `JSON.parse` en try/catch mostrando el error en el `Field`.

`draftToSetInline(draft)`: devuelve `{ id: draft.id, classes: draft.classes.map(...) }` con la forma exacta que espera el media-plane (la misma que ya produce `translation.py` del BFF para runs — espejarla desde el shape de `PromptSetDetail`).

- [ ] **Step 4: Run tests**

Run: `npx vitest run src/__tests__/CamerasPage.test.tsx src/__tests__/nav.test.ts`
Expected: PASS

---

### Task 10: ComposePage — aviso de preview activa + verificación final

**Files:**
- Modify: `webconsole/frontend/src/pages/ComposePage.tsx:121-140` (handler 409) y `:285-289` (render del aviso)
- Test: ampliar `webconsole/frontend/src/__tests__/ComposePage.test.tsx`

**Interfaces:**
- Consumes: el 409 del BFF al lanzar run ahora puede traer `{"reason": "preview_active"}` (Task 2/4). El shape previo (`active_run_id`) sigue igual.

- [ ] **Step 1: Write the failing test**

En `ComposePage.test.tsx`, siguiendo el patrón de los tests de 409 existentes en ese archivo (mock de `launchRun` rechazando con `ApiError`):

```tsx
it('muestra aviso de prueba de cámara activa ante 409 preview_active', async () => {
  mocks.launchRun.mockRejectedValue(
    new ApiError(409, { detail: 'ocupado', reason: 'preview_active' }),
  )
  // ... (mismo setup/submit que el test de 409 run activo existente)
  expect(await screen.findByText(/prueba de cámara activa/i)).toBeTruthy()
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/__tests__/ComposePage.test.tsx`
Expected: FAIL — el texto no existe

- [ ] **Step 3: Implement**

En `ComposePage.tsx`, ampliar el estado y el handler:

```tsx
const [busyRunId, setBusyRunId] = useState<string | null>(null)
const [previewBusy, setPreviewBusy] = useState(false)
// en submit():
} else if (e instanceof ApiError && e.status === 409) {
  const payload = (e.payload ?? {}) as { active_run_id?: string; reason?: string }
  if (payload.reason === 'preview_active') {
    setPreviewBusy(true)
    setBusyRunId(null)
  } else {
    setBusyRunId(payload.active_run_id ?? null)
    setPreviewBusy(false)
  }
}
// en el render, junto al aviso de busyRunId existente:
{previewBusy && (
  <p className="eo-note eo-note--warn">
    Hay una prueba de cámara activa. Cerrala en <a href="#/cameras">Cámaras</a> para lanzar el run.
  </p>
)}
```

- [ ] **Step 4: Run test**

Run: `npx vitest run src/__tests__/ComposePage.test.tsx`
Expected: PASS

- [ ] **Step 5: Verificación final de no-regresión (los tres frentes)**

```bash
cd /home/simonll4/projects/e-ovrt_media-plane && make test && make lint
cd /home/simonll4/projects/e-ovrt_experimental-setup/webconsole/backend && .venv/bin/python -m pytest -q && .venv/bin/ruff check src tests
cd /home/simonll4/projects/e-ovrt_experimental-setup/webconsole/frontend && npx vitest run
```

Expected: las tres suites completas en verde.

- [ ] **Step 6: Smoke manual opcional (sin hardware)**

```bash
cd /home/simonll4/projects/e-ovrt_media-plane && EOVRT_MODEL_REF=mock make serve &
cd /home/simonll4/projects/e-ovrt_experimental-setup/webconsole && # levantar BFF+SPA como de costumbre
# En la UI: /cameras → crear preset image_folder apuntando a un split de datasets → Conectar (raw)
# → ver frames; activar Detección con un set del catálogo → ver cajas del mock.
```

Reportar resultado al usuario; el smoke con OAK-D/RTSP reales queda como verificación manual del usuario (spec §6).
