import json

import pytest

from eovrt_webconsole.recording.occupancy import check_media_plane_free
from eovrt_webconsole.run_backend import ServiceUnavailable, UnknownRun


class _Backend:
    def __init__(self, preview=None, runs=None, falla=False, excepcion=None):
        self._preview = preview or {"status": "idle", "preview_id": None}
        self._runs = runs or []
        self._falla = falla
        self._excepcion = excepcion or ServiceUnavailable("media-plane caído")

    async def preview_status(self):
        if self._falla:
            raise self._excepcion
        return self._preview

    async def list_runs(self):
        if self._falla:
            raise self._excepcion
        return self._runs


@pytest.mark.asyncio
async def test_media_plane_libre():
    assert await check_media_plane_free(_Backend()) is None


@pytest.mark.asyncio
async def test_preview_activo_ocupa():
    backend = _Backend(preview={"status": "streaming", "preview_id": "pv_ab12"})
    assert await check_media_plane_free(backend) == "preview:pv_ab12"


@pytest.mark.asyncio
async def test_run_activo_ocupa():
    backend = _Backend(runs=[{"run_id": "r_991", "status": "running"}])
    assert await check_media_plane_free(backend) == "run:r_991"


@pytest.mark.asyncio
@pytest.mark.parametrize("terminal", ["succeeded", "failed", "stopped"])
async def test_run_terminado_no_ocupa(terminal):
    """Los tres estados terminales REALES del media-plane (run_manager.py).
    El doble de test tiene que hablar su vocabulario: un terminal inventado
    pasaría por estar fuera de _RUN_ACTIVO, sin probar nada del contrato."""
    backend = _Backend(runs=[{"run_id": "r_990", "status": terminal}])
    assert await check_media_plane_free(backend) is None


@pytest.mark.asyncio
async def test_media_plane_caido_no_bloquea(caplog):
    assert await check_media_plane_free(_Backend(falla=True)) is None
    assert "media-plane" in caplog.text.lower()


@pytest.mark.asyncio
async def test_media_plane_404_no_bloquea(caplog):
    """run_backend.RunBackend._get_json levanta UnknownRun ante un 404 (p. ej.
    una versión del media-plane sin /api/preview). Antes del fix, occupancy.py
    solo capturaba ServiceUnavailable: esta excepción atravesaba el chequeo, el
    router la dejaba escapar sin manejar y POST /api/recordings terminaba en
    500 -- la regla del diseño es que grabar nunca depende de este servicio."""
    backend = _Backend(falla=True, excepcion=UnknownRun("/api/preview"))
    assert await check_media_plane_free(backend) is None
    assert "media-plane" in caplog.text.lower()


@pytest.mark.asyncio
async def test_media_plane_respuesta_no_json_no_bloquea(caplog):
    """Un 200 con cuerpo no-JSON hace que response.json() de httpx levante
    json.JSONDecodeError dentro de _get_json: otra forma de "no pude
    preguntar" que antes del fix no estaba cubierta."""
    backend = _Backend(falla=True, excepcion=json.JSONDecodeError("msg", "doc", 0))
    assert await check_media_plane_free(backend) is None
    assert "media-plane" in caplog.text.lower()
