"""Pruebas unitarias del gate de distribución, sin levantar TestClient."""
from __future__ import annotations

import yaml

from eovrt_webconsole.experiment.manifest import ExperimentManifest
from eovrt_webconsole.preflight import _distribution_preflight_checks


def _manifest(config: str) -> ExperimentManifest:
    return ExperimentManifest.model_validate(
        {
            "schema_version": "experiment.manifest.v1",
            "slug": "distribution_preflight",
            "runs": {
                "distribution": {
                    "service": "distribution",
                    "config": config,
                    "mode": "replay",
                }
            },
        }
    )


def _write_config(tmp_path, mode: str):
    path = tmp_path / "distribution.yaml"
    path.write_text(
        yaml.safe_dump({"channel": {"mode": mode, "host": "broker", "port": 1883}}),
        encoding="utf-8",
    )
    return path


def test_distribution_preflight_blocks_missing_executable(tmp_path, monkeypatch):
    config = _write_config(tmp_path, "live")

    def _missing():
        raise FileNotFoundError("missing")

    monkeypatch.setattr("eovrt_webconsole.preflight.resolve_distribution_executable", _missing)

    blockers = _distribution_preflight_checks(_manifest(config.name), tmp_path)

    assert any("binario eovrt-distribute" in blocker for blocker in blockers)


def test_distribution_preflight_blocks_unreachable_live_broker(tmp_path, monkeypatch):
    config = _write_config(tmp_path, "live")
    monkeypatch.setattr("eovrt_webconsole.preflight.resolve_distribution_executable", list)

    def _refuse(*_args, **_kwargs):
        raise ConnectionRefusedError("unreachable")

    monkeypatch.setattr("eovrt_webconsole.preflight.socket.create_connection", _refuse)

    blockers = _distribution_preflight_checks(_manifest(config.name), tmp_path)

    assert any("broker MQTT inalcanzable" in blocker for blocker in blockers)


def test_distribution_preflight_skips_broker_for_dry_run(tmp_path, monkeypatch):
    config = _write_config(tmp_path, "dry_run")
    monkeypatch.setattr("eovrt_webconsole.preflight.resolve_distribution_executable", list)

    def _unexpected(*_args, **_kwargs):
        raise AssertionError("dry_run no debe abrir un socket")

    monkeypatch.setattr("eovrt_webconsole.preflight.socket.create_connection", _unexpected)

    assert _distribution_preflight_checks(_manifest(config.name), tmp_path) == []
