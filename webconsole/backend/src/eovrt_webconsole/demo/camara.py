"""La cámara de la demo: elegirla y comprobar que se ve (✎ 2026-11-01).

Hasta acá la demo usaba SIEMPRE la OAK-D de la plantilla. Ahora se elige entre los presets de
`cameras/` (OAK-D y RTSP) desde la pantalla, y se puede comprobar que la cámara se ve antes de
iniciar. Tres reglas:

* **Lo medido no se toca.** Con la OAK-D la plantilla manda (960×540 a 5 fps): del preset solo
  se toma la dirección. Una cámara de otro tipo (RTSP) usa lo que dice su preset.
* **La comprobación no estorba.** La OAK-D admite una sola conexión a la vez (F-101.5): con una
  sesión o un experimento en curso no se la abre. La prueba corre en un proceso APARTE dentro del
  contenedor del motor activo (el mismo `oakd_probe.py` del manual), nunca en el servidor del motor.
* **Las credenciales no se muestran ni se guardan.** Un preset RTSP trae `user:clave@` en la URL:
  a la pantalla solo llega `host:puerto`, los mensajes de error se redactan y, al cerrar la
  sesión, la config guardada se limpia (ver `redactar`).
"""
from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml

PLUGINS_APTOS = ("oak_d", "rtsp")
CAMARA_POR_DEFECTO = "oak_d_lab"
_ID = re.compile(r"^[a-z0-9_-]+$")
_URL_CON_CLAVE = re.compile(r"(rtsp://[^:/@\s]+:)[^@\s]+@")

#: (comando, stdin o None, timeout en s) -> (código, stdout, stderr)
Ejecutor = Callable[[list[str], bytes | None, float], Awaitable[tuple[int, str, str]]]


class CamaraDesconocida(Exception):
    """El id no existe en `cameras/` o su plugin no sirve para la demo."""


def redactar(texto: str) -> str:
    """`rtsp://user:clave@host` -> `rtsp://user:***@host`."""
    return _URL_CON_CLAVE.sub(r"\1***@", texto)


async def ejecutar_subproceso(cmd: list[str], entrada: bytes | None, timeout: float) -> tuple[int, str, str]:
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE if entrada is not None else asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError:
        return 127, "", f"{cmd[0]}: no disponible en este entorno"
    try:
        salida, error = await asyncio.wait_for(proc.communicate(entrada), timeout)
    except TimeoutError:
        proc.kill()
        await proc.wait()
        return 124, "", f"tiempo agotado ({timeout:.0f} s)"
    return proc.returncode or 0, salida.decode(errors="replace"), error.decode(errors="replace")


# --- presets ---------------------------------------------------------------------------------


def _leer(path: Path) -> dict | None:
    try:
        data = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("camera")
    except (OSError, yaml.YAMLError, AttributeError):
        return None
    return data if isinstance(data, dict) and data.get("id") and data.get("plugin") else None


def destino(preset: dict) -> str:
    """A dónde apunta el preset, SIN credenciales (es lo único que viaja a la pantalla)."""
    cfg = preset.get("config") or {}
    if preset.get("plugin") == "rtsp":
        url = urlparse(str(cfg.get("url") or ""))
        return f"{url.hostname or '?'}:{url.port or 554}"
    return str(cfg.get("url") or cfg.get("ip") or "?")


def resumen(preset: dict) -> dict:
    return {"id": preset["id"], "nombre": preset.get("name") or preset["id"],
            "plugin": preset["plugin"], "destino": destino(preset)}


def cargar(cameras_dir: Path, camara_id: str) -> dict:
    if not _ID.match(camara_id or ""):
        raise CamaraDesconocida(f"id de cámara inválido: {camara_id!r}")
    preset = _leer(Path(cameras_dir) / f"{camara_id}.yaml")
    if preset is None:
        raise CamaraDesconocida(f"no hay un preset de cámara {camara_id!r} en cameras/")
    if preset["plugin"] not in PLUGINS_APTOS:
        raise CamaraDesconocida(
            f"la cámara {camara_id!r} (plugin {preset['plugin']}) no sirve para la demo: "
            f"solo {', '.join(PLUGINS_APTOS)}")
    return preset


def listar(cameras_dir: Path) -> list[dict]:
    """Los presets utilizables, con el de la demo (la OAK-D del laboratorio) marcado."""
    filas = []
    for path in sorted(Path(cameras_dir).glob("*.yaml")):
        preset = _leer(path)
        if preset and preset["plugin"] in PLUGINS_APTOS and _ID.match(preset["id"]):
            filas.append(resumen(preset))
    por_defecto = next((f["id"] for f in filas if f["id"] == CAMARA_POR_DEFECTO),
                       next((f["id"] for f in filas if f["plugin"] == "oak_d"), None))
    return [{**f, "por_defecto": f["id"] == por_defecto} for f in filas]


def aplicar(ingest: dict | None, preset: dict) -> dict:
    """La fuente de la sesión con la cámara elegida.

    Mismo tipo que la plantilla (OAK-D): la plantilla manda —resolución y cadencia son lo
    medido— y del preset se toma solo la dirección. Otro tipo: lo que dice el preset.
    """
    cfg = dict(preset.get("config") or {})
    ingest = ingest or {}
    if preset["plugin"] == ingest.get("plugin"):
        base = dict(ingest.get("config") or {})
        direccion = cfg.get("url") or cfg.get("ip")
        if direccion:
            base["url"] = direccion
        return {**ingest, "config": base}
    return {"plugin": preset["plugin"], "config": cfg}


# --- estado a la vista (sin molestar a la cámara) ---------------------------------------------

#: Hasta cuándo vale una comprobación explícita para decir «activa»/«inactiva» de una OAK-D.
VIGENCIA_COMPROBACION_S = 900.0
Conectar = Callable[..., Awaitable[Any]]


def _hace(segundos: float) -> str:
    if segundos < 90:
        return f"hace {segundos:.0f} s"
    if segundos < 5400:
        return f"hace {segundos / 60:.0f} min"
    return f"hace {segundos / 3600:.0f} h"


async def estado_pasivo(preset: dict, *, ultimo: tuple[dict, float] | None, ahora_s: float,
                        conectar: Conectar = asyncio.open_connection, espera_s: float = 1.5) -> dict:
    """Si la cámara está activa, para mostrarlo siempre en el selector. NUNCA abre la cámara.

    * **RTSP**: un intento de conexión TCP al puerto (liviano; admite varias conexiones). «Activa» =
      el puerto contesta. Si la última comprobación completa (con video) falló hace poco, se dice:
      que el puerto conteste no quiere decir que entregue video (clave mala, ruta equivocada).
    * **OAK-D**: abrirla ocupa su única conexión (F-101.5), así que no se la sondea: el estado sale de
      la última comprobación explícita (`comprobar`), con su antigüedad. Sin ninguna, «sin comprobar».

    Devuelve `{estado: activa|inactiva|problema|sin_comprobar, detalle}`.
    """
    prueba = None  # (resultado, antigüedad_s) de la última comprobación explícita, si es reciente
    if ultimo is not None and ahora_s - ultimo[1] <= VIGENCIA_COMPROBACION_S:
        prueba = (ultimo[0], ahora_s - ultimo[1])

    if preset["plugin"] == "oak_d":
        if prueba is None:
            return {"estado": "sin_comprobar",
                    "detalle": "La OAK-D admite una sola conexión: no se sondea sola. Tocá «Comprobar»."}
        res, edad = prueba
        if res["estado"] == "ok":
            return {"estado": "activa", "detalle": f"Comprobada {_hace(edad)}: se ve."}
        return {"estado": "inactiva", "detalle": f"Comprobada {_hace(edad)}: {res.get('causa') or 'no se ve'}"}

    url = urlparse(str((preset.get("config") or {}).get("url") or ""))
    host, puerto = url.hostname or "", url.port or 554
    if not host:
        return {"estado": "inactiva", "detalle": "El preset no tiene URL."}
    t0 = asyncio.get_running_loop().time()
    try:
        _, escritor = await asyncio.wait_for(conectar(host, puerto), espera_s)
    except TimeoutError:
        return {"estado": "inactiva", "detalle": f"{host}:{puerto} no contesta."}
    except ConnectionRefusedError:
        # El rechazo puede darlo la cámara (otro servicio en ese puerto) o, con la cámara
        # desconectada, la propia PC o el router de la ruta: no se afirma que la cámara responda.
        return {"estado": "inactiva",
                "detalle": f"{host} rechaza el puerto {puerto}: no hay una cámara RTSP escuchando ahí."}
    except OSError as exc:
        return {"estado": "inactiva", "detalle": f"{host}: {exc.strerror or exc}."}
    ms = (asyncio.get_running_loop().time() - t0) * 1000.0
    escritor.close()
    try:
        await escritor.wait_closed()
    except OSError:
        pass
    if prueba is not None and prueba[0]["estado"] == "falla":
        return {"estado": "problema",
                "detalle": f"El puerto contesta, pero la última comprobación ({_hace(prueba[1])}) falló: "
                           f"{prueba[0].get('causa') or 'no entregó video'}"}
    return {"estado": "activa", "detalle": f"{host}:{puerto} responde ({ms:.0f} ms)."}


# --- comprobación -----------------------------------------------------------------------------

_PASOS_OAKD = [
    ("Conectá la OAK-D por el inyector PoE: puerto DATA IN del lado de la PC (o del switch) y PoE OUT a la "
     "cámara. Si están invertidos, no enciende."),
    "Esperá 10–40 s a que bootee y volvé a comprobar.",
    ("Sin DHCP en el medio: con un router o un switch con DHCP la PC toma otra red y la IP de la cámara "
     "queda inalcanzable."),
    "Si sigue sin verse: desenchufá el PoE 10 s (power-cycle) y repetí.",
]
_PASOS_RTSP = [
    "Revisá que la cámara o el DVR estén encendidos y el cable esté en la Ethernet de esta PC.",
    "La ruta tiene que salir por esa Ethernet y no por el router (`ip route get <ip>` en WSL).",
]


def _paso(id_: str, nombre: str, ok: bool, detalle: str) -> dict:
    return {"id": id_, "nombre": nombre, "ok": ok, "detalle": detalle}


def _acciones(*extra: tuple[str, str]) -> list[dict]:
    return [{"id": i, "etiqueta": e} for i, e in extra] + [{"id": "reintentar", "etiqueta": "Volver a comprobar"}]


def _resultado(preset: dict, estado: str, pasos: list[dict], causa: str | None, ayuda: list[str],
               acciones: list[dict], ahora: str) -> dict:
    return {"camara": preset["id"], "nombre": preset.get("name") or preset["id"],
            "plugin": preset["plugin"], "destino": destino(preset), "estado": estado,
            "causa": causa, "pasos": pasos, "ayuda": ayuda, "acciones": acciones,
            "comprobado_en": ahora}


def _pista_del_host(host: dict | None) -> str | None:
    """La causa más común de «no se ve»: la Ethernet de la PC tomó la IP de la cámara. Solo se
    sabe por el chequeo del host (corre en el host, no en el contenedor)."""
    try:
        ruta = ((host or {}).get("datos") or {}).get("chequeos", {}).get("ruta_camara") or {}
    except AttributeError:
        return None
    if ruta.get("ok") is False and "misma PC" in str(ruta.get("detalle", "")):
        edad = (host or {}).get("edad_s")
        cuando = f" (hace {edad / 60:.0f} min)" if isinstance(edad, (int, float)) else ""
        return ("Según el último chequeo del host" + cuando + ", la IP de la cámara es la de esta misma PC: "
                "la cámara no está en el cable o hay una IP duplicada.")
    return None


async def _comprobar_rtsp(preset: dict, ejecutar: Ejecutor, ahora: str) -> dict:
    url = str((preset.get("config") or {}).get("url") or "")
    if not url:
        return _resultado(preset, "falla", [_paso("preset", "Preset", False, "el preset no tiene `url`")],
                          "El preset RTSP no trae la URL.", ["Corregilo en Cámaras."], _acciones(), ahora)
    u = urlparse(url)
    host, puerto = u.hostname or "", u.port or 554
    pasos: list[dict] = []
    try:
        _, escritor = await asyncio.wait_for(asyncio.open_connection(host, puerto), 4.0)
        escritor.close()
        try:
            await escritor.wait_closed()
        except OSError:
            pass
        pasos.append(_paso("red", "Red", True, f"{host}:{puerto} responde"))
    except TimeoutError:
        pasos.append(_paso("red", "Red", False, f"{host}:{puerto} no contesta (4 s)"))
        return _resultado(preset, "falla", pasos,
                          f"No hay respuesta de {host}:{puerto}: la cámara no está en el cable, está apagada o la IP es otra.",
                          _PASOS_RTSP, _acciones(), ahora)
    except ConnectionRefusedError:
        pasos.append(_paso("red", "Red", False, f"{host} rechaza el puerto {puerto}"))
        return _resultado(preset, "falla", pasos,
                          f"No hay una cámara RTSP escuchando en {host}:{puerto}: la conexión fue rechazada "
                          "(cámara desconectada o apagada, otra IP, o la Ethernet de la PC caída).",
                          [*_PASOS_RTSP, "Si la cámara está bien conectada, revisá la URL del preset en Cámaras."],
                          _acciones(), ahora)
    except OSError as exc:
        pasos.append(_paso("red", "Red", False, redactar(str(exc.strerror or exc))))
        return _resultado(preset, "falla", pasos, f"No se pudo conectar a {host}: {exc.strerror or exc}.",
                          _PASOS_RTSP, _acciones(), ahora)

    codigo, salida, error = await ejecutar(
        ["ffprobe", "-v", "error", "-rtsp_transport", "tcp", "-timeout", "8000000", "-select_streams", "v:0",
         "-show_entries", "stream=codec_name,width,height,r_frame_rate", "-of", "json", url], None, 20.0)
    if codigo == 127:
        pasos.append(_paso("video", "Video", True, "ffprobe no está disponible: solo se comprobó el puerto"))
        return _resultado(preset, "ok", pasos, None, [], _acciones(), ahora)
    stream = None
    if codigo == 0:
        try:
            stream = (json.loads(salida).get("streams") or [None])[0]
        except (ValueError, AttributeError):
            stream = None
    if stream:
        fps = stream.get("r_frame_rate", "?/1").split("/")
        try:
            fps_txt = f"{float(fps[0]) / float(fps[1]):.0f}"
        except (ValueError, ZeroDivisionError, IndexError):
            fps_txt = "?"
        pasos.append(_paso("video", "Video", True,
                           f"{stream.get('codec_name', '?')} {stream.get('width')}×{stream.get('height')} a {fps_txt} fps"))
        return _resultado(preset, "ok", pasos, None, [], _acciones(), ahora)
    texto = redactar(error).strip()
    bajo = texto.lower()
    if "401" in bajo or "unauthorized" in bajo:
        causa, ayuda = "La cámara rechazó el usuario o la clave.", ["Revisá las credenciales del preset en Cámaras."]
    elif "404" in bajo or "not found" in bajo:
        causa, ayuda = "La cámara no tiene ese stream.", ["Revisá la ruta de la URL del preset (p. ej. /Streaming/Channels/1)."]
    elif codigo == 124 or "timed out" in bajo:
        causa, ayuda = "La cámara respondió al puerto pero no entregó video a tiempo.", _PASOS_RTSP
    else:
        causa, ayuda = "La cámara no entregó video.", _PASOS_RTSP
    pasos.append(_paso("video", "Video", False, (texto.splitlines() or ["sin detalle"])[-1][:200]))
    return _resultado(preset, "falla", pasos, causa, ayuda, _acciones(), ahora)


async def _comprobar_oakd(preset: dict, ejecutar: Ejecutor, ahora: str, *, contenedor: str | None,
                          sonda: str | None, en_uso: bool, host: dict | None) -> dict:
    cfg = preset.get("config") or {}
    ip = str(cfg.get("url") or cfg.get("ip") or "")
    if en_uso:
        return _resultado(
            preset, "en_uso", [_paso("uso", "Disponibilidad", False, "hay una sesión o un experimento en curso")],
            "La OAK-D admite una sola conexión a la vez y ahora la está usando una sesión o un experimento.",
            ["Esperá a que termine y volvé a comprobar."], _acciones(), ahora)
    if not contenedor:
        return _resultado(
            preset, "falla", [_paso("motor", "Motor de detección", False, "no hay un motor activo")],
            "No hay un motor de detección activo para hacer la prueba (se abre la cámara desde ahí, como en la corrida).",
            ["Activá un motor en Plataforma, o corré `plataforma.sh up`."], _acciones(), ahora)
    if not ip or sonda is None:
        return _resultado(
            preset, "falla", [_paso("prueba", "Prueba", False, "falta la dirección del preset o el script de prueba")],
            "No se pudo preparar la prueba de la OAK-D.", ["Revisá el preset en Cámaras."], _acciones(), ahora)

    pasos = [_paso("motor", "Motor de detección", True, contenedor)]
    codigo, salida, error = await ejecutar(
        ["docker", "exec", "-i", contenedor, "python3.11", "-", ip], sonda.encode(), 75.0)
    conecto = re.search(r"conectada en ([\d.]+) s: (.+)", salida)
    if codigo == 0 and "OK:" in salida:
        detalle = (f"cuadro recibido de {conecto.group(2).split()[0]}, conectó en {conecto.group(1)} s"
                   if conecto else "cuadro recibido")
        pasos.append(_paso("prueba", "Prueba de la cámara", True, detalle))
        return _resultado(preset, "ok", pasos, None, [], _acciones(), ahora)

    falla = next((linea[6:].strip() for linea in salida.splitlines() if linea.startswith("FALLA:")), "")
    pista = next((linea[6:].strip() for linea in salida.splitlines() if linea.startswith("PISTA:")), "")
    if not falla:
        falla = redactar(error).strip().splitlines()[-1] if error.strip() else f"salió con código {codigo}"
    pasos.append(_paso("prueba", "Prueba de la cámara", False, falla[:240]))
    bajo = (falla + " " + pista).lower()
    ocupada = "already" in bajo or "in_use" in bajo or "otro proceso" in bajo
    extra_acciones: list[tuple[str, str]] = []
    if ocupada:
        causa = "Otro proceso tiene la cámara: la OAK-D admite una sola conexión a la vez."
        ayuda = ["Si fue una sesión anterior, reiniciar el motor libera la cámara.",
                 "Si hay un media-plane nativo u otra instancia mp-* abierta, cerrala."]
        extra_acciones.append(("reiniciar_motor", "Reiniciar el motor"))
    elif "docker" in bajo or "no such container" in bajo or "is not running" in bajo:
        causa = "No se pudo ejecutar la prueba dentro del motor."
        ayuda = ["Reiniciá el motor y volvé a comprobar."]
        extra_acciones.append(("reiniciar_motor", "Reiniciar el motor"))
    else:
        causa = pista or f"La OAK-D no responde en {ip}."
        ayuda = list(_PASOS_OAKD)
    del_host = _pista_del_host(host)
    if del_host:
        ayuda = [del_host, *ayuda]
    return _resultado(preset, "falla", pasos, causa, ayuda, _acciones(*extra_acciones), ahora)


async def comprobar(preset: dict, *, ahora: str, ejecutar: Ejecutor = ejecutar_subproceso,
                    motor_contenedor: str | None = None, sonda: str | None = None, en_uso: bool = False,
                    host: dict | None = None) -> dict:
    """Comprueba que la cámara se ve. Nunca levanta: un fallo es un resultado con su causa."""
    if preset["plugin"] == "oak_d":
        return await _comprobar_oakd(preset, ejecutar, ahora, contenedor=motor_contenedor, sonda=sonda,
                                     en_uso=en_uso, host=host)
    return await _comprobar_rtsp(preset, ejecutar, ahora)


def leer_sonda_oakd(repo_root: Path) -> str | None:
    try:
        return (Path(repo_root) / "infra" / "platform" / "oakd_probe.py").read_text(encoding="utf-8")
    except OSError:
        return None


def limpiar_credenciales(carpeta_config: Path) -> int:
    """Quita `clave` de las URLs RTSP de las configs guardadas de una sesión. Devuelve cuántos
    archivos cambió. Se llama al cerrar: durante la corrida la config tiene que ser la real."""
    cambiados = 0
    for path in Path(carpeta_config).glob("*.yaml"):
        try:
            texto = path.read_text(encoding="utf-8")
        except OSError:
            continue
        limpio = redactar(texto)
        if limpio != texto:
            path.write_text(limpio, encoding="utf-8")
            cambiados += 1
    return cambiados
