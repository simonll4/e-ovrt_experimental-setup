import pytest

from eovrt_webconsole.recording.naming import InvalidTakeId, next_basename


def test_primer_take_cuando_no_hay_nada(tmp_path):
    assert next_basename(tmp_path, "P1", "a") == "P1-a-take1"


def test_directorio_inexistente_devuelve_primer_take(tmp_path):
    assert next_basename(tmp_path / "no-existe", "P1", "a") == "P1-a-take1"


def test_autoincrementa_sobre_lo_existente(tmp_path):
    (tmp_path / "P1-a-take1.mp4").touch()
    (tmp_path / "P1-a-take2.mp4").touch()
    assert next_basename(tmp_path, "P1", "a") == "P1-a-take3"


def test_huecos_en_la_numeracion_no_reusan_numeros(tmp_path):
    (tmp_path / "P1-a-take1.mp4").touch()
    (tmp_path / "P1-a-take7.mp4").touch()
    assert next_basename(tmp_path, "P1", "a") == "P1-a-take8"


def test_no_se_mezclan_escenarios_ni_variantes(tmp_path):
    (tmp_path / "P1-a-take5.mp4").touch()
    (tmp_path / "P2-a-take9.mp4").touch()
    (tmp_path / "P1-b-take3.mp4").touch()
    assert next_basename(tmp_path, "P1", "a") == "P1-a-take6"
    assert next_basename(tmp_path, "P1", "b") == "P1-b-take4"
    assert next_basename(tmp_path, "P3", "a") == "P3-a-take1"


def test_ignora_archivos_ajenos(tmp_path):
    (tmp_path / "4.1.mp4").touch()
    (tmp_path / "P1-a-notatake.mp4").touch()
    assert next_basename(tmp_path, "P1", "a") == "P1-a-take1"


@pytest.mark.parametrize("scenario", ["P0", "P10", "x", "P", "P1a", ""])
def test_escenario_invalido(tmp_path, scenario):
    with pytest.raises(InvalidTakeId):
        next_basename(tmp_path, scenario, "a")


@pytest.mark.parametrize("variant", ["A", "ab", "1", ""])
def test_variante_invalida(tmp_path, variant):
    with pytest.raises(InvalidTakeId):
        next_basename(tmp_path, "P1", variant)
