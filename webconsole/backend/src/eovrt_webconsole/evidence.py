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
CLASES: tuple[str, ...] = ("resultado", "instrumento", "ensayo", "plataforma", "sin_clasificar")


def coincide_vista(evidence: dict, vista: Vista) -> bool:
    return vista == "todas" or evidence["is_evidence"] == (vista == "evidencia")


def cabeceras_de_disponibilidad(registry: EvidenceRegistry) -> dict[str, str]:
    """Los dos archivos de los que depende toda clasificación, declarados.

    Sin ellos la pantalla sigue armando frases perfectas —"472 corridas
    agrupadas en 1 resultados", chip "Fuera del registro 472"— construidas
    enteras sobre un archivo ausente. Son dos estados distintos: el archivo
    CONGELADO (`available`, los cuatro CSV) y la configuración MUTABLE
    (`clasificacion.yaml`, que una persona edita a mano y cuya ausencia no baja
    `available`). Los dos viajan, y la pantalla los declara.

    Los dos miran CONTENIDO, no sólo existencia (R-31): un archivo presente pero
    vacío —cuatro CSV sin una sola fila, o un `roles:` renombrado o vaciado a
    mano— carga sin excepción, deja TODO en `sin_clasificar` y era el último
    camino por el que la pantalla afirmaba una clasificación sin advertir nada.

    Un booleano no alcanza para el estado INTERMEDIO: con 1 de 21 roles
    declarados la clasificación está disponible —hay una clasificación, y es
    real— pero 1.435 corridas se muestran «Fuera del registro» sin que nada lo
    diga. Por eso viaja también el CONTEO (`X-Clasificacion-Roles`, "N/M" =
    roles sin clasificar sobre roles del registro): no hace falta un tercer
    umbral arbitrario, alcanza con que la pantalla pueda decir cuántos son.
    `roles_sin_clasificar()` ya devolvía la lista; lo que faltaba era exponerla.
    """
    sin_clasificar = registry.roles_sin_clasificar()
    return {
        "X-Evidence-Available": str(registry.available).lower(),
        "X-Clasificacion-Available": str(registry.clasificacion_disponible).lower(),
        "X-Clasificacion-Roles": f"{len(sin_clasificar)}/{len(registry.roles())}",
    }


def clase_mas_fuerte(clases) -> str:
    """La primera clase presente en el orden de precedencia de `CLASES`.

    Una corrida puede cumplir dos roles y un manifiesto agrupar ejecuciones de
    clases distintas: la regla es siempre la misma —si algo es Resultado en
    algún lado, es Resultado— y vive acá una sola vez para que Corridas,
    Experimentos y `describe()` no la reimplementen cada uno a su manera.
    Un conjunto vacío es `sin_clasificar`: el default, nunca una heurística.
    """
    presentes = set(clases)
    return next((c for c in CLASES if c in presentes), "sin_clasificar")


class EvidenceRegistry:
    def __init__(self, archive_dir: Path, config_dir: Path | None = None):
        # `archive_dir` es el archivo CONGELADO: tiene integridad por hash
        # (`files.sha256`) y `tools/evidence_runs.py --check` la verifica. La
        # configuración de la vista es MUTABLE —`titulos.yaml` lo edita una
        # persona— así que vive fuera, en `results/evidence-vista/`. Meterla
        # adentro rompía el check en cada edición.
        self.config_dir = config_dir or archive_dir.parent / "evidence-vista"
        presentes = all((archive_dir / "collections" / name).is_file() for name in CSV_FILES)
        self._rows: dict[str, list[dict]] = defaultdict(list)
        self._force: dict[str, bool] = {}
        if presentes:
            for name in CSV_FILES:
                with (archive_dir / "collections" / name).open(encoding="utf-8", newline="") as src:
                    for row in csv.DictReader(src):
                        self._rows[row["run_id"]].append(row)
        # CONTENIDO, no existencia (R-31): cuatro CSV con encabezado y ninguna
        # fila cargan sin error y dejan cada corrida fuera del registro. Que eso
        # NO baje `available` era el único camino que quedaba para afirmar una
        # clasificación —"Fuera del registro 472"— sin una sola advertencia.
        self.available = presentes and bool(self._rows)
        if not self.available:
            logger.warning(
                "Registro de evidencia %s: %s/collections",
                "ausente o incompleto" if not presentes else "presente pero sin filas",
                archive_dir,
            )

        overrides = self.config_dir / "consola.yaml"
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

        # La clase se declara por ROL, no por corrida: 21 decisiones en vez de
        # 1.436, y una corrida nueva hereda la clase de su rol sin tocar nada.
        self._clase_de_rol: dict[str, str] = {}
        self._clase_forzada: dict[str, str] = {}
        clasificacion = self.config_dir / "clasificacion.yaml"
        # `clasificacion.yaml` es MUTABLE y lo edita una persona: si falta, el
        # registro carga igual (`available` sigue en True) y TODO cae a
        # `sin_clasificar` en silencio. Eso se DECLARA en la pantalla, así que
        # el estado tiene que viajar — de ahí este flag, separado de `available`.
        if clasificacion.is_file():
            data = yaml.safe_load(clasificacion.read_text(encoding="utf-8")) or {}
            for clase, roles in (data.get("roles") or {}).items():
                if clase not in CLASES:
                    raise ValueError(f"clasificacion.yaml: clase desconocida {clase}")
                for rol in roles:
                    if rol in self._clase_de_rol:
                        raise ValueError(f"clasificacion.yaml: {rol} declarado dos veces")
                    self._clase_de_rol[rol] = clase
            for clase, entradas in (data.get("excepciones") or {}).items():
                if clase not in CLASES:
                    raise ValueError(f"clasificacion.yaml: clase desconocida {clase}")
                for entrada in entradas:
                    self._clase_forzada[entrada] = clase

        # Disponibilidad por CONTENIDO (R-31). El archivo existe justamente
        # porque lo edita una persona: si `roles:` se renombra o se vacía a
        # mano, el YAML carga, no salta ninguna excepción y todas las corridas
        # caen a `sin_clasificar` sin que nada lo advierta. El detector ya
        # existía sin cablear: `roles_sin_clasificar()`. La clasificación está
        # disponible cuando declara roles Y alcanza a ALGUNO de los que el
        # registro realmente trae — declarar roles que ya nadie usa clasifica
        # tan poco como no declarar ninguno. Con el registro vacío no hay roles
        # que alcanzar y el aviso lo da `available`, que ya está en False.
        alcanza_al_registro = (
            not self.roles() or len(self.roles_sin_clasificar()) < len(self.roles())
        )
        self.clasificacion_disponible = bool(self._clase_de_rol) and alcanza_al_registro

    def es_evidencia(self, run_id: str) -> bool:
        return run_id in self._rows

    def clase_de_rol(self, rol: str) -> str:
        return self._clase_de_rol.get(rol, "sin_clasificar")

    def clase_de(self, run_id: str) -> str:
        """La clase MÁS FUERTE entre los roles de la corrida.

        Una corrida puede cumplir dos roles (es evidencia de dos resultados). El
        orden de `CLASES` es la precedencia: si algo es Resultado en algún lado,
        es Resultado.
        """
        if run_id in self._clase_forzada:
            return self._clase_forzada[run_id]
        return clase_mas_fuerte(
            self.clase_de_rol(row["role"]) for row in self._rows.get(run_id, []))

    def clase_de_slug(self, slug: str, default: str = "sin_clasificar") -> str:
        """La excepción explícita del slug, o lo que decida el llamador.

        Los slugs no tienen rol en el registro (no producen corridas de
        evidencia), así que su clase sale sólo de `clasificacion.yaml`.
        """
        return self._clase_forzada.get(slug, default)

    def roles(self) -> list[str]:
        """Los roles que el registro realmente trae — el denominador de todo
        conteo de clasificación. No son los roles DECLARADOS en
        `clasificacion.yaml`: declarar un rol que ya nadie usa no clasifica
        nada."""
        return sorted({row["role"] for rows in self._rows.values() for row in rows})

    def roles_sin_clasificar(self) -> list[str]:
        return [rol for rol in self.roles() if rol not in self._clase_de_rol]

    def filas(self) -> list[dict]:
        """Relaciones completas del CSV; preserva los roles y las pertenencias múltiples."""
        return [dict(row) for rows in self._rows.values() for row in rows]

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
            # La MÁS FUERTE entre los roles de las corridas pedidas (Task 7): un
            # `run_ids` de una sola corrida usa la precedencia de `clase_de`
            # directo; describir varias a la vez (como en `resultados()`) toma
            # la más fuerte del conjunto, con la misma regla de precedencia.
            "clase": clase_mas_fuerte(self.clase_de(run_id) for run_id in run_ids),
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
