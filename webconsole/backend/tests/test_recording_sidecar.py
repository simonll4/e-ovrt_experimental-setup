import hashlib
import json

from eovrt_webconsole.recording.probe import Measured
from eovrt_webconsole.recording.sidecar import sha256_of, write_sidecar
from eovrt_webconsole.recording.types import RecordingResult, RecordingSpec


def _result(path, **kwargs):
    base = dict(
        path=path,
        started_wallclock_ms=1784646000000,
        duration_ms=33150,
        size_bytes=path.stat().st_size,
        truncated=False,
        error=None,
    )
    base.update(kwargs)
    return RecordingResult(**base)


def test_sha256_coincide_con_hashlib(tmp_path):
    archivo = tmp_path / "x.mp4"
    archivo.write_bytes(b"contenido de prueba")
    assert sha256_of(archivo) == hashlib.sha256(b"contenido de prueba").hexdigest()


def test_sidecar_oakd_tiene_requested_y_measured(tmp_path):
    master = tmp_path / "P1-a-take2.mp4"
    master.write_bytes(b"\x00" * 1024)
    spec = RecordingSpec(
        plugin="oak_d", config={"url": "192.168.1.50"}, basename="P1-a-take2", label="oak_d_lab"
    )
    path = write_sidecar(spec, _result(master), Measured(1920, 1080, 59.94, 33150))

    assert path == tmp_path / "P1-a-take2.rec.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["basename"] == "P1-a-take2"
    assert data["camera_id"] == "oak_d_lab"
    assert data["plugin"] == "oak_d"
    assert data["requested"] == {
        "fps": 60,
        "resolution": "1080p",
        "codec": "h264",
        "bitrate_bps": 25_000_000,
    }
    assert data["measured"]["resolution"] == "1920x1080"
    assert data["measured"]["fps"] == 59.94
    assert data["truncated"] is False
    assert data["sha256"] == sha256_of(master)


def test_sidecar_rtsp_tiene_requested_vacio(tmp_path):
    master = tmp_path / "P2-a-take1.mp4"
    master.write_bytes(b"\x00" * 16)
    spec = RecordingSpec(plugin="rtsp", config={"url": "rtsp://cam/live"}, basename="P2-a-take1")
    data = json.loads(
        write_sidecar(spec, _result(master), Measured(1280, 720, 15.0, 20000)).read_text()
    )
    assert data["requested"] == {}
    assert data["camera_id"] is None


def test_sidecar_de_toma_truncada_sin_medicion(tmp_path):
    master = tmp_path / "P1-a-take3.mp4"
    master.write_bytes(b"\x00" * 8)
    spec = RecordingSpec(plugin="rtsp", config={"url": "rtsp://cam/live"}, basename="P1-a-take3")
    data = json.loads(
        write_sidecar(
            spec, _result(master, truncated=True, error="ffmpeg murió con rc=1"), None
        ).read_text()
    )
    assert data["truncated"] is True
    assert data["error"] == "ffmpeg murió con rc=1"
    assert data["measured"]["resolution"] is None
