"""GET /api/preflight (estado agregado de ambos planos) + gate 503 en
POST /api/experiments/run cuando la plataforma no está lista."""
from __future__ import annotations

import httpx
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
    """El chequeo de binario local solo corre en el fallback por subproceso
    (ADR-020: HTTP es el default) -- seleccionarlo explicitamente."""
    _write_distribution_manifest(repo, slug="pf_dist_exec")
    monkeypatch.setenv("EOVRT_CONSOLE_DISTRIBUTION_TRANSPORT", "subprocess")
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
    """Chequeo de broker MQTT, agnostico del transporte -- se fija el fallback
    por subproceso (ADR-020: HTTP es el default) para no depender del
    healthz real del servicio de distribucion, que es un gate aparte."""
    _write_distribution_manifest(repo, slug="pf_dist_broker", broker_host="127.0.0.1", broker_port=1883)
    monkeypatch.setenv("EOVRT_CONSOLE_DISTRIBUTION_TRANSPORT", "subprocess")
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


# --- I3: con EOVRT_CONSOLE_DISTRIBUTION_TRANSPORT=http (ADR-019) el gate NO
# debe exigir el binario local -- el distribuidor puede vivir en otro host o
# contenedor. En su lugar sondea /healthz contra distribution_service_url. ---


class _FakeHealthzResponse:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code


def test_run_experimento_transporte_http_no_exige_binario_pero_chequea_healthz(
    two_plane_client, repo, fake_state, control_state, monkeypatch
):
    """No pasar EOVRT_DISTRIBUTION_EXECUTABLE (ni tenerlo en PATH): con
    transporte http eso ya no debe bloquear. El servicio de distribucion
    inalcanzable si debe bloquear, y con un blocker distinto al del binario."""
    _write_distribution_manifest(
        repo, slug="pf_dist_http_down", distribution_channel_mode="dry_run"
    )
    monkeypatch.delenv("EOVRT_DISTRIBUTION_EXECUTABLE", raising=False)
    monkeypatch.setenv("EOVRT_CONSOLE_DISTRIBUTION_TRANSPORT", "http")

    class _RefusingClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc) -> None:
            return None

        async def get(self, url):
            raise httpx.ConnectError("connection refused", request=None)

    monkeypatch.setattr("eovrt_webconsole.preflight.httpx.AsyncClient", _RefusingClient)

    r = two_plane_client.post("/api/experiments/run", json={"slug": "pf_dist_http_down"})
    assert r.status_code == 503
    body = r.json()
    blockers = body["preflight"]["blockers"]
    assert not any("binario eovrt-distribute" in blocker for blocker in blockers)
    assert any("no es alcanzable" in blocker for blocker in blockers)
    assert fake_state.launched == []
    assert control_state.launched == []


def test_run_experimento_transporte_http_con_servicio_ok_no_gatea_por_distribucion(
    two_plane_client, repo, fake_state, control_state, monkeypatch
):
    _write_distribution_manifest(
        repo, slug="pf_dist_http_ok", distribution_channel_mode="dry_run"
    )
    monkeypatch.delenv("EOVRT_DISTRIBUTION_EXECUTABLE", raising=False)
    monkeypatch.setenv("EOVRT_CONSOLE_DISTRIBUTION_TRANSPORT", "http")

    class _HealthyClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc) -> None:
            return None

        async def get(self, url):
            return _FakeHealthzResponse(200)

    monkeypatch.setattr("eovrt_webconsole.preflight.httpx.AsyncClient", _HealthyClient)

    r = two_plane_client.post("/api/experiments/run", json={"slug": "pf_dist_http_ok"})
    assert r.status_code == 202


def test_run_experimento_skips_broker_check_with_dry_run(
    two_plane_client, repo, fake_state, control_state, monkeypatch
):
    """dry_run salta el chequeo de broker MQTT, agnostico del transporte -- se
    fija el fallback por subproceso (ADR-020: HTTP es el default) para no
    depender del healthz real del servicio de distribucion, que es un gate
    aparte no relacionado con lo que este test verifica."""
    _write_distribution_manifest(
        repo,
        slug="pf_dist_dryrun",
        distribution_channel_mode="dry_run",
        broker_host="localhost",
        broker_port=0,
    )
    monkeypatch.setenv("EOVRT_CONSOLE_DISTRIBUTION_TRANSPORT", "subprocess")
    monkeypatch.setenv("EOVRT_DISTRIBUTION_EXECUTABLE", "/bin/true")

    def _no_se_llama(*_args, **_kwargs):
        raise AssertionError("socket.create_connection no debe invocarse para channel.mode=dry_run")

    monkeypatch.setattr("eovrt_webconsole.preflight.socket.create_connection", _no_se_llama)

    r = two_plane_client.post("/api/experiments/run", json={"slug": "pf_dist_dryrun"})
    assert r.status_code == 202
