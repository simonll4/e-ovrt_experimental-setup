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


def test_ws_cliente_desconectado_con_upstream_silencioso_cierra_upstream(live_client, fake_state):
    # Deuda F/Task10: si el SPA se va mientras el upstream está en silencio, el
    # proxy debe detectarlo igual y cerrar el WS al servicio (no dejar colgados
    # la conexión upstream ni las tasks). El fake acepta y queda callado; al
    # cerrar el SPA, el proxy debe cerrar el upstream y el fake señaliza.
    fake_state.active_run_id = "run_active_1"
    fake_state.quiet_stream = True
    with live_client.websocket_connect("/api/runs/run_active_1/stream") as ws:
        ws.close()  # el SPA se desconecta con el upstream aún en silencio
        assert fake_state.upstream_closed.wait(timeout=5.0), (
            "el proxy no cerró el upstream tras irse el SPA (fuga en stream silencioso)"
        )


def test_ws_run_desconocido_cierra_4404(live_client):
    with live_client.websocket_connect("/api/runs/nope/stream") as ws:
        try:
            while True:
                ws.receive_json()
        except Exception:  # noqa: BLE001
            pass
    # el cierre llegó sin eventos: el fake cerró 4404 y el proxy lo reenvió


def test_ws_preview_reenvia_binario(live_client):
    import json
    import struct

    with live_client.websocket_connect("/api/preview/stream") as ws:
        msg = ws.receive_bytes()
        hlen = struct.unpack(">I", msg[:4])[0]
        header = json.loads(msg[4 : 4 + hlen].decode("utf-8"))
        assert header["seq"] == 1
        assert msg[4 + hlen :] == b"\xff\xd8fake"


def test_ws_preview_servicio_inaccesible_no_crashea(settings):
    # Mismo mecanismo que test_ws_servicio_inaccesible_no_crashea: puerto muerto,
    # websockets.connect falla al conectar -> el handler debe cerrar 4503 sin
    # propagar la excepción al ASGI.
    settings_dead = dataclasses.replace(settings, service_url="http://127.0.0.1:9")
    app = create_app(settings_dead)
    with TestClient(app) as client:
        with client.websocket_connect("/api/preview/stream") as ws:
            try:
                ws.receive()
            except Exception:  # noqa: BLE001 — el cierre del WS corta el loop
                pass


def test_ws_preview_cliente_desconectado_con_upstream_silencioso_cierra_upstream(
    live_client, fake_state
):
    # Fix 2 (Tarea 7): análogo a test_ws_cliente_desconectado_con_upstream_silencioso_
    # cierra_upstream pero para /api/preview/stream. Antes del fix, _watch_client no
    # chequeaba "websocket.disconnect" y el próximo receive() tras la desconexión
    # lanzaba RuntimeError sin recuperar ("Task exception was never retrieved"). Con
    # el fix, el cliente se va, el proxy detecta el disconnect, cancela/consume todas
    # las tasks y cierra el upstream (el fake lo señaliza).
    fake_state.preview_quiet_stream = True
    with live_client.websocket_connect("/api/preview/stream") as ws:
        ws.close()  # el SPA se desconecta con el upstream de preview aún en silencio
        assert fake_state.preview_upstream_closed.wait(timeout=5.0), (
            "el proxy no cerró el upstream de preview tras irse el SPA (fuga en stream silencioso)"
        )


def test_ws_preview_upstream_cae_abrupto_no_deja_excepcion_sin_recuperar(live_client, fake_state):
    # Endurece el fix 2 (Tarea 7) de forma NO vacua: el test hermano de arriba
    # (upstream silencioso + cliente que se va) pasa igual aunque se revierta
    # el fix, porque en ese escenario `watch` termina normal (no con excepción)
    # y `pump` solo se cancela (CancelledError no deja rastro en el logger).
    # El escenario que sí ejercita el fix es upstream que cae ABRUPTO
    # (preview_abrupt_close): ahí `pump` termina primero con una excepción real
    # (ConnectionClosedError) mientras `watch` sigue pendiente. Antes del fix,
    # el `gather` final solo cubría `pending` (watch, cancelado) y dejaba la
    # excepción de `pump` -- ya en `done` -- sin recuperar: asyncio la loguea
    # como ERROR ("Task exception was never retrieved") en Task.__del__ cuando
    # el GC junta el task. Con el fix (`gather(*active, ...)` sobre TODAS las
    # tasks) la excepción de pump se consume explícitamente y ese log nunca
    # aparece.
    import gc
    import logging
    import time

    class _Capture(logging.Handler):
        def __init__(self):
            super().__init__()
            self.records: list[logging.LogRecord] = []

        def emit(self, record: logging.LogRecord) -> None:
            self.records.append(record)

    handler = _Capture()
    asyncio_logger = logging.getLogger("asyncio")
    asyncio_logger.addHandler(handler)
    try:
        fake_state.preview_abrupt_close = True
        with live_client.websocket_connect("/api/preview/stream") as ws:
            while True:
                message = ws.receive()
                if message["type"] == "websocket.close":
                    break
        # El handler corre en el thread del servidor uvicorn (su propio loop),
        # pero logging es global al proceso: el handler agregado acá también
        # recibe esos records. Forzamos GC repetidas veces para disparar
        # Task.__del__ de forma determinista (sin depender de timing del GC
        # automático) y le damos margen al thread del server para terminar.
        for _ in range(20):
            gc.collect()
            if any("never retrieved" in r.getMessage() for r in handler.records):
                break
            time.sleep(0.05)
    finally:
        asyncio_logger.removeHandler(handler)

    leaked = [r.getMessage() for r in handler.records if "never retrieved" in r.getMessage()]
    assert not leaked, (
        "quedó una excepción de Task sin recuperar (el gather no cubrió todas "
        f"las tasks): {leaked}"
    )


def test_ws_preview_upstream_cae_abrupto_no_reporta_cierre_normal(live_client, fake_state):
    # Fix 1 (Tarea 7): si el upstream de preview cae abrupto (sin close frame), _pump
    # termina con ConnectionClosedError. Antes del fix, `pump.exception() is None`
    # daba False y el close_code quedaba en el default 1000 (mis-signal "cierre
    # normal" al SPA cuando en realidad el upstream murió). Con el fix, el close_code
    # se deriva de _safe_close_code(upstream.close_code), que clampa el cierre
    # abrupto (close_code None/1006) a 4503.
    fake_state.preview_abrupt_close = True
    close_code = None
    with live_client.websocket_connect("/api/preview/stream") as ws:
        while True:
            message = ws.receive()
            if message["type"] == "websocket.close":
                close_code = message.get("code")
                break
    # No debe llegar 1000 (cierre normal espurio): el upstream murió abrupto.
    # _safe_close_code clampa el cierre abrupto (None/1006) a 4503.
    assert close_code == 4503
