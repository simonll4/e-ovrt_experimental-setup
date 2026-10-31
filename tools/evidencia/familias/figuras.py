"""Cuadros anotados de éxito y de fallo (VIS-01, doc 137 §3.2).

Dibuja sobre el cuadro original del clip (ffmpeg lo extrae, Pillow dibuja):

  - la caja de cada persona con su puntaje y su track (reconstruido como en ERR-01);
  - las cajas de casco y chaleco con su puntaje;
  - la región que evalúa la regla para la condición (upper_body / torso, del pattern set);
  - la caja de la referencia, punteada;
  - una franja con la condición, qué pasó y de qué prueba sale.

La selección está pre-registrada en la receta, sin elegir a mano:

  exitos      la primera alerta acertada de cada escenario, del rodaje y de obra real (por sujeto)
  fallos      toda falsa alarma y todo episodio perdido del rodaje (escena y sujeto); en obra real,
              los episodios perdidos (sus falsas alarmas están en la muestra de ERR-01)
  obra_real   la muestra de ERR-01, en dos versiones: CIEGA (solo el sujeto y su región, sin
              puntajes ni referencia ni causa) para la revisión humana, y COMPLETA para el informe

Dónde queda: los cuadros, en `defensa/figuras/VIS-01/` (git-ignorado). Los de los clips de
internet NUNCA van a un repo público ni a un canal nuevo (CLAUDE.md, paquete de evidencia).
Antes de pasar uno al informe se recorta y se difuminan las caras a mano (doc 137, D2). En
`results/gen2/VIS-01/` queda solo el índice: qué cuadro, de qué alerta, con qué huella.
"""
from __future__ import annotations

import csv
import json
import os
import subprocess
from collections.abc import Callable
from pathlib import Path

from ..catalogo import Prueba
from ..herramientas import clips_de, ruta_video
from ..huellas import sha256_archivo
from ..registro import Carpeta
from . import Contexto, familia
from .errores import (
    cargar_referencia,
    leer_cuadros,
    leer_jsonl,
    patrones_por_condicion,
    rastrear,
    region,
)

COLOR = {"person": (70, 140, 230), "helmet": (60, 190, 90), "vest": (250, 150, 40)}
COLOR_SUJETO = (230, 40, 40)
COLOR_REGION = (255, 230, 0)
COLOR_REF = (255, 255, 255)
CSV_COLUMNAS = ("n", "imagen", "condicion", "es_persona", "epp_visible", "nota")


def extraer_cuadro(video: Path, cuadro: int, fps: float, salida: Path) -> Path:
    """Un cuadro del video por su índice (búsqueda exacta de ffmpeg con `-ss` antes de `-i`)."""
    salida.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-v", "error", "-y", "-ss", f"{cuadro / fps:.4f}", "-i", str(video),
           "-frames:v", "1", str(salida)]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0 or not salida.is_file():
        raise RuntimeError(f"ffmpeg no extrajo el cuadro {cuadro} de {video}: {proc.stderr[-300:]}")
    return salida


def _punteada(draw, caja, color, paso: int = 8, ancho: int = 2) -> None:
    x1, y1, x2, y2 = caja
    for (a, b) in (((x1, y1), (x2, y1)), ((x2, y1), (x2, y2)), ((x2, y2), (x1, y2)), ((x1, y2), (x1, y1))):
        largo = max(abs(b[0] - a[0]), abs(b[1] - a[1]))
        n = max(1, int(largo // paso))
        for i in range(0, n, 2):
            t0, t1 = i / n, min(1.0, (i + 1) / n)
            draw.line([(a[0] + (b[0] - a[0]) * t0, a[1] + (b[1] - a[1]) * t0),
                       (a[0] + (b[0] - a[0]) * t1, a[1] + (b[1] - a[1]) * t1)], fill=color, width=ancho)


def dibujar(imagen: Path, salida: Path, *, cuadro: dict, sujeto: str | None, pat: dict | None,
            referencia: list[tuple], titulo: str, ciega: bool = False) -> Path:
    """`cuadro` es una entrada de `errores.leer_cuadros`. En la versión ciega solo se marca el
    sujeto y su región: ni puntajes, ni otras cajas, ni referencia, ni causa."""
    from PIL import Image, ImageDraw  # Pillow viene con el BFF

    img = Image.open(imagen).convert("RGB")
    draw = ImageDraw.Draw(img)
    grosor = max(2, img.width // 640)
    chica, grande = _fuente(max(12, img.width // 110)), _fuente(max(14, img.width // 70))

    def rotulo(caja, texto, color):
        x, y = caja[0], max(0, caja[1] - chica.size - 4 if hasattr(chica, "size") else caja[1] - 16)
        draw.text((x, y), texto, fill=color, font=chica, stroke_width=2, stroke_fill=(0, 0, 0))

    if not ciega:
        for _tid, caja, _attrs, _occ in referencia:
            _punteada(draw, caja, COLOR_REF, ancho=grosor)
        for etiqueta, caja, conf in cuadro.get("epp") or []:
            color = COLOR.get(etiqueta, (200, 200, 200))
            draw.rectangle(caja, outline=color, width=grosor)
            rotulo(caja, f"{etiqueta} {conf:.2f}", color)
        for tid, (caja, conf) in (cuadro.get("personas") or {}).items():
            if tid == sujeto:
                continue
            draw.rectangle(caja, outline=COLOR["person"], width=grosor)
            rotulo(caja, f"{tid} {conf:.2f}", COLOR["person"])
    if sujeto and sujeto in (cuadro.get("personas") or {}):
        caja, conf = cuadro["personas"][sujeto]
        draw.rectangle(caja, outline=COLOR_SUJETO, width=grosor + 1)
        if pat:
            draw.rectangle(region(caja, pat["region"]), outline=COLOR_REGION, width=grosor)
        if not ciega:
            rotulo(caja, f"{sujeto} {conf:.2f}", COLOR_SUJETO)
    alto_barra = (grande.size if hasattr(grande, "size") else 14) + 16
    draw.rectangle([(0, 0), (img.width, alto_barra)], fill=(20, 20, 20))
    draw.text((10, 8), titulo, fill=(255, 255, 255), font=grande)
    salida.parent.mkdir(parents=True, exist_ok=True)
    img.save(salida)
    return salida


def _fuente(tamano: int):
    """La tipografía por defecto de Pillow escalable (≥ 10.1); si no, la de mapa de bits."""
    from PIL import ImageFont

    try:
        return ImageFont.load_default(size=tamano)
    except TypeError:
        return ImageFont.load_default()


def recortar(crudo: Path, caja, salida: Path, *, cuadro: dict, sujeto: str | None, pat: dict | None,
             referencia: list[tuple], titulo: str, ciega: bool = False, margen: float = 0.8,
             lado_min: int = 240, alto_final: int = 640) -> Path:
    """El sujeto con contexto, para el informe (doc 137, D2) y para la revisión ciega.

    Recorta del cuadro CRUDO (su caja más un 80 % por lado, al menos `lado_min` px), lo amplía
    sin suavizar (vecino más cercano: se ven los píxeles que hubo, no un detalle inventado) y
    recién ahí dibuja, con las cajas llevadas a la escala del recorte, para que los rótulos se
    lean. Las caras se difuminan a mano antes de llevarlo al informe si hiciera falta.
    """
    from PIL import Image

    img = Image.open(crudo).convert("RGB")
    x1, y1, x2, y2 = caja
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    medio_w = max((x2 - x1) * (0.5 + margen), lado_min / 2)
    medio_h = max((y2 - y1) * (0.5 + margen), lado_min / 2)
    ox, oy = max(0, int(cx - medio_w)), max(0, int(cy - medio_h))
    fx, fy = min(img.width, int(cx + medio_w)), min(img.height, int(cy + medio_h))
    escala = max(1.0, alto_final / max(1, fy - oy))
    rec = img.crop((ox, oy, fx, fy))
    rec = rec.resize((round(rec.width * escala), round(rec.height * escala)), Image.NEAREST)
    tmp = salida.with_name(f".{salida.stem}.crudo.png")
    salida.parent.mkdir(parents=True, exist_ok=True)
    rec.save(tmp)

    def llevar(b):
        return [(b[0] - ox) * escala, (b[1] - oy) * escala, (b[2] - ox) * escala, (b[3] - oy) * escala]

    local = {
        "personas": {t: (llevar(c), conf) for t, (c, conf) in (cuadro.get("personas") or {}).items()},
        "epp": [(e, llevar(c), conf) for e, c, conf in cuadro.get("epp") or []],
    }
    ref = [(t, llevar(c), a, o) for t, c, a, o in referencia]
    try:
        return dibujar(tmp, salida, cuadro=local, sujeto=sujeto, pat=pat, referencia=ref,
                       titulo=f"{titulo} · x{escala:.1f}", ciega=ciega)
    finally:
        tmp.unlink(missing_ok=True)


# --- selección ------------------------------------------------------------------------


def _alertas_de(ctx: Contexto, registro: dict) -> list[dict]:
    return [a for a in leer_jsonl(ctx.ent.control_runs / registro["control_run_id"] / "alerts.jsonl")
            if a.get("event_type") == "alert_event"]


def episodios_perdidos(ev: dict, gt: dict, alertas: list[dict]) -> list[tuple[str, int, str | None]]:
    """(condición, cuadro en que la alerta tendría que haber salido, episodio) de cada perdido.

    El evaluador por episodio cuenta los perdidos (`missed_alerts_count`) pero no los lista; se
    derivan con sus mismas ventanas (`effective_matching_windows`): un episodio sin ninguna alerta
    de su condición entre su inicio y `t_alert_max_ms`. El cuadro dibujado es el del inicio más la
    persistencia mínima. Quien llama compara la cantidad con la del evaluador y lo anota.
    """
    if ev.get("missed_alerts"):
        return [(m["condition_id"], int(m["expected_alert_frame_index"]), m.get("expected_id"))
                for m in ev["missed_alerts"]]
    if not ev.get("missed_alerts_count"):
        return []
    ventanas = ev.get("effective_matching_windows") or {}
    fps = float(gt.get("fps_nominal") or 30)
    out = []
    for epi in gt.get("episodes") or []:
        w = ventanas.get(epi["condition_id"]) or {}
        fin = epi["start_ms"] + float(w.get("t_alert_max_ms") or (epi["end_ms"] - epi["start_ms"]))
        acertado = any(a["condition_id"] == epi["condition_id"] and epi["start_ms"] <= float(a["timestamp_ms"]) <= fin
                       for a in alertas)
        if not acertado:
            t = epi["start_ms"] + float(w.get("persistencia_min_ms") or 0)
            out.append((epi["condition_id"], int(t / 1000 * fps), epi.get("id")))
    return out


def seleccionar_banco(ctx: Contexto, spec: dict, banco: str = "rodaje") -> list[dict]:
    """Éxitos (primera alerta acertada por escenario) y fallos (falsas alarmas y perdidos) de un
    banco (`rodaje` o `internet`). En obra real las falsas alarmas se dejan afuera
    (`falsas_alarmas: false`): son cientos y las representa la muestra de ERR-01."""
    ent = ctx.ent
    elegidos = []
    vistos_escenario = set()
    for etiqueta, pid in spec["pruebas"].items():
        corridas = ctx.corridas_completas(pid)
        carpeta = ctx.carpeta(pid)
        for clip in clips_de(ent, banco):
            reg = corridas.get(clip)
            if not reg:
                continue
            ev = json.loads((carpeta.dir / reg["eval"]).read_text(encoding="utf-8"))
            gt = json.loads((ent.gt_banco / f"{clip}.json").read_text(encoding="utf-8"))
            alertas = _alertas_de(ctx, reg)
            for u in (ev.get("unexpected_alerts") or []) if spec.get("falsas_alarmas", True) else []:
                a = next((x for x in alertas if x.get("alert_id") == u.get("alert_id")), None)
                if a:
                    elegidos.append({"tipo": "fallo_falsa_alarma", "banco": banco, "prueba": pid, "granularidad": etiqueta,
                                     "clip": clip, "cuadro": int(a["frame_index"]), "condicion": a["condition_id"],
                                     "sujeto": a["subject_key"].split(":")[-1] if etiqueta == "sujeto" else None,
                                     "alert_id": a["alert_id"]})
            perdidos = episodios_perdidos(ev, gt, alertas)
            for cond, cuadro, episodio in perdidos:
                elegidos.append({"tipo": "fallo_perdido", "banco": banco, "prueba": pid, "granularidad": etiqueta, "clip": clip,
                                 "cuadro": cuadro, "condicion": cond, "sujeto": None, "episodio": episodio,
                                 "consistente_con_evaluador": len(perdidos) == ev.get("missed_alerts_count", 0)})
            if etiqueta != spec.get("exitos_de") or ev.get("matched_alerts_count", 0) < 1:
                continue
            escenario = gt.get("scenario")
            if spec.get("uno_por_escenario", True) and escenario in vistos_escenario:
                continue
            for epi in gt["episodes"]:
                a = next((x for x in alertas if x["condition_id"] == epi["condition_id"]
                          and epi["start_ms"] <= float(x["timestamp_ms"]) <= epi["end_ms"] + 2000), None)
                if a:
                    vistos_escenario.add(escenario)
                    elegidos.append({"tipo": "exito", "banco": banco, "prueba": pid, "granularidad": etiqueta, "clip": clip,
                                     "escenario": escenario, "cuadro": int(a["frame_index"]),
                                     "condicion": a["condition_id"], "sujeto": a["subject_key"].split(":")[-1],
                                     "alert_id": a["alert_id"]})
                    break
    return elegidos


def seleccionar_obra_real(ctx: Contexto, spec: dict) -> list[dict]:
    m = ctx.carpeta(spec["muestra_de"]).leer("muestra.json")
    if m is None:
        raise RuntimeError(f"{spec['muestra_de']} no dejó muestra.json: corréla antes")
    return [{"tipo": "obra_real", "banco": "internet", "prueba": spec["muestra_de"], "clip": x["clip"], "cuadro": x["cuadro_alerta"],
             "condicion": x["condicion"], "sujeto": x["track"], "alert_id": x["alert_id"], "n": x["n"],
             "causa": x["causa"]} for x in m]


# --- prueba ---------------------------------------------------------------------------


def carpeta_cuadros(ctx: Contexto, prueba_id: str) -> Path:
    """`defensa/figuras/<ID>/` del repo (git-ignorado); con `EOVRT_EVIDENCIA_SALIDA`, bajo esa
    raíz, como el resto de un ensayo fuera de la Victus."""
    salida = os.environ.get("EOVRT_EVIDENCIA_SALIDA")
    return (Path(salida) if salida else ctx.ent.repo) / "defensa" / "figuras" / prueba_id


@familia("figuras")
def correr(ctx: Contexto, prueba: Prueba, carpeta: Carpeta) -> dict:
    r = prueba.receta
    ent = ctx.ent
    extraer: Callable[[Path, int, float, Path], Path] = ctx.opciones.get("extraer_cuadro", extraer_cuadro)
    salida = carpeta_cuadros(ctx, prueba.id)
    patrones = patrones_por_condicion(ent.patrones / f"{r['patrones']}.yaml")
    detecciones = {**ctx.corridas_completas(r["detecciones"]["rodaje"]),
                   **ctx.corridas_completas(r["detecciones"]["obra_real"])}
    elegidos = seleccionar_banco(ctx, r["rodaje"], "rodaje") + seleccionar_obra_real(ctx, r["obra_real"])
    if r["obra_real"].get("pruebas"):
        # en obra real hay muy pocos episodios: se muestran todos los aciertos, no uno por escenario
        elegidos += seleccionar_banco(ctx, {**r["obra_real"], "falsas_alarmas": False, "uno_por_escenario": False},
                                      "internet")
    for i, e in enumerate(elegidos, 1):
        e["orden"] = i
    cache: dict[str, tuple] = {}
    indice, filas_csv = [], []
    # Por clip: rastrear un clip largo (v06_c01, 11 mil cuadros) una sola vez.
    for e in sorted(elegidos, key=lambda x: (x["clip"], x["cuadro"], x["orden"])):
        i, clip = e["orden"], e["clip"]
        if clip not in cache:
            gt = json.loads((ent.gt_banco / f"{clip}.json").read_text(encoding="utf-8"))
            rastreado = rastrear(Path(detecciones[clip]["detecciones"]), ent.trabajo / prueba.id / "rastreado" / f"{clip}.jsonl")
            cache = {clip: (gt, leer_cuadros(rastreado), cargar_referencia(ent.banco / "annotations" / f"{clip}.xml"))}
        gt, cuadros, referencia = cache[clip]
        fps = float(gt.get("fps_nominal") or 30)
        crudo = extraer(ruta_video(ent, clip), e["cuadro"], fps, salida / "_crudos" / f"{clip}_{e['cuadro']}.png")
        cuadro = cuadros.get(e["cuadro"], {})
        pat = patrones.get(e["condicion"])
        titulo = f"{e['tipo']} · {e['condicion']} · {clip} · cuadro {e['cuadro']} · {e['prueba']}"
        nombre = f"{e['tipo']}_{i:03d}_{clip}_{e['cuadro']}.png"
        completa = dibujar(crudo, salida / "completas" / nombre, cuadro=cuadro, sujeto=e.get("sujeto"), pat=pat,
                           referencia=referencia.get(e["cuadro"], []),
                           titulo=titulo + (f" · causa {e['causa']}" if e.get("causa") else ""))
        fila = {**e, "archivo": str(completa.relative_to(salida)), "sha256": sha256_archivo(completa),
                "internet": clip.startswith("v")}
        sujeto_caja = (cuadro.get("personas") or {}).get(e.get("sujeto") or "")
        if sujeto_caja:
            rec = recortar(crudo, sujeto_caja[0], salida / "recortes" / nombre, cuadro=cuadro, sujeto=e.get("sujeto"),
                           pat=pat, referencia=referencia.get(e["cuadro"], []), titulo=f"{e['condicion']} · {clip}")
            fila["recorte"] = str(rec.relative_to(salida))
            fila["sha256_recorte"] = sha256_archivo(rec)
        if e["tipo"] == "obra_real":
            ciega = dibujar(crudo, salida / "revision_ciega" / f"{e['n']:03d}.png", cuadro=cuadro,
                            sujeto=e.get("sujeto"), pat=pat, referencia=[], titulo=f"#{e['n']} · {e['condicion']}",
                            ciega=True)
            fila["archivo_ciego"] = str(ciega.relative_to(salida))
            if sujeto_caja:
                ciega_rec = recortar(crudo, sujeto_caja[0], salida / "revision_ciega" / f"{e['n']:03d}_recorte.png",
                                     cuadro=cuadro, sujeto=e.get("sujeto"), pat=pat, referencia=[],
                                     titulo=f"#{e['n']} · {e['condicion']}", ciega=True)
                fila["recorte_ciego"] = str(ciega_rec.relative_to(salida))
            filas_csv.append({"n": e["n"], "imagen": fila["archivo_ciego"], "condicion": e["condicion"],
                              "es_persona": "", "epp_visible": "", "nota": ""})
        indice.append(fila)
    indice.sort(key=lambda x: x["orden"])
    if filas_csv:
        ruta_csv = salida / "revision_ciega.csv"
        with ruta_csv.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=CSV_COLUMNAS)
            w.writeheader()
            w.writerows(sorted(filas_csv, key=lambda x: x["n"]))
        (salida / "LEEME.txt").write_text(
            "Revisión ciega de la muestra de ERR-01 (doc 137 §3.1).\n"
            "Mirá cada imagen de revision_ciega/ y completá revision_ciega.csv:\n"
            "  es_persona:   si / no  (¿la caja roja es una persona?)\n"
            "  epp_visible:  si / no / no_se_puede  (¿se ve el casco (CR-01) o el chaleco (CR-02)?)\n"
            "Sin abrir completas/ ni muestra.json antes de terminar. Al terminar, copiá el CSV a\n"
            "results/gen2/ERR-01/revision_humana.csv y volvé a correr ERR-01.\n"
            "Con asistencia de Claude: `revision-ciega pagina` arma revision.html con sus propuestas\n"
            "(propuestas_ia.json) y `revision-ciega cerrar` valida y copia el CSV (doc 134 §13.12).\n"
            "Los cuadros de clips de internet (v*) no se publican: nada de esta carpeta va a git.\n",
            encoding="utf-8")
    carpeta.escribir("indice_cuadros.json", {"salida": str(salida), "cuadros": indice})
    claves = ("rodaje.exito", "rodaje.fallo_falsa_alarma", "rodaje.fallo_perdido",
              "internet.exito", "internet.fallo_perdido", "internet.obra_real")
    conteo = {k: sum(1 for x in indice if f"{x['banco']}.{x['tipo']}" == k) for k in claves}
    resumen = [{"clave": k, "nombre": f"Cuadros: {k.replace('_', ' ')}", "valor": v, "unidad": None, "gen1": None}
               for k, v in conteo.items()]
    datos = {"familia": "figuras", "estado": "completo", "metricas": conteo, "resumen": resumen,
             "veredicto": {"confirmado": None, "propuesto": "otra_combinacion", "referencia": None,
                           "motivo": "figuras nuevas de la generación 2: no hay cifra de la generación 1 que comparar",
                           "diferencias": {}}}
    carpeta.resultado(datos)
    return {"estado": "completo", **conteo}
