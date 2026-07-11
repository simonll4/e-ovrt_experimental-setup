"""Task 1 (spec 44b): segundo backend (control-plane :8081) cableado en el BFF."""
from __future__ import annotations

import httpx
from fastapi.testclient import TestClient

from eovrt_webconsole.app import create_app
from eovrt_webconsole.experiment.control_backend import ControlPlaneBackend
from eovrt_webconsole.run_backend import RunBackend
from eovrt_webconsole.settings import ConsoleSettings
from tests.fake_control_service import FakeControlState, make_fake_control_service
from tests.fake_service import FakeState, make_fake_service


def test_control_backend_wired_alongside_media_backend(
    settings: ConsoleSettings, fake_state: FakeState, control_state: FakeControlState
):
    """Ambos planos quedan en app.state tras el lifespan: media (viejo) + control (nuevo)."""
    service_transport = httpx.ASGITransport(app=make_fake_service(fake_state))
    control_transport = httpx.ASGITransport(app=make_fake_control_service(control_state))
    app = create_app(
        settings, service_transport=service_transport, control_transport=control_transport
    )
    with TestClient(app) as client:
        assert isinstance(client.app.state.control_backend, ControlPlaneBackend)
        assert isinstance(client.app.state.backend, RunBackend)


def test_two_plane_client_fixture_serves_both_planes(two_plane_client):
    """El fixture two_plane_client expone ambos backends operativos (media + control)."""
    assert isinstance(two_plane_client.app.state.control_backend, ControlPlaneBackend)
    assert isinstance(two_plane_client.app.state.backend, RunBackend)
