"""Réplica mínima de la API del servicio media-plane (Fase 1) para tests del BFF.

Shapes copiados de la implementación real (e-ovrt_media-plane, service/):
runs.py, model.py, catalog.py, run_manager.py, stream.py, events.py.
"""
from __future__ import annotations

import threading

from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, Response

MODEL = {
    "ref": "mock",
    "name": "mock",
    "adapter": "mock",
    "device": "cpu",
    "thresholds": {"box": 0.35, "text": 0.25, "confidence": None, "iou": None},
    "runtime": {"half_precision": False, "warmup": False},
}
PLUGINS = [
    {"id": "image_folder", "kind": "bounded", "available": True, "description": "Carpeta de imágenes"},
    {"id": "video_file", "kind": "bounded", "available": True, "description": "Archivo de video local"},
    {"id": "rtsp", "kind": "live", "available": True, "description": "Stream RTSP (cámara IP)"},
    {"id": "oak_d", "kind": "live", "available": False, "description": "OAK-D Pro PoE (no disponible)"},
]
DATASETS = [
    {"id": "demo_v2", "description": "CHV demo v2", "path": "/data/demo", "available": True},
    {"id": "bench_v2_test", "description": "BENCH v2 test", "path": "/data/bench", "available": True},
    {"id": "roto", "description": "no montado", "path": "/nope", "available": False},
]
SUMMARY_FINISHED = {
    "schema_version": "media.summary.v2",
    "run_id": "run_done_1",
    "status": "succeeded",
    "model_name": "mock",
    "prompt_set_id": "demo_set",
    "source_type": "image_folder",
    "units_processed": 3,
    "total_detections": 7,
    "detections_by_label": {"person": 5, "helmet": 2},
    "p95_latency_ms": 40.0,
    "fps_effective": 12.5,
    "duration_seconds": 0.24,
    "device": "cpu",
    "started_at": "2026-07-03T10:00:00+00:00",
}
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
DETECTIONS = [{"unit_id": f"u{i}", "detections": [{"label": "person"}]} for i in range(5)]
ARTIFACTS = {"summary.json": b'{"status": "succeeded"}', "previews/u0.preview.jpg": b"JPEGDATA"}
DEFAULT_STREAM_EVENTS = [
    {"type": "metric", "unit_id": "u0", "fps": 1.0, "latency_total_ms": 100.0,
     "detections_count": 1, "gpu_memory_mb": 0.0},
    {"type": "metric", "unit_id": "u1", "fps": 2.0, "latency_total_ms": 90.0,
     "detections_count": 2, "gpu_memory_mb": 0.0},
    {"type": "detection", "unit_id": "u1", "count": 2},
    {"type": "error", "unit_id": "u1", "stage": "inference", "message": "boom"},
    {"type": "state", "status": "succeeded", "error": None},
]


class FakeState:
    def __init__(self) -> None:
        self.ready = True
        self.active_run_id: str | None = None
        self.launched: list[dict] = []
        self.stopped: list[str] = []
        self.stream_events: list[dict] = list(DEFAULT_STREAM_EVENTS)
        self.reject_launch: bool = False
        self.send_malformed: bool = False
        self.eval_results: dict[str, dict] = {}
        self.evaluate_not_bench: bool = False
        # Stream que acepta y queda en silencio (nunca envía ni cierra): sirve
        # para verificar que el proxy detecta la desconexión del SPA aunque el
        # upstream esté callado. `upstream_closed` se activa cuando el proxy
        # cierra su conexión hacia este fake (cross-thread: se lee desde el test).
        self.quiet_stream: bool = False
        self.upstream_closed: threading.Event = threading.Event()


def make_fake_service(state: FakeState) -> FastAPI:
    app = FastAPI()

    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}

    @app.get("/readyz")
    def readyz():
        if state.ready:
            return {"status": "ready", "model": MODEL["ref"]}
        return JSONResponse(status_code=503, content={"status": "not_ready", "error": None})

    @app.get("/api/model")
    def model():
        return MODEL

    @app.get("/api/catalog/ingest-plugins")
    def plugins():
        return PLUGINS

    @app.get("/api/catalog/datasets")
    def datasets():
        return DATASETS

    @app.post("/api/runs", status_code=201)
    async def create_run(body: dict):
        if not state.ready:
            return JSONResponse(status_code=503, content={"detail": "Servicio no listo (modelo no cargado)"})
        # Rechazos que el BFF ejercita: 'model' en el body (extra prohibido) y faltantes requeridos.
        if "model" in body:
            return JSONResponse(status_code=422, content={"detail": "sección 'model' no permitida"})
        if "ingest" not in body or "prompts" not in body:
            return JSONResponse(
                status_code=422, content={"detail": "faltan campos requeridos (ingest, prompts)"}
            )
        if state.reject_launch:
            return JSONResponse(status_code=422, content={"detail": "config rechazada por el servicio"})
        if state.active_run_id:
            return JSONResponse(
                status_code=409,
                content={"detail": "run activo", "active_run_id": state.active_run_id},
            )
        state.launched.append(body)
        state.active_run_id = "run_active_1"
        return {"run_id": "run_active_1"}

    @app.get("/api/runs")
    def list_runs():
        if not state.ready:
            return JSONResponse(status_code=503, content={"detail": "Servicio no listo (modelo no cargado)"})
        runs = []
        if state.active_run_id:
            runs.append({"run_id": state.active_run_id, "status": "running"})
        runs.append(
            {
                "run_id": "run_done_1",
                "status": "succeeded",
                "bench_split": "bench_v2_test",
                "evaluated": "run_done_1" in state.eval_results,
            }
        )
        return runs

    @app.get("/api/runs/{run_id}")
    def get_run(run_id: str):
        if not state.ready:
            return JSONResponse(status_code=503, content={"detail": "Servicio no listo (modelo no cargado)"})
        if run_id == state.active_run_id:
            return {"run_id": run_id, "status": "running",
                    "started_at": "2026-07-03T12:00:00+00:00", "model": MODEL["ref"]}
        if run_id == "run_done_1":
            return {
                "run_id": run_id,
                "status": "succeeded",
                "summary": SUMMARY_FINISHED,
                "bench_split": "bench_v2_test",
                "evaluated": run_id in state.eval_results,
            }
        return JSONResponse(status_code=404, content={"detail": f"Run desconocido: {run_id}"})

    @app.post("/api/runs/{run_id}/stop", status_code=202)
    def stop_run(run_id: str):
        if not state.ready:
            return JSONResponse(status_code=503, content={"detail": "Servicio no listo (modelo no cargado)"})
        if run_id != state.active_run_id:
            return JSONResponse(status_code=404, content={"detail": f"Run desconocido: {run_id}"})
        state.stopped.append(run_id)
        return {"run_id": run_id, "stopping": True}

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

    @app.get("/api/runs/{run_id}/detections")
    def detections(run_id: str, page: int = Query(1, ge=1), page_size: int = Query(100, ge=1, le=1000)):
        if not state.ready:
            return JSONResponse(status_code=503, content={"detail": "Servicio no listo (modelo no cargado)"})
        if run_id != "run_done_1":
            return JSONResponse(status_code=404, content={"detail": "Sin detecciones"})
        start = (page - 1) * page_size
        items = DETECTIONS[start : start + page_size]
        return {"page": page, "page_size": page_size, "total": len(DETECTIONS), "items": items}

    @app.get("/api/runs/{run_id}/artifacts/{artifact_path:path}")
    def artifact(run_id: str, artifact_path: str):
        data = ARTIFACTS.get(artifact_path)
        if run_id != "run_done_1" or data is None:
            return JSONResponse(status_code=404, content={"detail": "Artefacto no encontrado"})
        return Response(content=data, media_type="application/octet-stream",
                        headers={"accept-ranges": "bytes"})

    @app.websocket("/api/runs/{run_id}/stream")
    async def stream(ws: WebSocket, run_id: str):
        await ws.accept()
        if state.quiet_stream and run_id == state.active_run_id:
            # Acepta y no emite nada; espera hasta que el proxy cierre el
            # upstream (al detectar que el SPA se fue) y lo señaliza.
            try:
                while True:
                    message = await ws.receive()
                    if message["type"] == "websocket.disconnect":
                        break
            except (WebSocketDisconnect, RuntimeError):
                pass
            state.upstream_closed.set()
            return
        if run_id == state.active_run_id:
            if state.send_malformed:
                # Frame no-JSON: ejercita el guard de _pump (no debe matar el proxy).
                await ws.send_text("not-json{")
            for event in state.stream_events:
                await ws.send_json(event)
            await ws.close(code=1000)
            return
        if run_id == "run_done_1":
            await ws.send_json({"type": "state", "status": "succeeded", "error": None})
            await ws.close(code=1000)
            return
        await ws.close(code=4404)

    return app
