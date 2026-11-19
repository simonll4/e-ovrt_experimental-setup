"""La evidencia de la generación 2 (doc 135). Disco local, cero clientes de servicios."""
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse, Response

from eovrt_webconsole.clips_de_prueba import ClipNoDisponible
from eovrt_webconsole.gen2 import ArchivoNoServible, PruebaInexistente

router = APIRouter(prefix="/api/gen2")


# «Mostrame un run donde pasó esto»: un clip de una prueba, con su referencia, sus alertas, sus cuadros y su video.
# Van antes de `/pruebas/{prueba_id}` solo por claridad: las rutas tienen más segmentos y no se pisan.
@router.get("/pruebas/ERR-01/falsas-alarmas")
def falsas_alarmas_err01(request: Request) -> dict:
    return request.app.state.clips.falsas_alarmas_err01()


@router.get("/pruebas/{prueba_id}/clips/{clip}")
def clip(prueba_id: str, clip: str, request: Request, lectura: str | None = Query(None)) -> dict:
    try:
        return request.app.state.clips.clip(prueba_id, clip, lectura or None)
    except ClipNoDisponible as exc:
        raise HTTPException(404, "Ese clip no está en esa prueba") from exc


@router.get("/pruebas/{prueba_id}/clips/{clip}/cuadro/{cuadro}")
def cuadro(prueba_id: str, clip: str, cuadro: int, request: Request, lectura: str | None = Query(None),
           alerta: str | None = Query(None), acercar: bool = Query(False)) -> Response:
    try:
        imagen = request.app.state.clips.cuadro(prueba_id, clip, cuadro, lectura or None, alerta or None, acercar)
    except ClipNoDisponible as exc:
        raise HTTPException(404, "Ese cuadro no se puede mostrar en este equipo") from exc
    return Response(imagen, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=3600"})


@router.get("/pruebas/{prueba_id}/clips/{clip}/video")
def video(prueba_id: str, clip: str, request: Request) -> FileResponse:
    try:
        ruta = request.app.state.clips.video(prueba_id, clip)
    except ClipNoDisponible as exc:
        raise HTTPException(404, "Ese clip no está en esa prueba") from exc
    if ruta is None:
        raise HTTPException(404, "El video de ese clip no está en este equipo")
    return FileResponse(ruta, media_type="video/mp4")


@router.get("/pruebas")
def pruebas(request: Request) -> list[dict]:
    return request.app.state.gen2.pruebas()


@router.get("/pruebas/{prueba_id}")
def prueba(prueba_id: str, request: Request) -> dict:
    try:
        return request.app.state.gen2.prueba(prueba_id)
    except PruebaInexistente as exc:
        raise HTTPException(404, "Esa prueba no está en el catálogo") from exc


@router.get("/pruebas/{prueba_id}/archivo")
def archivo(prueba_id: str, request: Request, ruta: str = Query(min_length=1)) -> FileResponse:
    try:
        path, media_type = request.app.state.gen2.archivo(prueba_id, ruta)
    except ArchivoNoServible as exc:
        raise HTTPException(404, "Ese archivo no existe o no se sirve") from exc
    return FileResponse(path, media_type=media_type)
