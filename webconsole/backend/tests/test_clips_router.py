import shutil
import subprocess
from pathlib import Path

import httpx
import pytest
import yaml
from fastapi.testclient import TestClient

from eovrt_webconsole.app import create_app
from eovrt_webconsole.settings import ConsoleSettings
from tests.fake_service import FakeState, make_fake_service

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
def dv(tmp_path):
    """Repo datasets falso con la forma que prepare_clip.sh espera."""
    root = tmp_path / "dsrepo"
    dv = root / "datasets-videos"
    (dv / "raw").mkdir(parents=True)
    (dv / "clips").mkdir()
    (dv / "preann").mkdir()
    script = root / "datasets" / "scripts" / "videogt" / "prepare_clip.sh"
    script.parent.mkdir(parents=True)
    shutil.copy(REAL_SCRIPT, script)
    return dv


@pytest.fixture
def master(dv):
    out = dv / "raw" / "P1-a-take1.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
         "-f", "lavfi", "-i", "testsrc=size=320x240:rate=30:duration=20",
         "-c:v", "libx264", "-preset", "ultrafast", str(out)],
        check=True,
    )
    return out


@pytest.fixture
def clips_client(repo: Path, dv, fake_state: FakeState):
    settings = ConsoleSettings(
        service_url="http://service.fake",
        repo_root=repo,
        frozen_set_ids=frozenset(),
        recordings_dir=dv / "raw",
        datasets_videos_dir=dv,
    )
    transport = httpx.ASGITransport(app=make_fake_service(fake_state))
    with TestClient(create_app(settings, service_transport=transport)) as client:
        client.dv = dv
        yield client


def test_lista_de_masters(clips_client, master):
    body = clips_client.get("/api/clips/masters").json()
    [m] = body["masters"]
    assert m["name"] == "P1-a-take1.mp4"
    assert m["scenario"] == "P1"
    assert m["readable"] is True
    assert m["clips"] == []


def test_generar_clip_de_punta_a_punta(clips_client, master):
    creado = clips_client.post(
        "/api/clips",
        json={"master": "P1-a-take1.mp4", "marks": [6.0, 12.0]},
    )
    assert creado.status_code == 201, creado.text
    body = creado.json()
    assert body["clip_id"] == "a_p1_c01"
    # ventana: ss=2.5, duración=(12+3)-2.5=12.5 s a 30 fps
    assert abs(body["info"]["n_frames"] - 375) <= 1
    # advertencia de duración P1 (<20 s), generado igual (D7)
    assert any("20" in w for w in body["warnings"])
    assert (clips_client.dv / "clips" / "a_p1_c01.mp4").exists()
    data = yaml.safe_load((clips_client.dv / "a_p1_c01.clip.yaml").read_text())
    assert data["episode_draft"][0]["onset_ms"] == 3500
    # y ahora el master figura recortado y el clip listado:
    [m] = clips_client.get("/api/clips/masters").json()["masters"]
    assert m["clips"] == ["a_p1_c01"]
    [c] = clips_client.get("/api/clips").json()["clips"]
    assert c["clip_id"] == "a_p1_c01"


def test_fin_antes_del_evento_da_422(clips_client, master):
    r = clips_client.post(
        "/api/clips",
        json={"master": "P1-a-take1.mp4", "marks": [12.0, 6.0]},
    )
    assert r.status_code == 422
    assert "posterior" in r.json()["detail"]


def test_master_ilegible_da_422_con_motivo(clips_client, dv):
    (dv / "raw" / "P2-a-take1.mp4").write_bytes(b"esto no es un mp4")
    r = clips_client.post(
        "/api/clips",
        json={"master": "P2-a-take1.mp4", "marks": [5.0, 8.0]},
    )
    assert r.status_code == 422


def test_media_master_soporta_range(clips_client, master):
    r = clips_client.get(
        "/api/clips/media/master/P1-a-take1.mp4", headers={"Range": "bytes=0-99"}
    )
    assert r.status_code == 206
    assert len(r.content) == 100
    assert r.headers["content-range"].startswith("bytes 0-99/")


def test_media_clip_tras_generar(clips_client, master):
    clips_client.post(
        "/api/clips",
        json={"master": "P1-a-take1.mp4", "marks": [6.0, 12.0]},
    )
    r = clips_client.get("/api/clips/media/clip/a_p1_c01")
    assert r.status_code == 200
    assert r.headers["content-type"] == "video/mp4"


def test_media_inexistente_y_traversal_dan_404(clips_client):
    assert clips_client.get("/api/clips/media/master/no-esta.mp4").status_code == 404
    assert (
        clips_client.get("/api/clips/media/master/..%2F..%2Fetc%2Fpasswd").status_code
        == 404
    )


def test_payload_invalido_da_422(clips_client, master):
    r = clips_client.post("/api/clips", json={"master": "P1-a-take1.mp4"})
    assert r.status_code == 422


def test_marcas_con_longitud_invalida_da_422(clips_client, master):
    r = clips_client.post(
        "/api/clips",
        json={"master": "P1-a-take1.mp4", "marks": [6.0, 12.0, 20.0]},
    )
    assert r.status_code == 422
