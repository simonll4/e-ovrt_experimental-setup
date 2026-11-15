"""Las diez figuras del informe (plan de la consola, §8). Disco local, de solo lectura."""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from eovrt_webconsole.figuras import FiguraInexistente

router = APIRouter(prefix="/api/figuras")


@router.get("")
def figuras(request: Request) -> dict:
    return request.app.state.figuras.vista()


@router.get("/{figura_id}/imagen")
def imagen(figura_id: str, request: Request) -> FileResponse:
    try:
        ruta = request.app.state.figuras.imagen(figura_id)
    except FiguraInexistente as exc:
        raise HTTPException(404, "Esa figura no existe o todavía no se generó") from exc
    return FileResponse(ruta, media_type="image/png")
