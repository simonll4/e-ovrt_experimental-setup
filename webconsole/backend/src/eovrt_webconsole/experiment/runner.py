"""Runner reproducible del experimento (ADR-004, spec 44 SS3).

Lee el manifiesto paraguas, genera/toma el experiment_id, y dispara los dos
planos por HTTP en el orden correcto. Cubre las dos ramas:
- DBE-replay (`runs.control.mode == "replay"`): media-plane primero, esperar
  a que termine, control-plane despues en modo replay sobre el
  detections.jsonl del run de media.
- live (`runs.control.mode == "live"`): control-plane primero -- su 201
  implica que el BusSource ya esta suscripto (PUB/SUB pierde lo publicado
  antes de la suscripcion) -- recien despues se dispara el media-plane con
  el bus habilitado.
"""
from __future__ import annotations

import asyncio
import functools
import json
import logging
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Protocol

import yaml
from pydantic import BaseModel

from eovrt_webconsole.experiment.consolidation import consolidate_experiment
from eovrt_webconsole.experiment.manifest import ExperimentManifest, generate_experiment_id
from eovrt_webconsole.experiment.report import write_report

logger = logging.getLogger(__name__)

# Estados terminales de un run en cualquiera de los dos planos. "stopped" es
# el resultado real y distinto de un stop manual explicito (boton "Detener"
# de la consola) -- ver eovrt_media/service/run_manager.py: solo degrada a
# "failed" si el stop_cause fue "stalled". Sin "stopped" aca, un experimento
# detenido a mano queda "running" en el tracker del BFF hasta que expira el
# timeout_s (300s por default) aunque ningun plano tenga una corrida activa
# -- bug real, bloqueaba "Lanzar experimento" con "hay un experimento en
# curso" (2026-07-25).
TERMINAL_STATUSES = frozenset({"succeeded", "failed", "error", "stopped"})

# Evalua alertas del control-plane contra un ground truth temporal (spec 43
# SS6). Firma: (alerts_path, ground_truth_path, output_path, detections_path,
# patterns_path) -> dict de la evaluacion (ya persistido en output_path por el
# propio callable) o None si la evaluacion no se pudo correr. Inyectable para
# tests; el default de produccion invoca la CLI `eovrt-control evaluate-alerts`
# (ver `_default_evaluate_temporal`).
EvaluateTemporal = Callable[[Path, Path, Path, Path | None, Path | None], dict | None]

LoadConfig = Callable[[str], dict]
# Resuelve el directorio runs/<run_id>/ de un plano ("media" | "control") a
# partir del run_id devuelto por ese plano. Inyectable para tests (dirs
# sinteticos); el default de produccion es la convencion de workspace hermano
# (ver CLAUDE.md raiz: los planos son repos hermanos de este).
ResolveRunDir = Callable[[str, str], Path]


class ExperimentTimeout(Exception):
    """El polling de un run supero timeout_s sin llegar a un estado terminal."""


class MediaBackendProtocol(Protocol):
    async def launch(self, run_request: dict) -> str: ...
    async def status(self, run_id: str) -> dict: ...


class ControlBackendProtocol(Protocol):
    async def launch(self, config: dict, mode: str, experiment_id: str | None) -> str: ...
    async def status(self, control_run_id: str) -> dict: ...
    async def current(self) -> dict: ...


class ExperimentResult(BaseModel):
    """Resultado consolidado de las dos corridas (media + control)."""

    experiment_id: str
    media_run_id: str | None
    control_run_id: str | None
    media_status: str | None
    control_status: str | None
    ok: bool
    # Paso final post-run (Tarea 4): set solo si ambas corridas terminaron OK
    # y la consolidacion + el reporte se generaron sin error.
    consolidated_dir: str | None = None
    report_path: str | None = None


def _default_load_config(config_path: str) -> dict:
    """Carga por defecto: yaml.safe_load del path tal cual viene del manifiesto.

    Para uso real (manifiesto en disco) el llamador puede inyectar un
    load_config que resuelva rutas relativas al directorio del manifiesto.
    """
    return yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))


def _repo_root() -> Path:
    """Raiz de e-ovrt_experimental-setup, derivada de la ubicacion de este archivo."""
    # runner.py -> experiment -> eovrt_webconsole -> src -> backend -> webconsole -> repo_root
    return Path(__file__).resolve().parents[5]


def _default_resolve_run_dir(plane: str, run_id: str) -> Path:
    """Convencion por defecto de layout de workspace (ver CLAUDE.md raiz):
    los planos son repos hermanos de e-ovrt_experimental-setup, y cada uno
    persiste sus corridas en `runs/<run_id>/` dentro de su propio repo."""
    return _repo_root().parent / f"e-ovrt_{plane}-plane" / "runs" / run_id


def _default_dest_root() -> Path:
    """dest_root por defecto para la consolidacion: `<repo_root>/runs`."""
    return _repo_root() / "runs"


async def _poll_until_terminal(
    get_status: Callable[[str], Any],
    run_id: str,
    *,
    poll_interval_s: float,
    timeout_s: float,
) -> dict:
    """Poll de un run hasta que su status sea terminal, con timeout."""
    deadline = time.monotonic() + timeout_s
    while True:
        summary = await get_status(run_id)
        if summary.get("status") in TERMINAL_STATUSES:
            return summary
        if time.monotonic() > deadline:
            raise ExperimentTimeout(
                f"run {run_id} no llego a un estado terminal en {timeout_s}s "
                f"(ultimo status={summary.get('status')!r})"
            )
        if poll_interval_s > 0:
            await asyncio.sleep(poll_interval_s)


# Regla de reconciliacion entre `sequencing` y `runs.control.mode` (nota de
# revision de la Tarea 3): la fuente de verdad OPERATIVA para el dispatch es
# `runs.control.mode` -- es el campo que decide que llamadas HTTP hace el
# runner y en que orden (ver run_experiment). `sequencing` es un campo
# declarativo del manifiesto que debe coincidir con esa decision; no se
# resuelve en silencio a favor de uno de los dos si difieren, se rechaza el
# manifiesto con un error claro.
_SEQUENCING_FOR_CONTROL_MODE = {"live": "control_first", "replay": "media_first"}


def _validate_sequencing(sequencing: str, control_mode: str) -> None:
    """Valida que `sequencing` no contradiga `runs.control.mode`."""
    expected = _SEQUENCING_FOR_CONTROL_MODE.get(control_mode)
    if expected is not None and sequencing != expected:
        raise ValueError(
            f"sequencing '{sequencing}' contradice runs.control.mode '{control_mode}' "
            f"(se esperaba '{expected}')"
        )


def _validate_planes_present(runs: dict[str, Any]) -> None:
    """Valida que `manifest.runs` tenga las dos claves de plano requeridas.

    Sin este chequeo, indexar `runs["media"]` / `runs["control"]` cuando falta
    una clave levanta un `KeyError` crudo antes de cualquier llamada HTTP. Se
    valida antes de tocar ningun backend para dar un error claro (que plano
    falta) en vez de un traceback opaco.
    """
    faltantes = [plano for plano in ("media", "control") if plano not in runs]
    if faltantes:
        raise ValueError(
            f"manifiesto invalido: falta(n) el/los plano(s) {faltantes} en manifest.runs"
        )


def _inject_source_id(media_config: dict, clip_id: str | None) -> dict:
    """Inyecta `ingest.config.source_id = clip_id` (spec 43 SS6), sin pisar un
    `source_id` explicito ya presente en la config (el explicito gana).

    No muta `media_config` in-place (ni sus dicts anidados `ingest`/`config`):
    el llamador puede reusar el dict devuelto por `loader()` en otro contexto
    (p.ej. anti-drift/sent_config) sin que esta inyeccion lo contamine.
    """
    if not clip_id:
        return media_config
    ingest = media_config.get("ingest")
    if not isinstance(ingest, dict):
        return media_config
    config = dict(ingest.get("config") or {})
    if "source_id" not in config:
        config["source_id"] = clip_id
    return {**media_config, "ingest": {**ingest, "config": config}}


_EVALUATE_ALERTS_CMD = ("eovrt-control", "evaluate-alerts")


@functools.lru_cache(maxsize=1)
def _evaluate_alerts_supports_extra_flags() -> bool:
    """Sonda si la CLI instalada de `eovrt-control evaluate-alerts` ya trae
    los flags `--detections`/`--patterns` (fix paralelo del control-plane, ver
    docstring de `_default_evaluate_temporal`). Cacheado: se corre `--help`
    una sola vez por proceso. Si la CLI no esta instalada o falla la sonda,
    se asume que no los soporta (False) y se hace el llamado sin ellos.
    """
    try:
        probe = subprocess.run(
            [*_EVALUATE_ALERTS_CMD, "--help"],
            capture_output=True, text=True, timeout=10, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return "--detections" in probe.stdout and "--patterns" in probe.stdout


def _default_evaluate_temporal(
    alerts_path: Path,
    ground_truth_path: Path,
    output_path: Path,
    detections_path: Path | None = None,
    patterns_path: Path | None = None,
) -> dict | None:
    """Corre `eovrt-control evaluate-alerts` como subproceso (spec 43 SS6).

    No hay endpoint HTTP para esto en el control-plane (:8081 solo expone
    /api/runs, /api/config -- ver `control_backend.py`); la evaluacion
    temporal contra ground truth es CLI-only (`eovrt_control.cli:evaluate_alerts`),
    asi que el runner la invoca por subproceso en vez de por HTTP, a
    diferencia del resto de la orquestacion (media/control por RunBackend/
    ControlPlaneBackend).

    Firma actual de la CLI (2026-07-11): `alerts` y `ground_truth` son
    posicionales, `--output/-o` es el unico flag. Los flags `--detections`/
    `--patterns` estan en desarrollo en paralelo en el control-plane (todavia
    no aterrizaron); se sondan con `--help` (`_evaluate_alerts_supports_extra_flags`,
    cacheado) y solo se agregan al comando si la CLI instalada los soporta Y
    el path correspondiente esta disponible. Mientras el fix paralelo no
    aterrice, la evaluacion corre igual, solo que sin cruzar detections/patterns.
    """
    cmd = [*_EVALUATE_ALERTS_CMD, str(alerts_path), str(ground_truth_path),
           "--output", str(output_path)]
    if _evaluate_alerts_supports_extra_flags():
        if detections_path is not None:
            cmd.extend(["--detections", str(detections_path)])
        if patterns_path is not None:
            cmd.extend(["--patterns", str(patterns_path)])
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=300)
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning("evaluate-alerts fallo (%s): %s", " ".join(cmd), exc)
        return None
    if not output_path.is_file():
        logger.warning("evaluate-alerts no escribio %s", output_path)
        return None
    return json.loads(output_path.read_text(encoding="utf-8"))


def _detections_path_for(media_run_id: str, media_summary: dict) -> str:
    """Deriva la ruta del detections.jsonl del run de media.

    Preferencia: si el summary del media-plane declara detections_path lo
    usamos tal cual; si no, aplicamos la convencion de workspace hermano
    (`_default_resolve_run_dir`) para derivar una ruta ABSOLUTA.

    El control-plane recibe la config por payload (ADR-009), lo que exige
    `input.path` absoluto (`_PAYLOAD_PATH_FIELDS` en config.py del
    control-plane); el fallback relativo `runs/<run_id>/detections.jsonl`
    resuelve contra el cwd del proceso que lo interpreta, que en topologia
    real (media-plane y control-plane como servicios separados, posiblemente
    en hosts/cwd distintos) no es el mismo que el del media-plane que escribio
    el archivo. Ver hallazgo del smoke DBE-replay real (2026-07-12).
    """
    nested = media_summary.get("summary") or {}
    declared = media_summary.get("detections_path") or nested.get("detections_path")
    if declared:
        return declared
    return str(_default_resolve_run_dir("media", media_run_id) / "detections.jsonl")


async def run_experiment(
    manifest: ExperimentManifest,
    *,
    media_backend: MediaBackendProtocol,
    control_backend: ControlBackendProtocol,
    now: datetime,
    poll_interval_s: float = 0.0,
    timeout_s: float = 300.0,
    load_config: LoadConfig | None = None,
    resolve_run_dir: ResolveRunDir | None = None,
    dest_root: Path | str | None = None,
    evaluate_temporal: EvaluateTemporal | None = None,
) -> ExperimentResult:
    """Orquesta el experimento paraguas segun el modo del control-plane.

    DBE-replay (`runs.control.mode == "replay"`): media-plane primero, se
    espera a que termine, y recien entonces se dispara el control-plane en
    modo replay apuntando al detections.jsonl del run de media.

    live (`runs.control.mode == "live"`): control-plane primero -- su 201
    implica que el BusSource ya esta suscripto -- y recien entonces se
    dispara el media-plane con el bus habilitado. Ver `_run_live`.

    `manifest.sequencing` se valida contra `runs.control.mode` antes de
    dispatchear (regla en `_validate_sequencing`): si contradicen se rechaza
    el manifiesto en vez de arrancar una secuencia ambigua.

    Paso final (Tarea 4, post-run): si ambas corridas terminan OK se invoca
    `consolidate_experiment` + `write_report` (`manifest.report` es siempre
    un dict presente en el manifiesto -- default `{}` -- asi que su sola
    presencia se interpreta como opt-in y el paso corre siempre que el
    resultado sea exitoso; no hay hoy un flag para desactivarlo). Es un paso
    protegido (`_consolidate_and_report`): si falla no tumba la corrida.
    """
    experiment_id = manifest.experiment_id or generate_experiment_id(manifest.slug, now)
    loader = load_config or _default_load_config
    resolver = resolve_run_dir or _default_resolve_run_dir
    resolved_dest_root = Path(dest_root) if dest_root is not None else _default_dest_root()

    _validate_planes_present(manifest.runs)
    control_run = manifest.runs["control"]
    _validate_sequencing(manifest.sequencing, control_run.mode)

    if control_run.mode == "replay":
        result = await _run_dbe_replay(
            manifest,
            experiment_id,
            media_backend=media_backend,
            control_backend=control_backend,
            poll_interval_s=poll_interval_s,
            timeout_s=timeout_s,
            loader=loader,
        )
    elif control_run.mode == "live":
        result = await _run_live(
            manifest,
            experiment_id,
            media_backend=media_backend,
            control_backend=control_backend,
            poll_interval_s=poll_interval_s,
            timeout_s=timeout_s,
            loader=loader,
        )
    else:
        raise NotImplementedError(f"modo de control '{control_run.mode}' no soportado")

    if not result.ok:
        # Si cualquiera de las dos corridas fallo, no hay artefactos
        # completos que consolidar: se deja consolidated_dir/report_path en None.
        return result

    manifest_effective = manifest.model_dump(mode="json")
    manifest_effective["experiment_id"] = experiment_id

    return await _consolidate_and_report(
        result,
        manifest_effective=manifest_effective,
        resolve_run_dir=resolver,
        dest_root=resolved_dest_root,
        evaluate_temporal=evaluate_temporal or _default_evaluate_temporal,
    )


def _control_patterns_file_path(effective_config_path: Path) -> Path:
    """Lee `patterns.file` de `control/effective_config.yaml` (ya copiado al
    consolidado) para ubicar el YAML de definicion de patrones real usado por
    la corrida de control -- ver nota en `_run_temporal_evaluation`.

    Devuelve un `Path` (existente o no); el llamador decide con `.is_file()`
    si lo pasa al subproceso. Si el archivo no existe o no se puede parsear,
    devuelve un path inexistente (el guard `.is_file()` del llamador se
    encarga de omitir el flag sin romper la evaluacion).
    """
    if not effective_config_path.is_file():
        return effective_config_path
    try:
        data = yaml.safe_load(effective_config_path.read_text(encoding="utf-8")) or {}
        patterns_file = (data.get("patterns") or {}).get("file")
    except (OSError, yaml.YAMLError):
        return effective_config_path
    if not patterns_file:
        return effective_config_path
    return Path(patterns_file)


def _run_temporal_evaluation(
    evaluate_temporal: EvaluateTemporal,
    *,
    consolidated_dir: Path,
    media_run_dir: Path,
    ground_truth: str,
) -> None:
    """Corre la evaluacion temporal post-replay y persiste su salida en el
    consolidado (spec 43 SS6), si el manifiesto declara `ground_truth`.

    Insumos (todos ya estan disponibles en este punto -- se llama despues de
    `consolidate_experiment`):
    - `alerts_path`: `control/alerts.jsonl` ya copiado al consolidado.
    - `ground_truth_path`: el path del manifiesto, resuelto igual que
      `runs.*.config` (relativo al cwd del proceso, o absoluto).
    - `detections_path`: el `detections.jsonl` pesado del media-plane (no se
      copia al consolidado -- ADR-014 -- pero para el fix paralelo del
      control-plane el subproceso lo lee directo del `runs/` del media-plane).
    - `patterns_path`: el YAML de definicion de patrones (`pattern_set`) que
      uso la corrida de control, resuelto desde `patterns.file` en
      `control/effective_config.yaml` (ya copiado al consolidado). Verificado
      contra la CLI real (smoke DBE-replay, 2026-07-12): `evaluate-alerts
      --patterns` espera ese YAML (`load_patterns_file`/`PatternsFile`), NO el
      `pattern_events.jsonl` (eventos ya emitidos, formato JSONL) que se
      asumia antes de correr contra servicios reales -- pasarle el JSONL hace
      que el subproceso explote (yaml.safe_load sobre JSONL). Si
      `effective_config.yaml` falta o no trae `patterns.file`, se omite el
      flag (mismo comportamiento que si la CLI no lo soportara).

    La salida se escribe en `control/temporal_evaluation.json` dentro del
    consolidado -- `report._temporal_evaluation` la busca ahi (mismo patron
    que `media/eval_perception.json` para las metricas de percepcion).
    """
    alerts_path = consolidated_dir / "control" / "alerts.jsonl"
    patterns_path = _control_patterns_file_path(consolidated_dir / "control" / "effective_config.yaml")
    detections_path = media_run_dir / "detections.jsonl"
    output_path = consolidated_dir / "control" / "temporal_evaluation.json"

    evaluate_temporal(
        alerts_path,
        Path(ground_truth),
        output_path,
        detections_path if detections_path.is_file() else None,
        patterns_path if patterns_path.is_file() else None,
    )


async def _consolidate_and_report(
    result: ExperimentResult,
    *,
    manifest_effective: dict,
    resolve_run_dir: ResolveRunDir,
    dest_root: Path,
    evaluate_temporal: EvaluateTemporal,
) -> ExperimentResult:
    """Paso final protegido: consolida + reporta un experimento ya exitoso.

    No debe tumbar la corrida si la consolidacion o el reporte fallan (dirs
    no resolubles, IO rota, etc.): se logea una advertencia y se devuelve el
    `result` original (con consolidated_dir/report_path en None), preservando
    `result.ok` tal cual refleja la corrida real. La evaluacion temporal
    (`_run_temporal_evaluation`) corre dentro de este mismo bloque protegido:
    si `ground_truth` no esta en el manifiesto, se saltea (comportamiento
    actual intacto); si esta pero la evaluacion falla, no tumba el reporte
    (queda sin `temporal_evaluation.json`, el reporte cae al fallback
    `no_ground_truth` de todas formas).
    """
    try:
        media_run_dir = resolve_run_dir("media", result.media_run_id)
        control_run_dir = resolve_run_dir("control", result.control_run_id)
        consolidated_dir = consolidate_experiment(
            result.experiment_id,
            media_run_dir=media_run_dir,
            control_run_dir=control_run_dir,
            manifest_effective=manifest_effective,
            dest_root=dest_root,
        )
        ground_truth = manifest_effective.get("ground_truth")
        if ground_truth:
            _run_temporal_evaluation(
                evaluate_temporal,
                consolidated_dir=consolidated_dir,
                media_run_dir=media_run_dir,
                ground_truth=ground_truth,
            )
        report_json_path, _report_md_path = write_report(consolidated_dir)
    except Exception:
        logger.warning(
            "post-run: fallo la consolidacion/reporte del experimento %s "
            "(no afecta el resultado de la corrida)",
            result.experiment_id,
            exc_info=True,
        )
        return result

    return result.model_copy(
        update={
            "consolidated_dir": str(consolidated_dir),
            "report_path": str(report_json_path),
        }
    )


async def _run_dbe_replay(
    manifest: ExperimentManifest,
    experiment_id: str,
    *,
    media_backend: MediaBackendProtocol,
    control_backend: ControlBackendProtocol,
    poll_interval_s: float,
    timeout_s: float,
    loader: LoadConfig,
) -> ExperimentResult:
    media_run = manifest.runs["media"]
    control_run = manifest.runs["control"]

    media_config = dict(loader(media_run.config))
    media_config["experiment_id"] = experiment_id
    media_config = _inject_source_id(media_config, manifest.clip_id)

    media_run_id = await media_backend.launch(media_config)
    media_summary = await _poll_until_terminal(
        media_backend.status, media_run_id, poll_interval_s=poll_interval_s, timeout_s=timeout_s
    )
    media_status = media_summary.get("status")

    if media_status != "succeeded":
        # Falla temprana: nunca se dispara el control-plane.
        return ExperimentResult(
            experiment_id=experiment_id,
            media_run_id=media_run_id,
            control_run_id=None,
            media_status=media_status,
            control_status=None,
            ok=False,
        )

    detections_path = _detections_path_for(media_run_id, media_summary)
    control_config = dict(loader(control_run.config))
    control_config["experiment_id"] = experiment_id
    control_config["input"] = {"type": "media_jsonl", "path": detections_path}

    control_run_id = await control_backend.launch(
        control_config, mode="replay", experiment_id=experiment_id
    )
    control_summary = await _poll_until_terminal(
        control_backend.status,
        control_run_id,
        poll_interval_s=poll_interval_s,
        timeout_s=timeout_s,
    )
    control_status = control_summary.get("status")

    return ExperimentResult(
        experiment_id=experiment_id,
        media_run_id=media_run_id,
        control_run_id=control_run_id,
        media_status=media_status,
        control_status=control_status,
        ok=media_status == "succeeded" and control_status == "succeeded",
    )


class SubscriptionNotConfirmed(Exception):
    """El control-plane no confirmo subscribed=True tras el 201 de live.

    Invariante no negociable (doc 50 SS5.1): PUB/SUB pierde lo publicado
    antes de la suscripcion, asi que el runner NO debe disparar el media
    si esto no se puede confirmar.
    """


async def _run_live(
    manifest: ExperimentManifest,
    experiment_id: str,
    *,
    media_backend: MediaBackendProtocol,
    control_backend: ControlBackendProtocol,
    poll_interval_s: float,
    timeout_s: float,
    loader: LoadConfig,
) -> ExperimentResult:
    """Rama live: control-plane primero, media-plane recien despues.

    Orden no negociable (spec 40 SS3.2 / doc 50 SS5.1): POST al control-plane
    en mode=live primero -- su 201 implica que el BusSource ya esta
    suscripto -- y solo entonces POST al media-plane con bus.enabled=true.
    El control cierra 1:1 con el media (run_finished); se hace poll de
    ambos hasta un estado terminal.
    """
    media_run = manifest.runs["media"]
    control_run = manifest.runs["control"]

    control_config = dict(loader(control_run.config))
    control_config["experiment_id"] = experiment_id
    # Fusion, NO reemplazo: el runner impone el transporte (`type='bus'`) pero
    # el payload conserva sus parametros de bus (endpoint, topics, timeouts).
    # `InputSection` del control-plane exige `input.bus` cuando type='bus' y
    # `endpoint` no tiene default, asi que pisar el dict entero deja un payload
    # invalido y el 422 mata el experimento antes de lanzar nada.
    control_config["input"] = {**dict(control_config.get("input") or {}), "type": "bus"}

    control_run_id = await control_backend.launch(
        control_config, mode="live", experiment_id=experiment_id
    )

    # Confirmacion explicita de la invariante antes de tocar el media: el
    # 201 ya implica suscripto, pero lo verificamos con current() en vez de
    # confiar ciegamente en el codigo de estado.
    current = await control_backend.current()
    if not current.get("subscribed"):
        raise SubscriptionNotConfirmed(
            f"control-plane run {control_run_id} no reporta subscribed=True tras el 201; "
            "se aborta el disparo del media (invariante de orden violada)"
        )

    media_config = dict(loader(media_run.config))
    media_config["experiment_id"] = experiment_id
    media_config["bus"] = {"enabled": True}
    media_config = _inject_source_id(media_config, manifest.clip_id)

    media_run_id = await media_backend.launch(media_config)

    media_summary = await _poll_until_terminal(
        media_backend.status, media_run_id, poll_interval_s=poll_interval_s, timeout_s=timeout_s
    )
    control_summary = await _poll_until_terminal(
        control_backend.status,
        control_run_id,
        poll_interval_s=poll_interval_s,
        timeout_s=timeout_s,
    )
    media_status = media_summary.get("status")
    control_status = control_summary.get("status")

    return ExperimentResult(
        experiment_id=experiment_id,
        media_run_id=media_run_id,
        control_run_id=control_run_id,
        media_status=media_status,
        control_status=control_status,
        ok=media_status == "succeeded" and control_status == "succeeded",
    )
