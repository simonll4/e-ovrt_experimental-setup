import shutil
import subprocess
import time

import pytest

from eovrt_webconsole.recording.ffmpeg_recorder import FfmpegCopyRecorder, build_ffmpeg_args
from eovrt_webconsole.recording.probe import measure
from eovrt_webconsole.recording.types import RecordingSpec

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="requiere ffmpeg y ffprobe en el sistema",
)


@pytest.fixture
def fuente_larga(tmp_path):
    """10 s de video a 25 fps: alcanza para arrancar, esperar y cortar."""
    out = tmp_path / "fuente.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", "testsrc=size=320x240:rate=25:duration=10",
            "-c:v", "libx264", "-preset", "ultrafast", "-g", "25", str(out),
        ],
        check=True,
    )
    return out


def _spec(url: str) -> RecordingSpec:
    return RecordingSpec(plugin="rtsp", config={"url": url}, basename="P1-a-take1")


def _args_file_para_test(url: str, out_path) -> list[str]:
    """Builder de test para inputs `file://`: NO es la rama de producción.

    `build_ffmpeg_args` de producción siempre agrega `-rtsp_transport tcp`, opción
    privada del demuxer rtsp que ffmpeg 8.0.1 rechaza con "Option not found" si el
    input es `file://` (por eso no va acá). Y una copia de bitstream de un archivo
    local termina en ~50 ms -- demasiado rápido para observar el estado "recording" --
    así que se agrega `-re` para simular el ritmo de una fuente en vivo. Ninguna de
    las dos cosas debe vivir en el código de producción: ahí nunca se graba un
    `file://`, solo `rtsp(s)://` real.
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


def test_args_fuerzan_tcp_y_copy():
    args = build_ffmpeg_args("rtsp://cam/live", "/tmp/x.mp4")
    assert "-rtsp_transport" in args and args[args.index("-rtsp_transport") + 1] == "tcp"
    assert "-c" in args and args[args.index("-c") + 1] == "copy"
    assert args[-1] == "/tmp/x.mp4"


def test_args_fuerzan_tcp_tambien_en_rtsps():
    """RTSP sobre TLS: mismo bug de esquema que translation.py ya tuvo que cubrir
    (ver _RTSP_USERINFO ahí). Sin esto, una cámara rtsps:// pierde el forzado a TCP
    y sobre UDP el DVR pierde paquetes, dejando macrobloques irreparables en el master."""
    args = build_ffmpeg_args("rtsps://cam/live", "/tmp/x.mp4")
    assert "-rtsp_transport" in args and args[args.index("-rtsp_transport") + 1] == "tcp"


def test_graba_y_corta_produciendo_un_mp4_reproducible(tmp_path, fuente_larga, monkeypatch):
    import eovrt_webconsole.recording.ffmpeg_recorder as recorder_mod

    monkeypatch.setattr(recorder_mod, "build_ffmpeg_args", _args_file_para_test)

    destino = tmp_path / "P1-a-take1.mp4"
    recorder = FfmpegCopyRecorder(_spec(f"file://{fuente_larga}"), destino)
    recorder.start()
    time.sleep(2.0)
    estado = recorder.poll()
    assert estado.state == "recording"
    result = recorder.stop()

    assert result.path == destino
    assert destino.exists() and result.size_bytes > 0
    assert result.truncated is False
    assert measure(destino).width == 320


def test_poll_reporta_error_si_la_fuente_no_existe(tmp_path, monkeypatch):
    import eovrt_webconsole.recording.ffmpeg_recorder as recorder_mod

    monkeypatch.setattr(recorder_mod, "build_ffmpeg_args", _args_file_para_test)

    destino = tmp_path / "P1-a-take1.mp4"
    recorder = FfmpegCopyRecorder(_spec("file:///no/existe/nada.mp4"), destino)
    recorder.start()
    deadline = time.monotonic() + 10
    while recorder.poll().state == "recording" and time.monotonic() < deadline:
        time.sleep(0.1)
    assert recorder.poll().state == "error"
    result = recorder.stop()
    assert result.truncated is True
    assert result.error is not None


def test_stop_sin_start_es_error_explicito(tmp_path):
    recorder = FfmpegCopyRecorder(_spec("file:///x"), tmp_path / "P1-a-take1.mp4")
    with pytest.raises(RuntimeError, match="sin arrancar"):
        recorder.stop()


def test_kill_por_timeout_deja_truncado_y_con_motivo(tmp_path, monkeypatch):
    """Hallazgo IMPORTANT: si ffmpeg ignora SIGINT y hay que matarlo con kill(),
    el mp4 queda sin el átomo moov (no reproducible). Antes del fix, `stop()`
    solo marcaba truncated/error cuando el proceso moría *solo*: un kill()
    forzado salía con truncated=False y error=None, como si la toma fuera sana.
    """
    import eovrt_webconsole.recording.ffmpeg_recorder as recorder_mod

    monkeypatch.setattr(recorder_mod, "_STOP_TIMEOUT_S", 0.3)

    def fake_args(url, out_path):
        # Ignora SIGINT a propósito y duerme mucho: fuerza el camino kill() por
        # timeout, igual que un ffmpeg colgado en producción.
        return ["bash", "-c", "trap '' SIGINT; sleep 30"]

    monkeypatch.setattr(recorder_mod, "build_ffmpeg_args", fake_args)
    destino = tmp_path / "P1-a-take1.mp4"
    recorder = FfmpegCopyRecorder(_spec("file:///x"), destino)
    recorder.start()
    time.sleep(0.2)

    result = recorder.stop()

    assert result.truncated is True
    assert result.error is not None
    assert "moov" in result.error


def test_stderr_con_credenciales_no_llega_al_result(tmp_path, monkeypatch):
    """Hallazgo CRITICAL: si ffmpeg falla, su stderr puede traer la URL con
    credenciales en claro (ffmpeg la imprime tal cual al reportar el error de
    conexión). Ese stderr no debe propagarse crudo a RecordingResult.error: de
    ahí lo escribe write_sidecar() verbatim en el .rec.json que queda en disco."""
    import eovrt_webconsole.recording.ffmpeg_recorder as recorder_mod

    url_con_credenciales = "rtsp://admin:supersecreta@192.168.1.50/live"

    def fake_args(url: str, out_path) -> list[str]:
        return [
            "bash", "-c",
            f"echo 'No se pudo conectar a {url_con_credenciales}' >&2; exit 1",
        ]

    monkeypatch.setattr(recorder_mod, "build_ffmpeg_args", fake_args)
    destino = tmp_path / "P1-a-take1.mp4"
    recorder = FfmpegCopyRecorder(_spec(url_con_credenciales), destino)
    recorder.start()
    recorder._proc.wait(timeout=5)
    result = recorder.stop()

    assert result.error is not None
    assert "supersecreta" not in result.error
    assert "***:***@" in result.error
