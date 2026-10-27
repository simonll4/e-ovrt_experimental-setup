"""Compara dos corridas del control-plane campo por campo (principio 1 de la demo).

Prueba de que lo agregado para la demo es SOLO observación: se relee el mismo
`detections.jsonl` antes y después del cambio y los artefactos tienen que coincidir.
Dos corridas nunca coinciden byte a byte en todo: el id de la corrida (y lo que se
deriva de él: `alert_id`, rutas de salida) y los relojes del proceso cambian siempre.
Por eso el criterio es de control: los campos que difieren antes/después tienen que
ser EXACTAMENTE los que difieren entre dos corridas del mismo código.

    python3 comparar_corridas_control.py ANTES DESPUES [--control OTRA_DEL_MISMO_CODIGO]

Sin `--control`, compara contra la lista de campos volátiles conocida (abajo). Solo
stdlib. Resultado del 2026-10-26 (episodes[] del control-plane, clip a_p1_c04 del banco,
escena y sujeto): 27 campos difieren antes/después, los mismos 27 que entre dos
corridas del mismo código; todo lo demás, idéntico.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

VOLATILES = {
    "alert_id", "alert_registered_ms", "control_run_id", "first_evidence_ms", "processing_ms",
    "ts_receive_ms", "avg_processing_ms", "finished_at", "started_at", "output_files",
    "processing_ms_percentiles", "ttfa_internal_ms_percentiles",
}


def _aplanar(obj, prefijo: str = "") -> dict:
    salida: dict = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            salida.update(_aplanar(v, f"{prefijo}.{k}" if prefijo else k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            salida.update(_aplanar(v, f"{prefijo}[{i}]"))
    else:
        salida[prefijo] = obj
    return salida


def _filas(path: Path) -> list | None:
    if path.suffix == ".jsonl":
        return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    if path.suffix == ".json":
        return [json.loads(path.read_text(encoding="utf-8"))]
    return None


def campos_distintos(a: Path, b: Path) -> tuple[set[str], list[str]]:
    distintos: set[str] = set()
    problemas: list[str] = []
    for archivo in sorted(p.name for p in a.iterdir() if p.is_file()):
        fa, fb = a / archivo, b / archivo
        if not fb.is_file():
            problemas.append(f"falta {archivo} en {b}")
            continue
        ra, rb = _filas(fa), _filas(fb)
        if ra is None:  # yaml, csv: se comparan crudos
            if fa.read_bytes() != fb.read_bytes() and archivo != "alerts.csv":
                problemas.append(f"{archivo} difiere byte a byte")
            continue
        if len(ra) != len(rb):
            problemas.append(f"{archivo}: {len(ra)} filas contra {len(rb)}")
            continue
        for x, y in zip(ra, rb):
            px, py = _aplanar(x), _aplanar(y)
            for clave in set(px) | set(py):
                if px.get(clave) != py.get(clave):
                    distintos.add(f"{archivo}:{clave.split('[')[0]}")
    return distintos, problemas


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("antes", type=Path)
    ap.add_argument("despues", type=Path)
    ap.add_argument("--control", type=Path, help="otra corrida del MISMO código que `despues`")
    args = ap.parse_args()
    distintos, problemas = campos_distintos(args.antes, args.despues)
    if args.control is not None:
        permitidos, _ = campos_distintos(args.despues, args.control)
    else:
        permitidos = {d for d in distintos if d.split(":", 1)[1].split(".")[0] in VOLATILES}
    inesperados = sorted(distintos - permitidos)
    print(f"campos distintos antes/después: {len(distintos)} · volátiles: {len(distintos & permitidos)}")
    for p in problemas:
        print(f"PROBLEMA: {p}")
    for c in inesperados:
        print(f"DIFIERE (no volátil): {c}")
    ok = not problemas and not inesperados
    print("IDÉNTICAS salvo lo volátil" if ok else "DISTINTAS")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
