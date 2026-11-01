"""Hidratar la página de corridas no es una lectura por fila en serie."""
import asyncio

from eovrt_webconsole.routers.runs import _hidratar_todas


class _Backend:
    def __init__(self, caidas=()):
        self.en_vuelo = 0
        self.maximo = 0
        self.caidas = set(caidas)

    async def status(self, run_id):
        from eovrt_webconsole.run_backend import UnknownRun

        self.en_vuelo += 1
        self.maximo = max(self.maximo, self.en_vuelo)
        await asyncio.sleep(0.01)
        self.en_vuelo -= 1
        if run_id in self.caidas:
            raise UnknownRun(run_id)
        return {"run_id": run_id, "status": "succeeded", "summary": {}}


async def test_las_lecturas_son_concurrentes_y_conservan_el_orden():
    backend = _Backend()
    items = [{"run_id": f"r{i}"} for i in range(40)]
    filas = await _hidratar_todas(backend, items)
    assert [f["run_id"] for f in filas] == [f"r{i}" for i in range(40)]
    assert backend.maximo > 1


async def test_la_concurrencia_esta_acotada():
    backend = _Backend()
    await _hidratar_todas(backend, [{"run_id": f"r{i}"} for i in range(100)], limite=8)
    assert 1 < backend.maximo <= 8


async def test_una_corrida_que_desaparecio_devuelve_la_fila_flaca_sin_perder_las_demas():
    backend = _Backend(caidas={"r1"})
    filas = await _hidratar_todas(backend, [{"run_id": r, "status": "succeeded"} for r in ("r0", "r1", "r2")])
    assert [f["run_id"] for f in filas] == ["r0", "r1", "r2"]
