"""Demo: el ciclo completo de una sesión con los servicios simulados (spec 2026-10-23 §8).

preparing → live (primer cuadro procesado) → alerta → mensaje en el testigo → F F →
cierre en cascada (media stopped → control cierra → distribución cierra) → render →
done, con ended_by operator. Más el chequeo previo y los bordes.
"""
from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from eovrt_webconsole.demo.sesion import DemoManager, DemoNoLista, DemoOcupada, DemoSinSesion
from eovrt_webconsole.experiment.run_manager import ExperimentRunManager
from eovrt_webconsole.settings import ConsoleSettings
from tests.demo_fixtures import MODELO_OK, repo_demo
from tests.test_demo_testigo import FakeBroker


class FakeMedia:
    """media-plane: corre hasta que lo detienen (como la OAK-D, sin max_units)."""

    def __init__(self) -> None:
        self.lanzadas: list[dict] = []
        self.detenidas: list[str] = []
        self.runs_en_disco = {"run_viejo"}

    async def launch(self, run_request: dict) -> str:
        self.lanzadas.append(run_request)
        self.runs_en_disco.add("run_demo")
        return "run_demo"

    async def status(self, run_id: str) -> dict:
        return {"run_id": run_id, "status": "stopped" if run_id in self.detenidas else "running"}

    async def stop(self, run_id: str) -> None:
        self.detenidas.append(run_id)

    async def list_runs(self) -> list[dict]:
        return [{"run_id": r, "status": "running" if r == "run_demo" and r not in self.detenidas
                 else "stopped"} for r in sorted(self.runs_en_disco)]


class FakeControl:
    """control-plane live: cierra cuando el media se detuvo (su run_finished)."""

    def __init__(self, media: FakeMedia) -> None:
        self.media = media
        self.lanzadas: list[tuple[dict, str]] = []
        self.unidades = 0
        self.episodios: list[dict] = []

    async def launch(self, config: dict, mode: str, experiment_id: str | None) -> str:
        self.lanzadas.append((config, mode))
        return "ctl_demo"

    def _cerrado(self) -> bool:
        return "run_demo" in self.media.detenidas

    async def status(self, control_run_id: str) -> dict:
        return {"control_run_id": control_run_id,
                "status": "succeeded" if self._cerrado() else "running"}

    async def current(self) -> dict:
        if self._cerrado():
            raise RuntimeError("404: no hay run activo")
        return {"control_run_id": "ctl_demo", "subscribed": True,
                "progress": {"units_processed": self.unidades, "bus_dropped_events": 0},
                "episodes": self.episodios}


def _transport(rutas: dict[str, tuple[int, object]]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        status, body = rutas.get(request.url.path, (404, {"detail": "no"}))
        return httpx.Response(status, json=body)

    return httpx.MockTransport(handler)


async def _esperar(condicion, timeout: float = 5.0) -> None:
    limite = time.monotonic() + timeout
    while not condicion():
        if time.monotonic() > limite:
            raise AssertionError("la condición no se cumplió a tiempo")
        await asyncio.sleep(0.01)


@pytest.fixture
def entorno(tmp_path):
    repo = repo_demo(tmp_path)
    settings = ConsoleSettings(
        service_url="http://localhost:8080", repo_root=repo, frozen_set_ids=frozenset(),
        experiment_poll_interval_s=0.01,
    )
    media = FakeMedia()
    control = FakeControl(media)
    broker = FakeBroker()
    dist_rutas = {"/healthz": (200, {"status": "ok"})}
    state = SimpleNamespace(
        settings=settings,
        http=httpx.AsyncClient(base_url="http://media", transport=_transport({
            "/healthz": (200, {}), "/readyz": (200, {}), "/api/model": (200, MODELO_OK),
        })),
        control_http=httpx.AsyncClient(base_url="http://control", transport=_transport({
            "/healthz": (200, {}),
        })),
        distribution_http=httpx.AsyncClient(base_url="http://dist", transport=_transport(dist_rutas)),
        backend=media,
        control_backend=control,
        experiment_manager=ExperimentRunManager(),
        target_manager=None,
    )
    app = SimpleNamespace(state=state)
    sesiones = repo / "defensa" / "sesiones"
    sesiones.mkdir(parents=True)
    (sesiones / "preflight_host.json").write_text(json.dumps({"chequeos": {}}))
    run_dirs = tmp_path / "planos"

    distribucion_cerro = asyncio.Event()

    async def fake_distribucion(*, out_dir: Path, **kwargs) -> dict:
        # Cierra con el run_finished que el control republica: acá, cuando el control cerró.
        while not control._cerrado():
            await asyncio.sleep(0.01)
        out_dir.mkdir(parents=True, exist_ok=True)
        summary = {"schema_version": "control.distribution_summary.v1", "counts": {"delivered": 1},
                   "source_stats": {"read": 1, "skipped_malformed": 0},
                   "talert_notification_ms": None}
        (out_dir / "distribution_summary.json").write_text(json.dumps(summary))
        distribucion_cerro.set()
        return summary

    renders: list[dict] = []

    def fake_render(salida: Path, **kwargs) -> dict:
        renders.append({"salida": salida, **kwargs})
        salida.mkdir(parents=True, exist_ok=True)
        resumen = {"video": None, "cuadros_clave": [], "errores": [], "faltantes": []}
        (salida / "resumen.json").write_text(json.dumps(resumen))
        return resumen

    dm = DemoManager(
        app, sesiones_dir=sesiones, poll_s=0.01,
        testigo_factory=lambda host, port: __import__(
            "eovrt_webconsole.demo.testigo", fromlist=["TestigoMqtt"]
        ).TestigoMqtt(host, port, client_factory=broker.cliente),
        ping=lambda host, port: {"ok": True, "rtt_ms": 1.0, "detalle": "ok"},
        render=fake_render, telemetria=False, run_distribution=fake_distribucion,
        resolve_run_dir=lambda plane, run_id: run_dirs / plane / run_id,
        dest_root=tmp_path / "runs", cierre_timeout_s=2.0, espera_fin_s=5.0,
    )
    return SimpleNamespace(dm=dm, app=app, media=media, control=control, broker=broker,
                           renders=renders, sesiones=sesiones, dist_rutas=dist_rutas,
                           distribucion_cerro=distribucion_cerro)


async def test_preflight_nativo_todo_verde_salvo_el_motor_en_amarillo(entorno):
    pf = await entorno.dm.preflight()
    por_id = {i["id"]: i["estado"] for i in pf["items"]}
    assert por_id["motor"] == "aviso"  # nativo: la consola no puede verificarlo
    assert all(v == "ok" for k, v in por_id.items() if k != "motor"), pf["items"]
    assert pf["listo"] is True
    assert pf["congelado"]["ok"] is True
    assert pf["stack"] == "nativo"


async def test_preflight_con_broker_caido_bloquea(entorno):
    entorno.dm._ping = lambda host, port: {"ok": False, "rtt_ms": None, "detalle": "no volvió"}
    pf = await entorno.dm.preflight()
    assert pf["listo"] is False
    assert {i["id"] for i in pf["items"] if i["estado"] == "error"} == {"broker"}
    with pytest.raises(DemoNoLista):
        await entorno.dm.start("oakd")


async def test_preflight_host_viejo_es_amarillo_y_no_bloquea(entorno):
    viejo = time.time() - 3600
    path = entorno.sesiones / "preflight_host.json"
    import os

    os.utime(path, (viejo, viejo))
    pf = await entorno.dm.preflight()
    host = next(i for i in pf["items"] if i["id"] == "host")
    assert host["estado"] == "aviso" and pf["listo"] is True


async def test_preflight_corrida_del_control_colgada_bloquea(entorno):
    entorno.app.state.control_http = httpx.AsyncClient(base_url="http://control", transport=_transport({
        "/healthz": (200, {}), "/api/runs/current": (200, {"control_run_id": "ctl_viejo"}),
    }))
    pf = await entorno.dm.preflight()
    reglas = next(i for i in pf["items"] if i["id"] == "reglas")
    assert reglas["estado"] == "error" and "ctl_viejo" in reglas["detalle"]


async def test_ciclo_completo_hasta_el_resultado(entorno):
    dm, media, control = entorno.dm, entorno.media, entorno.control
    inicio = await dm.start("oakd")
    sid = inicio["session_id"]
    carpeta = entorno.sesiones / sid
    assert (carpeta / "config" / "media.yaml").is_file()
    assert (carpeta / "preflight.json").is_file()

    # Orden real: control → distribución → medios (el control en live, suscripto).
    await _esperar(lambda: media.lanzadas)
    assert control.lanzadas[0][1] == "live"
    # El runner habilita el bus sin pisar la espera al suscriptor (slow joiner).
    assert media.lanzadas[0]["bus"] == {"wait_for_subscriber_ms": 10000, "enabled": True}
    assert media.lanzadas[0]["ingest"]["plugin"] == "oak_d"
    assert dm.estado()["fase"] == "preparing"
    await _esperar(lambda: dm.estado()["ids"].get("media_run_id") == "run_demo")

    # «Listo» = el primer cuadro procesado que llega al control.
    control.unidades = 1
    await _esperar(lambda: dm.estado()["fase"] == "live")

    control.episodios = [{"condition_id": "CR-01", "state": "candidate", "elapsed_ms": 2100.0,
                          "confirm_after_ms": 4000.0, "clear_elapsed_ms": None,
                          "resolve_after_ms": 2000.0, "severity": "high"}]
    await _esperar(lambda: dm.estado()["condiciones"][0]["estado"] == "confirmando")
    control.episodios = [{**control.episodios[0], "state": "confirmed", "elapsed_ms": 4100.0}]
    await _esperar(lambda: dm.estado()["condiciones"][0]["estado"] == "alerta")
    assert dm.estado()["condiciones"][0]["broker"] == "esperando"

    payload = {"alert_id": "al-1", "condition_id": "CR-01", "control_run_id": "ctl_demo",
               "confirmed_wall_ms": time.time() * 1000}
    entorno.broker.publicar("eovrt/alerts/high", json.dumps(payload).encode())
    await _esperar(lambda: dm.estado()["condiciones"][0]["broker"] == "recibido")
    assert dm.estado()["broker"]["ultimo"]["topic"] == "eovrt/alerts/high"

    # F F: cierre por el operador, en cascada.
    fin = await dm.finish()
    assert fin["fase"] == "finishing"
    await _esperar(lambda: dm.estado()["fase"] in {"done", "failed"})
    estado = dm.estado()
    assert estado["fase"] == "done", estado["error"]
    assert estado["ended_by"] == "operator"
    assert media.detenidas == ["run_demo"]
    assert entorno.distribucion_cerro.is_set()

    sesion = json.loads((carpeta / "session.json").read_text())
    assert sesion["fase"] == "done" and sesion["ended_by"] == "operator"
    assert sesion["experimento"]["ended_by"] == "operator"
    assert sesion["experimento"]["status"] == "succeeded"
    assert sesion["congelado"]["ok"] is True
    assert (carpeta / "witness.jsonl").read_text().strip()
    assert len((carpeta / "state_log.jsonl").read_text().splitlines()) > 3
    (render,) = entorno.renders
    assert render["media_dir"].name == "run_demo" and render["control_dir"].name == "ctl_demo"
    assert render["testigo"][0]["payload"]["alert_id"] == "al-1"

    detalle = dm.sesion(sid)
    assert detalle["session"]["session_id"] == sid
    assert detalle["resumen"] == {"video": None, "cuadros_clave": [], "errores": [], "faltantes": []}


async def test_finish_sin_sesion_es_error(entorno):
    with pytest.raises(DemoSinSesion):
        await entorno.dm.finish()


async def test_no_arranca_con_un_experimento_en_curso(entorno):
    entorno.app.state.experiment_manager._active_id = "exp_otro"
    entorno.app.state.experiment_manager._states["exp_otro"] = {"status": "running"}
    with pytest.raises(DemoOcupada):
        await entorno.dm.start("oakd")


async def test_no_arranca_dos_sesiones(entorno):
    await entorno.dm.start("oakd")
    with pytest.raises(DemoOcupada):
        await entorno.dm.start("oakd")
    await entorno.dm.finish()
    await _esperar(lambda: entorno.dm.estado()["fase"] in {"done", "failed"})


async def test_cierre_vencido_deja_failed_y_arma_el_resultado_igual(entorno):
    """El control no cierra nunca (el run del control no se puede cancelar, doc 68):
    vence el cierre, la sesión queda failed y el Resultado se arma con lo que haya."""
    dm, control = entorno.dm, entorno.control
    control._cerrado = lambda: False  # nunca cierra
    await dm.start("oakd")
    await _esperar(lambda: entorno.media.lanzadas)
    control.unidades = 1
    await _esperar(lambda: dm.estado()["fase"] == "live")
    await dm.finish()
    await _esperar(lambda: dm.estado()["fase"] in {"done", "failed"}, timeout=15.0)
    assert dm.estado()["fase"] == "failed"
    assert entorno.renders, "el Resultado se arma igual"
    assert entorno.app.state.experiment_manager.current() is None  # el slot quedó libre


async def test_motor_compose_desconocido_bloquea_hasta_reiniciar(entorno):
    reinicios = []

    class FakeTarget:
        active = "mp-gdino-tiny-560"

        async def restart_active(self):
            reinicios.append(1)
            return {"target": "mp-gdino-tiny-560", "model_ref": MODELO_OK["ref"]}

        async def contenedores(self):
            return [{"Service": "console", "State": "running"}]

    entorno.app.state.target_manager = FakeTarget()
    entorno.app.state.settings = ConsoleSettings(
        service_url="http://localhost:8080", repo_root=entorno.app.state.settings.repo_root,
        frozen_set_ids=frozenset(), experiment_poll_interval_s=0.01,
        compose_dir=entorno.app.state.settings.repo_root / "infra" / "platform",
    )
    pf = await entorno.dm.preflight()
    motor = next(i for i in pf["items"] if i["id"] == "motor")
    assert motor["estado"] == "error" and pf["listo"] is False

    await entorno.dm.reiniciar_motor()
    assert reinicios == [1]
    pf = await entorno.dm.preflight()
    assert next(i for i in pf["items"] if i["id"] == "motor")["estado"] == "ok"
    assert pf["listo"] is True

    # Una corrida nueva en el motor (de cualquier origen) lo deja usado.
    entorno.media.runs_en_disco.add("run_de_otro")
    pf = await entorno.dm.preflight()
    assert next(i for i in pf["items"] if i["id"] == "motor")["estado"] == "error"

    stack = await entorno.dm.stack()
    assert stack["modo"] == "compose" and stack["contenedores"][0]["Service"] == "console"
    assert {r["repo"] for r in stack["repos"]} >= {"e-ovrt_control-plane", "e-ovrt_media-plane"}
    assert all(r["url_tag"].endswith("/tree/informe-2026") for r in stack["repos"])


async def test_frescura_del_motor_por_el_runs_compartido(entorno, tmp_path):
    """Con el `runs/` del media-plane visible (paridad de rutas) se lista el directorio
    en vez de pedirle al motor el summary de cada corrida."""
    runs = tmp_path / "planos" / "media"
    (runs / "run_a").mkdir(parents=True)

    class FakeTarget:
        active = "mp-gdino-tiny-560"

        async def restart_active(self):
            return {"target": "mp-gdino-tiny-560", "model_ref": MODELO_OK["ref"]}

    entorno.app.state.target_manager = FakeTarget()
    entorno.media.list_runs = None  # si se usara la API, explotaría
    await entorno.dm.reiniciar_motor()
    assert (await entorno.dm.estado_motor())["estado"] == "fresco"
    (runs / "run_b").mkdir()
    motor = await entorno.dm.estado_motor()
    assert motor["estado"] == "usado" and motor["corridas_desde_reinicio"] == ["run_b"]


async def test_respaldo_y_archivos_con_guarda_de_ruta(entorno):
    dm = entorno.dm
    await dm.start("oakd")
    await dm.finish()
    await _esperar(lambda: dm.estado()["fase"] in {"done", "failed"})
    sid = dm.estado()["session_id"]
    assert dm.respaldo() is None
    dm.marcar_respaldo(sid)
    assert dm.respaldo() == sid
    assert dm.sesiones()[0]["respaldo"] is True
    assert dm.archivo(sid, "session.json").name == "session.json"
    from eovrt_webconsole.demo.sesion import SesionDesconocida

    with pytest.raises(SesionDesconocida):
        dm.archivo(sid, "../../../etc/passwd")
    with pytest.raises(SesionDesconocida):
        dm.sesion("../otra")


async def test_cifras_pendientes_sin_generacion_2(entorno):
    cifras = entorno.dm.cifras()
    assert cifras and all(c["pendiente"] for c in cifras)
    assert all(c["texto"] == "cifra pendiente (generación 2)" for c in cifras)


async def test_cifras_de_la_generacion_2_cuando_existen(entorno):
    destino = entorno.app.state.settings.repo_root / "results" / "gen2" / "ALR-01"
    destino.mkdir(parents=True)
    (destino / "resultado.json").write_text(json.dumps({
        "schema": "resultado.gen2.v1", "id": "ALR-01", "estado": "completo",
        "resumen": [{"clave": "f1", "nombre": "F1", "valor": 0.84, "unidad": None, "gen1": 0.841}],
    }))
    f1 = next(c for c in entorno.dm.cifras() if c["prueba"] == "ALR-01")
    assert f1["pendiente"] is False and f1["valor"] == 0.84
    assert f1["fuente"] == "results/gen2/ALR-01/resultado.json"


async def test_la_escena_etiqueta_la_sesion_sin_cambiar_lo_que_corre(entorno):
    """El rodaje en vivo (RT-04) nombra cada toma con su escena; la corrida es la misma."""
    inicio = await entorno.dm.start("oakd", "P1")
    sid = inicio["session_id"]
    assert sid.endswith("_P1")
    assert entorno.dm.estado()["escena"] == "P1"
    datos = json.loads((entorno.sesiones / sid / "session.json").read_text())
    assert datos["escena"] == "P1"
    await _esperar(lambda: entorno.media.lanzadas)
    assert entorno.media.lanzadas[0]["ingest"]["plugin"] == "oak_d"
    entorno.control.unidades = 1
    await _esperar(lambda: entorno.dm.estado()["fase"] == "live")
    assert entorno.dm.estado()["en_vivo_desde_ms"] > 0
    await entorno.dm.finish()
    await _esperar(lambda: entorno.dm.estado()["fase"] in {"done", "failed"})


async def test_escena_invalida_no_arranca(entorno):
    with pytest.raises(ValueError):
        await entorno.dm.start("oakd", "../fuera")


async def test_la_sesion_de_una_escena_se_puede_abrir_despues(entorno):
    """El Resultado de una toma del rodaje (`demo_…_P7a`) se abre como cualquier sesión:
    el id lleva la escena (mayúsculas) y, en una exploración, `_exp`."""
    dm = entorno.dm
    sid = (await dm.start("oakd", "P7a"))["session_id"]
    await dm.finish()
    await _esperar(lambda: dm.estado()["fase"] in {"done", "failed"})
    assert dm.sesion(sid)["session"]["session_id"] == sid
    assert dm.archivo(sid, "session.json").name == "session.json"
    dm.marcar_respaldo(sid)
    assert dm.respaldo() == sid
    assert dm.sesiones()[0]["escena"] == "P7a"


MODELO_YOLOE = {"ref": "yoloe/yoloe-26s", "thresholds": {"conf": 0.25}}


def _motor_cargado(entorno, modelo: dict) -> None:
    entorno.app.state.http = httpx.AsyncClient(base_url="http://media", transport=_transport({
        "/healthz": (200, {}), "/readyz": (200, {}), "/api/model": (200, modelo),
    }))


async def test_exploracion_corre_otro_motor_marcada_y_con_su_camara(entorno):
    """RT-05: la misma escena con otro motor y otra cadencia. No pasa lo congelado (queda
    registrado), no bloquea por eso, y la sesión queda marcada de punta a punta."""
    from eovrt_webconsole.demo.config import resolver_exploracion

    dm = entorno.dm
    _motor_cargado(entorno, MODELO_YOLOE)
    # La demo de siempre no arranca con un motor que no es el campeón.
    pf = await dm.preflight()
    assert next(i for i in pf["items"] if i["id"] == "deteccion")["estado"] == "error"
    with pytest.raises(DemoNoLista):
        await dm.start("oakd", "DEMO")

    exploracion = resolver_exploracion(dm.repo_root, "mp-yoloe-26s", "960x540@15")
    pf = await dm.preflight(exploracion)
    por_id = {i["id"]: i["estado"] for i in pf["items"]}
    assert por_id["deteccion"] == "ok" and por_id["congelado"] == "aviso"
    assert pf["listo"] is True and pf["exploracion"]["motor"] == "mp-yoloe-26s"

    sid = (await dm.start("oakd", "DEMO", {"motor": "mp-yoloe-26s", "camara": "960x540@15"}))["session_id"]
    assert sid.endswith("_DEMO_exp")
    assert dm.estado()["exploracion"]["camara"] == "960x540@15"
    datos = json.loads((entorno.sesiones / sid / "session.json").read_text())
    assert datos["exploracion"]["modelo"] == "yoloe/yoloe-26s"
    assert datos["exploracion"]["modelo_cargado"] == MODELO_YOLOE
    assert datos["congelado"]["ok"] is False  # se registra igual
    await _esperar(lambda: entorno.media.lanzadas)
    camara = entorno.media.lanzadas[0]["ingest"]["config"]
    assert camara["fps"] == 15 and camara["isp_scale"] == [1, 2]
    await dm.finish()
    await _esperar(lambda: dm.estado()["fase"] in {"done", "failed"})
    assert dm.sesiones()[0]["exploracion"]["motor"] == "mp-yoloe-26s"


async def test_exploracion_fuera_de_la_lista_o_sin_la_oakd_no_arranca(entorno):
    dm = entorno.dm
    with pytest.raises(ValueError, match="motor fuera"):
        await dm.start("oakd", "DEMO", {"motor": "mp-gdino-tiny", "camara": "960x540@5"})
    with pytest.raises(ValueError, match="cámara fuera"):
        await dm.start("oakd", "DEMO", {"motor": "mp-yoloe-26s", "camara": "1080p@30"})
    with pytest.raises(ValueError, match="OAK-D"):
        await dm.start("ensayo", "DEMO", {"motor": "mp-yoloe-26s"})
    # Pedir un motor que no es el cargado: el chequeo previo no queda listo.
    with pytest.raises(DemoNoLista):
        await dm.start("oakd", "DEMO", {"motor": "mp-yoloe-26s", "camara": "960x540@5"})
    assert not any(entorno.sesiones.glob("demo_*"))
