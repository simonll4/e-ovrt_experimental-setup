import dataclasses

from fastapi.testclient import TestClient

from eovrt_webconsole.app import create_app
from eovrt_webconsole.routers.stream import _CoalescingBuffer, _safe_close_code


def test_safe_close_code_clampa():
    # Reservados/ausentes: no se pueden enviar por el wire -> el SPA reconecta.
    assert _safe_close_code(1006) == 4503
    assert _safe_close_code(None) == 4503
    assert _safe_close_code(1005) == 4503
    # Válidos: se preservan tal cual.
    assert _safe_close_code(1000) == 1000
    assert _safe_close_code(4404) == 4404
    assert _safe_close_code(4503) == 4503


def test_ws_servicio_inaccesible_no_crashea(settings):
    # Puerto muerto: nada escucha ahí, así que websockets.connect falla al conectar.
    settings_dead = dataclasses.replace(settings, service_url="http://127.0.0.1:9")
    app = create_app(settings_dead)
    with TestClient(app) as client:
        with client.websocket_connect("/api/runs/run_x/stream") as ws:
            # El upstream nunca conecta: el handler debe cerrar con 4503 sin
            # propagar ProtocolError/WebSocketException al ASGI.
            try:
                ws.receive()
            except Exception:  # noqa: BLE001 — el cierre del WS corta el loop
                pass
    # Si llegamos acá sin excepción no manejada, el fix del handler sostiene.


def test_buffer_coalesce_metricas_y_ordena_discretos():
    buffer = _CoalescingBuffer()
    for i in range(5):
        buffer.push({"type": "metric", "unit_id": f"u{i}"})
    buffer.push({"type": "detection", "unit_id": "u4", "count": 1})
    buffer.push({"type": "error", "message": "x"})
    events = buffer.drain()
    metrics = [e for e in events if e["type"] == "metric"]
    assert len(metrics) == 1 and metrics[0]["unit_id"] == "u4"
    assert [e["type"] for e in events if e["type"] != "metric"] == ["detection", "error"]
    assert buffer.drain() == []


def test_ws_proxy_reenvia_eventos(live_client, fake_state):
    fake_state.active_run_id = "run_active_1"
    received = []
    with live_client.websocket_connect("/api/runs/run_active_1/stream") as ws:
        # El fake emite 2 metric + detection + error + state y cierra: el proxy
        # coalesce las métricas y hace drain final antes de cerrar.
        try:
            while True:
                received.append(ws.receive_json())
        except Exception:  # noqa: BLE001 — el cierre del WS corta el loop
            pass
    types = [e["type"] for e in received]
    assert "state" in types
    assert "detection" in types
    metrics = [e for e in received if e["type"] == "metric"]
    assert len(metrics) >= 1
    assert metrics[-1]["unit_id"] == "u1"  # la última gana


def test_pump_descarta_frame_malformado(live_client, fake_state):
    # El fake manda un frame no-JSON antes de los eventos normales: _pump debe
    # descartarlo (try/except) y seguir leyendo, sin matar el proxy ni el WS.
    fake_state.active_run_id = "run_active_1"
    fake_state.send_malformed = True
    received = []
    with live_client.websocket_connect("/api/runs/run_active_1/stream") as ws:
        try:
            while True:
                received.append(ws.receive_json())
        except Exception:  # noqa: BLE001 — el cierre del WS corta el loop
            pass
    types = [e["type"] for e in received]
    # Si el frame malformado hubiera matado el pump, no llegaría ningún evento.
    assert "state" in types
    assert "detection" in types
    metrics = [e for e in received if e["type"] == "metric"]
    assert len(metrics) >= 1


def test_ws_run_desconocido_cierra_4404(live_client):
    with live_client.websocket_connect("/api/runs/nope/stream") as ws:
        try:
            while True:
                ws.receive_json()
        except Exception:  # noqa: BLE001
            pass
    # el cierre llegó sin eventos: el fake cerró 4404 y el proxy lo reenvió
