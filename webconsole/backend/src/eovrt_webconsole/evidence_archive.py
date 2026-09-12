"""Lectura local del archivo curado. No importa clientes de los servicios."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

import yaml

from eovrt_webconsole.evidence import CSV_FILES, EvidenceRegistry
from eovrt_webconsole.evidence_metrics import campo_de, leer_metricas


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
        self.titles: dict[str, str | None] = {}
        self.reclamos: dict[str, str | None] = {}
        # Fuera del archivo congelado, por la misma razón que `consola.yaml`:
        # lo edita una persona y `self.directory` tiene integridad por hash.
        titles_path = registry.config_dir / "titulos.yaml"
        if titles_path.is_file():
            for row in (yaml.safe_load(titles_path.read_text()) or {}).get("resultados", []):
                self.titles[row["result_id"]] = row.get("titulo")
                self.reclamos[row["result_id"]] = row.get("reclamo")
        # El recorrido del argumento del informe: 4 pasos + respaldo instrumental,
        # también fuera del archivo congelado (lo edita una persona).
        self.recorrido_cfg: dict = {}
        recorrido_path = registry.config_dir / "recorrido.yaml"
        if recorrido_path.is_file():
            self.recorrido_cfg = yaml.safe_load(recorrido_path.read_text()) or {}
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
        archivos = (self.directory / "artifacts").is_dir() and all(
            (self.directory / "collections" / name).is_file() for name in CSV_FILES
        )
        available = self.registry.available and archivos
        # El remedio depende de CUÁL de los dos estados es (R-31): desde que
        # `registry.available` mira contenido, esto también dispara con los
        # cuatro CSV presentes y sin una sola fila — y ahí "restauralo del
        # backup" manda a reponer algo que no falta. Con los archivos presentes
        # el único estado que queda es "sin filas", porque el registro lee de
        # ESTE mismo directorio. Se dice el estado que se midió y el remedio que
        # le corresponde, nunca uno por el otro.
        remedio = (
            "Los archivos están pero el inventario no trae una sola fila: regeneralo con "
            "`python3 tools/evidence_runs.py sync`"
            if archivos else
            "Restauralo desde la capa de evidencia del backup (docs/operacion/126)"
        )
        return {
            "available": available,
            "message": None if available else (
                f"Archivo de evidencia no disponible o incompleto: {self.directory}. "
                f"{remedio} y reiniciá la consola."
            ),
        }

    def result_info(self, result_id: str) -> dict:
        rows = self.by_result[result_id]
        return {
            "result_id": result_id,
            "index": result_id.split("/", 1)[0],
            "etiqueta": etiqueta(result_id),
            "titulo": self.titles.get(result_id) or None,
            "reclamo": self.reclamos.get(result_id) or None,
            "n_runs": len({(r["plane"], r["run_id"]) for r in rows}),
            "n_rows": len(rows),
            "roles": dict(sorted(Counter(r["role"] for r in rows).items())),
            "documents": sorted(self.documents[result_id]),
            "source_refs": sorted({r["source_ref"] for r in rows}),
            "metricas": leer_metricas(self.root / f"results/{result_id}/metrics.json"),
        }

    def _cifra(self, paso: dict) -> dict:
        """Leída del metrics.json, o citada con su fuente. Nunca otra cosa."""
        if paso.get("leer"):
            valores = [campo_de(self.root / f"results/{item['result_id']}/metrics.json",
                                item["campo"]) for item in paso["leer"]]
            texto = " → ".join(f"{v:.3f}".replace(".", ",") if v is not None else "—"
                               for v in valores)
            return {"cifra": texto, "cifra_origen": "leida", "fuente": None}
        return {"cifra": paso.get("cifra"), "cifra_origen": "citada",
                "fuente": paso.get("fuente")}

    def paso_de(self, result_id: str) -> dict | None:
        """El paso del recorrido que cita este resultado, con su cifra — o
        `None` si el resultado no sostiene ninguno de los 4 pasos del argumento
        (instrumento, ensayo, plataforma, o un resultado que sólo aparece en el
        respaldo instrumental).

        Usado por `GET /api/runs/grupos` (Task 7): la cifra de un grupo es
        siempre la del paso que lo cita, nunca una que se recalcule acá.
        """
        paso = next((p for p in self.recorrido_cfg.get("pasos", [])
                     if result_id in p.get("resultados", [])), None)
        if paso is None:
            return None
        return {"n": paso["n"], "cifra_label": paso.get("cifra_label"), **self._cifra(paso)}

    def recorrido(self) -> dict:
        state = self.availability()
        if not state["available"]:
            return {**state, "pasos": [], "respaldo": None, "indices": []}
        pasos = [{
            "n": paso["n"], "titulo": paso["titulo"], "claim": paso["claim"],
            "cifra_label": paso.get("cifra_label"), "cifra_nota": paso.get("cifra_nota"),
            "n_resultados": len(paso["resultados"]),
            "indices": sorted({r.split("/", 1)[0] for r in paso["resultados"]}),
            **self._cifra(paso),
        } for paso in self.recorrido_cfg.get("pasos", [])]
        respaldo_cfg = self.recorrido_cfg.get("respaldo_instrumental", {})
        # El respaldo no tiene una ruta `/paso` propia: a diferencia de los cuatro
        # pasos del argumento (que se detallan vía `/api/evidencia/paso?n=`), su
        # desglose completo viaja acá mismo, o no hay dónde pedirlo.
        respaldo_resultados = [self.result_info(r) for r in respaldo_cfg.get("resultados", [])
                                if r in self.by_result]
        indices: dict[str, int] = defaultdict(int)
        for result_id in self.by_result:
            indices[result_id.split("/", 1)[0]] += 1
        return {**state, "pasos": pasos, "respaldo": {
            "titulo": respaldo_cfg.get("titulo"), "claim": respaldo_cfg.get("claim"),
            "n_resultados": len(respaldo_resultados), "resultados": respaldo_resultados,
        }, "indices": [{"id": k, "n_results": v} for k, v in sorted(indices.items())]}

    def paso(self, n: int) -> dict:
        # Igual que `recorrido()` y `result()`: primero la disponibilidad del
        # archivo. Si `recorrido.yaml` no cargó (config ausente o mal apuntada),
        # `recorrido_cfg` está vacío y CUALQUIER `n` daría "no encontrado" — hay
        # que decir "el archivo no está disponible", no "ese paso no existe".
        state = self.availability()
        if not state["available"]:
            return {**state, "paso": None, "resultados": [], "n_pasos": 0}
        pasos = self.recorrido_cfg.get("pasos", [])
        paso = next((p for p in pasos if p["n"] == n), None)
        if paso is None:
            raise KeyError(n)
        # Cuántos pasos hay lo decide `recorrido.yaml`: la pantalla decía "paso
        # N de 4" con el 4 hardcodeado, y un paso nuevo la dejaba mintiendo.
        return {**state, "n_pasos": len(pasos), "paso": {
            "n": paso["n"], "titulo": paso["titulo"], "claim": paso["claim"],
            "cifra_label": paso.get("cifra_label"), "cifra_nota": paso.get("cifra_nota"),
            **self._cifra(paso),
        }, "resultados": [self.result_info(r) for r in paso["resultados"]
                          if r in self.by_result]}

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
