"""Revisión ciega de la muestra de ERR-01, asistida por Claude (doc 134 §13.12).

ERR-01 pre-registró una revisión humana ciega: alguien mira cada cuadro de la muestra sin conocer
la causa automática y dice si la caja es una persona y si se ve el EPP. Desde el 2026-10-31 la
hace Claude Code en la Victus, con una persona que supervisa cada respuesta:

1. Claude mira solo `revision_ciega/` y `revision_ciega.csv`, nunca `completas/`, `recortes/`,
   `muestra.json` ni nada de ERR-01. Escribe `propuestas_ia.json`: por cuadro, su respuesta y una
   razón breve.
2. `pagina` arma `revision.html`, con cada cuadro y la propuesta marcada. La persona la confirma o
   la cambia; el progreso queda en el navegador, y al terminar descarga
   `revision_ciega_completa.csv`.
3. `cerrar` valida ese CSV: todos confirmados, valores válidos y los mismos cuadros. Después lo
   copia a `results/gen2/ERR-01/revision_humana.csv` con la propuesta de Claude al lado de la
   respuesta final, y ERR-01 informa cuántas cambió la persona.

La página no lleva nada que no esté en los cuadros ciegos: ni la causa, ni el clip, ni el tipo.
"""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path

from .familias.errores import leer_revision, normalizar_respuesta
from .registro import escribir_atomico

CSV_CIEGO = "revision_ciega.csv"
PROPUESTAS = "propuestas_ia.json"
PAGINA = "revision.html"
COMPLETO = "revision_ciega_completa.csv"
PLANTILLA = Path(__file__).with_name("revision_ciega.html")

ES_PERSONA = ("si", "no")
EPP_VISIBLE = ("si", "no", "no_se_puede")
COLUMNAS_FINALES = ("n", "imagen", "condicion", "es_persona", "epp_visible", "nota",
                    "propuesta_ia_es_persona", "propuesta_ia_epp_visible", "razon_ia", "revisado_por_persona")


class RevisionInvalida(ValueError):
    """El CSV o las propuestas no sirven para cerrar la revisión."""


def _respuesta_valida(es_persona: str, epp_visible: str) -> str | None:
    """None si el par es válido; si no, por qué. Si no es persona, el EPP no se juzga."""
    if es_persona not in ES_PERSONA:
        return f"es_persona {es_persona!r} (si/no)"
    if es_persona == "si" and epp_visible not in EPP_VISIBLE:
        return f"epp_visible {epp_visible!r} (si/no/no_se_puede)"
    return None


def leer_ciegos(carpeta: Path) -> list[dict]:
    with (carpeta / CSV_CIEGO).open(encoding="utf-8") as fh:
        return sorted(csv.DictReader(fh), key=lambda r: int(r["n"]))


def leer_propuestas(carpeta: Path, ciegos: list[dict]) -> dict[int, dict]:
    """`propuestas_ia.json`: `{"propuestas": [{"n", "es_persona", "epp_visible", "razon"}]}`."""
    ruta = carpeta / PROPUESTAS
    if not ruta.is_file():
        return {}
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    validos = {int(r["n"]) for r in ciegos}
    propuestas = {}
    for p in datos.get("propuestas") or []:
        n = int(p["n"])
        es, epp = normalizar_respuesta(p.get("es_persona", "")), normalizar_respuesta(p.get("epp_visible", ""))
        if n not in validos:
            raise RevisionInvalida(f"{PROPUESTAS}: el cuadro {n} no está en {CSV_CIEGO}")
        if motivo := _respuesta_valida(es, epp):
            raise RevisionInvalida(f"{PROPUESTAS}, cuadro {n}: {motivo}")
        propuestas[n] = {"es_persona": es, "epp_visible": epp if es == "si" else "",
                         "razon": str(p.get("razon") or "").strip()}
    return propuestas


def pagina(carpeta: Path) -> tuple[Path, int, int]:
    """Escribe `revision.html` junto a los cuadros. Devuelve la ruta, los cuadros y las propuestas."""
    ciegos = leer_ciegos(carpeta)
    propuestas = leer_propuestas(carpeta, ciegos)
    cuadros = []
    for r in ciegos:
        n = int(r["n"])
        recorte = Path(r["imagen"]).with_name(f"{n:03d}_recorte.png")
        cuadros.append({"n": n, "imagen": r["imagen"], "condicion": r.get("condicion", ""),
                        "recorte": recorte.as_posix() if (carpeta / recorte).is_file() else None,
                        "propuesta": propuestas.get(n)})
    datos = json.dumps({"cuadros": cuadros, "archivo": COMPLETO}, ensure_ascii=False).replace("</", "<\\/")
    ruta = carpeta / PAGINA
    escribir_atomico(ruta, PLANTILLA.read_text(encoding="utf-8").replace("__DATOS__", datos))
    return ruta, len(cuadros), len(propuestas)


def cerrar(carpeta: Path, completo: Path, destino: Path) -> dict:
    """Valida el CSV que bajó la página y lo deja donde ERR-01 lo lee."""
    if not completo.is_file():
        raise RevisionInvalida(f"no está {completo}: descargalo desde la página y movelo a esa carpeta")
    ciegos = {int(r["n"]): r for r in leer_ciegos(carpeta)}
    propuestas = leer_propuestas(carpeta, list(ciegos.values()))
    filas = leer_revision(completo)
    if set(filas) != set(ciegos):
        faltan, sobran = sorted(set(ciegos) - set(filas)), sorted(set(filas) - set(ciegos))
        raise RevisionInvalida(f"los cuadros no coinciden con {CSV_CIEGO}: faltan {faltan}, sobran {sobran}")
    salida, cambios = [], 0
    for n in sorted(ciegos):
        r = filas[n]
        es, epp = normalizar_respuesta(r.get("es_persona", "")), normalizar_respuesta(r.get("epp_visible", ""))
        if normalizar_respuesta(r.get("revisado_por_persona", "")) != "si":
            raise RevisionInvalida(f"el cuadro {n} no está confirmado por la persona")
        if motivo := _respuesta_valida(es, epp):
            raise RevisionInvalida(f"cuadro {n}: {motivo}")
        p = propuestas.get(n) or {}
        epp = epp if es == "si" else ""
        if p and (es, epp) != (p["es_persona"], p["epp_visible"]):
            cambios += 1
        salida.append({"n": n, "imagen": ciegos[n]["imagen"], "condicion": ciegos[n].get("condicion", ""),
                       "es_persona": es, "epp_visible": epp, "nota": r.get("nota", "").strip(),
                       "propuesta_ia_es_persona": p.get("es_persona", ""),
                       "propuesta_ia_epp_visible": p.get("epp_visible", ""),
                       "razon_ia": p.get("razon", ""), "revisado_por_persona": "si"})
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLUMNAS_FINALES, lineterminator="\n")
    w.writeheader()
    w.writerows(salida)
    escribir_atomico(destino, buf.getvalue())
    return {"cuadros": len(salida), "con_propuesta_ia": sum(1 for f in salida if f["propuesta_ia_es_persona"]),
            "cambios_de_la_persona": cambios, "destino": destino}
