"""Insumos compartidos por los tests de la demo: un workspace sintético con las
plantillas, lo congelado, los prompt sets, los pattern sets y el catálogo del modelo REALES
(los del campeón y los de los modos de `modos.yaml`)."""
from __future__ import annotations

import shutil
from pathlib import Path

REPO_REAL = Path(__file__).resolve().parents[3]
WORKSPACE_REAL = REPO_REAL.parent
MODELO_OK = {"ref": "grounding-dino/gdino-tiny-560", "thresholds": {"box": 0.3, "text": 0.25}}
PROMPT_SETS = ("cr01_cr02_v2_short.yaml", "eind_v1.yaml", "edir_v1.yaml", "clase_nueva_v1.yaml",
               "cr01_cr02_v2_tshirt.yaml")
PATTERN_SETS = ("cr01_cr02_v2.yaml", "cr01_cr02_edir_v1.yaml")
# La constancia de lo que midió cada modo (results/gen2/<prueba>/configuracion.json): el chequeo
# previo compara la huella del modo contra ella. Sin resultado.json: las cifras quedan pendientes.
CONSTANCIAS = ("ALR-04", "EXT-01")


# Un modo exploratorio (doc 134 §13.18): un set sin medición en la generación 2. modos.yaml no trae
# ninguno hoy (la distractora salió el 2026-11-04 por su piloto, doc 141 §4), así que los tests lo
# agregan al workspace sintético. Usa el set del piloto, que se conserva en prompts/ como constancia.
MODO_EXPLORATORIO = {
    "nombre": "Distractora «t-shirt»",
    "evidencia": "exploratoria",
    "resumen": "El campeón más una clase que ninguna regla lee.",
    "nota": None,
    "prompts": {
        "set_id": "cr01_cr02_v2_tshirt",
        "fuente": "prompts/cr01_cr02_v2_tshirt.yaml",
        "clases": ["person", "helmet", "vest", "t_shirt"],
        "payload_sha256": "f7d7b344d03b0b82a78c47fef8a25eb35302f330f0b9d9cd5c68a88ec7c72f33",
    },
    "patrones": {
        "id": "cr01_cr02_v2",
        "archivo": "e-ovrt_control-plane/configs/patterns/cr01_cr02_v2.yaml",
        "sha256_archivo": "4f80f5d3b4e78046f8a033044475a667cd0aed930cfeca05295cf63a323570e8",
    },
    "cifras": [],
}


def agregar_modo_exploratorio(repo: Path, id_: str = "distractora") -> None:
    import yaml

    archivo = repo / "experiments" / "demo_defensa" / "modos.yaml"
    datos = yaml.safe_load(archivo.read_text(encoding="utf-8"))
    datos["modos"][id_] = MODO_EXPLORATORIO
    archivo.write_text(yaml.safe_dump(datos, allow_unicode=True, sort_keys=False), encoding="utf-8")


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
    for prueba in CONSTANCIAS:
        destino = repo / "results" / "gen2" / prueba
        destino.mkdir(parents=True)
        shutil.copy2(REPO_REAL / "results" / "gen2" / prueba / "configuracion.json", destino)
    modelos = ws / "e-ovrt_media-plane" / "configs" / "models" / "grounding-dino"
    modelos.mkdir(parents=True)
    shutil.copy2(
        WORKSPACE_REAL / "e-ovrt_media-plane/configs/models/grounding-dino/gdino-tiny-560.yaml", modelos
    )
    return repo
