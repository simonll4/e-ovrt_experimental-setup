"""Inventario: lee raw/ y clips/ y deriva el estado de cada toma.

Solo lectura. Un master ilegible se marca (readable=False), no rompe la
vista; raw/ o clips/ inexistentes dan lista vacía (spec §7).
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from eovrt_webconsole.clips.naming import scenario_from_master
from eovrt_webconsole.recording.probe import ProbeError, measure


def _clips_por_master(videos_dir: Path) -> dict[str, list[str]]:
    """master ("raw/<name>") -> clip_ids, según el campo `master` de los .clip.yaml."""
    por_master: dict[str, list[str]] = {}
    if not videos_dir.is_dir():
        return por_master
    for path in sorted(videos_dir.glob("*.clip.yaml")):
        try:
            data = yaml.safe_load(path.read_text())
        except yaml.YAMLError:
            continue
        if not isinstance(data, dict):
            continue
        master = data.get("master")
        clip_id = data.get("clip_id")
        if isinstance(master, str) and isinstance(clip_id, str):
            por_master.setdefault(master, []).append(clip_id)
    return por_master


def list_masters(raw_dir: Path, videos_dir: Path) -> list[dict]:
    """Lista masters de raw/ con su estado: duración, legibilidad, clips vinculados.

    Args:
        raw_dir: directorio raw/ con masters *.mp4
        videos_dir: directorio padre donde buscar .clip.yaml

    Returns:
        Lista de dicts ordenada por nombre: {"name", "scenario", "size_bytes",
        "duration_ms", "readable", "clips"}. Un master ilegible tiene
        readable=False y duration_ms=None. raw_dir inexistente -> [].
    """
    if not raw_dir.is_dir():
        return []
    por_master = _clips_por_master(videos_dir)
    masters = []
    for path in sorted(raw_dir.glob("*.mp4")):
        try:
            measured = measure(path)
            duration_ms: int | None = measured.duration_ms
            readable = True
        except ProbeError:
            duration_ms = None
            readable = False
        masters.append(
            {
                "name": path.name,
                "scenario": scenario_from_master(path.name),
                "size_bytes": path.stat().st_size,
                "duration_ms": duration_ms,
                "readable": readable,
                "clips": sorted(por_master.get(f"raw/{path.name}", [])),
            }
        )
    return masters


def list_clips(videos_dir: Path) -> list[dict]:
    """Lista clips de videos_dir/clips/ con metadatos y vinculación al master.

    Args:
        videos_dir: directorio donde buscar clips/ y .clip.yaml

    Returns:
        Lista de dicts ordenada por clip_id: {"clip_id", "fps", "duration_ms",
        "n_frames", "resolution", "has_yaml", "master", "warnings"}.
        master y warnings vienen del .clip.yaml si existe, sino None/[].
        clips/ inexistente -> [].
    """
    clips_dir = videos_dir / "clips"
    if not clips_dir.is_dir():
        return []
    clips = []
    for info_path in sorted(clips_dir.glob("*.info.json")):
        try:
            info = json.loads(info_path.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        clip_id = info.get("clip_id", info_path.name.removesuffix(".info.json"))
        yaml_path = videos_dir / f"{clip_id}.clip.yaml"
        master = None
        warnings: list = []
        has_yaml = yaml_path.is_file()
        if has_yaml:
            try:
                meta = yaml.safe_load(yaml_path.read_text()) or {}
            except yaml.YAMLError:
                meta = {}
            master = meta.get("master")
            draft = meta.get("episode_draft") or {}
            if isinstance(draft, dict):
                warnings = draft.get("warnings") or []
        clips.append(
            {
                "clip_id": clip_id,
                "fps": info.get("fps"),
                "duration_ms": info.get("duration_ms"),
                "n_frames": info.get("n_frames"),
                "resolution": info.get("resolution"),
                "has_yaml": has_yaml,
                "master": master,
                "warnings": warnings,
            }
        )
    return clips
