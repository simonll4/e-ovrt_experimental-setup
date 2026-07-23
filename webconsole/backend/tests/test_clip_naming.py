import pytest

from eovrt_webconsole.clips.naming import (
    InvalidScenario,
    next_clip_id,
    scenario_from_master,
)


def test_primer_clip_del_escenario(tmp_path):
    assert next_clip_id(tmp_path, "P1") == "a_p1_c01"


def test_autoincremento_por_yaml(tmp_path):
    (tmp_path / "a_p1_c01.clip.yaml").write_text("clip_id: a_p1_c01\n")
    (tmp_path / "a_p1_c02.clip.yaml").write_text("clip_id: a_p1_c02\n")
    assert next_clip_id(tmp_path, "P1") == "a_p1_c03"


def test_mp4_sin_yaml_tambien_reserva_el_numero(tmp_path):
    # Un clip recortado cuyo yaml se borró no debe ser pisado.
    (tmp_path / "clips").mkdir()
    (tmp_path / "clips" / "a_p2_c05.mp4").write_bytes(b"")
    assert next_clip_id(tmp_path, "P2") == "a_p2_c06"


def test_huecos_no_se_rellenan(tmp_path):
    # c01 y c03: el próximo es c04, no c02 (regenerar c02 sería ambiguo).
    (tmp_path / "a_p1_c01.clip.yaml").write_text("x: 1\n")
    (tmp_path / "a_p1_c03.clip.yaml").write_text("x: 1\n")
    assert next_clip_id(tmp_path, "P1") == "a_p1_c04"


def test_material_ajeno_no_interfiere(tmp_path):
    (tmp_path / "cb_b01_p7.clip.yaml").write_text("x: 1\n")
    (tmp_path / "clips").mkdir()
    (tmp_path / "clips" / "v01_c01.mp4").write_bytes(b"")
    assert next_clip_id(tmp_path, "P1") == "a_p1_c01"


def test_escenarios_independientes(tmp_path):
    (tmp_path / "a_p1_c01.clip.yaml").write_text("x: 1\n")
    assert next_clip_id(tmp_path, "P2") == "a_p2_c01"


def test_directorio_inexistente_arranca_en_c01(tmp_path):
    assert next_clip_id(tmp_path / "no-existe", "P1") == "a_p1_c01"


def test_escenario_invalido(tmp_path):
    with pytest.raises(InvalidScenario):
        next_clip_id(tmp_path, "P0")
    with pytest.raises(InvalidScenario):
        next_clip_id(tmp_path, "x")


def test_scenario_from_master():
    assert scenario_from_master("P1-a-take2.mp4") == "P1"
    assert scenario_from_master("P9-c-take11.mp4") == "P9"
    assert scenario_from_master("4.1.mp4") is None
    assert scenario_from_master("cb_b01_p7.mp4") is None
