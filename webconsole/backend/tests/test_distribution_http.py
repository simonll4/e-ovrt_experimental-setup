import asyncio
import functools
import logging

import httpx
import pytest

from eovrt_webconsole.experiment import runner
from eovrt_webconsole.experiment.distribution_http import run_distribution_http

# El backend usa `asyncio_mode = "auto"` (pyproject): los tests async NO llevan
# marcador. `os` y `functools` ya estan importados en runner.py (lineas 20 y 16).

_MOD = "eovrt_webconsole.experiment.distribution_http"


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise AssertionError(f"HTTP {self.status_code}")


class _FakeClient:
    """Devuelve 201 al POST y un run terminal al primer GET."""

    def __init__(self, *args, **kwargs) -> None:
        self.posted: dict | None = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc) -> None:
        return None

    async def post(self, url, json=None):
        self.posted = json
        return _FakeResponse(201, {"distribution_run_id": "dist_x"})

    async def get(self, url):
        return _FakeResponse(
            200,
            {
                "distribution_run_id": "dist_x",
                "status": "succeeded",
                "summary": {"delivered": 1},
                "error": None,
            },
        )


async def test_devuelve_el_summary_del_servicio(monkeypatch, tmp_path):
    monkeypatch.setattr("eovrt_webconsole.experiment.distribution_http.httpx.AsyncClient", _FakeClient)
    summary = await run_distribution_http(
        mode="replay",
        alerts_path=tmp_path / "a.jsonl",
        out_dir=tmp_path / "out",
        config_path=None,
        endpoint=None,
        control_run_id=None,
        backfill_path=None,
        idle_timeout_ms=None,
        timeout_s=30.0,
        base_url="http://localhost:8082",
    )
    assert summary == {"delivered": 1}


async def test_modo_invalido_es_error(tmp_path):
    with pytest.raises(ValueError):
        await run_distribution_http(
            mode="nope", alerts_path=None, out_dir=tmp_path, config_path=None,
            endpoint=None, control_run_id=None, backfill_path=None,
            idle_timeout_ms=None, timeout_s=1.0, base_url="http://x",
        )


# --- Hallazgo 1: failed/cancelled deben propagar error, nunca tratarse como
# exito. Prueba negativa (documentada en el reporte, no forma parte del
# archivo): cambiar el `!=` del codigo por un `== "failed"` hace fallar el
# caso parametrizado "cancelled" (deja de levantar), lo que confirma que este
# test SI detecta la reintroduccion del bug original. ---


def _make_terminal_client(status: str, error: str | None):
    class _Client:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc) -> None:
            return None

        async def post(self, url, json=None):
            return _FakeResponse(201, {"distribution_run_id": "dist_z"})

        async def get(self, url):
            return _FakeResponse(
                200,
                {
                    "distribution_run_id": "dist_z",
                    "status": status,
                    "summary": {"delivered": 0},
                    "error": error,
                },
            )

    return _Client


@pytest.mark.parametrize(
    "status,error",
    [
        ("failed", "boom: motivo x"),
        ("cancelled", "detenida a mano: motivo y"),
    ],
)
async def test_estado_terminal_no_succeeded_propaga_error_con_detalle(
    monkeypatch, tmp_path, status, error
):
    monkeypatch.setattr(f"{_MOD}.httpx.AsyncClient", _make_terminal_client(status, error))
    with pytest.raises(RuntimeError) as excinfo:
        await run_distribution_http(
            mode="replay",
            alerts_path=tmp_path / "a.jsonl",
            out_dir=tmp_path / "out",
            config_path=None,
            endpoint=None,
            control_run_id=None,
            backfill_path=None,
            idle_timeout_ms=None,
            timeout_s=5.0,
            base_url="http://x",
        )
    message = str(excinfo.value)
    assert status in message
    assert error in message


# --- Hallazgo 2: 409/422 deben propagar el `detail` (y demas campos, p.ej.
# `active_run_id`) del body del servicio, no solo "HTTP 409". ---


class _FakeStatusErrorResponse:
    """Simula una respuesta de httpx que falla `raise_for_status()` con un
    body JSON accesible via `exc.response.json()` (como el httpx real)."""

    def __init__(self, status_code: int, payload: dict) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("POST", "http://x/api/runs")
            raise httpx.HTTPStatusError(
                f"HTTP {self.status_code}", request=request, response=self
            )


class _FakeClientConflictOnPost:
    def __init__(self, *args, **kwargs) -> None:
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc) -> None:
        return None

    async def post(self, url, json=None):
        return _FakeStatusErrorResponse(
            409, {"detail": "ya hay una corrida activa", "active_run_id": "dist_prev"}
        )

    async def get(self, url):
        raise AssertionError("no deberia llegar al GET: el POST ya fallo con 409")


async def test_409_en_post_propaga_detail_y_active_run_id(monkeypatch, tmp_path):
    monkeypatch.setattr(f"{_MOD}.httpx.AsyncClient", _FakeClientConflictOnPost)
    with pytest.raises(RuntimeError) as excinfo:
        await run_distribution_http(
            mode="replay",
            alerts_path=tmp_path / "a.jsonl",
            out_dir=tmp_path / "out",
            config_path=None,
            endpoint=None,
            control_run_id=None,
            backfill_path=None,
            idle_timeout_ms=None,
            timeout_s=5.0,
            base_url="http://x",
        )
    message = str(excinfo.value)
    assert "ya hay una corrida activa" in message
    assert "dist_prev" in message


class _FakeClientInvalidOnPoll:
    def __init__(self, *args, **kwargs) -> None:
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc) -> None:
        return None

    async def post(self, url, json=None):
        return _FakeResponse(201, {"distribution_run_id": "dist_y"})

    async def get(self, url):
        return _FakeStatusErrorResponse(
            422, {"detail": "config invalida: rutas inexistentes"}
        )


async def test_422_en_poll_propaga_detail(monkeypatch, tmp_path):
    monkeypatch.setattr(f"{_MOD}.httpx.AsyncClient", _FakeClientInvalidOnPoll)
    with pytest.raises(RuntimeError) as excinfo:
        await run_distribution_http(
            mode="replay",
            alerts_path=tmp_path / "a.jsonl",
            out_dir=tmp_path / "out",
            config_path=None,
            endpoint=None,
            control_run_id=None,
            backfill_path=None,
            idle_timeout_ms=None,
            timeout_s=5.0,
            base_url="http://x",
        )
    assert "config invalida: rutas inexistentes" in str(excinfo.value)


# --- Hallazgo 3: el timeout tiene que ser diagnosticable (run_id, timeout_s,
# ultimo status visto) y quedar logueado, igual que el camino por subproceso. ---


class _FakeClientNeverTerminal:
    def __init__(self, *args, **kwargs) -> None:
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc) -> None:
        return None

    async def post(self, url, json=None):
        return _FakeResponse(201, {"distribution_run_id": "dist_stuck"})

    async def get(self, url):
        return _FakeResponse(
            200,
            {
                "distribution_run_id": "dist_stuck",
                "status": "running",
                "summary": None,
                "error": None,
            },
        )


async def test_timeout_es_diagnosticable_y_queda_logueado(monkeypatch, tmp_path, caplog):
    monkeypatch.setattr(f"{_MOD}.httpx.AsyncClient", _FakeClientNeverTerminal)
    with caplog.at_level(logging.WARNING, logger=_MOD):
        with pytest.raises(TimeoutError) as excinfo:
            await run_distribution_http(
                mode="replay",
                alerts_path=tmp_path / "a.jsonl",
                out_dir=tmp_path / "out",
                config_path=None,
                endpoint=None,
                control_run_id=None,
                backfill_path=None,
                idle_timeout_ms=None,
                timeout_s=0.05,
                base_url="http://x",
                poll_interval_s=0.01,
            )
    message = str(excinfo.value)
    assert "dist_stuck" in message
    assert "0.05" in message
    assert "running" in message
    assert any("dist_stuck" in record.getMessage() for record in caplog.records)


# --- I2: abandonar el poll (timeout local o cancelacion de la task por el
# runner) debe avisarle al servicio remoto via POST /cancel -- best-effort,
# sin tapar ni reemplazar la excepcion original. Sin esto, el camino HTTP
# diverge del gemelo por subproceso (`_cancel_distribution_task`, que mata al
# hijo): el servicio sigue corriendo y publicando MQTT de un experimento ya
# dado por fallado, y el `POST /api/runs` siguiente ve 409 mientras tanto. ---


def _make_never_terminal_client_tracking_posts(recorder: list[str]):
    class _Client:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc) -> None:
            return None

        async def post(self, url, json=None):
            recorder.append(url)
            if url == "/api/runs":
                return _FakeResponse(201, {"distribution_run_id": "dist_stuck"})
            return _FakeResponse(200, {"ok": True})

        async def get(self, url):
            return _FakeResponse(
                200,
                {
                    "distribution_run_id": "dist_stuck",
                    "status": "running",
                    "summary": None,
                    "error": None,
                },
            )

    return _Client


class _FakeClientCancelPostFails:
    """El POST /api/runs anda bien; el POST /cancel de la limpieza explota."""

    def __init__(self, *args, **kwargs) -> None:
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc) -> None:
        return None

    async def post(self, url, json=None):
        if url == "/api/runs":
            return _FakeResponse(201, {"distribution_run_id": "dist_boom"})
        raise RuntimeError("cancel boom")

    async def get(self, url):
        return _FakeResponse(
            200,
            {
                "distribution_run_id": "dist_boom",
                "status": "running",
                "summary": None,
                "error": None,
            },
        )


async def test_timeout_dispara_cancel_best_effort(monkeypatch, tmp_path):
    posts: list[str] = []
    monkeypatch.setattr(
        f"{_MOD}.httpx.AsyncClient", _make_never_terminal_client_tracking_posts(posts)
    )
    with pytest.raises(TimeoutError):
        await run_distribution_http(
            mode="replay",
            alerts_path=tmp_path / "a.jsonl",
            out_dir=tmp_path / "out",
            config_path=None,
            endpoint=None,
            control_run_id=None,
            backfill_path=None,
            idle_timeout_ms=None,
            timeout_s=0.05,
            base_url="http://x",
            poll_interval_s=0.01,
        )
    assert posts == ["/api/runs", "/api/runs/dist_stuck/cancel"]


async def test_cancelacion_local_dispara_cancel_best_effort_y_propaga(monkeypatch, tmp_path):
    posts: list[str] = []
    monkeypatch.setattr(
        f"{_MOD}.httpx.AsyncClient", _make_never_terminal_client_tracking_posts(posts)
    )
    task = asyncio.create_task(
        run_distribution_http(
            mode="replay",
            alerts_path=tmp_path / "a.jsonl",
            out_dir=tmp_path / "out",
            config_path=None,
            endpoint=None,
            control_run_id=None,
            backfill_path=None,
            idle_timeout_ms=None,
            timeout_s=30.0,
            base_url="http://x",
            poll_interval_s=0.01,
        )
    )
    await asyncio.sleep(0.03)  # deja que el poll arranque y este en vuelo
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert posts == ["/api/runs", "/api/runs/dist_stuck/cancel"]


async def test_timeout_cuando_cancel_best_effort_falla_no_tapa_la_excepcion_original(
    monkeypatch, tmp_path, caplog
):
    monkeypatch.setattr(f"{_MOD}.httpx.AsyncClient", _FakeClientCancelPostFails)
    with caplog.at_level(logging.WARNING, logger=_MOD):
        with pytest.raises(TimeoutError) as excinfo:
            await run_distribution_http(
                mode="replay",
                alerts_path=tmp_path / "a.jsonl",
                out_dir=tmp_path / "out",
                config_path=None,
                endpoint=None,
                control_run_id=None,
                backfill_path=None,
                idle_timeout_ms=None,
                timeout_s=0.05,
                base_url="http://x",
                poll_interval_s=0.01,
            )
    # la excepcion original (timeout, con run_id/timeout_s/ultimo status) llega intacta
    assert "dist_boom" in str(excinfo.value)
    assert "0.05" in str(excinfo.value)
    # y el fallo del POST /cancel best-effort quedo logueado, no silencioso
    assert any("cancel best-effort" in record.getMessage() for record in caplog.records)


# --- Hallazgo 4 (ADR-020 invierte el default: HTTP es el acople, el
# subproceso baja a fallback operativo detras de
# EOVRT_CONSOLE_DISTRIBUTION_TRANSPORT=subprocess). Este bloque es el guard
# de que el default nuevo no se reinvierte -- si alguien vuelve a poner el
# subproceso como default, `test_switch_sin_env_var_usa_http` tiene que
# fallar. ---


def test_switch_sin_env_var_usa_http(monkeypatch):
    """Sin inyeccion ni env var: HTTP es el default (ADR-020)."""
    monkeypatch.delenv("EOVRT_CONSOLE_DISTRIBUTION_TRANSPORT", raising=False)
    caller = runner._resolve_distribution_caller(None)
    assert isinstance(caller, functools.partial)
    assert caller.func is run_distribution_http
    assert caller.keywords["base_url"] == "http://localhost:8082"


def test_switch_con_env_var_subprocess_usa_el_fallback(monkeypatch):
    """`EOVRT_CONSOLE_DISTRIBUTION_TRANSPORT=subprocess` activa el fallback
    operativo por subproceso (ADR-018, derogada como patron de acople pero el
    codigo se conserva)."""
    monkeypatch.setenv("EOVRT_CONSOLE_DISTRIBUTION_TRANSPORT", "subprocess")
    caller = runner._resolve_distribution_caller(None)
    assert caller is runner._default_run_distribution


def test_switch_con_env_var_http_explicito_sigue_usando_http(monkeypatch):
    """Back-compat: un operador que ya tenia `=http` seteado desde antes de
    ADR-020 (cuando era necesario para optar por HTTP) no se rompe -- sigue
    resolviendo a HTTP, ahora simplemente porque no es "subprocess"."""
    monkeypatch.setenv("EOVRT_CONSOLE_DISTRIBUTION_TRANSPORT", "http")
    caller = runner._resolve_distribution_caller(None)
    assert isinstance(caller, functools.partial)
    assert caller.func is run_distribution_http
    assert caller.keywords["base_url"] == "http://localhost:8082"


def test_switch_variantes_no_estrictas_no_activan_el_fallback(monkeypatch):
    """La comparacion contra "subprocess" es estricta: variantes de
    mayusculas/minusculas u otros valores "verdaderos" NO activan el
    fallback -- siguen resolviendo a HTTP, el default."""
    for value in ("SUBPROCESS", "1", "true", "Subprocess"):
        monkeypatch.setenv("EOVRT_CONSOLE_DISTRIBUTION_TRANSPORT", value)
        caller = runner._resolve_distribution_caller(None)
        assert isinstance(caller, functools.partial), value
        assert caller.func is run_distribution_http, value


def test_switch_run_distribution_inyectado_gana_sobre_el_env_var(monkeypatch):
    """La precedencia no cambia con ADR-020: una `run_distribution` inyectada
    explicitamente gana siempre, sin importar el env var (probado con
    `subprocess` seteado, el caso donde el switch por si solo elegiria el
    subproceso -- y aun asi gana la inyeccion)."""
    monkeypatch.setenv("EOVRT_CONSOLE_DISTRIBUTION_TRANSPORT", "subprocess")

    async def _fake(**kwargs):
        return {}

    caller = runner._resolve_distribution_caller(_fake)
    assert caller is _fake


def test_switch_run_distribution_inyectado_gana_sin_env_var(monkeypatch):
    """Misma precedencia, ahora con el default (HTTP, sin env var seteada):
    la inyeccion explicita sigue ganando."""
    monkeypatch.delenv("EOVRT_CONSOLE_DISTRIBUTION_TRANSPORT", raising=False)

    async def _fake(**kwargs):
        return {}

    caller = runner._resolve_distribution_caller(_fake)
    assert caller is _fake
