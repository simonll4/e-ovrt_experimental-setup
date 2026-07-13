from __future__ import annotations


def test_ingest_plugins_con_policy_soporte(client):
    plugins = {p["id"]: p for p in client.get("/api/catalog/ingest-plugins").json()}
    assert set(plugins) == {"image_folder", "video_file", "rtsp", "oak_d", "thermal_cam"}
    assert plugins["image_folder"]["enabled"] is True
    assert plugins["video_file"]["enabled"] is True
    # rtsp: fuente viva soportada de forma permanente por la consola
    assert plugins["rtsp"]["available"] is True
    assert plugins["rtsp"]["enabled"] is True
    # oak_d: soportado por la consola desde 2026-07-13 y disponible en el servicio
    assert plugins["oak_d"]["available"] is True
    assert plugins["oak_d"]["enabled"] is True
    # enabled = soportado por la consola ∧ available en el servicio:
    # un plugin no disponible queda deshabilitado aunque el catálogo lo liste.
    assert plugins["thermal_cam"]["enabled"] is False


def test_datasets_pass_through(client):
    datasets = {d["id"]: d for d in client.get("/api/catalog/datasets").json()}
    assert "demo_v2" in datasets
    assert datasets["roto"]["available"] is False


def test_servicio_caido_502(settings):
    import httpx
    from fastapi.testclient import TestClient

    from eovrt_webconsole.app import create_app

    def _down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down", request=request)

    app = create_app(settings, service_transport=httpx.MockTransport(_down))
    with TestClient(app) as c:
        assert c.get("/api/catalog/ingest-plugins").status_code == 502
        assert c.get("/api/catalog/datasets").status_code == 502
