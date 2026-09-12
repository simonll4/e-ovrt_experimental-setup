"""Runs: lanzar (compose→launch), listar hidratado, estado y stop (Spec B §5.5/§6)."""
from __future__ import annotations

import logging
import re
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse
from starlette.background import BackgroundTask

from eovrt_webconsole.evidence import (
    CLASES,
    Vista,
    cabeceras_de_disponibilidad,
    coincide_vista,
)
from eovrt_webconsole.evidence_archive import etiqueta
from eovrt_webconsole.experiment.control_backend import (
    RunActive as ControlRunActive,
)
from eovrt_webconsole.experiment.control_backend import (
    ServiceUnavailable as ControlServiceUnavailable,
)
from eovrt_webconsole.experiment.control_backend import (
    UnknownRun as ControlUnknownRun,
)
from eovrt_webconsole.routers.compose import validate_composition
from eovrt_webconsole.run_backend import (
    RunActive,
    RunBusy,
    RunNotFinished,
    ServiceRejected,
    ServiceUnavailable,
    UnknownRun,
)
from eovrt_webconsole.trace import build_trace_index, compose_trace, filtrar_frames
from eovrt_webconsole.translation import Composition, composition_to_run_request

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/runs")

_FORWARD_HEADERS = {"content-type", "content-length", "content-range", "accept-ranges"}


_RUN_ID_FECHA = re.compile(r"^run_(\d{8})_(\d{6})")


def _created_at(info: dict) -> str | None:
    """Cuándo se creó la corrida, en ISO-8601 UTC.

    `started_at` solo viene en las filas hidratadas, así que el listado tenía
    corridas con fecha y corridas sin fecha, y ordenarlo obligaba al cliente a
    reconstruirla parseando el `run_id`. El identificador es determinístico
    (`run_AAAAMMDD_HHMMSS_...`), así que la reconstrucción se hace acá una vez y
    el campo viaja siempre.
    """
    started_at = info.get("started_at") or (info.get("summary") or {}).get("started_at")
    if started_at:
        return started_at
    match = _RUN_ID_FECHA.match(info.get("run_id") or "")
    if not match:
        return None
    fecha, hora = match.groups()
    try:
        return datetime.strptime(
            f"{fecha}{hora}", "%Y%m%d%H%M%S"
        ).replace(tzinfo=UTC).isoformat()
    except ValueError:
        return None


def _row(info: dict) -> dict:
    summary = info.get("summary") or {}
    return {
        "run_id": info.get("run_id"),
        "created_at": _created_at(info),
        "name": info.get("name") or summary.get("name"),
        "status": info.get("status", "unknown"),
        "model": info.get("model") or summary.get("model_name"),
        "source_type": summary.get("source_type"),
        "prompt_set_id": summary.get("prompt_set_id"),
        "fps_effective": summary.get("fps_effective"),
        "total_detections": summary.get("total_detections"),
        "duration_seconds": summary.get("duration_seconds"),
        "started_at": info.get("started_at") or summary.get("started_at"),
        "bench_split": info.get("bench_split"),
        "evaluated": info.get("evaluated"),
        "live": info.get("live", False),
        "topology": (summary.get("run_descriptor") or {}).get("topology"),
    }


@router.post("", status_code=201)
async def launch(comp: Composition, request: Request):
    settings = request.app.state.settings
    backend = request.app.state.backend
    errors = await validate_composition(comp, settings, backend)
    if errors:
        return JSONResponse(status_code=422, content={"errors": errors})
    run_request = composition_to_run_request(comp, settings.prompts_dir)
    try:
        run_id = await backend.launch(run_request)
    except RunBusy as exc:
        content = {"detail": exc.detail, "active_run_id": exc.active_run_id}
        if exc.reason is not None:
            content["reason"] = exc.reason
        return JSONResponse(status_code=409, content=content)
    except ServiceRejected as exc:
        logger.warning("launch: el servicio rechazó la composición: %s", exc.detail)
        return JSONResponse(
            status_code=422, content={"errors": [{"field": "_service", "message": str(exc.detail)}]}
        )
    except ServiceUnavailable as exc:
        logger.warning("launch: servicio inaccesible: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    logger.info(
        "launch: plugin=%s dataset=%s prompt_set=%s -> run_id=%s",
        comp.ingest.plugin,
        comp.ingest.config.get("dataset"),
        comp.prompts.set_id,
        run_id,
    )
    return {"run_id": run_id}


# Campos por los que se puede ordenar. `created_at`, `name` y `status` salen del
# listado base; el resto necesita hidratar la fila, así que ordenar por ellos
# cuesta una lectura por corrida (acotada por `hydration_limit`).
_ORDENABLES = {
    "created_at", "name", "status", "model",
    "fps_effective", "total_detections", "duration_seconds",
}


def _coincide(fila: dict, q: str) -> bool:
    texto = f"{fila.get('run_id') or ''} {fila.get('name') or ''}".lower()
    return q in texto


def _clave_de_orden(fila: dict, campo: str):
    """Clave `(no_tiene_valor, valor)`, con el texto normalizado a minúsculas.

    El primer elemento separa las filas con valor de las que no lo tienen; quién
    va al final lo decide `_ordenar()`, no esta función.
    """
    valor = fila.get(campo)
    if valor is None:
        return (1, "")
    if isinstance(valor, str):
        return (0, valor.lower())
    return (0, valor)


def _ordenar(filas: list[dict], campo: str, direccion: str) -> None:
    """Ordena en el lugar dejando los nulos al final en las DOS direcciones.

    Son dos pasadas y no una porque `reverse=True` invierte la clave entera,
    incluido el indicador de "tiene valor": ordenando por una métrica de forma
    descendente, las corridas fallidas —que tienen casi todas las métricas en
    null— encabezaban el listado, que es exactamente lo contrario de lo que
    busca quien ordena por esa métrica. Como `list.sort` es estable, la segunda
    pasada empuja los nulos al final sin alterar el orden de la primera.
    """
    filas.sort(key=lambda r: _clave_de_orden(r, campo), reverse=(direccion == "desc"))
    filas.sort(key=lambda r: _clave_de_orden(r, campo)[0])


@router.get("")
async def list_runs(
    request: Request,
    response: Response,
    estado: str | None = Query(default=None, description="running | succeeded | failed | stopped"),
    q: str | None = Query(default=None, description="Busca en el identificador y el nombre"),
    orden: str = Query(default="created_at"),
    direccion: str = Query(default="desc", pattern="^(asc|desc)$"),
    pagina: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    vista: Vista = "todas",
    clase: str | None = Query(
        default=None, description="resultado | instrumento | ensayo | plataforma | sin_clasificar"
    ),
    result_id: str | None = Query(default=None, description="Sólo las corridas que citan este resultado"),
) -> list[dict]:
    """Listado de corridas, filtrado, ordenado y paginado del lado del servidor.

    La respuesta sigue siendo una lista (el contrato de antes) y el total va en
    la cabecera `X-Total-Count`: envolverlo en un objeto habría roto a todos los
    consumidores por un dato que la paginación necesita al margen.

    El filtro se aplica ANTES de hidratar, así que buscar entre cien corridas ya
    no cuesta cien lecturas al motor de detección: solo se hidrata la página que
    se va a devolver (o el conjunto filtrado, si el orden pedido depende de un
    campo que solo existe hidratado).
    """
    settings = request.app.state.settings
    backend = request.app.state.backend
    try:
        base = await backend.list_runs()
    except ServiceUnavailable as exc:
        logger.warning("list_runs: servicio inaccesible: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    registry = request.app.state.evidence
    evidence = {r["run_id"]: registry.describe([r["run_id"]]) for r in base}
    response.headers.update(cabeceras_de_disponibilidad(registry))
    response.headers["X-Archived-Count"] = str(sum(
        not evidence[r["run_id"]]["is_evidence"] for r in base
    ))
    base = [r for r in base if coincide_vista(evidence[r["run_id"]], vista)]
    if clase:
        base = [r for r in base if evidence[r["run_id"]]["clase"] == clase]
    if result_id:
        base = [r for r in base if result_id in evidence[r["run_id"]]["result_ids"]]

    if estado:
        base = [r for r in base if r.get("status") == estado]
    if q:
        aguja = q.strip().lower()
        base = [r for r in base if _coincide(r, aguja)]

    total = len(base)
    response.headers["X-Total-Count"] = str(total)

    campo = orden if orden in _ORDENABLES else "created_at"
    inicio = (pagina - 1) * page_size

    if campo in ("created_at", "name", "status"):
        # Ordenable sin hidratar: se ordena todo y se hidrata solo la página.
        for fila in base:
            fila.setdefault("created_at", _created_at(fila))
        _ordenar(base, campo, direccion)
        seleccion = base[inicio : inicio + page_size]
        return [dict(await _hidratar(backend, item), evidence=evidence[item["run_id"]])
                for item in seleccion]

    # Orden por una métrica: hay que hidratar antes de poder comparar. Se acota
    # con `hydration_limit` para no disparar una lectura por corrida sobre un
    # historial largo; las que quedan afuera van al final, sin métricas.
    hidratadas = [await _hidratar(backend, item) for item in base[: settings.hydration_limit]]
    resto = [_fila_flaca(item) for item in base[settings.hydration_limit :]]
    _ordenar(hidratadas, campo, direccion)
    return [dict(row, evidence=evidence[row["run_id"]])
            for row in (hidratadas + resto)[inicio : inicio + page_size]]


# `/grupos` tiene que registrarse ANTES de `GET /{run_id}`: Starlette matchea en
# el orden de alta, y un segmento estático después de uno dinámico de un solo
# path param nunca se alcanza (`/{run_id}` se comería `/grupos` con
# run_id="grupos"). Por eso vive acá y no más abajo, cerca de `run_comparison`.
def _cifra_de_grupo(archive, result_id: str | None) -> dict:
    """La cifra del paso que cita `result_id`, o declarada ausente.

    Nunca se calcula una cifra propia acá: instrumento, ensayo, plataforma y
    los resultados que sólo sostienen el respaldo (no un paso del argumento) no
    tienen paso -> no tienen cifra, y eso se DICE (`None`), no se dibuja como
    cero ni se inventa.
    """
    info = archive.paso_de(result_id) if result_id else None
    if info is None:
        return {"cifra": None, "cifra_label": None, "cifra_origen": None, "fuente": None, "paso": None}
    return {"cifra": info["cifra"], "cifra_label": info["cifra_label"],
            "cifra_origen": info["cifra_origen"], "fuente": info["fuente"], "paso": info["n"]}


@router.get("/grupos")
async def list_grupos(
    request: Request, response: Response, clase: str | None = None
) -> list[dict]:
    """Las corridas colapsadas en sus resultados de respaldo.

    El filtro de clase casi no reduce el LISTADO plano (412 de 472 corridas son
    'resultado'): lo que lo hace legible es agrupar, no filtrar. Acá 472
    corridas quedan en unas pocas decenas de grupos.

    Una corrida que es evidencia de DOS resultados aparece en los DOS grupos:
    la suma de `n_runs` es mayor al total de corridas, y ese total nunca se
    deriva sumando esta lista — se lee de `X-Total-Count` en `GET /api/runs`.

    Por lo mismo viaja `X-Class-Counts`: los conteos por clase son de corridas
    DISTINTAS —exactamente lo que devuelve `GET /api/runs?clase=…`—, y sumarlos
    del lado del cliente sobre `n_runs` cuenta CITACIONES (693 contra 412 en la
    plataforma real, un número mayor que el total). Se calculan acá, en el mismo
    handler, sobre el listado completo: un chip tiene que decir cuántas filas
    trae su filtro, no cuántas veces se las cita.
    """
    registry = request.app.state.evidence
    archive = request.app.state.evidence_archive
    backend = request.app.state.backend
    try:
        base = await backend.list_runs()
    except ServiceUnavailable as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    # Antes de filtrar: los chips son siempre globales. Se emiten las cinco
    # clases, cero incluido — un cero medido es un dato, no un dato ausente.
    conteos = dict.fromkeys(CLASES, 0)
    response.headers.update(cabeceras_de_disponibilidad(registry))

    grupos: dict[str | None, dict] = {}
    for fila in base:
        descripcion = registry.describe([fila["run_id"]])
        conteos[descripcion["clase"]] += 1
        claves = descripcion["result_ids"] or [None]
        for clave in claves:
            # `if clave not in grupos` en vez de `grupos.setdefault(clave, {...})`:
            # el segundo argumento de `setdefault` se evalúa SIEMPRE, en cada
            # corrida del grupo — incluida `_cifra_de_grupo`, que para una cifra
            # leída abre y parsea `metrics.json` sin caché. Con esto se abre una
            # sola vez por grupo, no una por corrida.
            if clave not in grupos:
                grupos[clave] = {
                    "result_id": clave,
                    "titulo": archive.titles.get(clave) if clave else "Fuera del registro de evidencia",
                    # El fallback de nombre lo calcula el backend, con la ÚNICA
                    # `etiqueta()` que existe (`evidence_archive.py`): antes el
                    # frontend tenía una segunda copia que partía por el ÚLTIMO
                    # `/` en vez del primero, y las dos se desviaban en cuanto
                    # un result_id tuviera más de un separador.
                    "etiqueta": etiqueta(clave) if clave else None,
                    "clase": descripcion["clase"],
                    "n_runs": 0,
                    "last_run_at": None,
                    **_cifra_de_grupo(archive, clave),
                }
            grupo = grupos[clave]
            # La clase del grupo es la MÁS FUERTE entre TODAS las corridas que lo
            # citan, con la misma precedencia de `CLASES` que usa `EvidenceRegistry`
            # en `describe()`/`ejecucion()` — no la de la primera corrida procesada
            # (`descripcion["clase"]` es la clase de la corrida entera, no de su rol
            # específico en `clave`, así que puede variar de una corrida a otra).
            if CLASES.index(descripcion["clase"]) < CLASES.index(grupo["clase"]):
                grupo["clase"] = descripcion["clase"]
            grupo["n_runs"] += 1
            creado = _created_at(fila)
            if creado and (grupo["last_run_at"] is None or creado > grupo["last_run_at"]):
                grupo["last_run_at"] = creado

    response.headers["X-Class-Counts"] = ",".join(f"{c}={n}" for c, n in conteos.items())
    filas = list(grupos.values())
    if clase:
        filas = [g for g in filas if g["clase"] == clase]
    return sorted(filas, key=lambda g: (g["last_run_at"] or ""), reverse=True)


def _fila_flaca(item: dict) -> dict:
    """Fila sin hidratar: lo que el listado base ya sabe, sin métricas."""
    return {
        "run_id": item["run_id"],
        "created_at": _created_at(item),
        "name": item.get("name"),
        "status": item["status"],
        "bench_split": item.get("bench_split"),
        "evaluated": item.get("evaluated"),
        "live": item.get("live", False),
    }


async def _hidratar(backend, item: dict) -> dict:
    try:
        return _row(await backend.status(item["run_id"]))
    except (UnknownRun, ServiceUnavailable):
        # La corrida desapareció entre el listado y la lectura, o el servicio se
        # cayó a mitad: se devuelve lo que ya se sabía en vez de perder la fila.
        return _fila_flaca(item)




# Qué hace "comparable" a dos corridas. Comparar contra la corrida anterior a
# secas no sirve: si cambió el modelo o el conjunto de prompts, la variación no
# mide una mejora, mide que se cambió el experimento.
_EJES_DE_COMPARACION = ("model", "prompt_set_id", "source_type")

# Métricas cuya variación se muestra en los indicadores. `mejor` dice hacia dónde
# es bueno moverse, para que la interfaz pueda pintar el delta sin repetir esta
# tabla: más cuadros por segundo es mejor, más latencia es peor.
_METRICAS_COMPARABLES = {
    "fps_effective": "mas",
    "total_detections": None,   # ni bueno ni malo: depende de la escena
    "duration_seconds": None,
    "p50_latency_ms": "menos",
    "p95_latency_ms": "menos",
    "gpu_memory_peak_mb": "menos",
}


def _metricas_de(info: dict) -> dict[str, float | None]:
    summary = info.get("summary") or {}
    return {
        clave: (summary.get(clave) if isinstance(summary.get(clave), (int, float)) else None)
        for clave in _METRICAS_COMPARABLES
    }


@router.get("/{run_id}/comparison")
async def run_comparison(run_id: str, request: Request) -> dict:
    """La corrida anterior comparable y la variación de cada indicador.

    Los indicadores del detalle muestran "+0,3 vs la corrida anterior", y para
    eso hace falta saber cuál es esa corrida. "La anterior" a secas no sirve: si
    entre las dos cambió el modelo o el conjunto de prompts, la variación no
    mide una mejora sino un cambio de experimento. Se compara contra la última
    corrida terminada que coincide en modelo, conjunto de prompts y tipo de
    fuente.

    Sin candidata devuelve `previous_run_id: null` y sin deltas, que la interfaz
    muestra como indicadores sin variación — no como variación cero.
    """
    backend = request.app.state.backend
    try:
        actual = await backend.status(run_id)
    except UnknownRun as exc:
        raise HTTPException(status_code=404, detail=f"Run desconocido: {run_id}") from exc
    except ServiceUnavailable as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    fila_actual = _row(actual)
    creada_actual = fila_actual.get("created_at") or ""

    try:
        base = await backend.list_runs()
    except ServiceUnavailable as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    candidatas = [
        item for item in base
        if item.get("run_id") != run_id and item.get("status") == "succeeded"
    ]
    # De la más nueva a la más vieja: la primera que coincida en los tres ejes y
    # sea anterior a la actual es la que se busca.
    candidatas.sort(key=lambda item: _created_at(item) or "", reverse=True)

    previa = None
    for item in candidatas:
        if (_created_at(item) or "") >= creada_actual:
            continue
        try:
            detalle = await backend.status(item["run_id"])
        except (UnknownRun, ServiceUnavailable):
            continue
        fila = _row(detalle)
        if all(fila.get(eje) == fila_actual.get(eje) for eje in _EJES_DE_COMPARACION):
            previa = detalle
            break

    if previa is None:
        return {
            "run_id": run_id,
            "previous_run_id": None,
            "matched_on": list(_EJES_DE_COMPARACION),
            "deltas": {},
        }

    actuales, anteriores = _metricas_de(actual), _metricas_de(previa)
    deltas = {}
    for clave, mejor in _METRICAS_COMPARABLES.items():
        ahora, antes = actuales[clave], anteriores[clave]
        if ahora is None or antes is None:
            continue
        deltas[clave] = {
            "current": ahora,
            "previous": antes,
            "delta": round(ahora - antes, 4),
            "better": mejor,
        }

    return {
        "run_id": run_id,
        "previous_run_id": previa.get("run_id"),
        "matched_on": list(_EJES_DE_COMPARACION),
        "deltas": deltas,
    }


@router.get("/{run_id}")
async def get_run(run_id: str, request: Request) -> dict:
    try:
        return await request.app.state.backend.status(run_id)
    except UnknownRun as exc:
        raise HTTPException(status_code=404, detail=f"Run desconocido: {run_id}") from exc
    except ServiceUnavailable as exc:
        logger.warning("get_run(%s): servicio inaccesible: %s", run_id, exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/{run_id}/stop", status_code=202)
async def stop_run(run_id: str, request: Request) -> dict:
    try:
        await request.app.state.backend.stop(run_id)
    except UnknownRun as exc:
        raise HTTPException(status_code=404, detail=f"Run desconocido: {run_id}") from exc
    except ServiceUnavailable as exc:
        logger.warning("stop_run(%s): servicio inaccesible: %s", run_id, exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    logger.info("stop_run: solicitado stop de run_id=%s", run_id)
    return {"run_id": run_id, "stopping": True}


@router.delete("/{run_id}", status_code=204)
async def delete_run(run_id: str, request: Request):
    backend = request.app.state.backend
    control = request.app.state.control_backend

    media_gone = False
    try:
        media_status = await backend.status(run_id)
    except UnknownRun:
        media_gone = True
    except ServiceUnavailable as exc:
        logger.warning("delete_run(%s): servicio media inaccesible: %s", run_id, exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    else:
        if media_status.get("status") == "running":
            raise HTTPException(status_code=409, detail="No se puede borrar un run activo")

    try:
        candidates = await control.list_runs(media_run_id=run_id)
    except ControlServiceUnavailable as exc:
        logger.warning(
            "delete_run(%s): control-plane inaccesible al resolver correlación: %s", run_id, exc
        )
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    control_run_ids = [item["control_run_id"] for item in candidates]

    if media_gone and not control_run_ids:
        raise HTTPException(status_code=404, detail=f"Run desconocido: {run_id}")

    for control_run_id in control_run_ids:
        try:
            control_status = await control.status(control_run_id)
        except ControlUnknownRun:
            continue
        except ControlServiceUnavailable as exc:
            logger.warning("delete_run(%s): control-plane inaccesible: %s", run_id, exc)
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        if control_status.get("status") == "running":
            raise HTTPException(
                status_code=409, detail=f"No se puede borrar: {control_run_id} sigue activo"
            )

    # Orden de borrado (finding de la revisión final): control-plane PRIMERO,
    # media-plane AL FINAL — y el borrado de media SOLO se intenta si el lado
    # control terminó sin errores. La visibilidad de la UI (RunsPage/
    # RunDetailPage) se nutre enteramente del media-plane, así que dejar media
    # como lo último en tocarse, y condicionado al éxito de control, garantiza
    # que ante CUALQUIER falla parcial el run siga visible para reintentar:
    # si control falla, media NI SE INTENTA (sigue existiendo, visible); si
    # control tiene éxito pero media falla, el borrado quedó incompleto y el
    # run también sigue visible (no se borró). Solo cuando ambos lados
    # terminan bien el run desaparece de la UI, que es lo correcto. Con el
    # orden inverso (media primero, sin gating), una falla del lado control
    # (el endpoint más nuevo, menos probado) dejaba el run invisible en la UI
    # sin forma de reintentar, pese a que control seguía huérfano.
    errors: dict[str, str] = {}
    control_errors: list[str] = []
    for control_run_id in control_run_ids:
        try:
            await control.delete(control_run_id)
        except ControlUnknownRun:
            continue
        except ControlRunActive as exc:
            control_errors.append(exc.detail)
        except ControlServiceUnavailable as exc:
            control_errors.append(str(exc))
    if control_errors:
        errors["control"] = "; ".join(control_errors)

    if not control_errors and not media_gone:
        try:
            await backend.delete(run_id)
        except UnknownRun:
            pass
        except RunActive as exc:
            errors["media"] = exc.detail
        except ServiceUnavailable as exc:
            errors["media"] = str(exc)

    if errors:
        logger.warning("delete_run(%s): borrado parcial: %s", run_id, errors)
        return JSONResponse(status_code=207, content={"detail": "borrado parcial", "errors": errors})
    logger.info("delete_run: run_id=%s borrado en ambos planos", run_id)
    return Response(status_code=204)


@router.post("/{run_id}/evaluate")
async def evaluate_run(run_id: str, request: Request):
    try:
        return await request.app.state.backend.evaluate(run_id)
    except UnknownRun as exc:
        raise HTTPException(status_code=404, detail=f"Run desconocido: {run_id}") from exc
    except RunNotFinished as exc:
        return JSONResponse(status_code=409, content={"detail": exc.detail})
    except ServiceRejected as exc:
        return JSONResponse(
            status_code=422,
            content={"errors": [{"field": "_service", "message": str(exc.detail)}]},
        )
    except ServiceUnavailable as exc:
        logger.warning("evaluate(%s): servicio inaccesible: %s", run_id, exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/{run_id}/evaluate")
async def get_evaluation(run_id: str, request: Request):
    try:
        return await request.app.state.backend.get_evaluation(run_id)
    except UnknownRun as exc:
        raise HTTPException(status_code=404, detail=f"Run no evaluado: {run_id}") from exc
    except ServiceUnavailable as exc:
        logger.warning("get_evaluation(%s): servicio inaccesible: %s", run_id, exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/{run_id}/detections")
async def detections(
    run_id: str,
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000),
) -> dict:
    try:
        return await request.app.state.backend.detections(run_id, page=page, page_size=page_size)
    except UnknownRun as exc:
        raise HTTPException(status_code=404, detail=f"Sin detecciones para: {run_id}") from exc
    except ServiceUnavailable as exc:
        logger.warning("detections(%s): servicio inaccesible: %s", run_id, exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc


async def _fetch_all(fetch, run_id: str) -> list[dict]:
    """Pagina un endpoint del media-plane (detections/dropped) hasta traer
    todas las filas (trampa de volumen del spec §7: sin esto, el trace solo
    vería la primera página)."""
    items: list[dict] = []
    page = 1
    page_size = 1000
    while True:
        result = await fetch(run_id, page=page, page_size=page_size)
        if not result["items"]:
            break
        items.extend(result["items"])
        if len(items) >= result["total"]:
            break
        page += 1
    return items


async def _gather_trace(
    run_id: str, request: Request, control_run_id: str | None
) -> tuple[dict, str | None]:
    """Junta las cuatro fuentes y compone la traza completa.

    Lo comparten `/trace` (que después pagina) y `/trace/index` (que proyecta el
    índice de la línea de tiempo): las dos necesitan exactamente la misma
    lectura, y tenerla duplicada garantizaba que se desincronizaran.
    """
    backend = request.app.state.backend
    control = request.app.state.control_backend
    try:
        summary = await backend.status(run_id)
    except UnknownRun as exc:
        raise HTTPException(status_code=404, detail=f"Run desconocido: {run_id}") from exc
    except ServiceUnavailable as exc:
        logger.warning("trace(%s): servicio media inaccesible: %s", run_id, exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    # Trae TODAS las paginas de detections y dropped (page_size=1000, loop hasta total).
    # UnknownRun en cualquiera de las dos lecturas se tolera como lista vacia: el
    # run ya fue validado por status() arriba, asi que un 404 puntual de detections
    # o dropped no debe tumbar el trace (I2 del review).
    try:
        detections_rows = await _fetch_all(backend.detections, run_id)
    except UnknownRun:
        detections_rows = []
    except ServiceUnavailable as exc:
        logger.warning("trace(%s): servicio media inaccesible (detections): %s", run_id, exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    try:
        dropped_rows = await _fetch_all(backend.dropped, run_id)
    except UnknownRun:
        dropped_rows = []
    except ServiceUnavailable as exc:
        logger.warning("trace(%s): servicio media inaccesible (dropped): %s", run_id, exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    # Lado control: best-effort (degradacion del spec §6). ControlUnknownRun en
    # el lookup o en las lecturas se trata como "sin control run" (no 404 del
    # trace); ControlServiceUnavailable puebla control_error y deja todo en n/d.
    progress, alerts, pattern_events, received, control_error = [], [], [], None, None
    try:
        if control_run_id is None:
            candidates = await control.list_runs(media_run_id=run_id)
            control_run_id = candidates[0]["control_run_id"] if candidates else None
        if control_run_id is not None:
            progress = await control.pattern_progress(control_run_id)
            alerts = await control.alerts(control_run_id)
            pattern_events = await control.pattern_events(control_run_id)
            received = {u["unit_id"] for u in await control.received_units(control_run_id)}
    except ControlServiceUnavailable as exc:
        logger.warning("trace(%s): servicio control inaccesible: %s", run_id, exc)
        control_error = str(exc)
        control_run_id, progress, alerts, pattern_events, received = None, [], [], [], None
    except ControlUnknownRun:
        control_run_id, progress, alerts, pattern_events, received = None, [], [], [], None
    topology = ((summary.get("summary") or {}).get("run_descriptor") or {}).get("topology")
    composed = compose_trace(
        detections=detections_rows, dropped=dropped_rows, progress=progress, alerts=alerts,
        pattern_events=pattern_events,
        received_unit_ids=received, control_run_id=control_run_id,
        topology=topology,
    )
    return composed, control_error


@router.get("/{run_id}/trace")
async def trace(
    run_id: str,
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000),
    control_run_id: str | None = Query(default=None),
    solo: str | None = Query(
        default=None,
        pattern="^(actividad|alertas)$",
        description="Filtra los cuadros antes de paginar",
    ),
) -> dict:
    composed, control_error = await _gather_trace(run_id, request, control_run_id)
    frames = filtrar_frames(composed.pop("frames"), solo)
    start = (page - 1) * page_size
    return {
        "media_run_id": run_id,
        **composed,
        "control_error": control_error,
        "page": page,
        "page_size": page_size,
        # Total del conjunto FILTRADO: es lo que la lista tiene que paginar.
        # `totals.frames` sigue siendo el de la corrida entera.
        "total": len(frames),
        "frames": frames[start : start + page_size],
    }


@router.get("/{run_id}/trace/index")
async def trace_index(
    run_id: str,
    request: Request,
    control_run_id: str | None = Query(default=None),
) -> dict:
    """Actividad de la corrida completa, en una sola respuesta.

    Sin esto la línea de tiempo tenía que paginar `/trace` hasta 40 veces para
    poder dibujarse.
    """
    composed, control_error = await _gather_trace(run_id, request, control_run_id)
    return {
        "media_run_id": run_id,
        **build_trace_index(composed),
        "control_error": control_error,
    }


# Declarada ANTES de la ruta con `{artifact_path:path}`: Starlette matchea por
# orden de registro, y `:path` acepta el segmento vacío.
@router.get("/{run_id}/artifacts")
async def artifacts_index(run_id: str, request: Request) -> dict:
    backend = request.app.state.backend
    try:
        return await backend.list_artifacts(run_id)
    except UnknownRun as exc:
        raise HTTPException(status_code=404, detail=f"Run desconocido: {run_id}") from exc
    except ServiceUnavailable as exc:
        logger.warning("artifacts_index(%s): servicio inaccesible: %s", run_id, exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/{run_id}/artifacts/{artifact_path:path}")
async def artifact(run_id: str, artifact_path: str, request: Request):
    backend = request.app.state.backend
    try:
        upstream = await backend.open_artifact(
            run_id, artifact_path, range_header=request.headers.get("range")
        )
    except ServiceUnavailable as exc:
        logger.warning("artifact(%s, %s): servicio inaccesible: %s", run_id, artifact_path, exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if upstream.status_code == 404:
        await upstream.aclose()
        raise HTTPException(status_code=404, detail="Artefacto no encontrado")
    headers = {k: v for k, v in upstream.headers.items() if k.lower() in _FORWARD_HEADERS}
    return StreamingResponse(
        upstream.aiter_bytes(),
        status_code=upstream.status_code,  # 200 o 206 (Range) del servicio
        headers=headers,
        background=BackgroundTask(upstream.aclose),
    )
