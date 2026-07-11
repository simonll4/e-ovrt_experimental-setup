"""Runner: rama live (control primero, suscripcion antes del disparo del media), spec 44 SS3."""
from __future__ import annotations

from datetime import datetime, timezone

import httpx
import pytest

from eovrt_webconsole.experiment.control_backend import ControlPlaneBackend
from eovrt_webconsole.experiment.manifest import ExperimentManifest
from eovrt_webconsole.experiment.runner import (
    ExperimentTimeout,
    SubscriptionNotConfirmed,
    run_experiment,
)
from eovrt_webconsole.run_backend import RunBackend
from tests.fake_control_service import FakeControlState, make_fake_control_service
from tests.fake_service import FakeState, make_fake_service

NOW = datetime(2026, 7, 12, 14, 0, 0, tzinfo=timezone.utc)

MEDIA_CONFIG = {"ingest": {"type": "rtsp", "path": "camera1"}, "prompts": {"ref": "eind_v1"}}
CONTROL_CONFIG = {"pattern_set": "cr01_cr02_v2"}


def _load_config(path: str) -> dict:
    if path == "media.yaml":
        return dict(MEDIA_CONFIG)
    if path == "control.yaml":
        return dict(CONTROL_CONFIG)
    raise AssertionError(f"config no esperada: {path}")


def _build_manifest(*, sequencing: str = "control_first", mode: str = "live") -> ExperimentManifest:
    return ExperimentManifest.model_validate(
        {
            "schema_version": "experiment.manifest.v1",
            "slug": "d1",
            "runs": {
                "media": {"service": "http://media", "config": "media.yaml", "mode": "run"},
                "control": {"service": "http://control", "config": "control.yaml", "mode": mode},
            },
            "sequencing": sequencing,
            "report": {},
            "frozen": {},
        }
    )


class RecordingMediaBackend:
    """Envuelve RunBackend (media-plane): status() es terminal de inmediato.

    Igual que en test_runner_dbe_replay.py: el fake real (tests/fake_service.py,
    no editable) no transiciona un run recien lanzado a un estado terminal por
    si solo (siempre 'running' hasta 'run_done_1' hardcodeado). Este wrapper
    ademas registra el orden de eventos para el assert de secuencia
    control-primero.
    """

    def __init__(
        self, backend: RunBackend, events: list, terminal_status: str = "succeeded"
    ) -> None:
        self._backend = backend
        self._events = events
        self._terminal_status = terminal_status

    async def launch(self, run_request: dict) -> str:
        run_id = await self._backend.launch(run_request)
        self._events.append(("media_launch", run_id))
        return run_id

    async def status(self, run_id: str) -> dict:
        self._events.append(("media_status", run_id))
        return {"run_id": run_id, "status": self._terminal_status, "summary": {}}


class RecordingControlBackend:
    """Envuelve ControlPlaneBackend y registra el orden de eventos.

    El evento clave es 'control_subscribed': se agrega cuando el runner
    consulta current() para confirmar que el BusSource ya esta suscripto,
    ANTES de que se dispare el media. Es la base del assert de orden
    discriminante: si el runner disparase el media antes de confirmar la
    suscripcion, este evento no existiria todavia (o aparecera despues del
    media_launch) y el assert de indices fallaria.
    """

    def __init__(self, backend: ControlPlaneBackend, events: list) -> None:
        self._backend = backend
        self._events = events

    async def launch(self, config: dict, mode: str, experiment_id: str | None) -> str:
        run_id = await self._backend.launch(config, mode=mode, experiment_id=experiment_id)
        self._events.append(("control_launch", mode))
        return run_id

    async def current(self) -> dict:
        result = await self._backend.current()
        self._events.append(("control_subscribed", result.get("subscribed")))
        return result

    async def status(self, control_run_id: str) -> dict:
        return await self._backend.status(control_run_id)


@pytest.fixture
def media_backend():
    state = FakeState()
    transport = httpx.ASGITransport(app=make_fake_service(state))
    http = httpx.AsyncClient(base_url="http://media", transport=transport)
    return RunBackend(http), state


@pytest.fixture
def control_backend():
    state = FakeControlState()
    transport = httpx.ASGITransport(app=make_fake_control_service(state))
    http = httpx.AsyncClient(base_url="http://control", transport=transport)
    return ControlPlaneBackend(http), state


async def test_live_control_subscribed_before_media_launch(media_backend, control_backend):
    real_media, media_state = media_backend
    real_control, control_state = control_backend
    control_state.finish_status = "succeeded"

    events: list = []
    media = RecordingMediaBackend(real_media, events)
    control = RecordingControlBackend(real_control, events)

    result = await run_experiment(
        _build_manifest(),
        media_backend=media,
        control_backend=control,
        now=NOW,
        load_config=_load_config,
    )

    assert result.ok
    assert result.experiment_id.startswith("exp_")
    assert result.media_run_id and result.control_run_id
    assert result.media_status == "succeeded"
    assert result.control_status == "succeeded"

    # orden: la confirmacion de suscripcion del control debe preceder al
    # disparo del media (invariante no negociable: PUB/SUB pierde lo
    # publicado antes de la suscripcion). Aserto por indice de evento, no
    # por timing.
    subscribed_idx = events.index(("control_subscribed", True))
    media_launch_idx = next(i for i, e in enumerate(events) if e[0] == "media_launch")
    assert subscribed_idx < media_launch_idx

    # el control-plane se dispara primero, en mode=live
    assert events[0] == ("control_launch", "live")

    # experiment_id propagado a ambos payloads
    assert media_state.launched[0]["experiment_id"] == result.experiment_id
    assert control_state.received_experiment_id == result.experiment_id
    assert control_state.received_mode == "live"

    # bus habilitado en el payload del media (spec 44 SS3 / doc 50 SS5.1)
    assert media_state.launched[0]["bus"]["enabled"] is True


async def test_live_sequencing_mismatch_is_rejected():
    """sequencing y runs.control.mode deben coincidir (regla de reconciliacion).

    mode 'live' implica sequencing 'control_first'; declarar 'media_first'
    junto con mode 'live' es una contradiccion del manifiesto y el runner
    debe rechazarla con un error claro en vez de arrancar una secuencia
    ambigua o resolverla en silencio a favor de uno de los dos campos.
    """
    manifest = _build_manifest(sequencing="media_first", mode="live")
    with pytest.raises(ValueError, match="sequencing"):
        await run_experiment(
            manifest,
            media_backend=None,  # type: ignore[arg-type]
            control_backend=None,  # type: ignore[arg-type]
            now=NOW,
            load_config=_load_config,
        )


async def test_missing_plane_key_raises_clear_value_error():
    """Un manifiesto sin la clave 'control' (o 'media') en runs debe fallar con
    un ValueError claro, no con un KeyError crudo al indexar runs["control"].

    Se valida antes de cualquier llamada HTTP: media_backend/control_backend
    se pasan en None para probar que ni siquiera se llegan a usar.
    """
    manifest = ExperimentManifest.model_validate(
        {
            "schema_version": "experiment.manifest.v1",
            "slug": "d1",
            "runs": {
                "media": {"service": "http://media", "config": "media.yaml", "mode": "run"},
                # falta "control"
            },
            "sequencing": "control_first",
            "report": {},
            "frozen": {},
        }
    )
    with pytest.raises(ValueError, match="control"):
        await run_experiment(
            manifest,
            media_backend=None,  # type: ignore[arg-type]
            control_backend=None,  # type: ignore[arg-type]
            now=NOW,
            load_config=_load_config,
        )


async def test_live_subscription_not_confirmed_blocks_media_launch(media_backend, control_backend):
    """Si current() reporta subscribed=False tras el 201 live, se aborta ANTES del media.

    Guard mutation-resistant (revision final Tarea 5): sin este test, borrar el
    `if not current.get("subscribed"): raise SubscriptionNotConfirmed(...)` en
    runner.py deja pasar toda la suite igual -- el media se lanzaria sin
    confirmar la suscripcion (carrera silenciosa PUB/SUB). Este test fuerza
    subscribed=False via `FakeControlState.force_unsubscribed` (el 201 se
    devuelve igual, solo cambia lo que reporta current()) y asserta que el
    media NUNCA se lanza.
    """
    real_media, media_state = media_backend
    real_control, control_state = control_backend
    control_state.force_unsubscribed = True

    events: list = []
    media = RecordingMediaBackend(real_media, events)
    control = RecordingControlBackend(real_control, events)

    with pytest.raises(SubscriptionNotConfirmed):
        await run_experiment(
            _build_manifest(),
            media_backend=media,
            control_backend=control,
            now=NOW,
            load_config=_load_config,
        )

    # el media nunca se lanza si la suscripcion no se confirma
    assert media_state.launched == []
    assert not any(e[0] == "media_launch" for e in events)


async def test_live_timeout_raises_when_control_never_terminal(media_backend, control_backend):
    """Si el control nunca reporta un estado terminal, con timeout_s chico debe
    levantar ExperimentTimeout en vez de colgarse (cierra el guard sin testear
    de _poll_until_terminal)."""
    real_media, media_state = media_backend
    real_control, control_state = control_backend
    # No seteamos control_state.finish_status: GET /api/runs/{id} para el run
    # activo siempre devuelve status "running" (ver fake_control_service.py),
    # asi que el poll del control jamas ve un estado terminal.

    events: list = []
    media = RecordingMediaBackend(real_media, events)
    control = RecordingControlBackend(real_control, events)

    with pytest.raises(ExperimentTimeout):
        await run_experiment(
            _build_manifest(),
            media_backend=media,
            control_backend=control,
            now=NOW,
            poll_interval_s=0.0,
            timeout_s=-1.0,
            load_config=_load_config,
        )
