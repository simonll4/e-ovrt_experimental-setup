"""Tests para clips/inventory.py: listar masters y clips del banco."""

from __future__ import annotations

import json

from eovrt_webconsole.clips.inventory import list_clips, list_masters
from eovrt_webconsole.recording.probe import Measured


def _dv(tmp_path):
    """Prepara un directorio datasets-videos con raw/ y clips/."""
    dv = tmp_path / "datasets-videos"
    (dv / "raw").mkdir(parents=True)
    (dv / "clips").mkdir()
    return dv


def _measure_fake(monkeypatch, duration_ms=33000):
    """Mockea measure() para devolver valores determinísticos."""
    import eovrt_webconsole.clips.inventory as inv

    monkeypatch.setattr(
        inv, "measure",
        lambda path: Measured(width=1920, height=1080, fps=30.0, duration_ms=duration_ms),
    )


def test_master_sin_recortar(tmp_path, monkeypatch):
    """Master sin clips vinculados."""
    dv = _dv(tmp_path)
    _measure_fake(monkeypatch)
    (dv / "raw" / "P1-a-take1.mp4").write_bytes(b"x" * 10)
    [m] = list_masters(dv / "raw", dv)
    assert m["name"] == "P1-a-take1.mp4"
    assert m["scenario"] == "P1"
    assert m["duration_ms"] == 33000
    assert m["readable"] is True
    assert m["clips"] == []


def test_master_con_clip_generado(tmp_path, monkeypatch):
    """Master vinculado a un clip mediante .clip.yaml."""
    dv = _dv(tmp_path)
    _measure_fake(monkeypatch)
    (dv / "raw" / "P1-a-take1.mp4").write_bytes(b"x")
    (dv / "a_p1_c01.clip.yaml").write_text(
        "clip_id: a_p1_c01\nblock: A\nscenario: P1\nmaster: raw/P1-a-take1.mp4\n"
    )
    [m] = list_masters(dv / "raw", dv)
    assert m["clips"] == ["a_p1_c01"]


def test_master_ilegible_se_marca_sin_romper(tmp_path, monkeypatch):
    """Master ilegible por ffprobe: readable=False, duration_ms=None."""
    import eovrt_webconsole.clips.inventory as inv
    from eovrt_webconsole.recording.probe import ProbeError

    dv = _dv(tmp_path)

    def _explota(path):
        raise ProbeError("no es un video")

    monkeypatch.setattr(inv, "measure", _explota)
    (dv / "raw" / "P1-a-take1.mp4").write_bytes(b"basura")
    [m] = list_masters(dv / "raw", dv)
    assert m["readable"] is False
    assert m["duration_ms"] is None


def test_raw_inexistente_lista_vacia(tmp_path):
    """raw/ inexistente devuelve lista vacía."""
    assert list_masters(tmp_path / "no", tmp_path) == []


def test_solo_mp4_y_ordenado(tmp_path, monkeypatch):
    """Solo se listan *.mp4; se ordena por nombre."""
    dv = _dv(tmp_path)
    _measure_fake(monkeypatch)
    (dv / "raw" / "P2-a-take1.mp4").write_bytes(b"x")
    (dv / "raw" / "P1-a-take1.mp4").write_bytes(b"x")
    (dv / "raw" / "README.txt").write_text("ignorar")
    ms = list_masters(dv / "raw", dv)
    assert len(ms) == 2
    assert [m["name"] for m in ms] == ["P1-a-take1.mp4", "P2-a-take1.mp4"]


def test_list_clips(tmp_path):
    """Clip con info.json y .clip.yaml."""
    dv = _dv(tmp_path)
    info = {
        "clip_id": "a_p1_c01", "file": "clips/a_p1_c01.mp4", "fps": 30,
        "duration_ms": 20500, "n_frames": 615, "resolution": "1920x1080",
        "sha256": "0" * 64,
    }
    (dv / "clips" / "a_p1_c01.info.json").write_text(json.dumps(info))
    (dv / "clips" / "a_p1_c01.mp4").write_bytes(b"x")
    (dv / "a_p1_c01.clip.yaml").write_text(
        "clip_id: a_p1_c01\nblock: A\nscenario: P1\nmaster: raw/P1-a-take1.mp4\n"
        "episode_draft:\n  onset_ms: 3500\n  end_ms: 17500\n  marked_by: consola\n"
        "  warnings: ['solo 2.0 s de cola, se necesitan 3']\n"
    )
    [c] = list_clips(dv)
    assert c["clip_id"] == "a_p1_c01"
    assert c["n_frames"] == 615
    assert c["has_yaml"] is True
    assert c["master"] == "raw/P1-a-take1.mp4"
    assert c["warnings"] == ["solo 2.0 s de cola, se necesitan 3"]


def test_clip_ajeno_sin_yaml(tmp_path):
    """Clip sin .clip.yaml (ajeno, recortado externamente)."""
    dv = _dv(tmp_path)
    info = {
        "clip_id": "v01_c01", "file": "clips/v01_c01.mp4", "fps": 30,
        "duration_ms": 15000, "n_frames": 450, "resolution": "1280x720",
        "sha256": "0" * 64,
    }
    (dv / "clips" / "v01_c01.info.json").write_text(json.dumps(info))
    [c] = list_clips(dv)
    assert c["has_yaml"] is False
    assert c["master"] is None
    assert c["warnings"] == []


def test_clips_inexistente_lista_vacia(tmp_path):
    """clips/ inexistente devuelve lista vacía."""
    assert list_clips(tmp_path) == []
