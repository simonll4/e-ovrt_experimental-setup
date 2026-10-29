"""CLI del driver de evidencia de la generación 2 (doc 134).

    python -m tools.evidencia lista [--fase F3]
    python -m tools.evidencia verificar [ID|FASE ...]        # sin correr nada
    python -m tools.evidencia correr ID|FASE|todas [...] [--solo a_p1_c02,...] [--reagregar] [--forzar]
    python -m tools.evidencia vivo RT-03 --toma t1 --config 960x540@5 [--unidades 250]
    python -m tools.evidencia descartar RT-04 <session_id> --motivo "..." --quien NOMBRE
    python -m tools.evidencia estado [ID|FASE ...]
    python -m tools.evidencia veredicto ID identico|equivalente_con_diferencia|otra_combinacion --motivo "..." --quien NOMBRE
    python -m tools.evidencia indice

En la Victus se invoca con `infra/platform/evidencia.sh` (o `.ps1`), que lo corre dentro del
contenedor de la consola.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from pathlib import Path

from .catalogo import CatalogoInvalido, cargar_catalogo, seleccionar
from .consola import Consola, ConsolaError
from .entorno import detectar, foto
from .familias import FAMILIAS, Contexto
from .huellas import HuellaInvalida, armar_prompts
from .registro import Carpeta, PreRegistroCambiado, ahora, escribir_json

VEREDICTOS = ("identico", "equivalente_con_diferencia", "otra_combinacion")
SIN_CONSOLA = {"integridad", "analisis", "figuras"}  # no disparan corridas


def _avisar(texto: str) -> None:
    print(texto, flush=True)


class Candado:
    """Un solo driver a la vez sobre `results/gen2/` (dos campañas cruzadas se pisarían)."""

    def __init__(self, ruta: Path) -> None:
        self.ruta = ruta

    def __enter__(self):
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        if self.ruta.is_file():
            try:
                datos = json.loads(self.ruta.read_text())
                os.kill(int(datos["pid"]), 0)
            except (ValueError, KeyError, ProcessLookupError, PermissionError, OSError):
                pass  # candado viejo: el proceso ya no existe
            else:
                raise SystemExit(f"hay otro driver corriendo (pid {datos['pid']} desde {datos.get('desde')}); "
                                 f"si no es así, borrá {self.ruta}")
        self.ruta.write_text(json.dumps({"pid": os.getpid(), "desde": ahora()}))
        return self

    def __exit__(self, *exc):
        try:
            self.ruta.unlink()
        except FileNotFoundError:
            pass


def _contexto(args, catalogo) -> Contexto:
    ent = detectar()
    return Contexto(
        ent=ent,
        consola=Consola(ent.consola_url, avisar=_avisar),
        catalogo=catalogo,
        avisar=_avisar,
        forzar=getattr(args, "forzar", False),
        solo=[s for s in (getattr(args, "solo", "") or "").split(",") if s] or None,
        reagregar=getattr(args, "reagregar", False),
    )


def _estado_prueba(ent, prueba) -> dict:
    carpeta = Carpeta(ent, prueba)
    resultado = carpeta.leer("resultado.json") or {}
    corridas = carpeta.corridas()
    veredicto = resultado.get("veredicto") or {}
    return {
        "id": prueba.id,
        "fase": prueba.fase,
        "familia": prueba.familia,
        "registro": prueba.estado,
        "estado": resultado.get("estado", "sin_correr"),
        "corridas_ok": sum(1 for c in corridas.values() if c.get("estado") == "ok"),
        "corridas": len(corridas),
        "veredicto": (veredicto.get("confirmado") or {}).get("valor") or veredicto.get("propuesto"),
        "confirmado": bool(veredicto.get("confirmado")),
    }


def escribir_indice(ent, catalogo) -> Path:
    """`results/gen2/indice.json`: lo que la consola muestra en «Resultados» (doc 135)."""
    filas = []
    for prueba in sorted(catalogo.values(), key=lambda p: (p.fase, p.id)):
        carpeta = Carpeta(ent, prueba)
        resultado = carpeta.leer("resultado.json") or {}
        filas.append({
            **_estado_prueba(ent, prueba),
            "titulo": prueba.titulo,
            "informe": prueba.datos.get("informe") or [],
            "pregunta": prueba.datos.get("pregunta"),
            "gen1": {k: prueba.gen1.get(k) for k in ("result_id", "doc", "relacion") if prueba.gen1.get(k)},
            "resumen": resultado.get("resumen") or [],
            "generado": resultado.get("generado"),
        })
    ruta = ent.resultados / "indice.json"
    escribir_json(ruta, {"schema": "indice.gen2.v1", "generado": ahora(), "pruebas": filas})
    return ruta


def cmd_lista(args) -> int:
    ent = detectar()
    catalogo = cargar_catalogo(ent.catalogo)
    for p in sorted(catalogo.values(), key=lambda p: (p.fase, p.id)):
        if args.fase and p.fase != args.fase:
            continue
        e = _estado_prueba(ent, p)
        marca = "" if p.estado == "activa" else f" [{p.estado}]"
        print(f"{p.fase}  {p.id:8} {p.familia:13} {e['estado']:11} {e['veredicto'] or '':27} {p.titulo}{marca}")
    return 0


def _verificar_prueba(ctx: Contexto, prueba) -> list[str]:
    """Lo que se puede comprobar sin disparar nada: familia, prompts congelados, pattern sets,
    insumos en disco y dependencias."""
    errores = []
    r = prueba.receta
    if prueba.familia not in FAMILIAS:
        errores.append(f"familia sin implementar: {prueba.familia}")
    specs = []
    if isinstance(r.get("medios"), dict) and r["medios"].get("prompts"):
        specs.append(r["medios"]["prompts"])
    if r.get("prompts"):
        specs.append(r["prompts"] if "clases" in r["prompts"] else None)
    if (r.get("eind") or {}).get("prompts"):
        specs.append(r["eind"]["prompts"])
    for spec in filter(None, specs):
        try:
            armar_prompts(spec, ctx.ent.repo)
        except (HuellaInvalida, FileNotFoundError, KeyError) as exc:
            errores.append(f"prompts: {exc}")
    for spec in [r.get("control"), *[v.get("control") for v in r.get("variantes") or []]]:
        if spec and not (ctx.ent.patrones / f"{spec['patrones']}.yaml").is_file():
            errores.append(f"pattern set inexistente: {spec['patrones']}")
    if prueba.familia == "clips" and r.get("tipo", "inferencia") == "inferencia":
        from .herramientas import clips_de, ruta_video  # noqa: PLC0415

        faltan = [c for c in clips_de(ctx.ent, r["clips"]) if not ruta_video(ctx.ent, c).is_file()]
        if faltan:
            errores.append(f"faltan {len(faltan)} videos del banco: {faltan[:5]}")
    for e in r.get("estratos") or []:
        if "imagenes" in e and not (ctx.ent.datasets / e["imagenes"]).is_dir():
            errores.append(f"falta la carpeta de imágenes {e['imagenes']}")
    pendientes = [dep for dep in prueba.depende_de
                  if (Carpeta(ctx.ent, ctx.catalogo[dep]).leer("resultado.json") or {}).get("estado") != "completo"]
    if pendientes:
        errores.append(f"depende de {', '.join(pendientes)}, todavía sin completar (se resuelve al correr la fase)")
    return errores


def cmd_verificar(args) -> int:
    ent = detectar()
    catalogo = cargar_catalogo(ent.catalogo)
    ctx = _contexto(args, catalogo)
    pruebas = seleccionar(catalogo, args.objetivos or ["todas"])
    print(f"modo {ent.modo} · workspace {ent.ws} · consola {ent.consola_url} · "
          f"media ve los datasets en {ent.datasets_medios}")
    malas = 0
    for p in pruebas:
        errores = _verificar_prueba(ctx, p)
        bloqueantes = [e for e in errores if "se resuelve al correr" not in e]
        malas += bool(bloqueantes)
        print(f"  {p.id:8} {'OK' if not bloqueantes else 'FALLA'}")
        for e in errores:
            print(f"           - {e}")
    if ctx.consola.salud():
        objetivo = ctx.consola.objetivo()
        print(f"consola OK · modelo cargado: {(objetivo.get('model') or {}).get('ref')} · listo: {objetivo.get('ready')}")
    else:
        print("⚠ la consola no responde: `correr` no va a poder disparar nada")
    return 1 if malas else 0


def _correr_una(ctx: Contexto, prueba) -> dict:
    carpeta = Carpeta(ctx.ent, prueba)
    carpeta.preparar(forzar=ctx.forzar)
    objetivo = None
    try:
        objetivo = ctx.consola.objetivo()
    except (ConsolaError, OSError):
        pass
    carpeta.escribir("entorno.json", foto(ctx.ent, objetivo=objetivo, servicio_gpu=prueba.receta.get("instancia")))
    carpeta.comando(f"python -m tools.evidencia {' '.join(sys.argv[1:])}")
    return FAMILIAS[prueba.familia](ctx, prueba, carpeta)


def _correr(args, opciones: dict | None = None) -> int:
    ent = detectar()
    catalogo = cargar_catalogo(ent.catalogo)
    ctx = _contexto(args, catalogo)
    if opciones:
        ctx.opciones.update(opciones)
    pruebas = seleccionar(catalogo, args.objetivos)
    if any(p.familia not in SIN_CONSOLA for p in pruebas) and not ctx.consola.salud():
        print(f"la consola no responde en {ent.consola_url}", file=sys.stderr)
        return 2
    fallas = 0
    with Candado(ent.resultados / ".driver.lock"):
        for prueba in pruebas:
            _avisar(f"== {prueba.id} — {prueba.titulo}")
            try:
                salida = _correr_una(ctx, prueba)
                _avisar(f"   {prueba.id}: {json.dumps(salida, ensure_ascii=False)}")
                if salida.get("estado") != "completo":
                    fallas += 1
            except PreRegistroCambiado as exc:
                _avisar(f"   {prueba.id}: {exc}")
                fallas += 1
            except Exception as exc:  # noqa: BLE001 - una prueba rota no frena a las demás
                fallas += 1
                _avisar(f"   {prueba.id}: ERROR {type(exc).__name__}: {exc}")
                carpeta = Carpeta(ent, prueba)
                carpeta.comando(f"ERROR {type(exc).__name__}: {exc}")
                (carpeta.dir / "logs").mkdir(parents=True, exist_ok=True)
                (carpeta.dir / "logs" / "ultimo_error.txt").write_text(traceback.format_exc(), encoding="utf-8")
                if getattr(args, "parar", False):
                    break
            finally:
                escribir_indice(ent, catalogo)
    return 1 if fallas else 0


def cmd_correr(args) -> int:
    return _correr(args)


def cmd_vivo(args) -> int:
    args.objetivos = [args.prueba]
    return _correr(args, {"toma": args.toma, "config": args.config, "unidades": args.unidades,
                          "sin_reinicio": args.sin_reinicio})


def cmd_estado(args) -> int:
    ent = detectar()
    catalogo = cargar_catalogo(ent.catalogo)
    for p in seleccionar(catalogo, args.objetivos or ["todas"]):
        e = _estado_prueba(ent, p)
        conf = " (confirmado)" if e["confirmado"] else ""
        print(f"{p.fase}  {p.id:8} {e['estado']:11} corridas {e['corridas_ok']}/{e['corridas']:<4} "
              f"veredicto: {e['veredicto'] or '—'}{conf}")
    return 0


def cmd_veredicto(args) -> int:
    ent = detectar()
    catalogo = cargar_catalogo(ent.catalogo)
    if args.prueba not in catalogo:
        raise SystemExit(f"no existe la prueba {args.prueba}")
    carpeta = Carpeta(ent, catalogo[args.prueba])
    resultado = carpeta.leer("resultado.json")
    if not resultado or resultado.get("estado") != "completo":
        raise SystemExit(f"{args.prueba} no está completa: no hay veredicto que confirmar")
    resultado.setdefault("veredicto", {})["confirmado"] = {
        "valor": args.valor, "motivo": args.motivo, "quien": args.quien, "fecha": ahora()}
    carpeta.escribir("resultado.json", resultado)
    carpeta.comando(f"veredicto confirmado: {args.valor} ({args.quien}): {args.motivo}")
    escribir_indice(ent, catalogo)
    print(f"{args.prueba}: veredicto {args.valor} confirmado por {args.quien}")
    return 0


def cmd_descartar(args) -> int:
    """Una toma que falló por algo ajeno a lo que se mide (alguien cruzó el cuadro, se cortó la
    cámara) se saca del agregado — con motivo y firma, y queda listada como no evaluable."""
    ent = detectar()
    catalogo = cargar_catalogo(ent.catalogo)
    carpeta = Carpeta(ent, catalogo[args.prueba])
    descartes = carpeta.leer("descartes.json") or {}
    descartes[args.session_id] = {"motivo": args.motivo, "quien": args.quien, "fecha": ahora()}
    carpeta.escribir("descartes.json", descartes)
    carpeta.comando(f"descartar {args.session_id} ({args.quien}): {args.motivo}")
    print(f"{args.prueba}: {args.session_id} descartada; volvé a correr `correr {args.prueba}` para re-agregar")
    return 0


def cmd_indice(_args) -> int:
    ent = detectar()
    print(escribir_indice(ent, cargar_catalogo(ent.catalogo)))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m tools.evidencia", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("lista")
    p.add_argument("--fase")
    p.set_defaults(f=cmd_lista)
    p = sub.add_parser("verificar")
    p.add_argument("objetivos", nargs="*")
    p.set_defaults(f=cmd_verificar)
    p = sub.add_parser("correr")
    p.add_argument("objetivos", nargs="+", help="IDs (ALR-01), fases (F3) o 'todas'")
    p.add_argument("--solo", help="subconjunto de claves (clips, estratos, trabajos) separadas por coma")
    p.add_argument("--reagregar", action="store_true", help="no dispara corridas: re-agrega lo que ya existe")
    p.add_argument("--forzar", action="store_true", help="archiva la carpeta si el pre-registro cambió")
    p.add_argument("--parar", action="store_true", help="frena en la primera prueba que falle")
    p.set_defaults(f=cmd_correr)
    p = sub.add_parser("vivo", help="una toma de latencia con la OAK-D (RT-03); el rodaje (RT-04) va por rodaje.ps1")
    p.add_argument("prueba", choices=["RT-03"])
    p.add_argument("--toma", required=True)
    p.add_argument("--config", required=True)
    p.add_argument("--unidades", type=int)
    p.add_argument("--sin-reinicio", action="store_true", help="nativo: el media-plane ya se reinició a mano")
    p.add_argument("--forzar", action="store_true")
    p.set_defaults(f=cmd_vivo)
    p = sub.add_parser("estado")
    p.add_argument("objetivos", nargs="*")
    p.set_defaults(f=cmd_estado)
    p = sub.add_parser("veredicto")
    p.add_argument("prueba")
    p.add_argument("valor", choices=VEREDICTOS)
    p.add_argument("--motivo", required=True)
    p.add_argument("--quien", required=True)
    p.set_defaults(f=cmd_veredicto)
    p = sub.add_parser("indice")
    p.set_defaults(f=cmd_indice)
    p = sub.add_parser("descartar", help="saca una toma del rodaje en vivo (RT-04) del agregado, con motivo")
    p.add_argument("prueba", choices=["RT-04"])
    p.add_argument("session_id")
    p.add_argument("--motivo", required=True)
    p.add_argument("--quien", required=True)
    p.set_defaults(f=cmd_descartar)
    args = ap.parse_args(argv)
    try:
        return args.f(args)
    except CatalogoInvalido as exc:
        print(f"catálogo inválido: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
