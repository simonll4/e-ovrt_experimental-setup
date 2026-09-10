"""Compatibilidad con el servicio real anterior al endpoint de inventario."""
import httpx
import pytest

from eovrt_webconsole.run_backend import RunBackend, ServiceUnavailable, UnknownRun


@pytest.mark.parametrize("index_status", [404, 307, 308])
async def test_legacy_index_probes_only_existing_standard_files(index_status):
    calls = []

    def respond(request):
        calls.append(request)
        path = request.url.path
        if path == "/api/runs/r/artifacts":
            return httpx.Response(index_status, headers={"location": "http://other.invalid/"})
        if path == "/api/runs/r":
            return httpx.Response(200, json={"run_id": "r", "status": "succeeded"})
        assert request.headers["range"] == "bytes=0-0"
        if path.endswith("/summary.json"):
            return httpx.Response(206, content=b"{", headers={"content-range": "bytes 0-0/123"})
        if path.endswith("/errors.jsonl"):
            return httpx.Response(416, headers={"content-range": "bytes */0"})
        return httpx.Response(404)

    async with httpx.AsyncClient(base_url="http://media", transport=httpx.MockTransport(respond)) as http:
        result = await RunBackend(http).list_artifacts("r")
    assert result["complete"] is False
    assert result["notice"]
    assert {i["name"]: i["size_bytes"] for i in result["items"]} == {
        "summary.json": 123, "errors.jsonl": 0,
    }
    assert all(request.url.host == "media" for request in calls)


async def test_missing_run_still_returns_unknown():
    async with httpx.AsyncClient(base_url="http://media", transport=httpx.MockTransport(
        lambda request: httpx.Response(404),
    )) as http:
        with pytest.raises(UnknownRun):
            await RunBackend(http).list_artifacts("missing")


async def test_index_outage_is_not_an_empty_inventory():
    async with httpx.AsyncClient(base_url="http://media", transport=httpx.MockTransport(
        lambda request: httpx.Response(503),
    )) as http:
        with pytest.raises(ServiceUnavailable):
            await RunBackend(http).list_artifacts("r")


async def test_partial_response_without_total_does_not_invent_file_size():
    def respond(request):
        if request.url.path == "/api/runs/r/artifacts":
            return httpx.Response(404)
        if request.url.path == "/api/runs/r":
            return httpx.Response(200, json={"status": "succeeded"})
        return httpx.Response(206, content=b"x", headers={"content-range": "bytes 0-0/*"})

    async with httpx.AsyncClient(base_url="http://media", transport=httpx.MockTransport(respond)) as http:
        with pytest.raises(ServiceUnavailable, match="tamaño no disponible"):
            await RunBackend(http).list_artifacts("r")
