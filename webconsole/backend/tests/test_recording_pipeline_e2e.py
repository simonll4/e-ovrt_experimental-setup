"""Criterio de aceptación del spec §8: el master grabado entra a la etapa 0."""

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

from eovrt_webconsole.recording.manager import RecordingManager
from eovrt_webconsole.recording.types import RecordingSpec

PREPARE_CLIP = (
    Path(__file__).resolve().parents[4]
    / "e-ovrt_datasets" / "datasets" / "scripts" / "videogt" / "prepare_clip.sh"
)

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None
    or shutil.which("ffprobe") is None
    or not PREPARE_CLIP.is_file(),
    reason="requiere ffmpeg/ffprobe y el repo e-ovrt_datasets como hermano",
)


def _args_file_para_test(url: str, out_path) -> list[str]:
    """Builder de test para inputs `file://`, igual al usado en test_recording_manager.py.

    `build_ffmpeg_args` de producción siempre agrega `-rtsp_transport tcp`, opción
    privada del demuxer rtsp que ffmpeg 8.0.1 rechaza con "Option not found" si el
    input es `file://` (nunca ocurre en producción: ahí solo se graba `rtsp(s)://`
    real). Se agrega `-re` para simular el ritmo de una fuente en vivo.
    """
    return [
        "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
        "-re",
        "-i", str(url),
        "-c", "copy",
        "-movflags", "+faststart",
        "-y",
        str(out_path),
    ]


@pytest.fixture(autouse=True)
def _sin_rtsp_transport_para_file(monkeypatch):
    import eovrt_webconsole.recording.ffmpeg_recorder as recorder_mod

    monkeypatch.setattr(recorder_mod, "build_ffmpeg_args", _args_file_para_test)


def test_el_master_grabado_pasa_por_prepare_clip(tmp_path):
    fuente = tmp_path / "fuente.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
         "-f", "lavfi", "-i", "testsrc=size=640x480:rate=30:duration=15",
         "-c:v", "libx264", "-preset", "ultrafast", "-g", "30", str(fuente)],
        check=True,
    )
    raw = tmp_path / "raw"
    raw.mkdir()

    manager = RecordingManager(
        raw_dir=raw,
        oakd_interpreter=Path(sys.executable),
        oakd_script=Path(__file__).resolve().parents[2] / "tools" / "record_oakd.py",
        # Gate de espacio libre desactivado: el default de producción (5.0 GB)
        # depende de cuánto espacio libre tenga la máquina que corre el test, y
        # tmp_path puede caer en un tmpfs chico (igual que en test_recording_manager.py).
        min_free_gb=0.0,
    )
    manager.start(
        RecordingSpec(
            plugin="rtsp", config={"url": f"file://{fuente}"}, basename="P1-a-take1"
        )
    )
    time.sleep(6.0)
    resumen = manager.stop()
    assert resumen["truncated"] is False

    # Etapa 0 real, con el script del repo de datasets sin modificar.
    # `--to` es relativo al punto de `--ss` en esta versión de ffmpeg (8.0.1): con
    # `-ss 1 -i ... -to N` la ventana de salida dura N segundos desde el segundo 1,
    # no hasta el segundo N absoluto del archivo. Verificado manualmente contra
    # ffmpeg 8.0.1 antes de fijar este valor: `--to 3` da la ventana de 3s / 90
    # frames que se verifica abajo.
    subprocess.run(
        ["bash", str(PREPARE_CLIP), str(raw / "P1-a-take1.mp4"), "v99_c01",
         "--ss", "1", "--to", "3", "--fps", "30"],
        check=True,
        cwd=tmp_path,
        env={"PATH": "/usr/bin:/bin:/usr/local/bin", "HOME": str(tmp_path)},
    )

    # prepare_clip.sh escribe en <repo_e-ovrt_datasets>/datasets-videos/clips
    # (REPO_ROOT/datasets-videos/clips, ver OUT_DIR en el script); se localiza el info.json.
    infos = list(PREPARE_CLIP.parents[3].glob("datasets-videos/clips/v99_c01.info.json"))
    assert infos, "prepare_clip.sh no emitió el info.json"
    info = json.loads(infos[0].read_text())
    try:
        assert info["fps"] == 30
        assert info["n_frames"] == pytest.approx(90, abs=3)
        assert info["duration_ms"] == pytest.approx(3000, abs=150)
    finally:
        infos[0].unlink(missing_ok=True)
        (infos[0].parent / "v99_c01.mp4").unlink(missing_ok=True)
