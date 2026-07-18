# Evaluación BENCH + compare-runs en la consola — Plan de implementación

> **Estado: COMPLETO (12/12 tasks + verificación final).** Whole-branch review "Ready to merge". Verificado end-to-end con GPU real (RTX 4060): GDINO-tiny mAP@0.5=0.4197, YOLOE-26s mAP@0.5=0.3561 sobre bench_v2_test completo (82 imgs); `/api/compare` agregando ambos runs correctamente. Detalle en `.superpowers/sdd/progress-bench-eval-console.md`.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Evaluar runs BENCH terminados contra el GT desde la consola (AP@0.5 por clase, CR-01 recall, mAP@0.5) y comparar N runs con tabla + gráfico de barras agrupadas.

**Architecture:** Tres capas: (1) el servicio media-plane corre la evaluación (único con artefactos + GT + `eovrt_media.evaluation`), expone `bench_split`/`evaluated` en el info del run y persiste `eval_perception.json` enriquecido y atómico; (2) el BFF de la webconsole proxya evaluate/get_evaluation y agrega el compare de N runs; (3) el frontend React agrega la sección "Evaluar contra BENCH" en el detalle del run y la página `/compare` con `GroupedBars` (SVG propio).

**Tech Stack:** FastAPI + pydantic v2 + pytest (ambos backends), httpx (BFF→servicio), React 18 + TS strict + vitest (frontend). Sin dependencias nuevas.

**Spec:** `docs/superpowers/specs/2026-07-04-bench-eval-console-design.md` (mismo repo).

## Global Constraints

- **NO COMMITS**: regla del workspace (`projects/CLAUDE.md`) — nunca correr `git commit`; dejar los cambios en el working tree. El usuario commitea explícitamente. Por eso **ningún task tiene paso de commit**.
- **Dos repos**: tasks 1–4 en `/home/simonll4/projects/e-ovrt_media-plane` (branch `feature/inference-service`); tasks 5–11 en `/home/simonll4/projects/e-ovrt_experimental-setup` (branch `feature/webconsole`). Verificar el branch antes de editar.
- **El BFF nunca importa `eovrt_media`** — solo habla HTTP con el servicio.
- El servicio corre desde la raíz del media-plane: el auto-descubrimiento del GT usa paths relativos al CWD (`../e-ovrt_datasets/...`). GT ausente → 422 accionable, nunca 500.
- IoU default `0.5`, override por env `EOVRT_EVAL_IOU_THRESHOLD` (sin tuning desde la UI).
- Splits BENCH reconocidos: `bench_v2_test`, `bench_v2_val` (ambos cubiertos por el único GT COCO `construction_site_safety_bench.json` + `person_gt.json`).
- `AP50` es `float | None` (`null` = clase sin GT; `0.0` = con GT y 0 matches). `mAP50` = media de los `AP50` no-nulos, `null` si todos son `null`.
- **NO (YAGNI)**: export CSV/JSON, eval automática al terminar, AP@[.5:.95]/PR curves, eval de runs de video, librerías de charts.
- Comandos de test:
  - media-plane: `cd /home/simonll4/projects/e-ovrt_media-plane && .venv/bin/python -m pytest <file> -q`
  - BFF: `cd /home/simonll4/projects/e-ovrt_experimental-setup/webconsole/backend && .venv/bin/python -m pytest <file> -q`
  - frontend: `cd /home/simonll4/projects/e-ovrt_experimental-setup/webconsole/frontend && npm test` (vitest run) y `npm run build` (tsc strict + vite).

---

### Task 1: `run_evaluation` — parámetros `restrict_gt_to_detections` y `persist`

**Files:**
- Modify: `e-ovrt_media-plane/src/eovrt_media/evaluation/runner.py:86-139`
- Test: `e-ovrt_media-plane/tests/test_evaluate.py` (extender)

**Interfaces:**
- Consumes: `evaluate_bench.load_detections/load_bench_coco/load_person_gt/evaluate_class/evaluate_cr01` (script hermano, ya cargado dinámicamente).
- Produces: `run_evaluation(run_dir, bench_coco=None, person_gt=None, iou_threshold=0.5, restrict_gt_to_detections=False, persist=True) -> EvalPerceptionResults`. Los defaults preservan el comportamiento del CLI (`tools/evaluate.py` no cambia). Task 3 la llama con `restrict_gt_to_detections=True, persist=False`.

Contexto de datos (verificado en `e-ovrt_datasets/datasets/scripts/bench/evaluate_bench.py`):
- `detections_by_img: dict[basename, list[det]]` — `load_detections` crea la key para toda imagen procesada, aun con 0 detecciones (`setdefault(...).extend(...)`), así que "imágenes del run" = keys de este dict.
- `images_by_filename: dict[basename, img]` (del COCO), `gt_by_image_id: dict[image_id, list[ann]]`, `person_gt_records: list[{file_name, has_helmet, person_bbox}]`.
- `evaluate_class` cuenta `n_gt` desde `gt_by_image_id` y recorre `images_by_filename` para las detecciones; `evaluate_cr01` recorre `person_gt_records`. Filtrar esas tres estructuras a las imágenes del run implementa la restricción.

- [x] **Step 1: Escribir los tests que fallan**

Agregar al final de `tests/test_evaluate.py`:

```python
def _capturing_evaluator(captured: dict) -> SimpleNamespace:
    """Evaluador sintético que captura las estructuras que recibe (para
    verificar la restricción del GT) y devuelve n_gt derivado del GT recibido."""

    def evaluate_class(
        class_name, _detections_by_img, images_by_filename, gt_by_image_id, _cat_by_id, _iou
    ):
        captured["images_by_filename"] = images_by_filename
        captured["gt_by_image_id"] = gt_by_image_id
        n_gt = sum(len(anns) for anns in gt_by_image_id.values())
        return {"class": class_name, "AP50": 0.5, "n_gt": n_gt, "n_det": 0}

    def evaluate_cr01(person_gt_records, *_args):
        captured["person_gt_records"] = person_gt_records
        return {"cr01_recall": None}

    return SimpleNamespace(
        # El run procesó img001/img002; img003 está en el BENCH pero NO en el run.
        load_detections=lambda _paths: {"img001.jpg": [], "img002.jpg": []},
        load_bench_coco=lambda _path: (
            {"img001.jpg": {"id": 1}, "img002.jpg": {"id": 2}, "img003.jpg": {"id": 3}},
            {1: [{"category_id": 1}], 3: [{"category_id": 1}, {"category_id": 1}]},
            {1: "person"},
        ),
        load_person_gt=lambda _path: [
            {"file_name": "/data/img001.jpg", "has_helmet": False, "person_bbox": [0, 0, 10, 30]},
            {"file_name": "/data/img003.jpg", "has_helmet": False, "person_bbox": [0, 0, 10, 30]},
        ],
        evaluate_class=evaluate_class,
        evaluate_cr01=evaluate_cr01,
    )


def test_restrict_gt_filtra_a_las_imagenes_del_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_dir = tmp_path / "run_r1"
    run_dir.mkdir()
    _write_detections(run_dir)
    bench_coco, person_gt = _write_benchmark(tmp_path)
    captured: dict = {}
    monkeypatch.setattr(runner, "_load_evaluate_bench", lambda: _capturing_evaluator(captured))

    result = run_evaluation(
        run_dir, bench_coco=bench_coco, person_gt=person_gt, restrict_gt_to_detections=True
    )

    assert set(captured["images_by_filename"]) == {"img001.jpg", "img002.jpg"}
    assert set(captured["gt_by_image_id"]) == {1}
    assert [Path(r["file_name"]).name for r in captured["person_gt_records"]] == ["img001.jpg"]
    assert result.per_class[0].n_gt == 1  # no 3: img003 quedó fuera


def test_sin_restrict_conserva_el_gt_completo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_dir = tmp_path / "run_r2"
    run_dir.mkdir()
    _write_detections(run_dir)
    bench_coco, person_gt = _write_benchmark(tmp_path)
    captured: dict = {}
    monkeypatch.setattr(runner, "_load_evaluate_bench", lambda: _capturing_evaluator(captured))

    result = run_evaluation(run_dir, bench_coco=bench_coco, person_gt=person_gt)

    assert set(captured["images_by_filename"]) == {"img001.jpg", "img002.jpg", "img003.jpg"}
    assert set(captured["gt_by_image_id"]) == {1, 3}
    assert len(captured["person_gt_records"]) == 2
    assert result.per_class[0].n_gt == 3


def test_persist_false_no_escribe_eval_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_dir = tmp_path / "run_r3"
    run_dir.mkdir()
    _write_detections(run_dir)
    bench_coco, person_gt = _write_benchmark(tmp_path)
    monkeypatch.setattr(runner, "_load_evaluate_bench", _synthetic_evaluator)

    result = run_evaluation(run_dir, bench_coco=bench_coco, person_gt=person_gt, persist=False)

    assert result.type == "perception"
    assert not (run_dir / "eval_perception.json").exists()
```

- [x] **Step 2: Correr los tests y verificar que fallan**

Run: `cd /home/simonll4/projects/e-ovrt_media-plane && .venv/bin/python -m pytest tests/test_evaluate.py -q`
Expected: FAIL con `TypeError: run_evaluation() got an unexpected keyword argument 'restrict_gt_to_detections'` (y `'persist'`).

- [x] **Step 3: Implementar en `runner.py`**

Reemplazar la firma y el cuerpo de `run_evaluation` (líneas 86–139) por:

```python
def run_evaluation(
    run_dir: Path,
    bench_coco: Path | None = None,
    person_gt: Path | None = None,
    iou_threshold: float = 0.5,
    restrict_gt_to_detections: bool = False,
    persist: bool = True,
) -> EvalPerceptionResults:
    run_dir = Path(run_dir)
    detections_path = run_dir / "detections.jsonl"
    if not detections_path.is_file():
        raise FileNotFoundError(f"Detections file not found: {detections_path}")

    bench_coco_path, person_gt_path = _resolve_bench_paths(bench_coco, person_gt)
    evaluate_bench = _load_evaluate_bench()
    detections_by_img = evaluate_bench.load_detections([detections_path])
    images_by_filename, gt_by_image_id, cat_by_id = evaluate_bench.load_bench_coco(
        bench_coco_path
    )
    person_gt_records = evaluate_bench.load_person_gt(person_gt_path)

    if restrict_gt_to_detections:
        # El GT del BENCH es un único COCO (val+test): evaluar un run de un solo
        # split contra el GT completo deflacta AP/recall. Se restringe el GT a
        # las imágenes que el run realmente procesó (keys de detections.jsonl,
        # presentes aun con 0 detecciones).
        detected = set(detections_by_img)
        images_by_filename = {
            name: img for name, img in images_by_filename.items() if name in detected
        }
        kept_image_ids = {img["id"] for img in images_by_filename.values()}
        gt_by_image_id = {
            image_id: anns
            for image_id, anns in gt_by_image_id.items()
            if image_id in kept_image_ids
        }
        person_gt_records = [
            rec for rec in person_gt_records if Path(rec["file_name"]).name in detected
        ]

    per_class = []
    for class_name in cat_by_id.values():
        raw = evaluate_bench.evaluate_class(
            class_name,
            detections_by_img,
            images_by_filename,
            gt_by_image_id,
            cat_by_id,
            iou_threshold,
        )
        per_class.append(
            ClassResult(
                class_name=raw["class"],
                AP50=raw.get("AP50"),
                n_gt=raw.get("n_gt", 0),
                n_det=raw.get("n_det", 0),
            )
        )

    cr01_raw = evaluate_bench.evaluate_cr01(
        person_gt_records,
        detections_by_img,
        images_by_filename,
        iou_threshold,
    )
    result = EvalPerceptionResults(
        run_id=run_dir.name,
        benchmark=bench_coco_path.stem,
        iou_threshold=iou_threshold,
        per_class=per_class,
        cr01_detection_recall=cr01_raw.get("cr01_recall"),
        evaluated_at=datetime.now(timezone.utc).isoformat(),
    )
    if persist:
        (run_dir / "eval_perception.json").write_text(result.model_dump_json(indent=2))
    return result
```

- [x] **Step 4: Correr los tests y verificar que pasan (todo el archivo, sin regresiones)**

Run: `.venv/bin/python -m pytest tests/test_evaluate.py -q`
Expected: PASS (todos, incluidos los preexistentes).

---

### Task 2: `bench_split` / `evaluated` en `RunManager.get()` y `list_runs()`

**Files:**
- Modify: `e-ovrt_media-plane/src/eovrt_media/service/run_manager.py` (helper nuevo + `get` líneas 120-145 + `list_runs` líneas 147-178)
- Create: `e-ovrt_media-plane/tests/test_bench_info.py`

**Interfaces:**
- Produces: `bench_metadata(run_dir: Path) -> dict[str, Any]` con keys `bench_split: str | None` y `evaluated: bool`; constante `BENCH_SPLITS = frozenset({"bench_v2_test", "bench_v2_val"})`. Todo dict devuelto por `get()` y toda fila de `list_runs()` incluye ambas keys. Task 3 usa `info.get("bench_split")` para el gate 422; el BFF (Task 6) las pasa al frontend.
- Nota: `run_provenance.json` lo escribe `RunArtifactWriter` con shape `{"run_id", "dataset_id", "view", "split", "vocabulary", "source_fingerprint"}`; `split` es p.ej. `"bench_v2_test"` o `"demo_v2"`.

- [x] **Step 1: Escribir los tests que fallan**

Crear `tests/test_bench_info.py`:

```python
import json

import pytest
from fastapi.testclient import TestClient

from eovrt_media.service.app import create_app
from eovrt_media.service.settings import ServiceSettings


@pytest.fixture()
def client(tmp_path):
    settings = ServiceSettings.from_env(
        {"EOVRT_MODEL_REF": "mock", "EOVRT_RUNS_DIR": str(tmp_path / "runs")}
    )
    with TestClient(create_app(settings)) as c:
        yield c


def _finished_run(tmp_path, run_id="run_b1", split="bench_v2_test", provenance=True):
    run_dir = tmp_path / "runs" / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "summary.json").write_text(
        json.dumps({"run_id": run_id, "status": "succeeded", "model_name": "mock"})
    )
    if provenance:
        (run_dir / "run_provenance.json").write_text(
            json.dumps(
                {
                    "run_id": run_id,
                    "dataset_id": "construction_site_safety",
                    "view": "canonical_v2",
                    "split": split,
                }
            )
        )
    return run_dir


def test_get_run_bench_expone_split_y_no_evaluado(client, tmp_path):
    _finished_run(tmp_path)
    body = client.get("/api/runs/run_b1").json()
    assert body["bench_split"] == "bench_v2_test"
    assert body["evaluated"] is False


def test_get_run_evaluado_true_si_existe_eval_json(client, tmp_path):
    run_dir = _finished_run(tmp_path)
    (run_dir / "eval_perception.json").write_text("{}")
    body = client.get("/api/runs/run_b1").json()
    assert body["evaluated"] is True


def test_get_run_split_no_bench_es_null(client, tmp_path):
    _finished_run(tmp_path, run_id="run_demo", split="demo_v2")
    body = client.get("/api/runs/run_demo").json()
    assert body["bench_split"] is None


def test_get_run_sin_provenance_es_null(client, tmp_path):
    _finished_run(tmp_path, run_id="run_sin_prov", provenance=False)
    body = client.get("/api/runs/run_sin_prov").json()
    assert body["bench_split"] is None
    assert body["evaluated"] is False


def test_get_run_provenance_corrupta_no_rompe(client, tmp_path):
    run_dir = _finished_run(tmp_path, run_id="run_corrupto", provenance=False)
    (run_dir / "run_provenance.json").write_text('{"split": "bench_v2')
    r = client.get("/api/runs/run_corrupto")
    assert r.status_code == 200
    assert r.json()["bench_split"] is None


def test_list_runs_incluye_flags(client, tmp_path):
    _finished_run(tmp_path)
    _finished_run(tmp_path, run_id="run_demo", split="demo_v2")
    rows = {row["run_id"]: row for row in client.get("/api/runs").json()}
    assert rows["run_b1"]["bench_split"] == "bench_v2_test"
    assert rows["run_b1"]["evaluated"] is False
    assert rows["run_demo"]["bench_split"] is None
```

- [x] **Step 2: Correr y verificar que fallan**

Run: `.venv/bin/python -m pytest tests/test_bench_info.py -q`
Expected: FAIL con `KeyError: 'bench_split'` en las aserciones.

- [x] **Step 3: Implementar en `run_manager.py`**

Después de `UnknownRunError` (línea ~36), agregar:

```python
# Splits del BENCH con GT disponible: un único COCO
# (construction_site_safety_bench.json) cubre val y test.
BENCH_SPLITS = frozenset({"bench_v2_test", "bench_v2_val"})


def bench_metadata(run_dir: Path) -> dict[str, Any]:
    """`bench_split`/`evaluated` derivados de los artefactos del run.

    Barato (2 stats por run); la provenance ilegible/ausente degrada a
    bench_split=None en vez de romper get/list.
    """
    bench_split = None
    provenance_path = run_dir / "run_provenance.json"
    if provenance_path.exists():
        try:
            provenance = json.loads(provenance_path.read_text())
        except (json.JSONDecodeError, OSError):
            provenance = {}
        split = provenance.get("split")
        if split in BENCH_SPLITS:
            bench_split = split
    return {
        "bench_split": bench_split,
        "evaluated": (run_dir / "eval_perception.json").exists(),
    }
```

Agregar el import `from pathlib import Path` al bloque de imports (no está hoy).

En `get()` (línea ~120), enriquecer ambos returns:

```python
    def get(self, run_id: str) -> dict[str, Any]:
        with self._lock:
            active = self._active
        if active is not None and active.run_id == run_id:
            return {
                "run_id": run_id,
                "status": active.status,
                "started_at": active.started_at.isoformat(),
                "model": self._model_section.ref,
                **bench_metadata(self._settings.runs_dir / run_id),
            }
        summary_path = self._settings.runs_dir / run_id / "summary.json"
        if not summary_path.exists():
            raise UnknownRunError(run_id)
        try:
            summary = json.loads(summary_path.read_text())
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("summary ilegible para run_id=%s: %s", run_id, exc)
            raise UnknownRunError(run_id) from exc
        return {
            "run_id": run_id,
            "status": summary.get("status", "unknown"),
            "summary": summary,
            **bench_metadata(self._settings.runs_dir / run_id),
        }
```

En `list_runs()`, enriquecer la fila del activo y las de disco:

```python
        if active is not None:
            runs.append(
                {
                    "run_id": active.run_id,
                    "status": active.status,
                    **bench_metadata(self._settings.runs_dir / active.run_id),
                }
            )
```

y dentro del loop de `dirs`:

```python
                    runs.append(
                        {
                            "run_id": d.name,
                            "status": summary.get("status", "unknown"),
                            **bench_metadata(d),
                        }
                    )
```

- [x] **Step 4: Correr y verificar que pasan + sin regresiones del área**

Run: `.venv/bin/python -m pytest tests/test_bench_info.py tests/test_runs_api.py tests/test_run_manager.py -q`
Expected: PASS.

---

### Task 3: `POST /api/runs/{run_id}/evaluate` en el servicio (+ `eval_iou_threshold` + `mAP50`)

**Files:**
- Modify: `e-ovrt_media-plane/src/eovrt_media/service/settings.py` (campo nuevo)
- Modify: `e-ovrt_media-plane/src/eovrt_media/service/routers/runs.py` (imports + helper + endpoint)
- Create: `e-ovrt_media-plane/tests/test_eval_api.py`

**Interfaces:**
- Consumes: `run_evaluation(..., restrict_gt_to_detections=True, persist=False)` (Task 1); `info["bench_split"]` de `manager.get()` (Task 2); `atomic_write_json` de `eovrt_media.sinks.jsonl_sink`; `require_valid_run_id`.
- Produces: `POST /api/runs/{run_id}/evaluate` → `200` con el JSON de §3.3 del spec (`EvalPerceptionResults` + `mAP50: float | None` + `model: str | None` + `bench_split: str`), persistido atómico en `runs/<run_id>/eval_perception.json`. Errores: `404` (desconocido/inválido), `409` (run en curso, chequeado ANTES que el 422), `422` (no-BENCH o GT ausente, con mensaje accionable), `503` (no ready). Helper `_mean_ap50(per_class: list[ClassResult]) -> float | None`. `ServiceSettings.eval_iou_threshold: float` (env `EOVRT_EVAL_IOU_THRESHOLD`, default `0.5`).

- [x] **Step 1: Escribir los tests que fallan**

Crear `tests/test_eval_api.py`:

```python
import json
import time
from types import SimpleNamespace

import pytest
from PIL import Image
from fastapi.testclient import TestClient

from eovrt_media.evaluation import runner
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


def _bench_run(tmp_path, run_id="run_b1", split="bench_v2_test"):
    run_dir = tmp_path / "runs" / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "summary.json").write_text(
        json.dumps({"run_id": run_id, "status": "succeeded", "model_name": "mock"})
    )
    (run_dir / "run_provenance.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "dataset_id": "construction_site_safety",
                "view": "canonical_v2",
                "split": split,
            }
        )
    )
    event = {
        "source": {"source_id": "img001.jpg"},
        "detections": [{"prompt_id": "person", "bbox_xyxy": [0, 0, 10, 10], "confidence": 0.9}],
    }
    (run_dir / "detections.jsonl").write_text(json.dumps(event) + "\n")
    return run_dir


def _patch_evaluator(tmp_path, monkeypatch):
    """El endpoint no pasa GT explícito: se apuntan los defaults del runner a
    fixtures y se reemplaza el evaluador por uno sintético."""
    script = tmp_path / "evaluate_bench.py"
    script.write_text("VALUE = 1\n")
    bench_coco = tmp_path / "bench.json"
    bench_coco.write_text("{}")
    person_gt = tmp_path / "person_gt.json"
    person_gt.write_text("{}")
    monkeypatch.setattr(runner, "EVALUATE_BENCH_SCRIPT", script)
    monkeypatch.setattr(runner, "DEFAULT_BENCH_COCO", bench_coco)
    monkeypatch.setattr(runner, "DEFAULT_PERSON_GT", person_gt)
    synthetic = SimpleNamespace(
        load_detections=lambda _p: {"img001.jpg": []},
        load_bench_coco=lambda _p: (
            {"img001.jpg": {"id": 1}},
            {1: [{"category_id": 1}]},
            {1: "person"},
        ),
        load_person_gt=lambda _p: [],
        evaluate_class=lambda cls, *_a: {"class": cls, "AP50": 0.8, "n_gt": 1, "n_det": 1},
        evaluate_cr01=lambda *_a: {"cr01_recall": 0.5},
    )
    monkeypatch.setattr(runner, "_load_evaluate_bench", lambda: synthetic)


def test_post_evaluate_ok_enriquecido_y_atomico(client, tmp_path, monkeypatch):
    run_dir = _bench_run(tmp_path)
    _patch_evaluator(tmp_path, monkeypatch)

    r = client.post("/api/runs/run_b1/evaluate")

    assert r.status_code == 200
    body = r.json()
    assert body["type"] == "perception"
    assert body["mAP50"] == 0.8
    assert body["model"] == "mock"
    assert body["bench_split"] == "bench_v2_test"
    assert body["cr01_detection_recall"] == 0.5
    # persistencia atómica y enriquecida
    assert list(run_dir.glob("*.tmp")) == []
    on_disk = json.loads((run_dir / "eval_perception.json").read_text())
    assert on_disk["mAP50"] == 0.8
    # el flag del run refleja la evaluación
    assert client.get("/api/runs/run_b1").json()["evaluated"] is True


def test_post_evaluate_no_bench_422(client, tmp_path):
    _bench_run(tmp_path, run_id="run_demo", split="demo_v2")
    r = client.post("/api/runs/run_demo/evaluate")
    assert r.status_code == 422
    assert "BENCH" in r.json()["detail"]


def test_post_evaluate_run_en_curso_409(client, tmp_path):
    folder = tmp_path / "imgs"
    folder.mkdir()
    for i in range(400):
        Image.new("RGB", (64, 48), (1, 2, 3)).save(folder / f"i{i:03d}.png")
    body = {
        "ingest": {"plugin": "image_folder", "config": {"path": str(folder)}},
        "prompts": {"set_inline": SET_INLINE},
        "run": {},
    }
    run_id = client.post("/api/runs", json=body).json()["run_id"]
    r = client.post(f"/api/runs/{run_id}/evaluate")
    assert r.status_code == 409
    client.post(f"/api/runs/{run_id}/stop")
    deadline = time.monotonic() + 15.0
    while time.monotonic() < deadline:
        if client.get(f"/api/runs/{run_id}").json()["status"] != "running":
            break
        time.sleep(0.05)


def test_post_evaluate_404_desconocido_e_invalido(client):
    assert client.post("/api/runs/nope/evaluate").status_code == 404
    assert client.post("/api/runs/%2e%2e/evaluate").status_code == 404


def test_post_evaluate_gt_ausente_422_accionable(client, tmp_path, monkeypatch):
    _bench_run(tmp_path)
    monkeypatch.setattr(runner, "EVALUATE_BENCH_SCRIPT", tmp_path / "no_existe.py")
    r = client.post("/api/runs/run_b1/evaluate")
    assert r.status_code == 422
    assert "e-ovrt_datasets" in r.json()["detail"]


def test_mean_ap50():
    from eovrt_media.evaluation.schemas import ClassResult
    from eovrt_media.service.routers.runs import _mean_ap50

    rows = [
        ClassResult(class_name="person", AP50=0.8, n_gt=2, n_det=2),
        ClassResult(class_name="helmet", AP50=None, n_gt=0, n_det=1),
        ClassResult(class_name="bare_head", AP50=0.0, n_gt=1, n_det=0),
    ]
    assert _mean_ap50(rows) == 0.4
    assert _mean_ap50([ClassResult(class_name="x", AP50=None, n_gt=0, n_det=0)]) is None


def test_settings_eval_iou_threshold():
    base = {"EOVRT_MODEL_REF": "mock"}
    assert ServiceSettings.from_env(base).eval_iou_threshold == 0.5
    assert (
        ServiceSettings.from_env({**base, "EOVRT_EVAL_IOU_THRESHOLD": "0.4"}).eval_iou_threshold
        == 0.4
    )
```

- [x] **Step 2: Correr y verificar que fallan**

Run: `.venv/bin/python -m pytest tests/test_eval_api.py -q`
Expected: FAIL — `405`/`404` en los POST (endpoint inexistente), `ImportError: _mean_ap50`, `AttributeError: eval_iou_threshold`.

- [x] **Step 3: Implementar settings**

En `service/settings.py`, agregar el campo al dataclass (después de `shutdown_grace_seconds`):

```python
    eval_iou_threshold: float = 0.5
```

y en `from_env`, dentro del `return cls(...)`:

```python
            eval_iou_threshold=float(env.get("EOVRT_EVAL_IOU_THRESHOLD", "0.5")),
```

- [x] **Step 4: Implementar el endpoint en `service/routers/runs.py`**

Agregar imports arriba:

```python
from eovrt_media.evaluation.runner import run_evaluation
from eovrt_media.evaluation.schemas import ClassResult
from eovrt_media.sinks.jsonl_sink import atomic_write_json
```

Agregar al final del archivo:

```python
def _mean_ap50(per_class: list[ClassResult]) -> float | None:
    """mAP@0.5 = media de los AP50 no-nulos (incluye 0.0 de clases con GT y
    0 matches; excluye clases sin GT). None si ninguna clase tiene GT."""
    values = [item.AP50 for item in per_class if item.AP50 is not None]
    return round(sum(values) / len(values), 4) if values else None


@router.post("/runs/{run_id}/evaluate")
def evaluate_run(run_id: str, request: Request):
    manager = _manager(request)
    _require_valid_run_id(run_id)
    try:
        info = manager.get(run_id)
    except UnknownRunError as exc:
        raise HTTPException(status_code=404, detail=f"Run desconocido: {run_id}") from exc
    if info["status"] == "running":
        raise HTTPException(status_code=409, detail="No se evalúa un run en curso")
    if info.get("bench_split") is None:
        raise HTTPException(
            status_code=422, detail="El run no fue sobre un split del BENCH (no evaluable)"
        )
    run_dir = request.app.state.settings.runs_dir / run_id
    try:
        result = run_evaluation(
            run_dir,
            iou_threshold=request.app.state.settings.eval_iou_threshold,
            restrict_gt_to_detections=True,
            persist=False,
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=422,
            detail=(
                "No se pudo evaluar: falta el GT del BENCH o detections.jsonl. "
                "Verificá que ../e-ovrt_datasets exista como hermano del media-plane "
                "(y corré build_person_gt.py si falta person_gt.json). "
                f"Causa: {exc}"
            ),
        ) from exc
    payload = result.model_dump(mode="json")
    payload["mAP50"] = _mean_ap50(result.per_class)
    payload["model"] = (info.get("summary") or {}).get("model_name")
    payload["bench_split"] = info["bench_split"]
    # El endpoint es dueño de la persistencia enriquecida y atómica (una sola
    # escritura; run_evaluation se llamó con persist=False).
    atomic_write_json(run_dir / "eval_perception.json", payload)
    return payload
```

- [x] **Step 5: Correr y verificar que pasan**

Run: `.venv/bin/python -m pytest tests/test_eval_api.py tests/test_runs_api.py tests/test_service_settings.py -q`
Expected: PASS.

---

### Task 4: `GET /api/runs/{run_id}/evaluate` en el servicio

**Files:**
- Modify: `e-ovrt_media-plane/src/eovrt_media/service/routers/runs.py`
- Test: `e-ovrt_media-plane/tests/test_eval_api.py` (extender)

**Interfaces:**
- Produces: `GET /api/runs/{run_id}/evaluate` → `200` con el `eval_perception.json` persistido (ya trae `mAP50`/`model`/`bench_split`) o `404` si no fue evaluado / archivo ilegible. No corre nada. El BFF (Task 5) lo consume vía `_get_json`.

- [x] **Step 1: Escribir los tests que fallan** (agregar a `tests/test_eval_api.py`)

```python
def test_get_evaluate_404_si_no_evaluado(client, tmp_path):
    _bench_run(tmp_path)
    assert client.get("/api/runs/run_b1/evaluate").status_code == 404


def test_get_evaluate_devuelve_lo_persistido(client, tmp_path, monkeypatch):
    _bench_run(tmp_path)
    _patch_evaluator(tmp_path, monkeypatch)
    posted = client.post("/api/runs/run_b1/evaluate").json()

    got = client.get("/api/runs/run_b1/evaluate")

    assert got.status_code == 200
    assert got.json() == posted


def test_get_evaluate_corrupto_es_404(client, tmp_path):
    run_dir = _bench_run(tmp_path)
    (run_dir / "eval_perception.json").write_text('{"mAP50": 0.4')
    assert client.get("/api/runs/run_b1/evaluate").status_code == 404


def test_get_evaluate_run_id_invalido_404(client):
    assert client.get("/api/runs/%2e%2e/evaluate").status_code == 404
```

- [x] **Step 2: Correr y verificar que fallan**

Run: `.venv/bin/python -m pytest tests/test_eval_api.py -q`
Expected: FAIL — `404` esperado pero `405`/otro en el caso 200 (`test_get_evaluate_devuelve_lo_persistido`).

- [x] **Step 3: Implementar** (agregar a `service/routers/runs.py`, después de `evaluate_run`)

```python
@router.get("/runs/{run_id}/evaluate")
def get_evaluation(run_id: str, request: Request):
    _manager(request)  # 503 si no ready
    _require_valid_run_id(run_id)
    path = request.app.state.settings.runs_dir / run_id / "eval_perception.json"
    try:
        return _json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        # No evaluado, borrado concurrente o JSON ilegible: mismo trato (404).
        raise HTTPException(status_code=404, detail=f"Run no evaluado: {run_id}") from exc
```

- [x] **Step 4: Correr y verificar que pasan + suite completa del repo**

Run: `.venv/bin/python -m pytest tests/test_eval_api.py -q && make test`
Expected: PASS (suite completa, sin regresiones). `make lint` también limpio.

---

### Task 5: BFF — `RunBackend.evaluate`/`get_evaluation` + `RunNotFinished` + fake service

**Files:**
- Modify: `webconsole/backend/src/eovrt_webconsole/run_backend.py`
- Modify: `webconsole/backend/tests/fake_service.py`
- Test: `webconsole/backend/tests/test_run_backend.py` (extender)

**Interfaces:**
- Produces: excepción `RunNotFinished(detail: str)` (409 del evaluate — SIN `active_run_id`; no confundir con `RunBusy`); `RunBackend.evaluate(run_id) -> dict` (POST; mapea 404→`UnknownRun`, 409→`RunNotFinished`, 422→`ServiceRejected`, 5xx/503/red→`ServiceUnavailable`); `RunBackend.get_evaluation(run_id) -> dict` (GET vía `_get_json`: 404→`UnknownRun`, 5xx→`ServiceUnavailable`). Fake service: constante `EVAL_RESULT`, `FakeState.eval_results: dict[str, dict]` (pre-sembrable) y knob `evaluate_not_bench: bool`; el fake `get_run`/`list_runs` exponen `bench_split`/`evaluated` para `run_done_1`. Tasks 6–7 usan todo esto.

- [x] **Step 1: Extender el fake service** (`tests/fake_service.py`)

Después de `SUMMARY_FINISHED`, agregar:

```python
EVAL_RESULT = {
    "type": "perception",
    "run_id": "run_done_1",
    "benchmark": "construction_site_safety_bench",
    "iou_threshold": 0.5,
    "evaluated_at": "2026-07-04T10:00:00+00:00",
    "per_class": [
        {"class_name": "person", "AP50": 0.72, "n_gt": 82, "n_det": 90},
        {"class_name": "helmet", "AP50": 0.61, "n_gt": 60, "n_det": 70},
        {"class_name": "vest", "AP50": 0.55, "n_gt": 48, "n_det": 44},
        {"class_name": "bare_head", "AP50": 0.0, "n_gt": 12, "n_det": 20},
    ],
    "cr01_detection_recall": 0.64,
    "mAP50": 0.47,
    "model": "mock",
    "bench_split": "bench_v2_test",
}
```

En `FakeState.__init__`, agregar:

```python
        self.eval_results: dict[str, dict] = {}
        self.evaluate_not_bench: bool = False
```

En `list_runs()` del fake, reemplazar la fila de `run_done_1` por:

```python
        runs.append(
            {
                "run_id": "run_done_1",
                "status": "succeeded",
                "bench_split": "bench_v2_test",
                "evaluated": "run_done_1" in state.eval_results,
            }
        )
```

En `get_run()` del fake, reemplazar el return de `run_done_1` por:

```python
        if run_id == "run_done_1":
            return {
                "run_id": run_id,
                "status": "succeeded",
                "summary": SUMMARY_FINISHED,
                "bench_split": "bench_v2_test",
                "evaluated": run_id in state.eval_results,
            }
```

Después de `stop_run`, agregar los endpoints (mismos semánticos que el servicio real):

```python
    @app.post("/api/runs/{run_id}/evaluate")
    def evaluate_run(run_id: str):
        if not state.ready:
            return JSONResponse(status_code=503, content={"detail": "Servicio no listo (modelo no cargado)"})
        if run_id == state.active_run_id:
            return JSONResponse(status_code=409, content={"detail": "No se evalúa un run en curso"})
        if run_id != "run_done_1":
            return JSONResponse(status_code=404, content={"detail": f"Run desconocido: {run_id}"})
        if state.evaluate_not_bench:
            return JSONResponse(
                status_code=422,
                content={"detail": "El run no fue sobre un split del BENCH (no evaluable)"},
            )
        result = {**EVAL_RESULT, "run_id": run_id}
        state.eval_results[run_id] = result
        return result

    @app.get("/api/runs/{run_id}/evaluate")
    def get_evaluation(run_id: str):
        if not state.ready:
            return JSONResponse(status_code=503, content={"detail": "Servicio no listo (modelo no cargado)"})
        result = state.eval_results.get(run_id)
        if result is None:
            return JSONResponse(status_code=404, content={"detail": f"Run no evaluado: {run_id}"})
        return result
```

- [x] **Step 2: Escribir los tests que fallan** (agregar a `tests/test_run_backend.py`; sumar `RunNotFinished` al import de `eovrt_webconsole.run_backend`)

```python
async def test_evaluate_ok(backend, state):
    result = await backend.evaluate("run_done_1")
    assert result["mAP50"] == 0.47
    assert result["bench_split"] == "bench_v2_test"
    assert "run_done_1" in state.eval_results


async def test_evaluate_run_en_curso_es_run_not_finished(backend, state):
    state.active_run_id = "run_x"
    with pytest.raises(RunNotFinished):
        await backend.evaluate("run_x")


async def test_evaluate_no_bench_es_service_rejected(backend, state):
    state.evaluate_not_bench = True
    with pytest.raises(ServiceRejected):
        await backend.evaluate("run_done_1")


async def test_evaluate_desconocido_es_unknown_run(backend):
    with pytest.raises(UnknownRun):
        await backend.evaluate("nope")


async def test_evaluate_servicio_no_listo_503(backend, state):
    state.ready = False
    with pytest.raises(ServiceUnavailable):
        await backend.evaluate("run_done_1")


async def test_get_evaluation_404_y_ok(backend, state):
    with pytest.raises(UnknownRun):
        await backend.get_evaluation("run_done_1")
    await backend.evaluate("run_done_1")
    result = await backend.get_evaluation("run_done_1")
    assert result["cr01_detection_recall"] == 0.64
```

- [x] **Step 3: Correr y verificar que fallan**

Run: `cd /home/simonll4/projects/e-ovrt_experimental-setup/webconsole/backend && .venv/bin/python -m pytest tests/test_run_backend.py -q`
Expected: FAIL con `ImportError: cannot import name 'RunNotFinished'`.

- [x] **Step 4: Implementar en `run_backend.py`**

Después de `RunBusy`, agregar:

```python
class RunNotFinished(Exception):
    """409 al evaluar: el run sigue en curso (sin active_run_id, a diferencia
    de RunBusy que es el 409 de lanzamiento)."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail
```

En la clase `RunBackend`, después de `stop`, agregar:

```python
    async def evaluate(self, run_id: str) -> dict:
        try:
            response = await self._http.post(f"/api/runs/{run_id}/evaluate")
        except httpx.HTTPError as exc:
            raise ServiceUnavailable(str(exc)) from exc
        if response.status_code == 404:
            raise UnknownRun(run_id)
        if response.status_code == 409:
            raise RunNotFinished(response.json().get("detail", "run en curso"))
        if response.status_code == 422:
            raise ServiceRejected(response.json().get("detail"))
        if response.status_code >= 500 or response.status_code == 503:
            raise ServiceUnavailable(
                f"POST /api/runs/{run_id}/evaluate -> {response.status_code}"
            )
        response.raise_for_status()
        return response.json()

    async def get_evaluation(self, run_id: str) -> dict:
        return await self._get_json(f"/api/runs/{run_id}/evaluate")
```

- [x] **Step 5: Correr y verificar que pasan**

Run: `.venv/bin/python -m pytest tests/test_run_backend.py -q`
Expected: PASS.

---

### Task 6: BFF — endpoints proxy evaluate/get_evaluation + passthrough de flags

**Files:**
- Modify: `webconsole/backend/src/eovrt_webconsole/routers/runs.py`
- Test: `webconsole/backend/tests/test_runs_router.py` (extender)

**Interfaces:**
- Consumes: `RunBackend.evaluate/get_evaluation`, `RunNotFinished` (Task 5).
- Produces: `POST /api/runs/{id}/evaluate` (200 passthrough; `UnknownRun→404`, `RunNotFinished→409 {detail}`, `ServiceRejected→422 {errors:[{field:"_service"}]}`, `ServiceUnavailable→502`); `GET /api/runs/{id}/evaluate` (200 / 404 / 502). `_row` y los fallbacks de `list_runs` incluyen `bench_split`/`evaluated`. `GET /api/runs/{id}` ya es passthrough (los flags fluyen solos).

- [x] **Step 1: Escribir los tests que fallan** (agregar a `tests/test_runs_router.py`; sumar import `from eovrt_webconsole.run_backend import ServiceUnavailable`)

```python
def test_evaluate_ok(client):
    r = client.post("/api/runs/run_done_1/evaluate")
    assert r.status_code == 200
    body = r.json()
    assert body["mAP50"] == 0.47
    assert body["bench_split"] == "bench_v2_test"


def test_evaluate_409_run_en_curso(client, fake_state):
    fake_state.active_run_id = "run_active_1"
    r = client.post("/api/runs/run_active_1/evaluate")
    assert r.status_code == 409
    assert "detail" in r.json()


def test_evaluate_422_no_bench_va_como_service(client, fake_state):
    fake_state.evaluate_not_bench = True
    r = client.post("/api/runs/run_done_1/evaluate")
    assert r.status_code == 422
    assert any(e["field"] == "_service" for e in r.json()["errors"])


def test_evaluate_404_desconocido(client):
    assert client.post("/api/runs/nope/evaluate").status_code == 404


def test_evaluate_502_servicio_caido(client, monkeypatch):
    async def down(_run_id):
        raise ServiceUnavailable("down")

    monkeypatch.setattr(client.app.state.backend, "evaluate", down)
    assert client.post("/api/runs/run_done_1/evaluate").status_code == 502


def test_get_evaluation_404_y_luego_200(client):
    assert client.get("/api/runs/run_done_1/evaluate").status_code == 404
    client.post("/api/runs/run_done_1/evaluate")
    r = client.get("/api/runs/run_done_1/evaluate")
    assert r.status_code == 200
    assert r.json()["mAP50"] == 0.47


def test_listado_trae_flags_de_evaluacion(client):
    rows = {r["run_id"]: r for r in client.get("/api/runs").json()}
    assert rows["run_done_1"]["bench_split"] == "bench_v2_test"
    assert rows["run_done_1"]["evaluated"] is False


def test_get_run_passthrough_trae_bench_split(client):
    body = client.get("/api/runs/run_done_1").json()
    assert body["bench_split"] == "bench_v2_test"
    assert body["evaluated"] is False
```

- [x] **Step 2: Correr y verificar que fallan**

Run: `.venv/bin/python -m pytest tests/test_runs_router.py -q`
Expected: FAIL — 405/404 en evaluate; `KeyError: 'bench_split'` en el listado.

- [x] **Step 3: Implementar en `routers/runs.py`**

Sumar `RunNotFinished` al import de `eovrt_webconsole.run_backend`.

En `_row`, agregar dos entradas al dict:

```python
        "bench_split": info.get("bench_split"),
        "evaluated": info.get("evaluated"),
```

En `list_runs`, reemplazar los dos fallbacks no-hidratados para que arrastren los flags que el servicio ya manda en el listado:

```python
        except (UnknownRun, ServiceUnavailable):
            rows.append(
                {
                    "run_id": item["run_id"],
                    "status": item["status"],
                    "bench_split": item.get("bench_split"),
                    "evaluated": item.get("evaluated"),
                }
            )
    rows.extend(
        {
            "run_id": item["run_id"],
            "status": item["status"],
            "bench_split": item.get("bench_split"),
            "evaluated": item.get("evaluated"),
        }
        for item in base[settings.hydration_limit :]
    )
```

Después de `stop_run`, agregar (antes de `detections` para mantener el archivo ordenado por recurso; el orden no afecta el ruteo):

```python
@router.post("/{run_id}/evaluate")
async def evaluate_run(run_id: str, request: Request):
    try:
        return await request.app.state.backend.evaluate(run_id)
    except UnknownRun as exc:
        raise HTTPException(status_code=404, detail=f"Run desconocido: {run_id}") from exc
    except RunNotFinished as exc:
        return JSONResponse(status_code=409, content={"detail": exc.detail})
    except ServiceRejected as exc:
        return JSONResponse(
            status_code=422,
            content={"errors": [{"field": "_service", "message": str(exc.detail)}]},
        )
    except ServiceUnavailable as exc:
        logger.warning("evaluate(%s): servicio inaccesible: %s", run_id, exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/{run_id}/evaluate")
async def get_evaluation(run_id: str, request: Request):
    try:
        return await request.app.state.backend.get_evaluation(run_id)
    except UnknownRun as exc:
        raise HTTPException(status_code=404, detail=f"Run no evaluado: {run_id}") from exc
    except ServiceUnavailable as exc:
        logger.warning("get_evaluation(%s): servicio inaccesible: %s", run_id, exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
```

- [x] **Step 4: Correr y verificar que pasan**

Run: `.venv/bin/python -m pytest tests/test_runs_router.py tests/test_run_backend.py -q`
Expected: PASS.

---

### Task 7: BFF — `GET /api/compare`

**Files:**
- Create: `webconsole/backend/src/eovrt_webconsole/routers/compare.py`
- Modify: `webconsole/backend/src/eovrt_webconsole/app.py` (registrar router)
- Create: `webconsole/backend/tests/test_compare_api.py`

**Interfaces:**
- Consumes: `RunBackend.get_evaluation` (Task 5). Solo N GETs de evals — `model`/`bench_split` vienen embebidos, no hace falta info extra por run.
- Produces: `GET /api/compare?runs=id1,id2,...` (coma-separado, dedupe preservando orden, tope 8) → `{"runs": [{run_id,label,model,bench_split,mAP50,cr01_detection_recall}], "classes": [...], "ap_by_class": {clase: [valores paralelos a runs]}, "skipped": [...]}`. `label` = `"{model} · {bench_split}"`. Runs sin eval (404) van a `skipped`. `422` con `detail` si vacío o >8; `502` si el servicio no responde.

- [x] **Step 1: Escribir los tests que fallan**

Crear `tests/test_compare_api.py`:

```python
from tests.fake_service import EVAL_RESULT


def _seed_second_eval(fake_state, run_id="run_other"):
    fake_state.eval_results[run_id] = {
        **EVAL_RESULT,
        "run_id": run_id,
        "model": "yoloe",
        "mAP50": 0.3,
        "cr01_detection_recall": 0.1,
        "per_class": [
            {"class_name": "person", "AP50": 0.68, "n_gt": 82, "n_det": 80},
            {"class_name": "helmet", "AP50": 0.55, "n_gt": 60, "n_det": 65},
            {"class_name": "vest", "AP50": None, "n_gt": 0, "n_det": 4},
            {"class_name": "bare_head", "AP50": 0.1, "n_gt": 12, "n_det": 9},
        ],
    }


def test_compare_agrega_y_alinea_por_clase(client, fake_state):
    client.post("/api/runs/run_done_1/evaluate")
    _seed_second_eval(fake_state)

    body = client.get("/api/compare?runs=run_done_1,run_other").json()

    assert [row["run_id"] for row in body["runs"]] == ["run_done_1", "run_other"]
    assert body["runs"][0]["label"] == "mock · bench_v2_test"
    assert body["runs"][1]["model"] == "yoloe"
    assert body["classes"] == ["person", "helmet", "vest", "bare_head"]
    assert body["ap_by_class"]["person"] == [0.72, 0.68]
    assert body["ap_by_class"]["vest"] == [0.55, None]
    assert body["skipped"] == []


def test_compare_omite_runs_sin_eval(client, fake_state):
    _seed_second_eval(fake_state, run_id="run_a")
    body = client.get("/api/compare?runs=run_a,run_sin_eval").json()
    assert [row["run_id"] for row in body["runs"]] == ["run_a"]
    assert body["skipped"] == ["run_sin_eval"]


def test_compare_dedupe_preserva_orden(client, fake_state):
    _seed_second_eval(fake_state, run_id="run_a")
    body = client.get("/api/compare?runs=run_a,run_a").json()
    assert len(body["runs"]) == 1


def test_compare_tope_8_es_422(client):
    ids = ",".join(f"r{i}" for i in range(9))
    assert client.get(f"/api/compare?runs={ids}").status_code == 422


def test_compare_vacio_es_422(client):
    assert client.get("/api/compare?runs=,").status_code == 422
```

- [x] **Step 2: Correr y verificar que fallan**

Run: `.venv/bin/python -m pytest tests/test_compare_api.py -q`
Expected: FAIL con `404` (ruta inexistente).

- [x] **Step 3: Implementar**

Crear `src/eovrt_webconsole/routers/compare.py`:

```python
"""Compare: agrega las evaluaciones BENCH de N runs para la vista comparativa."""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query, Request

from eovrt_webconsole.run_backend import ServiceUnavailable, UnknownRun

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

MAX_COMPARE_RUNS = 8


@router.get("/compare")
async def compare(request: Request, runs: str = Query(...)):
    # dedupe preservando orden; ids vacíos (",," o espacios) se descartan
    ids = [rid for rid in dict.fromkeys(part.strip() for part in runs.split(",")) if rid]
    if not ids:
        raise HTTPException(status_code=422, detail="Parámetro runs vacío")
    if len(ids) > MAX_COMPARE_RUNS:
        raise HTTPException(
            status_code=422, detail=f"Máximo {MAX_COMPARE_RUNS} runs a comparar"
        )
    backend = request.app.state.backend
    evals: list[tuple[str, dict]] = []
    skipped: list[str] = []
    for run_id in ids:
        try:
            evals.append((run_id, await backend.get_evaluation(run_id)))
        except UnknownRun:
            skipped.append(run_id)
        except ServiceUnavailable as exc:
            logger.warning("compare(%s): servicio inaccesible: %s", run_id, exc)
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    # El set/orden de clases es idéntico entre runs (mismo BENCH COCO): se toma
    # del primer eval resuelto.
    classes: list[str] = (
        [item.get("class_name") for item in evals[0][1].get("per_class") or []]
        if evals
        else []
    )
    rows: list[dict] = []
    ap_by_class: dict[str, list[float | None]] = {name: [] for name in classes}
    for run_id, ev in evals:
        model = ev.get("model")
        bench_split = ev.get("bench_split")
        rows.append(
            {
                "run_id": run_id,
                "label": f"{model or run_id} · {bench_split or '?'}",
                "model": model,
                "bench_split": bench_split,
                "mAP50": ev.get("mAP50"),
                "cr01_detection_recall": ev.get("cr01_detection_recall"),
            }
        )
        ap50_by_name = {
            item.get("class_name"): item.get("AP50") for item in ev.get("per_class") or []
        }
        for name in classes:
            ap_by_class[name].append(ap50_by_name.get(name))
    return {"runs": rows, "classes": classes, "ap_by_class": ap_by_class, "skipped": skipped}
```

En `app.py`: sumar `compare` al import de `eovrt_webconsole.routers` y registrar `app.include_router(compare.router)` junto a los demás.

- [x] **Step 4: Correr y verificar que pasan + suite BFF completa**

Run: `.venv/bin/python -m pytest tests/ -q`
Expected: PASS.

---

### Task 8: Frontend — tipos y cliente API

**Files:**
- Modify: `webconsole/frontend/src/types.ts`
- Modify: `webconsole/frontend/src/api.ts`
- Test: `webconsole/frontend/src/__tests__/api.test.ts` (extender)

**Interfaces:**
- Produces: tipos `EvalClassRow`, `EvalResult`, `CompareRunEntry`, `CompareResult`; `RunRow`/`RunDetail` ganan `bench_split?: string | null` y `evaluated?: boolean`. Funciones `evaluateRun(id): Promise<EvalResult>`, `getEvaluation(id): Promise<EvalResult>`, `getCompare(ids: string[]): Promise<CompareResult>`. Tasks 9–11 consumen estos nombres exactos.

- [x] **Step 1: Escribir los tests que fallan** (agregar a `__tests__/api.test.ts`; sumar `evaluateRun, getCompare` al import de `'../api'`)

```ts
  it('evaluateRun postea y parsea el eval', async () => {
    stubFetch(200, { run_id: 'r1', mAP50: 0.47, per_class: [] })
    const result = await evaluateRun('r1')
    expect(result.mAP50).toBe(0.47)
  })

  it('evaluateRun lanza ApiError en 422', async () => {
    stubFetch(422, { errors: [{ field: '_service', message: 'no evaluable' }] })
    const error = await evaluateRun('r1').catch((e) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect(error.status).toBe(422)
  })

  it('getCompare arma la URL con ids encodeados', async () => {
    const fetchMock = vi.fn(
      async () =>
        new Response(JSON.stringify({ runs: [], classes: [], ap_by_class: {}, skipped: [] }), {
          status: 200,
        }),
    )
    vi.stubGlobal('fetch', fetchMock)
    await getCompare(['run a', 'run_b'])
    expect(fetchMock.mock.calls[0][0]).toBe('/api/compare?runs=run%20a,run_b')
  })
```

- [x] **Step 2: Correr y verificar que fallan**

Run: `cd /home/simonll4/projects/e-ovrt_experimental-setup/webconsole/frontend && npm test`
Expected: FAIL (imports inexistentes).

- [x] **Step 3: Implementar tipos** (en `types.ts`)

A `RunRow` agregar:

```ts
  bench_split?: string | null
  evaluated?: boolean
```

A `RunDetail` agregar:

```ts
  bench_split?: string | null
  evaluated?: boolean
```

Al final del archivo agregar:

```ts
export interface EvalClassRow {
  class_name: string
  AP50: number | null
  n_gt: number
  n_det: number
}
export interface EvalResult {
  type: string
  run_id: string
  benchmark: string
  iou_threshold: number
  evaluated_at: string
  per_class: EvalClassRow[]
  cr01_detection_recall: number | null
  mAP50: number | null
  model: string | null
  bench_split: string | null
}
export interface CompareRunEntry {
  run_id: string
  label: string
  model: string | null
  bench_split: string | null
  mAP50: number | null
  cr01_detection_recall: number | null
}
export interface CompareResult {
  runs: CompareRunEntry[]
  classes: string[]
  ap_by_class: Record<string, Array<number | null>>
  skipped: string[]
}
```

- [x] **Step 4: Implementar API** (en `api.ts`: sumar `CompareResult, EvalResult` al import de tipos; agregar después de `stopRun`)

```ts
export const evaluateRun = (id: string) =>
  request<EvalResult>(`/api/runs/${encodeURIComponent(id)}/evaluate`, { method: 'POST' })
export const getEvaluation = (id: string) =>
  request<EvalResult>(`/api/runs/${encodeURIComponent(id)}/evaluate`)
export const getCompare = (ids: string[]) =>
  request<CompareResult>(`/api/compare?runs=${ids.map(encodeURIComponent).join(',')}`)
```

- [x] **Step 5: Correr y verificar que pasan (tests + build strict)**

Run: `npm test && npm run build`
Expected: PASS / build sin errores TS.

---

### Task 9: Frontend — componente `GroupedBars` (SVG propio)

**Files:**
- Create: `webconsole/frontend/src/components/GroupedBars.tsx`
- Create: `webconsole/frontend/src/__tests__/GroupedBars.test.tsx`

**Interfaces:**
- Produces: `groupedBarsLayout(groups: string[], series: Array<Array<number | null>>, width: number, plotHeight: number): BarRect[]` (función pura, exportada para test); `SERIES_COLORS: string[]` (paleta categórica fija de 8, validada CVD — coincide con el tope de 8 runs del compare); default export `GroupedBars({ groups, series, labels, width?, height? })`. `series[i]` es la fila del run `i`, paralela a `groups`; `null` = sin barra. Dominio de valores fijo [0,1] (AP@0.5). Task 11 lo consume con `groups=classes`, una serie por run y `labels` = labels del compare.
- Decisiones de diseño (dataviz): color por identidad de serie en orden fijo (nunca ciclado por aparición), gap de 2px entre barras adyacentes, leyenda siempre presente (≥2 series), tooltip nativo por barra (`<title>`), texto en tinta (no en color de serie); la tabla comparativa adyacente (Task 11) cubre el caso CVD/contraste.

- [x] **Step 1: Escribir los tests que fallan**

Crear `__tests__/GroupedBars.test.tsx`:

```tsx
import { describe, expect, it } from 'vitest'
import { groupedBarsLayout, SERIES_COLORS } from '../components/GroupedBars'

describe('groupedBarsLayout', () => {
  it('genera un rect por valor no-nulo, escalado al alto del plot', () => {
    const rects = groupedBarsLayout(['person', 'helmet'], [[1, 0.5], [null, 0.25]], 200, 100)
    // serie 0: person=1, helmet=0.5; serie 1: person=null (sin barra), helmet=0.25
    expect(rects).toHaveLength(3)
    expect(rects[0].height).toBe(100)
    expect(rects[0].y).toBe(0)
    expect(rects[1].height).toBe(50)
    expect(rects[1].y).toBe(50)
  })

  it('el color sigue el índice de serie, no el orden de aparición', () => {
    const rects = groupedBarsLayout(['a'], [[null], [0.5]], 100, 100)
    expect(rects).toHaveLength(1)
    expect(rects[0].color).toBe(SERIES_COLORS[1])
  })

  it('las barras quedan dentro del slot de su grupo', () => {
    const width = 200
    const rects = groupedBarsLayout(['a', 'b'], [[0.5, 0.5], [0.5, 0.5]], width, 100)
    const slot = width / 2
    for (const r of rects.filter((r) => r.group === 0)) {
      expect(r.x).toBeGreaterThanOrEqual(0)
      expect(r.x + r.width).toBeLessThanOrEqual(slot)
    }
    for (const r of rects.filter((r) => r.group === 1)) {
      expect(r.x).toBeGreaterThanOrEqual(slot)
      expect(r.x + r.width).toBeLessThanOrEqual(width)
    }
  })

  it('clampa valores fuera de [0,1]', () => {
    const rects = groupedBarsLayout(['a'], [[1.5]], 100, 100)
    expect(rects[0].height).toBe(100)
  })
})
```

- [x] **Step 2: Correr y verificar que fallan**

Run: `npm test`
Expected: FAIL (módulo inexistente).

- [x] **Step 3: Implementar**

Crear `components/GroupedBars.tsx`:

```tsx
// Paleta categórica fija (orden nunca ciclado): 8 slots validados para CVD
// (ΔE adyacente ≥ 24 en fondo claro). 8 = tope de runs del compare.
export const SERIES_COLORS = [
  '#2a78d6', '#1baf7a', '#eda100', '#008300', '#4a3aa7', '#e34948', '#e87ba4', '#eb6834',
]

export interface BarRect {
  x: number
  y: number
  width: number
  height: number
  color: string
  series: number
  group: number
  value: number
}

// Layout puro: dominio fijo [0,1] (AP@0.5). `series[i]` es paralela a `groups`.
export function groupedBarsLayout(
  groups: string[],
  series: Array<Array<number | null>>,
  width: number,
  plotHeight: number,
): BarRect[] {
  const rects: BarRect[] = []
  const nGroups = groups.length
  const nSeries = series.length
  if (!nGroups || !nSeries) return rects
  const slot = width / nGroups
  const inner = slot * 0.7
  const gap = 2
  const barWidth = Math.max(1, (inner - gap * (nSeries - 1)) / nSeries)
  groups.forEach((_group, gi) => {
    const start = gi * slot + (slot - inner) / 2
    series.forEach((values, si) => {
      const value = values[gi]
      if (value == null) return
      const clamped = Math.max(0, Math.min(1, value))
      rects.push({
        x: start + si * (barWidth + gap),
        y: plotHeight - clamped * plotHeight,
        width: barWidth,
        height: clamped * plotHeight,
        color: SERIES_COLORS[si % SERIES_COLORS.length],
        series: si,
        group: gi,
        value,
      })
    })
  })
  return rects
}

export default function GroupedBars({ groups, series, labels, width = 560, height = 220 }: {
  groups: string[]
  series: Array<Array<number | null>>
  labels: string[]
  width?: number
  height?: number
}) {
  const plotHeight = height - 40
  const rects = groupedBarsLayout(groups, series, width, plotHeight)
  return (
    <div>
      <svg width={width} height={height}>
        <line x1={0} y1={plotHeight} x2={width} y2={plotHeight} stroke="#ccc" />
        {rects.map((r) => (
          <rect
            key={`${r.series}-${r.group}`}
            x={r.x} y={r.y} width={r.width} height={r.height} fill={r.color} rx={2}
          >
            <title>{`${labels[r.series]} — ${groups[r.group]}: ${r.value.toFixed(3)}`}</title>
          </rect>
        ))}
        {groups.map((group, gi) => (
          <text
            key={group}
            x={(gi + 0.5) * (width / groups.length)}
            y={plotHeight + 16}
            textAnchor="middle"
            fontSize={12}
            fill="#444"
          >
            {group}
          </text>
        ))}
      </svg>
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', fontSize: 12 }}>
        {labels.map((label, i) => (
          <span key={label}>
            <span
              style={{
                background: SERIES_COLORS[i % SERIES_COLORS.length],
                display: 'inline-block', width: 10, height: 10, marginRight: 4,
              }}
            />
            {label}
          </span>
        ))}
      </div>
    </div>
  )
}
```

- [x] **Step 4: Correr y verificar que pasan**

Run: `npm test && npm run build`
Expected: PASS.

---

### Task 10: Frontend — `EvalSection` en el detalle del run

**Files:**
- Create: `webconsole/frontend/src/components/EvalSection.tsx`
- Modify: `webconsole/frontend/src/pages/RunDetailPage.tsx`
- Create: `webconsole/frontend/src/__tests__/EvalSection.test.tsx`

**Interfaces:**
- Consumes: `evaluateRun`, `getEvaluation`, `ApiError` (Task 8); `run.bench_split`/`run.evaluated` del `RunDetail` (fluyen del servicio vía passthrough del BFF).
- Produces: `EvalSection({ runId, benchSplit, evaluated })` — no renderiza nada si `benchSplit` es null/undefined; si `evaluated`, carga el eval con GET; si no, botón "Evaluar contra BENCH" (estado "Evaluando…") que dispara el POST. Muestra mAP@0.5 destacado + CR-01 recall + tabla AP@0.5 por clase con n_gt/n_det (`null`→"—"). Errores: 422 "no evaluable", 409 "esperá a que termine", 502 "servicio inaccesible".

- [x] **Step 1: Escribir los tests que fallan**

Crear `__tests__/EvalSection.test.tsx`:

```tsx
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import EvalSection from '../components/EvalSection'
import { ApiError, evaluateRun, getEvaluation } from '../api'
import type { EvalResult } from '../types'

vi.mock('../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api')>()),
  evaluateRun: vi.fn(),
  getEvaluation: vi.fn(),
}))

const EVAL: EvalResult = {
  type: 'perception',
  run_id: 'r1',
  benchmark: 'construction_site_safety_bench',
  iou_threshold: 0.5,
  evaluated_at: '2026-07-04T10:00:00+00:00',
  per_class: [
    { class_name: 'person', AP50: 0.72, n_gt: 82, n_det: 90 },
    { class_name: 'helmet', AP50: null, n_gt: 0, n_det: 3 },
  ],
  cr01_detection_recall: 0.64,
  mAP50: 0.47,
  model: 'mock',
  bench_split: 'bench_v2_test',
}

beforeEach(() => vi.clearAllMocks())

describe('EvalSection', () => {
  it('no renderiza nada si el run no es BENCH', () => {
    const { container } = render(<EvalSection runId="r1" benchSplit={null} evaluated={false} />)
    expect(container.innerHTML).toBe('')
  })

  it('evalúa al click y muestra la tabla con mAP', async () => {
    vi.mocked(evaluateRun).mockResolvedValue(EVAL)
    render(<EvalSection runId="r1" benchSplit="bench_v2_test" evaluated={false} />)
    fireEvent.click(screen.getByText('Evaluar contra BENCH'))
    await waitFor(() => expect(screen.getByText(/mAP@0\.5/)).toBeTruthy())
    expect(screen.getByText('person')).toBeTruthy()
    expect(screen.getAllByText('—').length).toBeGreaterThan(0) // AP50 null → —
    expect(evaluateRun).toHaveBeenCalledWith('r1')
  })

  it('si ya está evaluado carga el eval con GET (sin botón)', async () => {
    vi.mocked(getEvaluation).mockResolvedValue(EVAL)
    render(<EvalSection runId="r1" benchSplit="bench_v2_test" evaluated={true} />)
    await waitFor(() => expect(screen.getByText(/mAP@0\.5/)).toBeTruthy())
    expect(getEvaluation).toHaveBeenCalledWith('r1')
    expect(screen.queryByText('Evaluar contra BENCH')).toBeNull()
  })

  it('422 muestra "no evaluable"', async () => {
    vi.mocked(evaluateRun).mockRejectedValue(new ApiError(422, { errors: [] }))
    render(<EvalSection runId="r1" benchSplit="bench_v2_test" evaluated={false} />)
    fireEvent.click(screen.getByText('Evaluar contra BENCH'))
    await waitFor(() => expect(screen.getByText(/no es evaluable/)).toBeTruthy())
  })
})
```

- [x] **Step 2: Correr y verificar que fallan**

Run: `npm test`
Expected: FAIL (componente inexistente).

- [x] **Step 3: Implementar el componente**

Crear `components/EvalSection.tsx`:

```tsx
import { useEffect, useState } from 'react'
import { ApiError, evaluateRun, getEvaluation } from '../api'
import type { EvalResult } from '../types'

const CELL = { padding: '4px 10px', borderBottom: '1px solid #ddd' } as const

function errorMessage(e: unknown): string {
  if (e instanceof ApiError) {
    if (e.status === 422)
      return 'El run no es evaluable (no fue sobre un split del BENCH o falta el GT en disco).'
    if (e.status === 409) return 'El run sigue en curso: esperá a que termine.'
    if (e.status === 502) return 'Servicio media-plane inaccesible.'
  }
  return String(e)
}

const fmt = (v: number | null | undefined) => (v == null ? '—' : v)

export default function EvalSection({ runId, benchSplit, evaluated }: {
  runId: string
  benchSplit: string | null | undefined
  evaluated: boolean | undefined
}) {
  const [result, setResult] = useState<EvalResult | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (benchSplit && evaluated)
      getEvaluation(runId).then(setResult).catch((e) => setError(errorMessage(e)))
  }, [runId, benchSplit, evaluated])

  if (!benchSplit) return null

  const evaluate = () => {
    setBusy(true)
    setError(null)
    evaluateRun(runId)
      .then(setResult)
      .catch((e) => setError(errorMessage(e)))
      .finally(() => setBusy(false))
  }

  return (
    <section>
      <h3>Evaluación BENCH ({benchSplit})</h3>
      {!result && (
        <button onClick={evaluate} disabled={busy}>
          {busy ? 'Evaluando…' : 'Evaluar contra BENCH'}
        </button>
      )}
      {error && <p style={{ color: '#b00' }}>{error}</p>}
      {result && (
        <>
          <p>
            <b>mAP@0.5: {fmt(result.mAP50)}</b> · CR-01 recall: {fmt(result.cr01_detection_recall)}
            {' '}· IoU ≥ {result.iou_threshold}
          </p>
          <table style={{ borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                {['clase', 'AP@0.5', 'n_gt', 'n_det'].map((h) => (
                  <th key={h} style={{ ...CELL, textAlign: 'left', background: '#f5f5f5' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {result.per_class.map((c) => (
                <tr key={c.class_name}>
                  <td style={CELL}>{c.class_name}</td>
                  <td style={CELL}>{fmt(c.AP50)}</td>
                  <td style={CELL}>{c.n_gt}</td>
                  <td style={CELL}>{c.n_det}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </section>
  )
}
```

- [x] **Step 4: Integrar en `RunDetailPage.tsx`**

Sumar el import:

```tsx
import EvalSection from '../components/EvalSection'
```

Dentro del JSX, inmediatamente después del cierre del bloque `{!running && run.summary && ( ... )}` (después de su `)}`), agregar:

```tsx
      {!running && (
        <EvalSection runId={id} benchSplit={run.bench_split} evaluated={run.evaluated} />
      )}
```

- [x] **Step 5: Correr y verificar que pasan**

Run: `npm test && npm run build`
Expected: PASS.

---

### Task 11: Frontend — página `/compare` + navegación

**Files:**
- Create: `webconsole/frontend/src/pages/ComparePage.tsx`
- Modify: `webconsole/frontend/src/App.tsx`
- Create: `webconsole/frontend/src/__tests__/ComparePage.test.tsx`

**Interfaces:**
- Consumes: `listRuns` (filtra `evaluated: true`), `getCompare` (Task 8), `GroupedBars` (Task 9).
- Produces: página `/compare` (multi-select con checkboxes de runs evaluados etiquetados `run_id — model · split`; con ≥2 seleccionados fetchea el compare y muestra tabla con mejor-por-fila en negrita + `GroupedBars` + aviso de omitidos); helper puro exportado `bestPerRow(values: Array<number | null>): number` (índice del máximo no-nulo, −1 si no hay); link "Comparar" en el nav y ruta en `App.tsx`.

- [x] **Step 1: Escribir los tests que fallan**

Crear `__tests__/ComparePage.test.tsx`:

```tsx
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ComparePage, { bestPerRow } from '../pages/ComparePage'
import { getCompare, listRuns } from '../api'
import type { CompareResult, RunRow } from '../types'

vi.mock('../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api')>()),
  listRuns: vi.fn(),
  getCompare: vi.fn(),
}))

const ROWS: RunRow[] = [
  { run_id: 'run_a', status: 'succeeded', model: 'gdino', bench_split: 'bench_v2_test', evaluated: true },
  { run_id: 'run_b', status: 'succeeded', model: 'yoloe', bench_split: 'bench_v2_test', evaluated: true },
  { run_id: 'run_c', status: 'succeeded', model: 'mock', bench_split: null, evaluated: false },
]

const COMPARE: CompareResult = {
  runs: [
    { run_id: 'run_a', label: 'gdino · bench_v2_test', model: 'gdino', bench_split: 'bench_v2_test', mAP50: 0.47, cr01_detection_recall: 0.64 },
    { run_id: 'run_b', label: 'yoloe · bench_v2_test', model: 'yoloe', bench_split: 'bench_v2_test', mAP50: 0.3, cr01_detection_recall: 0.1 },
  ],
  classes: ['person', 'helmet'],
  ap_by_class: { person: [0.72, 0.68], helmet: [0.61, null] },
  skipped: ['run_x'],
}

beforeEach(() => vi.clearAllMocks())

describe('bestPerRow', () => {
  it('devuelve el índice del máximo no-nulo', () => {
    expect(bestPerRow([0.3, 0.7, null])).toBe(1)
    expect(bestPerRow([null, null])).toBe(-1)
  })
})

describe('ComparePage', () => {
  it('lista solo runs evaluados y compara al seleccionar 2', async () => {
    vi.mocked(listRuns).mockResolvedValue(ROWS)
    vi.mocked(getCompare).mockResolvedValue(COMPARE)
    render(<ComparePage />)
    await waitFor(() => expect(screen.getByText(/run_a/)).toBeTruthy())
    expect(screen.queryByText(/run_c/)).toBeNull()

    fireEvent.click(screen.getByRole('checkbox', { name: /run_a/ }))
    fireEvent.click(screen.getByRole('checkbox', { name: /run_b/ }))

    await waitFor(() => expect(screen.getByText('gdino · bench_v2_test')).toBeTruthy())
    expect(getCompare).toHaveBeenCalledWith(['run_a', 'run_b'])
    expect(screen.getByText(/AP@0\.5 person/)).toBeTruthy()
    expect(screen.getByText(/omitidos/i)).toBeTruthy() // aviso de skipped
  })
})
```

- [x] **Step 2: Correr y verificar que fallan**

Run: `npm test`
Expected: FAIL (página inexistente).

- [x] **Step 3: Implementar la página**

Crear `pages/ComparePage.tsx`:

```tsx
import { useEffect, useState } from 'react'
import type { CSSProperties } from 'react'
import { getCompare, listRuns } from '../api'
import GroupedBars from '../components/GroupedBars'
import type { CompareResult, RunRow } from '../types'

const CELL: CSSProperties = { padding: '4px 10px', borderBottom: '1px solid #ddd' }

// Índice del mejor valor no-nulo de la fila (−1 si no hay ninguno).
export function bestPerRow(values: Array<number | null>): number {
  let best = -1
  let bestValue = -Infinity
  values.forEach((v, i) => {
    if (v != null && v > bestValue) {
      bestValue = v
      best = i
    }
  })
  return best
}

function MetricRow({ name, values }: { name: string; values: Array<number | null> }) {
  const best = bestPerRow(values)
  return (
    <tr>
      <td style={CELL}>{name}</td>
      {values.map((v, i) => (
        <td key={i} style={{ ...CELL, fontWeight: i === best ? 700 : 400 }}>
          {v ?? '—'}
        </td>
      ))}
    </tr>
  )
}

export default function ComparePage() {
  const [rows, setRows] = useState<RunRow[] | null>(null)
  const [selected, setSelected] = useState<string[]>([])
  const [result, setResult] = useState<CompareResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    listRuns().then(setRows).catch((e) => setError(String(e)))
  }, [])

  useEffect(() => {
    if (selected.length < 2) {
      setResult(null)
      return
    }
    getCompare(selected)
      .then((r) => {
        setResult(r)
        setError(null)
      })
      .catch((e) => setError(String(e)))
  }, [selected])

  const toggle = (id: string) =>
    setSelected((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]))

  if (error && !rows) return <p style={{ color: '#b00' }}>Error: {error}</p>
  if (!rows) return <p>Cargando…</p>
  const evaluables = rows.filter((r) => r.evaluated)
  const series = result
    ? result.runs.map((_r, i) => result.classes.map((c) => result.ap_by_class[c]?.[i] ?? null))
    : []
  return (
    <div style={{ display: 'grid', gap: 16 }}>
      <h2>Comparar runs (BENCH)</h2>
      {evaluables.length === 0 && (
        <p>No hay runs evaluados todavía. Evaluá un run BENCH desde su detalle.</p>
      )}
      <div style={{ display: 'grid', gap: 4 }}>
        {evaluables.map((r) => (
          <label key={r.run_id}>
            <input
              type="checkbox"
              checked={selected.includes(r.run_id)}
              onChange={() => toggle(r.run_id)}
            />{' '}
            {r.run_id} — {r.model ?? '—'} · {r.bench_split ?? '—'}
          </label>
        ))}
      </div>
      {evaluables.length > 0 && selected.length < 2 && <p>Seleccioná al menos 2 runs.</p>}
      {error && rows && <p style={{ color: '#b00' }}>{error}</p>}
      {result && (
        <>
          {result.skipped.length > 0 && (
            <p style={{ color: '#a60' }}>Sin evaluación (omitidos): {result.skipped.join(', ')}</p>
          )}
          <table style={{ borderCollapse: 'collapse', maxWidth: 760 }}>
            <thead>
              <tr>
                <th style={{ ...CELL, textAlign: 'left', background: '#f5f5f5' }}>métrica</th>
                {result.runs.map((r) => (
                  <th key={r.run_id} style={{ ...CELL, textAlign: 'left', background: '#f5f5f5' }}>
                    {r.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {result.classes.map((cls) => (
                <MetricRow key={cls} name={`AP@0.5 ${cls}`} values={result.ap_by_class[cls] ?? []} />
              ))}
              <MetricRow
                name="CR-01 recall"
                values={result.runs.map((r) => r.cr01_detection_recall)}
              />
              <MetricRow name="mAP@0.5" values={result.runs.map((r) => r.mAP50)} />
            </tbody>
          </table>
          <GroupedBars
            groups={result.classes}
            series={series}
            labels={result.runs.map((r) => r.label)}
          />
        </>
      )}
    </div>
  )
}
```

- [x] **Step 4: Registrar ruta y nav en `App.tsx`**

Sumar el import:

```tsx
import ComparePage from './pages/ComparePage'
```

En el `<nav>`, después del link a Catálogos:

```tsx
          <Link to="/compare">Comparar</Link>
```

En `<Routes>`:

```tsx
        <Route path="/compare" element={<ComparePage />} />
```

- [x] **Step 5: Correr y verificar que pasan (suite frontend completa + build)**

Run: `npm test && npm run build`
Expected: PASS.

---

### Task 12: Verificación end-to-end

**Files:** ninguno (verificación operativa; spec §9).

- [x] **Step 1: Suites completas en los tres módulos**

```bash
cd /home/simonll4/projects/e-ovrt_media-plane && make test && make lint
cd /home/simonll4/projects/e-ovrt_experimental-setup/webconsole/backend && .venv/bin/python -m pytest -q && .venv/bin/python -m ruff check src tests
cd /home/simonll4/projects/e-ovrt_experimental-setup/webconsole/frontend && npm test && npm run build
```
Expected: todo PASS.

- [x] **Step 2: Smoke E2E con mock (verifica el cableado y la restricción del GT)**

```bash
# Terminal 1 — servicio desde la raíz del media-plane (CWD importa para el GT)
cd /home/simonll4/projects/e-ovrt_media-plane
EOVRT_MODEL_REF=mock make serve   # :8080

# Terminal 2 — BFF
cd /home/simonll4/projects/e-ovrt_experimental-setup/webconsole/backend
.venv/bin/uvicorn eovrt_webconsole.app:create_app --factory --port 8090

# Terminal 3 — corrida corta sobre bench_v2_test (10 unidades) y evaluación
curl -s -X POST http://localhost:8090/api/runs -H 'Content-Type: application/json' -d '{
  "ingest": {"plugin": "image_folder", "config": {"dataset": "bench_v2_test"}},
  "prompts": {"set_id": "cr01_cr02_bench_v2", "active_ids": null},
  "run": {"max_units": 10}
}'
# esperar a succeeded:
curl -s http://localhost:8090/api/runs/<run_id> | python3 -m json.tool
# debe traer "bench_split": "bench_v2_test", "evaluated": false
curl -s -X POST http://localhost:8090/api/runs/<run_id>/evaluate | python3 -m json.tool
```

Verificar: la respuesta trae `mAP50`, `model`, `bench_split`; los `n_gt` por clase corresponden a las ~10 imágenes procesadas (decenas, **no** los totales de las 196 del GT completo) — esa es la prueba viva de `restrict_gt_to_detections`. `GET .../evaluate` devuelve lo mismo; en la UI (`http://localhost:8090`) el detalle del run muestra la sección de evaluación y `/compare` lista el run.

- [x] **Step 3: Verificación final del spec §9 (requiere GPU + pesos descargados)**

Correr GDINO-tiny y YOLOE-26s sobre `bench_v2_test` completo desde la consola (mismo flow del Step 2, sin `max_units`, arrancando el servicio una vez con cada `EOVRT_MODEL_REF`), evaluar ambos runs y compararlos en `/compare`: tabla + gráfico con AP@0.5 no-deflactados (`n_gt` de person ≈ el del split test, no el del GT combinado). Si no hay GPU disponible en la sesión, dejar este paso documentado como pendiente para el usuario.

---

## Self-review (hecho al escribir el plan)

- **Cobertura del spec**: §3.1→Task 2; §3.2→Task 3; §3.3→Task 3 (shape+mAP50); §3.4→Tasks 1+3+4 (persist/atómico/GET); §3.5→Task 1; §4.1→Task 5; §4.2→Tasks 6–7; §5→Tasks 8–11; §6→Tasks 3/5/6/10; §7→tests por task; §9→Task 12. Sin gaps.
- **Consistencia de tipos**: `run_evaluation(..., restrict_gt_to_detections, persist)` (T1) = lo que llama T3; `bench_metadata`/`BENCH_SPLITS` (T2) = lo que lee T3 (`info.get("bench_split")`); `RunNotFinished(detail)` (T5) = lo que captura T6; shape de `EVAL_RESULT` (T5) = shape real de T3; `EvalResult`/`CompareResult` (T8) = payloads de T3/T7; `groupedBarsLayout`/`SERIES_COLORS`/props (T9) = uso en T11.
