"""Proxy REST BFF de /api/preview (Tarea 6)."""
from __future__ import annotations


def test_post_preview_ok(client, fake_state):
    r = client.post("/api/preview", json={"mode": "raw", "ingest": {"plugin": "rtsp", "config": {}}})
    assert r.status_code == 201
    assert r.json()["preview_id"] == "pv_1"


def test_post_preview_409_passthrough(client, fake_state):
    fake_state.preview_conflict = {"detail": "ocupado", "reason": "run_active", "active_run_id": "run_9"}
    r = client.post("/api/preview", json={"mode": "raw", "ingest": {"plugin": "rtsp", "config": {}}})
    assert r.status_code == 409
    assert r.json() == fake_state.preview_conflict


def test_get_y_delete_preview(client, fake_state):
    fake_state.preview_status = "streaming"
    assert client.get("/api/preview").json()["status"] == "streaming"
    assert client.delete("/api/preview").status_code == 204
    assert fake_state.preview_stopped == 1
