"""Montaje lado a lado ESCENA | SUJETO sobre el MISMO clip y el MISMO instante.

Es la evidencia visual de F-89.1 y del argumento central de la tesis: las
detecciones de los dos lados son **bit a bit las mismas** (G1 reusa las
detecciones de T1, doc 89), así que toda la diferencia que se ve en pantalla la
produce el motor, no el modelo. En `a_p7_c01` el vuelco es completo:

    escena (T1)  -> 0 detectadas, 1 NO detectada, 1 falsa alarma
    sujeto (G1)  -> 1 detectada,  0 NO detectadas, 0 falsas alarmas

Salida 1920x1080 (proyector): dos paneles sincronizados frame a frame, con banda
superior de título, etiqueta por panel y banda inferior con el veredicto medido.

Uso:
  <venv-media-plane>/bin/python montaje_lado_a_lado.py \
      --clip a_p7_c01 \
      --izq-control <dir replay escena> --der-control <dir replay sujeto> \
      --izq-detections <detections.jsonl> --der-detections <tracked.jsonl> \
      --out videos/VG1_lado_a_lado.mp4
"""

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from overlay_render import (COL_CLASS, COL_STATE, COL_TRACK,  # noqa: E402
                            construir_timeline, frame_de, leer_jsonl)

W_OUT, H_OUT = 1920, 1080
PW, PH = 944, 531           # panel: 1920x1080 escalado ~0,4917
GAP = 32
X_IZQ, X_DER = 0, PW + GAP
Y_PANEL = 150
Y_PIE = Y_PANEL + PH + 18
F = None                    # cv2.FONT_HERSHEY_SIMPLEX, se setea en main


def cargar_lado(detections, control_run, n_frames):
    dets = {}
    for e in leer_jsonl(detections):
        dets[e["source"]["frame_index"]] = e.get("detections") or []
    cr = Path(control_run)
    pe = leer_jsonl(cr / "pattern_events.jsonl") if (cr / "pattern_events.jsonl").exists() else []
    al = leer_jsonl(cr / "alerts.jsonl") if (cr / "alerts.jsonl").exists() else []
    return {"dets": dets, "timeline": construir_timeline(pe, n_frames),
            "alertas": sorted((a.get("frame_index") or 0, a) for a in al)}


def dibujar_panel(cv2, img, lado, f, color_por_track, track_col, min_conf):
    """Devuelve el panel ya escalado a (PW, PH) con cajas dibujadas."""
    p = img.copy()
    for d in lado["dets"].get(f, []):
        if d["confidence"] < min_conf:
            continue
        x1, y1, x2, y2 = (int(v) for v in d["bbox_xyxy"])
        lbl = d["label"]
        if color_por_track and lbl == "person" and d.get("track_id"):
            tid = d["track_id"]
            if tid not in track_col:
                track_col[tid] = COL_TRACK[len(track_col) % len(COL_TRACK)]
            col, th = track_col[tid], 6
            etiqueta = str(tid)
        else:
            col = COL_CLASS.get(lbl, (180, 180, 180))
            th = 5 if lbl == "person" else 3
            etiqueta = lbl if lbl != "person" else "person"
        cv2.rectangle(p, (x1, y1), (x2, y2), col, th)
        if lbl == "person":
            # Arriba de la caja: en el montaje no se rotulan helmet/vest, así que
            # no hay colisión, y pegado al borde inferior del panel se cortaba.
            (tw, thh), _ = cv2.getTextSize(etiqueta, F, 1.5, 3)
            yy = max(y1 - 8, thh + 14)
            cv2.rectangle(p, (x1, yy - thh - 12), (x1 + tw + 14, yy), col, -1)
            cv2.putText(p, etiqueta, (x1 + 7, yy - 8), F, 1.5, (0, 0, 0), 3,
                        cv2.LINE_AA)
    return cv2.resize(p, (PW, PH), interpolation=cv2.INTER_AREA)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clip", required=True)
    ap.add_argument("--video", required=True)
    ap.add_argument("--izq-detections", required=True)
    ap.add_argument("--der-detections", required=True)
    ap.add_argument("--izq-control", required=True)
    ap.add_argument("--der-control", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--min-conf", type=float, default=0.25)
    ap.add_argument("--izq-alerta-nota", default="FALSA ALARMA")
    ap.add_argument("--der-alerta-nota", default="CORRECTA")
    ap.add_argument("--mecanismo", default=(
        "Mecanismo (F-89.1): bajo ESCENA basta que CUALQUIER persona este sin casco. "
        "La alerta de la izquierda dispara temprano por el otro sujeto,|"
        "mientras el sujeto objetivo todavia cumplia; y el episodio real queda sin "
        "detectar. No era que el modelo no viera el casco: el motor miraba a otra "
        "persona."))
    a = ap.parse_args()

    import cv2
    global F
    F = cv2.FONT_HERSHEY_SIMPLEX

    cap = cv2.VideoCapture(a.video)
    n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    izq = cargar_lado(a.izq_detections, a.izq_control, n_frames)
    der = cargar_lado(a.der_detections, a.der_control, n_frames)

    tmp = Path(a.out).with_suffix(".raw.mp4")
    vw = cv2.VideoWriter(str(tmp), cv2.VideoWriter_fourcc(*"mp4v"), fps,
                         (W_OUT, H_OUT))
    track_col = {}
    f = 0
    while True:
        ok, img = cap.read()
        if not ok:
            break
        lienzo = cv2.copyMakeBorder(
            cv2.resize(img, (2, 2)), 0, 0, 0, 0, cv2.BORDER_CONSTANT)  # placeholder
        lienzo = 0 * cv2.resize(lienzo, (W_OUT, H_OUT))                # negro
        lienzo[Y_PANEL:Y_PANEL + PH, X_IZQ:X_IZQ + PW] = dibujar_panel(
            cv2, img, izq, f, False, {}, a.min_conf)
        lienzo[Y_PANEL:Y_PANEL + PH, X_DER:X_DER + PW] = dibujar_panel(
            cv2, img, der, f, True, track_col, a.min_conf)

        # --- banda superior ---
        cv2.putText(lienzo, "Las mismas detecciones, bit a bit. La unica variable "
                            "es el motor.", (24, 46), F, 1.0, (255, 255, 255), 2,
                    cv2.LINE_AA)
        cv2.putText(lienzo, f"clip {a.clip} (escenario P7: multitud)   ·   "
                            f"t = {f / fps:5.1f} s", (24, 82), F, 0.7,
                    (170, 170, 170), 1, cv2.LINE_AA)
        for x, txt, sub in (
                (X_IZQ, "GRANULARIDAD DE ESCENA  (T1)", "\"alguien sin casco\""),
                (X_DER, "GRANULARIDAD POR SUJETO  (G1)", "\"QUIEN esta sin casco\"")):
            cv2.putText(lienzo, txt, (x + 16, 126), F, 0.85, (255, 255, 255), 2,
                        cv2.LINE_AA)
            (tw, _), _ = cv2.getTextSize(txt, F, 0.85, 2)
            cv2.putText(lienzo, sub, (x + 32 + tw, 126), F, 0.72, (150, 150, 150),
                        1, cv2.LINE_AA)

        # --- estado + alerta por panel, CON su veredicto contra el GT ---
        # Sin la nota, los dos lados muestran un cartel "ALERTA" y el jurado no
        # puede saber que la de la izquierda es la FALSA. El veredicto sale del
        # eval de la campaña (T1: 0 matched/1 missed/1 FP; G1: 1/0/0).
        for x, lado, nota, col_nota in (
                (X_IZQ, izq, a.izq_alerta_nota, (90, 90, 245)),
                (X_DER, der, a.der_alerta_nota, (120, 220, 120))):
            st = (lado["timeline"].get("CR-01") or ["inactive"] * n_frames)[
                min(f, n_frames - 1)]
            cv2.putText(lienzo, f"CR-01: {st.upper()}", (x + PW - 330, Y_PIE + 34),
                        F, 0.9, COL_STATE[st], 2, cv2.LINE_AA)
            vivas = [(af, al) for af, al in lado["alertas"] if f >= af]
            for i, (af, al) in enumerate(vivas):
                pulso = (f - af) / fps < 2.0 and int((f - af) / fps * 4) % 2 == 0
                y = Y_PIE + 62 + 58 * i
                cv2.rectangle(lienzo, (x + 16, y), (x + 700, y + 48),
                              col_nota if pulso else (25, 25, 25), -1)
                cv2.rectangle(lienzo, (x + 16, y), (x + 700, y + 48), col_nota, 2)
                fg = (0, 0, 0) if pulso else col_nota
                cv2.putText(lienzo, f"ALERTA t={af / fps:.1f} s  ->  {nota}",
                            (x + 28, y + 32), F, 0.72, fg, 2, cv2.LINE_AA)
                clave = str(al.get("subject_key"))
                (tw, _), _ = cv2.getTextSize(clave, F, 0.5, 1)
                cv2.putText(lienzo, clave, (x + 692 - tw, y + 32), F, 0.5,
                            (0, 0, 0) if pulso else (170, 170, 170), 1, cv2.LINE_AA)

        # --- mecanismo (F-89.1) ---
        for i, linea in enumerate(a.mecanismo.split("|")):
            cv2.putText(lienzo, linea.strip(), (24, H_OUT - 128 + 34 * i), F, 0.78,
                        (215, 215, 215), 2, cv2.LINE_AA)

        # --- veredicto medido (fijo, es el dato del banco) ---
        for x, linea, col in (
                (X_IZQ, "resultado medido:  0 detectadas   1 NO detectada   "
                        "1 falsa alarma", (90, 90, 245)),
                (X_DER, "resultado medido:  1 detectada    0 NO detectadas  "
                        "0 falsas alarmas", (120, 220, 120))):
            cv2.putText(lienzo, linea, (x + 16, H_OUT - 24), F, 0.72, col, 2,
                        cv2.LINE_AA)
        vw.write(lienzo)
        f += 1

    cap.release()
    vw.release()
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp),
                    "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p",
                    str(a.out)], check=True)
    tmp.unlink()
    print(f"-> {a.out}  ({f} frames)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
