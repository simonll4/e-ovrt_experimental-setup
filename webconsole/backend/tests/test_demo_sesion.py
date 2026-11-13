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

from eovrt_webconsole.demo.sesion import (
    VISTA_CUADRO_OAKD_S,
    VISTA_REUSO_S,
    DemoManager,
    DemoNoLista,
    DemoOcupada,
    DemoSinSesion,
    VistaFallida,
    _SinCuadro,
)
from eovrt_webconsole.experiment.run_manager import ExperimentRunManager
from eovrt_webconsole.run_backend import PreviewConflict, ServiceUnavailable
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


async def _cuadro_llega(timeout: float) -> None:
    """El primer cuadro de la vista previa llega (en los tests no hay motor detrás)."""


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
        primer_cuadro=_cuadro_llega, espera_motor_s=2.0,
    )
    return SimpleNamespace(dm=dm, app=app, media=media, control=control, broker=broker,
                           renders=renders, sesiones=sesiones, dist_rutas=dist_rutas,
                           distribucion_cerro=distribucion_cerro)


async def test_preflight_nativo_todo_verde_salvo_el_motor_en_amarillo(entorno):
    pf = await entorno.dm.preflight()
    por_id = {i["id"]: i["estado"] for i in pf["items"]}
    assert por_id["motor"] == "aviso"  # nativo: la consola no puede verificarlo
    assert por_id["encuadre"] == "aviso"  # sin calibración de encuadre todavía (doc 134 §13.19)
    assert all(v == "ok" for k, v in por_id.items() if k not in ("motor", "encuadre")), pf["items"]
    assert pf["listo"] is True
    assert pf["congelado"]["ok"] is True
    assert pf["stack"] == "nativo"


def _vigente(repo: Path, fecha: str, **resto) -> None:
    ruta = repo / "results" / "gen2" / "_calibraciones" / "vigente.json"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps({"schema": "calibraciones.vigentes.v1", "por_camara": {"oak_d": {
        "session_id": "demo_x_CAL", "fecha": fecha, "ok": True, "aceptada": False, "motivo": None,
        "altura_m": 1.9, "fallan": [], "observaciones": [], **resto}}}))


async def test_preflight_encuadre_calibrado_verde_vencido_o_sin_pasar_amarillo(entorno):
    """✎ 2026-11-05 (doc 134 §13.19): la calibración vigente de la OAK-D se muestra en el chequeo
    previo. Pasó y es reciente: verde. Vencida (más de la vigencia máxima), o aceptada sin pasar:
    amarillo, y nunca bloquea (lo que frena una toma es rodaje.ps1)."""
    from datetime import UTC, datetime, timedelta

    dm = entorno.dm
    ahora = datetime.now(UTC)
    _vigente(dm.repo_root, (ahora - timedelta(minutes=10)).isoformat(timespec="seconds"), observaciones=["pies_visibles"])
    pf = await dm.preflight()
    enc = next(i for i in pf["items"] if i["id"] == "encuadre")
    assert enc["estado"] == "ok" and "1.9 m" in enc["detalle"] and "pies_visibles" in enc["detalle"]
    assert pf["encuadre"]["por_camara"]["oak_d"]["sirve"] is True

    _vigente(dm.repo_root, (ahora - timedelta(hours=13)).isoformat(timespec="seconds"))
    pf = await dm.preflight()
    enc = next(i for i in pf["items"] if i["id"] == "encuadre")
    assert enc["estado"] == "aviso" and "no sirve" in enc["detalle"] and pf["listo"] is True

    _vigente(dm.repo_root, ahora.isoformat(timespec="seconds"), ok=False, aceptada=True,
             motivo="control del encuadre del 11-01", fallan=["cerca_no_cortada"])
    pf = await dm.preflight()
    enc = next(i for i in pf["items"] if i["id"] == "encuadre")
    assert enc["estado"] == "aviso" and "aceptada con motivo" in enc["detalle"] and pf["listo"] is True


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


def _sesion_en_disco(raiz: Path, sid: str, *, escena: str, con_resultado: bool = True) -> Path:
    carpeta = raiz / sid
    carpeta.mkdir(parents=True)
    (carpeta / "session.json").write_text(json.dumps(
        {"session_id": sid, "variante": "oakd", "fase": "done", "escena": escena}))
    if con_resultado:
        (carpeta / "resultado").mkdir()
        (carpeta / "resultado" / "resumen.json").write_text("{}")
    return carpeta


def test_las_sesiones_de_otras_jornadas_se_listan_y_se_abren_sin_copiarlas(entorno, tmp_path):
    """Los paquetes de las jornadas en vivo no viven en el repo (tienen video con personas):
    la consola los lee desde carpetas adicionales, de solo lectura."""
    dm = entorno.dm
    jornada = tmp_path / "paquete-jornada" / "sesiones"
    _sesion_en_disco(dm.sesiones_dir, "demo_20261101T100000Z_P1", escena="P1", con_resultado=False)
    _sesion_en_disco(jornada, "demo_20261107T160250Z_P2", escena="P2")
    # La misma sesión en las dos carpetas: gana la de esta consola y aparece una sola vez.
    _sesion_en_disco(dm.sesiones_dir, "demo_20261107T120000Z_P5", escena="P5")
    _sesion_en_disco(jornada, "demo_20261107T120000Z_P5", escena="otra copia")
    assert [f["session_id"] for f in dm.sesiones()] == ["demo_20261107T120000Z_P5", "demo_20261101T100000Z_P1"]

    dm.sesiones_extra = (jornada, tmp_path / "no-existe")
    filas = {f["session_id"]: f for f in dm.sesiones()}
    assert list(filas) == ["demo_20261107T160250Z_P2", "demo_20261107T120000Z_P5", "demo_20261101T100000Z_P1"]
    assert filas["demo_20261107T160250Z_P2"]["archivada"] is True
    assert filas["demo_20261107T160250Z_P2"]["tiene_resultado"] is True
    assert filas["demo_20261107T120000Z_P5"]["archivada"] is False and filas["demo_20261107T120000Z_P5"]["escena"] == "P5"
    assert filas["demo_20261101T100000Z_P1"]["tiene_resultado"] is False
    # Se abre y sirve sus archivos igual que una propia, con la misma guarda de ruta.
    assert dm.sesion("demo_20261107T160250Z_P2")["session"]["escena"] == "P2"
    assert dm.archivo("demo_20261107T160250Z_P2", "resultado/resumen.json").is_file()
    from eovrt_webconsole.demo.sesion import SesionDesconocida

    with pytest.raises(SesionDesconocida):
        dm.archivo("demo_20261107T160250Z_P2", "../demo_20261107T120000Z_P5/session.json")
    # Marcar como respaldo una sesión archivada escribe la marca en la carpeta de esta consola.
    dm.marcar_respaldo("demo_20261107T160250Z_P2")
    assert (dm.sesiones_dir / "RESPALDO").is_file() and not (jornada / "RESPALDO").exists()


def test_una_sesion_guardada_trae_el_equipo_donde_corrio_y_su_log(entorno):
    """La capa de evidencia de una sesión guardada muestra lo que registró la sesión, no el
    equipo ni el estado de quien la abre después."""
    dm = entorno.dm
    carpeta = _sesion_en_disco(dm.sesiones_dir, "demo_20261107T160250Z_P1", escena="P1")
    (carpeta / "preflight.json").write_text(json.dumps(
        {"consola": {"stack": "compose"}, "host": {"presente": True, "datos": {"equipo": "HP Victus", "ram_gb": 31.3}}}))
    log = carpeta / "resultado" / "log"
    (log / "experimento").mkdir(parents=True)
    (log / "control").mkdir()
    (log / "experimento" / "report.md").write_text("# Informe del experimento\n")
    (log / "control" / "alerts.jsonl").write_text('{"condition_id": "CR-01"}\n')
    d = dm.sesion("demo_20261107T160250Z_P1")
    assert d["equipo"] == {"equipo": "HP Victus", "ram_gb": 31.3}
    assert d["log"]["archivos"] == ["resultado/log/control/alerts.jsonl", "resultado/log/experimento/report.md"]
    assert d["log"]["informe"] == "# Informe del experimento\n"
    assert d["log"]["alertas"] == '{"condition_id": "CR-01"}\n'
    assert d["log"]["distribucion"] is None  # el archivo no está: se dice, no se inventa
    # Una sesión sin chequeo ni log se abre igual.
    _sesion_en_disco(dm.sesiones_dir, "demo_20261101T100000Z_P2", escena="P2", con_resultado=False)
    d = dm.sesion("demo_20261101T100000Z_P2")
    assert d["equipo"] is None and d["log"] == {"archivos": [], "informe": None, "alertas": None, "distribucion": None}


def test_las_carpetas_adicionales_de_sesiones_salen_del_entorno():
    import os

    from eovrt_webconsole.settings import ConsoleSettings

    repo = str(Path(__file__).resolve().parents[3])
    env = {"EOVRT_CONSOLE_REPO_ROOT": repo,
           "EOVRT_CONSOLE_DEMO_SESSIONS_EXTRA": os.pathsep.join(["/a/sesiones", "", "/b/sesiones"])}
    assert ConsoleSettings.from_env(env).demo_sessions_extra == (Path("/a/sesiones"), Path("/b/sesiones"))
    assert ConsoleSettings.from_env({"EOVRT_CONSOLE_REPO_ROOT": repo}).demo_sessions_extra == ()


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


# --- el modo de prompts (✎ 2026-11-01, modos.yaml) -------------------------------------------


async def test_modo_edir_manda_lo_medido_y_marca_la_sesion(entorno):
    """Otro par prompt set + pattern set ya medido: lo congelado queda en amarillo (no bloquea),
    los prompts van por corrida sin tocar el motor, y la sesión queda marcada de punta a punta."""
    from eovrt_webconsole.demo import modos as demo_modos

    dm = entorno.dm
    edir = demo_modos.resolver(dm.repo_root, "edir")
    pf = await dm.preflight(None, edir)
    por_id = {i["id"]: i for i in pf["items"]}
    assert por_id["congelado"]["estado"] == "aviso" and "E-DIR" in por_id["congelado"]["detalle"]
    assert por_id["modo"]["estado"] == "ok" and "ALR-04" in por_id["modo"]["detalle"]
    assert pf["listo"] is True and pf["congelado"]["ok"] is False
    assert pf["modo_prompts"]["id"] == "edir" and pf["modo_prompts"]["verificacion"]["ok"] is True

    sid = (await dm.start("oakd", modo="edir"))["session_id"]
    assert sid.endswith("_modo-edir")
    await _esperar(lambda: entorno.media.lanzadas)
    assert entorno.media.lanzadas[0]["prompts"] == demo_modos.payload(edir)
    control = entorno.control.lanzadas[0][0]
    assert control["patterns"]["file"].endswith("/cr01_cr02_edir_v1.yaml")
    assert dm.estado()["modo_prompts"]["id"] == "edir"
    datos = json.loads((entorno.sesiones / sid / "session.json").read_text())
    assert datos["modo_prompts"]["prompt_set"] == "edir_v1_pair_nivel_b"
    assert datos["modo_prompts"]["pattern_set"]["id"] == "cr01_cr02_edir_v1"
    assert datos["modo_prompts"]["verificacion"]["ok"] is True
    assert datos["congelado"]["ok"] is False  # se registra igual
    assert datos["exploracion"] is None
    await dm.finish()
    await _esperar(lambda: dm.estado()["fase"] in {"done", "failed"})
    assert dm.sesiones()[0]["modo_prompts"]["id"] == "edir"
    assert dm.sesion(sid)["session"]["modo_prompts"]["id"] == "edir"


async def test_el_campeon_pedido_por_nombre_es_la_demo_congelada(entorno):
    dm = entorno.dm
    sid = (await dm.start("oakd", "DEMO", modo="campeon"))["session_id"]
    assert sid.endswith("_DEMO")
    datos = json.loads((entorno.sesiones / sid / "session.json").read_text())
    assert datos["modo_prompts"] is None and datos["congelado"]["ok"] is True
    await _esperar(lambda: entorno.media.lanzadas)
    assert entorno.media.lanzadas[0]["prompts"]["set_inline"]["id"] == "cr01_cr02_v2_short"
    await dm.finish()
    await _esperar(lambda: dm.estado()["fase"] in {"done", "failed"})


async def test_modo_fuera_de_la_lista_o_con_exploracion_no_arranca(entorno):
    from eovrt_webconsole.demo.config import ConfigDemoError

    dm = entorno.dm
    with pytest.raises(ConfigDemoError, match="fuera de la lista"):
        await dm.start("oakd", modo="vocabulario_libre")
    with pytest.raises(ValueError, match="no se combina"):
        await dm.start("oakd", "DEMO", {"motor": "mp-gdino-tiny-560", "camara": "960x540@5"}, modo="edir")
    assert not any(entorno.sesiones.glob("demo_*"))


async def test_un_modo_que_ya_no_es_el_medido_queda_en_rojo(entorno):
    """Una frase cambiada en prompts/ después de la medición: el modo ya no es lo que midió su
    prueba, el chequeo previo lo pone en rojo y la sesión no arranca."""
    from eovrt_webconsole.demo import modos as demo_modos

    dm = entorno.dm
    archivo = dm.repo_root / "prompts" / "edir_v1.yaml"
    archivo.write_text(archivo.read_text(encoding="utf-8").replace(
        "construction worker without safety helmet", "worker with no helmet"), encoding="utf-8")
    pf = await dm.preflight(None, demo_modos.resolver(dm.repo_root, "edir"))
    modo = next(i for i in pf["items"] if i["id"] == "modo")
    assert modo["estado"] == "error" and "ALR-04" in modo["detalle"] and pf["listo"] is False
    with pytest.raises(DemoNoLista):
        await dm.start("oakd", modo="edir")
    assert not any(entorno.sesiones.glob("demo_*"))


async def test_un_modo_exploratorio_queda_en_amarillo_y_arranca(entorno):
    """✎ 2026-11-04 (doc 134 §13.18): la distractora no tiene medición todavía. El chequeo previo
    verifica igual que se manda exactamente lo declarado, pero lo deja en amarillo (no verde) y dice
    que es exploración; la sesión arranca y queda marcada como cualquier modo."""
    from eovrt_webconsole.demo import modos as demo_modos

    from tests.demo_fixtures import agregar_modo_exploratorio

    dm = entorno.dm
    agregar_modo_exploratorio(dm.repo_root)
    distractora = demo_modos.resolver(dm.repo_root, "distractora")
    pf = await dm.preflight(None, distractora)
    por_id = {i["id"]: i for i in pf["items"]}
    assert por_id["modo"]["estado"] == "aviso" and "exploración" in por_id["modo"]["detalle"]
    assert por_id["congelado"]["estado"] == "aviso"
    assert pf["listo"] is True
    assert pf["modo_prompts"]["verificacion"]["exploratorio"] is True

    sid = (await dm.start("oakd", "P2", modo="distractora"))["session_id"]
    assert sid.endswith("_modo-distractora")
    await _esperar(lambda: entorno.media.lanzadas)
    enviados = entorno.media.lanzadas[0]["prompts"]
    assert [c["id"] for c in enviados["set_inline"]["classes"]] == ["person", "helmet", "vest", "t_shirt"]
    assert demo_modos.huella_prompts(enviados) == distractora["payload_sha256"]
    control = entorno.control.lanzadas[0][0]
    assert control["patterns"]["file"].endswith("/cr01_cr02_v2.yaml")
    datos = json.loads((entorno.sesiones / sid / "session.json").read_text())
    assert datos["modo_prompts"]["evidencia"] == "exploratoria"
    assert datos["modo_prompts"]["medido_en"] is None
    await dm.finish()
    await _esperar(lambda: dm.estado()["fase"] in {"done", "failed"})


async def test_un_modo_exploratorio_con_una_frase_cambiada_queda_en_rojo(entorno):
    from eovrt_webconsole.demo import modos as demo_modos

    from tests.demo_fixtures import agregar_modo_exploratorio

    dm = entorno.dm
    agregar_modo_exploratorio(dm.repo_root)
    archivo = dm.repo_root / "prompts" / "cr01_cr02_v2_tshirt.yaml"
    archivo.write_text(archivo.read_text(encoding="utf-8").replace('["t-shirt"]', '["shirt"]'), encoding="utf-8")
    pf = await dm.preflight(None, demo_modos.resolver(dm.repo_root, "distractora"))
    modo = next(i for i in pf["items"] if i["id"] == "modo")
    assert modo["estado"] == "error" and "modos.yaml" in modo["detalle"] and pf["listo"] is False
    with pytest.raises(DemoNoLista):
        await dm.start("oakd", modo="distractora")
    assert not any(entorno.sesiones.glob("demo_*"))


# --- la cámara elegida en la pantalla (✎ 2026-11-01) -------------------------------------------

CLAVE_DVR = "S3cr3ta"
URL_DVR = f"rtsp://admin:{CLAVE_DVR}@169.254.31.140:554/Streaming/Channels/2"


def _presets(entorno) -> None:
    import yaml
    cameras = Path(entorno.app.state.settings.repo_root) / "cameras"
    cameras.mkdir(exist_ok=True)
    for id_, plugin, config in (("oak_d_lab", "oak_d", {"url": "169.254.31.137"}),
                                ("rtsp_dvr_1", "rtsp", {"url": URL_DVR})):
        (cameras / f"{id_}.yaml").write_text(yaml.safe_dump(
            {"camera": {"id": id_, "name": id_, "plugin": plugin, "config": config}}))


async def test_arrancar_con_una_camara_rtsp_manda_su_fuente_y_deja_la_clave_solo_mientras_corre(entorno):
    _presets(entorno)
    dm, media = entorno.dm, entorno.media
    inicio = await dm.start("oakd", camara="rtsp_dvr_1")
    carpeta = entorno.sesiones / inicio["session_id"]
    await _esperar(lambda: media.lanzadas)
    # Lo que corre es la fuente de la cámara elegida, con la URL real (hay que abrirla)...
    assert media.lanzadas[0]["ingest"] == {"plugin": "rtsp", "config": {"url": URL_DVR}}
    assert CLAVE_DVR in (carpeta / "config" / "media.yaml").read_text()
    # ...y la pantalla/estado dicen cuál es, sin credenciales.
    assert dm.estado()["camara_elegida"] == {
        "id": "rtsp_dvr_1", "nombre": "rtsp_dvr_1", "plugin": "rtsp", "destino": "169.254.31.140:554"}
    assert CLAVE_DVR not in json.dumps(dm.estado())

    entorno.control.unidades = 1
    await _esperar(lambda: dm.estado()["fase"] == "live")
    await dm.finish()
    await _esperar(lambda: dm.estado()["fase"] in {"done", "failed"})
    assert dm.estado()["fase"] == "done", dm.estado()["error"]
    # Al cerrar, la config guardada se limpia: la clave no queda en disco en la carpeta de la sesión.
    assert CLAVE_DVR not in (carpeta / "config" / "media.yaml").read_text()
    sesion = json.loads((carpeta / "session.json").read_text())
    assert sesion["camara"]["id"] == "rtsp_dvr_1" and CLAVE_DVR not in json.dumps(sesion)
    textos = [f for f in carpeta.rglob("*") if f.is_file() and f.suffix in {".json", ".yaml", ".jsonl"}]
    assert textos and all(CLAVE_DVR not in f.read_text() for f in textos)


async def test_con_la_oak_d_elegida_la_plantilla_manda_y_solo_cambia_la_direccion(entorno):
    _presets(entorno)
    await entorno.dm.start("oakd", camara="oak_d_lab")
    await _esperar(lambda: entorno.media.lanzadas)
    ingest = entorno.media.lanzadas[0]["ingest"]
    assert ingest["plugin"] == "oak_d" and ingest["config"]["url"] == "169.254.31.137"
    assert ingest["config"]["isp_scale"] == [1, 2] and ingest["config"]["fps"] == 5  # lo medido


async def test_sin_camara_elegida_sigue_la_de_la_plantilla(entorno):
    await entorno.dm.start("oakd")
    await _esperar(lambda: entorno.media.lanzadas)
    assert entorno.media.lanzadas[0]["ingest"]["plugin"] == "oak_d"
    assert entorno.dm.estado()["camara_elegida"] is None


async def test_camara_desconocida_o_con_exploracion_no_arranca(entorno):
    _presets(entorno)
    with pytest.raises(ValueError, match="no hay un preset"):
        await entorno.dm.start("oakd", camara="no_existe")
    with pytest.raises(ValueError, match="no se combina"):
        await entorno.dm.start("oakd", camara="rtsp_dvr_1", exploracion={"motor": "mp-gdino-tiny-560"})
    assert entorno.dm.estado()["fase"] == "idle"


async def test_comprobar_camara_con_una_sesion_en_curso_no_abre_la_oak_d(entorno):
    _presets(entorno)
    llamadas: list = []

    async def ejecutar(cmd, entrada, timeout):
        llamadas.append(cmd)
        return 0, "OK: cuadro", ""
    entorno.dm._ejecutar = ejecutar
    await entorno.dm.start("oakd")
    r = await entorno.dm.comprobar_camara("oak_d_lab")
    assert r["estado"] == "en_uso" and not llamadas


# --- vista previa de la cámara, antes de iniciar -----------------------------------------------


class _Preview:
    """Lo que el motor hace con el canal de preview: anota las llamadas y simula que se suelta."""

    def __init__(self, suelta_tras: int = 0):
        self.arranques: list[dict] = []
        self.paradas = 0
        self._consultas = 0
        self._suelta_tras = suelta_tras

    async def preview_start(self, body):
        self.arranques.append(body)
        return {"preview_id": "pv1"}

    async def preview_stop(self):
        self.paradas += 1

    async def preview_status(self):
        self._consultas += 1
        return {"status": "streaming" if self._consultas <= self._suelta_tras else "idle"}


async def test_vista_previa_oak_d_usa_la_fuente_de_la_demo_y_deja_el_motor_sin_fresco(entorno):
    _presets(entorno)
    entorno.dm._motor = {**entorno.dm._motor, "estado": "fresco"}
    pv = _Preview()
    entorno.media.preview_start = pv.preview_start
    r = await entorno.dm.iniciar_vista("oak_d_lab")
    assert r["id"] == "oak_d_lab" and r["plugin"] == "oak_d"
    (cuerpo,) = pv.arranques
    assert cuerpo["mode"] == "raw"  # sin modelo: es para ver el encuadre
    assert cuerpo["ingest"]["plugin"] == "oak_d"
    assert cuerpo["ingest"]["config"]["isp_scale"] == [1, 2] and cuerpo["ingest"]["config"]["fps"] == 5
    # F-101.5: la OAK-D abierta en el proceso del motor es un uso; el chequeo previo pide reiniciarlo.
    assert entorno.dm.estado()["motor"]["estado"] == "usado"


async def test_vista_previa_rtsp_arma_la_url_en_el_servidor_y_no_toca_la_frescura(entorno):
    _presets(entorno)
    entorno.dm._motor = {**entorno.dm._motor, "estado": "fresco"}
    pv = _Preview()
    entorno.media.preview_start = pv.preview_start
    r = await entorno.dm.iniciar_vista("rtsp_dvr_1")
    assert pv.arranques[0]["ingest"] == {"plugin": "rtsp", "config": {"url": URL_DVR}}  # al motor, completa
    assert CLAVE_DVR not in json.dumps(r)  # a la pantalla, nunca
    assert entorno.dm.estado()["motor"]["estado"] == "fresco"  # un RTSP no tiene el límite de la OAK-D


async def test_no_se_previsualiza_con_una_sesion_en_curso(entorno):
    _presets(entorno)
    entorno.media.preview_start = _Preview().preview_start
    await entorno.dm.start("oakd")
    with pytest.raises(DemoOcupada):
        await entorno.dm.iniciar_vista("rtsp_dvr_1")


async def test_al_iniciar_la_sesion_se_corta_el_preview_y_se_espera_a_que_se_suelte(entorno):
    pv = _Preview(suelta_tras=3)
    entorno.media.preview_stop = pv.preview_stop
    entorno.media.preview_status = pv.preview_status
    await entorno.dm.start("oakd")
    assert pv.paradas == 1 and pv._consultas == 4  # preguntó hasta que dejó de estar «streaming»
    await _esperar(lambda: entorno.media.lanzadas)  # y recién después lanzó la corrida


async def test_detener_la_vista_sin_motor_o_sin_preview_no_revienta(entorno):
    async def cae():
        raise RuntimeError("sin motor")
    entorno.media.preview_stop = cae
    await entorno.dm.detener_vista()


# --- «Ver la cámara» a prueba de fricción (✎ 2026-11-07, jornada de la Victus) -----------------


class _MotorVista:
    """El canal de preview del motor con su estado real: un solo slot, quién lo tiene, y el 409
    «Slot de actividad ocupado por preview (…)» si se pide otra vista con una abierta."""

    def __init__(self, entorno, *, colgada: str | None = None) -> None:
        self.arranques: list[dict] = []
        self.paradas = 0
        self.activa: str | None = colgada
        self._n = 0
        entorno.media.preview_start = self.preview_start
        entorno.media.preview_stop = self.preview_stop
        entorno.media.preview_status = self.preview_status

    async def preview_start(self, body):
        if self.activa is not None:
            raise PreviewConflict({"detail": f"Slot de actividad ocupado por preview ({self.activa})",
                                   "reason": "preview_active"})
        self._n += 1
        self.activa = f"pv{self._n}"
        self.arranques.append(body)
        return {"preview_id": self.activa}

    async def preview_stop(self):
        self.paradas += 1
        self.activa = None

    async def preview_status(self):
        if self.activa:
            return {"status": "streaming", "preview_id": self.activa, "mode": "raw", "error": None}
        return {"status": "idle", "preview_id": None, "mode": None, "error": None}


def _compose(entorno, motor: _MotorVista | None = None) -> list[int]:
    """Despliegue en compose: la consola puede reiniciar el motor (y el reinicio mata la vista)."""
    reinicios: list[int] = []

    class FakeTarget:
        active = "mp-gdino-tiny-560"

        async def restart_active(self):
            reinicios.append(1)
            if motor is not None:
                motor.activa = None
            return {"target": "mp-gdino-tiny-560", "model_ref": MODELO_OK["ref"]}

    entorno.app.state.target_manager = FakeTarget()
    return reinicios


async def test_vista_de_la_misma_camara_se_reusa_sin_reabrir_la_oak_d(entorno):
    """La pantalla se recargó (o se cerró la pestaña) con la vista abierta: tocar «Ver la cámara»
    otra vez no reabre la OAK-D ni choca con el slot."""
    _presets(entorno)
    motor = _MotorVista(entorno)
    await entorno.dm.iniciar_vista("oak_d_lab")
    await entorno.dm.iniciar_vista("oak_d_lab")
    assert len(motor.arranques) == 1 and motor.paradas == 0


async def test_vista_colgada_en_el_motor_se_corta_y_se_abre_la_pedida(entorno):
    """El «Slot de actividad ocupado por preview (pv_…)» del 11-07: una vista que quedó abierta
    desde otra pantalla ya no bloquea."""
    _presets(entorno)
    motor = _MotorVista(entorno, colgada="pv_2b8f8dfb")
    r = await entorno.dm.iniciar_vista("oak_d_lab")
    assert r["id"] == "oak_d_lab"
    assert motor.paradas >= 1 and len(motor.arranques) == 1 and motor.activa == "pv1"


async def test_vista_abierta_pero_muda_no_se_reusa(entorno):
    _presets(entorno)
    motor = _MotorVista(entorno)
    await entorno.dm.iniciar_vista("rtsp_dvr_1")
    esperas: list[float] = []

    async def muda_la_primera_vez(timeout):
        esperas.append(timeout)
        if len(esperas) == 1:
            raise _SinCuadro("sin cuadros")
    entorno.dm._primer_cuadro = muda_la_primera_vez
    await entorno.dm.iniciar_vista("rtsp_dvr_1")
    assert esperas[0] == VISTA_REUSO_S and len(motor.arranques) == 2


async def test_vista_espera_el_reinicio_del_motor_en_vez_de_fallar(entorno):
    """Recién cortada la vista de la OAK-D la consola reinicia el motor (~30 s): «Ver la cámara»
    en esa ventana espera, no responde «no hay un motor de detección activo»."""
    _presets(entorno)
    motor = _MotorVista(entorno)
    entorno.dm._motor = {"estado": "reiniciando", "desde": None, "runs": None}

    async def termina():
        await asyncio.sleep(0.05)
        entorno.dm._motor = {"estado": "fresco", "desde": "x", "runs": set()}
    tarea = asyncio.create_task(termina())
    await entorno.dm.iniciar_vista("oak_d_lab")
    await tarea
    assert len(motor.arranques) == 1


async def test_vista_oak_d_sin_cuadro_reinicia_el_motor_y_reintenta(entorno):
    _presets(entorno)
    motor = _MotorVista(entorno)
    reinicios = _compose(entorno, motor)
    esperas: list[float] = []

    async def falla_la_primera(timeout):
        esperas.append(timeout)
        if len(esperas) == 1:
            raise _SinCuadro("Couldn't read data from stream: 'rgb' (X_LINK_ERROR)")
    entorno.dm._primer_cuadro = falla_la_primera
    r = await entorno.dm.iniciar_vista("oak_d_lab")
    assert r["id"] == "oak_d_lab"
    assert reinicios == [1] and len(motor.arranques) == 2 and motor.activa == "pv2"
    assert esperas[0] == VISTA_CUADRO_OAKD_S
    assert entorno.dm.estado()["motor"]["estado"] == "usado"  # F-101.5: igual que antes


async def test_vista_oak_d_con_el_motor_usado_lo_reinicia_antes_de_abrir(entorno):
    _presets(entorno)
    motor = _MotorVista(entorno)
    reinicios = _compose(entorno, motor)
    await entorno.dm.reiniciar_motor()
    reinicios.clear()
    entorno.media.runs_en_disco.add("run_de_otro")  # corrió algo en esta vida del motor
    await entorno.dm.iniciar_vista("oak_d_lab")
    assert reinicios == [1] and len(motor.arranques) == 1


async def test_vista_rtsp_sin_cuadros_no_reinicia_el_motor_y_explica(entorno):
    _presets(entorno)
    motor = _MotorVista(entorno)
    reinicios = _compose(entorno, motor)

    async def nunca(timeout):
        raise _SinCuadro("no llegó ningún cuadro en 15 s")
    entorno.dm._primer_cuadro = nunca
    with pytest.raises(VistaFallida) as exc:
        await entorno.dm.iniciar_vista("rtsp_dvr_1")
    assert reinicios == [] and motor.activa is None  # no quedó la cámara tomada
    assert "no entrega cuadros" in str(exc.value) and CLAVE_DVR not in str(exc.value)


async def test_vista_oak_d_que_no_vuelve_explica_que_hacer_y_no_deja_nada_colgado(entorno):
    _presets(entorno)
    motor = _MotorVista(entorno)

    async def nunca(timeout):
        raise _SinCuadro("OAK-D: no se pudo conectar tras 12 intentos: 169.254.31.137")
    entorno.dm._primer_cuadro = nunca
    with pytest.raises(VistaFallida) as exc:
        await entorno.dm.iniciar_vista("oak_d_lab")
    assert len(motor.arranques) == 2 and motor.activa is None
    assert "12 intentos" in str(exc.value) and "inyector 1–2 min" in str(exc.value)


async def test_vista_no_pisa_una_corrida_del_motor(entorno):
    _presets(entorno)
    motor = _MotorVista(entorno)
    reinicios = _compose(entorno, motor)

    async def con_corrida(body):
        raise PreviewConflict({"detail": "Slot de actividad ocupado por run (run_x)",
                               "reason": "run_active", "active_run_id": "run_x"})
    entorno.media.preview_start = con_corrida
    with pytest.raises(VistaFallida, match="run_x"):
        await entorno.dm.iniciar_vista("rtsp_dvr_1")
    assert reinicios == [] and motor.paradas == 0


async def test_toma_con_la_vista_de_la_oak_d_abierta_espera_un_motor_nuevo(entorno):
    """Compose: con la vista de la OAK-D abierta el chequeo previo queda en rojo (la toma la abriría
    por segunda vez, F-101.5); si nadie la mira se corta sola, el motor se reinicia y vuelve el verde
    (lo único que `rodaje.ps1` espera)."""
    _presets(entorno)
    motor = _MotorVista(entorno)
    reinicios = _compose(entorno, motor)
    await entorno.dm.reiniciar_motor()
    reinicios.clear()
    await entorno.dm.iniciar_vista("oak_d_lab")

    async def item_motor():
        pf = await entorno.dm.preflight()
        return next(i for i in pf["items"] if i["id"] == "motor")
    abierta = await item_motor()
    assert abierta["estado"] == "error" and "vista de la OAK-D está abierta" in abierta["detalle"]
    assert motor.activa == "pv1" and reinicios == []  # la mira alguien: no se toca

    entorno.dm._vista_abierta_en -= 60  # pestaña cerrada hace un minuto
    assert (await item_motor())["estado"] == "error"  # se cortó sola y el motor se está reiniciando
    assert motor.activa is None
    await _esperar(lambda: reinicios == [1] and entorno.dm._motor["estado"] == "fresco")
    assert (await item_motor())["estado"] == "ok"


async def test_primer_cuadro_por_el_websocket_del_motor(entorno):
    """La espera del primer cuadro contra un WebSocket de verdad, con los tres finales posibles."""
    import websockets

    modo = {"v": "cuadro"}

    async def motor(ws):
        if modo["v"] == "cuadro":
            await ws.send(b"\x00\x00\x00\x02{}\xff\xd8")
            await asyncio.sleep(1)
        elif modo["v"] == "error":
            await ws.send(json.dumps({"type": "state", "status": "error", "error": "X_LINK_ERROR"}))
        else:
            await ws.close(code=4404)  # la vista ya no está: la causa la tiene el estado

    async def estado_con_error():
        return {"status": "error", "preview_id": None, "error": "Cannot find any device"}
    entorno.media.preview_status = estado_con_error
    dm = entorno.dm
    async with websockets.serve(motor, "127.0.0.1", 0) as servidor:
        puerto = servidor.sockets[0].getsockname()[1]
        entorno.app.state.http = httpx.AsyncClient(base_url=f"http://127.0.0.1:{puerto}")
        await dm._primer_cuadro_ws(2.0)
        modo["v"] = "error"
        with pytest.raises(_SinCuadro, match="X_LINK_ERROR"):
            await dm._primer_cuadro_ws(2.0)
        modo["v"] = "cerrada"
        with pytest.raises(_SinCuadro, match="Cannot find any device"):
            await dm._primer_cuadro_ws(2.0)
    with pytest.raises(ServiceUnavailable):  # sin motor del otro lado
        await dm._primer_cuadro_ws(2.0)


async def test_camaras_traen_su_estado_y_la_oak_d_lo_toma_de_la_ultima_comprobacion(entorno):
    _presets(entorno)
    conectados: list = []

    class _W:
        def close(self): pass
        async def wait_closed(self): return None

    async def conectar(host, puerto):
        conectados.append((host, puerto))
        return None, _W()
    entorno.dm._conectar = conectar

    async def ejecutar(cmd, entrada, timeout):
        return 0, "conectada en 9.4 s: OAK-D-PRO-POE 1944\nOK: cuadro 320x180 recibido.\n", ""
    entorno.dm._ejecutar = ejecutar

    filas = {f["id"]: f for f in await entorno.dm.camaras()}
    assert filas["rtsp_dvr_1"]["estado"] == "activa" and conectados == [("169.254.31.140", 554)]
    assert filas["oak_d_lab"]["estado"] == "sin_comprobar"  # y no se la sondeó
    assert CLAVE_DVR not in json.dumps(filas)
    assert filas["rtsp_dvr_1"]["medido_en"]

    sonda = Path(entorno.app.state.settings.repo_root) / "infra" / "platform" / "oakd_probe.py"
    sonda.parent.mkdir(parents=True, exist_ok=True)
    sonda.write_text("print('sonda')\n")
    entorno.app.state.target_manager = SimpleNamespace(active="mp-gdino-tiny-560")
    assert (await entorno.dm.comprobar_camara("oak_d_lab"))["estado"] == "ok"
    filas = {f["id"]: f for f in await entorno.dm.camaras()}
    assert filas["oak_d_lab"]["estado"] == "activa"
