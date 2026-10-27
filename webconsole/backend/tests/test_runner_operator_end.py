"""Runner: los ganchos aditivos de la demo (`RunHooks`, spec 2026-10-23 §6.4.2).

- los ids de las corridas se publican apenas se conocen (no recién al terminar);
- el cierre por el operador: el `stopped` del media es el fin normal, la
  distribución no se cancela y la corrida cuenta como exitosa si todo cerró bien;
- sin el gancho, un `stopped` sigue siendo una falla (el «Detener» no cambia).
"""
from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

from eovrt_webconsole.experiment.manifest import ExperimentManifest
from eovrt_webconsole.experiment.run_manager import ExperimentRunManager
from eovrt_webconsole.experiment.runner import RunHooks, run_experiment

NOW = datetime(2026, 10, 26, 12, 0, 0, tzinfo=UTC)


def _manifest(tmp_path: Path, *, con_distribucion: bool = True) -> ExperimentManifest:
    runs = {
        "media": {"service": "media-plane", "config": "media.yaml", "mode": "run"},
        "control": {"service": "control-plane", "config": "control.yaml", "mode": "live"},
    }
    if con_distribucion:
        runs["distribution"] = {"service": "alert-distribution", "config": "d.yaml", "mode": "live",
                                "endpoint": "tcp://control-plane:5558"}
    return ExperimentManifest.model_validate({
        "schema_version": "experiment.manifest.v1", "slug": "demo_defensa",
        "runs": runs, "sequencing": "control_first",
    })


def _loader(path: str) -> dict:
    return {"media.yaml": {"ingest": {"plugin": "oak_d", "config": {}}},
            "control.yaml": {"input": {"type": "bus", "bus": {"endpoint": "tcp://mp:5557"}}}}[path]


class Media:
    def __init__(self) -> None:
        self.detenido = asyncio.Event()

    async def launch(self, run_request: dict) -> str:
        return "run_m"

    async def status(self, run_id: str) -> dict:
        return {"status": "stopped" if self.detenido.is_set() else "running"}


class Control:
    def __init__(self, media: Media, *, cierra: bool = True) -> None:
        self.media = media
        self.cierra = cierra

    async def launch(self, config: dict, mode: str, experiment_id: str | None) -> str:
        return "ctl_c"

    async def status(self, control_run_id: str) -> dict:
        cerrado = self.cierra and self.media.detenido.is_set()
        return {"status": "succeeded" if cerrado else "running"}

    async def current(self) -> dict:
        return {"subscribed": True}


def _distribucion(media: Media, registro: list[str], control: Control | None = None):
    """Como el servicio real: cierra con el run_finished que el CONTROL republica en el
    bus de alertas (acá: cuando el control cerró; sin control, cuando paró el media)."""

    def cerro() -> bool:
        if control is None:
            return media.detenido.is_set()
        return control.cierra and media.detenido.is_set()

    async def correr(*, out_dir: Path, **kwargs) -> dict:
        try:
            while not cerro():
                await asyncio.sleep(0.01)
        except asyncio.CancelledError:
            registro.append("cancelada")
            raise
        out_dir.mkdir(parents=True, exist_ok=True)
        summary = {"schema_version": "control.distribution_summary.v1", "counts": {},
                   "source_stats": {"read": 0, "skipped_malformed": 0},
                   "talert_notification_ms": None}
        (out_dir / "distribution_summary.json").write_text(json.dumps(summary))
        registro.append("cerrada")
        return summary
    return correr


async def _correr(tmp_path, hooks, *, media=None, control=None, registro=None, timeout_s=5.0,
                  con_distribucion=True):
    media = media or Media()
    control = control or Control(media)
    registro = registro if registro is not None else []
    tarea = asyncio.create_task(run_experiment(
        _manifest(tmp_path, con_distribucion=con_distribucion),
        media_backend=media, control_backend=control, now=NOW, load_config=_loader,
        run_distribution=_distribucion(media, registro, control), hooks=hooks, timeout_s=timeout_s,
        resolve_run_dir=lambda plane, run_id: tmp_path / plane / run_id,
        dest_root=tmp_path / "runs",
        # Con pausa: los dobles responden sin ceder el loop y, sin pausa, el poll lo
        # monopolizaría (en producción la pausa la pone el setting de la consola).
        poll_interval_s=0.01,
    ))
    return tarea, media, registro


async def test_los_ids_se_publican_apenas_se_conocen(tmp_path):
    vistos: list[dict] = []
    hooks = RunHooks(on_ids=vistos.append)
    tarea, media, _ = await _correr(tmp_path, hooks)
    for _ in range(200):
        if len(vistos) >= 2:
            break
        await asyncio.sleep(0.01)
    assert vistos == [{"control_run_id": "ctl_c"}, {"media_run_id": "run_m"}]
    assert not tarea.done()  # la corrida sigue: los ids llegaron ANTES del final
    hooks.ended_by = "operator"
    media.detenido.set()
    await tarea


async def test_cierre_por_el_operador_es_un_fin_normal(tmp_path):
    hooks = RunHooks(close_timeout_s=2.0)
    tarea, media, registro = await _correr(tmp_path, hooks)
    await asyncio.sleep(0.05)
    hooks.ended_by = "operator"
    media.detenido.set()
    resultado = await tarea
    assert resultado.ok is True
    assert resultado.ended_by == "operator"
    assert resultado.media_status == "stopped"
    assert resultado.distribution_status == "succeeded"
    assert registro == ["cerrada"]  # la distribución NO se canceló: cerró sola
    assert resultado.consolidated_dir is not None


async def test_sin_el_gancho_un_stopped_sigue_siendo_falla(tmp_path):
    tarea, media, registro = await _correr(tmp_path, RunHooks())
    await asyncio.sleep(0.05)
    media.detenido.set()  # «Detener» de la consola: semántica de siempre
    resultado = await tarea
    assert resultado.ok is False
    assert resultado.ended_by is None
    assert resultado.distribution_status == "failed"
    assert resultado.consolidated_dir is None  # sin reporte, como siempre


async def test_un_error_del_media_no_es_un_cierre_del_operador(tmp_path):
    class MediaFalla(Media):
        async def status(self, run_id: str) -> dict:
            return {"status": "failed" if self.detenido.is_set() else "running"}

    hooks = RunHooks()
    media = MediaFalla()
    tarea, media, _ = await _correr(tmp_path, hooks, media=media, control=Control(media))
    await asyncio.sleep(0.05)
    hooks.ended_by = "operator"
    media.detenido.set()
    resultado = await tarea
    assert resultado.ok is False and resultado.ended_by is None


async def test_si_el_control_no_cierra_vence_su_propia_espera(tmp_path):
    hooks = RunHooks(close_timeout_s=0.3)
    media = Media()
    tarea, media, registro = await _correr(
        tmp_path, hooks, media=media, control=Control(media, cierra=False), timeout_s=60.0,
    )
    await asyncio.sleep(0.05)
    hooks.ended_by = "operator"
    media.detenido.set()
    try:
        await asyncio.wait_for(tarea, timeout=5.0)
    except Exception as exc:  # noqa: BLE001
        assert "no llego a un estado terminal" in str(exc)
    else:
        raise AssertionError("debió vencer la espera del control")
    assert registro == ["cancelada"]


async def test_el_manager_publica_los_ids_en_el_estado_mientras_corre(tmp_path):
    manager = ExperimentRunManager()
    media = Media()
    hooks = RunHooks()
    experiment_id = manager.start(
        _manifest(tmp_path), media_backend=media, control_backend=Control(media), now=NOW,
        load_config=_loader, run_distribution=_distribucion(media, []), hooks=hooks,
        resolve_run_dir=lambda plane, run_id: tmp_path / plane / run_id,
        dest_root=tmp_path / "runs", poll_interval_s=0.01,
    )
    for _ in range(200):
        if manager.get(experiment_id).get("media_run_id"):
            break
        await asyncio.sleep(0.01)
    estado = manager.get(experiment_id)
    assert estado["status"] == "running"
    assert estado["control_run_id"] == "ctl_c" and estado["media_run_id"] == "run_m"
    hooks.ended_by = "operator"
    media.detenido.set()
    for _ in range(300):
        if manager.current() is None:
            break
        await asyncio.sleep(0.01)
    final = manager.get(experiment_id)
    assert final["status"] == "succeeded" and final["ended_by"] == "operator"


async def test_cancel_libera_el_slot(tmp_path):
    manager = ExperimentRunManager()
    media = Media()
    experiment_id = manager.start(
        _manifest(tmp_path), media_backend=media, control_backend=Control(media), now=NOW,
        load_config=_loader, run_distribution=_distribucion(media, []),
        resolve_run_dir=lambda plane, run_id: tmp_path / plane / run_id,
        dest_root=tmp_path / "runs", poll_interval_s=0.01,
    )
    await asyncio.sleep(0.05)
    assert manager.cancel("otro") is False
    assert manager.cancel(experiment_id) is True
    for _ in range(200):
        if manager.current() is None:
            break
        await asyncio.sleep(0.01)
    assert manager.current() is None
    assert manager.get(experiment_id)["status"] == "failed"
