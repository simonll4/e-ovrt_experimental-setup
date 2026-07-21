import json
import shutil
import sys
import time
from pathlib import Path

import pytest

from eovrt_webconsole.recording.guards import GateError
from eovrt_webconsole.recording.manager import (
    BasenameTaken,
    RecordingBusy,
    RecordingManager,
)
from eovrt_webconsole.recording.types import RecordingSpec

SCRIPT_REAL = Path(__file__).resolve().parents[2] / "tools" / "record_oakd.py"

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="requiere ffmpeg y ffprobe en el sistema",
)


def _args_file_para_test(url: str, out_path) -> list[str]:
    """Builder de test para inputs `file://`, igual al usado en test_ffmpeg_recorder.py.

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


@pytest.fixture
def fuente(tmp_path):
    import subprocess

    out = tmp_path / "fuente.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
         "-f", "lavfi", "-i", "testsrc=size=320x240:rate=25:duration=20",
         "-c:v", "libx264", "-preset", "ultrafast", "-g", "25", str(out)],
        check=True,
    )
    return out


@pytest.fixture
def raw_dir(tmp_path):
    d = tmp_path / "raw"
    d.mkdir()
    return d


def _manager(raw_dir, **kwargs):
    """Helper de test para construir el manager.

    Por defecto desactiva el gate de espacio libre (`min_free_gb=0.0`): el
    default de producción (5.0 GB) depende de cuánto espacio tenga libre la
    máquina que corre los tests, y `tmp_path` puede caer en un tmpfs chico
    (p. ej. `/tmp` con pocos GB). Los tests que no ejercen el gate no deben
    depender del entorno. El test que sí prueba el gate (`min_free_gb`
    altísimo) lo pasa explícitamente y sobrescribe este default.
    """
    kwargs.setdefault("min_free_gb", 0.0)
    return RecordingManager(
        raw_dir=raw_dir,
        oakd_interpreter=Path(sys.executable),
        oakd_script=SCRIPT_REAL,
        **kwargs,
    )


def _spec(fuente, basename="P1-a-take1", **kwargs):
    return RecordingSpec(
        plugin="rtsp", config={"url": f"file://{fuente}"}, basename=basename, **kwargs
    )


def test_start_stop_deja_master_y_sidecar(raw_dir, fuente):
    manager = _manager(raw_dir)
    manager.start(_spec(fuente))
    time.sleep(2.0)
    resumen = manager.stop()

    master = raw_dir / "P1-a-take1.mp4"
    sidecar = raw_dir / "P1-a-take1.rec.json"
    assert master.exists() and sidecar.exists()
    assert resumen["basename"] == "P1-a-take1"
    assert resumen["truncated"] is False
    data = json.loads(sidecar.read_text())
    assert data["measured"]["resolution"] == "320x240"
    assert data["sha256"]


def test_una_sola_grabacion_activa(raw_dir, fuente):
    manager = _manager(raw_dir)
    manager.start(_spec(fuente))
    try:
        with pytest.raises(RecordingBusy):
            manager.start(_spec(fuente, basename="P1-a-take2"))
    finally:
        manager.stop()


def test_basename_existente_se_rechaza(raw_dir, fuente):
    (raw_dir / "P1-a-take1.mp4").touch()
    manager = _manager(raw_dir)
    with pytest.raises(BasenameTaken):
        manager.start(_spec(fuente))


def test_espacio_insuficiente_se_rechaza_antes_de_grabar(raw_dir, fuente):
    manager = _manager(raw_dir, min_free_gb=10_000_000.0)
    with pytest.raises(GateError):
        manager.start(_spec(fuente))
    assert not (raw_dir / "P1-a-take1.mp4").exists()


def test_status_sin_grabacion_es_idle(raw_dir):
    assert _manager(raw_dir).status()["state"] == "idle"


def test_stop_sin_grabacion_es_error(raw_dir):
    with pytest.raises(RecordingBusy):
        _manager(raw_dir).stop()


def test_corte_automatico_por_max_duration(raw_dir, fuente):
    reloj = {"t": 0.0}
    manager = _manager(raw_dir, clock=lambda: reloj["t"])
    manager.start(_spec(fuente, max_duration_s=5))
    time.sleep(1.0)
    reloj["t"] = 6.0
    estado = manager.status()
    assert estado["state"] == "finished"
    assert estado["truncated"] is True
    assert (raw_dir / "P1-a-take1.mp4").exists()


def test_recover_orphans_muxea_y_marca(raw_dir):
    huerfana = raw_dir / "P9-a-take1.mp4"
    huerfana.write_bytes(b"\x00" * 32)
    recuperadas = _manager(raw_dir).recover_orphans()
    assert recuperadas == ["P9-a-take1"]
    data = json.loads((raw_dir / "P9-a-take1.rec.json").read_text())
    assert data["truncated"] is True


def test_recover_orphans_no_toca_material_ajeno(raw_dir):
    """El directorio se comparte con videos de otra procedencia (lote de internet:
    `4.1.mp4`, `10.1.mp4`). Solo se tocan tomas propias sin sidecar."""
    ajeno = raw_dir / "4.1.mp4"
    ajeno.write_bytes(b"video ajeno que no se toca")
    huerfana = raw_dir / "P9-a-take1.mp4"
    huerfana.write_bytes(b"\x00" * 32)

    recuperadas = _manager(raw_dir).recover_orphans()

    assert recuperadas == ["P9-a-take1"]
    assert ajeno.read_bytes() == b"video ajeno que no se toca"
    assert not (raw_dir / "4.1.rec.json").exists()


def test_recover_orphans_muxea_h264_oakd_y_no_miente_procedencia(raw_dir):
    """Hallazgo IMPORTANT: la rama OAK-D escribe primero <basename>.h264 y recién
    muxea a mp4 al cortar. Si el backend cae en plena toma, antes del fix el
    bucle de *.mp4 "recuperaba" la reserva vacía con plugin="rtsp" hardcodeado
    (procedencia falsa) y el .h264 con el material real quedaba fuera del
    mecanismo, sin sidecar."""
    import subprocess

    raw = raw_dir / "P9-a-take1.h264"
    subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
         "-f", "lavfi", "-i", "testsrc=size=320x240:rate=25:duration=2",
         "-c:v", "libx264", "-preset", "ultrafast", "-f", "h264", str(raw)],
        check=True,
    )
    # La reserva vacía que deja `_reserve()` de start() antes de que el backend
    # caiga.
    (raw_dir / "P9-a-take1.mp4").write_bytes(b"")

    recuperadas = _manager(raw_dir).recover_orphans()

    assert recuperadas == ["P9-a-take1"]
    assert raw.exists()  # el .h264 nunca se borra en el rescate
    mp4 = raw_dir / "P9-a-take1.mp4"
    assert mp4.exists() and mp4.stat().st_size > 0
    data = json.loads((raw_dir / "P9-a-take1.rec.json").read_text())
    assert data["plugin"] == "oak_d"
    assert data["truncated"] is True


def test_recover_orphans_h264_no_muxeable_no_se_borra_ni_miente(raw_dir):
    """Si el muxeo falla (h264 corrupto), el rescate no debe borrar el único
    material de la toma ni afirmar que la grabó una cámara rtsp."""
    raw = raw_dir / "P9-b-take1.h264"
    raw.write_bytes(b"esto no es un elemental h264 valido")
    (raw_dir / "P9-b-take1.mp4").write_bytes(b"")

    recuperadas = _manager(raw_dir).recover_orphans()

    assert recuperadas == ["P9-b-take1"]
    assert raw.exists() and raw.read_bytes() == b"esto no es un elemental h264 valido"
    data = json.loads((raw_dir / "P9-b-take1.rec.json").read_text())
    assert data["plugin"] == "oak_d"
    assert "grabación huérfana" in data["error"]


def test_falla_al_escribir_sidecar_no_tira_500_y_marca_el_problema(
    raw_dir, fuente, monkeypatch
):
    """Hallazgo IMPORTANT: si el disco se llena justo al cerrar, write_sidecar
    puede levantar OSError. Antes del fix, esa excepción cruda atravesaba
    stop() sin protección: el DELETE terminaba en 500 y se perdía el resumen,
    aunque el video ya estuviera en disco."""
    import eovrt_webconsole.recording.manager as manager_mod

    def _sin_espacio(*args, **kwargs):
        raise OSError("No space left on device")

    monkeypatch.setattr(manager_mod, "write_sidecar", _sin_espacio)
    manager = _manager(raw_dir)
    manager.start(_spec(fuente))
    time.sleep(1.0)

    resumen = manager.stop()  # no debe propagar OSError

    assert resumen["state"] == "finished"
    assert resumen["truncated"] is True
    assert "sidecar" in resumen["error"]
    assert (raw_dir / "P1-a-take1.mp4").exists()
    assert not (raw_dir / "P1-a-take1.rec.json").exists()


def test_status_no_propaga_si_un_stop_concurrente_gana_la_carrera(
    raw_dir, fuente, monkeypatch
):
    """status() es de solo lectura y la UI la pollea mientras el operador puede
    apretar Detener. Si el plazo vence, status() suelta el lock antes de llamar a
    stop(); en esa ventana un stop() externo puede cerrar la toma y hacer que el
    stop() interno levante RecordingBusy. status() nunca debe propagarlo.

    La carrera se inyecta de forma determinista haciendo que stop() levante, que
    es exactamente lo que ve status() cuando pierde la carrera (reproducido con
    dos hilos reales en la revisión; acá se fija sin depender del scheduler).
    """
    reloj = {"t": 0.0}
    manager = _manager(raw_dir, clock=lambda: reloj["t"])
    manager.start(_spec(fuente, max_duration_s=5))
    resumen_ganador = {"state": "finished", "basename": "P1-a-take1", "truncated": True}

    def _ya_lo_cerro_otro(self, truncar=False):
        with self._lock:
            self._last = resumen_ganador
        raise RecordingBusy("no hay ninguna grabación activa")

    monkeypatch.setattr(type(manager), "stop", _ya_lo_cerro_otro)
    reloj["t"] = 6.0  # vence el plazo -> status() intenta el corte automático

    estado = manager.status()

    assert estado == resumen_ganador


def test_reserva_se_libera_si_falla_el_arranque(raw_dir, fuente, monkeypatch):
    """Si el grabador no arranca, el archivo vacío de reserva no puede quedar
    bloqueando ese nombre: en pleno rodaje daría 409 sobre una toma que no existe.
    """
    import eovrt_webconsole.recording.manager as manager_mod

    def _explota(self, spec, path):
        raise RuntimeError("el grabador no arrancó")

    monkeypatch.setattr(manager_mod.RecordingManager, "_build_recorder", _explota)
    manager = _manager(raw_dir)

    with pytest.raises(RuntimeError, match="no arrancó"):
        manager.start(_spec(fuente))

    assert not (raw_dir / "P1-a-take1.mp4").exists()
    assert manager.status()["state"] == "idle"
