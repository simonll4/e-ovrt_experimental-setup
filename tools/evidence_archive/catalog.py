from __future__ import annotations

import hashlib
from collections.abc import Iterable, Mapping
from pathlib import Path

from .manifest import COLLECTION_NAMES
from .model import EvidenceError, Manifest, Relation, ResolvedRun, RunKey, RunRequest


def merge_requests(requests: Iterable[RunRequest]) -> dict[RunKey, RunRequest]:
    grouped: dict[RunKey, list[RunRequest]] = {}
    for request in requests:
        grouped.setdefault(request.key, []).append(request)

    merged: dict[RunKey, RunRequest] = {}
    for key, items in grouped.items():
        relations = tuple(
            sorted({relation for item in items for relation in item.relations})
        )
        source_hints = tuple(
            sorted({hint for item in items for hint in item.source_hints})
        )
        substitutes = tuple(
            sorted({path for item in items for path in item.archived_substitutes})
        )
        merged[key] = RunRequest(
            key=key,
            relations=relations,
            source_hints=source_hints,
            archived_substitutes=substitutes,
        )
    return merged


def portable_docs_path(raw_path: str, workspace_root: Path) -> Path | None:
    normalized = raw_path.replace("\\", "/")
    marker = "/docs/"
    if marker not in normalized:
        return None
    suffix = normalized.split(marker, 1)[1]
    parts = Path(suffix).parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        return None
    candidate = workspace_root / "docs" / Path(*parts)
    return candidate.parent


def _required_string(item: Mapping[str, object], key: str, label: str) -> str:
    value = item.get(key)
    if not isinstance(value, str) or not value.strip():
        raise EvidenceError(f"{label} requiere {key}")
    return value.strip()


def manual_requests(manifest: Manifest) -> list[RunRequest]:
    requests: list[RunRequest] = []
    for raw_group in manifest.manual_groups:
        group: Mapping[str, object] = raw_group
        group_id = _required_string(group, "id", "manual_group")
        collection = _required_string(group, "collection", group_id)
        if collection not in COLLECTION_NAMES:
            raise EvidenceError(f"{group_id} declara collection inválida")
        result_id = _required_string(group, "result_id", group_id)
        role = _required_string(group, "role", group_id)
        document = _required_string(group, "document", group_id)
        relation = Relation(collection, result_id, role, document)

        if group.get("requires_pair") is True:
            pairs = group.get("pairs")
            if not isinstance(pairs, list) or not pairs:
                raise EvidenceError(f"{group_id} requiere pairs no vacío")
            for index, raw_pair in enumerate(pairs, start=1):
                if not isinstance(raw_pair, Mapping):
                    raise EvidenceError(f"{group_id} pair {index} debe ser un objeto")
                media_id = raw_pair.get("media_run_id")
                control_id = raw_pair.get("control_run_id")
                if not isinstance(media_id, str) or not isinstance(control_id, str):
                    raise EvidenceError(
                        f"{group_id} pair {index} requiere media_run_id y control_run_id"
                    )
                requests.append(
                    RunRequest(RunKey("media-plane", media_id), (relation,))
                )
                requests.append(
                    RunRequest(RunKey("control-plane", control_id), (relation,))
                )
            continue

        plane = group.get("plane")
        run_ids = group.get("runs")
        if plane not in {"media-plane", "control-plane"}:
            raise EvidenceError(f"{group_id} requiere plane válido")
        if not isinstance(run_ids, list) or not run_ids:
            raise EvidenceError(f"{group_id} requiere runs no vacío")
        if any(not isinstance(run_id, str) or not run_id for run_id in run_ids):
            raise EvidenceError(f"{group_id} contiene un run ID inválido")
        requests.extend(
            RunRequest(RunKey(plane, run_id), (relation,)) for run_id in run_ids
        )
    return requests


def _allowed_extensions(manifest: Manifest) -> set[str]:
    raw = manifest.archive_policy.get("allowed_extensions", [])
    if not isinstance(raw, list) or any(not isinstance(item, str) for item in raw):
        raise EvidenceError("archive_policy.allowed_extensions debe ser una lista")
    return {item.lower() for item in raw}


def _tree_digest(root: Path, allowed_extensions: set[str]) -> str:
    digest = hashlib.sha256()
    count = 0
    for path in sorted(root.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        if path.suffix.lower() not in allowed_extensions:
            continue
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
        digest.update(b"\0")
        count += 1
    if count == 0:
        raise EvidenceError(f"run sin archivos textuales admitidos: {root.name}")
    return digest.hexdigest()


def _source_candidates(
    manifest: Manifest,
    request: RunRequest,
    workspace_root: Path,
) -> tuple[Path, ...]:
    repo_root = manifest.path.parent.parent
    candidates: set[Path] = set()
    for raw_root in manifest.source_roots.get(request.key.plane, ()):
        candidate = (repo_root / raw_root / request.key.run_id).resolve()
        if candidate.is_dir():
            candidates.add(candidate)
    if request.key.plane == "control-plane":
        for hint in request.source_hints:
            candidate = portable_docs_path(hint, workspace_root)
            if (
                candidate is not None
                and candidate.name == request.key.run_id
                and candidate.is_dir()
            ):
                candidates.add(candidate.resolve())
    return tuple(sorted(candidates, key=lambda path: path.as_posix()))


def _archived_substitutes(
    manifest: Manifest,
    request: RunRequest,
) -> tuple[tuple[Path, ...], str | None]:
    repo_root = manifest.path.parent.parent
    for rule in manifest.archived_only:
        reason = rule.get("reason")
        if not isinstance(reason, str) or not reason:
            raise EvidenceError("cada regla archived_only requiere reason")

        exact_match = (
            rule.get("plane") == request.key.plane
            and rule.get("run_id") == request.key.run_id
        )
        campaign_match = False
        source = rule.get("request_source")
        if isinstance(source, str) and source.startswith("campaign:"):
            campaign_id = source.removeprefix("campaign:")
            campaign_match = any(
                relation.result_id == campaign_id for relation in request.relations
            )
        relation_result_id = rule.get("relation_result_id")
        result_match = isinstance(relation_result_id, str) and any(
            relation.result_id == relation_result_id for relation in request.relations
        )
        rule_plane = rule.get("plane")
        if result_match and rule_plane is not None and rule_plane != request.key.plane:
            result_match = False
        if not exact_match and not campaign_match and not result_match:
            continue

        raw_paths: tuple[str, ...]
        if rule.get("substitute_from") == "matching_eval":
            raw_paths = request.archived_substitutes
        else:
            substitutes = rule.get("substitutes")
            if not isinstance(substitutes, list) or any(
                not isinstance(path, str) for path in substitutes
            ):
                raise EvidenceError(
                    f"regla archived_only inválida para {request.key.run_id}"
                )
            raw_paths = tuple(substitutes)
        paths = tuple(
            sorted(((repo_root / path).resolve() for path in raw_paths), key=str)
        )
        if not paths or any(not path.is_file() for path in paths):
            return (), f"sustituto archivado ausente para {request.key.run_id}"
        return paths, reason
    return (), None


def resolve_catalog(
    manifest: Manifest,
    requests: Iterable[RunRequest],
    workspace_root: Path,
) -> list[ResolvedRun]:
    allowed_extensions = _allowed_extensions(manifest)
    resolved: list[ResolvedRun] = []
    for key, request in sorted(merge_requests(requests).items()):
        candidates = _source_candidates(manifest, request, workspace_root)
        if candidates:
            digests = {
                _tree_digest(candidate, allowed_extensions) for candidate in candidates
            }
            if len(digests) > 1:
                resolved.append(
                    ResolvedRun(
                        key,
                        "conflict",
                        request.relations,
                        source_dirs=candidates,
                        reason="se encontraron copias textuales divergentes",
                    )
                )
            else:
                resolved.append(
                    ResolvedRun(
                        key, "copied", request.relations, source_dirs=candidates
                    )
                )
            continue

        substitutes, reason = _archived_substitutes(manifest, request)
        if substitutes:
            resolved.append(
                ResolvedRun(
                    key,
                    "archived_only",
                    request.relations,
                    archived_substitutes=substitutes,
                    reason=reason,
                )
            )
        else:
            resolved.append(
                ResolvedRun(
                    key,
                    "missing",
                    request.relations,
                    reason=reason or "no se encontró el run ni un sustituto declarado",
                )
            )
    return resolved
