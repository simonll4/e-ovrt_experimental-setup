"""La documentación de la consola. Disco local, cero clientes de servicios."""
from fastapi import APIRouter, Request

router = APIRouter(prefix="/api/documentacion")


@router.get("")
def index(request: Request) -> dict:
    return request.app.state.documentacion.payload()
