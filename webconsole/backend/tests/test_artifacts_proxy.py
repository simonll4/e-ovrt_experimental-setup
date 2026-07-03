def test_detections_proxy(client):
    r = client.get("/api/runs/run_done_1/detections", params={"page": 1, "page_size": 2})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 5 and len(body["items"]) == 2


def test_detections_404(client):
    assert client.get("/api/runs/nope/detections").status_code == 404


def test_artifact_pass_through(client):
    r = client.get("/api/runs/run_done_1/artifacts/summary.json")
    assert r.status_code == 200
    assert r.content == b'{"status": "succeeded"}'
    assert r.headers.get("accept-ranges") == "bytes"


def test_artifact_anidado_y_404(client):
    assert client.get("/api/runs/run_done_1/artifacts/previews/u0.preview.jpg").status_code == 200
    assert client.get("/api/runs/run_done_1/artifacts/nope.bin").status_code == 404
