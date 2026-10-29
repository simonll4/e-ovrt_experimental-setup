"""Integridad de los insumos (INT-01…03) y foto de la plataforma (PLAT-01). Sin GPU.

Cada prueba es una lista de chequeos con su detalle. Si un chequeo falla, la prueba queda
`fallida` y lo que dependa de ese insumo no se puede reportar hasta resolverlo (doc 134 §2).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

from ..catalogo import Prueba
from ..entorno import docker_compose, foto
from ..huellas import coincide, leer_prompt_set, sha256_archivo, verificar_lista
from ..registro import Carpeta
from . import Contexto, familia


def _chequeo(nombre: str, ok: bool, **detalle) -> dict:
    return {"nombre": nombre, "ok": bool(ok), **detalle}


def _lista(ctx: Contexto, nombre: str, lista, base, esperado_lista: str | None = None) -> dict:
    ctx.avisar(f"    {nombre}: verificando {lista}")
    res = verificar_lista(lista, base, avance=ctx.avisar)
    ok = not res["fallan"] and not res["faltan"]
    if esperado_lista:
        ok = ok and esperado_lista in (res["lista_sha256"], res["lista_sha256_lf"])
    detalle = {k: v for k, v in res.items() if k not in ("fallan", "faltan", "ok")}
    return _chequeo(nombre, ok, **detalle, coinciden=res["ok"],
                    fallan=res["fallan"][:50], faltan=res["faltan"][:50],
                    n_fallan=len(res["fallan"]), n_faltan=len(res["faltan"]),
                    lista_sha256_esperado=esperado_lista)


def _sub(cmd: list[str], cwd=None) -> tuple[int, str]:
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False, cwd=cwd)
    return proc.returncode, (proc.stdout + proc.stderr)[-4000:]


def _int01(ctx: Contexto, prueba: Prueba, carpeta: Carpeta) -> list[dict]:
    ds = ctx.ent.datasets
    r = prueba.receta
    chequeos = [_lista(ctx, "imagenes_bench_v3", ds / r["lista_imagenes"], ds)]
    cmd = [sys.executable, str(ctx.ent.scripts_datasets / "curate" / "build_bench_strata.py"), "--verify"]
    carpeta.comando(" ".join(cmd))
    rc, salida = _sub(cmd)
    chequeos.append(_chequeo("estratos_byte_a_byte", rc == 0, comando=" ".join(cmd), salida=salida))
    # Reconstrucción de bench_v3.json en memoria (nunca se escribe: el archivo está congelado).
    raiz = str(ctx.ent.scripts_datasets)
    if raiz not in sys.path:
        sys.path.insert(0, raiz)
    from curate import build_bench_v3 as b3  # noqa: PLC0415

    estratos = {n: json.loads(p.read_text()) for n, p in b3.STRATUM_SOURCES.items()}
    merged, _manifest = b3.assemble_bench_v3(estratos)
    reconstruido = b3.manifest_sha256(b3.freeze_payload(merged))
    congelado = ds / "datasets/processed/coco/bench/curated/bench_v3.json"
    manifest = json.loads((congelado.parent / "bench_v3_manifest.json").read_text())
    chequeos.append(_chequeo(
        "bench_v3_reconstruido", reconstruido == sha256_archivo(congelado) == manifest.get("bench_v3_sha256"),
        reconstruido=reconstruido, en_disco=sha256_archivo(congelado), manifiesto=manifest.get("bench_v3_sha256"),
    ))
    return chequeos


def _int02(ctx: Contexto, prueba: Prueba, carpeta: Carpeta) -> list[dict]:
    banco = ctx.ent.banco
    r = prueba.receta
    manifest = yaml.safe_load((banco / "manifest.yaml").read_text())
    malos, faltan = [], []
    for clip in manifest["clips"]:
        mp4 = (banco / clip["file"])
        if not mp4.is_file():
            faltan.append(clip["clip_id"])
        elif sha256_archivo(mp4) != clip["sha256"]:
            malos.append(clip["clip_id"])
    chequeos = [_chequeo("clips_mp4_contra_manifiesto", not malos and not faltan,
                         total=len(manifest["clips"]), fallan=malos, faltan=faltan)]
    chequeos.append(_lista(ctx, "gt_y_anotaciones_del_banco", banco / "clip_bench.sha256", banco,
                           esperado_lista=r.get("clip_bench_sha256")))
    cmd = [sys.executable, str(ctx.ent.scripts_datasets / "bench" / "validate_clip_gt.py"),
           "--gt-dir", str(banco / "gt"), "--manifest", str(banco / "manifest.yaml"), "--base-dir", str(banco)]
    carpeta.comando(" ".join(cmd))
    rc, salida = _sub(cmd)
    chequeos.append(_chequeo("validate_clip_gt", rc == 0, comando=" ".join(cmd), salida=salida))
    return chequeos


def _int03(ctx: Contexto, prueba: Prueba, carpeta: Carpeta) -> list[dict]:
    r = prueba.receta
    chequeos = [_lista(ctx, "pesos_de_los_modelos", prueba.ruta.parent / r["lista_modelos"], ctx.ent.media_plane)]
    for rel, esperado in (r.get("prompt_sets") or {}).items():
        datos = leer_prompt_set(ctx.ent.repo / rel)
        chequeos.append(_chequeo(f"prompt_set:{rel}", datos["clases_sha256"] == esperado,
                                 esperado=esperado, calculado=datos["clases_sha256"],
                                 declarado_en_el_yaml=datos["frozen_sha256"]))
    for nombre, esperado in (r.get("pattern_sets") or {}).items():
        ruta = ctx.ent.patrones / f"{nombre}.yaml"
        estado = coincide(ruta, esperado) if ruta.is_file() else None
        chequeos.append(_chequeo(f"pattern_set:{nombre}", estado is not None, esperado=esperado,
                                 calculado=sha256_archivo(ruta) if ruta.is_file() else None,
                                 finales_de_linea="CRLF (contenido idéntico)" if estado == "ok_crlf" else None))
    catalogos = {}
    for rel in r.get("catalogos_modelo") or []:
        ruta = ctx.ent.media_plane / rel
        catalogos[rel] = yaml.safe_load(ruta.read_text()) if ruta.is_file() else None
    chequeos.append(_chequeo("catalogos_de_modelo_leidos", all(catalogos.values()), catalogos=catalogos))
    return chequeos


# La infraestructura declarada: un Dockerfile por servicio y el compose de la plataforma completa.
INFRA_DECLARADA = (
    "e-ovrt_media-plane/infra/docker/Dockerfile",
    "e-ovrt_control-plane/infra/docker/Dockerfile",
    "e-ovrt_alert-distribution/infra/docker/Dockerfile",
    "e-ovrt_experimental-setup/infra/console/Dockerfile",
    "e-ovrt_experimental-setup/infra/platform/docker-compose.yml",
    "e-ovrt_experimental-setup/infra/platform/docker-compose.demo.yml",
)
LOG_BUILD = "compose_build.log"


def infra_declarada(ent, logs: Path) -> dict:
    """Las huellas de la infraestructura con la que se construyó la plataforma y, si la preparación
    guardó la salida de `docker compose build` en `logs/compose_build.log`, la huella de ese log
    (doc 137 §8). Es información, no un chequeo: el build corre en la preparación, fuera del driver."""
    archivos = {rel: (sha256_archivo(ent.ws / rel) if (ent.ws / rel).is_file() else None) for rel in INFRA_DECLARADA}
    log = logs / LOG_BUILD
    build = None
    if log.is_file():
        crudo = log.read_bytes()
        # `Tee-Object` de Windows PowerShell 5.1 escribe UTF-16 con BOM; Git Bash y WSL, UTF-8.
        texto = crudo.decode("utf-16") if crudo[:2] in (b"\xff\xfe", b"\xfe\xff") else crudo.decode("utf-8", "replace")
        lineas = texto.splitlines()
        build = {"archivo": f"logs/{LOG_BUILD}", "sha256": sha256_archivo(log), "lineas": len(lineas),
                 "imagenes_nombradas": sorted({x.split("naming to ")[1].split()[0] for x in lineas if "naming to " in x})}
    return {"archivos": archivos, "build": build}


def _plat01(ctx: Contexto, prueba: Prueba, carpeta: Carpeta) -> list[dict]:
    chequeos = []
    salud = ctx.consola.salud()
    chequeos.append(_chequeo("consola_responde", salud, url=ctx.consola.url))
    objetivo = ctx.consola.objetivo() if salud else None
    instancias = ctx.consola.instancias() if salud else None
    chequeos.append(_chequeo("media_plane_listo", bool(objetivo and objetivo.get("ready")), objetivo=objetivo))
    if ctx.ent.modo == "docker":
        config = docker_compose(ctx.ent, "config", "--quiet")
        chequeos.append(_chequeo("compose_config_valido", config is not None))
        ps = docker_compose(ctx.ent, "ps", "--all", "--format", "json")
        chequeos.append(_chequeo("compose_ps", ps is not None, salida=ps))
    datos = foto(ctx.ent, objetivo=objetivo,
                 servicio_gpu=next((i["name"] for i in (instancias or []) if i.get("is_target")), None))
    carpeta.escribir("plataforma.json", {"instancias": instancias, **datos,
                                         "infra_declarada": infra_declarada(ctx.ent, carpeta.logs)})
    chequeos.append(_chequeo("gpu_identificada", bool(datos.get("gpu")), gpu=datos.get("gpu")))
    return chequeos


_PRUEBAS = {"INT-01": _int01, "INT-02": _int02, "INT-03": _int03, "PLAT-01": _plat01}


@familia("integridad")
@familia("plataforma")
def correr(ctx: Contexto, prueba: Prueba, carpeta: Carpeta) -> dict:
    funcion = _PRUEBAS.get(prueba.id)
    if funcion is None:
        raise ValueError(f"{prueba.id}: no hay chequeos definidos para esta prueba")
    chequeos = funcion(ctx, prueba, carpeta)
    ok = all(c["ok"] for c in chequeos)
    metricas = {c["nombre"]: c["ok"] for c in chequeos}
    resumen = [{"clave": c["nombre"], "nombre": c["nombre"].replace("_", " "),
                "valor": "ok" if c["ok"] else "FALLA", "unidad": None, "gen1": None} for c in chequeos]
    datos = {
        "familia": prueba.familia,
        "estado": "completo" if ok else "fallido",
        "metricas": metricas,
        "resumen": resumen,
        "chequeos": chequeos,
        "veredicto": {"propuesto": "identico" if ok else "a_revisar",
                      "motivo": "todas las huellas coinciden" if ok else "hay chequeos que fallan",
                      "confirmado": None, "diferencias": {}},
    }
    carpeta.resultado(datos)
    return {"estado": datos["estado"], "fallan": [c["nombre"] for c in chequeos if not c["ok"]]}
