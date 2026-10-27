"""Familias de pruebas: cada una sabe correr un tipo de prueba del catálogo.

Todas reciben el mismo `Contexto` y escriben en la carpeta de la prueba. El registro es un
diccionario simple; una familia nueva se agrega con el decorador `familia`.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from ..catalogo import Prueba
from ..consola import Consola
from ..entorno import Entorno
from ..registro import Carpeta


class ModeloIncorrecto(RuntimeError):
    pass


class DependenciaIncompleta(RuntimeError):
    pass


@dataclass
class Contexto:
    ent: Entorno
    consola: Consola
    catalogo: dict[str, Prueba]
    avisar: Callable[[str], None] = print
    forzar: bool = False
    solo: list[str] | None = None  # subconjunto de claves (clips, trabajos) para correr
    reagregar: bool = False  # no dispara corridas: re-evalúa y re-agrega lo que ya existe
    opciones: dict = field(default_factory=dict)  # opciones de una familia (p.ej. la toma en vivo)

    def carpeta(self, prueba_id: str) -> Carpeta:
        return Carpeta(self.ent, self.catalogo[prueba_id])

    def corridas_completas(self, prueba_id: str) -> dict[str, dict]:
        """Corridas OK de una prueba de la que esta depende; falla si no terminó."""
        carpeta = self.carpeta(prueba_id)
        resultado = carpeta.leer("resultado.json") or {}
        if resultado.get("estado") != "completo":
            raise DependenciaIncompleta(
                f"{prueba_id} no está completa (estado {resultado.get('estado')!r}): corréla antes"
            )
        return {k: v for k, v in carpeta.corridas().items() if v.get("estado") == "ok"}


FAMILIAS: dict[str, Callable[[Contexto, Prueba, Carpeta], dict]] = {}


def familia(nombre: str):
    def registrar(funcion):
        FAMILIAS[nombre] = funcion
        return funcion

    return registrar


def preparar_modelo(ctx: Contexto, receta: dict, carpeta: Carpeta) -> dict:
    """Deja activa la instancia que pide la receta y verifica el modelo cargado.

    En Docker activa la instancia del fleet si no es la activa (la consola para la anterior
    y espera `readyz`). En nativo no puede cambiar de modelo: si el cargado no es el pedido,
    se niega a seguir y dice qué levantar.
    """
    instancia = receta.get("instancia")
    modelo = receta.get("modelo")
    if ctx.ent.modo == "docker" and instancia:
        instancias = ctx.consola.instancias() or []
        activa = next((i for i in instancias if i.get("is_target")), None)
        if activa is None or activa.get("name") != instancia or not activa.get("ready"):
            ctx.avisar(f"  activando la instancia {instancia} (puede tardar unos minutos)")
            carpeta.comando(f"POST /api/platform/instances/{instancia}/activate")
            ctx.consola.activar(instancia)
    objetivo = ctx.consola.objetivo()
    cargado = (objetivo.get("model") or {}).get("ref")
    if not objetivo.get("ready"):
        raise ModeloIncorrecto("el media-plane activo no está listo (`readyz`)")
    if modelo and cargado != modelo:
        pista = (
            f"activá la instancia {instancia}" if ctx.ent.modo == "docker"
            else f"levantá el media-plane con EOVRT_MODEL_REF={modelo}"
        )
        raise ModeloIncorrecto(f"el modelo cargado es {cargado!r} y la prueba pide {modelo!r}: {pista}")
    return objetivo


# Registro de las familias (los módulos se registran al importarse).
from . import analisis, clips, imagenes, integridad, nivel_a, rodaje, vivo  # noqa: E402,F401
