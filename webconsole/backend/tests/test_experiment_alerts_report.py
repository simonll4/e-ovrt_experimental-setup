"""Vista de alertas (proxy control-plane) + lectura del reporte consolidado
(Spec 44 B, Tarea 4)."""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from eovrt_webconsole.experiment.control_backend import ServiceUnavailable

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
    """Igual que en test_experiment_orchestration.py: manifiesto paraguas + sus
    dos configs referenciadas, con rutas absolutas."""
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
    un run recien lanzado a un estado terminal por si solo; se monkeypatchea
    status() del RunBackend real ya cableado en app.state (mismo patron que
    test_experiment_orchestration.py)."""

    async def fake_status(run_id: str) -> dict:
        return {
            "run_id": run_id,
            "status": status,
            "summary": {"detections_path": f"runs/{run_id}/detections.jsonl"},
        }

    client.app.state.backend.status = fake_status


def _run_experiment_to_terminal(client, repo, control_state, *, slug: str) -> dict:
    _write_umbrella_manifest(repo, slug=slug)
    _make_media_status_terminal(client)
    control_state.finish_status = "succeeded"

    r = client.post("/api/experiments/run", json={"slug": slug})
    assert r.status_code == 202
    experiment_id = r.json()["experiment_id"]

    for _ in range(200):
        body = client.get(f"/api/experiments/{experiment_id}").json()
        if body["status"] in ("succeeded", "failed"):
            return body
    raise AssertionError(f"experimento {experiment_id} nunca llego a un estado terminal")


# ---------------------------------------------------------------------------
# GET /api/experiments/{experiment_id}/alerts
# ---------------------------------------------------------------------------


def test_alerts_200_proxya_las_del_control_fake(two_plane_client, repo, control_state):
    body = _run_experiment_to_terminal(two_plane_client, repo, control_state, slug="orq_alerts")
    assert body["status"] == "succeeded"
    control_run_id = body["control_run_id"]
    assert control_run_id

    # Se siembra DESPUES de terminar la corrida: el fake lee state.alerts en vivo
    # en cada GET, asi que mutar el dict ahora alcanza.
    seeded = [{"alert_id": "al-1", "pattern_id": "cr01", "confirmed_at_ms": 1234.0}]
    control_state.alerts[control_run_id] = seeded

    r = two_plane_client.get(f"/api/experiments/{body['experiment_id']}/alerts")
    assert r.status_code == 200
    assert r.json() == seeded


def test_alerts_404_experimento_desconocido(two_plane_client):
    r = two_plane_client.get("/api/experiments/no_existe/alerts")
    assert r.status_code == 404


def test_alerts_404_sin_control_run_id(two_plane_client, repo, fake_state, control_state):
    """Si el media falla, el runner nunca dispara el control-plane: el resultado
    queda con control_run_id=None. La ruta de alertas debe dar 404 (no intentar
    proxyar con None)."""
    _write_umbrella_manifest(repo, slug="orq_media_fail")
    fake_state.reject_launch = True

    r = two_plane_client.post("/api/experiments/run", json={"slug": "orq_media_fail"})
    assert r.status_code == 202
    experiment_id = r.json()["experiment_id"]

    for _ in range(200):
        body = two_plane_client.get(f"/api/experiments/{experiment_id}").json()
        if body["status"] in ("succeeded", "failed"):
            break
    else:
        raise AssertionError("experimento nunca llego a un estado terminal")

    r_alerts = two_plane_client.get(f"/api/experiments/{experiment_id}/alerts")
    assert r_alerts.status_code == 404


def test_alerts_502_service_unavailable(two_plane_client, repo, control_state):
    body = _run_experiment_to_terminal(
        two_plane_client, repo, control_state, slug="orq_alerts_502"
    )
    assert body["status"] == "succeeded"

    async def boom(control_run_id: str):
        raise ServiceUnavailable("control-plane caido")

    two_plane_client.app.state.control_backend.alerts = boom

    r = two_plane_client.get(f"/api/experiments/{body['experiment_id']}/alerts")
    assert r.status_code == 502


# ---------------------------------------------------------------------------
# GET /api/experiments/{experiment_id}/report
# ---------------------------------------------------------------------------


def _write_report(dest_root: Path, experiment_id: str, report: dict) -> Path:
    report_dir = dest_root / experiment_id / "report"
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / "report.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    return path


def _base_report(experiment_id: str, source_clock: str) -> dict:
    return {
        "identificacion": {"experiment_id": experiment_id},
        "temporalidad": {"source_clock": source_clock},
        "resultados": [
            {
                "name": "t_capture->alert",
                "unit": "ms",
                "status": "not_applicable" if source_clock == "none" else "not_interpretable",
                "cause": "non_temporal_source" if source_clock == "none" else "dbe_media_time",
            }
        ],
    }


def test_report_200_source_clock_none_marca_non_temporal(two_plane_client, settings):
    experiment_id = "exp_images_synth"
    report = _base_report(experiment_id, "none")
    _write_report(settings.repo_root / "runs", experiment_id, report)

    r = two_plane_client.get(f"/api/experiments/{experiment_id}/report")
    assert r.status_code == 200
    body = r.json()
    assert body["identificacion"]["experiment_id"] == experiment_id
    assert body["non_temporal"] is True


def test_report_200_source_clock_media_no_marca_non_temporal(two_plane_client, settings):
    experiment_id = "exp_video_synth"
    report = _base_report(experiment_id, "media")
    _write_report(settings.repo_root / "runs", experiment_id, report)

    r = two_plane_client.get(f"/api/experiments/{experiment_id}/report")
    assert r.status_code == 200
    body = r.json()
    assert body["non_temporal"] is False


def test_report_404_experimento_sin_consolidado(two_plane_client):
    r = two_plane_client.get("/api/experiments/no_existe/report")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Path traversal (hallazgo de seguridad, revision de Tarea 4): experiment_id
# es input crudo de cliente y _resolve_consolidated_dir lo usaba para armar
# un path de filesystem sin validar. ".." percent-encoded (%2e%2e) llega
# decodificado al handler (el server ASGI decodifica antes de que Starlette
# matchee la ruta), asi que GET /api/experiments/%2e%2e/report resolvia a
# <repo_root>/runs/.. == <repo_root> y servia <repo_root>/report/report.json,
# un nivel afuera de runs/.
# ---------------------------------------------------------------------------


def _plant_marker_outside_runs(settings) -> None:
    """Siembra el mismo fixture que uso la revision para confirmar el hueco:
    un report.json 'marcador' un nivel afuera de runs/ (en repo_root
    directo), con runs/ vacio. Si alguna corrida hostil de experiment_id
    consigue leer este marcador, la contencion no esta funcionando."""
    marker_dir = settings.repo_root / "report"
    marker_dir.mkdir(parents=True, exist_ok=True)
    (marker_dir / "report.json").write_text(
        json.dumps({"marker": "OUTSIDE_RUNS_ROOT"}), encoding="utf-8"
    )
    (settings.repo_root / "runs").mkdir(parents=True, exist_ok=True)


def test_report_traversal_percent_encoded_dotdot_no_escapa_runs(two_plane_client, settings):
    _plant_marker_outside_runs(settings)

    r = two_plane_client.get("/api/experiments/%2e%2e/report")

    assert r.status_code != 200
    assert r.status_code == 404
    assert "OUTSIDE_RUNS_ROOT" not in r.text


def test_report_traversal_mixto_encoded_no_escapa_runs(two_plane_client, settings):
    """foo%2f..%2fbar/report: no discriminante contra el fix (Starlette ya
    rechaza el "/" decodificado dentro del segmento {experiment_id} y da 404
    generico ANTES de que el handler corra, con o sin el guard), pero queda
    como regresion: si algun dia el matcher de ruta cambiara a un converter
    tipo "path", _is_safe_experiment_id lo seguiria bloqueando."""
    _plant_marker_outside_runs(settings)

    r = two_plane_client.get("/api/experiments/foo%2f..%2fbar/report")

    assert r.status_code != 200
    assert "OUTSIDE_RUNS_ROOT" not in r.text


def test_is_safe_experiment_id_rechaza_ids_hostiles():
    """Unit test directo de la guarda de formato. No se prueba ".." literal
    vía HTTP porque httpx normaliza los dot-segments del lado cliente antes
    de mandar la request (RFC 3986): "/api/experiments/.." nunca le llega al
    handler como experiment_id="..", asi que un test HTTP con ese path no
    ejercitaria el codigo del guard. Se prueba la funcion directo."""
    from eovrt_webconsole.routers.experiments import _is_safe_experiment_id

    for hostile in ("..", "", ".", "foo/bar", "foo\\bar", "...", ".hidden", "a/../b"):
        assert _is_safe_experiment_id(hostile) is False, hostile

    for safe in ("no_existe", "exp_images_synth", "exp_20260711T000000Z_smoke", "orq_1"):
        assert _is_safe_experiment_id(safe) is True, safe


# ---------------------------------------------------------------------------
# Rama resuelta por el manager (gap MEDIUM senalado por la revision): cuando
# el manager tiene consolidated_dir en el estado (post-run exitoso) la ruta
# debe leer de ahi, no de la convencion <repo_root>/runs/<experiment_id>.
# ---------------------------------------------------------------------------


def _seed_manager_state_con_consolidated_dir(client, experiment_id: str, consolidated_dir: Path):
    """Siembra directo el estado terminado en el manager, en vez de correr la
    orquestacion completa: en este entorno de test _default_dest_root() (en
    runner.py) resuelve al repo real via __file__, no al settings.repo_root
    de tmp_path, asi que la consolidacion real de un run orquestado falla
    (paths de los planos hermanos no existen) y consolidated_dir queda en
    None -- nunca ejercita esta rama. Sembrar el estado a mano es el atajo
    que documenta la Tarea 4 para cubrir la rama de produccion."""
    client.app.state.experiment_manager._states[experiment_id] = {
        "experiment_id": experiment_id,
        "status": "succeeded",
        "consolidated_dir": str(consolidated_dir),
    }


def test_report_200_lee_del_consolidated_dir_del_manager_no_de_la_convencion(
    two_plane_client, settings
):
    experiment_id = "exp_seeded_manager"
    manager_dir = settings.repo_root / "runs" / "otro_dir_no_convencional"
    report = _base_report(experiment_id, "media")
    _write_report(settings.repo_root / "runs", "otro_dir_no_convencional", report)
    # Nada en la ruta por convencion (<repo_root>/runs/<experiment_id>): si la
    # ruta cayera ahi en vez de al consolidated_dir sembrado, esto daria 404.
    assert not (settings.repo_root / "runs" / experiment_id / "report" / "report.json").exists()

    _seed_manager_state_con_consolidated_dir(two_plane_client, experiment_id, manager_dir)

    r = two_plane_client.get(f"/api/experiments/{experiment_id}/report")
    assert r.status_code == 200
    body = r.json()
    assert body["identificacion"]["experiment_id"] == experiment_id
    assert body["non_temporal"] is False
