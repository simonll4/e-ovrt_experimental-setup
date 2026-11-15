"""«Tomas en vivo» (plan de la consola, §6): las sesiones guardadas, agrupadas por la prueba en la que
cuentan. Disco local, de solo lectura."""
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from eovrt_webconsole.demo.sesion import SesionDesconocida
from eovrt_webconsole.tomas_en_vivo import TomasEnVivo

router = APIRouter(prefix="/api/tomas")


@router.get("")
def tomas(request: Request) -> dict:
    manager = getattr(request.app.state, "demo_manager", None)
    if manager is None:
        raise HTTPException(status_code=503, detail="La demo no está inicializada")

    def carpeta(session_id: str) -> Path | None:
        try:
            return manager._dir_sesion(session_id)
        except SesionDesconocida:
            return None

    return TomasEnVivo(request.app.state.gen2.resultados_dir, manager.sesiones, carpeta).vista()
