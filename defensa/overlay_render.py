"""Overlay renderer para los videos de la defensa (V1/V2/V3/V-G1).

Compone sobre un clip del banco: detecciones (`detections.jsonl` del media-plane),
estados del patrón (`pattern_events.jsonl` del control-plane) y alertas
(`alerts.jsonl`), con banner de estado, línea de tiempo y panel de alerta.
Herramienta prevista en `docs/nucleo/09` §6.3; decisiones de alcance en
`docs/operacion/90` D-90.7 (resuelta 2026-08-05): V1–V3 = una persona, escena,
sin identidad; V-G1 = multitud con color por `track_id`.

Principio (doc 81 §1): el video ilustra una combinación MEDIDA — los insumos son
los artefactos reales de las campañas, no una corrida ad-hoc.

Uso:
  .venv-del-media-plane/bin/python overlay_render.py \
      --video <clip.mp4> --detections <detections.jsonl> \
      --control-run <dir con pattern_events.jsonl y alerts.jsonl> \
      --out <salida.mp4> [--color-by-track] [--highlight-class gloves] \
      [--title "V1 — la cadena completa"] [--fps-video 30]

  python3 overlay_render.py --selfcheck   # verifica la lógica de timeline
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

# --- paleta (BGR) ---
COL_CLASS = {
    "person": (200, 160, 60),
    "helmet": (80, 200, 80),
    "vest": (60, 140, 255),
}
COL_HIGHLIGHT = (255, 80, 255)     # clase nueva (V2)
COL_STATE = {
    "inactive": (140, 140, 140),
    "candidate": (60, 200, 255),   # amarillo
    "sustained": (40, 160, 255),   # ámbar
    "confirmed": (60, 60, 230),    # rojo
    "resolved": (120, 200, 120),   # verde
}
ORDEN_ESTADO = {"inactive": 0, "resolved": 0, "candidate": 1, "sustained": 2,
                "confirmed": 3}
COL_TRACK = [(80, 200, 80), (60, 140, 255), (230, 90, 60), (200, 160, 60),
             (180, 80, 220), (90, 220, 220), (140, 140, 250), (220, 200, 90)]


def leer_jsonl(p: Path):
    return [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]


def frame_de(unit_id: str) -> int:
    return int(unit_id.rsplit("_", 1)[1])


def construir_timeline(pattern_events: list, n_frames: int) -> dict:
    """condition_id -> lista de estados por frame (longitud n_frames).

    Con granularidad sujeto puede haber varias `subject_key` por condición: el
    estado mostrado es el MÁS AVANZADO entre sujetos en ese instante (el banner
    cuenta la condición de la escena; el detalle por sujeto va en las cajas).
    `resolved` vuelve a pintarse como estado propio durante RESOLVED_HOLD frames
    y después decae a inactive (visualmente: el episodio cerró bien).
    """
    RESOLVED_HOLD = 45  # 1,5 s a 30 fps
    por_subj: dict[tuple, list] = {}
    for e in pattern_events:
        if e.get("event_type") != "pattern_state_changed":
            continue
        clave = (e["condition_id"], e.get("subject_key") or "")
        por_subj.setdefault(clave, []).append((frame_de(e["unit_id"]), e["state"]))

    condiciones = sorted({c for c, _ in por_subj})
    out = {}
    for cond in condiciones:
        pistas = []
        for (c, _s), cambios in por_subj.items():
            if c != cond:
                continue
            cambios.sort()
            estados, actual, i = [], "inactive", 0
            resolved_desde = None
            for f in range(n_frames):
                while i < len(cambios) and cambios[i][0] <= f:
                    actual = cambios[i][1]
                    resolved_desde = f if actual == "resolved" else None
                    i += 1
                if (actual == "resolved" and resolved_desde is not None
                        and f - resolved_desde >= RESOLVED_HOLD):
                    actual = "inactive"
                estados.append(actual)
            pistas.append(estados)
        out[cond] = [max((p[f] for p in pistas), key=lambda s: ORDEN_ESTADO[s])
                     if pistas else "inactive" for f in range(n_frames)]
    return out


def _selfcheck():
    evs = [
        {"event_type": "pattern_state_changed", "condition_id": "CR-01",
         "subject_key": "k1", "unit_id": "frame_000010", "state": "candidate"},
        {"event_type": "pattern_state_changed", "condition_id": "CR-01",
         "subject_key": "k1", "unit_id": "frame_000020", "state": "confirmed"},
        {"event_type": "pattern_state_changed", "condition_id": "CR-01",
         "subject_key": "k1", "unit_id": "frame_000030", "state": "resolved"},
        {"event_type": "pattern_state_changed", "condition_id": "CR-01",
         "subject_key": "k2", "unit_id": "frame_000025", "state": "candidate"},
    ]
    tl = construir_timeline(evs, 100)["CR-01"]
    assert tl[5] == "inactive" and tl[10] == "candidate" and tl[19] == "candidate"
    assert tl[20] == "confirmed" and tl[29] == "confirmed"
    # a f=30 k1 resuelve pero k2 sigue candidate => gana candidate (más avanzado)
    assert tl[30] == "candidate" and tl[99] == "candidate"
    # sin k2: resolved sostiene 45 frames y decae
    tl1 = construir_timeline(evs[:3], 100)["CR-01"]
    assert tl1[30] == "resolved" and tl1[74] == "resolved" and tl1[80] == "inactive"
    print("selfcheck OK (timeline)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--video")
    ap.add_argument("--detections")
    ap.add_argument("--control-run")
    ap.add_argument("--out")
    ap.add_argument("--title", default="")
    ap.add_argument("--subtitle", default="")
    ap.add_argument("--color-by-track", action="store_true")
    ap.add_argument("--highlight-class", default=None)
    ap.add_argument("--min-conf", type=float, default=0.25)
    ap.add_argument("--fps-video", type=float, default=30.0)
    a = ap.parse_args()
    if a.selfcheck:
        return _selfcheck()
    for req in ("video", "detections", "out"):
        if not getattr(a, req):
            ap.error(f"--{req} es obligatorio (o usar --selfcheck)")

    import cv2  # import tardío: --selfcheck no lo necesita

    dets_por_frame = {}
    for e in leer_jsonl(a.detections):
        dets_por_frame[e["source"]["frame_index"]] = e.get("detections") or []

    pattern_events, alertas = [], []
    if a.control_run:
        cr = Path(a.control_run)
        if (cr / "pattern_events.jsonl").exists():
            pattern_events = leer_jsonl(cr / "pattern_events.jsonl")
        if (cr / "alerts.jsonl").exists():
            alertas = leer_jsonl(cr / "alerts.jsonl")

    cap = cv2.VideoCapture(a.video)
    n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or a.fps_video

    timeline = construir_timeline(pattern_events, n_frames) if pattern_events else {}
    alert_frames = sorted((al.get("frame_index") or 0, al) for al in alertas)
    primera_ev = min((frame_de(al["first_evidence_unit_id"]) for al in alertas
                      if al.get("first_evidence_unit_id")), default=None)

    tmp = Path(a.out).with_suffix(".raw.mp4")
    vw = cv2.VideoWriter(str(tmp), cv2.VideoWriter_fourcc(*"mp4v"), fps, (W, H))
    track_col: dict = {}

    def color_track(tid):
        if tid not in track_col:
            track_col[tid] = COL_TRACK[len(track_col) % len(COL_TRACK)]
        return track_col[tid]

    f = 0
    while True:
        ok, img = cap.read()
        if not ok:
            break
        # --- cajas ---
        for d in dets_por_frame.get(f, []):
            if d["confidence"] < a.min_conf:
                continue
            x1, y1, x2, y2 = (int(v) for v in d["bbox_xyxy"])
            lbl = d["label"]
            hl = a.highlight_class and lbl == a.highlight_class
            if hl:
                col, th = COL_HIGHLIGHT, 5
            elif a.color_by_track and lbl == "person" and d.get("track_id"):
                col, th = color_track(d["track_id"]), 4
            else:
                col, th = COL_CLASS.get(lbl, (180, 180, 180)), 2 if lbl != "person" else 3
            cv2.rectangle(img, (x1, y1), (x2, y2), col, th)
            texto = f"{lbl} {d['confidence']:.2f}"
            # En modo track, la identidad va ABAJO de la caja de persona: arriba
            # chocaría con las etiquetas de helmet/vest, que viven en el torso/cabeza.
            abajo = a.color_by_track and lbl == "person" and d.get("track_id")
            if abajo:
                texto = f"{d['track_id']} · {texto}"
            (tw, thh), _ = cv2.getTextSize(texto, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
            ty = min(y2 + thh + 12, H - 4) if abajo else y1
            cv2.rectangle(img, (x1, ty - thh - 10), (x1 + tw + 8, ty), col, -1)
            cv2.putText(img, texto, (x1 + 4, ty - 6), cv2.FONT_HERSHEY_SIMPLEX,
                        0.7, (0, 0, 0), 2, cv2.LINE_AA)

        # --- banner superior: título + estado por condición ---
        band = img.copy()
        cv2.rectangle(band, (0, 0), (W, 78), (20, 20, 20), -1)
        cv2.addWeighted(band, 0.65, img, 0.35, 0, img)
        cv2.putText(img, a.title, (16, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.95,
                    (255, 255, 255), 2, cv2.LINE_AA)
        if a.subtitle:
            cv2.putText(img, a.subtitle, (16, 64), cv2.FONT_HERSHEY_SIMPLEX, 0.62,
                        (200, 200, 200), 1, cv2.LINE_AA)
        x = W - 16
        for cond in sorted(timeline, reverse=True):
            st = timeline[cond][min(f, n_frames - 1)]
            texto = f"{cond}: {st.upper()}"
            (tw, _), _ = cv2.getTextSize(texto, cv2.FONT_HERSHEY_SIMPLEX, 0.85, 2)
            x -= tw + 30
            cv2.putText(img, texto, (x, 46), cv2.FONT_HERSHEY_SIMPLEX, 0.85,
                        COL_STATE[st], 2, cv2.LINE_AA)

        # --- línea de tiempo inferior ---
        y0, y1b = H - 56, H - 22
        cv2.rectangle(img, (0, y0 - 26), (W, H), (20, 20, 20), -1)
        for cond_i, cond in enumerate(sorted(timeline)):
            yy0 = y0 + cond_i * 18
            paso = max(1, n_frames // W)
            for px in range(W):
                fr = min(n_frames - 1, px * n_frames // W)
                cv2.line(img, (px, yy0), (px, min(yy0 + 14, H - 6)),
                         COL_STATE[timeline[cond][fr]], 1)
        if primera_ev is not None:
            px = primera_ev * W // n_frames
            cv2.line(img, (px, y0 - 22), (px, H - 6), (255, 255, 255), 1)
            cv2.putText(img, "1a evidencia", (px + 6, y0 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
        for af, al in alert_frames:
            px = af * W // n_frames
            cv2.line(img, (px, y0 - 22), (px, H - 6), (60, 60, 230), 2)
            cv2.putText(img, "ALERTA", (px + 6, H - 10), cv2.FONT_HERSHEY_SIMPLEX,
                        0.55, (60, 60, 230), 2, cv2.LINE_AA)
        pxc = f * W // max(1, n_frames)
        cv2.line(img, (pxc, y0 - 26), (pxc, H), (255, 255, 255), 2)
        cv2.putText(img, f"t = {f / fps:5.1f} s", (16, H - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (220, 220, 220), 1, cv2.LINE_AA)

        # --- panel de alerta: arriba a la IZQUIERDA (pared vacía en el encuadre
        # del rodaje; a la derecha pisaba las cajas), fondo sólido SIEMPRE (con
        # borde solo, el texto quedaba ilegible sobre la escena tras el pulso) ---
        vivos = [(af, al) for af, al in alert_frames if f >= af]
        for idx, (af, al) in enumerate(vivos):
            edad = (f - af) / fps
            pulso = edad < 2.0 and int(edad * 4) % 2 == 0
            bg = (60, 60, 230) if pulso else (25, 25, 25)
            box_y = 92 + 78 * idx
            cv2.rectangle(img, (16, box_y), (600, box_y + 66), bg, -1)
            cv2.rectangle(img, (16, box_y), (600, box_y + 66), (60, 60, 230), 3)
            fg = (255, 255, 255) if pulso else (90, 90, 245)
            cv2.putText(img, f"ALERTA {al.get('condition_id')} ({al.get('severity')})"
                             f"  t={af / fps:.1f} s",
                        (30, box_y + 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, fg, 2,
                        cv2.LINE_AA)
            cv2.putText(img, str(al.get("subject_key")), (30, box_y + 56),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.62, (230, 230, 230), 1,
                        cv2.LINE_AA)
        vw.write(img)
        f += 1

    cap.release()
    vw.release()
    # H.264 para que cualquier proyector/notebook lo reproduzca
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp),
                    "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p",
                    str(a.out)], check=True)
    tmp.unlink()
    print(f"-> {a.out}  ({f} frames)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
