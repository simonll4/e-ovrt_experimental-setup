"""La evidencia de la generación 2 (doc 135). Disco local, cero clientes de servicios."""
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse

from eovrt_webconsole.gen2 import ArchivoNoServible, PruebaInexistente

router = APIRouter(prefix="/api/gen2")


@router.get("/observaciones")
def observaciones(request: Request) -> dict:
    return request.app.state.gen2.observaciones()


@router.get("/pruebas")
def pruebas(request: Request) -> list[dict]:
    return request.app.state.gen2.pruebas()


@router.get("/pruebas/{prueba_id}")
def prueba(prueba_id: str, request: Request) -> dict:
    try:
        return request.app.state.gen2.prueba(prueba_id)
    except PruebaInexistente as exc:
        raise HTTPException(404, "Esa prueba no está en el catálogo de la generación 2") from exc


@router.get("/pruebas/{prueba_id}/archivo")
def archivo(prueba_id: str, request: Request, ruta: str = Query(min_length=1)) -> FileResponse:
    try:
        path, media_type = request.app.state.gen2.archivo(prueba_id, ruta)
    except ArchivoNoServible as exc:
        raise HTTPException(404, "Ese archivo no existe o no se sirve") from exc
    return FileResponse(path, media_type=media_type)
