import pytest
from pydantic import ValidationError

from eovrt_webconsole.recording.guards import GateError, check_destination, check_free_space
from eovrt_webconsole.recording.types import CaptureSpec, RecordingSpec


def test_destino_valido(tmp_path):
    check_destination(tmp_path)  # no levanta


def test_destino_bajo_mnt_c_se_rechaza(tmp_path, monkeypatch):
    fake = tmp_path / "mnt" / "c" / "raw"
    fake.mkdir(parents=True)
    monkeypatch.setattr(
        "eovrt_webconsole.recording.guards._FORBIDDEN_PREFIXES", (str(tmp_path / "mnt" / "c"),)
    )
    with pytest.raises(GateError, match="/mnt/c"):
        check_destination(fake)


def test_destino_se_crea_si_no_existe(tmp_path):
    destino = tmp_path / "nuevo" / "raw"
    check_destination(destino)
    assert destino.is_dir()


def test_destino_que_es_un_archivo_se_rechaza(tmp_path):
    archivo = tmp_path / "soy-un-archivo"
    archivo.touch()
    with pytest.raises(GateError, match="no es un directorio"):
        check_destination(archivo)


def test_espacio_suficiente(tmp_path):
    check_free_space(tmp_path, min_gb=0.0)  # no levanta


def test_espacio_insuficiente(tmp_path):
    with pytest.raises(GateError, match="espacio"):
        check_free_space(tmp_path, min_gb=10_000_000.0)


def test_spec_rtsp_con_capture_es_invalida():
    with pytest.raises(ValidationError, match="capture"):
        RecordingSpec(
            plugin="rtsp",
            config={"url": "rtsp://cam/live"},
            basename="P1-a-take1",
            capture=CaptureSpec(),
        )


def test_spec_rtsp_sin_capture_es_valida():
    spec = RecordingSpec(plugin="rtsp", config={"url": "rtsp://cam/live"}, basename="P1-a-take1")
    assert spec.capture is None
    assert spec.max_duration_s == 600


def test_spec_oakd_completa_por_default():
    spec = RecordingSpec(plugin="oak_d", config={"url": "192.168.1.50"}, basename="P1-a-take1")
    assert spec.capture is not None
    assert spec.capture.fps == 60
    assert spec.capture.bitrate_bps == 25_000_000


def test_spec_rechaza_plugin_desconocido():
    with pytest.raises(ValidationError):
        RecordingSpec(plugin="image_folder", config={}, basename="P1-a-take1")


def test_spec_rechaza_basename_invalido():
    with pytest.raises(ValidationError):
        RecordingSpec(plugin="rtsp", config={"url": "x"}, basename="../../etc/passwd")
