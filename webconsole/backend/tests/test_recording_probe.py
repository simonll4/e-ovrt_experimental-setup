import shutil
import subprocess

import pytest

from eovrt_webconsole.recording.probe import ProbeError, measure

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="requiere ffmpeg y ffprobe en el sistema",
)


@pytest.fixture
def video_2s(tmp_path):
    """2 segundos de barras de color a 25 fps, 320x240."""
    out = tmp_path / "muestra.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", "testsrc=size=320x240:rate=25:duration=2",
            "-c:v", "libx264", "-preset", "ultrafast", str(out),
        ],
        check=True,
    )
    return out


def test_mide_dimensiones_fps_y_duracion(video_2s):
    m = measure(video_2s)
    assert (m.width, m.height) == (320, 240)
    assert m.fps == pytest.approx(25.0, abs=0.1)
    assert m.duration_ms == pytest.approx(2000, abs=100)


def test_archivo_inexistente(tmp_path):
    with pytest.raises(ProbeError):
        measure(tmp_path / "no-existe.mp4")


def test_archivo_vacio_no_es_video(tmp_path):
    vacio = tmp_path / "vacio.mp4"
    vacio.touch()
    with pytest.raises(ProbeError):
        measure(vacio)
