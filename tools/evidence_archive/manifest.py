from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import yaml

from .model import EvidenceError, Manifest, Relation, RunKey, RunRequest

COLLECTION_NAMES = {"dbe_datasets", "dbe_video", "ebe_realtime", "shared"}
CAMPAIGN_ROOTS = ("clip_bench", "bench_nivel_a")
MEDIA_FIELDS = {
    "media_run_id",
    "eind_run_id",
    "edir_run_id",
    "detections_from",
    "run_id",
}


def _require_mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise EvidenceError(f"{label} debe ser un objeto YAML")
    return value


def _require_list(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise EvidenceError(f"{label} debe ser una lista YAML")
    return value


def _unique_strings(values: object, label: str) -> tuple[str, ...]:
    items = _require_list(values, label)
    if any(not isinstance(item, str) or not item.strip() for item in items):
        raise EvidenceError(f"{label} solo admite strings no vacíos")
    normalized = tuple(item.strip() for item in items)
    if len(set(normalized)) != len(normalized):
        raise EvidenceError(f"{label} contiene entradas duplicadas")
    return normalized


def load_manifest(path: Path) -> Manifest:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise EvidenceError(f"no se pudo cargar el manifiesto {path}") from exc
    data = _require_mapping(raw, "manifest")
    if data.get("schema_version") != "evidence_runs.v1":
        raise EvidenceError("schema_version debe ser evidence_runs.v1")

    collections = _require_mapping(data.get("collections"), "collections")
    if set(collections) != COLLECTION_NAMES:
        raise EvidenceError(
            "collections debe declarar exactamente las cuatro colecciones"
        )

    source_roots_raw = _require_mapping(data.get("source_roots"), "source_roots")
    if not {"media-plane", "control-plane"}.issubset(source_roots_raw):
        raise EvidenceError("source_roots debe declarar media-plane y control-plane")
    source_roots = {
        plane: _unique_strings(paths, f"source_roots.{plane}")
        for plane, paths in source_roots_raw.items()
    }

    generated_date = data.get("generated_date")
    if hasattr(generated_date, "isoformat"):
        generated_date = generated_date.isoformat()
    if not isinstance(generated_date, str) or not generated_date:
        raise EvidenceError("generated_date debe ser una fecha")

    structured_sources = _require_list(
        data.get("structured_sources"), "structured_sources"
    )
    manual_groups = _require_list(data.get("manual_groups"), "manual_groups")
    archived_only = _require_list(data.get("archived_only"), "archived_only")
    source_dispositions = _require_list(
        data.get("source_dispositions", []), "source_dispositions"
    )
    archive_policy = dict(
        _require_mapping(data.get("archive_policy"), "archive_policy")
    )

    for label, entries in (
        ("structured_sources", structured_sources),
        ("manual_groups", manual_groups),
        ("archived_only", archived_only),
        ("source_dispositions", source_dispositions),
    ):
        ids: list[str] = []
        for entry in entries:
            item = _require_mapping(entry, f"{label} entry")
            entry_id = item.get("id")
            if not isinstance(entry_id, str) or not entry_id:
                raise EvidenceError(f"cada entrada de {label} requiere id")
            ids.append(entry_id)
        if len(ids) != len(set(ids)):
            raise EvidenceError(f"{label} contiene IDs duplicados")

    return Manifest(
        path=path.resolve(),
        generated_date=generated_date,
        collections=tuple(sorted(collections)),
        source_roots=source_roots,
        expected_campaigns=_unique_strings(
            data.get("expected_campaigns"), "expected_campaigns"
        ),
        structured_sources=tuple(dict(item) for item in structured_sources),
        manual_groups=tuple(dict(item) for item in manual_groups),
        archived_only=tuple(dict(item) for item in archived_only),
        archive_policy=archive_policy,
        source_dispositions=tuple(dict(item) for item in source_dispositions),
    )


def extract_values(data: object, selector: str) -> list[str]:
    if not selector or any(not token for token in selector.split(".")):
        raise EvidenceError(f"selector inválido: {selector!r}")
    nodes: list[object] = [data]
    for token in selector.split("."):
        next_nodes: list[object] = []
        for node in nodes:
            if token == "*":
                if isinstance(node, Mapping):
                    next_nodes.extend(node[key] for key in sorted(node, key=str))
                elif isinstance(node, Sequence) and not isinstance(
                    node, (str, bytes, bytearray)
                ):
                    next_nodes.extend(node)
                else:
                    raise EvidenceError(
                        f"selector {selector!r} aplica * sobre un escalar"
                    )
            elif isinstance(node, Mapping) and token in node:
                next_nodes.append(node[token])
            else:
                raise EvidenceError(f"selector {selector!r} no encuentra {token!r}")
        nodes = next_nodes
    if not nodes:
        raise EvidenceError(f"selector {selector!r} no devolvió valores")
    if any(not isinstance(value, str) or not value.strip() for value in nodes):
        raise EvidenceError(f"selector {selector!r} devolvió un valor no-string")
    return [str(value).strip() for value in nodes]


def discover_campaigns(repo_root: Path) -> dict[str, Path]:
    campaigns: dict[str, Path] = {}
    for family in CAMPAIGN_ROOTS:
        family_root = repo_root / "results" / family
        if not family_root.is_dir():
            continue
        for candidate in sorted(family_root.iterdir()):
            if not candidate.is_dir() or not (candidate / "metrics.json").is_file():
                continue
            key = f"{family}/{candidate.name}"
            if not (candidate / "campaign.yaml").is_file():
                raise EvidenceError(f"campaña {key} no tiene campaign.yaml")
            if not list(candidate.glob("provenance*.json")):
                raise EvidenceError(f"campaña {key} no tiene provenance JSON")
            campaigns[key] = candidate
    return campaigns


def _recursive_media_ids(value: object, source_ref: str) -> set[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        for key, child in value.items():
            if key in MEDIA_FIELDS:
                if child is None:
                    continue
                if not isinstance(child, str) or not child.strip():
                    raise EvidenceError(f"campo de run inválido en {source_ref}")
                found.add(child.strip())
            else:
                found.update(_recursive_media_ids(child, source_ref))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for child in value:
            found.update(_recursive_media_ids(child, source_ref))
    return found


def _json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"JSON inválido: {path}") from exc


def campaign_requests(manifest: Manifest, repo_root: Path) -> list[RunRequest]:
    campaigns = discover_campaigns(repo_root)
    expected = set(manifest.expected_campaigns)
    actual = set(campaigns)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise EvidenceError(
            f"campañas fuera de contrato; faltan={missing}, sobran={extra}"
        )

    requests: list[RunRequest] = []
    for campaign_key, campaign_dir in sorted(campaigns.items()):
        collection = (
            "dbe_video" if campaign_key.startswith("clip_bench/") else "dbe_datasets"
        )
        for provenance_path in sorted(campaign_dir.glob("provenance*.json")):
            source_ref = provenance_path.relative_to(repo_root).as_posix()
            media_ids = _recursive_media_ids(_json(provenance_path), source_ref)
            if not media_ids:
                raise EvidenceError(f"provenance sin media runs: {source_ref}")
            relation = Relation(collection, campaign_key, "campaign_media", source_ref)
            requests.extend(
                RunRequest(RunKey("media-plane", run_id), (relation,))
                for run_id in sorted(media_ids)
            )

        if campaign_key.startswith("clip_bench/"):
            eval_paths = sorted((campaign_dir / "evals").glob("eval_*.json"))
            if not eval_paths:
                raise EvidenceError(f"campaña temporal sin evals: {campaign_key}")
            for eval_path in eval_paths:
                source_ref = eval_path.relative_to(repo_root).as_posix()
                eval_data = _json(eval_path)
                if not isinstance(eval_data, Mapping):
                    raise EvidenceError(f"eval inválido: {source_ref}")
                alerts_path = eval_data.get("alerts_path")
                if not isinstance(alerts_path, str) or not alerts_path:
                    raise EvidenceError(f"eval sin alerts_path: {source_ref}")
                control_id = Path(alerts_path).parent.name
                if not control_id:
                    raise EvidenceError(f"alerts_path sin control run: {source_ref}")
                relation = Relation(
                    collection, campaign_key, "campaign_control", source_ref
                )
                requests.append(
                    RunRequest(
                        RunKey("control-plane", control_id),
                        (relation,),
                        source_hints=(alerts_path,),
                        archived_substitutes=(source_ref,),
                    )
                )
    return requests


def structured_requests(manifest: Manifest, repo_root: Path) -> list[RunRequest]:
    requests: list[RunRequest] = []
    for source in manifest.structured_sources:
        source_id = source.get("id")
        kind = source.get("kind", "selectors")
        raw_path = source.get("path")
        selectors = source.get("selectors")
        expected_count = source.get("expected_count")
        plane = source.get("plane", "media-plane")
        collection = source.get("collection")
        result_id = source.get("result_id")
        role = source.get("role")
        if not isinstance(source_id, str) or not source_id:
            raise EvidenceError("structured_source requiere id")
        if not isinstance(expected_count, int) or expected_count <= 0:
            raise EvidenceError(f"{source_id} requiere expected_count positivo")
        if collection not in COLLECTION_NAMES:
            raise EvidenceError(f"{source_id} declara collection inválida")
        if not isinstance(result_id, str) or not result_id:
            raise EvidenceError(f"{source_id} requiere result_id")
        if not isinstance(role, str) or not role:
            raise EvidenceError(f"{source_id} requiere role")

        if kind == "eval_control_runs":
            raw_paths = source.get("paths")
            if (
                not isinstance(raw_paths, list)
                or not raw_paths
                or any(not isinstance(path, str) for path in raw_paths)
            ):
                raise EvidenceError(f"{source_id} requiere paths")
            found_ids: set[str] = set()
            relation_requests: list[RunRequest] = []
            for raw_directory in raw_paths:
                directory = (repo_root / raw_directory).resolve()
                if not directory.is_dir():
                    raise EvidenceError(f"directorio de evals ausente: {raw_directory}")
                eval_paths = sorted(directory.glob("eval_*.json"))
                if not eval_paths:
                    raise EvidenceError(f"directorio sin evals: {raw_directory}")
                for eval_path in eval_paths:
                    data = _json(eval_path)
                    if not isinstance(data, Mapping):
                        raise EvidenceError(f"eval inválido: {eval_path.name}")
                    alerts_path = data.get("alerts_path")
                    if not isinstance(alerts_path, str) or not alerts_path:
                        raise EvidenceError(f"eval sin alerts_path: {eval_path.name}")
                    control_id = Path(alerts_path).parent.name
                    if not control_id:
                        raise EvidenceError(f"eval sin control run: {eval_path.name}")
                    source_ref = f"{raw_directory.rstrip('/')}/{eval_path.name}"
                    relation = Relation(collection, result_id, role, source_ref)
                    relation_requests.append(
                        RunRequest(
                            RunKey("control-plane", control_id),
                            (relation,),
                            source_hints=(alerts_path,),
                            archived_substitutes=(source_ref,),
                        )
                    )
                    found_ids.add(control_id)
            if len(found_ids) != expected_count:
                raise EvidenceError(
                    f"{source_id} resolvió {len(found_ids)} runs; esperaba {expected_count}"
                )
            requests.extend(relation_requests)
            continue

        if kind != "selectors":
            raise EvidenceError(f"{source_id} declara kind inválido")
        if not isinstance(raw_path, str) or not raw_path:
            raise EvidenceError(f"{source_id} requiere path")
        if (
            not isinstance(selectors, list)
            or not selectors
            or any(not isinstance(selector, str) for selector in selectors)
        ):
            raise EvidenceError(f"{source_id} requiere selectors")
        if plane not in {"media-plane", "control-plane"}:
            raise EvidenceError(f"{source_id} declara plane inválido")

        path = (repo_root / raw_path).resolve()
        if not path.is_file():
            raise EvidenceError(f"fuente estructurada ausente: {raw_path}")
        if path.suffix.lower() == ".jsonl":
            try:
                data: object = [
                    json.loads(line)
                    for line in path.read_text(encoding="utf-8").splitlines()
                    if line.strip()
                ]
            except (OSError, json.JSONDecodeError) as exc:
                raise EvidenceError(f"JSONL inválido: {raw_path}") from exc
        else:
            data = _json(path)
        run_ids = {
            run_id
            for selector in selectors
            for run_id in extract_values(data, selector)
        }
        if len(run_ids) != expected_count:
            raise EvidenceError(
                f"{source_id} resolvió {len(run_ids)} runs; esperaba {expected_count}"
            )
        relation = Relation(collection, result_id, role, raw_path)
        requests.extend(
            RunRequest(RunKey(plane, run_id), (relation,)) for run_id in sorted(run_ids)
        )
    return requests
