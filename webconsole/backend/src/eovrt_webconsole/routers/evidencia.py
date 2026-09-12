"""Los tres niveles de evidencia, leídos exclusivamente del disco local."""
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, Request

router = APIRouter(prefix="/api/evidencia")


@router.get("")
def index(request: Request) -> dict:
    return request.app.state.evidence_archive.recorrido()


@router.get("/paso")
def paso(request: Request, n: Annotated[int, Query(ge=1)]) -> dict:
    try:
        return request.app.state.evidence_archive.paso(n)
    except KeyError as exc:
        raise HTTPException(404, "Ese paso del recorrido no existe") from exc


@router.get("/resultado")
def result(
    request: Request, id: str,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 25,
) -> dict:
    try:
        return request.app.state.evidence_archive.result(id, page, page_size)
    except KeyError as exc:
        raise HTTPException(404, "Resultado fuera del registro de evidencia") from exc
    except ValueError as exc:
        raise HTTPException(400, "Referencia de evidencia inválida") from exc


@router.get("/run")
def run(request: Request, plane: Literal["media-plane", "control-plane"], run_id: str) -> dict:
    try:
        return request.app.state.evidence_archive.run(plane, run_id)
    except KeyError as exc:
        raise HTTPException(404, "Corrida fuera del registro de evidencia") from exc
    except (ValueError, OSError) as exc:
        raise HTTPException(400, "No se pudo leer el artefacto curado") from exc
