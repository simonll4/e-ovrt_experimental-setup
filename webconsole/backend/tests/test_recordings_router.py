import shutil
import subprocess
import time
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from eovrt_webconsole.app import create_app
from eovrt_webconsole.settings import ConsoleSettings
from tests.fake_service import FakeState, make_fake_service

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="requiere ffmpeg y ffprobe en el sistema",
)


@pytest.fixture(autouse=True)
def _sin_rtsp_transport_para_file(monkeypatch):
    """El input de prueba es `file://`, no un DVR real.

    `build_ffmpeg_args` de producción siempre agrega `-rtsp_transport tcp`,
    opción privada del demuxer rtsp que ffmpeg 8.0.1 rechaza con "Option not
    found" si el input es `file://` (nunca ocurre en producción: ahí solo se
    graba `rtsp(s)://` real). Mismo parche que `test_recording_manager.py`.
    """
    import eovrt_webconsole.recording.ffmpeg_recorder as recorder_mod

    def _args_file_para_test(url: str, out_path) -> list[str]:
        return [
            "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
            "-re",
            "-i", str(url),
            "-c", "copy",
            "-movflags", "+faststart",
            "-y",
            str(out_path),
        ]

    monkeypatch.setattr(recorder_mod, "build_ffmpeg_args", _args_file_para_test)


@pytest.fixture(autouse=True)
def _sin_gate_de_espacio(monkeypatch):
    """El gate de espacio libre (5.0 GB default) depende de cuánto tenga libre
    la máquina que corre los tests (p. ej. `/tmp` como tmpfs chico) y no debe
    hacer flakear estos tests. Se desactiva igual que en `_manager()` de
    `test_recording_manager.py`, pero acá el RecordingManager lo instancia
    `app.py` en el lifespan, así que se parchea la función del gate en vez de
    pasar un kwarg.
    """
    import eovrt_webconsole.recording.manager as manager_mod

    monkeypatch.setattr(manager_mod, "check_free_space", lambda *a, **k: None)


@pytest.fixture
def fuente(tmp_path):
    out = tmp_path / "fuente.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
         "-f", "lavfi", "-i", "testsrc=size=320x240:rate=25:duration=20",
         "-c:v", "libx264", "-preset", "ultrafast", "-g", "25", str(out)],
        check=True,
    )
    return out


@pytest.fixture
def rec_client(repo: Path, tmp_path: Path, fake_state: FakeState, fuente):
    raw = tmp_path / "raw"
    raw.mkdir()
    (repo / "cameras").mkdir(exist_ok=True)
    (repo / "cameras" / "dvr_test.yaml").write_text(
        "camera:\n"
        "  id: dvr_test\n"
        "  name: DVR de prueba\n"
        "  plugin: rtsp\n"
        f"  config: {{ url: 'file://{fuente}' }}\n"
    )
    settings = ConsoleSettings(
        service_url="http://service.fake",
        repo_root=repo,
        frozen_set_ids=frozenset(),
        recordings_dir=raw,
    )
    transport = httpx.ASGITransport(app=make_fake_service(fake_state))
    with TestClient(create_app(settings, service_transport=transport)) as client:
        client.raw_dir = raw
        yield client


def test_next_propone_el_primer_take(rec_client):
    body = rec_client.get("/api/recordings/next?scenario=P1&variant=a").json()
    assert body["basename"] == "P1-a-take1"


def test_next_rechaza_escenario_invalido(rec_client):
    assert rec_client.get("/api/recordings/next?scenario=P0&variant=a").status_code == 422


def test_estado_inicial_es_idle(rec_client):
    assert rec_client.get("/api/recordings").json()["state"] == "idle"


def test_ciclo_completo_por_camera_id(rec_client):
    creado = rec_client.post(
        "/api/recordings", json={"camera_id": "dvr_test", "scenario": "P1", "variant": "a"}
    )
    assert creado.status_code == 201
    assert creado.json()["basename"] == "P1-a-take1"

    time.sleep(2.0)
    assert rec_client.get("/api/recordings").json()["state"] == "recording"

    final = rec_client.delete("/api/recordings")
    assert final.status_code == 200
    assert final.json()["truncated"] is False
    assert (rec_client.raw_dir / "P1-a-take1.mp4").exists()
    assert (rec_client.raw_dir / "P1-a-take1.rec.json").exists()


def test_segunda_grabacion_da_409(rec_client):
    rec_client.post(
        "/api/recordings", json={"camera_id": "dvr_test", "scenario": "P1", "variant": "a"}
    )
    try:
        conflicto = rec_client.post(
            "/api/recordings", json={"camera_id": "dvr_test", "scenario": "P1", "variant": "b"}
        )
        assert conflicto.status_code == 409
    finally:
        rec_client.delete("/api/recordings")


def test_camera_inexistente_da_404(rec_client):
    respuesta = rec_client.post(
        "/api/recordings", json={"camera_id": "no-existe", "scenario": "P1", "variant": "a"}
    )
    assert respuesta.status_code == 404


def test_preview_activo_en_el_media_plane_da_409(rec_client, fake_state):
    # Corrección al brief: FakeState no tiene atributo `preview`; el estado real
    # del preview vive en `preview_status` ("idle"/"streaming", ver fake_service.py).
    # check_media_plane_free lee GET /api/preview -> {"status": ..., "preview_id": ...}
    # y como el fake siempre devuelve preview_id=None, el ocupante queda "preview:None".
    fake_state.preview_status = "streaming"
    respuesta = rec_client.post(
        "/api/recordings", json={"camera_id": "dvr_test", "scenario": "P1", "variant": "a"}
    )
    assert respuesta.status_code == 409
    assert "preview" in respuesta.json()["detail"]


def test_delete_sin_grabacion_da_409(rec_client):
    assert rec_client.delete("/api/recordings").status_code == 409


def test_config_invalido_no_filtra_credenciales_en_el_422(rec_client):
    """Hallazgo MINOR: si `config` llega como string en vez de objeto, el
    mensaje de validación de pydantic incluye el valor recibido tal cual. Si ese
    string es una URL rtsp con credenciales, el 422 las devolvía en claro."""
    respuesta = rec_client.post(
        "/api/recordings",
        json={
            "plugin": "rtsp",
            "config": "rtsp://admin:supersecreta@192.168.1.50/live",
            "basename": "P1-a-take1",
        },
    )
    assert respuesta.status_code == 422
    detalle = str(respuesta.json()["detail"])
    assert "supersecreta" not in detalle
    assert "***:***@" in detalle
