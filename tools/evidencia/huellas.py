"""Huellas: sha256 de insumos y la verificación de la configuración congelada.

Regla del doc 134 §1: si una huella declarada en el pre-registro no coincide, la prueba NO
corre. Los prompts se arman desde los YAML congelados de `prompts/` (verificando su
`frozen_sha256`) con la misma forma `set_inline` que usaron los runners de la generación 1.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml

_BLOQUE = 1024 * 1024


class HuellaInvalida(ValueError):
    pass


def sha256_archivo(ruta: Path) -> str:
    h = hashlib.sha256()
    with Path(ruta).open("rb") as fh:
        for bloque in iter(lambda: fh.read(_BLOQUE), b""):
            h.update(bloque)
    return h.hexdigest()


def sha256_texto(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def sha256_lf(ruta: Path) -> str | None:
    """sha256 del archivo con los CRLF pasados a LF, o None si no tiene CRLF.

    Los repos no fijan finales de línea (no hay `.gitattributes`): un clon con Git para
    Windows (`core.autocrlf=true`) deja los YAML/JSON/XML con CRLF y su huella cambia sin que
    cambie el contenido. Las verificaciones aceptan esa diferencia y la declaran aparte.
    """
    datos = Path(ruta).read_bytes()
    if b"\r\n" not in datos:
        return None
    return hashlib.sha256(datos.replace(b"\r\n", b"\n")).hexdigest()


def coincide(ruta: Path, esperado: str) -> str | None:
    """'ok', 'ok_crlf' o None (no coincide)."""
    if sha256_archivo(ruta) == esperado:
        return "ok"
    return "ok_crlf" if sha256_lf(ruta) == esperado else None


def verificar_lista(lista: Path, base: Path, *, avance=None) -> dict:
    """Equivalente de `sha256sum -c <lista>` con las rutas relativas a `base`."""
    ok = ok_crlf = 0
    fallan: list[str] = []
    faltan: list[str] = []
    lineas = [l for l in lista.read_text(encoding="utf-8").splitlines() if l.strip()]
    for i, linea in enumerate(lineas, 1):
        esperado, _, nombre = linea.partition(" ")
        nombre = nombre.strip().lstrip("*")
        archivo = base / nombre
        if not archivo.is_file():
            faltan.append(nombre)
        else:
            estado = coincide(archivo, esperado)
            if estado == "ok":
                ok += 1
            elif estado == "ok_crlf":
                ok_crlf += 1
            else:
                fallan.append(nombre)
        if avance and i % 500 == 0:
            avance(f"      {i}/{len(lineas)}")
    return {
        "lista": str(lista),
        "lista_sha256": sha256_archivo(lista),
        "lista_sha256_lf": sha256_lf(lista),
        "total": len(lineas),
        "ok": ok,
        "ok_salvo_finales_de_linea": ok_crlf,
        "fallan": fallan,
        "faltan": faltan,
    }


def hash_clases(clases: list) -> str:
    """Convención de la consola (`prompt_store.classes_sha256`): el bloque `classes` crudo."""
    payload = json.dumps(clases, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def leer_prompt_set(ruta: Path) -> dict:
    datos = (yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}).get("prompt_set") or {}
    clases = datos.get("classes") or []
    calculado = hash_clases(clases)
    declarado = datos.get("frozen_sha256")
    if datos.get("status") == "frozen" and declarado != calculado:
        raise HuellaInvalida(
            f"{ruta}: frozen_sha256 declarado {declarado} != calculado {calculado}"
        )
    return {
        "id": datos.get("id"),
        "status": datos.get("status"),
        "frozen_sha256": declarado,
        "clases_sha256": calculado,
        "clases": {c["id"]: c for c in clases},
    }


def armar_prompts(spec: dict, repo: Path) -> tuple[dict, dict]:
    """(payload `prompts` para `POST /api/runs`, constancia de verificación).

    `spec`:
      set_id: id que viaja en `set_inline` (el mismo que usó la generación 1)
      fuente: prompts/<set>.yaml (fuente por default de las clases)
      clases: [person, helmet, {id: cr01_spec, fuente: prompts/edir_v1.yaml}, ...]
      frozen: {prompts/<set>.yaml: <frozen_sha256 esperado>, ...}
    """
    por_defecto = spec.get("fuente")
    esperados: dict = spec.get("frozen") or {}
    sets: dict[str, dict] = {}

    def set_de(rel: str) -> dict:
        if rel not in sets:
            sets[rel] = leer_prompt_set(repo / rel)
        return sets[rel]

    clases_payload = []
    for entrada in spec.get("clases") or []:
        cid, rel = (entrada, por_defecto) if isinstance(entrada, str) else (entrada["id"], entrada.get("fuente", por_defecto))
        if not rel:
            raise HuellaInvalida(f"la clase {cid!r} no declara de qué prompt set sale")
        origen = set_de(rel)
        if cid not in origen["clases"]:
            raise HuellaInvalida(f"la clase {cid!r} no está en {rel}")
        frases = (origen["clases"][cid].get("phrasings") or {}).get("default")
        if not frases:
            raise HuellaInvalida(f"{rel}: la clase {cid!r} no tiene phrasings.default")
        clases_payload.append({"id": cid, "phrasings": {"default": list(frases)}})

    for rel, esperado in esperados.items():
        origen = set_de(rel)
        if origen["clases_sha256"] != esperado:
            raise HuellaInvalida(
                f"{rel}: el bloque classes tiene sha256 {origen['clases_sha256']}, "
                f"el pre-registro espera {esperado}"
            )

    payload = {
        "set_inline": {"id": spec["set_id"], "classes": clases_payload},
        "active_ids": [c["id"] for c in clases_payload],
    }
    constancia = {
        "set_id": spec["set_id"],
        "fuentes": {
            rel: {"status": s["status"], "frozen_sha256": s["frozen_sha256"], "clases_sha256": s["clases_sha256"]}
            for rel, s in sets.items()
        },
        "payload_sha256": sha256_texto(json.dumps(payload, sort_keys=True)),
    }
    return payload, constancia
