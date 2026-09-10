"""Registro curado, cargado una vez; archivar sólo cambia la visibilidad."""
from __future__ import annotations

import csv
import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import Literal

import yaml

logger = logging.getLogger(__name__)
Vista = Literal["evidencia", "archivadas", "todas"]
CSV_FILES = ("dbe-datasets.csv", "dbe-video.csv", "ebe-realtime.csv", "shared.csv")


def coincide_vista(evidence: dict, vista: Vista) -> bool:
    return vista == "todas" or evidence["is_evidence"] == (vista == "evidencia")


class EvidenceRegistry:
    def __init__(self, archive_dir: Path):
        self.available = all((archive_dir / "collections" / name).is_file() for name in CSV_FILES)
        self._rows: dict[str, list[dict]] = defaultdict(list)
        self._force: dict[str, bool] = {}
        if self.available:
            for name in CSV_FILES:
                with (archive_dir / "collections" / name).open(encoding="utf-8", newline="") as src:
                    for row in csv.DictReader(src):
                        self._rows[row["run_id"]].append(row)
        else:
            logger.warning("Registro de evidencia ausente o incompleto: %s/collections", archive_dir)

        overrides = archive_dir / "consola.yaml"
        if overrides.is_file():
            data = yaml.safe_load(overrides.read_text(encoding="utf-8")) or {}
            for key, verdict in (("forzar_evidencia", True), ("forzar_archivado", False)):
                entries = data.get(key, [])
                if not isinstance(entries, list) or any(not isinstance(s, str) for s in entries):
                    raise ValueError(f"consola.yaml: {key} debe ser una lista de slug o id")
                for entry in entries:
                    if entry in self._force and self._force[entry] != verdict:
                        raise ValueError(f"consola.yaml: excepción contradictoria para {entry}")
                    self._force[entry] = verdict

    def es_evidencia(self, run_id: str) -> bool:
        return run_id in self._rows

    def relaciones(self, run_id: str) -> list[dict]:
        keys = ("collection", "result_id", "role", "source_ref")
        return [dict(zip(keys, values)) for values in sorted({
            tuple(row[key] for key in keys) for row in self._rows.get(run_id, [])
        })]

    def resultados(self) -> list[dict]:
        groups: dict[str, set[tuple[str, str]]] = defaultdict(set)
        for rows in self._rows.values():
            for row in rows:
                groups[row["result_id"]].add((row["plane"], row["run_id"]))
        # shared describe pertenencia múltiple, nunca una quinta colección.
        return [{
            "result_id": result_id,
            "collection": result_id.split("/", 1)[0],
            "n_runs": len(runs),
            "planes": sorted({plane for plane, _ in runs}),
        } for result_id, runs in sorted(groups.items())]

    def describe(self, run_ids: list[str]) -> dict:
        rows = [row for run_id in run_ids for row in self._rows.get(run_id, [])]
        return {
            "is_evidence": bool(rows),
            "result_ids": sorted({row["result_id"] for row in rows}),
            "collections": sorted({
                {"bench_imagenes": "dbe_datasets", "bench_nivel_a": "dbe_datasets",
                 "clip_bench": "dbe_video", "realtime": "ebe_realtime"}.get(
                    row["result_id"].split("/", 1)[0], row["collection"]
                ) for row in rows
            }),
        }

    def ejecucion(self, experiment_id: str, slug: str, run_ids: list[str]) -> dict:
        evidence = self.describe(run_ids)
        # Una excepción de ejecución es más específica que la del manifiesto.
        key = next((key for key in (experiment_id, slug) if key in self._force), None)
        if key is not None:
            evidence.update(is_evidence=self._force[key], reason=f"Excepción explícita: {key}")
        else:
            matching = sorted({run_id for run_id in run_ids if self.es_evidencia(run_id)})
            evidence["reason"] = (
                "Corridas en el registro: " + ", ".join(matching) if matching else
                "Ninguna corrida consolidada figura en el registro"
            )
        return evidence

    def manifiesto(self, slug: str, executions: list[dict]) -> dict:
        evidence = {
            "is_evidence": any(e["is_evidence"] for e in executions),
            "result_ids": sorted({r for e in executions for r in e["result_ids"]}),
            "collections": sorted({c for e in executions for c in e["collections"]}),
        }
        if slug in self._force:
            evidence.update(is_evidence=self._force[slug], reason=f"Excepción explícita: {slug}")
        else:
            n = sum(e["is_evidence"] for e in executions)
            evidence["reason"] = (
                f"{n} de {len(executions)} ejecuciones son evidencia" if executions else
                "Sin ejecuciones consolidadas asociadas al slug"
            )
        return evidence


def _identidades(data) -> set[str]:
    ids: set[str] = set()
    if isinstance(data, dict):
        for key, value in data.items():
            name = key if isinstance(key, str) else ""
            if (name == "run_id" or name.endswith("_run_id")) and isinstance(value, str) and value:
                ids.add(value)
            elif (name == "run_ids" or name.endswith("_run_ids")) and isinstance(value, list):
                ids.update(v for v in value if isinstance(v, str) and v)
            if isinstance(value, (dict, list)):
                ids.update(_identidades(value))
    elif isinstance(data, list):
        for value in data:
            ids.update(_identidades(value))
    return ids


def corridas_consolidadas(directory: Path) -> list[str]:
    """Recorre todo el subárbol local; nunca abre destinos de archivos .ref.

    Incluye identidades anidadas en JSON, JSONL y YAML. Las líneas JSONL se
    procesan individualmente para no cargar detecciones y métricas completas.
    """
    ids: set[str] = set()
    for path in sorted(directory.rglob("*")):
        if path.suffix not in {".json", ".jsonl", ".yaml", ".yml"}:
            continue
        if not path.is_file() or not path.resolve().is_relative_to(directory.resolve()):
            continue
        try:
            if path.suffix == ".jsonl":
                with path.open(encoding="utf-8") as src:
                    for line in src:
                        if "run_id" in line:
                            ids.update(_identidades(json.loads(line)))
            else:
                text = path.read_text(encoding="utf-8")
                if "run_id" not in text:
                    continue
                data = json.loads(text) if path.suffix == ".json" else yaml.safe_load(text)
                ids.update(_identidades(data))
        except (OSError, ValueError, yaml.YAMLError) as exc:
            logger.warning("No se pudo leer la identidad consolidada de %s: %s", path, exc)
    return sorted(ids)


def directorios_consolidados(runs_dir: Path) -> list[Path]:
    """Descubrimiento recursivo independiente del listado histórico por slug."""
    base = runs_dir.resolve()
    return [path.parent for path in sorted(runs_dir.rglob("manifest.effective.yaml"))
            if path.is_file() and path.resolve().is_relative_to(base)]


def clasificar_ejecuciones(runs_dir: Path, registry: EvidenceRegistry) -> list[dict]:
    executions = []
    for directory in directorios_consolidados(runs_dir):
        try:
            manifest = yaml.safe_load((directory / "manifest.effective.yaml").read_text())
            slug = manifest.get("slug") if isinstance(manifest, dict) else None
            if not isinstance(slug, str) or not slug:
                continue
            ids = corridas_consolidadas(directory)
            executions.append({
                "experiment_id": directory.name,
                "slug": slug,
                "directory": directory,
                "run_ids": ids,
                "evidence": registry.ejecucion(directory.name, slug, ids),
            })
        except (OSError, yaml.YAMLError) as exc:
            logger.warning("No se pudo clasificar %s: %s", directory, exc)
    return executions
