"""Nombrado de clips: clip_id = a_<escenario>_c<NN> (D4 del spec)."""

from __future__ import annotations

import re
from pathlib import Path

SCENARIO_RE = re.compile(r"^P[1-9]$")
# Mismo formato de toma que recording/naming.py: P1-a-take2.mp4
MASTER_RE = re.compile(r"^(P[1-9])-[a-z]-take[0-9]+\.mp4$")


class InvalidScenario(ValueError):
    pass


def scenario_from_master(name: str) -> str | None:
    """Escenario heredado del master (se eligió al grabar); None si es material ajeno."""
    match = MASTER_RE.match(name)
    return match.group(1) if match else None


def next_clip_id(videos_dir: Path, scenario: str) -> str:
    if not SCENARIO_RE.match(scenario):
        raise InvalidScenario(f"escenario inválido: {scenario!r} (esperado P1..P9)")
    prefix = f"a_{scenario.lower()}_c"
    yaml_re = re.compile(rf"^{re.escape(prefix)}([0-9]+)\.clip\.yaml$")
    mp4_re = re.compile(rf"^{re.escape(prefix)}([0-9]+)\.mp4$")
    highest = 0
    if videos_dir.is_dir():
        for path in videos_dir.iterdir():
            match = yaml_re.match(path.name)
            if match is not None:
                highest = max(highest, int(match.group(1)))
    clips_dir = videos_dir / "clips"
    if clips_dir.is_dir():
        # Un mp4 huérfano (sin yaml) también reserva el número: pisarlo sería
        # perder un clip ya recortado.
        for path in clips_dir.iterdir():
            match = mp4_re.match(path.name)
            if match is not None:
                highest = max(highest, int(match.group(1)))
    return f"{prefix}{highest + 1:02d}"
