"""ExperimentRunManager + rutas de disparo orquestado (Tarea 3, spec 44 B)."""
from __future__ import annotations

import yaml

VALID_UMBRELLA = {
    "schema_version": "experiment.manifest.v1",
    "slug": "orq_1",
    "runs": {
        "media": {"service": "media-plane", "config": "media.yaml", "mode": "run"},
        "control": {"service": "control-plane", "config": "control.yaml", "mode": "replay"},
    },
    "sequencing": "media_first",
}

MEDIA_CONFIG = {"ingest": {"type": "image_folder", "path": "demo"}, "prompts": {"ref": "demo_set"}}
CONTROL_CONFIG = {"pattern_set": "cr01_cr02_v2"}


def _write_umbrella_manifest(repo, *, slug: str) -> None:
    """Escribe el manifiesto paraguas + sus dos configs referenciadas, con rutas
    absolutas (el loader por defecto del runner hace Path(config).read_text() tal
    cual, sin resolver contra ningun directorio base)."""
    media_path = repo / "experiments" / f"{slug}_media.yaml"
    control_path = repo / "experiments" / f"{slug}_control.yaml"
    media_path.write_text(yaml.safe_dump(MEDIA_CONFIG))
    control_path.write_text(yaml.safe_dump(CONTROL_CONFIG))

    manifest = dict(VALID_UMBRELLA)
    manifest["slug"] = slug
    manifest["runs"] = {
        "media": {"service": "media-plane", "config": str(media_path), "mode": "run"},
        "control": {"service": "control-plane", "config": str(control_path), "mode": "replay"},
    }
    (repo / "experiments" / f"{slug}.yaml").write_text(yaml.safe_dump(manifest, sort_keys=False))


def _make_media_status_terminal(client, *, status: str = "succeeded") -> None:
    """El fake media-plane (tests/fake_service.py, no editable) nunca transiciona
    un run recien lanzado a un estado terminal por si solo (siempre 'running'
    mientras sea el run activo). Igual que en test_runner_dbe_replay.py /
    test_runner_live.py, se monkeypatchea el metodo status() del RunBackend real
    ya cableado en app.state (mismo patron que test_runs_router.py con
    monkeypatch.setattr(client.app.state.backend, "status", ...))."""

    async def fake_status(run_id: str) -> dict:
        return {
            "run_id": run_id,
            "status": status,
            "summary": {"detections_path": f"runs/{run_id}/detections.jsonl"},
        }

    client.app.state.backend.status = fake_status


def _poll_experiment(client, experiment_id: str, *, max_iters: int = 200) -> dict:
    for _ in range(max_iters):
        r = client.get(f"/api/experiments/{experiment_id}")
        assert r.status_code == 200
        body = r.json()
        if body["status"] in ("succeeded", "failed"):
            return body
    raise AssertionError(f"experimento {experiment_id} nunca llego a un estado terminal")


def test_run_202_y_polling_hasta_succeeded(two_plane_client, repo, control_state):
    _write_umbrella_manifest(repo, slug="orq_1")
    _make_media_status_terminal(two_plane_client)
    control_state.finish_status = "succeeded"

    r = two_plane_client.post("/api/experiments/run", json={"slug": "orq_1"})
    assert r.status_code == 202
    experiment_id = r.json()["experiment_id"]
    assert experiment_id

    body = _poll_experiment(two_plane_client, experiment_id)
    assert body["status"] == "succeeded"
    assert body["ok"] is True
    assert body["media_run_id"]
    assert body["control_run_id"]
    assert body["media_status"] == "succeeded"
    assert body["control_status"] == "succeeded"


def test_run_409_mientras_hay_uno_activo(two_plane_client, repo, control_state, fake_state):
    _write_umbrella_manifest(repo, slug="orq_busy")
    # No se resuelve el status a terminal: el primer experimento queda "running".
    fake_state.reject_launch = False

    r1 = two_plane_client.post("/api/experiments/run", json={"slug": "orq_busy"})
    assert r1.status_code == 202

    r2 = two_plane_client.post("/api/experiments/run", json={"slug": "orq_busy"})
    assert r2.status_code == 409
    body = r2.json()
    assert body["active_experiment_id"] == r1.json()["experiment_id"]


def test_slot_se_libera_tras_crash_en_background_task(
    two_plane_client, repo, control_state, fake_state
):
    """Regresion critica (guardia mas importante de la Tarea 3): si el task de
    background de run_experiment revienta con una excepcion real -- no un
    ExperimentResult con ok=False, sino la corrutina propagando una excepcion --
    _on_done debe (1) registrar el experimento como 'failed' en vez de tragarse
    la excepcion, y (2) liberar `_active_id` para que el manager no quede
    wedeado despues de una corrida rota.

    El crash se fuerza con fake_state.reject_launch=True: el fake media-plane
    devuelve 422 en POST /api/runs, y RunBackend.launch() lo traduce a
    ServiceRejected (tests/fake_service.py, src/eovrt_webconsole/routers/
    run_backend.py -- ninguno de los dos se edita aca). Como el manifiesto es
    media_first (runs.control.mode == 'replay'), esa es la primera llamada HTTP
    de run_experiment: la excepcion se propaga sin catch hasta el asyncio.Task,
    exactamente el camino que _on_done tiene que cubrir con
    `task.exception()`."""
    _write_umbrella_manifest(repo, slug="orq_crash")
    fake_state.reject_launch = True

    r1 = two_plane_client.post("/api/experiments/run", json={"slug": "orq_crash"})
    assert r1.status_code == 202
    experiment_id = r1.json()["experiment_id"]

    body = _poll_experiment(two_plane_client, experiment_id)
    assert body["status"] == "failed"
    assert "error" in body

    # El slot debe estar libre: un segundo POST /run (slug distinto, para no
    # depender de que `now` avance de segundo) debe aceptarse con 202, no 409.
    # Si _on_done no liberara `_active_id` en el done-callback, este POST
    # devolveria 409 para siempre y el manager quedaria wedeado.
    _write_umbrella_manifest(repo, slug="orq_after_crash")
    fake_state.reject_launch = False
    r2 = two_plane_client.post("/api/experiments/run", json={"slug": "orq_after_crash"})
    assert r2.status_code == 202
    assert r2.json()["experiment_id"] != experiment_id


def test_slot_se_libera_tras_completar(two_plane_client, repo, control_state):
    _write_umbrella_manifest(repo, slug="orq_2a")
    _write_umbrella_manifest(repo, slug="orq_2b")
    _make_media_status_terminal(two_plane_client)
    control_state.finish_status = "succeeded"

    r1 = two_plane_client.post("/api/experiments/run", json={"slug": "orq_2a"})
    assert r1.status_code == 202
    _poll_experiment(two_plane_client, r1.json()["experiment_id"])

    # el slot debe estar libre: un segundo POST /run (slug distinto, para no
    # depender de que `now` avance de segundo) debe aceptarse con 202, no 409.
    r2 = two_plane_client.post("/api/experiments/run", json={"slug": "orq_2b"})
    assert r2.status_code == 202
    assert r2.json()["experiment_id"] != r1.json()["experiment_id"]


def test_run_slug_desconocido_422(two_plane_client):
    r = two_plane_client.post("/api/experiments/run", json={"slug": "no_existe"})
    assert r.status_code == 422


def test_current_404_sin_activo(two_plane_client):
    r = two_plane_client.get("/api/experiments/current")
    assert r.status_code == 404


def test_current_200_mientras_corre(two_plane_client, repo, control_state, fake_state):
    _write_umbrella_manifest(repo, slug="orq_3")
    # No se fuerza terminal: el experimento queda "running" el tiempo suficiente
    # para observar /current en ese estado.

    r = two_plane_client.post("/api/experiments/run", json={"slug": "orq_3"})
    experiment_id = r.json()["experiment_id"]

    r_current = two_plane_client.get("/api/experiments/current")
    assert r_current.status_code == 200
    assert r_current.json()["experiment_id"] == experiment_id
    assert r_current.json()["status"] == "running"


def test_get_experiment_id_desconocido_404(two_plane_client):
    r = two_plane_client.get("/api/experiments/no_such_experiment")
    assert r.status_code == 404


def test_manifests_route_no_es_shadowed_por_experiment_id(two_plane_client):
    """GET /api/experiments/manifests debe seguir siendo el listado (Tarea 2),
    no ser capturado como si "manifests" fuera un experiment_id."""
    r = two_plane_client.get("/api/experiments/manifests")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
