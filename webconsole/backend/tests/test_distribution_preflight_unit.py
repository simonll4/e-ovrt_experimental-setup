"""Pruebas unitarias del gate de distribución, sin levantar TestClient."""
from __future__ import annotations

import httpx
import pytest
import yaml

from eovrt_webconsole.experiment.manifest import ExperimentManifest
from eovrt_webconsole.preflight import (
    _distribution_http_transport_checks,
    _distribution_preflight_checks,
)


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
    """El chequeo de binario local solo corre en el fallback por subproceso
    (ADR-020: HTTP es el default) -- seleccionarlo explicitamente para
    ejercitar este camino."""
    config = _write_config(tmp_path, "live")
    monkeypatch.setenv("EOVRT_CONSOLE_DISTRIBUTION_TRANSPORT", "subprocess")

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


# --- I3: con transporte HTTP -- el default desde ADR-020 -- el distribuidor
# puede vivir en otro host/contenedor -- exigir el binario local tumbaria el
# experimento antes de empezar. El chequeo equivalente es un sondeo async a
# /healthz, no forma parte de `_distribution_preflight_checks` (sync). ---


def test_distribution_preflight_no_exige_binario_local_con_transporte_http_explicito(
    tmp_path, monkeypatch
):
    """Back-compat: `=http` explicito (valor usado antes de ADR-020 para optar
    por HTTP) sigue sin exigir el binario local."""
    config = _write_config(tmp_path, "dry_run")

    def _missing():
        raise FileNotFoundError("no deberia llamarse con transporte http")

    monkeypatch.setattr("eovrt_webconsole.preflight.resolve_distribution_executable", _missing)
    monkeypatch.setenv("EOVRT_CONSOLE_DISTRIBUTION_TRANSPORT", "http")

    assert _distribution_preflight_checks(_manifest(config.name), tmp_path) == []


def test_distribution_preflight_exige_binario_en_el_fallback_subproceso(tmp_path, monkeypatch):
    """Guard de no-regresion (ADR-020): con el fallback explicito por
    subproceso, el chequeo de binario local sigue vigente."""
    config = _write_config(tmp_path, "dry_run")
    monkeypatch.setenv("EOVRT_CONSOLE_DISTRIBUTION_TRANSPORT", "subprocess")

    def _missing():
        raise FileNotFoundError("missing")

    monkeypatch.setattr("eovrt_webconsole.preflight.resolve_distribution_executable", _missing)

    blockers = _distribution_preflight_checks(_manifest(config.name), tmp_path)

    assert any("binario eovrt-distribute" in blocker for blocker in blockers)


def test_distribution_preflight_no_exige_binario_local_por_defecto_sin_env_var(
    tmp_path, monkeypatch
):
    """Guard de no-regresion (ADR-020): sin el env var seteada -- el default
    real, no un valor explicito -- HTTP es el transporte y el chequeo de
    binario local NO corre. Si alguien revierte el default a subproceso, este
    test empieza a fallar (ver `test_distribution_preflight_exige_binario_en_
    el_fallback_subproceso` para el contraste con el fallback explicito)."""
    config = _write_config(tmp_path, "dry_run")
    monkeypatch.delenv("EOVRT_CONSOLE_DISTRIBUTION_TRANSPORT", raising=False)

    def _missing():
        raise FileNotFoundError("no deberia llamarse por defecto (HTTP)")

    monkeypatch.setattr("eovrt_webconsole.preflight.resolve_distribution_executable", _missing)

    assert _distribution_preflight_checks(_manifest(config.name), tmp_path) == []


class _FakeHealthzResponse:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code


class _FakeHealthzClient:
    def __init__(self, status_code: int, *args, **kwargs) -> None:
        self._status_code = status_code

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc) -> None:
        return None

    async def get(self, url):
        return _FakeHealthzResponse(self._status_code)


def _fake_healthz_client(status_code: int):
    def _factory(*args, **kwargs):
        return _FakeHealthzClient(status_code, *args, **kwargs)

    return _factory


async def test_distribution_http_transport_checks_ok(monkeypatch):
    monkeypatch.setattr(
        "eovrt_webconsole.preflight.httpx.AsyncClient", _fake_healthz_client(200)
    )
    assert await _distribution_http_transport_checks("http://localhost:8082") == []


async def test_distribution_http_transport_checks_status_no_ok(monkeypatch):
    monkeypatch.setattr(
        "eovrt_webconsole.preflight.httpx.AsyncClient", _fake_healthz_client(503)
    )
    blockers = await _distribution_http_transport_checks("http://localhost:8082")
    assert any("503" in blocker for blocker in blockers)


async def test_distribution_http_transport_checks_inalcanzable(monkeypatch):
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
    blockers = await _distribution_http_transport_checks("http://localhost:8082")
    assert any("no es alcanzable" in blocker for blocker in blockers)
