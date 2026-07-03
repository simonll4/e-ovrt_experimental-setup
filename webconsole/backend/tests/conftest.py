from __future__ import annotations

import socket
import threading
import time
from pathlib import Path

import httpx
import pytest
import uvicorn
from fastapi.testclient import TestClient

from eovrt_webconsole.app import create_app
from eovrt_webconsole.settings import ConsoleSettings
from tests.fake_service import FakeState, make_fake_service

PROMPT_SET_YAML = """\
prompt_set:
  id: demo_set
  description: "Set de prueba"
  language: en
  classes:
    - id: person
      role: entity
      phrasings: { default: ["person"] }
    - id: helmet
      role: ppe
      phrasings: { default: ["helmet"] }
"""

FROZEN_SET_YAML = """\
prompt_set:
  id: frozen_set
  description: "Congelado para BENCH"
  classes:
    - id: person
      phrasings: { default: ["person"] }
"""

MANIFEST_YAML = """\
run:
  scenario: DBE
  name: demo_manifest
source:
  ref: demo_v2
model:
  ref: grounding-dino/gdino-tiny
prompts:
  ref: demo_set
  active_ids: [person, helmet]
"""

BENCH_MANIFEST_YAML = """\
run:
  scenario: DBE
  name: bench_manifest
source:
  ref: bench_v2_test
rate_control:
  stride: 2
model:
  ref: yoloe/yoloe-26l
prompts:
  ref: frozen_set
  active_ids: [person]
outputs:
  save_annotated_video: true
"""


@pytest.fixture
def fake_state() -> FakeState:
    return FakeState()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    (tmp_path / "prompts").mkdir()
    (tmp_path / "experiments" / "bench_v2").mkdir(parents=True)
    (tmp_path / "prompts" / "demo_set.yaml").write_text(PROMPT_SET_YAML)
    (tmp_path / "prompts" / "frozen_set.yaml").write_text(FROZEN_SET_YAML)
    (tmp_path / "experiments" / "demo_manifest.yaml").write_text(MANIFEST_YAML)
    (tmp_path / "experiments" / "bench_v2" / "bench_manifest.yaml").write_text(BENCH_MANIFEST_YAML)
    return tmp_path


@pytest.fixture
def settings(repo: Path) -> ConsoleSettings:
    return ConsoleSettings(
        service_url="http://service.fake",
        repo_root=repo,
        frozen_set_ids=frozenset({"frozen_set"}),
    )


@pytest.fixture
def client(settings: ConsoleSettings, fake_state: FakeState):
    transport = httpx.ASGITransport(app=make_fake_service(fake_state))
    app = create_app(settings, service_transport=transport)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def live_client(repo: Path, fake_state: FakeState):
    """BFF (TestClient) apuntando a un fake service REAL en uvicorn (para WS)."""
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    config = uvicorn.Config(
        make_fake_service(fake_state), host="127.0.0.1", port=port, log_level="warning"
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 5.0
    while not server.started:
        if time.monotonic() > deadline:
            raise RuntimeError("El fake service no arrancó")
        time.sleep(0.02)
    settings = ConsoleSettings(
        service_url=f"http://127.0.0.1:{port}",
        repo_root=repo,
        frozen_set_ids=frozenset({"frozen_set"}),
    )
    with TestClient(create_app(settings)) as test_client:
        yield test_client
    server.should_exit = True
    thread.join(timeout=5)
