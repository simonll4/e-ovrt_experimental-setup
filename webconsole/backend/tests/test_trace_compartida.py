"""`/trace` y `/trace/index` salen juntas al abrir un run: la lectura se hace una vez."""
import asyncio
from types import SimpleNamespace

from eovrt_webconsole.routers.runs import _gather_trace


class _Media:
    def __init__(self):
        self.status_llamadas = 0
        self.en_vuelo = 0
        self.maximo = 0

    async def status(self, run_id):
        self.status_llamadas += 1
        await asyncio.sleep(0.02)
        return {"run_id": run_id, "summary": {}}

    async def _pagina(self, run_id, page, page_size):
        self.en_vuelo += 1
        self.maximo = max(self.maximo, self.en_vuelo)
        await asyncio.sleep(0.02)
        self.en_vuelo -= 1
        return {"items": [], "total": 0}

    async def detections(self, run_id, page, page_size):
        return await self._pagina(run_id, page, page_size)

    async def dropped(self, run_id, page, page_size):
        return await self._pagina(run_id, page, page_size)


class _Control:
    def __init__(self):
        self.en_vuelo = 0
        self.maximo = 0

    async def _lectura(self, valor):
        self.en_vuelo += 1
        self.maximo = max(self.maximo, self.en_vuelo)
        await asyncio.sleep(0.02)
        self.en_vuelo -= 1
        return valor

    async def list_runs(self, media_run_id):
        return [{"control_run_id": "c1"}]

    async def pattern_progress(self, cid):
        return await self._lectura([])

    async def alerts(self, cid):
        return await self._lectura([])

    async def pattern_events(self, cid):
        return await self._lectura([])

    async def received_units(self, cid):
        return await self._lectura([])


def _request():
    media, control = _Media(), _Control()
    estado = SimpleNamespace(backend=media, control_backend=control, trace_en_vuelo={})
    return SimpleNamespace(app=SimpleNamespace(state=estado)), media, control


async def test_dos_pedidos_simultaneos_comparten_una_sola_lectura():
    request, media, _ = _request()
    (a, _), (b, _) = await asyncio.gather(
        _gather_trace("run1", request, None), _gather_trace("run1", request, None)
    )
    assert media.status_llamadas == 1
    # Cada consumidor recibe su copia: /trace hace pop("frames") y no debe afectar al otro.
    a.pop("frames")
    assert "frames" in b
    assert request.app.state.trace_en_vuelo == {}


async def test_corridas_distintas_no_se_comparten():
    request, media, _ = _request()
    await asyncio.gather(_gather_trace("run1", request, None), _gather_trace("run2", request, None))
    assert media.status_llamadas == 2


async def test_las_lecturas_independientes_van_en_paralelo():
    request, media, control = _request()
    await _gather_trace("run1", request, None)
    assert media.maximo == 2  # detecciones y descartes juntas
    assert control.maximo == 4  # progreso, alertas, eventos y unidades juntas
