#!/usr/bin/env python3
"""Driver offline del media-plane para los brazos de la jornada E-04 (DBE, single-host).

Carga una run config YAML con el loader real del plano (`load_run_config`: model.ref
contra el catálogo del media-plane, prompts.ref contra `prompts/` de este repo) y la
ejecuta con `run_pipeline` (crea el adapter, corre, cierra). Es el mismo camino
in-process con que se produjeron los brazos baseline/tuned de T1 y el brazo base de
retención OV: acá queda como comando reproducible.

Uso (con el venv del media-plane, que tiene torch+GPU):

    ../e-ovrt_media-plane/.venv/bin/python finetuning/scripts/run_offline_media_plane.py \
        --config finetuning/runs/<arm>_run_config.yaml
"""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args()

    from eovrt_media.config.loader import load_run_config
    from eovrt_media.runtime.pipeline import run_pipeline

    config = load_run_config(args.config.resolve())
    run_id = run_pipeline(config)
    print(f"run_id={run_id}")
    print(f"base_dir={config.outputs.base_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
