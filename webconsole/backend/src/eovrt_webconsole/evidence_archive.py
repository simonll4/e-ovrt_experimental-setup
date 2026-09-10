"""Lectura local del archivo curado. No importa clientes de los servicios."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

import yaml

from eovrt_webconsole.evidence import CSV_FILES, EvidenceRegistry


def etiqueta(result_id: str) -> str:
    return result_id.split("/", 1)[-1].replace("_", " ").replace("-", " ")


def contained(base: Path, relative: str) -> Path:
    path = (base / relative).resolve()
    if not path.is_relative_to(base.resolve()):
        raise ValueError("Ruta fuera del archivo de evidencia")
    return path


def preserved_summaries(data, run_id: str) -> list[dict]:
    """Selecciona sólo summaries con identidad explícita, sin recalcular métricas."""
    found = []
    if isinstance(data, dict):
        identity = data.get("run_id", data.get("control_run_id"))
        if identity == run_id and ".summary." in str(data.get("schema_version", "")):
            found.append(data)
        for value in data.values():
            found.extend(preserved_summaries(value, run_id))
    elif isinstance(data, list):
        for value in data:
            found.extend(preserved_summaries(value, run_id))
    return found


class EvidenceArchive:
    def __init__(self, repo_root: Path, registry: EvidenceRegistry):
        self.root = repo_root
        self.directory = repo_root / "results/evidence-runs"
        self.registry = registry
        self.by_result: dict[str, list[dict]] = defaultdict(list)
        self.by_run: dict[tuple[str, str], list[dict]] = defaultdict(list)
        for row in registry.filas():
            self.by_result[row["result_id"]].append(row)
            self.by_run[row["plane"], row["run_id"]].append(row)
        self.metadata = {}
        resolved = self.directory / "resolved-runs.json"
        if resolved.is_file():
            for run in json.loads(resolved.read_text())["runs"]:
                self.metadata[run["plane"], run["run_id"]] = run
        self.titles = {}
        titles_path = self.directory / "titulos.yaml"
        if titles_path.is_file():
            self.titles = {
                row["result_id"]: row.get("titulo")
                for row in (yaml.safe_load(titles_path.read_text()) or {}).get("resultados", [])
            }
        # Sólo procedencia documental del manifiesto, nunca selección ni conteos.
        self.documents: dict[str, set[str]] = defaultdict(set)
        manifest = repo_root / "results/evidence-runs.yaml"
        if manifest.is_file():
            data = yaml.safe_load(manifest.read_text()) or {}
            for source in [*data.get("structured_sources", []), *data.get("manual_groups", [])]:
                if source.get("result_id") and source.get("document"):
                    self.documents[source["result_id"]].add(source["document"])
        for result_id in self.by_result:
            campaign = f"results/{result_id}/campaign.yaml"
            if contained(repo_root, campaign).is_file():
                self.documents[result_id].add(campaign)

    def availability(self) -> dict:
        available = self.registry.available and (self.directory / "artifacts").is_dir() and all(
            (self.directory / "collections" / name).is_file() for name in CSV_FILES
        )
        return {
            "available": available,
            "message": None if available else (
                f"Archivo de evidencia no disponible o incompleto: {self.directory}. "
                "Restauralo desde la capa de evidencia del backup (docs/operacion/126) "
                "y reiniciá la consola."
            ),
        }

    def result_info(self, result_id: str) -> dict:
        rows = self.by_result[result_id]
        return {
            "result_id": result_id,
            "index": result_id.split("/", 1)[0],
            "etiqueta": etiqueta(result_id),
            "titulo": self.titles.get(result_id) or None,
            "n_runs": len({(r["plane"], r["run_id"]) for r in rows}),
            "n_rows": len(rows),
            "roles": dict(sorted(Counter(r["role"] for r in rows).items())),
            "documents": sorted(self.documents[result_id]),
            "source_refs": sorted({r["source_ref"] for r in rows}),
        }

    def index(self) -> dict:
        state = self.availability()
        groups: dict[str, list[dict]] = defaultdict(list)
        if state["available"]:
            for result_id in sorted(self.by_result):
                info = self.result_info(result_id)
                groups[info["index"]].append(info)
        return {**state, "collections": [
            {"id": name, "n_results": len(results), "results": results,
             "n_rows": sum(r["n_rows"] for r in results)}
            for name, results in sorted(groups.items())
        ]}

    def run_info(self, row: dict) -> dict:
        plane, run_id = row["plane"], row["run_id"]
        metadata = self.metadata.get((plane, run_id), {})
        live = False
        if row["status"] == "copied" and plane in {"media-plane", "control-plane"}:
            base = self.root.parent / f"e-ovrt_{plane}" / "runs"
            live = contained(base, run_id).is_dir()
        return {**row, "reason": metadata.get("reason"), "tiene_detalle_vivo": live}

    def result(self, result_id: str, page: int, page_size: int) -> dict:
        state = self.availability()
        if not state["available"]:
            return {**state, "result": None, "items": [], "total": 0,
                    "page": page, "page_size": page_size}
        if result_id not in self.by_result:
            raise KeyError(result_id)
        rows = sorted(self.by_result[result_id], key=lambda r: (r["role"], r["plane"], r["run_id"]))
        start = (page - 1) * page_size
        return {**state, "result": self.result_info(result_id),
                "items": [self.run_info(r) for r in rows[start:start + page_size]],
                "total": len(rows), "page": page, "page_size": page_size}

    def run(self, plane: str, run_id: str) -> dict:
        state = self.availability()
        if not state["available"]:
            return {**state, "run": None, "summary": None, "substitutes": [], "notice": None}
        rows = self.by_run.get((plane, run_id))
        if not rows:
            raise KeyError(run_id)
        info = self.run_info(rows[0])
        directory = contained(self.directory, rows[0]["artifact_path"])
        summary_path = contained(directory, "summary.json")
        summary = json.loads(summary_path.read_text()) if summary_path.is_file() else None
        substitutes = []
        if info["status"] == "archived_only" and directory.is_dir():
            for path in sorted(directory.glob("*.json")):
                safe = contained(directory, path.name)
                substitutes.append({"name": path.name, "data": json.loads(safe.read_text())})
        summary_source = "summary.json" if summary is not None else None
        if summary is None:
            candidates = [(artifact["name"], value) for artifact in substitutes
                          for value in preserved_summaries(artifact["data"], run_id)]
            if len(candidates) == 1:
                summary_source, summary = candidates[0]
        return {**state, "run": info, "summary": summary, "substitutes": substitutes,
                "summary_source": summary_source,
                "relations": [dict(r) for r in rows], "notice": None if summary is not None else (
                    "No se conserva un summary individual; se muestran los artefactos "
                    "sustitutos registrados." if substitutes else
                    "El summary no está disponible en esta copia del archivo."
                )}
