"""Orquestación: marcas -> ventana -> clip_id -> prepare_clip.sh -> clip.yaml.

Reglas del spec §7 que se implementan acá:
- clip_id explícito = REGENERACIÓN: sobrescribe e invalida la pre-anotación
  vieja (D9) renombrándola a *.stale — el XML viejo son cajas de un video
  que ya no existe.
- Sin clip_id: se toma el siguiente libre (nunca pisa por accidente).
- El master nunca se toca (D8): prepare_clip.sh solo lo lee.
"""

from __future__ import annotations

from pathlib import Path

from eovrt_webconsole.clips.clip_yaml import write_clip_yaml
from eovrt_webconsole.clips.naming import next_clip_id, scenario_from_master
from eovrt_webconsole.clips.trim import run_prepare_clip
from eovrt_webconsole.clips.window import compute_window, compute_window_multi
from eovrt_webconsole.recording.probe import measure


class InvalidRequest(ValueError):
    pass


def _invalidate_preann(preann_dir: Path, clip_id: str) -> list[str]:
    invalidated = []
    for name in (f"{clip_id}.xml", f"{clip_id}.preview.mp4"):
        path = preann_dir / name
        if path.is_file():
            path.replace(path.with_name(name + ".stale"))
            invalidated.append(f"preann/{name}")
    return invalidated


def generate_clip(
    *,
    raw_dir: Path,
    videos_dir: Path,
    script: Path,
    master_name: str,
    marks: list[float],
    scenario: str | None = None,
    clip_id: str | None = None,
) -> dict:
    if Path(master_name).name != master_name:
        raise InvalidRequest(f"nombre de master inválido: {master_name!r}")
    master = raw_dir / master_name
    if not master.is_file():
        raise InvalidRequest(f"master inexistente: {master_name}")

    scenario = scenario or scenario_from_master(master_name)
    if scenario is None:
        raise InvalidRequest(
            f"{master_name} no sigue el patrón de toma (P1-a-take2.mp4): "
            "indicá el escenario a mano"
        )

    measured = measure(master)  # ProbeError si el master no es video legible
    master_duration_s = measured.duration_ms / 1000.0
    if len(marks) == 2:
        window = compute_window(marks[0], marks[1], master_duration_s, scenario)
    elif len(marks) == 4:
        window = compute_window_multi(marks, master_duration_s, scenario)
    else:
        raise InvalidRequest(f"se esperan 2 o 4 marcas, recibidas {len(marks)}")

    regenerated = clip_id is not None
    if clip_id is None:
        clip_id = next_clip_id(videos_dir, scenario)
    invalidated = _invalidate_preann(videos_dir / "preann", clip_id) if regenerated else []

    info = run_prepare_clip(
        script, videos_dir / "clips", master, clip_id,
        ss=window.ss, duration=window.duration,
    )
    write_clip_yaml(videos_dir, clip_id, scenario, master_name, window)

    return {
        "clip_id": clip_id,
        "info": info,
        "warnings": list(window.warnings),
        "regenerated": regenerated,
        "invalidated": invalidated,
    }
