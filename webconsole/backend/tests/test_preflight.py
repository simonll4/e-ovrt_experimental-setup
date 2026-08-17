"""GET /api/preflight (estado agregado de ambos planos) + gate 503 en
POST /api/experiments/run cuando la plataforma no está lista."""
from __future__ import annotations

import yaml


def _write_umbrella_manifest(repo, *, slug: str) -> None:
    """Mismo patron que test_experiment_orchestration.py: manifiesto paraguas con
    configs referenciadas por ruta absoluta."""
    media_path = repo / "experiments" / f"{slug}_media.yaml"
    control_path = repo / "experiments" / f"{slug}_control.yaml"
    media_path.write_text(yaml.safe_dump({"ingest": {"type": "image_folder", "path": "demo"}}))
    control_path.write_text(yaml.safe_dump({"pattern_set": "cr01_cr02_v2"}))
    manifest = {
        "schema_version": "experiment.manifest.v1",
        "slug": slug,
        "sequencing": "media_first",
        "runs": {
            "media": {"service": "media-plane", "config": str(media_path), "mode": "run"},
            "control": {"service": "control-plane", "config": str(control_path), "mode": "replay"},
        },
    }
    (repo / "experiments" / f"{slug}.yaml").write_text(yaml.safe_dump(manifest, sort_keys=False))


def _write_distribution_manifest(
    repo,
    *,
    slug: str,
    distribution_channel_mode: str = "live",
    distribution_mode: str = "replay",
    broker_host: str = "127.0.0.1",
    broker_port: int = 1883,
) -> None:
    """Escribe un manifiesto con runs.media, runs.control y runs.distribution."""
    media_path = repo / "experiments" / f"{slug}_media.yaml"
    control_path = repo / "experiments" / f"{slug}_control.yaml"
    distribution_path = repo / "experiments" / f"{slug}_distribution.yaml"
    media_path.write_text(yaml.safe_dump({"ingest": {"type": "image_folder", "path": "demo"}}))
    control_path.write_text(yaml.safe_dump({"pattern_set": "cr01_cr02_v2"}))
    distribution_config = {
        "notification_policy": {"cooldown_ms": 30000},
        "channel": {
            "mode": distribution_channel_mode,
            "host": broker_host,
            "port": broker_port,
            "topic_prefix": "eovrt/alerts",
            "qos": 1,
        },
    }
    distribution_path.write_text(yaml.safe_dump(distribution_config))

    manifest = {
        "schema_version": "experiment.manifest.v1",
        "slug": slug,
        "runs": {
            "media": {"service": "media-plane", "config": str(media_path), "mode": "run"},
            "control": {
                "service": "control-plane",
                "config": str(control_path),
                "mode": "replay",
            },
            "distribution": {
                "service": "distribution",
                "config": str(distribution_path),
                "mode": distribution_mode,
            },
        },
        "sequencing": "media_first",
    }
    (repo / "experiments" / f"{slug}.yaml").write_text(yaml.safe_dump(manifest, sort_keys=False))


def test_preflight_todo_verde(two_plane_client):
    body = two_plane_client.get("/api/preflight").json()
    assert body["ready"] is True
    assert body["blockers"] == []
    assert body["media"]["healthy"] and body["media"]["ready"]
    assert body["media"]["model"] is not None
    assert body["control"]["healthy"] and body["control"]["ready"]


def test_preflight_control_no_listo(two_plane_client, control_state):
    control_state.ready = False
    body = two_plane_client.get("/api/preflight").json()
    assert body["ready"] is False
    assert body["control"]["healthy"] is True
    assert body["control"]["ready"] is False
    assert any("control-plane" in b for b in body["blockers"])


def test_preflight_media_no_listo(two_plane_client, fake_state):
    fake_state.ready = False
    body = two_plane_client.get("/api/preflight").json()
    assert body["ready"] is False
    assert body["media"]["ready"] is False
    assert body["media"]["model"] is None
    assert any("media-plane" in b for b in body["blockers"])


def test_run_experimento_gateado_503_si_control_no_listo(two_plane_client, repo, control_state):
    control_state.ready = False
    _write_umbrella_manifest(repo, slug="pf_exp")
    r = two_plane_client.post("/api/experiments/run", json={"slug": "pf_exp"})
    assert r.status_code == 503
    body = r.json()
    assert "Plataforma no lista" in body["detail"]
    assert body["preflight"]["ready"] is False
    # El gate corta ANTES de disparar nada: ningún plano recibió un launch.
    assert control_state.launched == []


def test_run_experimento_gateado_503_si_media_no_listo(
    two_plane_client, repo, fake_state, control_state
):
    fake_state.ready = False
    _write_umbrella_manifest(repo, slug="pf_exp2")
    r = two_plane_client.post("/api/experiments/run", json={"slug": "pf_exp2"})
    assert r.status_code == 503
    assert control_state.launched == []


def test_run_experimento_falla_preflight_por_distributor_executable_inaccesible(
    two_plane_client, repo, fake_state, control_state, monkeypatch
):
    _write_distribution_manifest(repo, slug="pf_dist_exec")
    monkeypatch.setenv("EOVRT_DISTRIBUTION_EXECUTABLE", "/no/existe/bin")

    r = two_plane_client.post("/api/experiments/run", json={"slug": "pf_dist_exec"})
    assert r.status_code == 503
    body = r.json()
    assert body["preflight"]["ready"] is False
    assert any("el binario eovrt-distribute" in blocker for blocker in body["preflight"]["blockers"])
    assert fake_state.launched == []
    assert control_state.launched == []


def test_run_experimento_falla_preflight_por_broker_live_inalcanzable(
    two_plane_client, repo, fake_state, control_state, monkeypatch
):
    _write_distribution_manifest(repo, slug="pf_dist_broker", broker_host="127.0.0.1", broker_port=1883)
    monkeypatch.setenv("EOVRT_DISTRIBUTION_EXECUTABLE", "/bin/true")

    def _refuse(*_args, **_kwargs):
        raise ConnectionRefusedError("broker unreachable")

    monkeypatch.setattr("eovrt_webconsole.preflight.socket.create_connection", _refuse)

    r = two_plane_client.post("/api/experiments/run", json={"slug": "pf_dist_broker"})
    assert r.status_code == 503
    body = r.json()
    assert body["preflight"]["ready"] is False
    assert any("broker MQTT inalcanzable" in blocker for blocker in body["preflight"]["blockers"])
    assert fake_state.launched == []
    assert control_state.launched == []


def test_run_experimento_skips_broker_check_with_dry_run(
    two_plane_client, repo, fake_state, control_state, monkeypatch
):
    _write_distribution_manifest(
        repo,
        slug="pf_dist_dryrun",
        distribution_channel_mode="dry_run",
        broker_host="localhost",
        broker_port=0,
    )
    monkeypatch.setenv("EOVRT_DISTRIBUTION_EXECUTABLE", "/bin/true")

    def _no_se_llama(*_args, **_kwargs):
        raise AssertionError("socket.create_connection no debe invocarse para channel.mode=dry_run")

    monkeypatch.setattr("eovrt_webconsole.preflight.socket.create_connection", _no_se_llama)

    r = two_plane_client.post("/api/experiments/run", json={"slug": "pf_dist_dryrun"})
    assert r.status_code == 202
