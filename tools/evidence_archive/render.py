from __future__ import annotations

import csv
import hashlib
import io
import json
from collections import Counter
from collections.abc import Sequence
from pathlib import Path

from .archive import ArchivedFile
from .model import EvidenceError, Relation, ResolvedRun, RunKey

COLLECTION_FILES = {
    "dbe_datasets": "dbe-datasets.csv",
    "dbe_video": "dbe-video.csv",
    "ebe_realtime": "ebe-realtime.csv",
    "shared": "shared.csv",
}
CSV_COLUMNS = (
    "collection",
    "result_id",
    "role",
    "plane",
    "run_id",
    "status",
    "source_ref",
    "artifact_path",
)


def _json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _portable(path: Path, workspace_root: Path) -> str:
    try:
        return path.resolve().relative_to(workspace_root.resolve()).as_posix()
    except ValueError as exc:
        raise EvidenceError(f"ruta fuente fuera del workspace: {path.name}") from exc


def _artifact_path(run: ResolvedRun) -> str | None:
    if run.status == "copied":
        return f"artifacts/{run.key.plane}/{run.key.run_id}"
    if run.status == "archived_only":
        return f"artifacts/archived-only/{run.key.plane}--{run.key.run_id}"
    return None


def _relation_dict(relation: Relation) -> dict[str, str]:
    return {
        "collection": relation.collection,
        "result_id": relation.result_id,
        "role": relation.role,
        "source_ref": relation.source_ref,
    }


def render_resolved_runs(runs: Sequence[ResolvedRun], workspace_root: Path) -> bytes:
    records = []
    for run in sorted(runs, key=lambda item: item.key):
        records.append(
            {
                "archive_path": _artifact_path(run),
                "archived_substitutes": [
                    _portable(path, workspace_root) for path in run.archived_substitutes
                ],
                "plane": run.key.plane,
                "reason": run.reason,
                "relations": [
                    _relation_dict(relation) for relation in sorted(run.relations)
                ],
                "run_id": run.key.run_id,
                "source_dirs": [
                    _portable(path, workspace_root) for path in run.source_dirs
                ],
                "status": run.status,
            }
        )
    return _json_bytes({"runs": records, "schema_version": "evidence_runs.resolved.v1"})


def _csv_bytes(rows: list[dict[str, str]]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=CSV_COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def _relation_row(run: ResolvedRun, relation: Relation) -> dict[str, str]:
    return {
        "collection": relation.collection,
        "result_id": relation.result_id,
        "role": relation.role,
        "plane": run.key.plane,
        "run_id": run.key.run_id,
        "status": run.status,
        "source_ref": relation.source_ref,
        "artifact_path": _artifact_path(run) or "",
    }


def render_collections(runs: Sequence[ResolvedRun]) -> dict[str, bytes]:
    rows_by_collection: dict[str, list[dict[str, str]]] = {
        collection: [] for collection in COLLECTION_FILES
    }
    for run in sorted(runs, key=lambda item: item.key):
        non_shared = {r.collection for r in run.relations if r.collection != "shared"}
        for relation in sorted(run.relations):
            rows_by_collection[relation.collection].append(_relation_row(run, relation))
            if len(non_shared) > 1 and relation.collection != "shared":
                shared_row = _relation_row(run, relation)
                shared_row["collection"] = "shared"
                rows_by_collection["shared"].append(shared_row)
    return {
        COLLECTION_FILES[collection]: _csv_bytes(
            sorted(
                rows,
                key=lambda row: (
                    row["run_id"],
                    row["collection"],
                    row["result_id"],
                    row["role"],
                    row["source_ref"],
                ),
            )
        )
        for collection, rows in rows_by_collection.items()
    }


def render_archive_files(files: Sequence[ArchivedFile], workspace_root: Path) -> bytes:
    records = []
    for item in sorted(files, key=lambda value: value.archive_path.as_posix()):
        records.append(
            {
                "archive_path": item.archive_path.as_posix(),
                "archive_sha256": item.archive_sha256,
                "archive_size": item.archive_size,
                "compression": item.compression,
                "plane": item.run_key.plane,
                "redaction": item.redaction,
                "run_id": item.run_key.run_id,
                "source_path": _portable(item.source_path, workspace_root),
                "source_sha256": item.source_sha256,
                "source_size": item.source_size,
            }
        )
    return _json_bytes(
        {"files": records, "schema_version": "evidence_archive.files.v1"}
    )


def _run_link(run: ResolvedRun) -> str:
    artifact = _artifact_path(run)
    if artifact is None:
        return f"`{run.key.run_id}`"
    return f"[`{run.key.run_id}`](evidence-runs/{artifact}/)"


def render_inventory_markdown(
    generated_date: str,
    runs: Sequence[ResolvedRun],
    files: Sequence[ArchivedFile],
) -> bytes:
    ordered = sorted(runs, key=lambda item: item.key)
    by_plane = Counter(run.key.plane for run in ordered)
    by_status = Counter(run.status for run in ordered)
    collection_keys: dict[str, set[RunKey]] = {
        "dbe_datasets": set(),
        "dbe_video": set(),
        "ebe_realtime": set(),
    }
    result_runs: dict[tuple[str, str], dict[RunKey, ResolvedRun]] = {}
    shared_keys: set[RunKey] = set()
    for run in ordered:
        run_collections = {
            relation.collection
            for relation in run.relations
            if relation.collection != "shared"
        }
        if len(run_collections) > 1:
            shared_keys.add(run.key)
        for relation in run.relations:
            if relation.collection == "shared":
                continue
            collection_keys.setdefault(relation.collection, set()).add(run.key)
            result_runs.setdefault((relation.collection, relation.result_id), {})[
                run.key
            ] = run
    campaign_ids = sorted(
        {
            relation.result_id
            for run in ordered
            for relation in run.relations
            if relation.role in {"campaign_media", "campaign_control"}
        }
    )
    t1_archived = sum(
        run.status == "archived_only"
        and any(
            relation.result_id == "clip_bench/t1_gdinotiny560_v2short_scene"
            for relation in run.relations
        )
        for run in ordered
    )
    lines = [
        "# Runs canónicos de evidencia",
        "",
        f"Generado de forma determinista desde `evidence-runs.yaml` ({generated_date}).",
        "",
        f"**{len(ordered)} runs únicos**: {by_plane['media-plane']} del media-plane y "
        f"{by_plane['control-plane']} del control-plane. Estados: "
        f"`copied`={by_status['copied']}, `archived_only`={by_status['archived_only']}, "
        f"`missing`={by_status['missing']}, `conflict`={by_status['conflict']}.",
        "",
        f"Campañas con artefactos: **{len(campaign_ids)}**. "
        f"Controles T1 en estado `archived_only`: **{t1_archived}**.",
        "",
        "## Interpretación",
        "",
        "El conjunto incluye resultados principales, contrastes, resultados negativos y "
        "validaciones citadas. Un directorio original fuera de esta lista no es evidencia "
        "canónica por el solo hecho de existir.",
        "",
        "Cobertura por colección (las relaciones pueden solaparse): "
        f"dbe_datasets={len(collection_keys['dbe_datasets'])}, "
        f"dbe_video={len(collection_keys['dbe_video'])}, "
        f"ebe_realtime={len(collection_keys['ebe_realtime'])}, "
        f"compartidos={len(shared_keys)}.",
        "",
        "## Cobertura por resultado",
        "",
        "| Colección | Resultado | Runs | Media | Control | `archived_only` |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for (collection, result_id), keyed_runs in sorted(result_runs.items()):
        grouped = list(keyed_runs.values())
        media_count = sum(run.key.plane == "media-plane" for run in grouped)
        control_count = sum(run.key.plane == "control-plane" for run in grouped)
        archived_count = sum(run.status == "archived_only" for run in grouped)
        lines.append(
            f"| {collection} | `{result_id}` | {len(grouped)} | {media_count} | "
            f"{control_count} | {archived_count} |"
        )
    lines.extend(
        [
            "",
            "## Inventario completo",
            "",
            "| Plano | Run | Estado | Resultados / roles |",
            "|---|---|---|---|",
        ]
    )
    for run in ordered:
        relations = "; ".join(
            f"`{relation.result_id}` ({relation.role})"
            for relation in sorted(run.relations)
        )
        lines.append(
            f"| {run.key.plane} | {_run_link(run)} | `{run.status}` | {relations} |"
        )
    lines.extend(
        [
            "",
            "## Archivo versionable",
            "",
            f"Contiene {len(files)} archivos curados. Los JSONL se comprimen de forma "
            "determinista; `archive-files.json` conserva hashes y tamaños de origen/destino.",
            "No contiene imágenes, videos, previews, presets de cámara ni credenciales.",
            "",
            "## Verificación",
            "",
            "```bash",
            "python3 tools/evidence_runs.py --check",
            "python3 tools/evidence_runs.py --check --archive-only",
            "```",
            "",
        ]
    )
    return "\n".join(lines).encode("utf-8")


def render_archive_readme(generated_date: str, runs: Sequence[ResolvedRun]) -> bytes:
    return (
        "# Archivo curado de runs de evidencia\n\n"
        f"Catálogo generado el {generated_date}: {len(runs)} runs únicos. Esta carpeta conserva "
        "solo artefactos textuales; excluye imágenes, videos, previews, presets y secretos.\n\n"
        "No edites las copias a mano. Desde la raíz del repo:\n\n"
        "```bash\n"
        "python3 tools/evidence_runs.py sync\n"
        "python3 tools/evidence_runs.py --check\n"
        "python3 tools/evidence_runs.py --check --archive-only\n"
        "```\n\n"
        "El check normal compara contra los runs originales. `--archive-only` valida una copia "
        "clonada sin esos originales y lo informa expresamente.\n"
    ).encode("utf-8")


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def render_checksums(root: Path) -> bytes:
    lines = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name == "files.sha256":
            continue
        lines.append(f"{_file_sha256(path)}  {path.relative_to(root).as_posix()}")
    return ("\n".join(lines) + ("\n" if lines else "")).encode("utf-8")
