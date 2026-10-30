"""Catálogo de pruebas: `experiments/evidencia/<ID>/prueba.yaml` (pre-registro, doc 134 §4).

Una prueba se escribe y se commitea ANTES de correr. El driver la copia a su carpeta de
resultados al arrancar y, si después alguien la cambia, se niega a seguir sobre la misma
carpeta (ver `registro.Carpeta.preparar`).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

ESQUEMA = "prueba.gen2.v1"
FAMILIAS = (
    "clips",
    "imagenes",
    "nivel_a",
    "nivel_a_video",
    "clase_nueva",
    "integridad",
    "plataforma",
    "analisis",
    "vivo",
    "rodaje",
    "figuras",
)
# `no_se_regenera`: prueba de contraste cuya cifra vigente es la de la generación 1 (doc 134
# §13.6). Queda en el catálogo con su receta: las fases la saltean, un ID explícito la corre.
# Desde la enmienda del 2026-10-30 (doc 134 §13.10) ninguna prueba lo usa: todo se corre.
ESTADOS = ("activa", "opcional", "pendiente_decision", "no_se_regenera")
_ID = re.compile(r"^[A-Z]+-\d{2}$")
_FASE = re.compile(r"^F\d$")


class CatalogoInvalido(ValueError):
    pass


@dataclass(frozen=True)
class Prueba:
    id: str
    titulo: str
    fase: str
    familia: str
    estado: str
    ruta: Path
    datos: dict = field(repr=False)

    @property
    def receta(self) -> dict:
        return self.datos.get("receta") or {}

    @property
    def depende_de(self) -> list[str]:
        return list(self.datos.get("depende_de") or [])

    @property
    def gen1(self) -> dict:
        return self.datos.get("gen1") or {}


def cargar_prueba(ruta: Path) -> Prueba:
    datos = yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}
    errores = []
    if datos.get("schema") != ESQUEMA:
        errores.append(f"schema debe ser {ESQUEMA!r}")
    pid = datos.get("id")
    if not isinstance(pid, str) or not _ID.match(pid):
        errores.append(f"id inválido: {pid!r}")
    elif pid != ruta.parent.name:
        errores.append(f"el id {pid!r} no coincide con la carpeta {ruta.parent.name!r}")
    if not datos.get("titulo"):
        errores.append("falta titulo")
    if not isinstance(datos.get("fase"), str) or not _FASE.match(datos["fase"]):
        errores.append(f"fase inválida: {datos.get('fase')!r}")
    if datos.get("familia") not in FAMILIAS:
        errores.append(f"familia inválida: {datos.get('familia')!r}")
    estado = datos.get("estado", "activa")
    if estado not in ESTADOS:
        errores.append(f"estado inválido: {estado!r}")
    if estado == "no_se_regenera":
        if not datos.get("no_se_regenera"):
            errores.append("una prueba que no se regenera dice por qué (campo no_se_regenera)")
        if not (datos.get("gen1") or {}).get("cifras"):
            errores.append("una prueba que no se regenera trae su cifra vigente (gen1.cifras)")
    if errores:
        raise CatalogoInvalido(f"{ruta}: " + "; ".join(errores))
    return Prueba(
        id=pid,
        titulo=datos["titulo"],
        fase=datos["fase"],
        familia=datos["familia"],
        estado=estado,
        ruta=ruta,
        datos=datos,
    )


def cargar_catalogo(directorio: Path) -> dict[str, Prueba]:
    pruebas: dict[str, Prueba] = {}
    for ruta in sorted(directorio.glob("*/prueba.yaml")):
        if ruta.parent.name.startswith("_"):
            continue
        prueba = cargar_prueba(ruta)
        pruebas[prueba.id] = prueba
    faltan = {
        dep: p.id for p in pruebas.values() for dep in p.depende_de if dep not in pruebas
    }
    if faltan:
        raise CatalogoInvalido(f"dependencias inexistentes: {faltan}")
    return pruebas


def _orden(prueba: Prueba) -> tuple:
    familia, numero = prueba.id.split("-")
    return (prueba.fase, familia, int(numero))


def seleccionar(catalogo: dict[str, Prueba], objetivos: list[str]) -> list[Prueba]:
    """IDs explícitos (corren cualquiera sea su estado) o fases `F3` (solo las activas).

    El orden respeta las dependencias: una prueba nunca va antes de otra de la que depende.
    """
    elegidas: dict[str, Prueba] = {}
    for objetivo in objetivos:
        if objetivo in catalogo:
            elegidas[objetivo] = catalogo[objetivo]
        elif _FASE.match(objetivo):
            for p in catalogo.values():
                if p.fase == objetivo and p.estado == "activa":
                    elegidas[p.id] = p
        elif objetivo == "todas":
            for p in catalogo.values():
                if p.estado == "activa":
                    elegidas[p.id] = p
        else:
            raise CatalogoInvalido(f"no existe la prueba ni la fase {objetivo!r}")
    ordenadas: list[Prueba] = []
    visitadas: set[str] = set()

    def visitar(p: Prueba) -> None:
        if p.id in visitadas:
            return
        visitadas.add(p.id)
        for dep in p.depende_de:
            if dep in elegidas:
                visitar(elegidas[dep])
        ordenadas.append(p)

    for p in sorted(elegidas.values(), key=_orden):
        visitar(p)
    return ordenadas
