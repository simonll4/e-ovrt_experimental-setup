"""Runner: los tres cambios que pide la generacion 2 de la evidencia (doc 134 §5.2).

- Experimento de medios solos (sin `runs.control`): bench de imagenes.
- Reuso de detecciones (`runs.media.reuse_run_id` / `reuse_run_dir`): el replay
  relee una corrida ya escrita; el media-plane no infiere.
- `timeout_s` por experimento (manifiesto) y por disparo (ruta).

Mas el arreglo de `input`: el replay conserva `track_persons` de la config de
control (sin el, el pattern set por sujeto corria sin identidad y en silencio).
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from eovrt_webconsole.experiment import runner as runner_mod
from eovrt_webconsole.experiment.manifest import ExperimentManifest
from eovrt_webconsole.experiment.runner import run_experiment

NOW = datetime(2026, 10, 26, 12, 0, 0, tzinfo=UTC)

MEDIA_CONFIG = {"ingest": {"plugin": "image_folder", "config": {"path": "/bench"}}}
CONTROL_CONFIG = {"patterns": {"file": "p.yaml"}}
SUBJECT_CONTROL_CONFIG = {
    "patterns": {"file": "p_subject.yaml"},
    "input": {"type": "media_jsonl", "path": "/placeholder", "track_persons": True},
}


class FakeMedia:
    def __init__(self, status: str = "succeeded") -> None:
        self.launched: list[dict] = []
        self._status = status

    async def launch(self, run_request: dict) -> str:
        self.launched.append(run_request)
        return f"run_media_{len(self.launched)}"

    async def status(self, run_id: str) -> dict:
        return {"run_id": run_id, "status": self._status}


class FakeControl:
    def __init__(self) -> None:
        self.launched: list[tuple[dict, str]] = []

    async def launch(self, config: dict, mode: str, experiment_id: str | None) -> str:
        self.launched.append((config, mode))
        return f"ctl_{len(self.launched)}"

    async def status(self, control_run_id: str) -> dict:
        return {"control_run_id": control_run_id, "status": "succeeded"}

    async def current(self) -> dict:
        return {"subscribed": True}


def _loader(configs: dict[str, dict]):
    def load(path: str) -> dict:
        return json.loads(json.dumps(configs[path]))

    return load


def _manifest(runs: dict, **extra) -> ExperimentManifest:
    control = runs.get("control")
    sequencing = "media_first" if control is None or control["mode"] == "replay" else "control_first"
    return ExperimentManifest.model_validate(
        {
            "schema_version": "experiment.manifest.v1",
            "slug": "gen2",
            "runs": runs,
            "sequencing": sequencing,
            **extra,
        }
    )


MEDIA_RUN = {"service": "media-plane", "config": "media.yaml", "mode": "run"}
CONTROL_REPLAY = {"service": "control-plane", "config": "control.yaml", "mode": "replay"}


def _write_media_run(run_dir: Path, *, summary: dict | None = None, detections: bool = True) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    if summary is not None:
        (run_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    if detections:
        (run_dir / "detections.jsonl").write_text('{"frame": 0}\n', encoding="utf-8")


# --- medios solos -------------------------------------------------------------


async def test_medios_solos_corre_solo_el_media_plane_y_consolida_sin_control(tmp_path):
    media_dir = tmp_path / "media_runs" / "run_media_1"
    _write_media_run(media_dir, summary={"run_id": "run_media_1", "status": "succeeded"})
    media, control = FakeMedia(), FakeControl()

    result = await run_experiment(
        _manifest({"media": MEDIA_RUN}),
        media_backend=media,
        control_backend=control,
        now=NOW,
        load_config=_loader({"media.yaml": MEDIA_CONFIG}),
        resolve_run_dir=lambda plane, run_id: tmp_path / f"{plane}_runs" / run_id,
        dest_root=tmp_path / "consolidado",
    )

    assert result.ok is True
    assert result.control_run_id is None and result.control_status is None
    assert len(media.launched) == 1 and control.launched == []
    exp_dir = Path(result.consolidated_dir)
    assert (exp_dir / "media" / "summary.json").is_file()
    assert not (exp_dir / "control").exists()
    assert result.report_path is not None


async def test_medios_solos_fallido_no_consolida(tmp_path):
    result = await run_experiment(
        _manifest({"media": MEDIA_RUN}),
        media_backend=FakeMedia(status="failed"),
        control_backend=FakeControl(),
        now=NOW,
        load_config=_loader({"media.yaml": MEDIA_CONFIG}),
        dest_root=tmp_path / "consolidado",
    )
    assert result.ok is False
    assert result.media_status == "failed"
    assert result.consolidated_dir is None


async def test_medios_solos_con_ground_truth_no_evalua_temporal(tmp_path):
    media_dir = tmp_path / "media_runs" / "run_media_1"
    _write_media_run(media_dir, summary={"status": "succeeded"})
    llamadas: list = []

    result = await run_experiment(
        _manifest({"media": MEDIA_RUN}, ground_truth="/gt.json"),
        media_backend=FakeMedia(),
        control_backend=FakeControl(),
        now=NOW,
        load_config=_loader({"media.yaml": MEDIA_CONFIG}),
        resolve_run_dir=lambda plane, run_id: tmp_path / f"{plane}_runs" / run_id,
        dest_root=tmp_path / "consolidado",
        evaluate_temporal=lambda *args: llamadas.append(args),
    )
    assert result.ok is True
    assert llamadas == []


async def test_distribucion_sin_control_se_rechaza():
    manifest = _manifest(
        {
            "media": MEDIA_RUN,
            "distribution": {"service": "distribution", "config": "d.yaml", "mode": "replay"},
        }
    )
    with pytest.raises(ValueError, match="distribution"):
        await run_experiment(
            manifest, media_backend=FakeMedia(), control_backend=FakeControl(), now=NOW
        )


async def test_sin_media_se_rechaza():
    manifest = _manifest({"control": CONTROL_REPLAY})
    with pytest.raises(ValueError, match="media"):
        await run_experiment(
            manifest, media_backend=FakeMedia(), control_backend=FakeControl(), now=NOW
        )


# --- reuso de detecciones -----------------------------------------------------


async def test_reuso_por_run_id_no_infiere_y_replay_lee_esas_detecciones(tmp_path):
    reused = tmp_path / "media_runs" / "run_viejo"
    _write_media_run(reused, summary={"run_id": "run_viejo", "status": "succeeded"})
    (tmp_path / "control_runs" / "ctl_1").mkdir(parents=True)
    media, control = FakeMedia(), FakeControl()

    result = await run_experiment(
        _manifest({"media": {**MEDIA_RUN, "reuse_run_id": "run_viejo"}, "control": CONTROL_REPLAY}),
        media_backend=media,
        control_backend=control,
        now=NOW,
        load_config=_loader({"control.yaml": CONTROL_CONFIG}),
        resolve_run_dir=lambda plane, run_id: tmp_path / f"{plane}_runs" / run_id,
        dest_root=tmp_path / "consolidado",
    )

    assert result.ok is True
    assert media.launched == []
    assert result.media_run_id == "run_viejo"
    config, mode = control.launched[0]
    assert mode == "replay"
    assert config["input"] == {"type": "media_jsonl", "path": str(reused / "detections.jsonl")}
    ref = json.loads(
        (Path(result.consolidated_dir) / "media" / "detections.ref.json").read_text(encoding="utf-8")
    )
    assert ref == {"run_id": "run_viejo", "path": str(reused / "detections.jsonl")}


async def test_reuso_por_directorio_sin_summary_usa_ese_directorio(tmp_path):
    fusion = tmp_path / "fusiones" / "h1_clip_a"
    _write_media_run(fusion, summary=None)
    (tmp_path / "control_runs" / "ctl_1").mkdir(parents=True)
    control = FakeControl()

    result = await run_experiment(
        _manifest({"media": {**MEDIA_RUN, "reuse_run_dir": str(fusion)}, "control": CONTROL_REPLAY}),
        media_backend=FakeMedia(),
        control_backend=control,
        now=NOW,
        load_config=_loader({"control.yaml": CONTROL_CONFIG}),
        resolve_run_dir=lambda plane, run_id: tmp_path / f"{plane}_runs" / run_id,
        dest_root=tmp_path / "consolidado",
    )

    assert result.ok is True
    assert result.media_run_id == "h1_clip_a"
    assert control.launched[0][0]["input"]["path"] == str(fusion / "detections.jsonl")
    ref = json.loads(
        (Path(result.consolidated_dir) / "media" / "detections.ref.json").read_text(encoding="utf-8")
    )
    assert ref["path"] == str(fusion / "detections.jsonl")


async def test_reuso_de_corrida_fallida_no_dispara_control(tmp_path):
    reused = tmp_path / "media_runs" / "run_roto"
    _write_media_run(reused, summary={"status": "failed"})
    control = FakeControl()

    result = await run_experiment(
        _manifest({"media": {**MEDIA_RUN, "reuse_run_id": "run_roto"}, "control": CONTROL_REPLAY}),
        media_backend=FakeMedia(),
        control_backend=control,
        now=NOW,
        load_config=_loader({"control.yaml": CONTROL_CONFIG}),
        resolve_run_dir=lambda plane, run_id: tmp_path / f"{plane}_runs" / run_id,
    )
    assert result.ok is False
    assert result.media_status == "failed"
    assert control.launched == []


async def test_reuso_sin_detecciones_falla_con_mensaje_claro(tmp_path):
    reused = tmp_path / "media_runs" / "run_vacio"
    _write_media_run(reused, summary={"status": "succeeded"}, detections=False)

    with pytest.raises(FileNotFoundError, match="detections.jsonl"):
        await run_experiment(
            _manifest({"media": {**MEDIA_RUN, "reuse_run_id": "run_vacio"}, "control": CONTROL_REPLAY}),
            media_backend=FakeMedia(),
            control_backend=FakeControl(),
            now=NOW,
            load_config=_loader({"control.yaml": CONTROL_CONFIG}),
            resolve_run_dir=lambda plane, run_id: tmp_path / f"{plane}_runs" / run_id,
        )


async def test_reuso_exige_control_en_replay():
    manifest = _manifest(
        {
            "media": {**MEDIA_RUN, "reuse_run_id": "run_x"},
            "control": {**CONTROL_REPLAY, "mode": "live"},
        }
    )
    with pytest.raises(ValueError, match="replay"):
        await run_experiment(
            manifest, media_backend=FakeMedia(), control_backend=FakeControl(), now=NOW
        )


async def test_reuso_solo_en_el_plano_de_medios():
    manifest = _manifest(
        {"media": MEDIA_RUN, "control": {**CONTROL_REPLAY, "reuse_run_id": "ctl_x"}}
    )
    with pytest.raises(ValueError, match="media"):
        await run_experiment(
            manifest, media_backend=FakeMedia(), control_backend=FakeControl(), now=NOW
        )


async def test_reuso_sin_control_se_rechaza():
    manifest = _manifest({"media": {**MEDIA_RUN, "reuse_run_id": "run_x"}})
    with pytest.raises(ValueError, match="replay"):
        await run_experiment(
            manifest, media_backend=FakeMedia(), control_backend=FakeControl(), now=NOW
        )


# --- input del replay ---------------------------------------------------------


async def test_replay_conserva_track_persons_de_la_config(tmp_path):
    control = FakeControl()
    result = await run_experiment(
        _manifest({"media": MEDIA_RUN, "control": CONTROL_REPLAY}),
        media_backend=FakeMedia(),
        control_backend=control,
        now=NOW,
        load_config=_loader({"media.yaml": MEDIA_CONFIG, "control.yaml": SUBJECT_CONTROL_CONFIG}),
        resolve_run_dir=lambda plane, run_id: tmp_path / f"{plane}_runs" / run_id,
        dest_root=tmp_path / "consolidado",
    )
    assert result.ok is True
    config, _mode = control.launched[0]
    assert config["input"]["type"] == "media_jsonl"
    assert config["input"]["track_persons"] is True
    assert config["input"]["path"] != "/placeholder"


async def test_replay_sin_track_persons_no_lo_agrega(tmp_path):
    control = FakeControl()
    await run_experiment(
        _manifest({"media": MEDIA_RUN, "control": CONTROL_REPLAY}),
        media_backend=FakeMedia(),
        control_backend=control,
        now=NOW,
        load_config=_loader({"media.yaml": MEDIA_CONFIG, "control.yaml": CONTROL_CONFIG}),
        resolve_run_dir=lambda plane, run_id: tmp_path / f"{plane}_runs" / run_id,
        dest_root=tmp_path / "consolidado",
    )
    assert "track_persons" not in control.launched[0][0]["input"]


async def test_vivo_conserva_la_seccion_bus_de_la_config_de_medios(tmp_path):
    """El runner habilita el bus, pero sin pisar `wait_for_subscriber_ms`: con una fuente que
    publica en el primer instante (un video) el primer evento se perdía (RT-02, 2026-10-26)."""
    media = FakeMedia()
    media_cfg = {**MEDIA_CONFIG, "bus": {"wait_for_subscriber_ms": 10000}}
    await run_experiment(
        _manifest({"media": MEDIA_RUN, "control": {**CONTROL_REPLAY, "mode": "live"}}),
        media_backend=media,
        control_backend=FakeControl(),
        now=NOW,
        load_config=_loader({"media.yaml": media_cfg, "control.yaml": CONTROL_CONFIG}),
        resolve_run_dir=lambda plane, run_id: tmp_path / f"{plane}_runs" / run_id,
        dest_root=tmp_path / "consolidado",
    )
    assert media.launched[0]["bus"] == {"wait_for_subscriber_ms": 10000, "enabled": True}


# --- tiempo maximo ------------------------------------------------------------


@pytest.fixture
def poll_timeouts(monkeypatch):
    vistos: list[float] = []
    original = runner_mod._poll_until_terminal

    async def espia(get_status, run_id, *, poll_interval_s, timeout_s):
        vistos.append(timeout_s)
        return await original(
            get_status, run_id, poll_interval_s=poll_interval_s, timeout_s=timeout_s
        )

    monkeypatch.setattr(runner_mod, "_poll_until_terminal", espia)
    return vistos


async def test_timeout_por_default_es_300(poll_timeouts):
    await run_experiment(
        _manifest({"media": MEDIA_RUN}),
        media_backend=FakeMedia(status="failed"),
        control_backend=FakeControl(),
        now=NOW,
        load_config=_loader({"media.yaml": MEDIA_CONFIG}),
    )
    assert poll_timeouts == [300.0]


async def test_timeout_del_manifiesto(poll_timeouts):
    await run_experiment(
        _manifest({"media": MEDIA_RUN}, timeout_s=5400),
        media_backend=FakeMedia(status="failed"),
        control_backend=FakeControl(),
        now=NOW,
        load_config=_loader({"media.yaml": MEDIA_CONFIG}),
    )
    assert poll_timeouts == [5400.0]


async def test_timeout_explicito_gana_sobre_el_manifiesto(poll_timeouts):
    await run_experiment(
        _manifest({"media": MEDIA_RUN}, timeout_s=5400),
        media_backend=FakeMedia(status="failed"),
        control_backend=FakeControl(),
        now=NOW,
        load_config=_loader({"media.yaml": MEDIA_CONFIG}),
        timeout_s=60,
    )
    assert poll_timeouts == [60]


def test_manifiesto_rechaza_timeout_no_positivo():
    with pytest.raises(ValidationError):
        _manifest({"media": MEDIA_RUN}, timeout_s=0)


async def test_sin_control_y_control_first_sigue_siendo_error():
    """Medios solos se declara: un manifiesto al que le falta el control y
    dice `control_first` (el default) no corre como medios solos."""
    manifest = ExperimentManifest.model_validate(
        {"schema_version": "experiment.manifest.v1", "slug": "x", "runs": {"media": MEDIA_RUN}}
    )
    with pytest.raises(ValueError, match="control"):
        await run_experiment(
            manifest, media_backend=FakeMedia(), control_backend=FakeControl(), now=NOW
        )


# --- ruta: timeout_s por disparo y preflight de medios solos -----------------


def _write_media_only_manifest(repo, slug: str) -> None:
    media_path = repo / "experiments" / f"{slug}_media.yaml"
    media_path.write_text(yaml.safe_dump(MEDIA_CONFIG))
    manifest = {
        "schema_version": "experiment.manifest.v1",
        "slug": slug,
        "runs": {"media": {"service": "media-plane", "config": str(media_path), "mode": "run"}},
        "sequencing": "media_first",
    }
    (repo / "experiments" / f"{slug}.yaml").write_text(yaml.safe_dump(manifest, sort_keys=False))


def test_ruta_pasa_timeout_s_al_manager(two_plane_client, repo):
    _write_media_only_manifest(repo, "img_bench")
    capturado: dict = {}

    def fake_start(manifest, **kwargs):
        capturado.update(kwargs)
        return "exp_fake"

    two_plane_client.app.state.experiment_manager.start = fake_start
    r = two_plane_client.post(
        "/api/experiments/run", json={"slug": "img_bench", "timeout_s": 7200}
    )
    assert r.status_code == 202
    assert capturado["timeout_s"] == 7200.0


def test_ruta_sin_timeout_no_lo_pasa(two_plane_client, repo):
    _write_media_only_manifest(repo, "img_bench2")
    capturado: dict = {}

    def fake_start(manifest, **kwargs):
        capturado.update(kwargs)
        return "exp_fake"

    two_plane_client.app.state.experiment_manager.start = fake_start
    r = two_plane_client.post("/api/experiments/run", json={"slug": "img_bench2"})
    assert r.status_code == 202
    assert "timeout_s" not in capturado


def test_preflight_medios_solos_no_exige_control(two_plane_client, repo, control_state):
    control_state.ready = False
    _write_media_only_manifest(repo, "img_bench4")
    two_plane_client.app.state.experiment_manager.start = lambda manifest, **kw: "exp_fake"
    r = two_plane_client.post("/api/experiments/run", json={"slug": "img_bench4"})
    assert r.status_code == 202


def test_preflight_reuso_no_exige_media(two_plane_client, repo, fake_state):
    fake_state.ready = False
    control_path = repo / "experiments" / "reuso_control.yaml"
    control_path.write_text(yaml.safe_dump(CONTROL_CONFIG))
    manifest = {
        "schema_version": "experiment.manifest.v1",
        "slug": "reuso_1",
        "runs": {
            "media": {
                "service": "media-plane",
                "config": "no-se-lee.yaml",
                "mode": "run",
                "reuse_run_id": "run_viejo",
            },
            "control": {"service": "control-plane", "config": str(control_path), "mode": "replay"},
        },
        "sequencing": "media_first",
    }
    (repo / "experiments" / "reuso_1.yaml").write_text(yaml.safe_dump(manifest, sort_keys=False))
    two_plane_client.app.state.experiment_manager.start = lambda manifest, **kw: "exp_fake"
    r = two_plane_client.post("/api/experiments/run", json={"slug": "reuso_1"})
    assert r.status_code == 202


def test_preflight_sin_manifiesto_sigue_exigiendo_los_dos(two_plane_client, control_state):
    control_state.ready = False
    body = two_plane_client.get("/api/preflight").json()
    assert body["ready"] is False


@pytest.mark.parametrize("valor", [0, -5, "mucho", True])
def test_ruta_rechaza_timeout_invalido(two_plane_client, repo, valor):
    _write_media_only_manifest(repo, "img_bench3")
    r = two_plane_client.post(
        "/api/experiments/run", json={"slug": "img_bench3", "timeout_s": valor}
    )
    assert r.status_code == 422
