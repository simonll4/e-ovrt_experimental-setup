"""Arma los videos de la defensa (D-90.7): prepara insumos y llama al renderer.

Por video: toma las detecciones REALES de la campaña T1 (30 fps, provenance del
banco), re-corre el replay del control-plane para obtener pattern_events/alerts
frescos (determinístico — verificado que reproduce T1 campo a campo,
`datos/96-verificar-comparabilidad-t1.py`), y compone con `overlay_render.py`.

  V1     a_p1_c02  escena   la cadena completa: candidate -> confirmed -> alerta
  V3     a_p3_c01  escena   el silencio correcto: la oclusion breve NO alerta
  V-G1   a_p7_c01  sujeto   multitud + color por track: T1 0/1/1 -> G1 1/0/0
  V-G1e  a_p7_c01  escena   la contraparte para el lado-a-lado del deck

V2 (gloves) se arma aparte: necesita una corrida nueva del media-plane con la
clase agregada (unica pieza con GPU), ver README.

Uso: python3 armar_videos.py [--solo V1,V3,VG1,VG1e]
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).parent
DS = Path("/home/simonll4/projects/e-ovrt_datasets")
MP = Path("/home/simonll4/projects/e-ovrt_media-plane")
CP = Path("/home/simonll4/projects/e-ovrt_control-plane")
RES = Path("/home/simonll4/projects/e-ovrt_experimental-setup/results/clip_bench")
T1_PROV = RES / "t1_gdinotiny560_v2short_scene/provenance.json"
RENDER_PY = MP / ".venv/bin/python"   # el venv con cv2

sys.path.insert(0, str(CP / "src"))
from eovrt_control.tools.track_detections import track_event_stream  # noqa: E402

VIDEOS = {
    "V1": {
        # a_p1_c04: 30,7 s, 1 alerta observada y 0 re_alerts (a_p1_c02 tiene una
        # re-emision ADR-011 que en el video central invitaria preguntas evitables)
        "clip": "a_p1_c04", "gran": "scene",
        "title": "V1 - la cadena completa: deteccion no es alerta",
        "subtitle": "gdino-tiny-560 + cr01_cr02_v2_short + patron CR-01 (4 s) - combinacion T1 del banco (F1 0,789)",
        "track": False,
    },
    "V3": {
        "clip": "a_p3_c01", "gran": "scene",
        "title": "V3 - lo que NO alerta: la persistencia filtra el transitorio",
        "subtitle": "misma combinacion T1 - el episodio queda candidate y resuelve sin alerta (verificado 2/2 en vivo, doc 71)",
        "track": False,
    },
    "VG1": {
        "clip": "a_p7_c01", "gran": "subject",
        "title": "V-G1 - identidad por sujeto en multitud (G1, F1 0,930)",
        "subtitle": "mismas detecciones bit a bit que T1; unica variable: granularidad por track_id (P7: 0,400 -> 1,000)",
        "track": True,
    },
    "VG1e": {
        "clip": "a_p7_c01", "gran": "scene",
        "title": "V-G1 (contraparte escena) - el motor mira a otra persona",
        "subtitle": "granularidad de escena sobre el mismo clip: 1 missed + 1 FP (F-89.1)",
        "track": False,
    },
}


def replay(clip_id, det_path, gran, out_dir):
    patterns = CP / "configs/patterns" / (
        "cr01_cr02_v2_subject.yaml" if gran == "subject" else "cr01_cr02_v2.yaml")
    cfg = out_dir / f"replay_{clip_id}_{gran}.yaml"
    cfg.write_text(
        "run:\n  id: null\n  scenario: DBE\n"
        f"  name: defensa_{clip_id}_{gran}\n"
        f'  description: "Insumo de video de defensa (D-90.7) - {clip_id}, {gran}."\n'
        f"input:\n  type: media_jsonl\n  path: {det_path}\n"
        f"patterns:\n  file: {patterns}\n  active_ids:\n    - CR-01\n    - CR-02\n"
        f"outputs:\n  base_dir: {out_dir / 'control_runs'}\n"
        "  save_pattern_events_jsonl: true\n  save_alerts_jsonl: true\n"
        "  save_metrics_jsonl: true\n  save_errors_jsonl: true\n  save_summary_json: true\n"
        "logging:\n  level: WARNING\n")
    before = {p.name for p in (out_dir / "control_runs").glob("*") if p.is_dir()}
    r = subprocess.run([str(CP / ".venv/bin/eovrt-control"), "replay", str(cfg)],
                       capture_output=True, text=True, cwd=str(CP))
    if r.returncode != 0:
        raise RuntimeError(f"replay {clip_id}: {(r.stderr or r.stdout)[-300:]}")
    nuevos = [p for p in (out_dir / "control_runs").glob("*")
              if p.is_dir() and p.name not in before]
    if len(nuevos) != 1:
        raise RuntimeError(f"replay {clip_id}: {len(nuevos)} dirs nuevos")
    return nuevos[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--solo", default="")
    a = ap.parse_args()
    pedidos = [s.strip() for s in a.solo.split(",") if s.strip()] or list(VIDEOS)

    t1 = {r["clip_id"]: r["media_run_id"] for r in json.loads(T1_PROV.read_text())}
    work = AQUI / "trabajo"
    (work / "control_runs").mkdir(parents=True, exist_ok=True)
    (AQUI / "videos").mkdir(exist_ok=True)

    for vid in pedidos:
        spec = VIDEOS[vid]
        cid = spec["clip"]
        det = MP / "runs" / t1[cid] / "detections.jsonl"
        print(f"[{vid}] {cid} ({spec['gran']})", flush=True)

        if spec["track"]:
            tracked = work / f"{cid}.tracked.jsonl"
            stats = track_event_stream(det, tracked)
            print(f"   tracking: {stats['tracks']} tracks / "
                  f"{stats['person_detections']} personas", flush=True)
            det_render = det_replay = tracked
        else:
            det_render = det_replay = det

        crun = replay(cid, det_replay, spec["gran"], work)
        n_al = len([1 for x in (crun / "alerts.jsonl").read_text().splitlines()
                    if x.strip()]) if (crun / "alerts.jsonl").exists() else 0
        print(f"   replay: {crun.name} ({n_al} alertas)", flush=True)

        out = AQUI / "videos" / f"{vid}_{cid}.mp4"
        cmd = [str(RENDER_PY), str(AQUI / "overlay_render.py"),
               "--video", str(DS / "datasets-videos/clips" / f"{cid}.mp4"),
               "--detections", str(det_render),
               "--control-run", str(crun),
               "--out", str(out),
               "--title", spec["title"], "--subtitle", spec["subtitle"]]
        if spec["track"]:
            cmd.append("--color-by-track")
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            print(f"   RENDER FALLO: {(r.stderr or r.stdout)[-400:]}")
            return 1
        print(f"   {r.stdout.strip()}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
