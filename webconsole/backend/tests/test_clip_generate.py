import pytest

from eovrt_webconsole.clips.generate import InvalidRequest, generate_clip
from eovrt_webconsole.clips.window import InvalidMarks
from eovrt_webconsole.recording.probe import Measured, ProbeError


@pytest.fixture
def dv(tmp_path):
    dv = tmp_path / "datasets-videos"
    (dv / "raw").mkdir(parents=True)
    (dv / "clips").mkdir()
    (dv / "preann").mkdir()
    (dv / "raw" / "P1-a-take1.mp4").write_bytes(b"master")
    return dv


@pytest.fixture
def stubs(monkeypatch):
    import eovrt_webconsole.clips.generate as gen

    llamadas = {}

    def _measure(path):
        return Measured(width=1920, height=1080, fps=30.0, duration_ms=33000)

    def _run(script, clips_dir, master, clip_id, ss, duration, fps=30):
        llamadas["trim"] = {
            "master": master, "clip_id": clip_id, "ss": ss, "duration": duration,
        }
        info = {
            "clip_id": clip_id, "file": f"clips/{clip_id}.mp4", "fps": fps,
            "duration_ms": round(duration * 1000),
            "n_frames": round(duration * fps), "resolution": "1920x1080",
            "sha256": "0" * 64,
        }
        (clips_dir / f"{clip_id}.mp4").write_bytes(b"clip")
        import json
        (clips_dir / f"{clip_id}.info.json").write_text(json.dumps(info))
        return info

    monkeypatch.setattr(gen, "measure", _measure)
    monkeypatch.setattr(gen, "run_prepare_clip", _run)
    return llamadas


def test_flujo_nominal(dv, stubs, tmp_path):
    result = generate_clip(
        raw_dir=dv / "raw", videos_dir=dv, script=tmp_path / "s.sh",
        master_name="P1-a-take1.mp4", t_event=10.5, t_end=24.5,
    )
    assert result["clip_id"] == "a_p1_c01"
    assert result["regenerated"] is False
    assert result["invalidated"] == []
    assert result["warnings"] == []
    assert stubs["trim"]["ss"] == 7.0
    assert stubs["trim"]["duration"] == 20.5
    # El yaml quedó escrito con el borrador del episodio:
    import yaml
    data = yaml.safe_load((dv / "a_p1_c01.clip.yaml").read_text())
    assert data["episode_draft"]["onset_ms"] == 3500


def test_autoincremento_si_ya_hay_clips(dv, stubs, tmp_path):
    (dv / "a_p1_c01.clip.yaml").write_text("clip_id: a_p1_c01\nmaster: raw/x.mp4\n")
    result = generate_clip(
        raw_dir=dv / "raw", videos_dir=dv, script=tmp_path / "s.sh",
        master_name="P1-a-take1.mp4", t_event=10.5, t_end=24.5,
    )
    assert result["clip_id"] == "a_p1_c02"


def test_regenerar_invalida_la_preann_vieja(dv, stubs, tmp_path):
    (dv / "preann" / "a_p1_c01.xml").write_text("<annotations/>")
    (dv / "preann" / "a_p1_c01.preview.mp4").write_bytes(b"v")
    result = generate_clip(
        raw_dir=dv / "raw", videos_dir=dv, script=tmp_path / "s.sh",
        master_name="P1-a-take1.mp4", t_event=11.0, t_end=25.0,
        clip_id="a_p1_c01",
    )
    assert result["regenerated"] is True
    assert sorted(result["invalidated"]) == [
        "preann/a_p1_c01.preview.mp4", "preann/a_p1_c01.xml",
    ]
    # D9: el XML viejo son cajas de un video que ya no existe.
    assert not (dv / "preann" / "a_p1_c01.xml").exists()
    assert (dv / "preann" / "a_p1_c01.xml.stale").exists()


def test_regenerar_dos_veces_pisa_el_stale(dv, stubs, tmp_path):
    (dv / "preann" / "a_p1_c01.xml").write_text("v1")
    (dv / "preann" / "a_p1_c01.xml.stale").write_text("v0")
    generate_clip(
        raw_dir=dv / "raw", videos_dir=dv, script=tmp_path / "s.sh",
        master_name="P1-a-take1.mp4", t_event=11.0, t_end=25.0,
        clip_id="a_p1_c01",
    )
    assert (dv / "preann" / "a_p1_c01.xml.stale").read_text() == "v1"


def test_material_ajeno_requiere_escenario(dv, stubs, tmp_path):
    (dv / "raw" / "4.1.mp4").write_bytes(b"m")
    with pytest.raises(InvalidRequest):
        generate_clip(
            raw_dir=dv / "raw", videos_dir=dv, script=tmp_path / "s.sh",
            master_name="4.1.mp4", t_event=5.0, t_end=10.0,
        )
    result = generate_clip(
        raw_dir=dv / "raw", videos_dir=dv, script=tmp_path / "s.sh",
        master_name="4.1.mp4", t_event=5.0, t_end=10.0, scenario="P2",
    )
    assert result["clip_id"] == "a_p2_c01"


def test_master_inexistente(dv, stubs, tmp_path):
    with pytest.raises(InvalidRequest):
        generate_clip(
            raw_dir=dv / "raw", videos_dir=dv, script=tmp_path / "s.sh",
            master_name="no-esta.mp4", t_event=5.0, t_end=10.0,
        )


def test_path_traversal_rechazado(dv, stubs, tmp_path):
    with pytest.raises(InvalidRequest):
        generate_clip(
            raw_dir=dv / "raw", videos_dir=dv, script=tmp_path / "s.sh",
            master_name="../../../etc/passwd", t_event=5.0, t_end=10.0,
        )


def test_master_ilegible_propaga_probe_error(dv, stubs, monkeypatch, tmp_path):
    import eovrt_webconsole.clips.generate as gen

    def _explota(path):
        raise ProbeError("no es un video")

    monkeypatch.setattr(gen, "measure", _explota)
    with pytest.raises(ProbeError):
        generate_clip(
            raw_dir=dv / "raw", videos_dir=dv, script=tmp_path / "s.sh",
            master_name="P1-a-take1.mp4", t_event=5.0, t_end=10.0,
        )


def test_marcas_invalidas_propagan(dv, stubs, tmp_path):
    with pytest.raises(InvalidMarks):
        generate_clip(
            raw_dir=dv / "raw", videos_dir=dv, script=tmp_path / "s.sh",
            master_name="P1-a-take1.mp4", t_event=20.0, t_end=10.0,
        )
