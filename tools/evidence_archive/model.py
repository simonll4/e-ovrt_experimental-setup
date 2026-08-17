from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

Plane = Literal["media-plane", "control-plane"]
Collection = Literal["dbe_datasets", "dbe_video", "ebe_realtime", "shared"]
RunStatus = Literal["copied", "archived_only", "missing", "conflict"]


class EvidenceError(RuntimeError):
    """A validation error safe to show without leaking source contents."""


@dataclass(frozen=True, order=True)
class RunKey:
    plane: Plane
    run_id: str


@dataclass(frozen=True, order=True)
class Relation:
    collection: Collection
    result_id: str
    role: str
    source_ref: str


@dataclass(frozen=True)
class RunRequest:
    key: RunKey
    relations: tuple[Relation, ...]
    source_hints: tuple[str, ...] = ()
    archived_substitutes: tuple[str, ...] = ()


@dataclass(frozen=True)
class ResolvedRun:
    key: RunKey
    status: RunStatus
    relations: tuple[Relation, ...]
    source_dirs: tuple[Path, ...] = ()
    archived_substitutes: tuple[Path, ...] = ()
    reason: str | None = None


@dataclass(frozen=True)
class CheckReport:
    ok: bool
    messages: tuple[str, ...] = ()
    counts: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class Manifest:
    path: Path
    generated_date: str
    collections: tuple[str, ...]
    source_roots: dict[str, tuple[str, ...]]
    expected_campaigns: tuple[str, ...]
    structured_sources: tuple[dict[str, Any], ...]
    manual_groups: tuple[dict[str, Any], ...]
    archived_only: tuple[dict[str, Any], ...]
    archive_policy: dict[str, Any]
    source_dispositions: tuple[dict[str, Any], ...] = ()
