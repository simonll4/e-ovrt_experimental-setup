"""La salud permanente del distribuidor informa sin cambiar el gate de lanzamiento."""
import httpx
import pytest
from fastapi.testclient import TestClient

from eovrt_webconsole.app import create_app


@pytest.mark.parametrize(
    ("health", "ready", "expected"),
    [(200, 200, (True, True)), (200, 503, (True, False)),
     (503, 503, (False, False)), (None, None, (False, False))],
)
def test_distribution_health_is_informational(settings, health, ready, expected):
    requests = []

    def distribution(request):
        requests.append(request.url.path)
        if health is None:
            raise httpx.ConnectError("distribuidor apagado", request=request)
        return httpx.Response(health if request.url.path == "/healthz" else ready)

    def operational(request):
        return httpx.Response(200, json={})

    app = create_app(
        settings,
        service_transport=httpx.MockTransport(operational),
        control_transport=httpx.MockTransport(operational),
        distribution_transport=httpx.MockTransport(distribution),
    )
    with TestClient(app) as client:
        distribution_http = app.state.distribution_http
        assert not distribution_http.is_closed
        for _ in range(2):
            response = client.get("/api/preflight")
            assert response.status_code == 200
            body = response.json()
            assert body["distribution"] == {
                "service_url": settings.distribution_service_url,
                "healthy": expected[0],
                "ready": expected[1],
            }
            assert body["ready"] is True
            assert body["blockers"] == []
            assert app.state.distribution_http is distribution_http
        assert requests.count("/healthz") == 2
        assert requests.count("/readyz") == (0 if health is None else 2)
    assert distribution_http.is_closed


def test_healthy_distribution_does_not_remove_control_blocker(settings):
    app = create_app(
        settings,
        service_transport=httpx.MockTransport(lambda request: httpx.Response(200, json={})),
        control_transport=httpx.MockTransport(lambda request: httpx.Response(503)),
        distribution_transport=httpx.MockTransport(lambda request: httpx.Response(200)),
    )
    with TestClient(app) as client:
        body = client.get("/api/preflight").json()
        assert body["distribution"]["healthy"] is True
        assert body["ready"] is False
        assert body["blockers"] == ["el control-plane no responde"]
