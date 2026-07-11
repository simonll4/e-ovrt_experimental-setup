"""Gate spec 44 B (Tarea 5): flujo completo dos-planos a traves del BFF.

Ejercita, con TestClient + `two_plane_client` (fakes de media-plane y
control-plane), la secuencia completa que describe spec 44 SS5.1:

1. POST /api/experiments/manifests crea un manifiesto paraguas (via la ruta
   HTTP real, no escribiendo el YAML a mano como hacen los tests unitarios
   de las tareas 2-4).
2. POST /api/experiments/run lo dispara -> 202.
3. Polling de GET /api/experiments/{id} hasta un estado terminal.
4. GET /api/experiments/{id}/alerts proxya las alertas del control fake.
5. GET /api/experiments/{id}/report lee el reporte consolidado.
6. Un segundo POST /api/experiments/run mientras hay uno activo -> 409.

Nota sobre el paso 5 (reporte): en este entorno de test, `_default_dest_root()`
(runner.py) resuelve el dest_root de la consolidacion contra el repo real via
`__file__`, no contra `settings.repo_root` (tmp_path del fixture `repo`) -- el
mismo gap que ya documenta `test_experiment_alerts_report.py`
(`_seed_manager_state_con_consolidated_dir`). Una corrida orquestada real en
este entorno por lo tanto NUNCA deja `consolidated_dir` seteado en el estado
del manager, y GET /report da 404 despues de que el experimento termina en
succeeded. Se elige el camino deterministico documentado por esa tarea: el
gate primero confirma ese 404 (el estado real, sin adornar) y despues siembra
`consolidated_dir` a mano en el manager -- mismo atajo que la Tarea 4 -- para
ejercitar el camino feliz de la ruta con un report.json real."""
from __future__ import annotations

import json
from pathlib import Path

import yaml

VALID_UMBRELLA = {
    "schema_version": "experiment.manifest.v1",
    "slug": "gate_orq",
    "sequencing": "media_first",
}

MEDIA_CONFIG = {"ingest": {"type": "image_folder", "path": "demo"}, "prompts": {"ref": "demo_set"}}
CONTROL_CONFIG = {"pattern_set": "cr01_cr02_v2"}


def _write_referenced_configs(repo: Path, *, slug: str) -> tuple[Path, Path]:
    """Escribe los YAML de config de media/control que referencia el manifiesto
    paraguas (no son manifiestos en si, el runner los carga con
    Path(config).read_text() sin resolver contra ningun directorio base, por
    eso rutas absolutas)."""
    media_path = repo / "experiments" / f"{slug}_media.yaml"
    control_path = repo / "experiments" / f"{slug}_control.yaml"
    media_path.write_text(yaml.safe_dump(MEDIA_CONFIG))
    control_path.write_text(yaml.safe_dump(CONTROL_CONFIG))
    return media_path, control_path


def _umbrella_manifest_body(repo: Path, *, slug: str, sequencing: str = "media_first") -> dict:
    media_path, control_path = _write_referenced_configs(repo, slug=slug)
    body = dict(VALID_UMBRELLA)
    body["slug"] = slug
    body["sequencing"] = sequencing
    body["runs"] = {
        "media": {"service": "media-plane", "config": str(media_path), "mode": "run"},
        "control": {"service": "control-plane", "config": str(control_path), "mode": "replay"},
    }
    return body


def _make_media_status_terminal(client, *, status: str = "succeeded") -> None:
    """El fake media-plane (tests/fake_service.py, no editable) nunca transiciona
    un run recien lanzado a un estado terminal por si solo. Se monkeypatchea
    status() del RunBackend real ya cableado en app.state -- mismo patron que
    test_experiment_orchestration.py / test_experiment_alerts_report.py."""

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


def _seed_manager_state_con_consolidated_dir(client, experiment_id: str, consolidated_dir: Path):
    """Mismo atajo que test_experiment_alerts_report.py: siembra el estado
    terminado del manager a mano para ejercitar el camino feliz de /report sin
    depender de que la consolidacion real corra en este entorno de test."""
    state = dict(client.app.state.experiment_manager._states[experiment_id])
    state["consolidated_dir"] = str(consolidated_dir)
    client.app.state.experiment_manager._states[experiment_id] = state


def _write_report(dest_root: Path, experiment_id: str, report: dict) -> Path:
    report_dir = dest_root / experiment_id / "report"
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / "report.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    return path


def test_gate_flujo_completo_por_bff(two_plane_client, repo, settings, control_state):
    client = two_plane_client

    # --- 1. POST /api/experiments/manifests crea el manifiesto paraguas -----
    manifest_body = _umbrella_manifest_body(repo, slug="gate_orq")
    r_manifest = client.post("/api/experiments/manifests", json=manifest_body)
    assert r_manifest.status_code == 201
    assert r_manifest.json() == {"slug": "gate_orq"}
    assert (repo / "experiments" / "gate_orq.yaml").exists()

    r_get_manifest = client.get("/api/experiments/manifests/gate_orq")
    assert r_get_manifest.status_code == 200
    assert r_get_manifest.json()["sequencing"] == "media_first"

    # --- 2. Se siembran los fakes para que la corrida termine deterministica -
    _make_media_status_terminal(client)
    control_state.finish_status = "succeeded"

    # --- 3. POST /api/experiments/run dispara el experimento -> 202 ---------
    r_run = client.post("/api/experiments/run", json={"slug": "gate_orq"})
    assert r_run.status_code == 202
    experiment_id = r_run.json()["experiment_id"]
    assert experiment_id

    # --- 4. Polling de GET /api/experiments/{id} hasta un estado terminal ---
    body = _poll_experiment(client, experiment_id)
    assert body["status"] == "succeeded"
    assert body["ok"] is True
    assert body["media_run_id"]
    assert body["control_run_id"]
    assert body["media_status"] == "succeeded"
    assert body["control_status"] == "succeeded"

    # --- 5. GET /api/experiments/{id}/alerts proxya el control fake ---------
    control_run_id = body["control_run_id"]
    seeded_alerts = [
        {"alert_id": "al-gate-1", "pattern_id": "cr01", "confirmed_at_ms": 4321.0}
    ]
    control_state.alerts[control_run_id] = seeded_alerts

    r_alerts = client.get(f"/api/experiments/{experiment_id}/alerts")
    assert r_alerts.status_code == 200
    assert r_alerts.json() == seeded_alerts

    # --- 6. GET /api/experiments/{id}/report lee el reporte consolidado -----
    # Primero, el estado real de este entorno de test: la consolidacion
    # orquestada no corrio (ver docstring del modulo), no hay report.json
    # resoluble todavia -> 404.
    r_report_sin_consolidar = client.get(f"/api/experiments/{experiment_id}/report")
    assert r_report_sin_consolidar.status_code == 404

    # Se siembra el consolidado (mismo atajo documentado por la Tarea 4) para
    # ejercitar el camino feliz: report.json real, non_temporal calculado.
    consolidated_dir = settings.repo_root / "runs" / "gate_consolidado"
    report = {
        "identificacion": {"experiment_id": experiment_id},
        "temporalidad": {"source_clock": "media"},
        "resultados": [
            {
                "name": "t_capture->alert",
                "unit": "ms",
                "status": "not_interpretable",
                "cause": "dbe_media_time",
            }
        ],
    }
    _write_report(settings.repo_root / "runs", "gate_consolidado", report)
    _seed_manager_state_con_consolidated_dir(client, experiment_id, consolidated_dir)

    r_report = client.get(f"/api/experiments/{experiment_id}/report")
    assert r_report.status_code == 200
    report_body = r_report.json()
    assert report_body["identificacion"]["experiment_id"] == experiment_id
    assert report_body["non_temporal"] is False


def test_gate_segundo_run_mientras_hay_uno_activo_409(
    two_plane_client, repo, control_state, fake_state
):
    client = two_plane_client

    manifest_1 = _umbrella_manifest_body(repo, slug="gate_busy_1")
    manifest_2 = _umbrella_manifest_body(repo, slug="gate_busy_2")
    assert client.post("/api/experiments/manifests", json=manifest_1).status_code == 201
    assert client.post("/api/experiments/manifests", json=manifest_2).status_code == 201

    # No se resuelve el status a terminal: el primer experimento queda
    # "running" -- el slot sigue ocupado cuando llega el segundo POST /run.
    fake_state.reject_launch = False

    r1 = client.post("/api/experiments/run", json={"slug": "gate_busy_1"})
    assert r1.status_code == 202
    experiment_id_1 = r1.json()["experiment_id"]

    r2 = client.post("/api/experiments/run", json={"slug": "gate_busy_2"})
    assert r2.status_code == 409
    body = r2.json()
    assert body["active_experiment_id"] == experiment_id_1
