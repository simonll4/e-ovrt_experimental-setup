from __future__ import annotations

import json
import socket
import subprocess
import threading
import time
from collections import Counter
from pathlib import Path
from typing import Any, Self

import paho.mqtt.client as mqtt

from .model import GateViolation, WitnessMessage


class MqttWitness:
    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self._client: mqtt.Client | None = None
        self._subscribed = threading.Event()
        self._lock = threading.Lock()
        self._messages: list[WitnessMessage] = []
        self._errors: list[str] = []

    def start(self, topic: str) -> None:
        if self._client is not None:
            raise GateViolation("MQTT witness already started")
        client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)

        def on_connect(client, userdata, flags, reason_code, properties) -> None:
            if reason_code != 0:
                self._errors.append(f"connect reason={reason_code}")
                return
            client.subscribe(topic, qos=1)

        def on_subscribe(client, userdata, mid, reason_codes, properties) -> None:
            if not reason_codes or any(code.is_failure for code in reason_codes):
                self._errors.append("subscription rejected")
                return
            self._subscribed.set()

        def on_message(client, userdata, message) -> None:
            try:
                payload: Any = json.loads(message.payload)
                notification_id = payload["notification_id"]
                control_run_id = payload["control_run_id"]
                if not isinstance(notification_id, str) or not isinstance(control_run_id, str):
                    raise TypeError("invalid identity fields")
                captured = WitnessMessage(
                    notification_id=notification_id,
                    control_run_id=control_run_id,
                    topic=message.topic,
                    qos=message.qos,
                    payload_bytes=len(message.payload),
                    received_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                )
            except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
                with self._lock:
                    self._errors.append(f"invalid MQTT payload: {type(exc).__name__}")
                return
            with self._lock:
                self._messages.append(captured)

        client.on_connect = on_connect
        client.on_subscribe = on_subscribe
        client.on_message = on_message
        client.connect(self.host, self.port, keepalive=30)
        client.loop_start()
        self._client = client

    def wait_subscribed(self, timeout_s: float = 5.0) -> None:
        if not self._subscribed.wait(timeout_s):
            raise GateViolation("MQTT witness did not subscribe before timeout")
        if self._errors:
            raise GateViolation(self._errors[0])

    def wait_for_ids(self, expected: set[str], timeout_s: float = 5.0) -> None:
        observed: set[str] = set()
        deadline = time.monotonic() + timeout_s
        while True:
            with self._lock:
                observed = {message.notification_id for message in self._messages}
                errors = tuple(self._errors)
            if errors:
                raise GateViolation(errors[0])
            if expected.issubset(observed):
                return
            if time.monotonic() >= deadline:
                break
            time.sleep(0.01)
        missing = sorted(expected - observed)
        raise GateViolation(f"MQTT witness missing notification IDs: {missing}")

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            messages = tuple(self._messages)
            errors = tuple(self._errors)
        multiplicity = Counter(message.notification_id for message in messages)
        return {
            "messages": [message.__dict__ for message in messages],
            "multiplicity": dict(sorted(multiplicity.items())),
            "errors": list(errors),
        }

    def close(self) -> None:
        client, self._client = self._client, None
        if client is None:
            return
        client.disconnect()
        client.loop_stop()


class ManagedBroker:
    def __init__(self, process: subprocess.Popen[bytes], host: str, port: int) -> None:
        self.process = process
        self.host = host
        self.port = port

    @classmethod
    def start(
        cls,
        executable: Path,
        config_path: Path,
        *,
        host: str = "127.0.0.1",
        port: int = 1883,
        timeout_s: float = 5.0,
    ) -> ManagedBroker:
        if _port_open(host, port):
            raise GateViolation(f"broker port already occupied: {host}:{port}")
        process = subprocess.Popen(
            [str(executable), "-c", str(config_path)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        broker = cls(process, host, port)
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise GateViolation(f"aMQTT exited during startup with code {process.returncode}")
            if _port_open(host, port):
                return broker
            time.sleep(0.05)
        broker.close()
        raise GateViolation("aMQTT readiness timeout")

    def close(self) -> None:
        if self.process.poll() is not None:
            return
        self.process.terminate()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=5)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()


def _port_open(host: str, port: int) -> bool:
    with socket.socket() as probe:
        probe.settimeout(0.2)
        return probe.connect_ex((host, port)) == 0
