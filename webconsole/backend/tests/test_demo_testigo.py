"""Demo: testigo MQTT y la ida y vuelta del chequeo previo, con un cliente paho simulado.

El cliente simulado reproduce el contrato de callbacks de paho v2 (on_connect →
subscribe → on_subscribe; publish → on_message en los suscriptos). La prueba con un
broker real es el smoke G1 en la Victus (`infra/demo/README.md`).
"""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from eovrt_webconsole.demo.testigo import TestigoError, TestigoMqtt, ping_broker


class _ReasonCode:
    def __init__(self, failure: bool) -> None:
        self.is_failure = failure


class FakeBroker:
    def __init__(self, *, rechaza_conexion=False, rechaza_suscripcion=False, eco=True):
        self.rechaza_conexion = rechaza_conexion
        self.rechaza_suscripcion = rechaza_suscripcion
        self.eco = eco
        self.clientes: list[FakeClient] = []

    def cliente(self):
        c = FakeClient(self)
        self.clientes.append(c)
        return c

    def publicar(self, topic: str, payload: bytes, qos: int = 1) -> None:
        for c in self.clientes:
            if any(_coincide(f, topic) for f in c.filtros):
                c.on_message(c, None, SimpleNamespace(topic=topic, qos=qos, payload=payload))


def _coincide(filtro: str, topic: str) -> bool:
    if filtro.endswith("/#"):
        return topic.startswith(filtro[:-2])
    return filtro == topic


class FakeClient:
    def __init__(self, broker: FakeBroker) -> None:
        self.broker = broker
        self.filtros: list[str] = []
        self.qos_suscripto: list[int] = []
        self.on_connect = self.on_subscribe = self.on_message = None
        self.conectado = False

    def connect(self, host, port, keepalive=60):
        if host == "inalcanzable":
            raise OSError("connection refused")
        self.conectado = True

    def loop_start(self):
        self.on_connect(self, None, {}, _ReasonCode(self.broker.rechaza_conexion), None)

    def subscribe(self, topic, qos=0):
        self.filtros.append(topic)
        self.qos_suscripto.append(qos)
        self.on_subscribe(self, None, 1, [_ReasonCode(self.broker.rechaza_suscripcion)], None)

    def publish(self, topic, payload, qos=0):
        if self.broker.eco:
            self.broker.publicar(topic, payload.encode() if isinstance(payload, str) else payload, qos)

    def disconnect(self):
        self.conectado = False

    def loop_stop(self):
        pass


def test_testigo_se_suscribe_qos1_a_las_alertas_y_registra_crudo_y_hora():
    broker = FakeBroker()
    testigo = TestigoMqtt("mosquitto", 1883, client_factory=broker.cliente, reloj=lambda: 1000.5)
    testigo.iniciar()
    testigo.esperar_suscripcion(0.1)
    cliente = broker.clientes[0]
    assert cliente.filtros == ["eovrt/alerts/#"] and cliente.qos_suscripto == [1]
    payload = {"notification_id": "n1", "alert_id": "a1", "condition_id": "CR-01",
               "confirmed_wall_ms": 1000000.0}
    broker.publicar("eovrt/alerts/high", json.dumps(payload).encode())
    (msg,) = testigo.mensajes()
    assert msg["topic"] == "eovrt/alerts/high" and msg["qos"] == 1
    assert msg["payload"] == payload
    assert json.loads(msg["crudo"]) == payload
    assert msg["recibido_ms"] == 1000500.0
    testigo.cerrar()
    assert not cliente.conectado


def test_testigo_guarda_un_payload_invalido_sin_romperse():
    broker = FakeBroker()
    testigo = TestigoMqtt("h", 1, client_factory=broker.cliente)
    testigo.iniciar()
    broker.publicar("eovrt/alerts/high", b"no es json")
    (msg,) = testigo.mensajes()
    assert msg["payload"] is None and msg["error"] == "payload no es JSON"


def test_testigo_suscripcion_rechazada():
    broker = FakeBroker(rechaza_suscripcion=True)
    testigo = TestigoMqtt("h", 1, client_factory=broker.cliente)
    testigo.iniciar()
    with pytest.raises(TestigoError, match="suscripción"):
        testigo.esperar_suscripcion(0.05)


def test_testigo_broker_inalcanzable():
    testigo = TestigoMqtt("inalcanzable", 1, client_factory=FakeBroker().cliente)
    with pytest.raises(TestigoError, match="inalcanzable"):
        testigo.iniciar()


def test_testigo_escribe_jsonl(tmp_path):
    broker = FakeBroker()
    testigo = TestigoMqtt("h", 1, client_factory=broker.cliente)
    testigo.iniciar()
    broker.publicar("eovrt/alerts/medium", b'{"alert_id": "x"}')
    testigo.escribir(tmp_path / "witness.jsonl")
    lineas = (tmp_path / "witness.jsonl").read_text().splitlines()
    assert len(lineas) == 1 and json.loads(lineas[0])["payload"] == {"alert_id": "x"}


def test_ping_ida_y_vuelta_por_un_topic_que_no_es_el_de_alertas():
    broker = FakeBroker()
    res = ping_broker("mosquitto", 1883, timeout_s=0.5, client_factory=broker.cliente)
    assert res["ok"] is True and res["rtt_ms"] is not None
    (filtro,) = broker.clientes[0].filtros
    assert filtro.startswith("eovrt/demo/ping/") and not filtro.startswith("eovrt/alerts")


def test_ping_sin_eco_falla():
    res = ping_broker("h", 1, timeout_s=0.2, client_factory=FakeBroker(eco=False).cliente)
    assert res["ok"] is False and "no volvió" in res["detalle"]


def test_ping_broker_inalcanzable():
    res = ping_broker("inalcanzable", 1, timeout_s=0.2, client_factory=FakeBroker().cliente)
    assert res["ok"] is False and "inalcanzable" in res["detalle"]
