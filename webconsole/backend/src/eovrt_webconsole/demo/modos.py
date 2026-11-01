"""Modos de prompts de la demo: la lista cerrada de `experiments/demo_defensa/modos.yaml`.

Un modo es un par prompt set + pattern set ya medido en la generación 2. El default (el
campeón) es la configuración congelada y no cambia nada de lo que manda la plantilla. Los
otros reemplazan los prompts de la corrida (`set_inline`, sin recargar el motor) y el pattern
set del control, y la sesión queda marcada (`modo_prompts` en session.json, id con
`_modo-<id>`): no es la demo congelada, no cuenta como ensayo y el driver de evidencia no la
importa.

Lo que lo separa del «vocabulario improvisado» que la spec de la demo deja afuera: cada modo
manda EXACTAMENTE el set que midió su prueba, y `verificar` lo comprueba por huella antes de
dejar iniciar: la del payload de prompts con la convención del driver
(`tools/evidencia/huellas.armar_prompts`, `payload_sha256` de
results/gen2/<prueba>/configuracion.json) y la del archivo del pattern set.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from eovrt_webconsole.demo.cifras import leer_cifra
from eovrt_webconsole.demo.config import _BASE, ConfigDemoError, _item, _sha256

_MODOS = "modos.yaml"
# Va en el id de la sesión (`_modo-<id>`): sin puntos ni barras.
_MODO_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,23}$")
# Lo que un modo cambia de la configuración congelada (ítems de `verificar_congelado`). Todo lo
# demás —el modelo, sus umbrales y la distribución— tiene que seguir igual al tag.
_CAMBIA = frozenset({"prompt_set_archivo", "prompt_set_enviado", "pattern_set"})


def cargar(repo_root: Path) -> dict:
    path = Path(repo_root) / "experiments" / _BASE / _MODOS
    try:
        datos = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigDemoError(f"no se pudo leer {path}: {exc}") from exc
    modos = datos.get("modos")
    if not isinstance(modos, dict) or datos.get("default") not in modos:
        raise ConfigDemoError(f"{path}: hacen falta `modos` y un `default` que esté en la lista")
    for id_ in modos:
        if not _MODO_ID.match(str(id_)):
            raise ConfigDemoError(f"{path}: id de modo inválido {id_!r} (minúsculas, números, '-' y '_')")
    return datos


def _clases(repo_root: Path, prompts: Mapping) -> list[dict]:
    """Las clases del modo, en orden, con sus frases (`phrasings.default`) leídas de cada archivo
    de `prompts/`: la misma composición que armó el driver para la prueba que lo midió."""
    por_defecto = prompts.get("fuente")
    archivos: dict[str, dict] = {}
    clases = []
    for entrada in prompts.get("clases") or []:
        if isinstance(entrada, str):
            cid, rel = entrada, por_defecto
        else:
            cid, rel = entrada.get("id"), entrada.get("fuente", por_defecto)
        if not rel:
            raise ConfigDemoError(f"la clase {cid!r} no dice de qué prompt set sale")
        if rel not in archivos:
            path = Path(repo_root) / rel
            try:
                datos = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("prompt_set") or {}
            except (OSError, yaml.YAMLError) as exc:
                raise ConfigDemoError(f"no se pudo leer {path}: {exc}") from exc
            archivos[rel] = {c["id"]: c for c in datos.get("classes") or [] if isinstance(c, dict) and "id" in c}
        frases = ((archivos[rel].get(cid) or {}).get("phrasings") or {}).get("default")
        if not frases:
            raise ConfigDemoError(f"{rel}: la clase {cid!r} no está o no tiene phrasings.default")
        clases.append({"id": cid, "frases": list(frases), "fuente": rel})
    if not clases:
        raise ConfigDemoError("el modo no declara clases")
    return clases


def resolver(repo_root: Path, modo: str | None) -> dict | None:
    """Valida un modo contra la lista cerrada. Sin modo, o con el default (el campeón), no hay
    nada que cambiar: None, la demo congelada. Con otro, devuelve lo que la sesión usa y registra."""
    if not modo:
        return None
    datos = cargar(repo_root)
    modos = datos["modos"]
    if modo not in modos:
        raise ConfigDemoError(f"modo fuera de la lista: {modo!r} (opciones: {list(modos)})")
    if modo == datos["default"]:
        return None
    m = modos[modo]
    prompts, patrones = m.get("prompts") or {}, m.get("patrones") or {}
    if not prompts.get("payload_sha256") or not patrones.get("sha256_archivo"):
        raise ConfigDemoError(f"el modo {modo!r} no declara las huellas de lo que midió su prueba")
    return {
        "id": modo,
        "nombre": m.get("nombre", modo),
        "evidencia": m.get("evidencia"),
        "prompt_set": prompts["set_id"],
        "clases": _clases(repo_root, prompts),
        "payload_sha256": prompts["payload_sha256"],
        "medido_en": prompts.get("medido_en"),
        "pattern_set": {"id": patrones["id"], "archivo": patrones["archivo"],
                        "sha256_archivo": patrones["sha256_archivo"]},
    }


def payload(modo: Mapping) -> dict:
    """La sección `prompts` de la corrida, con la forma que mandó el driver a la prueba."""
    return {
        "set_inline": {"id": modo["prompt_set"],
                       "classes": [{"id": c["id"], "phrasings": {"default": list(c["frases"])}}
                                   for c in modo["clases"]]},
        "active_ids": [c["id"] for c in modo["clases"]],
    }


def huella_prompts(prompts: Mapping) -> str:
    """`payload_sha256` del driver de evidencia: sha256 de `{set_inline, active_ids}` con
    `json.dumps(sort_keys=True)`."""
    datos = {"set_inline": prompts.get("set_inline"), "active_ids": prompts.get("active_ids")}
    return hashlib.sha256(json.dumps(datos, sort_keys=True).encode("utf-8")).hexdigest()


def aplicar(media: dict, control: dict, modo: Mapping, workspace: str) -> None:
    """Pisa los prompts de la corrida y el pattern set del control con los del modo. `workspace`
    es el marcador `EOVRT_WORKSPACE` ya resuelto: la ruta queda con la forma de la plantilla."""
    media["prompts"] = payload(modo)
    control["patterns"] = {**(control.get("patterns") or {}),
                           "file": f"{workspace}/{modo['pattern_set']['archivo']}"}


def verificar(configs: Mapping[str, dict], modo: Mapping, congelado: Mapping) -> dict:
    """¿Lo que se va a mandar es lo que midió la prueba del modo? Tres chequeos: la huella de los
    prompts de la corrida, la del archivo del pattern set y, de la configuración congelada, todo
    lo que el modo no cambia (catálogo y umbrales del modelo, motor cargado, distribución)."""
    items: list[dict] = []
    prompts = (configs.get("media") or {}).get("prompts") or {}
    huella = huella_prompts(prompts)
    items.append(_item(
        "modo_prompts", f"Prompts de {modo['nombre']} ({modo['prompt_set']}), los que midió {modo['medido_en']}",
        huella == modo["payload_sha256"], modo["payload_sha256"], huella,
    ))
    pat = modo["pattern_set"]
    archivo = Path(((configs.get("control") or {}).get("patterns") or {}).get("file") or "")
    sha = _sha256(archivo) if archivo.name else None
    items.append(_item(
        "modo_patrones", f"Pattern set {pat['id']}",
        archivo.name == Path(pat["archivo"]).name and sha == pat["sha256_archivo"],
        pat["sha256_archivo"], sha, ruta=str(archivo),
    ))
    resto = [i for i in congelado.get("items") or [] if i["id"] not in _CAMBIA]
    distintos = [i["id"] for i in resto if not i["ok"]]
    items.append(_item(
        "modo_resto", "Lo que el modo no cambia (modelo, umbrales, distribución), igual al tag",
        bool(resto) and not distintos and not congelado.get("error"),
        sorted(i["id"] for i in resto), distintos or congelado.get("error"),
    ))
    return {"ok": all(i["ok"] for i in items), "items": items}


def describir(repo_root: Path) -> dict[str, Any]:
    """La lista para el selector de /demo: cada modo con sus frases por clase y sus cifras de la
    generación 2 (leídas de results/gen2, nunca escritas a mano). Un modo cuyas clases no se pueden
    leer se muestra igual, con el error: la pantalla no puede quedarse sin el campeón."""
    datos = cargar(repo_root)
    results = Path(repo_root) / "results"
    modos = []
    for id_, m in datos["modos"].items():
        prompts, patrones = m.get("prompts") or {}, m.get("patrones") or {}
        try:
            clases, error = _clases(repo_root, prompts), None
        except ConfigDemoError as exc:
            clases, error = [], str(exc)
        modos.append({
            "id": id_,
            "nombre": m.get("nombre", id_),
            "evidencia": m.get("evidencia"),
            "resumen": m.get("resumen"),
            "nota": m.get("nota"),
            "por_defecto": id_ == datos["default"],
            "prompt_set": prompts.get("set_id"),
            "pattern_set": patrones.get("id"),
            "medido_en": prompts.get("medido_en"),
            "clases": clases,
            "cifras": [leer_cifra(results, c["prueba"], c["clave"], c.get("que_es", ""))
                       for c in m.get("cifras") or []],
            "error": error,
        })
    return {"default": datos["default"], "modos": modos}
