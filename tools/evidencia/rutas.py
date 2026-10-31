"""Las rutas del workspace en `results/gen2/` (doc 134 §13.12).

El driver escribe rutas absolutas: en la Victus el workspace es la carpeta de un usuario de
Windows montada por Docker Desktop (`/run/desktop/mnt/host/c/Users/<usuario>/...`), y ese
nombre no va a un repo público. Antes de cada commit, `limpiar` reemplaza el workspace por
`$EOVRT_WORKSPACE` en todos los archivos de texto de `results/gen2/` y deja constancia en
`_registro/limpieza_rutas.json`. Al leer `corridas.json`, `Entorno.expandir` hace la inversa:
VIS-01, ERR-01 y la reanudación de una prueba siguen las rutas guardadas, así que funcionan igual
antes y después de limpiar. Lo que el driver escriba después vuelve a traer la ruta: se limpia
otra vez antes del commit siguiente (es idempotente).

Las huellas `sha256.*_config` de `corridas.json` son de la configuración tal como se envió, con
la ruta original. La copia de `logs/ejemplo/` queda limpia; su huella original es `sha256_antes`
en la constancia.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml

from .entorno import MARCA_WORKSPACE
from .registro import ahora, escribir_atomico, escribir_json

CONSTANCIA = Path("_registro") / "limpieza_rutas.json"


def usuario_de(desde: str) -> str | None:
    """El segmento que sigue a `Users/` en la ruta del workspace, si lo hay."""
    partes = desde.replace("\\", "/").split("/")
    for i, parte in enumerate(partes[:-1]):
        if parte.lower() == "users" and partes[i + 1]:
            return partes[i + 1]
    return None


def _parsea(ruta: Path, texto: str) -> bool:
    try:
        if ruta.suffix == ".json":
            json.loads(texto)
        elif ruta.suffix in (".yaml", ".yml"):
            yaml.safe_load(texto)
    except (ValueError, yaml.YAMLError):
        return False
    return True


def limpiar(resultados: Path, desde: str, *, simular: bool = False) -> dict:
    """Reemplaza `desde` por la marca en todo `resultados/`. Calcula todo antes de escribir: si
    un archivo deja de parsear o el nombre del usuario sigue en algún lado, no escribe nada."""
    desde = desde.rstrip("/")
    if not desde or MARCA_WORKSPACE in desde:
        raise ValueError(f"ruta del workspace inválida: {desde!r}")
    usuario = usuario_de(desde)
    cambios, rotos, restos, binarios = [], [], [], []
    for ruta in sorted(p for p in resultados.rglob("*") if p.is_file()):
        rel = ruta.relative_to(resultados).as_posix()
        crudo = ruta.read_bytes()
        try:
            texto = crudo.decode("utf-8")
        except UnicodeDecodeError:
            if desde.encode() in crudo or (usuario and usuario.encode() in crudo):
                binarios.append(rel)
            continue
        n = texto.count(desde)
        nuevo = texto.replace(desde, MARCA_WORKSPACE) if n else texto
        if usuario and usuario in nuevo:
            restos.append(rel)
        if not n:
            continue
        if _parsea(ruta, texto) and not _parsea(ruta, nuevo):
            rotos.append(rel)
        cambios.append({"ruta": rel, "reemplazos": n,
                        "sha256_antes": hashlib.sha256(crudo).hexdigest(),
                        "sha256_despues": hashlib.sha256(nuevo.encode("utf-8")).hexdigest(),
                        "texto": nuevo})
    informe = {"archivos": len(cambios), "reemplazos": sum(c["reemplazos"] for c in cambios),
               "rotos": rotos, "restos": restos, "binarios": binarios, "escrito": False}
    if simular or rotos or restos or binarios or not cambios:
        return informe
    for c in cambios:
        escribir_atomico(resultados / c["ruta"], c.pop("texto"))
    constancia = resultados / CONSTANCIA
    previas = json.loads(constancia.read_text(encoding="utf-8")) if constancia.is_file() else []
    previas.append({
        "fecha": ahora(),
        "marca": MARCA_WORKSPACE,
        "de": "el workspace de la máquina que corrió las pruebas (ruta con el usuario de Windows; no se publica)",
        "nota": "Las huellas sha256.*_config de corridas.json son de la configuración tal como se envió, "
                "con la ruta original; la de cada copia de logs/ejemplo/ antes de limpiar es sha256_antes.",
        "archivos": cambios,
    })
    escribir_json(constancia, previas)
    informe["escrito"] = True
    return informe
