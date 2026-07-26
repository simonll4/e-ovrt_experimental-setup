import importlib.util
from pathlib import Path

import pytest
import yaml

from eovrt_webconsole.clips.clip_yaml import write_clip_yaml
from eovrt_webconsole.clips.window import EpisodeDraft, TrimWindow

# Contrato real (spec §8): el YAML generado se valida con la MISMA función
# del script consumidor, no con lo que este repo suponga.
DERIVE_GT = (
    Path(__file__).resolve().parents[4]
    / "e-ovrt_datasets" / "datasets" / "scripts" / "videogt" / "derive_clip_gt.py"
)

VENTANA = TrimWindow(
    ss=7.0, duration=20.5,
    episodes=[EpisodeDraft(onset_ms=3500, end_ms=17500, condition="CR-01")],
    warnings=[],
)


def test_contenido_del_yaml(tmp_path):
    path = write_clip_yaml(tmp_path, "a_p1_c01", "P1", "P1-a-take2.mp4", VENTANA)
    assert path == tmp_path / "a_p1_c01.clip.yaml"
    data = yaml.safe_load(path.read_text())
    assert data["clip_id"] == "a_p1_c01"
    assert data["block"] == "A"
    assert data["scenario"] == "P1"
    assert data["source_id"] == "a_p1_c01"
    assert data["level"] == "scene"
    assert data["master"] == "raw/P1-a-take2.mp4"
    assert data["episode_draft"] == [
        {"onset_ms": 3500, "end_ms": 17500, "condition": "CR-01"},
    ]


def test_las_advertencias_quedan_registradas(tmp_path):
    ventana = TrimWindow(
        ss=0.0, duration=18.0,
        episodes=[EpisodeDraft(onset_ms=2000, end_ms=15000, condition="CR-01")],
        warnings=["solo 2.0 s de pre-roll, se necesitan 3.5 — el TTFD va a salir degradado"],
    )
    path = write_clip_yaml(tmp_path, "a_p1_c02", "P1", "P1-a-take3.mp4", ventana)
    data = yaml.safe_load(path.read_text())
    assert data["warnings"] == ventana.warnings


def test_regenerar_sobrescribe(tmp_path):
    write_clip_yaml(tmp_path, "a_p1_c01", "P1", "P1-a-take2.mp4", VENTANA)
    nueva = TrimWindow(
        ss=8.0, duration=19.0,
        episodes=[EpisodeDraft(onset_ms=3500, end_ms=16000, condition="CR-01")],
        warnings=[],
    )
    write_clip_yaml(tmp_path, "a_p1_c01", "P1", "P1-a-take2.mp4", nueva)
    data = yaml.safe_load((tmp_path / "a_p1_c01.clip.yaml").read_text())
    assert data["episode_draft"][0]["end_ms"] == 16000


def test_dos_episodios_se_escriben_como_lista_de_dos(tmp_path):
    ventana = TrimWindow(
        ss=3.0, duration=32.5,
        episodes=[
            EpisodeDraft(onset_ms=3500, end_ms=6500, condition="CR-01"),
            EpisodeDraft(onset_ms=6500, end_ms=29500, condition="CR-02"),
        ],
        warnings=[],
    )
    path = write_clip_yaml(tmp_path, "a_p6_c01", "P6", "P6-a-take2.mp4", ventana)
    data = yaml.safe_load(path.read_text())
    assert len(data["episode_draft"]) == 2
    assert data["episode_draft"][1]["condition"] == "CR-02"


@pytest.mark.skipif(not DERIVE_GT.exists(), reason="repo e-ovrt_datasets no disponible")
def test_el_yaml_pasa_la_validacion_real_de_derive_clip_gt(tmp_path):
    spec = importlib.util.spec_from_file_location("derive_clip_gt", DERIVE_GT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    path = write_clip_yaml(tmp_path, "a_p1_c01", "P1", "P1-a-take2.mp4", VENTANA)
    meta = mod.load_clip_meta(path)   # levanta ValueError si el contrato se rompe
    assert meta["clip_id"] == "a_p1_c01"
    assert meta["block"] == "A"
    assert meta["scenario"] == "P1"
