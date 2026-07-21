"""Nombrado de tomas: escenario + variante -> próximo basename libre."""

from __future__ import annotations

import re
from pathlib import Path

SCENARIO_RE = re.compile(r"^P[1-9]$")
VARIANT_RE = re.compile(r"^[a-z]$")
BASENAME_RE = re.compile(r"^P[1-9]-[a-z]-take[0-9]+$")


class InvalidTakeId(ValueError):
    pass


def next_basename(raw_dir: Path, scenario: str, variant: str) -> str:
    if not SCENARIO_RE.match(scenario):
        raise InvalidTakeId(f"escenario inválido: {scenario!r} (esperado P1..P9)")
    if not VARIANT_RE.match(variant):
        raise InvalidTakeId(f"variante inválida: {variant!r} (esperada una letra a-z)")
    take_re = re.compile(rf"^{scenario}-{variant}-take([0-9]+)\.mp4$")
    highest = 0
    if raw_dir.is_dir():
        for path in raw_dir.iterdir():
            match = take_re.match(path.name)
            if match is not None:
                highest = max(highest, int(match.group(1)))
    return f"{scenario}-{variant}-take{highest + 1}"
