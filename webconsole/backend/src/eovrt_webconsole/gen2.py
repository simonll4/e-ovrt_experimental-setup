"""La evidencia de la generación 2 (doc 135), leída exclusivamente del disco local.

Dos fuentes, las dos versionadas en este repo:

- el catálogo de pre-registros: `experiments/evidencia/<ID>/prueba.yaml` (doc 134);
- lo que dejó el driver al correr cada prueba: `results/gen2/<ID>/` (`resultado.json`,
  `corridas.json`, `entorno.json`, `comandos.txt`, `logs/`, `evals/`, `capturas/`).

Como `/api/evidencia`, no consulta ningún servicio: funciona con los tres planos
apagados. Tampoco calcula nada: devuelve lo que dicen los archivos. Una prueba que
todavía no corrió aparece igual (`estado: sin_correr`), con su pre-registro; una de
contraste que no se regenera (`registro: no_se_regenera`) trae su cifra de la
generación 1 (`gen1.cifras`) y el motivo, los dos escritos en el pre-registro.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

ID_PRUEBA = re.compile(r"^[A-Z]+-\d{2}$")
# Lo único que se sirve desde la carpeta de una prueba: texto legible e imágenes.
EXTENSIONES = {
    ".json": "application/json",
    ".yaml": "text/plain; charset=utf-8",
    ".yml": "text/plain; charset=utf-8",
    ".txt": "text/plain; charset=utf-8",
    ".log": "text/plain; charset=utf-8",
    ".md": "text/plain; charset=utf-8",
    ".csv": "text/plain; charset=utf-8",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}
# Carpetas de la prueba que la consola lista (el resto queda accesible por su ruta).
CARPETAS = ("logs", "evals", "capturas")
MAX_LISTADO = 500
MAX_COMANDOS = 200_000  # bytes de comandos.txt que se devuelven (el final, que es lo último)
# Lo que se muestra de cada toma de una prueba en vivo (`evals/tomas.json`), tal cual está escrito.
CAMPOS_TOMA = ("escena", "session_id", "remera", "stream", "motor", "camara", "modelo", "encuadre",
               "por_condicion", "como_se_esperaba", "alertas_antes_de_la_accion", "ensayo_demo")
CAMPOS_ALERTA = ("condicion", "accion", "primera_evidencia_a_confirmacion_ms", "accion_a_confirmacion_ms",
                 "confirmacion_a_broker_ms")
# La prueba que registra el equipo y el despliegue; de ahí sale la GPU cuando una prueba no la registró.
PRUEBA_PLATAFORMA = "PLAT-01"


class PruebaInexistente(KeyError):
    pass


class ArchivoNoServible(KeyError):
    pass


def _leer_json(ruta: Path) -> Any | None:
    if not ruta.is_file():
        return None
    try:
        return json.loads(ruta.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        logger.warning("gen2: %s no es JSON legible", ruta)
        return None


def _leer_yaml(ruta: Path) -> Any | None:
    if not ruta.is_file():
        return None
    try:
        return yaml.safe_load(ruta.read_text(encoding="utf-8-sig"))
    except (OSError, yaml.YAMLError):
        logger.warning("gen2: %s no es YAML legible", ruta)
        return None


class Gen2:
    """Vista de solo lectura de la generación 2."""

    def __init__(self, repo_root: Path) -> None:
        self.catalogo_dir = Path(repo_root) / "experiments" / "evidencia"
        self.resultados_dir = Path(repo_root) / "results" / "gen2"
        # Las observaciones del tribunal no viven en este repo (es público): la copia
        # canónica está en el repo privado `docs`, hermano en el workspace. Una copia
        # local en results/gen2/ (gitignorada) tiene prioridad.
        self.observaciones_rutas = (
            self.resultados_dir / "observaciones.yaml",
            Path(repo_root).parent / "docs" / "observaciones-tribunal" / "observaciones.yaml",
        )

    # --- catálogo y resultados --------------------------------------------------------

    def _catalogo(self) -> dict[str, dict]:
        pruebas: dict[str, dict] = {}
        if not self.catalogo_dir.is_dir():
            return pruebas
        for ruta in sorted(self.catalogo_dir.glob("*/prueba.yaml")):
            if ruta.parent.name.startswith("_"):
                continue
            datos = _leer_yaml(ruta)
            pid = (datos or {}).get("id") if isinstance(datos, dict) else None
            if not isinstance(pid, str) or not ID_PRUEBA.match(pid) or pid != ruta.parent.name:
                logger.warning("gen2: pre-registro inválido en %s", ruta)
                continue
            pruebas[pid] = datos
        return pruebas

    def _dir(self, pid: str) -> Path:
        return self.resultados_dir / pid

    @staticmethod
    def _gen1(datos: dict) -> dict:
        gen1 = datos.get("gen1") or {}
        ref = gen1.get("referencia") or {}
        return {
            "result_id": gen1.get("result_id"),
            "doc": gen1.get("doc"),
            "relacion": gen1.get("relacion"),
            "motivo": gen1.get("motivo"),
            "referencia": ref.get("fuente") or ref.get("archivo"),
            "nota": ref.get("nota"),
            # La cifra vigente de una prueba que no se regenera, tal cual el pre-registro.
            "cifras": [c for c in gen1.get("cifras") or [] if isinstance(c, dict)],
        }

    def _fila(self, pid: str, datos: dict) -> dict:
        resultado = _leer_json(self._dir(pid) / "resultado.json")
        resultado = resultado if isinstance(resultado, dict) else {}
        return {
            "id": pid,
            "titulo": datos.get("titulo"),
            "fase": datos.get("fase"),
            "familia": datos.get("familia"),
            "informe": datos.get("informe") or [],
            "pregunta": datos.get("pregunta"),
            "esperado": datos.get("esperado"),
            "registro": datos.get("estado", "activa"),
            "no_se_regenera": datos.get("no_se_regenera"),
            "depende_de": datos.get("depende_de") or [],
            "gen1": self._gen1(datos),
            "estado": resultado.get("estado", "sin_correr"),
            "generado": resultado.get("generado"),
            "resumen": resultado.get("resumen") or [],
            "veredicto": resultado.get("veredicto"),
        }

    def titulos(self) -> dict[str, str]:
        """{id de prueba: título}, del pre-registro. Sin cargar sus resultados."""
        return {pid: datos["titulo"] for pid, datos in self._catalogo().items()
                if isinstance(datos.get("titulo"), str)}

    def pruebas(self) -> list[dict]:
        return [self._fila(pid, datos) for pid, datos in sorted(self._catalogo().items())]

    def observaciones(self) -> dict:
        ruta = next((r for r in self.observaciones_rutas if r.is_file()), None)
        datos = _leer_yaml(ruta) if ruta else None
        if not isinstance(datos, dict):
            return {"available": False, "observaciones": [],
                    "message": "No está el archivo de observaciones (docs/observaciones-tribunal/observaciones.yaml)."}
        filas = {f["id"]: f for f in self.pruebas()}
        observaciones = []
        for obs in datos.get("observaciones") or []:
            referidas = []
            for pid in obs.get("pruebas") or []:
                fila = filas.get(pid)
                referidas.append({
                    "id": pid,
                    "titulo": fila["titulo"] if fila else None,
                    "estado": fila["estado"] if fila else "desconocida",
                    "registro": fila["registro"] if fila else None,
                    "veredicto": fila["veredicto"] if fila else None,
                })
            observaciones.append({**obs, "pruebas": referidas})
        return {"available": True, "observaciones": observaciones}

    # --- detalle de una prueba --------------------------------------------------------

    def _listar(self, base: Path) -> dict[str, list[str]]:
        listado: dict[str, list[str]] = {}
        for nombre in CARPETAS:
            carpeta = base / nombre
            if not carpeta.is_dir():
                listado[nombre] = []
                continue
            archivos = sorted(
                p.relative_to(base).as_posix() for p in carpeta.rglob("*")
                if p.is_file() and p.suffix.lower() in EXTENSIONES
            )
            listado[nombre] = archivos[:MAX_LISTADO]
        return listado

    @staticmethod
    def _lecturas(resultado: Any) -> list[dict]:
        """Las otras lecturas de la prueba (`variantes` del resultado: por sujeto, otra regla…),
        cada una con su resumen tal cual. La lectura principal es el `resumen` de la prueba."""
        variantes = resultado.get("variantes") if isinstance(resultado, dict) else None
        if not isinstance(variantes, dict):
            return []
        return [{"nombre": nombre, "resumen": v.get("resumen") or []}
                for nombre, v in variantes.items() if isinstance(v, dict)]

    @staticmethod
    def _tomas(base: Path) -> list[dict]:
        """Las tomas de una prueba en vivo (`evals/tomas.json`): qué se esperaba de cada una, qué
        pasó y cuánto tardó cada alerta. Solo selecciona campos; no calcula."""
        crudo = _leer_json(base / "evals" / "tomas.json")
        if not isinstance(crudo, list):
            return []
        tomas = []
        for toma in crudo[:MAX_LISTADO]:
            if not isinstance(toma, dict):
                continue
            fila = {k: toma[k] for k in CAMPOS_TOMA if k in toma}
            sujeto = toma.get("sujeto")
            latencia = toma.get("latencia")
            fila["sujeto_como_se_esperaba"] = sujeto.get("como_se_esperaba") if isinstance(sujeto, dict) else None
            fila["fps_efectivos"] = latencia.get("fps_efectivos") if isinstance(latencia, dict) else None
            fila["alertas"] = [{k: a.get(k) for k in CAMPOS_ALERTA}
                               for a in toma.get("alertas") or [] if isinstance(a, dict)]
            tomas.append(fila)
        return tomas

    def _gpu_de_la_plataforma(self, entorno: Any) -> str | None:
        """La GPU que registró PLAT-01, para la prueba cuyo `entorno.json` no la trae (la foto
        del entorno solo la ve cuando hay una instancia de detección levantada)."""
        if not isinstance(entorno, dict) or entorno.get("gpu"):
            return None
        plataforma = _leer_json(self._dir(PRUEBA_PLATAFORMA) / "entorno.json")
        gpu = plataforma.get("gpu") if isinstance(plataforma, dict) else None
        return gpu if isinstance(gpu, str) and gpu else None

    def prueba(self, pid: str) -> dict:
        if not ID_PRUEBA.match(pid):
            raise PruebaInexistente(pid)
        catalogo = self._catalogo()
        base = self._dir(pid)
        if pid not in catalogo and not base.is_dir():
            raise PruebaInexistente(pid)
        datos = catalogo.get(pid) or (_leer_yaml(base / "prueba.yaml") or {})
        texto_catalogo = (self.catalogo_dir / pid / "prueba.yaml")
        texto_catalogo = texto_catalogo.read_text(encoding="utf-8") if texto_catalogo.is_file() else None
        copia = base / "prueba.yaml"
        texto_copia = copia.read_text(encoding="utf-8") if copia.is_file() else None
        comandos = base / "comandos.txt"
        texto_comandos = None
        if comandos.is_file():
            crudo = comandos.read_bytes()
            texto_comandos = crudo[-MAX_COMANDOS:].decode("utf-8", errors="replace")
        corridas = _leer_json(base / "corridas.json")
        resultado = _leer_json(base / "resultado.json")
        entorno = _leer_json(base / "entorno.json")
        return {
            **self._fila(pid, datos),
            "pre_registro": {
                # Lo que estaba escrito cuando corrió (la copia) manda sobre el catálogo actual.
                "texto": texto_copia or texto_catalogo,
                "origen": "copia_al_correr" if texto_copia else "catalogo",
                "coincide_con_catalogo": (texto_copia == texto_catalogo) if texto_copia and texto_catalogo else None,
            },
            "resultado": resultado,
            "lecturas": self._lecturas(resultado),
            "tomas": self._tomas(base),
            "corridas": (corridas or {}).get("corridas") if isinstance(corridas, dict) else None,
            "entorno": entorno,
            "gpu_de_la_plataforma": self._gpu_de_la_plataforma(entorno),
            "plataforma": _leer_json(base / "plataforma.json"),
            "comandos": texto_comandos,
            "archivos": self._listar(base) if base.is_dir() else {n: [] for n in CARPETAS},
        }

    def archivo(self, pid: str, ruta: str) -> tuple[Path, str]:
        """(archivo, media type) dentro de la carpeta de la prueba, o ArchivoNoServible."""
        if not ID_PRUEBA.match(pid):
            raise ArchivoNoServible(ruta)
        base = self._dir(pid).resolve()
        try:
            candidato = (base / ruta).resolve()
        except (OSError, RuntimeError, ValueError) as exc:
            raise ArchivoNoServible(ruta) from exc
        if not candidato.is_relative_to(base) or candidato == base:
            raise ArchivoNoServible(ruta)
        media_type = EXTENSIONES.get(candidato.suffix.lower())
        if media_type is None or not candidato.is_file():
            raise ArchivoNoServible(ruta)
        return candidato, media_type
