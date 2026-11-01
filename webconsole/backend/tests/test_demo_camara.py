"""La cámara de la demo (✎ 2026-11-01): elegirla, aplicarla a la sesión y comprobar que se ve."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
import yaml

from eovrt_webconsole.demo import camara as cam

CLAVE = "S3cr3ta"
URL_RTSP = f"rtsp://admin:{CLAVE}@169.254.31.140:554/Streaming/Channels/2"


def _preset(carpeta: Path, id_: str, plugin: str, config: dict, nombre: str | None = None) -> None:
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / f"{id_}.yaml").write_text(yaml.safe_dump(
        {"camera": {"id": id_, "name": nombre or id_, "plugin": plugin, "config": config}}))


@pytest.fixture
def cameras(tmp_path):
    d = tmp_path / "cameras"
    _preset(d, "oak_d_lab", "oak_d", {"url": "169.254.31.137", "fps": 30}, "OAK-D laboratorio")
    _preset(d, "rtsp_dvr_1", "rtsp", {"url": URL_RTSP}, "RTSP DVR canal 1")
    _preset(d, "clip", "video_file", {"path": "/x.mp4"})
    (d / "roto.yaml").write_text("camera: [esto no es un mapa")
    return d


class Ejecutor:
    """Un `ejecutar` programable que anota lo que se le pidió."""

    def __init__(self, *respuestas):
        self.respuestas = list(respuestas)
        self.llamadas: list[tuple[list[str], bytes | None]] = []

    async def __call__(self, cmd, entrada, timeout):
        self.llamadas.append((cmd, entrada))
        return self.respuestas.pop(0)


AHORA = "2026-11-01T00:00:00+00:00"


# --- presets -----------------------------------------------------------------------------------


def test_listar_deja_oak_d_y_rtsp_sin_credenciales_y_marca_la_de_la_demo(cameras):
    filas = cam.listar(cameras)
    assert [f["id"] for f in filas] == ["oak_d_lab", "rtsp_dvr_1"]  # sin video_file ni el YAML roto
    assert {f["id"]: f["destino"] for f in filas} == {
        "oak_d_lab": "169.254.31.137", "rtsp_dvr_1": "169.254.31.140:554"}
    assert [f["por_defecto"] for f in filas] == [True, False]
    assert CLAVE not in json.dumps(filas)


def test_cargar_valida_id_existencia_y_plugin(cameras):
    assert cam.cargar(cameras, "rtsp_dvr_1")["plugin"] == "rtsp"
    for malo in ("../etc/passwd", "no_existe", "clip", "ROTO", ""):
        with pytest.raises(cam.CamaraDesconocida):
            cam.cargar(cameras, malo)


def test_aplicar_oak_d_deja_mandar_a_la_plantilla_y_toma_solo_la_direccion():
    plantilla = {"plugin": "oak_d", "config": {"url": "169.254.31.137", "isp_scale": [1, 2], "fps": 5,
                                                "warmup_frames": 20}}
    preset = {"id": "otra", "plugin": "oak_d", "config": {"url": "10.0.0.9", "fps": 30}}
    assert cam.aplicar(plantilla, preset) == {
        "plugin": "oak_d", "config": {"url": "10.0.0.9", "isp_scale": [1, 2], "fps": 5, "warmup_frames": 20}}


def test_aplicar_otro_tipo_usa_lo_que_dice_el_preset():
    plantilla = {"plugin": "oak_d", "config": {"url": "169.254.31.137", "isp_scale": [1, 2], "fps": 5}}
    preset = {"id": "dvr", "plugin": "rtsp", "config": {"url": URL_RTSP}}
    assert cam.aplicar(plantilla, preset) == {"plugin": "rtsp", "config": {"url": URL_RTSP}}


def test_redactar_y_limpiar_credenciales(tmp_path):
    assert cam.redactar(f"abrió {URL_RTSP} y falló") == (
        "abrió rtsp://admin:***@169.254.31.140:554/Streaming/Channels/2 y falló")
    d = tmp_path / "config"
    d.mkdir()
    (d / "media.yaml").write_text(yaml.safe_dump({"ingest": {"config": {"url": URL_RTSP}}}))
    (d / "control.yaml").write_text("run: {name: x}\n")
    assert cam.limpiar_credenciales(d) == 1
    assert CLAVE not in (d / "media.yaml").read_text()
    assert yaml.safe_load((d / "media.yaml").read_text())["ingest"]["config"]["url"].startswith("rtsp://admin:***@")


# --- comprobar RTSP ----------------------------------------------------------------------------


async def _servidor_tcp():
    servidor = await asyncio.start_server(lambda r, w: w.close(), "127.0.0.1", 0)
    return servidor, servidor.sockets[0].getsockname()[1]


async def test_rtsp_ok_con_resolucion_y_cuadros_por_segundo(cameras):
    servidor, puerto = await _servidor_tcp()
    preset = {"id": "x", "name": "X", "plugin": "rtsp", "config": {"url": f"rtsp://u:{CLAVE}@127.0.0.1:{puerto}/s"}}
    ffprobe = json.dumps({"streams": [{"codec_name": "h264", "width": 768, "height": 432, "r_frame_rate": "10/1"}]})
    ejecutor = Ejecutor((0, ffprobe, ""))
    try:
        r = await cam.comprobar(preset, ahora=AHORA, ejecutar=ejecutor)
    finally:
        servidor.close()
    assert r["estado"] == "ok" and r["causa"] is None
    assert [p["ok"] for p in r["pasos"]] == [True, True]
    assert "h264 768×432 a 10 fps" in r["pasos"][1]["detalle"]
    assert r["destino"] == f"127.0.0.1:{puerto}"
    assert CLAVE not in json.dumps(r)
    assert [a["id"] for a in r["acciones"]] == ["reintentar"]


@pytest.mark.parametrize("excepcion, esperado", [
    (TimeoutError(), "no contesta"),
    (ConnectionRefusedError(), "rechaza el puerto"),
    (OSError(-2, "Name or service not known"), "Name or service not known"),
])
async def test_rtsp_sin_red_explica_la_causa_y_no_corre_ffprobe(monkeypatch, excepcion, esperado):
    async def falla(*a, **k):
        raise excepcion
    monkeypatch.setattr(asyncio, "open_connection", falla)
    ejecutor = Ejecutor()
    r = await cam.comprobar({"id": "x", "plugin": "rtsp", "config": {"url": f"rtsp://u:{CLAVE}@10.9.9.9:554/s"}},
                            ahora=AHORA, ejecutar=ejecutor)
    assert r["estado"] == "falla" and not ejecutor.llamadas
    assert esperado in json.dumps(r, ensure_ascii=False) and r["ayuda"]
    assert CLAVE not in json.dumps(r)


@pytest.mark.parametrize("stderr, causa", [
    (f"Server returned 401 Unauthorized (authorization failed) rtsp://admin:{CLAVE}@h/s", "usuario o la clave"),
    ("Server returned 404 Not Found", "no tiene ese stream"),
])
async def test_rtsp_con_video_caido_distingue_credenciales_y_ruta_sin_filtrar_la_clave(stderr, causa):
    servidor, puerto = await _servidor_tcp()
    preset = {"id": "x", "plugin": "rtsp", "config": {"url": f"rtsp://u:{CLAVE}@127.0.0.1:{puerto}/s"}}
    try:
        r = await cam.comprobar(preset, ahora=AHORA, ejecutar=Ejecutor((1, "", stderr)))
    finally:
        servidor.close()
    assert r["estado"] == "falla" and causa in r["causa"]
    assert CLAVE not in json.dumps(r)


async def test_rtsp_sin_ffprobe_solo_comprueba_el_puerto():
    servidor, puerto = await _servidor_tcp()
    try:
        r = await cam.comprobar({"id": "x", "plugin": "rtsp", "config": {"url": f"rtsp://127.0.0.1:{puerto}/s"}},
                                ahora=AHORA, ejecutar=Ejecutor((127, "", "ffprobe: no disponible")))
    finally:
        servidor.close()
    assert r["estado"] == "ok" and "solo se comprobó el puerto" in r["pasos"][1]["detalle"]


# --- comprobar OAK-D ---------------------------------------------------------------------------

OAK = {"id": "oak_d_lab", "name": "OAK-D", "plugin": "oak_d", "config": {"url": "169.254.31.137"}}
SONDA = "print('sonda')"


async def test_oakd_ok_corre_la_sonda_apartada_en_el_contenedor_del_motor():
    ejecutor = Ejecutor((0, ("depthai 2.32 → conectando\nconectada en 9.4 s: OAK-D-PRO-POE 1944\n"
                             "OK: cuadro 320x180 recibido.\n"), ""))
    r = await cam.comprobar(OAK, ahora=AHORA, ejecutar=ejecutor, motor_contenedor="eovrt-mp-gdino-tiny-560-1",
                            sonda=SONDA)
    assert r["estado"] == "ok"
    (cmd, entrada), = ejecutor.llamadas
    assert cmd == ["docker", "exec", "-i", "eovrt-mp-gdino-tiny-560-1", "python3.11", "-", "169.254.31.137"]
    assert entrada == SONDA.encode()  # entra por stdin: un proceso aparte, no el servidor del motor
    assert "OAK-D-PRO-POE" in r["pasos"][-1]["detalle"] and "9.4 s" in r["pasos"][-1]["detalle"]


async def test_oakd_no_se_abre_con_una_sesion_en_curso():
    ejecutor = Ejecutor()
    r = await cam.comprobar(OAK, ahora=AHORA, ejecutar=ejecutor, motor_contenedor="c", sonda=SONDA, en_uso=True)
    assert r["estado"] == "en_uso" and not ejecutor.llamadas


async def test_oakd_sin_motor_activo_lo_dice_y_no_intenta_nada():
    ejecutor = Ejecutor()
    r = await cam.comprobar(OAK, ahora=AHORA, ejecutar=ejecutor, motor_contenedor=None, sonda=SONDA)
    assert r["estado"] == "falla" and "motor de detección activo" in r["causa"] and not ejecutor.llamadas


async def test_oakd_que_no_responde_da_los_pasos_fisicos_y_nombra_la_ip_duplicada():
    salida = "depthai 2.32 → conectando\nFALLA: X_LINK_DEVICE_NOT_FOUND\n"
    host = {"presente": True, "edad_s": 120.0, "datos": {"chequeos": {"ruta_camara": {
        "ok": False, "detalle": "la IP de la camara (169.254.31.137) es la de esta misma PC: ..."}}}}
    r = await cam.comprobar(OAK, ahora=AHORA, ejecutar=Ejecutor((1, salida, "")), motor_contenedor="c",
                            sonda=SONDA, host=host)
    assert r["estado"] == "falla" and "X_LINK_DEVICE_NOT_FOUND" in r["pasos"][-1]["detalle"]
    assert "misma PC" in r["ayuda"][0] and "hace 2 min" in r["ayuda"][0]
    assert any("DATA IN" in linea and "PoE OUT" in linea for linea in r["ayuda"])
    assert [a["id"] for a in r["acciones"]] == ["reintentar"]


async def test_oakd_ocupada_ofrece_reiniciar_el_motor():
    salida = "FALLA: X_LINK_DEVICE_ALREADY_IN_USE\nPISTA: Otro proceso tiene la cámara (media-plane nativo).\n"
    r = await cam.comprobar(OAK, ahora=AHORA, ejecutar=Ejecutor((1, salida, "")), motor_contenedor="c", sonda=SONDA)
    assert r["estado"] == "falla" and "Otro proceso" in r["causa"]
    assert [a["id"] for a in r["acciones"]] == ["reiniciar_motor", "reintentar"]


async def test_oakd_con_el_motor_apagado_a_mitad_de_camino_ofrece_reiniciarlo():
    r = await cam.comprobar(OAK, ahora=AHORA, ejecutar=Ejecutor((1, "", "Error response from daemon: container c is not running")),
                            motor_contenedor="c", sonda=SONDA)
    assert r["estado"] == "falla" and "dentro del motor" in r["causa"]
    assert [a["id"] for a in r["acciones"]] == ["reiniciar_motor", "reintentar"]


# --- estado a la vista (sin abrir la cámara) -----------------------------------------------------

DVR = {"id": "dvr", "name": "DVR", "plugin": "rtsp", "config": {"url": URL_RTSP}}


class _Escritor:
    def __init__(self): self.cerrado = False
    def close(self): self.cerrado = True
    async def wait_closed(self): return None


def _conecta(excepcion: BaseException | None = None):
    llamadas: list[tuple] = []

    async def conectar(host, puerto):
        llamadas.append((host, puerto))
        if excepcion is not None:
            raise excepcion
        return None, _Escritor()
    conectar.llamadas = llamadas
    return conectar


async def test_estado_rtsp_activa_si_el_puerto_contesta_y_no_filtra_la_clave():
    conectar = _conecta()
    r = await cam.estado_pasivo(DVR, ultimo=None, ahora_s=1000.0, conectar=conectar)
    assert r["estado"] == "activa" and "169.254.31.140:554 responde" in r["detalle"]
    assert conectar.llamadas == [("169.254.31.140", 554)]
    assert CLAVE not in json.dumps(r)


@pytest.mark.parametrize("excepcion, texto", [
    (TimeoutError(), "no contesta"),
    (ConnectionRefusedError(), "rechaza el puerto 554"),
    (OSError(113, "No route to host"), "No route to host"),
])
async def test_estado_rtsp_inactiva_si_no_hay_camino(excepcion, texto):
    r = await cam.estado_pasivo(DVR, ultimo=None, ahora_s=0.0, conectar=_conecta(excepcion))
    assert r["estado"] == "inactiva" and texto in r["detalle"]


async def test_estado_rtsp_con_puerto_vivo_pero_la_ultima_prueba_fallo_es_problema():
    falla = ({"estado": "falla", "causa": "La cámara rechazó el usuario o la clave."}, 940.0)
    r = await cam.estado_pasivo(DVR, ultimo=falla, ahora_s=1000.0, conectar=_conecta())
    assert r["estado"] == "problema" and "usuario o la clave" in r["detalle"] and "hace 60 s" in r["detalle"]
    # Una falla vieja ya no vale: el puerto contesta y no hay otra evidencia.
    vieja = ({"estado": "falla", "causa": "x"}, 0.0)
    r = await cam.estado_pasivo(DVR, ultimo=vieja, ahora_s=cam.VIGENCIA_COMPROBACION_S + 5, conectar=_conecta())
    assert r["estado"] == "activa"


async def test_estado_rtsp_sin_url_es_inactiva_sin_intentar_nada():
    conectar = _conecta()
    r = await cam.estado_pasivo({"id": "x", "plugin": "rtsp", "config": {}}, ultimo=None, ahora_s=0.0, conectar=conectar)
    assert r["estado"] == "inactiva" and not conectar.llamadas


async def test_estado_oak_d_nunca_se_sondea_y_sale_de_la_ultima_comprobacion():
    conectar = _conecta()
    r = await cam.estado_pasivo(OAK, ultimo=None, ahora_s=0.0, conectar=conectar)
    assert r["estado"] == "sin_comprobar" and "Comprobar" in r["detalle"]
    ok = ({"estado": "ok", "causa": None}, 700.0)
    r = await cam.estado_pasivo(OAK, ultimo=ok, ahora_s=1000.0, conectar=conectar)
    assert r["estado"] == "activa" and "hace 5 min" in r["detalle"]
    mal = ({"estado": "falla", "causa": "La OAK-D no responde en 169.254.31.137."}, 940.0)
    r = await cam.estado_pasivo(OAK, ultimo=mal, ahora_s=1000.0, conectar=conectar)
    assert r["estado"] == "inactiva" and "no responde" in r["detalle"]
    assert not conectar.llamadas  # la OAK-D admite una sola conexión: ni un intento


async def test_estado_oak_d_con_una_comprobacion_vieja_vuelve_a_sin_comprobar():
    vieja = ({"estado": "ok", "causa": None}, 0.0)
    r = await cam.estado_pasivo(OAK, ultimo=vieja, ahora_s=cam.VIGENCIA_COMPROBACION_S + 1, conectar=_conecta())
    assert r["estado"] == "sin_comprobar"
