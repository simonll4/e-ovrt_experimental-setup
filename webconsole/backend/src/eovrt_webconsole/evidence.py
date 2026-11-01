"""Registro curado, cargado una vez; archivar sólo cambia la visibilidad."""
from __future__ import annotations

import asyncio
import csv
import json
import logging
import os
import time
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


def _indice_gen2(archivos: list[Path]) -> dict[str, list[dict]]:
    """run_id -> las pruebas de la generación 2 que lo citan.

    Toda corrida que cita una prueba pre-registrada sostiene una cifra del informe,
    así que es `resultado` (la definición de la clase). Solo cuentan las identidades
    reales: texto no vacío. Un archivo ilegible se salta sin tumbar a los demás.
    """
    indice: dict[str, list[dict]] = defaultdict(list)
    for archivo in archivos:
        try:
            datos = json.loads(archivo.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            continue  # el driver puede estar escribiéndolo ahora mismo
        corridas = datos.get("corridas") if isinstance(datos, dict) else None
        if not isinstance(corridas, dict):
            continue
        prueba = archivo.parent.name
        vistos: set[tuple[str, str]] = set()
        for corrida in corridas.values():
            if not isinstance(corrida, dict):
                continue
            for plano, clave in (("media-plane", "media_run_id"), ("control-plane", "control_run_id")):
                run_id = corrida.get(clave)
                if isinstance(run_id, str) and run_id and (run_id, prueba) not in vistos:
                    vistos.add((run_id, prueba))
                    indice[run_id].append({
                        "collection": "generacion_2", "result_id": prueba, "role": "prueba_gen2",
                        "clase": "resultado", "plane": plano, "run_id": run_id,
                        "source_ref": f"results/gen2/{prueba}/corridas.json",
                    })
    return dict(indice)


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
        # La generación 2 vive APARTE del archivo congelado: lo que cita cada prueba
        # en `results/gen2/*/corridas.json`. No entra en `roles()`, `resultados()` ni
        # `filas()` (los conteos de la generación 1 no se mueven).
        self._gen2_dir: Path | None = None
        self._gen2_refresco_s = 1.0
        self._gen2_firma: tuple = ()
        self._gen2_revisado = float("-inf")
        self._gen2: dict[str, list[dict]] = {}
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

    def cargar_gen2(self, gen2_dir: Path, refresco_s: float = 1.0) -> None:
        """Suma lo que citan las pruebas de la generación 2 (`corridas.json`).

        El índice se rearma solo cuando cambia algún `corridas.json`: el driver lo
        escribe mientras corre, y la consola no se reinicia por eso.
        """
        self._gen2_dir = gen2_dir
        self._gen2_refresco_s = refresco_s
        self._gen2_firma = ()
        self._gen2_revisado = float("-inf")
        self._gen2 = {}

    def _filas_gen2(self, run_id: str) -> list[dict]:
        if self._gen2_dir is None:
            return []
        ahora = time.monotonic()
        if ahora - self._gen2_revisado >= self._gen2_refresco_s:
            self._gen2_revisado = ahora
            try:
                archivos = sorted(self._gen2_dir.glob("*/corridas.json"))
                firma = tuple((a.parent.name, a.stat().st_mtime_ns) for a in archivos)
            except OSError:
                archivos, firma = [], ()
            if firma != self._gen2_firma:
                self._gen2_firma = firma
                self._gen2 = _indice_gen2(archivos)
        return self._gen2.get(run_id, [])

    def _todas_las_filas(self, run_id: str) -> list[dict]:
        return [*self._rows.get(run_id, []), *self._filas_gen2(run_id)]

    def es_evidencia(self, run_id: str) -> bool:
        return run_id in self._rows or bool(self._filas_gen2(run_id))

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
            row.get("clase") or self.clase_de_rol(row["role"])
            for row in self._todas_las_filas(run_id))

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
            tuple(row.get(key, "") for key in keys) for row in self._todas_las_filas(run_id)
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
        rows = [row for run_id in run_ids for row in self._todas_las_filas(run_id)]
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


# PyYAML trae un parser en C; el de Python puro es ~10x más lento y se usa en los
# listados, que releen cientos de archivos.
_YAML_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)

# ruta -> (mtime_ns, tamaño, identidades). Clasificar las ejecuciones releía ~12.000
# archivos (822.000 líneas de JSONL) en cada pedido, ~50 s en frío: ahora solo se
# vuelve a abrir lo que cambió. Un archivo que no se pudo leer NO se guarda.
_IDENTIDADES_POR_ARCHIVO: dict[str, tuple[int, int, frozenset[str]]] = {}


def cargar_yaml(text: str):
    return yaml.load(text, Loader=_YAML_LOADER)  # SafeLoader en C o en Python


_YAML_POR_ARCHIVO: dict[str, tuple[int, int, object]] = {}


def cargar_yaml_archivo(path: Path):
    """YAML de un archivo, sin reparsearlo mientras no cambie (los manifiestos de
    ejecución son cientos y se piden en cada listado). Quien lo llama no lo muta."""
    info = path.stat()
    guardado = _YAML_POR_ARCHIVO.get(str(path))
    if guardado is not None and guardado[:2] == (info.st_mtime_ns, info.st_size):
        return guardado[2]
    datos = cargar_yaml(path.read_text(encoding="utf-8"))
    _YAML_POR_ARCHIVO[str(path)] = (info.st_mtime_ns, info.st_size, datos)
    return datos


def _identidades_de_archivo(path: Path) -> frozenset[str]:
    info = path.stat()
    guardado = _IDENTIDADES_POR_ARCHIVO.get(str(path))
    if guardado is not None and guardado[:2] == (info.st_mtime_ns, info.st_size):
        return guardado[2]
    ids: set[str] = set()
    if path.suffix == ".jsonl":
        with path.open(encoding="utf-8") as src:
            for line in src:
                if "run_id" in line:
                    ids.update(_identidades(json.loads(line)))
    else:
        text = path.read_text(encoding="utf-8")
        if "run_id" in text:
            data = json.loads(text) if path.suffix == ".json" else cargar_yaml(text)
            ids.update(_identidades(data))
    resultado = frozenset(ids)
    _IDENTIDADES_POR_ARCHIVO[str(path)] = (info.st_mtime_ns, info.st_size, resultado)
    return resultado


_SUFIJOS = frozenset({".json", ".jsonl", ".yaml", ".yml"})


def _archivos_de_identidad(directory: Path, base: Path):
    """Archivos con identidades dentro del subárbol, sin salirse de `directory`.

    os.scandir en lugar de rglob + resolve() por archivo: con ~12.000 archivos
    el resolve() solo costaba más de un segundo por pedido. Solo se resuelve lo
    que es un symlink (lo único que puede apuntar afuera).
    """
    pendientes = [directory]
    while pendientes:
        try:
            with os.scandir(pendientes.pop()) as entradas:
                entradas = list(entradas)
        except OSError as exc:
            logger.warning("No se pudo listar %s: %s", directory, exc)
            continue
        for entrada in entradas:
            if entrada.is_symlink():
                ruta = Path(entrada.path)
                if not ruta.resolve().is_relative_to(base):
                    continue
                if ruta.is_dir():
                    pendientes.append(ruta)
                    continue
            elif entrada.is_dir(follow_symlinks=False):
                pendientes.append(Path(entrada.path))
                continue
            if os.path.splitext(entrada.name)[1] in _SUFIJOS and entrada.is_file():
                yield Path(entrada.path)


def corridas_consolidadas(directory: Path) -> list[str]:
    """Recorre todo el subárbol local; nunca abre destinos de archivos .ref.

    Incluye identidades anidadas en JSON, JSONL y YAML. Las líneas JSONL se
    procesan individualmente para no cargar detecciones y métricas completas.
    """
    ids: set[str] = set()
    for path in _archivos_de_identidad(directory, directory.resolve()):
        try:
            ids.update(_identidades_de_archivo(path))
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
            manifest = cargar_yaml_archivo(directory / "manifest.effective.yaml")
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


class ClasificacionCompartida:
    """Un único cálculo en vuelo, compartido por los pedidos concurrentes.

    Clasificar las ejecuciones son miles de `stat`/lecturas cortas. Con varios hilos
    a la vez el GIL se disputa en cada una (efecto convoy): uno tardaba 1,2 s, dos
    5 s y cuatro 20 s, y Experimentos pide el listado dos veces al abrir. Acá el
    cálculo corre una vez, en un hilo, y quienes llegan mientras tanto esperan el
    mismo resultado. `ttl_s` además sirve el último resultado unos segundos; un
    error nunca se guarda.
    """

    def __init__(self, calculo, ttl_s: float = 2.0, reloj=time.monotonic) -> None:
        self._calculo = calculo
        self._ttl_s = ttl_s
        self._reloj = reloj
        self._guardado: tuple[tuple, float, object] | None = None  # (clave, instante, valor)
        self._en_vuelo: tuple[tuple, asyncio.Future] | None = None

    async def obtener(self, runs_dir: Path, *claves):
        clave = (runs_dir, *claves)
        guardado = self._guardado
        if guardado and guardado[0] == clave and self._reloj() - guardado[1] < self._ttl_s:
            return guardado[2]
        if self._en_vuelo and self._en_vuelo[0] == clave:
            return await asyncio.shield(self._en_vuelo[1])
        tarea = asyncio.ensure_future(asyncio.to_thread(self._calculo, runs_dir, *claves))
        self._en_vuelo = (clave, tarea)
        try:
            valor = await asyncio.shield(tarea)
        finally:
            if self._en_vuelo and self._en_vuelo[1] is tarea:
                self._en_vuelo = None
        self._guardado = (clave, self._reloj(), valor)
        return valor
