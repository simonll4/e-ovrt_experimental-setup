"""Réplica mínima de la API del servicio media-plane (Fase 1) para tests del BFF.

Shapes copiados de la implementación real (e-ovrt_media-plane, service/):
runs.py, model.py, catalog.py, run_manager.py, stream.py, events.py.
"""
from __future__ import annotations

import json
import struct
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
    {"id": "oak_d", "kind": "live", "available": True, "description": "OAK-D Pro PoE (RGB vía DepthAI, IP fija)"},
    # Plugin ficticio no disponible: cubre la política enabled = soportado ∧ available.
    {"id": "thermal_cam", "kind": "live", "available": False, "description": "cámara térmica (no disponible)"},
]
DATASETS = [
    {"id": "demo_v2", "description": "CHV demo v2", "path": "/data/demo", "available": True},
    {"id": "bench_v2_test", "description": "BENCH v2 test", "path": "/data/bench", "available": True},
    {"id": "roto", "description": "no montado", "path": "/nope", "available": False},
]
SUMMARY_FINISHED = {
    "schema_version": "media.summary.v2",
    "run_id": "run_done_1",
    "name": "corrida terminada demo",
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
    "run_descriptor": {"topology": "two_node"},
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
DETECTIONS = [
    {
        "unit_id": f"u{i}",
        "source": {"frame_index": i, "timestamp_ms": float(i) * 100.0},
        "detections": [{"label": "person"}],
    }
    for i in range(5)
]
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
        # Análogo a preview_conflict: cuando está seteado, el 409 de lanzamiento
        # (create_run) incluye este "reason" en el body, como haría el
        # media-plane real al rechazar un run mientras hay una preview activa.
        self.launch_busy_reason: str | None = None
        self.launched: list[dict] = []
        self.stopped: list[str] = []
        self.stream_events: list[dict] = list(DEFAULT_STREAM_EVENTS)
        self.reject_launch: bool = False
        self.send_malformed: bool = False
        self.eval_results: dict[str, dict] = {}
        self.evaluate_not_bench: bool = False
        self.dropped: dict[str, list[dict]] = {}
        self.deleted: list[str] = []
        # Stream que acepta y queda en silencio (nunca envía ni cierra): sirve
        # para verificar que el proxy detecta la desconexión del SPA aunque el
        # upstream esté callado. `upstream_closed` se activa cuando el proxy
        # cierra su conexión hacia este fake (cross-thread: se lee desde el test).
        self.quiet_stream: bool = False
        self.upstream_closed: threading.Event = threading.Event()
        self.preview_status: str = "idle"
        self.preview_started: list[dict] = []
        self.preview_stopped: int = 0
        self.preview_conflict: dict | None = None
        # Análogo a quiet_stream/upstream_closed pero para el WS de preview:
        # acepta y queda en silencio hasta que el proxy cierre el upstream tras
        # irse el cliente (Fix 2, Tarea 7).
        self.preview_quiet_stream: bool = False
        self.preview_upstream_closed: threading.Event = threading.Event()
        # Simula una caída abrupta del upstream de preview (sin close frame):
        # el handler revienta después de aceptar, así el server ASGI corta el
        # socket sin handshake de cierre (Fix 1, Tarea 7).
        self.preview_abrupt_close: bool = False


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
            content = {"detail": "run activo", "active_run_id": state.active_run_id}
            if state.launch_busy_reason is not None:
                content["reason"] = state.launch_busy_reason
            return JSONResponse(status_code=409, content=content)
        state.launched.append(body)
        state.active_run_id = "run_active_1"
        return {"run_id": "run_active_1"}

    @app.get("/api/runs")
    def list_runs():
        if not state.ready:
            return JSONResponse(status_code=503, content={"detail": "Servicio no listo (modelo no cargado)"})
        runs = []
        if state.active_run_id:
            runs.append({"run_id": state.active_run_id, "name": "corrida activa demo",
                         "status": "running", "live": True})
        if "run_done_1" not in state.deleted:
            runs.append(
                {
                    "run_id": "run_done_1",
                    "name": "corrida terminada demo",
                    "status": "succeeded",
                    "bench_split": "bench_v2_test",
                    "evaluated": "run_done_1" in state.eval_results,
                    "live": False,
                }
            )
        return runs

    @app.get("/api/runs/{run_id}")
    def get_run(run_id: str):
        if not state.ready:
            return JSONResponse(status_code=503, content={"detail": "Servicio no listo (modelo no cargado)"})
        if run_id == state.active_run_id:
            return {"run_id": run_id, "status": "running", "live": True,
                    "name": "corrida activa demo",
                    "started_at": "2026-07-03T12:00:00+00:00", "model": MODEL["ref"]}
        if run_id == "run_done_1" and run_id not in state.deleted:
            return {
                "run_id": run_id,
                "status": "succeeded",
                "summary": SUMMARY_FINISHED,
                "bench_split": "bench_v2_test",
                "evaluated": run_id in state.eval_results,
                "live": False,
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

    @app.delete("/api/runs/{run_id}", status_code=204)
    def delete_run(run_id: str):
        if not state.ready:
            return JSONResponse(status_code=503, content={"detail": "Servicio no listo (modelo no cargado)"})
        if run_id == state.active_run_id:
            return JSONResponse(status_code=409, content={"detail": "No se puede borrar un run activo"})
        if run_id != "run_done_1" or run_id in state.deleted:
            return JSONResponse(status_code=404, content={"detail": f"Run desconocido: {run_id}"})
        state.deleted.append(run_id)
        return Response(status_code=204)

    @app.post("/api/runs/{run_id}/evaluate")
    def evaluate_run(run_id: str):
        if not state.ready:
            return JSONResponse(status_code=503, content={"detail": "Servicio no listo (modelo no cargado)"})
        if run_id == state.active_run_id:
            return JSONResponse(status_code=409, content={"detail": "No se evalúa un run en curso"})
        if run_id != "run_done_1" or run_id in state.deleted:
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
        if result is None or run_id in state.deleted:
            return JSONResponse(status_code=404, content={"detail": f"Run no evaluado: {run_id}"})
        return result

    @app.get("/api/runs/{run_id}/detections")
    def detections(run_id: str, page: int = Query(1, ge=1), page_size: int = Query(100, ge=1, le=1000)):
        if not state.ready:
            return JSONResponse(status_code=503, content={"detail": "Servicio no listo (modelo no cargado)"})
        if run_id != "run_done_1" or run_id in state.deleted:
            return JSONResponse(status_code=404, content={"detail": "Sin detecciones"})
        start = (page - 1) * page_size
        items = DETECTIONS[start : start + page_size]
        return {"page": page, "page_size": page_size, "total": len(DETECTIONS), "items": items}

    @app.get("/api/runs/{run_id}/dropped")
    def dropped(run_id: str, page: int = Query(1, ge=1), page_size: int = Query(100, ge=1, le=1000)):
        if not state.ready:
            return JSONResponse(status_code=503, content={"detail": "Servicio no listo (modelo no cargado)"})
        if run_id not in state.dropped or run_id in state.deleted:
            return JSONResponse(status_code=404, content={"detail": f"Run desconocido: {run_id}"})
        items_all = state.dropped[run_id]
        start = (page - 1) * page_size
        items = items_all[start : start + page_size]
        return {"page": page, "page_size": page_size, "total": len(items_all), "items": items}

    @app.get("/api/runs/{run_id}/artifacts")
    def artifacts_index(run_id: str):
        if run_id in state.deleted:
            return JSONResponse(status_code=404, content={"detail": "Run desconocido"})
        return {
            "run_id": run_id,
            "items": [
                {"path": "summary.json", "name": "summary.json", "size_bytes": 23,
                 "n_files": None, "description": "Métricas de la corrida"},
                {"path": "previews/", "name": "previews/", "size_bytes": 8,
                 "n_files": 1, "description": "1 imágenes de vista previa"},
            ],
        }

    @app.get("/api/runs/{run_id}/artifacts/{artifact_path:path}")
    def artifact(run_id: str, artifact_path: str):
        data = ARTIFACTS.get(artifact_path)
        if run_id != "run_done_1" or run_id in state.deleted or data is None:
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
        if run_id == "run_done_1" and run_id not in state.deleted:
            await ws.send_json({"type": "state", "status": "succeeded", "error": None})
            await ws.close(code=1000)
            return
        await ws.close(code=4404)

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
        return Response(status_code=204)

    @app.websocket("/api/preview/stream")
    async def fake_preview_stream(ws: WebSocket):
        await ws.accept()
        if state.preview_quiet_stream:
            # Acepta y no emite nada; espera hasta que el proxy cierre el
            # upstream (al detectar que el SPA se fue) y lo señaliza.
            try:
                while True:
                    message = await ws.receive()
                    if message["type"] == "websocket.disconnect":
                        break
            except (WebSocketDisconnect, RuntimeError):
                pass
            state.preview_upstream_closed.set()
            return
        if state.preview_abrupt_close:
            # Revienta después de aceptar: el server ASGI corta el socket sin
            # handshake de cierre, así el cliente (websockets) ve una caída
            # abrupta (ConnectionClosedError, close_code None/no enviable).
            raise RuntimeError("upstream de preview cae abrupto (simulado)")
        header = json.dumps(
            {"seq": 1, "ts": 0.0, "width": 64, "height": 48, "mode": "raw", "detections": []}
        ).encode("utf-8")
        await ws.send_bytes(struct.pack(">I", len(header)) + header + b"\xff\xd8fake")
        await ws.send_json({"type": "state", "status": "idle", "error": None})
        await ws.close()

    return app
