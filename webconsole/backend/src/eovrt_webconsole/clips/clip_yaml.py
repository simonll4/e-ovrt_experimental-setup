"""Escritura del <clip_id>.clip.yaml (spec §5.2): cero campos a mano (D5).

derive_clip_gt.load_clip_meta exige solo clip_id/block/scenario y tolera
claves extra (verificado leyendo el script): `master` y `episode_draft` son
seguras y no se filtran al GT. `episode_draft` es un BORRADOR: la verdad
sale de CVAT.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from eovrt_webconsole.clips.window import TrimWindow


def write_clip_yaml(
    videos_dir: Path,
    clip_id: str,
    scenario: str,
    master_name: str,
    window: TrimWindow,
) -> Path:
    """Escribe el metadata YAML del clip con validación y mapeo al master.

    Args:
        videos_dir: directorio donde escribir el <clip_id>.clip.yaml
        clip_id: identificador del clip
        scenario: escenario (ej: "P1", "P2", ...)
        master_name: nombre del archivo master (ej: "P1-a-take2.mp4")
        window: TrimWindow con onset_ms, end_ms, warnings

    Returns:
        Path al archivo .clip.yaml creado
    """
    payload = {
        "clip_id": clip_id,
        "block": "A",                 # rodaje propio guionado
        "scenario": scenario,
        # El evaluador matchea alert.source_id == episode.source_id; la corrida
        # del bench configura su fuente con el clip_id.
        "source_id": clip_id,
        "level": "scene",
        # Clave extra tolerada: mapea el clip a su master para el inventario
        # de la consola y para rehacer el corte sin volver a filmar (D8).
        "master": f"raw/{master_name}",
        "episode_draft": {
            "onset_ms": window.onset_ms,
            "end_ms": window.end_ms,
            "marked_by": "consola",
            "warnings": list(window.warnings),
        },
    }
    path = videos_dir / f"{clip_id}.clip.yaml"
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return path
