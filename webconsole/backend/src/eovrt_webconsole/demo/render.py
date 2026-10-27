"""Render post-corrida de la demo (spec 2026-10-23 §6.4.5): video, cuadros clave, línea de tiempo.

Insumos (todos artefactos reales de la corrida, leídos del filesystem compartido —
paridad de rutas, ADR-009—):
- `previews/<unit_id>.preview.jpg` del media-plane: cada cuadro procesado, ya anotado
  con sus cajas (`save_previews: true`);
- `detections.jsonl` del media-plane: el orden y la hora (`source.timestamp_ms`) de
  cada cuadro;
- `pattern_events.jsonl` y `alerts.jsonl` del control-plane: el estado de cada
  condición y las alertas (la verdad del Resultado: en vivo no se escriben a disco);
- `distribution/notifications.jsonl` del experimento: qué pasó con cada notificación;
- los mensajes del testigo MQTT de la sesión.

El video muestra EXACTAMENTE los cuadros que procesó el sistema: cada cuadro dura hasta
el siguiente según su hora de fuente (el último, 1 s), con el demuxer concat de ffmpeg,
en H.264 a 30 fps. Los colores de estado son los de `defensa/overlay_render.py`, para
que se vea igual que V1 y VG1.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Colores de estado de defensa/overlay_render.py (COL_STATE, ahí en BGR para cv2),
# convertidos a RGB para Pillow. Un test compara ambas tablas.
COLOR_ESTADO_RGB = {
    "inactive": (140, 140, 140),
    "candidate": (255, 200, 60),
    "sustained": (255, 160, 40),
    "confirmed": (230, 60, 60),
    "resolved": (120, 200, 120),
}
ORDEN_ESTADO = {"inactive": 0, "resolved": 0, "candidate": 1, "sustained": 2, "confirmed": 3}
ROTULO_ESTADO = {
    "inactive": "OK",
    "candidate": "CONFIRMANDO",
    "confirmed": "ALERTA",
    "sustained": "ALERTA",
    "resolved": "RESUELTA",
}
NOMBRE_CONDICION = {"CR-01": "Casco", "CR-02": "Chaleco"}
RESUELTA_VISIBLE_MS = 1500.0  # como RESOLVED_HOLD del overlay (45 cuadros a 30 fps)
ULTIMO_CUADRO_S = 1.0
FPS_SALIDA = 30


@dataclass
class Cuadro:
    frame_index: int
    unit_id: str
    timestamp_ms: float
    preview: Path | None


def _leer_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    filas: list[dict] = []
    for linea in path.read_text(encoding="utf-8").splitlines():
        if not linea.strip():
            continue
        try:
            fila = json.loads(linea)
        except json.JSONDecodeError:
            continue  # línea truncada por un corte: se saltea
        if isinstance(fila, dict):
            filas.append(fila)
    return filas


def leer_cuadros(media_dir: Path) -> list[Cuadro]:
    cuadros: list[Cuadro] = []
    for evento in _leer_jsonl(media_dir / "detections.jsonl"):
        source = evento.get("source") or {}
        frame, ts, unit = source.get("frame_index"), source.get("timestamp_ms"), evento.get("unit_id")
        if frame is None or ts is None or not unit:
            continue
        preview = media_dir / "previews" / f"{unit}.preview.jpg"
        cuadros.append(Cuadro(int(frame), str(unit), float(ts), preview if preview.is_file() else None))
    cuadros.sort(key=lambda c: c.frame_index)
    return cuadros


def duraciones_s(cuadros: list[Cuadro]) -> list[float]:
    """Cada cuadro dura hasta el siguiente según su hora de fuente; el último, 1 s."""
    durs: list[float] = []
    for actual, siguiente in zip(cuadros, cuadros[1:]):
        durs.append(max(0.001, (siguiente.timestamp_ms - actual.timestamp_ms) / 1000.0))
    if cuadros:
        durs.append(ULTIMO_CUADRO_S)
    return durs


def estados_por_cuadro(cuadros: list[Cuadro], eventos: list[dict]) -> dict[str, list[str]]:
    """condición -> estado mostrado en cada cuadro (el más avanzado entre sujetos)."""
    cambios = sorted(
        (
            (int(e["frame_index"]), float(e.get("timestamp_ms") or 0.0), e["condition_id"],
             e.get("subject_key") or "", e["state"])
            for e in eventos
            if e.get("event_type") == "pattern_state_changed" and e.get("frame_index") is not None
            and e.get("condition_id") and e.get("state") in ORDEN_ESTADO
        ),
        key=lambda c: c[0],
    )
    condiciones = sorted({c[2] for c in cambios} | set(NOMBRE_CONDICION))
    por_sujeto: dict[tuple[str, str], tuple[str, float]] = {}
    salida: dict[str, list[str]] = {c: [] for c in condiciones}
    i = 0
    for cuadro in cuadros:
        while i < len(cambios) and cambios[i][0] <= cuadro.frame_index:
            frame, ts, cond, sujeto, estado = cambios[i]
            por_sujeto[(cond, sujeto)] = (estado, ts)
            i += 1
        for cond in condiciones:
            visibles = []
            for (c, _s), (estado, desde) in por_sujeto.items():
                if c != cond:
                    continue
                if estado == "resolved" and cuadro.timestamp_ms - desde >= RESUELTA_VISIBLE_MS:
                    estado = "inactive"
                visibles.append(estado)
            salida[cond].append(max(visibles, key=lambda s: ORDEN_ESTADO[s]) if visibles else "inactive")
    return salida


def _fuente(tamano: int):
    from PIL import ImageFont

    try:
        return ImageFont.load_default(size=tamano)
    except TypeError:  # Pillow sin FreeType: la fuente bitmap fija
        return ImageFont.load_default()


def _tira_linea_de_tiempo(estados: dict[str, list[str]], ancho: int, alto_fila: int):
    """La línea de tiempo completa, dibujada UNA vez y pegada en cada cuadro."""
    from PIL import Image, ImageDraw

    conds = sorted(estados)
    n = max((len(v) for v in estados.values()), default=0)
    tira = Image.new("RGB", (ancho, max(1, alto_fila * len(conds))), (20, 20, 20))
    if n == 0:
        return tira
    draw = ImageDraw.Draw(tira)
    for fila, cond in enumerate(conds):
        y0 = fila * alto_fila
        for x in range(ancho):
            estado = estados[cond][min(n - 1, x * n // ancho)]
            draw.line([(x, y0 + 1), (x, y0 + alto_fila - 2)], fill=COLOR_ESTADO_RGB[estado])
    return tira


def _componer(
    img, idx: int, total: int, cuadro: Cuadro, estados: dict[str, list[str]], tira,
    marcas_alerta: list[int], fps_efectivos: float | None, t0_ms: float,
):
    from PIL import ImageDraw

    ancho, alto = img.size
    draw = ImageDraw.Draw(img, "RGBA")
    grande, chica = _fuente(max(14, alto // 22)), _fuente(max(11, alto // 36))
    # Franja superior: estado por condición (los colores del overlay de la defensa).
    draw.rectangle([(0, 0), (ancho, alto // 9)], fill=(20, 20, 20, 170))
    x = 12
    for cond in sorted(estados):
        estado = estados[cond][idx]
        texto = f"{cond} {NOMBRE_CONDICION.get(cond, '')}: {ROTULO_ESTADO[estado]}"
        draw.text((x, 10), texto, font=grande, fill=COLOR_ESTADO_RGB[estado] + (255,))
        x += int(draw.textlength(texto, font=grande)) + 36
    # Franja inferior: línea de tiempo, marcas de alerta y el cursor.
    alto_tira = tira.size[1]
    y_tira = alto - alto_tira - 26
    draw.rectangle([(0, y_tira - 6), (ancho, alto)], fill=(20, 20, 20, 200))
    img.paste(tira, (0, y_tira))
    for marca in marcas_alerta:
        px = marca * ancho // max(1, total)
        draw.line([(px, y_tira - 6), (px, y_tira + alto_tira)], fill=(230, 60, 60, 255), width=2)
    px = idx * ancho // max(1, total)
    draw.line([(px, y_tira - 6), (px, alto)], fill=(255, 255, 255, 255), width=2)
    # «~» y no «≈»: la fuente por defecto de Pillow no trae ese glifo.
    fps = f" · ~{fps_efectivos:.1f} cuadros/s efectivos" if fps_efectivos else ""
    rotulo = f"t = {(cuadro.timestamp_ms - t0_ms) / 1000.0:5.1f} s · cuadro {idx + 1} de {total}{fps}"
    draw.text((12, alto - 22), rotulo, font=chica, fill=(230, 230, 230, 255))
    return img


def _indice_desde(cuadros: list[Cuadro], frame_index: int | None) -> int | None:
    """Primer cuadro procesado con frame_index >= el pedido (y con preview)."""
    if frame_index is None:
        return None
    for i, c in enumerate(cuadros):
        if c.frame_index >= frame_index and c.preview is not None:
            return i
    return None


def linea_de_tiempo(
    alertas: list[dict], eventos: list[dict], cuadros: list[Cuadro],
    testigo: list[dict], notificaciones: dict[str, dict],
) -> list[dict[str, Any]]:
    """Por alerta: primera evidencia, confirmación, broker, resolución y los dos tramos.

    - evidencia → confirmación: hora de FUENTE de los dos cuadros (la espera a
      propósito de la ventana de persistencia; no es latencia).
    - confirmación → broker: hora de recepción del testigo menos `confirmed_wall_ms`
      del mensaje (el instante en que el control publicó la alerta en el bus).
    """
    ts_por_frame = {c.frame_index: c.timestamp_ms for c in cuadros}
    ts_por_unidad = {c.unit_id: c.timestamp_ms for c in cuadros}
    salida: list[dict[str, Any]] = []
    for n, alerta in enumerate(sorted(alertas, key=lambda a: a.get("frame_index") or 0), start=1):
        frame_conf = alerta.get("frame_index")
        frame_ev = alerta.get("first_evidence_frame_index")
        t_ev = ts_por_unidad.get(alerta.get("first_evidence_unit_id")) or ts_por_frame.get(frame_ev)
        t_conf = alerta.get("timestamp_ms")
        resolucion = next(
            (
                e for e in sorted(eventos, key=lambda e: e.get("frame_index") or 0)
                if e.get("state") == "resolved" and e.get("subject_key") == alerta.get("subject_key")
                and (e.get("frame_index") or 0) > (frame_conf or 0)
            ),
            None,
        )
        mensaje = next(
            (m for m in testigo if (m.get("payload") or {}).get("alert_id") == alerta.get("alert_id")),
            None,
        )
        confirmado_wall = ((mensaje or {}).get("payload") or {}).get("confirmed_wall_ms")
        t_broker = mensaje.get("recibido_ms") if mensaje else None
        entrega = notificaciones.get(str(alerta.get("alert_id"))) or {}
        salida.append({
            "n": n,
            "alert_id": alerta.get("alert_id"),
            "condition_id": alerta.get("condition_id"),
            "severity": alerta.get("severity"),
            "frame_primera_evidencia": frame_ev,
            "frame_confirmacion": frame_conf,
            "frame_resolucion": (resolucion or {}).get("frame_index"),
            "t_primera_evidencia_ms": t_ev,
            "t_confirmacion_ms": t_conf,
            "t_resolucion_ms": (resolucion or {}).get("timestamp_ms"),
            "confirmed_wall_ms": confirmado_wall,
            "t_broker_ms": t_broker,
            "broker_topic": (mensaje or {}).get("topic"),
            "entrega": entrega.get("outcome"),
            "tramos": {
                "evidencia_a_confirmacion_ms": (
                    round(t_conf - t_ev, 1) if t_conf is not None and t_ev is not None else None
                ),
                "confirmacion_a_broker_ms": (
                    round(t_broker - confirmado_wall, 1)
                    if t_broker is not None and confirmado_wall is not None else None
                ),
            },
        })
    return salida


def _cuadros_clave(
    salida: Path, renders: dict[int, Path], cuadros: list[Cuadro], linea: list[dict],
) -> list[dict[str, Any]]:
    destino = salida / "cuadros"
    destino.mkdir(parents=True, exist_ok=True)
    claves: list[dict[str, Any]] = []
    for entrada in linea:
        for orden, (tipo, frame) in enumerate(
            (("evidencia", entrada["frame_primera_evidencia"]),
             ("confirmacion", entrada["frame_confirmacion"]),
             ("resolucion", entrada["frame_resolucion"])),
            start=1,
        ):
            idx = _indice_desde(cuadros, frame)
            if idx is None or idx not in renders:
                continue
            nombre = f"alerta{entrada['n']:02d}_{entrada['condition_id']}_{orden}-{tipo}.jpg"
            shutil.copy2(renders[idx], destino / nombre)
            claves.append({"alerta": entrada["n"], "tipo": tipo, "archivo": f"cuadros/{nombre}",
                           "frame_index": cuadros[idx].frame_index})
    return claves


def _copiar_log(salida: Path, fuentes: dict[str, Path | None]) -> list[str]:
    destino = salida / "log"
    copiados: list[str] = []
    for nombre, origen in fuentes.items():
        if origen is None or not origen.is_file():
            continue
        (destino / nombre).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origen, destino / nombre)
        copiados.append(f"log/{nombre}")
    return copiados


def render_sesion(
    salida: Path,
    *,
    media_dir: Path | None,
    control_dir: Path | None,
    experimento_dir: Path | None,
    testigo: list[dict],
    ffmpeg: str = "ffmpeg",
) -> dict[str, Any]:
    """Arma `salida/` (= `defensa/sesiones/<id>/resultado/`). Nunca levanta por un
    insumo faltante: arma lo que se pueda y lo dice en `faltantes`/`errores`."""
    salida.mkdir(parents=True, exist_ok=True)
    errores: list[str] = []
    faltantes: list[str] = []
    cuadros = leer_cuadros(media_dir) if media_dir is not None else []
    if not cuadros:
        faltantes.append("detections.jsonl del media-plane")
    eventos = _leer_jsonl(control_dir / "pattern_events.jsonl") if control_dir else []
    alertas = _leer_jsonl(control_dir / "alerts.jsonl") if control_dir else []
    if control_dir is None or not (control_dir / "pattern_events.jsonl").is_file():
        faltantes.append("pattern_events.jsonl del control-plane")
    notificaciones = {
        str(r.get("alert_id")): r
        for r in _leer_jsonl(experimento_dir / "distribution" / "notifications.jsonl")
    } if experimento_dir is not None else {}

    con_preview = [c for c in cuadros if c.preview is not None]
    if cuadros and not con_preview:
        faltantes.append("previews del media-plane (save_previews)")
    duracion_fuente_s = (
        (cuadros[-1].timestamp_ms - cuadros[0].timestamp_ms) / 1000.0 if len(cuadros) > 1 else None
    )
    fps_efectivos = (
        round((len(cuadros) - 1) / duracion_fuente_s, 2) if duracion_fuente_s else None
    )
    linea = linea_de_tiempo(alertas, eventos, cuadros, testigo, notificaciones)

    renders: dict[int, Path] = {}
    video: str | None = None
    trabajo = salida / ".render"
    if con_preview:
        from PIL import Image

        estados = estados_por_cuadro(cuadros, eventos)
        trabajo.mkdir(parents=True, exist_ok=True)
        primero = Image.open(con_preview[0].preview)
        ancho = primero.size[0]
        primero.close()
        tira = _tira_linea_de_tiempo(estados, ancho, alto_fila=8)
        marcas = [
            i for i in (
                _indice_desde(cuadros, a.get("frame_index")) for a in alertas
            ) if i is not None
        ]
        entradas: list[list] = []  # [archivo, duración en s]
        durs = duraciones_s(cuadros)
        t0 = cuadros[0].timestamp_ms
        for idx, cuadro in enumerate(cuadros):
            if cuadro.preview is None:
                # Sin preview (p.ej. el escritor de previews falló en uno): el cuadro
                # anterior se queda en pantalla también ese intervalo.
                if entradas:
                    entradas[-1][1] += durs[idx]
                continue
            with Image.open(cuadro.preview) as original:
                img = original.convert("RGB")
            img = _componer(img, idx, len(cuadros), cuadro, estados, tira, marcas, fps_efectivos, t0)
            destino = trabajo / f"{idx:06d}.jpg"
            img.save(destino, quality=88)
            renders[idx] = destino
            entradas.append([destino, durs[idx]])
        if entradas:
            # El demuxer concat no respeta la duración del ÚLTIMO archivo (y cómo la
            # trata cambia entre versiones de ffmpeg): se repite el último y se corta
            # el video en la suma exacta de las duraciones (`-t`).
            texto = "".join(f"file '{p}'\nduration {d:.6f}\n" for p, d in entradas)
            texto += f"file '{entradas[-1][0]}'\n"
            (trabajo / "lista.txt").write_text(texto, encoding="utf-8")
            total_s = sum(d for _p, d in entradas)
            destino_video = salida / "video.mp4"
            cmd = [
                ffmpeg, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                "-i", str(trabajo / "lista.txt"),
                "-vf", f"fps={FPS_SALIDA},scale=trunc(iw/2)*2:trunc(ih/2)*2,format=yuv420p",
                "-t", f"{total_s:.3f}",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-movflags", "+faststart",
                str(destino_video),
            ]
            try:
                subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=600)
                video = "video.mp4"
            except (OSError, subprocess.SubprocessError) as exc:
                detalle = getattr(exc, "stderr", None) or str(exc)
                errores.append(f"ffmpeg no pudo armar el video: {str(detalle)[-300:]}")

    claves = _cuadros_clave(salida, renders, cuadros, linea)
    shutil.rmtree(trabajo, ignore_errors=True)

    (salida / "linea_de_tiempo.json").write_text(
        json.dumps(linea, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    log = _copiar_log(salida, {
        "media/summary.json": media_dir / "summary.json" if media_dir else None,
        "media/metrics.jsonl": media_dir / "metrics.jsonl" if media_dir else None,
        "media/effective_config.yaml": media_dir / "effective_config.yaml" if media_dir else None,
        "control/summary.json": control_dir / "summary.json" if control_dir else None,
        "control/alerts.jsonl": control_dir / "alerts.jsonl" if control_dir else None,
        "control/pattern_events.jsonl": control_dir / "pattern_events.jsonl" if control_dir else None,
        "control/effective_config.yaml": control_dir / "effective_config.yaml" if control_dir else None,
        "distribucion/distribution_summary.json": (
            experimento_dir / "distribution" / "distribution_summary.json" if experimento_dir else None
        ),
        "distribucion/notifications.jsonl": (
            experimento_dir / "distribution" / "notifications.jsonl" if experimento_dir else None
        ),
        "experimento/report.json": (
            experimento_dir / "report" / "report.json" if experimento_dir else None
        ),
        "experimento/report.md": experimento_dir / "report" / "report.md" if experimento_dir else None,
    })
    resumen = {
        "cuadros_procesados": len(cuadros),
        "cuadros_con_preview": len(con_preview),
        "duracion_fuente_s": round(duracion_fuente_s, 2) if duracion_fuente_s else None,
        "fps_efectivos": fps_efectivos,
        "alertas": len(alertas),
        "video": video,
        "cuadros_clave": claves,
        "linea_de_tiempo": "linea_de_tiempo.json",
        "log": log,
        "faltantes": faltantes,
        "errores": errores,
    }
    (salida / "resumen.json").write_text(
        json.dumps(resumen, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return resumen
