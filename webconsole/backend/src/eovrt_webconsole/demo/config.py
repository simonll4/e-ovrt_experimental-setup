"""Configs de la demo: plantillas versionadas → configs resueltas, y el chequeo de lo congelado.

Las plantillas viven en `experiments/demo_defensa/` (la OAK-D) y
`experiments/demo_defensa_ensayo/` (la cámara de ensayo por RTSP). Sus marcadores
`${...}` dependen del despliegue —en compose los servicios se llaman por nombre
(`mp-gdino-tiny-560`, `control-plane`, `mosquitto`); en nativo, por loopback— y se
resuelven acá, al apretar Iniciar. Así la misma plantilla sirve en la Victus (compose)
y en un entorno nativo, y la carpeta de la sesión guarda exactamente lo que se mandó.

El prompt set va por referencia (`prompts.ref`) y se resuelve al set congelado completo
de `prompts/`, el mismo dict que manda «Nueva corrida»: la demo no puede usar otra
redacción que la evaluada.
"""
from __future__ import annotations

import hashlib
import os
import string
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml

from eovrt_webconsole.prompt_store import classes_sha256
from eovrt_webconsole.repo_catalog import get_prompt_set

# Variante -> carpeta de experiments/ con su `media.template.yaml`. Control y
# distribución son siempre los de demo_defensa: solo cambia la fuente.
VARIANTES = {"oakd": "demo_defensa", "ensayo": "demo_defensa_ensayo"}
_BASE = "demo_defensa"
_CONGELADO = "congelado.yaml"
_EXPLORACION = "exploracion.yaml"
MOTOR_DEMO = "mp-gdino-tiny-560"


class ConfigDemoError(ValueError):
    """Una plantilla o lo congelado no se pudieron resolver: la demo no arranca."""


@dataclass(frozen=True)
class Despliegue:
    """Cómo se llaman los servicios entre sí en este despliegue."""

    modo: str  # "compose" | "nativo"
    workspace: Path
    media_bus_endpoint: str
    alert_bus_endpoint: str
    mqtt_host: str
    mqtt_port: int
    ensayo_rtsp_url: str

    def marcadores(self) -> dict[str, str]:
        return {
            "EOVRT_WORKSPACE": str(self.workspace),
            "EOVRT_MEDIA_BUS_ENDPOINT": self.media_bus_endpoint,
            "EOVRT_ALERT_BUS_ENDPOINT": self.alert_bus_endpoint,
            "EOVRT_MQTT_HOST": self.mqtt_host,
            "EOVRT_MQTT_PORT": str(self.mqtt_port),
            "EOVRT_ENSAYO_RTSP_URL": self.ensayo_rtsp_url,
        }


def despliegue(settings: Any, target: str | None, env: Mapping[str, str] | None = None) -> Despliegue:
    """Deriva los endpoints del despliegue.

    Compose (`EOVRT_CONSOLE_COMPOSE_DIR` definido): nombres de servicio de la red
    `eovrt` (paridad de rutas y endpoints internos, README de infra/platform). Nativo:
    los hosts de las URLs de servicio de la consola. El broker y la cámara de ensayo
    admiten override por entorno (`EOVRT_CONSOLE_MQTT_HOST`/`_PORT`,
    `EOVRT_CONSOLE_ENSAYO_RTSP_URL`).
    """
    env = os.environ if env is None else env
    compose = settings.compose_dir is not None
    if compose:
        media_host = target or MOTOR_DEMO
        mqtt_default = "mosquitto"
        rtsp_default = "rtsp://mediamtx:8554/ensayo"
    else:
        media_host = urlparse(settings.service_url).hostname or "127.0.0.1"
        mqtt_default = "127.0.0.1"
        rtsp_default = "rtsp://127.0.0.1:8554/ensayo"
    control_host = urlparse(settings.control_service_url).hostname or "127.0.0.1"
    return Despliegue(
        modo="compose" if compose else "nativo",
        workspace=Path(settings.repo_root).parent,
        media_bus_endpoint=f"tcp://{media_host}:5557",
        alert_bus_endpoint=f"tcp://{control_host}:5558",
        mqtt_host=env.get("EOVRT_CONSOLE_MQTT_HOST", mqtt_default),
        mqtt_port=int(env.get("EOVRT_CONSOLE_MQTT_PORT", "1883")),
        ensayo_rtsp_url=env.get("EOVRT_CONSOLE_ENSAYO_RTSP_URL", rtsp_default),
    )


def _render(path: Path, marcadores: Mapping[str, str]) -> dict:
    try:
        texto = string.Template(path.read_text(encoding="utf-8")).substitute(marcadores)
    except OSError as exc:
        raise ConfigDemoError(f"no se pudo leer la plantilla {path}: {exc}") from exc
    except (KeyError, ValueError) as exc:
        raise ConfigDemoError(f"marcador sin resolver en {path.name}: {exc}") from exc
    data = yaml.safe_load(texto)
    if not isinstance(data, dict):
        raise ConfigDemoError(f"la plantilla {path.name} no es un mapa YAML")
    return data


def _resolver_prompts(prompts_dir: Path, media: dict) -> dict:
    prompts = dict(media.get("prompts") or {})
    ref = prompts.pop("ref", None)
    if ref is None:
        return media
    prompt_set = get_prompt_set(prompts_dir, ref)
    if prompt_set is None:
        raise ConfigDemoError(f"prompt set desconocido: {ref!r}")
    return {**media, "prompts": {"set_inline": prompt_set, **prompts}}


def resolver_exploracion(repo_root: Path, motor: str | None, camara: str | None) -> dict | None:
    """Valida un pedido de exploración (RT-05) contra la lista cerrada de `exploracion.yaml`.

    Sin motor ni cámara no hay exploración (None). Con alguno, los dos tienen que estar en la
    lista; la cámara por defecto es la de la demo. Devuelve lo que la sesión registra.
    """
    if not motor and not camara:
        return None
    path = Path(repo_root) / "experiments" / _BASE / _EXPLORACION
    try:
        datos = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigDemoError(f"no se pudo leer {path}: {exc}") from exc
    motores, camaras = datos.get("motores") or {}, datos.get("camaras") or {}
    motor = motor or MOTOR_DEMO
    camara = camara or next(iter(camaras), None)
    if motor not in motores:
        raise ConfigDemoError(f"motor fuera de la exploración: {motor!r} (opciones: {sorted(motores)})")
    if camara not in camaras:
        raise ConfigDemoError(f"cámara fuera de la exploración: {camara!r} (opciones: {sorted(camaras)})")
    return {"motor": motor, "modelo": motores[motor]["modelo"],
            "familia": motores[motor].get("familia"), "camara": camara,
            "ingest": dict(camaras[camara])}


def resolver_configs(repo_root: Path, variante: str, desp: Despliegue,
                     exploracion: dict | None = None) -> dict[str, dict]:
    """Las tres configs de la sesión, ya resueltas (media, control, distribution). Con una
    exploración, la cámara de la plantilla se pisa con la de la lista (el resto, igual)."""
    if variante not in VARIANTES:
        raise ConfigDemoError(f"variante desconocida: {variante!r} (opciones: {sorted(VARIANTES)})")
    experiments = Path(repo_root) / "experiments"
    marcadores = desp.marcadores()
    media = _render(experiments / VARIANTES[variante] / "media.template.yaml", marcadores)
    if exploracion:
        ingest = media.setdefault("ingest", {})
        ingest["config"] = {**(ingest.get("config") or {}), **exploracion["ingest"]}
    control = _render(experiments / _BASE / "control.template.yaml", marcadores)
    distribucion = _render(experiments / _BASE / "distribution.template.yaml", marcadores)
    return {
        "media": _resolver_prompts(Path(repo_root) / "prompts", media),
        "control": control,
        "distribution": distribucion,
    }


def _sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _item(id_: str, nombre: str, ok: bool, esperado: Any, actual: Any, **extra: Any) -> dict:
    return {"id": id_, "nombre": nombre, "ok": bool(ok), "esperado": esperado, "actual": actual,
            **extra}


def _igual(a: Any, b: Any) -> bool:
    try:
        return abs(float(a) - float(b)) < 1e-9
    except (TypeError, ValueError):
        return False


def cargar_congelado(repo_root: Path) -> dict:
    path = Path(repo_root) / "experiments" / _BASE / _CONGELADO
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigDemoError(f"no se pudo leer {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigDemoError(f"{path} no es un mapa YAML")
    return data


def verificar_congelado(repo_root: Path, configs: Mapping[str, dict], modelo: dict | None) -> dict:
    """Compara lo que la sesión va a usar con las huellas del tag `informe-2026`.

    Cinco chequeos: el archivo del prompt set y el set que efectivamente se manda
    (su `frozen_sha256`, la convención de `prompt_store.classes_sha256`), el archivo
    del pattern set que referencia la config de control, el catálogo del modelo y lo
    que el motor reporta tener cargado (`/api/model`), y el enfriamiento/QoS de la
    distribución. `modelo=None` (motor caído) deja ese chequeo en falso.
    """
    repo_root = Path(repo_root)
    workspace = repo_root.parent
    esperado = cargar_congelado(repo_root)
    items: list[dict] = []

    ps = esperado["prompt_set"]
    archivo_ps = repo_root / "prompts" / Path(ps["archivo"]).name
    items.append(_item(
        "prompt_set_archivo", f"Prompt set {ps['id']} (archivo)",
        _sha256(archivo_ps) == ps["sha256_archivo"], ps["sha256_archivo"], _sha256(archivo_ps),
    ))
    enviado = ((configs.get("media") or {}).get("prompts") or {}).get("set_inline")
    try:
        congelado_yaml = (yaml.safe_load(archivo_ps.read_text(encoding="utf-8")) or {}).get("prompt_set")
    except (OSError, yaml.YAMLError):
        congelado_yaml = None
    hash_enviado = classes_sha256(enviado.get("classes")) if isinstance(enviado, dict) else None
    items.append(_item(
        "prompt_set_enviado", f"Prompt set enviado al motor ({ps['id']})",
        hash_enviado == ps["frozen_sha256"] and enviado == congelado_yaml,
        ps["frozen_sha256"], hash_enviado,
    ))

    pat = esperado["pattern_set"]
    archivo_pat = Path(((configs.get("control") or {}).get("patterns") or {}).get("file") or "")
    sha_pat = _sha256(archivo_pat) if archivo_pat.name else None
    items.append(_item(
        "pattern_set", f"Pattern set {pat['id']}",
        archivo_pat.name == Path(pat["archivo"]).name and sha_pat == pat["sha256_archivo"],
        pat["sha256_archivo"], sha_pat, ruta=str(archivo_pat),
    ))

    mod = esperado["modelo"]
    sha_mod = _sha256(workspace / mod["archivo"])
    items.append(_item(
        "modelo_catalogo", f"Catálogo del modelo {mod['ref']}",
        sha_mod == mod["sha256_archivo"], mod["sha256_archivo"], sha_mod,
    ))
    th = (modelo or {}).get("thresholds") or {}
    en_uso = {"ref": (modelo or {}).get("ref"), "box": th.get("box"), "text": th.get("text")}
    items.append(_item(
        "modelo_en_uso", "Modelo cargado en el motor",
        modelo is not None and en_uso["ref"] == mod["ref"]
        and _igual(en_uso["box"], mod["box_threshold"]) and _igual(en_uso["text"], mod["text_threshold"]),
        {"ref": mod["ref"], "box": mod["box_threshold"], "text": mod["text_threshold"]}, en_uso,
    ))

    dist = configs.get("distribution") or {}
    actual_dist = {
        "cooldown_ms": (dist.get("notification_policy") or {}).get("cooldown_ms"),
        "qos": (dist.get("channel") or {}).get("qos"),
    }
    items.append(_item(
        "enfriamiento", "Enfriamiento y QoS de la distribución",
        actual_dist == {"cooldown_ms": esperado["distribucion"]["cooldown_ms"],
                        "qos": esperado["distribucion"]["qos"]},
        esperado["distribucion"], actual_dist,
    ))
    return {"tag": esperado.get("tag"), "ok": all(i["ok"] for i in items), "items": items}


def escribir_configs(destino: Path, configs: Mapping[str, dict]) -> dict[str, Path]:
    """Persiste las configs resueltas en la carpeta de la sesión (lo que se mandó)."""
    destino.mkdir(parents=True, exist_ok=True)
    rutas: dict[str, Path] = {}
    for plano, data in configs.items():
        path = destino / f"{plano}.yaml"
        path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
        rutas[plano] = path
    return rutas
