"""Insumos compartidos por los tests de la demo: un workspace sintético con las
plantillas, lo congelado, los prompt sets, los pattern sets y el catálogo del modelo REALES
(los del campeón y los de los modos de `modos.yaml`)."""
from __future__ import annotations

import shutil
from pathlib import Path

REPO_REAL = Path(__file__).resolve().parents[3]
WORKSPACE_REAL = REPO_REAL.parent
MODELO_OK = {"ref": "grounding-dino/gdino-tiny-560", "thresholds": {"box": 0.3, "text": 0.25}}
PROMPT_SETS = ("cr01_cr02_v2_short.yaml", "eind_v1.yaml", "edir_v1.yaml", "clase_nueva_v1.yaml")
PATTERN_SETS = ("cr01_cr02_v2.yaml", "cr01_cr02_edir_v1.yaml")


def repo_demo(tmp_path: Path) -> Path:
    ws = tmp_path / "ws"
    repo = ws / "e-ovrt_experimental-setup"
    for carpeta in ("demo_defensa", "demo_defensa_ensayo"):
        shutil.copytree(REPO_REAL / "experiments" / carpeta, repo / "experiments" / carpeta)
    (repo / "prompts").mkdir(parents=True)
    for archivo in PROMPT_SETS:
        shutil.copy2(REPO_REAL / "prompts" / archivo, repo / "prompts")
    patrones = ws / "e-ovrt_control-plane" / "configs" / "patterns"
    patrones.mkdir(parents=True)
    for archivo in PATTERN_SETS:
        shutil.copy2(WORKSPACE_REAL / "e-ovrt_control-plane/configs/patterns" / archivo, patrones)
    modelos = ws / "e-ovrt_media-plane" / "configs" / "models" / "grounding-dino"
    modelos.mkdir(parents=True)
    shutil.copy2(
        WORKSPACE_REAL / "e-ovrt_media-plane/configs/models/grounding-dino/gdino-tiny-560.yaml", modelos
    )
    return repo
