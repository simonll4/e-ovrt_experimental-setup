import shutil
import subprocess
from pathlib import Path

import pytest

from eovrt_webconsole.clips.trim import TrimFailed, run_prepare_clip

REAL_SCRIPT = (
    Path(__file__).resolve().parents[4]
    / "e-ovrt_datasets" / "datasets" / "scripts" / "videogt" / "prepare_clip.sh"
)

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None
    or shutil.which("ffprobe") is None
    or not REAL_SCRIPT.exists(),
    reason="requiere ffmpeg/ffprobe y el repo e-ovrt_datasets",
)


@pytest.fixture
def fake_repo(tmp_path):
    """Réplica de la forma del repo datasets: el script escribe SIEMPRE en
    <su repo>/datasets-videos/clips, así que se lo copia a un repo falso."""
    script = tmp_path / "datasets" / "scripts" / "videogt" / "prepare_clip.sh"
    script.parent.mkdir(parents=True)
    shutil.copy(REAL_SCRIPT, script)
    clips = tmp_path / "datasets-videos" / "clips"
    clips.mkdir(parents=True)
    return script, clips


@pytest.fixture
def master(tmp_path):
    out = tmp_path / "P1-a-take1.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
         "-f", "lavfi", "-i", "testsrc=size=320x240:rate=30:duration=20",
         "-c:v", "libx264", "-preset", "ultrafast", str(out)],
        check=True,
    )
    return out


def test_recorte_nominal(fake_repo, master):
    script, clips_dir = fake_repo
    # Criterio de aceptación del spec §8: n_frames coherente con la ventana.
    info = run_prepare_clip(script, clips_dir, master, "a_p1_c01", ss=5.0, duration=8.0)
    assert info["clip_id"] == "a_p1_c01"
    assert info["fps"] == 30
    # 8 s a 30 fps = 240 frames (tolerancia 1 por el borde del corte)
    assert abs(info["n_frames"] - 240) <= 1
    assert (clips_dir / "a_p1_c01.mp4").exists()
    # D3: --to fue duración. Si prepare_clip lo hubiera tratado como instante
    # absoluto el clip tendría ~90 frames (3 s); la trampa quedaría atrapada acá.


def test_master_intacto_tras_recortar(fake_repo, master):
    script, clips_dir = fake_repo
    antes = master.read_bytes()
    run_prepare_clip(script, clips_dir, master, "a_p1_c02", ss=0.0, duration=5.0)
    assert master.read_bytes() == antes  # D8


def test_falla_reporta_salida_real(fake_repo, tmp_path):
    script, clips_dir = fake_repo
    inexistente = tmp_path / "no-existe.mp4"
    with pytest.raises(TrimFailed) as excinfo:
        run_prepare_clip(script, clips_dir, inexistente, "a_p1_c03", ss=0.0, duration=5.0)
    # La salida real de ffmpeg, no un genérico:
    assert "no-existe.mp4" in str(excinfo.value)


def test_clip_id_invalido_lo_rechaza_el_script(fake_repo, master):
    script, clips_dir = fake_repo
    with pytest.raises(TrimFailed) as excinfo:
        run_prepare_clip(script, clips_dir, master, "a p1 c01", ss=0.0, duration=5.0)
    assert "clip_id" in str(excinfo.value)
