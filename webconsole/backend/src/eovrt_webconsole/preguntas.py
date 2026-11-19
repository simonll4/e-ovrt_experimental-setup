"""Las siete preguntas de la consola de evidencia (plan de la consola, §2 y §9).

Lee `results/evidence-vista/preguntas.yaml`, que declara la portada y las siete páginas, y resuelve
cada cifra que nombra contra lo que dejó el driver en `results/gen2/<ID>/`. Ninguna cifra se escribe
a mano: el archivo dice de qué prueba y de qué clave sale, y esta vista la lee al mostrarla.

Como `gen2.py`, es de solo lectura y no consulta servicios. Una referencia que no resuelve no rompe
la pantalla: vuelve con `ok: false` y su motivo, y queda listada en `errores` (los tests exigen que
el archivo real no tenga ninguna).
"""
from __future__ import annotations

import json
import logging
import re
import subprocess
from pathlib import Path
from typing import Any

import yaml

from eovrt_webconsole.gen2 import Gen2

logger = logging.getLogger(__name__)

ARCHIVOS = {"resultado": "resultado.json", "entorno": "entorno.json", "plataforma": "plataforma.json"}
FORMATOS = {"numero", "signo", "porcentaje", "verificado"}
PRESENTACION = ("etiqueta", "decimales", "formato", "unidad")
VER = re.compile(r"[a-z_]+=[A-Za-z0-9_-]+")
MARCADOR = re.compile(r"\{([a-z0-9_]+)\}")


def _leer_json(ruta: Path) -> Any | None:
    if not ruta.is_file():
        return None
    try:
        return json.loads(ruta.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        logger.warning("preguntas: %s no es JSON legible", ruta)
        return None


def _camino(datos: Any, clave: str) -> Any:
    """La clave tal cual y, si no está, como camino con puntos (`host.cpu`)."""
    if isinstance(datos, dict) and clave in datos:
        return datos[clave]
    actual = datos
    for parte in clave.split("."):
        if not isinstance(actual, dict) or parte not in actual:
            raise KeyError(clave)
        actual = actual[parte]
    return actual


class _Resolutor:
    """Resuelve las referencias de una lectura del archivo, con los resultados en memoria."""

    def __init__(self, gen2: Gen2) -> None:
        self.gen2 = gen2
        self._archivos: dict[tuple[str, str], Any] = {}
        self._filas: list[dict] | None = None
        self.errores: list[str] = []

    def filas(self) -> list[dict]:
        if self._filas is None:
            self._filas = self.gen2.pruebas()
        return self._filas

    def _archivo(self, prueba: str, archivo: str) -> Any:
        clave = (prueba, archivo)
        if clave not in self._archivos:
            self._archivos[clave] = _leer_json(self.gen2.resultados_dir / prueba / ARCHIVOS[archivo])
        return self._archivos[clave]

    def _lectura(self, ref: dict, prueba: str, variante: str | None) -> tuple[Any, str | None]:
        archivo = ref.get("archivo", "resultado")
        if archivo not in ARCHIVOS:
            raise LookupError(f"archivo desconocido «{archivo}»")
        clave = ref.get("clave")
        if not isinstance(clave, str) or not clave:
            raise LookupError("falta la clave")
        datos = self._archivo(prueba, archivo)
        if not isinstance(datos, dict):
            raise LookupError(f"{prueba} no tiene {ARCHIVOS[archivo]}")
        if archivo != "resultado":
            return _camino(datos, clave), None
        if variante:
            datos = (datos.get("variantes") or {}).get(variante)
            if not isinstance(datos, dict):
                raise LookupError(f"{prueba} no tiene la variante «{variante}»")
        for cifra in datos.get("resumen") or []:
            if isinstance(cifra, dict) and cifra.get("clave") == clave:
                return cifra.get("valor"), cifra.get("unidad")
        return _camino(datos.get("metricas") or {}, clave), None

    def _calculo(self, ref: dict, donde: str) -> dict:
        calculo = ref["calculo"]
        if calculo == "pruebas":
            return {"valor": len(self.filas())}
        if calculo == "veredicto":
            buscado = ref.get("valor")
            return {"valor": sum(1 for f in self.filas()
                                 if ((f.get("veredicto") or {}).get("confirmado") or {}).get("valor") == buscado)}
        if calculo == "contar":
            partes = [self.resolver(r, None, None, f"{donde}.de[{i}]") for i, r in enumerate(ref.get("de") or [])]
            if not partes or not all(p["ok"] for p in partes):
                raise LookupError("alguna referencia del conteo no resuelve")
            return {"valor": sum(1 for p in partes if p["valor"] is True or p["valor"] == "ok"),
                    "total": len(partes)}
        raise LookupError(f"cálculo desconocido «{calculo}»")

    def resolver(self, ref: Any, prueba_fila: str | None, variante_fila: str | None, donde: str) -> dict:
        if isinstance(ref, str):
            ref = {"clave": ref}
        if not isinstance(ref, dict):
            return self._falla({}, None, donde, "referencia ilegible")
        salida = {k: ref[k] for k in PRESENTACION if k in ref}
        if ref.get("formato") is not None and ref["formato"] not in FORMATOS:
            return self._falla(salida, None, donde, f"formato desconocido «{ref['formato']}»")
        if "calculo" in ref:
            try:
                return {**salida, **self._calculo(ref, donde), "prueba": None, "ok": True}
            except LookupError as exc:
                return self._falla(salida, None, donde, str(exc))
        prueba = ref.get("prueba") or prueba_fila
        # La variante de la fila vale para las celdas de la misma prueba; una celda que nombra otra
        # prueba declara la suya.
        variante = ref["variante"] if "variante" in ref else (variante_fila if prueba == prueba_fila else None)
        if not isinstance(prueba, str) or not prueba:
            return self._falla(salida, None, donde, "falta la prueba")
        try:
            valor, unidad = self._lectura(ref, prueba, variante)
        except LookupError as exc:
            return self._falla(salida, prueba, donde, str(exc) if not isinstance(exc, KeyError)
                               else f"{prueba} no tiene la clave «{ref.get('clave')}»")
        if valor is None or isinstance(valor, (dict, list)):
            return self._falla(salida, prueba, donde, f"«{ref.get('clave')}» de {prueba} no es una cifra")
        salida.setdefault("unidad", unidad)
        return {**salida, "valor": valor, "prueba": prueba, "ok": True}

    def _falla(self, salida: dict, prueba: str | None, donde: str, motivo: str) -> dict:
        self.errores.append(f"{donde}: {motivo}")
        return {**salida, "valor": None, "prueba": prueba, "ok": False, "error": motivo}


def _celda(celda: Any) -> list | None:
    """Una celda es nada, una clave, una referencia o una lista de referencias."""
    if celda is None:
        return None
    return celda if isinstance(celda, list) else [celda]


def version_resultados(repo_root: Path) -> dict | None:
    """El commit de los resultados: el último que tocó `results/gen2`, si hay git; si no (la consola
    en contenedor no lo trae), el commit en que está el repositorio, leído de `.git`."""
    try:
        salida = subprocess.run(
            ["git", "-C", str(repo_root), "log", "-1", "--format=%h %cs", "--", "results/gen2"],
            capture_output=True, text=True, timeout=5, check=True,
        ).stdout.split()
        if len(salida) == 2:
            return {"commit": salida[0], "fecha": salida[1], "de": "resultados"}
    except (OSError, subprocess.SubprocessError):
        pass
    git = repo_root / ".git"
    try:
        head = (git / "HEAD").read_text(encoding="utf-8").strip()
        if head.startswith("ref: "):
            ref = head[5:]
            suelta = git / ref
            if suelta.is_file():
                head = suelta.read_text(encoding="utf-8").strip()
            else:
                empaquetadas = (git / "packed-refs").read_text(encoding="utf-8").splitlines()
                head = next(l.split()[0] for l in empaquetadas if l.endswith(" " + ref))
    except (OSError, StopIteration):
        return None
    return {"commit": head[:7], "fecha": None, "de": "repositorio"} if re.fullmatch(r"[0-9a-f]{40}", head) else None


class Preguntas:
    """Vista de solo lectura de la portada y las siete preguntas."""

    def __init__(self, repo_root: Path, gen2: Gen2) -> None:
        self.repo_root = Path(repo_root)
        self.archivo = self.repo_root / "results" / "evidence-vista" / "preguntas.yaml"
        self.gen2 = gen2

    def _leer(self) -> dict | None:
        if not self.archivo.is_file():
            return None
        try:
            datos = yaml.safe_load(self.archivo.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError):
            logger.warning("preguntas: %s no es YAML legible", self.archivo)
            return None
        return datos if isinstance(datos, dict) else None

    def vista(self) -> dict:
        datos = self._leer()
        if datos is None:
            return {"available": False, "message": "No está el archivo de las preguntas "
                                                    "(results/evidence-vista/preguntas.yaml)."}
        r = _Resolutor(self.gen2)
        preguntas = [self._pregunta(p, r) for p in datos.get("preguntas") or [] if isinstance(p, dict)]
        # La campaña va del primer al último resultado medido. La prueba de plataforma no cuenta: se vuelve a
        # correr cada vez que cambia la imagen de la consola, y su fecha es la del último despliegue, no la de una
        # medición.
        fechas = sorted(f["generado"][:10] for f in r.filas()
                        if isinstance(f.get("generado"), str) and f.get("familia") != "plataforma")
        return {
            "available": True,
            "proyecto": datos.get("proyecto") or {},
            "preguntas": preguntas,
            "pie": {
                "pruebas": len(r.filas()),
                "desde": fechas[0] if fechas else None,
                "hasta": fechas[-1] if fechas else None,
                "version": version_resultados(self.repo_root),
            },
            "errores": r.errores,
        }

    def _pregunta(self, p: dict, r: _Resolutor) -> dict:
        pid = p.get("id")
        cifras = {nombre: r.resolver(ref, None, None, f"{pid}.cifras.{nombre}")
                  for nombre, ref in (p.get("cifras") or {}).items()}
        for campo in ("titular", "respuesta"):
            for nombre in MARCADOR.findall(p.get(campo) or ""):
                if nombre not in cifras:
                    r.errores.append(f"{pid}.{campo}: usa {{{nombre}}}, que no está en sus cifras")
        tablas = []
        for t, tabla in enumerate(p.get("tablas") or []):
            filas = []
            for f, fila in enumerate(tabla.get("filas") or []):
                prueba, variante = fila.get("prueba"), fila.get("variante")
                celdas = []
                for c, celda in enumerate(fila.get("celdas") or []):
                    items = _celda(celda)
                    celdas.append(None if items is None else [
                        r.resolver(ref, prueba, variante, f"{pid}.tablas[{t}].filas[{f}].celdas[{c}]")
                        for ref in items])
                pruebas = [prueba] if prueba else []
                for item in (i for c in celdas if c for i in c):
                    if item.get("prueba") and item["prueba"] not in pruebas:
                        pruebas.append(item["prueba"])
                # `ver`: una consulta para abrir los casos de esa fila en su prueba (p. ej. `causa=P-no-detectado`
                # en ERR-01: las falsas alarmas de esa causa, cada una con su clip). Solo `clave=valor` simple.
                ver = fila.get("ver")
                if ver is not None and not (isinstance(ver, str) and VER.fullmatch(ver)):
                    r.errores.append(f"{pid}.tablas[{t}].filas[{f}]: `ver` tiene que ser clave=valor")
                    ver = None
                filas.append({"nombre": fila.get("nombre"), "pruebas": pruebas, "celdas": celdas, "ver": ver})
            tablas.append({"titulo": tabla.get("titulo"), "informe": tabla.get("informe"),
                           "columnas": tabla.get("columnas") or [], "nota": tabla.get("nota"), "filas": filas})
        return {
            "id": pid,
            "titulo": p.get("titulo"),
            "informe": p.get("informe") or [],
            "titular": p.get("titular"),
            "respuesta": p.get("respuesta"),
            "cifras": cifras,
            "tablas": tablas,
            "limites": p.get("limites") or [],
        }
