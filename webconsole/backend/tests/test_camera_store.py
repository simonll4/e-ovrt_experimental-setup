import pytest

from eovrt_webconsole import camera_store as cs

PRESET = {
    "id": "oak_d_lab",
    "name": "OAK-D laboratorio",
    "plugin": "oak_d",
    "config": {"url": "192.168.1.50"},
}


def test_create_y_get(tmp_path):
    created = cs.create_camera(tmp_path, PRESET)
    assert created["id"] == "oak_d_lab"
    assert (tmp_path / "oak_d_lab.yaml").exists()
    assert cs.get_camera(tmp_path, "oak_d_lab")["config"] == {"url": "192.168.1.50"}


def test_list(tmp_path):
    cs.create_camera(tmp_path, PRESET)
    cs.create_camera(tmp_path, {**PRESET, "id": "rtsp_norte", "plugin": "rtsp"})
    ids = [c["id"] for c in cs.list_cameras(tmp_path)]
    assert ids == ["oak_d_lab", "rtsp_norte"]


def test_create_duplicado(tmp_path):
    cs.create_camera(tmp_path, PRESET)
    with pytest.raises(cs.CameraExists):
        cs.create_camera(tmp_path, PRESET)


def test_update(tmp_path):
    cs.create_camera(tmp_path, PRESET)
    updated = cs.update_camera(tmp_path, "oak_d_lab", {**PRESET, "name": "OAK-D obra"})
    assert updated["name"] == "OAK-D obra"


def test_delete(tmp_path):
    cs.create_camera(tmp_path, PRESET)
    cs.delete_camera(tmp_path, "oak_d_lab")
    with pytest.raises(cs.CameraNotFound):
        cs.get_camera(tmp_path, "oak_d_lab")


def test_id_invalido(tmp_path):
    with pytest.raises(cs.CameraInvalid):
        cs.create_camera(tmp_path, {**PRESET, "id": "Oak D!"})


def test_get_inexistente(tmp_path):
    with pytest.raises(cs.CameraNotFound):
        cs.get_camera(tmp_path, "nada")


def test_list_saltea_yaml_corrupto(tmp_path):
    cs.create_camera(tmp_path, PRESET)
    (tmp_path / "corrupt.yaml").write_text("id: [unclosed\n  - broken", encoding="utf-8")
    ids = [c["id"] for c in cs.list_cameras(tmp_path)]
    assert ids == ["oak_d_lab"]


def test_get_yaml_corrupto_lanza_camera_invalid(tmp_path):
    (tmp_path / "corrupt.yaml").write_text("id: [unclosed\n  - broken", encoding="utf-8")
    with pytest.raises(cs.CameraInvalid):
        cs.get_camera(tmp_path, "corrupt")
