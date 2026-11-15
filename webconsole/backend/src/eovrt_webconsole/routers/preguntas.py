"""La portada y las siete preguntas de la consola (plan de la consola, §2 y §9). Disco local."""
from fastapi import APIRouter, Request

router = APIRouter(prefix="/api/preguntas")


@router.get("")
def preguntas(request: Request) -> dict:
    return request.app.state.preguntas.vista()
