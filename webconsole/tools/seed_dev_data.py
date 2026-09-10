"""Genera corridas de prueba para desarrollar la consola sin hardware.

DESCARTABLE. Esto no es parte del producto: existe para que las pantallas
Corridas / Detalle / Traza tengan algo detrás en una máquina de desarrollo, donde
`e-ovrt_media-plane/runs/` arranca vacío y no hay cámara conectada.

Cómo funciona
-------------
El media-plane trae un detector `mock` (``configs/models/mock.yaml``) con RNG
sembrado que no necesita GPU, pesos ni CUDA. Levantando el servicio con
``EOVRT_MODEL_REF=mock`` se puede correr el pipeline completo sobre archivos de
video locales. Este script solo dispara corridas por HTTP contra el BFF y, si se
le pasa ``--control-python``, encadena el replay del motor de reglas sobre las
detecciones de cada corrida para que la traza quede correlacionada (que es lo que
alimenta la línea de tiempo: entregado / descartado / alertas).

Usa únicamente la biblioteca estándar: corre con cualquier intérprete.

Uso
---
    python seed_dev_data.py --videos-dir <dir con .mp4>
    python seed_dev_data.py --videos-dir <dir> --control-python <ruta a python con eovrt_control>
    python seed_dev_data.py --purge        # borra lo que este script creó

Todo lo que crea lleva el nombre marcado con SEED_TAG, así que ``--purge`` no
puede tocar corridas de verdad.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

# Marca en el nombre de la corrida. `--purge` borra exactamente las que la llevan;
# sin esto no habría forma de distinguir datos de prueba de corridas reales.
SEED_TAG = "[seed]"

# Registro de lo creado, para que `--purge` sea exacto y no tenga que adivinar.
REGISTRO = Path(__file__).with_name(".seed_runs.json")

# La consola de Windows abre stdout en cp1252, que no puede codificar «·» ni «→».
# Sin esto el script muere con UnicodeEncodeError al imprimir el progreso, después
# de haber lanzado las corridas — lo peor de los dos mundos.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DEFAULT_BFF = "http://127.0.0.1:8090"
DEFAULT_PROMPT_SET = "cr01_cr02_v2_short"
DEFAULT_CLASSES = ["person", "helmet", "vest"]

# Formas distintas a propósito: el listado tiene filtros por estado, orden por
# columna y estados vacíos, y con corridas todas iguales no se ve si funcionan.
# `video` es un índice dentro de los .mp4 encontrados; se cicla si hay menos.
PERFILES = [
    {"nombre": "Recorte diurno — obra 01", "video": 0, "stride": 5, "max_units": 60, "anotado": True},
    {"nombre": None, "video": 1, "stride": 10, "max_units": 40, "anotado": False},
    {"nombre": "Perímetro — turno tarde", "video": 2, "stride": 2, "max_units": 120, "anotado": True},
    {"nombre": "Barrido largo — patio norte", "video": 3, "stride": 1, "max_units": 200, "anotado": False},
    {"nombre": "Prueba de umbrales (falla esperada)", "video": None, "stride": 1, "max_units": 10, "anotado": False},
]


def pedir(url: str, metodo: str = "GET", cuerpo: dict | None = None, timeout: int = 60) -> tuple[int, object]:
    """Devuelve (status, payload). No levanta excepción en 4xx/5xx: varias de las
    corridas de prueba fallan a propósito y el error es el dato que interesa."""
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    req = urllib.request.Request(
        url, data=datos, method=metodo, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            crudo = r.read().decode() or "null"
            return r.status, json.loads(crudo)
    except urllib.error.HTTPError as e:
        crudo = e.read().decode() or "null"
        try:
            return e.code, json.loads(crudo)
        except json.JSONDecodeError:
            return e.code, crudo
    except urllib.error.URLError as e:
        raise SystemExit(
            f"No se pudo hablar con el BFF en {url}: {e.reason}\n"
            "¿Están levantados los tres servicios? Ver el README de webconsole/."
        ) from e


def esperar_fin(bff: str, run_id: str, limite_s: int = 180) -> str:
    """Bloquea hasta que la corrida sale de `running`. Las corridas mock terminan
    en menos de un segundo, pero un video largo con stride 1 puede tardar.

    Un estado que no se puede leer corta enseguida en vez de reintentar hasta el
    límite: si el servicio contesta 5xx, esperar tres minutos no lo va a arreglar
    y esconde el error real detrás de un «timeout» que no explica nada.
    """
    limite = time.monotonic() + limite_s
    while time.monotonic() < limite:
        status, d = pedir(f"{bff}/api/runs/{run_id}")
        if status >= 500:
            return f"error del servicio ({status}: {d})"
        if not isinstance(d, dict):
            return f"respuesta inesperada: {d!r}"
        estado = d.get("status")
        if estado and estado != "running":
            return estado
        time.sleep(1.0)
    return f"sigue corriendo después de {limite_s}s"


def lanzar(bff: str, perfil: dict, videos: list[Path], prompt_set: str) -> str | None:
    idx = perfil["video"]
    if idx is None:
        # Falla a propósito: ruta inexistente. El listado necesita al menos una
        # corrida fallida para que el filtro "Fallidas" y el estado vacío del
        # detalle tengan algo que mostrar.
        ruta = "C:/ruta/que/no/existe/video_faltante.mp4"
    else:
        ruta = videos[idx % len(videos)].as_posix()

    base = perfil["nombre"] or "sin nombre"
    nombre = None if perfil["nombre"] is None else f"{perfil['nombre']} {SEED_TAG}"
    composicion = {
        "ingest": {"plugin": "video_file", "config": {"path": ruta}},
        "prompts": {"set_id": prompt_set, "active_ids": list(DEFAULT_CLASSES)},
        "run": {
            "name": nombre,
            "stride": perfil["stride"],
            "max_units": perfil["max_units"],
            "save_annotated_video": perfil["anotado"],
            "save_previews": True,
        },
    }
    status, payload = pedir(f"{bff}/api/runs", "POST", composicion)
    if status != 201:
        print(f"  ! no se pudo lanzar «{base}»: {status} {payload}")
        return None
    run_id = payload["run_id"]
    final = esperar_fin(bff, run_id)
    print(f"  · {run_id}  ({base}) → {final}")
    return run_id


def replay_control(control_python: Path, control_repo: Path, media_runs: Path, run_id: str) -> None:
    """Corre el motor de reglas sobre las detecciones de una corrida ya terminada.

    Sin esto la traza existe pero le falta la mitad de control: la columna de
    entrega queda en «sin dato» y no hay alertas ni progreso de condiciones. El
    BFF correlaciona por `media_run_id`, que el replay escribe en su summary.
    """
    detecciones = media_runs / run_id / "detections.jsonl"
    if not detecciones.is_file():
        print(f"  ! sin detections.jsonl para {run_id}, se omite el replay")
        return
    patrones = control_repo / "configs" / "patterns" / "cr01_cr02_v2.yaml"
    cfg = {
        "run": {"id": f"ctl_{run_id}", "scenario": "DBE", "name": f"replay_{run_id}"},
        "input": {"type": "media_jsonl", "path": detecciones.as_posix()},
        "patterns": {"file": patrones.as_posix(), "active_ids": ["CR-01", "CR-02"]},
        "outputs": {
            "base_dir": (control_repo / "runs").as_posix(),
            "save_pattern_events_jsonl": True,
            "save_alerts_jsonl": True,
            "save_metrics_jsonl": True,
            "save_errors_jsonl": True,
            "save_summary_json": True,
        },
        "logging": {"level": "WARNING"},
    }
    # El CLI toma YAML, pero YAML es un superconjunto de JSON: esto evita
    # depender de pyyaml en el intérprete que corre este script.
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as fh:
        json.dump(cfg, fh)
        ruta_cfg = fh.name
    try:
        r = subprocess.run(
            [str(control_python), "-m", "eovrt_control.cli", "replay", ruta_cfg],
            cwd=control_repo, capture_output=True, text=True, timeout=300,
        )
        if r.returncode != 0:
            print(f"  ! replay falló para {run_id}: {(r.stderr or r.stdout).strip()[:300]}")
        else:
            alertas = re.search(r"Alertas:\s*(\d+)", r.stdout or "")
            print(f"  · ctl_{run_id} → {alertas.group(1) if alertas else '?'} alertas")
    finally:
        Path(ruta_cfg).unlink(missing_ok=True)


def purgar(bff: str, media_runs: Path, control_repo: Path) -> None:
    # Se borra por el registro exacto de lo que este script creó. La marca en el
    # nombre sola no alcanza: uno de los perfiles crea una corrida SIN nombre a
    # propósito (el listado necesita mostrar el caso "sin nombre" con el id y la
    # antigüedad), y esa no se puede reconocer por el nombre.
    registro = REGISTRO
    ids: list[str] = []
    if registro.is_file():
        try:
            ids = json.loads(registro.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            ids = []

    status, filas = pedir(f"{bff}/api/runs")
    if status == 200 and isinstance(filas, list):
        # Red de seguridad para corridas de una ejecución previa cuyo registro se
        # perdió: solo las que llevan la marca, nunca una corrida real.
        ids += [
            f["run_id"] for f in filas
            if isinstance(f, dict) and SEED_TAG in (f.get("name") or "") and f["run_id"] not in ids
        ]

    if not ids:
        print("No hay corridas del seed registradas. Nada que borrar.")
        return

    for run_id in ids:
        status, _ = pedir(f"{bff}/api/runs/{run_id}", "DELETE")
        print(f"  · {run_id} → {status}")
        ctl = control_repo / "runs" / f"ctl_{run_id}"
        if ctl.is_dir():
            for hijo in sorted(ctl.rglob("*"), reverse=True):
                hijo.unlink() if hijo.is_file() else hijo.rmdir()
            ctl.rmdir()
            print(f"    y su corrida de reglas ctl_{run_id}")
    registro.unlink(missing_ok=True)
    _ = media_runs  # el borrado del directorio del media-plane lo hace el propio servicio


def main() -> None:
    raiz = Path(__file__).resolve().parents[3]
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--bff", default=DEFAULT_BFF, help=f"URL del BFF (default {DEFAULT_BFF})")
    p.add_argument("--videos-dir", type=Path, help="Directorio con .mp4 para alimentar las corridas")
    p.add_argument("--prompt-set", default=DEFAULT_PROMPT_SET)
    p.add_argument("--control-python", type=Path, help="Intérprete con eovrt_control instalado; si se pasa, encadena el replay del motor de reglas")
    p.add_argument("--control-repo", type=Path, default=raiz / "e-ovrt_control-plane")
    p.add_argument("--media-runs", type=Path, default=raiz / "e-ovrt_media-plane" / "runs")
    p.add_argument("--purge", action="store_true", help="Borra las corridas que creó este script")
    a = p.parse_args()

    if a.purge:
        print(f"Borrando corridas marcadas con «{SEED_TAG}»…")
        purgar(a.bff, a.media_runs, a.control_repo)
        return

    status, pre = pedir(f"{a.bff}/api/preflight")
    if status != 200 or not isinstance(pre, dict) or not pre.get("ready"):
        motivos = "; ".join(pre.get("blockers", [])) if isinstance(pre, dict) else str(pre)
        raise SystemExit(f"La plataforma no está lista: {motivos or status}")

    if not a.videos_dir or not a.videos_dir.is_dir():
        raise SystemExit("Falta --videos-dir con archivos .mp4")
    videos = sorted(a.videos_dir.glob("*.mp4"))
    if not videos:
        raise SystemExit(f"No hay .mp4 en {a.videos_dir}")
    print(f"{len(videos)} videos disponibles; usando los primeros {min(4, len(videos))}\n")

    print("Lanzando corridas:")
    ids = [rid for perfil in PERFILES if (rid := lanzar(a.bff, perfil, videos, a.prompt_set))]
    previas = json.loads(REGISTRO.read_text(encoding="utf-8")) if REGISTRO.is_file() else []
    REGISTRO.write_text(json.dumps(previas + ids, indent=2), encoding="utf-8")

    if a.control_python:
        print("\nCorrelacionando con el motor de reglas:")
        for run_id in ids:
            replay_control(a.control_python, a.control_repo, a.media_runs, run_id)

    print(f"\nListo: {len(ids)} corridas. Para deshacer: python {Path(__file__).name} --purge")


if __name__ == "__main__":
    sys.exit(main())
