"""Testigo MQTT de la demo: la prueba de que la alerta pasó por el broker.

Es independiente del distribuidor: se suscribe a `eovrt/alerts/#` con QoS 1 ANTES de
lanzar la corrida y registra cada mensaje con su hora de recepción. Lógica tomada de
`tools/talert_campaign/mqtt_witness.py` (la campaña t_alert); acá además se guarda el
mensaje crudo, porque la capa de evidencia lo muestra tal cual llegó.

`ping_broker` es la ida y vuelta real del chequeo previo: publica un nonce en
`eovrt/demo/ping/<nonce>` (no es el topic de alertas) y espera recibirlo.

El cliente paho se inyecta (`client_factory`) para poder probar sin broker.
"""
from __future__ import annotations

import json
import secrets
import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

TOPIC_ALERTAS = "eovrt/alerts/#"
TOPIC_PING = "eovrt/demo/ping"


def _cliente_paho() -> Any:
    import paho.mqtt.client as mqtt  # import tardío: el resto del BFF no lo necesita

    return mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)


def _fallo(reason_code: Any) -> bool:
    """paho v2 entrega ReasonCode (con `is_failure`) o enteros en versiones viejas."""
    if hasattr(reason_code, "is_failure"):
        return bool(reason_code.is_failure)
    return reason_code not in (0, None)


class TestigoError(RuntimeError):
    """El testigo no pudo conectarse o suscribirse a tiempo."""

    __test__ = False  # el nombre empieza con "Test": que pytest no lo tome por un test


class TestigoMqtt:
    __test__ = False

    def __init__(
        self,
        host: str,
        port: int,
        topic: str = TOPIC_ALERTAS,
        *,
        client_factory: Callable[[], Any] = _cliente_paho,
        reloj: Callable[[], float] = time.time,
    ) -> None:
        self.host = host
        self.port = port
        self.topic = topic
        self._factory = client_factory
        self._reloj = reloj
        self._client: Any = None
        self._suscripto = threading.Event()
        self._lock = threading.Lock()
        self._mensajes: list[dict[str, Any]] = []
        self._errores: list[str] = []

    def iniciar(self) -> None:
        if self._client is not None:
            raise TestigoError("el testigo ya está iniciado")
        client = self._factory()

        def on_connect(client, userdata, flags, reason_code, properties=None) -> None:
            if _fallo(reason_code):
                with self._lock:
                    self._errores.append(f"conexión rechazada por el broker ({reason_code})")
                return
            client.subscribe(self.topic, qos=1)

        def on_subscribe(client, userdata, mid, reason_codes, properties=None) -> None:
            codes = reason_codes if isinstance(reason_codes, (list, tuple)) else [reason_codes]
            if not codes or any(_fallo(code) for code in codes):
                with self._lock:
                    self._errores.append("el broker rechazó la suscripción")
                return
            self._suscripto.set()

        def on_message(client, userdata, message) -> None:
            ahora = self._reloj()
            crudo = message.payload.decode("utf-8", errors="replace")
            try:
                payload = json.loads(crudo)
                error = None
            except (json.JSONDecodeError, ValueError):
                payload, error = None, "payload no es JSON"
            registro = {
                "recibido_ms": round(ahora * 1000.0, 3),
                "recibido_en": datetime.fromtimestamp(ahora, tz=UTC).isoformat(),
                "topic": message.topic,
                "qos": message.qos,
                "payload": payload,
                "crudo": crudo,
                "error": error,
            }
            with self._lock:
                self._mensajes.append(registro)

        client.on_connect = on_connect
        client.on_subscribe = on_subscribe
        client.on_message = on_message
        try:
            client.connect(self.host, self.port, keepalive=30)
        except OSError as exc:
            raise TestigoError(f"broker inalcanzable ({self.host}:{self.port}): {exc}") from exc
        client.loop_start()
        self._client = client

    def esperar_suscripcion(self, timeout_s: float = 5.0) -> None:
        if not self._suscripto.wait(timeout_s):
            with self._lock:
                causa = self._errores[0] if self._errores else "sin respuesta del broker"
            raise TestigoError(f"el testigo no se suscribió a tiempo: {causa}")

    def mensajes(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._mensajes)

    def errores(self) -> list[str]:
        with self._lock:
            return list(self._errores)

    def escribir(self, path: Path) -> None:
        lineas = "".join(json.dumps(m, ensure_ascii=False) + "\n" for m in self.mensajes())
        path.write_text(lineas, encoding="utf-8")

    def cerrar(self) -> None:
        client, self._client = self._client, None
        if client is None:
            return
        try:
            client.disconnect()
        finally:
            client.loop_stop()


def ping_broker(
    host: str,
    port: int,
    *,
    timeout_s: float = 3.0,
    client_factory: Callable[[], Any] = _cliente_paho,
) -> dict[str, Any]:
    """Ida y vuelta real por el broker: publica un nonce y espera recibirlo.

    Devuelve `{"ok": bool, "rtt_ms": float | None, "detalle": str}`. Bloquea hasta
    `timeout_s`: llamarlo fuera del loop de asyncio (`asyncio.to_thread`).
    """
    nonce = secrets.token_hex(6)
    topic = f"{TOPIC_PING}/{nonce}"
    recibido = threading.Event()
    suscripto = threading.Event()
    errores: list[str] = []
    client = client_factory()

    def on_connect(client, userdata, flags, reason_code, properties=None) -> None:
        if _fallo(reason_code):
            errores.append(f"conexión rechazada ({reason_code})")
            return
        client.subscribe(topic, qos=1)

    def on_subscribe(client, userdata, mid, reason_codes, properties=None) -> None:
        suscripto.set()

    def on_message(client, userdata, message) -> None:
        if message.payload.decode("utf-8", errors="replace") == nonce:
            recibido.set()

    client.on_connect = on_connect
    client.on_subscribe = on_subscribe
    client.on_message = on_message
    inicio = time.monotonic()
    try:
        client.connect(host, port, keepalive=10)
    except OSError as exc:
        return {"ok": False, "rtt_ms": None, "detalle": f"broker inalcanzable ({host}:{port}): {exc}"}
    client.loop_start()
    try:
        if not suscripto.wait(timeout_s):
            causa = errores[0] if errores else "sin respuesta"
            return {"ok": False, "rtt_ms": None, "detalle": f"no se pudo suscribir al ping: {causa}"}
        envio = time.monotonic()
        client.publish(topic, nonce, qos=1)
        restante = max(0.1, timeout_s - (envio - inicio))
        if not recibido.wait(restante):
            return {"ok": False, "rtt_ms": None, "detalle": "el ping no volvió del broker"}
        rtt = (time.monotonic() - envio) * 1000.0
        return {"ok": True, "rtt_ms": round(rtt, 1), "detalle": f"ida y vuelta en {rtt:.0f} ms"}
    finally:
        try:
            client.disconnect()
        finally:
            client.loop_stop()
