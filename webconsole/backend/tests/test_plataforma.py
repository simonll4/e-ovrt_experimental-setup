"""La plataforma (plan de la consola de evidencia, §7.1): estado de los trece servicios, orquestación del
núcleo al lado del orquestador (sin tocarlo), guardas y registro de acciones."""
from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from eovrt_webconsole.app import create_app
from eovrt_webconsole.settings import ConsoleSettings
from tests.fake_service import make_fake_service

CONFIG = json.dumps({"services": {
    "console": {"image": "eovrt/console:latest", "ports": [{"target": 8090, "published": "8090"}]},
    "control-plane": {"image": "eovrt/control-plane:latest"},
    "distribution": {"image": "eovrt/alert-distribution:latest"},
    "mosquitto": {"image": "eclipse-mosquitto:2"},
    "mp-mock": {"labels": {"eovrt.instance": "true", "eovrt.model_ref": "mock"}},
    "mp-gdino-tiny-560": {"labels": ["eovrt.instance=true", "eovrt.model_ref=grounding-dino/gdino-tiny-560"]},
}})


def fake_docker(state: dict):
    async def run_cmd(*args: str, cwd: Path):
        state.setdefault("calls", []).append(list(args))
        if args[1] == "inspect":
            return 0, "\n".join(f"/{n} 2026-11-15T10:00:00Z" for n in args[4:]), ""
        verbo = args[4]
        ps = state["ps"]
        if verbo == "config":
            return 0, CONFIG, ""
        if verbo == "ps":
            return 0, "\n".join(json.dumps({
                "Service": n, "Name": f"eovrt-{n}-1", "State": s, "Health": "healthy" if s == "running" else "",
                "Image": "sha256:3f2a" if n == "distribution" else f"img/{n}", "Publishers": [{"TargetPort": 8081, "PublishedPort": 8081}] if n == "control-plane"
                else [{"TargetPort": 8080, "PublishedPort": 0}]}) for n, s in ps.items()), ""
        if verbo == "exec":
            if state.get("sin_gpu"):
                return 1, "", "nvidia-smi: not found"
            return 0, "NVIDIA GeForce RTX 4060 Laptop GPU, 2310, 8188\n", ""
        if verbo == "up":
            ps[args[-1]] = "running"
            return 0, "", ""
        if verbo == "stop":
            ps[args[-1]] = "exited"
            return 0, "", ""
        if verbo == "restart":
            ps[args[-1]] = "running"
            return 0, "", ""
        return 1, "", f"verbo inesperado: {verbo}"
    return run_cmd


@pytest.fixture
def state():
    return {"ps": {"console": "running", "control-plane": "running", "distribution": "exited", "mp-mock": "exited"}}


@pytest.fixture
def cliente(state, fake_state, repo, tmp_path):
    settings = ConsoleSettings(
        service_url="http://ignored", repo_root=repo, frozen_set_ids=frozenset({"frozen_set"}),
        compose_dir=tmp_path, switch_timeout_seconds=1.0,
    )
    app = create_app(settings, service_transport=httpx.ASGITransport(app=make_fake_service(fake_state)),
                     compose_runner=fake_docker(state))
    with TestClient(app) as client:
        yield client


def _verbos(state):
    return [c[4:] for c in state["calls"] if c[1] == "compose" and c[4] in ("up", "stop", "restart")]


def test_el_estado_trae_los_dos_grupos_con_salud_imagen_puerto_y_desde(cliente):
    datos = cliente.get("/api/plataforma").json()
    assert datos["orquestada"] is True
    assert [f["servicio"] for f in datos["nucleo"]] == ["console", "control-plane", "distribution", "mosquitto"]
    rc = datos["nucleo"][1]
    assert (rc["nombre"], rc["estado"], rc["salud"], rc["imagen"], rc["puerto"]) == (
        "Motor de reglas", "running", "healthy", "img/control-plane", "8081")
    assert rc["desde"] == "2026-11-15T10:00:00Z"
    assert datos["nucleo"][3]["estado"] == "ausente"
    # La etiqueta se movió a otra construcción después de crear el contenedor: el nombre declarado y el aviso.
    assert (datos["nucleo"][2]["imagen"], datos["nucleo"][2]["etiqueta_movida"]) == ("eovrt/alert-distribution:latest", True)
    assert datos["nucleo"][1]["etiqueta_movida"] is False
    assert datos["deteccion"][0]["puerto"] == "8080 (red interna)"  # detenida y sin crear: el mismo puerto adentro
    assert [f["servicio"] for f in datos["deteccion"]] == ["mp-gdino-tiny-560", "mp-mock"]
    assert datos["deteccion"][1]["puerto"] == "8080 (red interna)"
    assert datos["gpu"]["disponible"] is False and datos["en_curso"] is None


def test_con_una_instancia_activa_la_destaca_y_lee_la_memoria_de_gpu(cliente, state):
    assert cliente.post("/api/plataforma/servicios/mp-mock/activar").status_code == 200
    datos = cliente.get("/api/plataforma").json()
    assert datos["activa"] == "mp-mock" and datos["deteccion"][0]["servicio"] == "mp-mock"
    assert datos["deteccion"][0]["activa"] is True
    assert datos["gpu"] == {"disponible": True, "instancia": "mp-mock", "nombre": "NVIDIA GeForce RTX 4060 Laptop GPU",
                            "usada_mb": 2310, "total_mb": 8188}
    exec_ = [c for c in state["calls"] if len(c) > 4 and c[4] == "exec"][0]
    assert exec_[4:8] == ["exec", "-T", "mp-mock", "nvidia-smi"]


def test_el_nucleo_se_orquesta_con_verbos_fijos(cliente, state):
    assert cliente.post("/api/plataforma/servicios/distribution/levantar").status_code == 200
    assert cliente.post("/api/plataforma/servicios/control-plane/reiniciar").status_code == 200
    assert cliente.post("/api/plataforma/servicios/control-plane/detener").status_code == 200
    assert _verbos(state) == [["up", "-d", "--no-build", "distribution"], ["restart", "control-plane"],
                              ["stop", "control-plane"]]


def test_fuera_de_la_lista_cerrada_no_se_hace_nada(cliente, state):
    assert cliente.post("/api/plataforma/servicios/redis/levantar").status_code == 422
    assert cliente.post("/api/plataforma/servicios/control-plane/borrar").status_code == 422
    assert cliente.post("/api/plataforma/servicios/mp-mock/reiniciar").status_code == 422
    assert _verbos(state) == []


def test_la_consola_no_se_detiene_a_si_misma(cliente, state):
    r = cliente.post("/api/plataforma/servicios/console/reiniciar")
    assert r.status_code == 409 and r.json()["comando"] == "docker compose --project-name eovrt restart console"
    assert _verbos(state) == []


def test_con_algo_en_curso_detener_pide_confirmacion(cliente, state):
    cliente.app.state.experiment_manager.current = lambda: {"experiment_id": "exp_clip"}
    r = cliente.post("/api/plataforma/servicios/control-plane/detener")
    assert r.status_code == 409 and r.json()["confirmar"] is True and "exp_clip" in r.json()["detail"]
    assert _verbos(state) == []
    assert cliente.post("/api/plataforma/servicios/distribution/levantar").status_code == 200
    r = cliente.post("/api/plataforma/servicios/control-plane/detener", json={"confirmar": True})
    assert r.status_code == 200 and state["ps"]["control-plane"] == "exited"


def test_dejar_lista_levanta_lo_que_falta_y_activa_el_perfil_operativo_sin_recrear(cliente, state):
    r = cliente.post("/api/plataforma/lista")
    assert r.status_code == 200
    assert r.json()["detalle"] == "levantó distribución de alertas; levantó broker mqtt; activó mp-gdino-tiny-560"
    assert ["up", "-d", "--no-build", "control-plane"] not in _verbos(state)
    antes = len(_verbos(state))
    r = cliente.post("/api/plataforma/lista")
    assert r.json()["detalle"] == "ya estaba lista" and len(_verbos(state)) == antes


def test_cada_pedido_queda_en_el_registro(cliente, state):
    cliente.post("/api/plataforma/servicios/distribution/levantar")
    state["ps"].pop("mosquitto", None)
    cliente.post("/api/plataforma/servicios/mp-mock/detener")
    acciones = cliente.get("/api/plataforma").json()["acciones"]
    assert [(a["accion"], a["servicio"], a["resultado"]) for a in acciones][-1] == ("levantar", "distribution", "ok")


def test_en_nativo_muestra_que_no_hay_orquestacion(client):
    datos = client.get("/api/plataforma").json()
    assert datos["orquestada"] is False and datos["nucleo"] == []
    assert client.post("/api/plataforma/lista").status_code == 422
