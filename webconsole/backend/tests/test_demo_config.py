"""Demo: plantillas → configs resueltas y el chequeo de lo congelado (spec 2026-10-23 §3.1)."""
from __future__ import annotations

import hashlib
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from eovrt_webconsole.demo import config as demo_config
from eovrt_webconsole.settings import ConsoleSettings
from tests.demo_fixtures import MODELO_OK, REPO_REAL, WORKSPACE_REAL
from tests.demo_fixtures import repo_demo as _repo_demo


def _settings(repo: Path, *, compose: bool) -> ConsoleSettings:
    return ConsoleSettings(
        service_url="http://localhost:8080",
        repo_root=repo,
        frozen_set_ids=frozenset(),
        control_service_url="http://localhost:8081",
        compose_dir=repo / "infra" / "platform" if compose else None,
    )


def test_despliegue_compose_usa_nombres_de_servicio(tmp_path):
    repo = _repo_demo(tmp_path)
    desp = demo_config.despliegue(_settings(repo, compose=True), "mp-gdino-tiny-560", env={})
    assert desp.modo == "compose"
    assert desp.media_bus_endpoint == "tcp://mp-gdino-tiny-560:5557"
    assert desp.mqtt_host == "mosquitto"
    assert desp.ensayo_rtsp_url == "rtsp://mediamtx:8554/ensayo"
    assert desp.workspace == repo.parent


def test_despliegue_nativo_usa_loopback(tmp_path):
    repo = _repo_demo(tmp_path)
    desp = demo_config.despliegue(_settings(repo, compose=False), None, env={})
    assert desp.modo == "nativo"
    assert desp.media_bus_endpoint == "tcp://localhost:5557"
    assert desp.alert_bus_endpoint == "tcp://localhost:5558"
    assert desp.mqtt_host == "127.0.0.1"


def test_resolver_oakd_960x540_a_5fps_escena_y_prompt_set_congelado(tmp_path):
    repo = _repo_demo(tmp_path)
    desp = demo_config.despliegue(_settings(repo, compose=True), None, env={})
    configs = demo_config.resolver_configs(repo, "oakd", desp)
    ingest = configs["media"]["ingest"]
    assert ingest["plugin"] == "oak_d"
    assert ingest["config"]["isp_scale"] == [1, 2] and ingest["config"]["fps"] == 5
    assert "max_units" not in configs["media"]["run"]
    assert configs["media"]["run"]["save_previews"] is True
    assert configs["media"]["bus"] == {"wait_for_subscriber_ms": 10000}
    set_inline = configs["media"]["prompts"]["set_inline"]
    assert set_inline["id"] == "cr01_cr02_v2_short"
    assert "ref" not in configs["media"]["prompts"]
    # Escena, nunca el _subject: la demo muestra una sola persona en cuadro.
    assert configs["control"]["patterns"]["file"].endswith("/cr01_cr02_v2.yaml")
    assert "track_persons" not in configs["control"]["input"]
    assert configs["control"]["input"]["bus"]["endpoint"] == "tcp://mp-gdino-tiny-560:5557"
    assert configs["distribution"]["channel"]["host"] == "mosquitto"
    assert configs["distribution"]["channel"]["port"] == 1883
    assert configs["distribution"]["notification_policy"]["cooldown_ms"] == 30000


def test_resolver_ensayo_cambia_solo_la_fuente(tmp_path):
    repo = _repo_demo(tmp_path)
    desp = demo_config.despliegue(_settings(repo, compose=True), None, env={})
    oakd = demo_config.resolver_configs(repo, "oakd", desp)
    ensayo = demo_config.resolver_configs(repo, "ensayo", desp)
    assert ensayo["media"]["ingest"] == {
        "plugin": "rtsp", "config": {"url": "rtsp://mediamtx:8554/ensayo", "warmup_frames": 5},
    }
    assert ensayo["control"] == oakd["control"]
    assert ensayo["distribution"] == oakd["distribution"]
    assert ensayo["media"]["prompts"] == oakd["media"]["prompts"]
    assert ensayo["media"]["bus"] == oakd["media"]["bus"] == {"wait_for_subscriber_ms": 10000}


def test_variante_desconocida(tmp_path):
    repo = _repo_demo(tmp_path)
    desp = demo_config.despliegue(_settings(repo, compose=False), None, env={})
    with pytest.raises(demo_config.ConfigDemoError):
        demo_config.resolver_configs(repo, "webcam", desp)


def test_congelado_ok_con_lo_del_repo(tmp_path):
    repo = _repo_demo(tmp_path)
    desp = demo_config.despliegue(_settings(repo, compose=True), None, env={})
    configs = demo_config.resolver_configs(repo, "oakd", desp)
    res = demo_config.verificar_congelado(repo, configs, MODELO_OK)
    assert res["ok"], [i for i in res["items"] if not i["ok"]]
    assert res["tag"] == "informe-2026"
    assert {i["id"] for i in res["items"]} == {
        "prompt_set_archivo", "prompt_set_enviado", "pattern_set", "modelo_catalogo",
        "modelo_en_uso", "enfriamiento",
    }


def test_congelado_detecta_un_pattern_set_tocado(tmp_path):
    repo = _repo_demo(tmp_path)
    desp = demo_config.despliegue(_settings(repo, compose=True), None, env={})
    configs = demo_config.resolver_configs(repo, "oakd", desp)
    patron = Path(configs["control"]["patterns"]["file"])
    patron.write_text(patron.read_text() + "\n# tocado\n")
    res = demo_config.verificar_congelado(repo, configs, MODELO_OK)
    assert not res["ok"]
    assert [i["id"] for i in res["items"] if not i["ok"]] == ["pattern_set"]


def test_congelado_detecta_otro_modelo_cargado(tmp_path):
    repo = _repo_demo(tmp_path)
    desp = demo_config.despliegue(_settings(repo, compose=True), None, env={})
    configs = demo_config.resolver_configs(repo, "oakd", desp)
    otro = {"ref": "grounding-dino/gdino-base-560", "thresholds": {"box": 0.3, "text": 0.25}}
    res = demo_config.verificar_congelado(repo, configs, otro)
    assert [i["id"] for i in res["items"] if not i["ok"]] == ["modelo_en_uso"]
    assert not demo_config.verificar_congelado(repo, configs, None)["ok"]


def test_congelado_detecta_una_frase_cambiada_en_el_set_enviado(tmp_path):
    repo = _repo_demo(tmp_path)
    desp = demo_config.despliegue(_settings(repo, compose=True), None, env={})
    configs = demo_config.resolver_configs(repo, "oakd", desp)
    configs["media"]["prompts"]["set_inline"]["classes"][1]["phrasings"]["default"] = ["hard hat"]
    res = demo_config.verificar_congelado(repo, configs, MODELO_OK)
    assert [i["id"] for i in res["items"] if not i["ok"]] == ["prompt_set_enviado"]


def test_las_huellas_de_congelado_son_las_del_tag_informe_2026():
    """Re-deriva las huellas desde el tag cuando hay git y el tag (si no, se saltea)."""
    if shutil.which("git") is None:
        pytest.skip("sin git")
    esperado = yaml.safe_load((REPO_REAL / "experiments/demo_defensa/congelado.yaml").read_text())
    for clave in ("prompt_set", "pattern_set", "modelo"):
        repo_rel, archivo = esperado[clave]["archivo"].split("/", 1)
        try:
            contenido = subprocess.run(
                ["git", "-C", str(WORKSPACE_REAL / repo_rel), "show", f"informe-2026:{archivo}"],
                check=True, capture_output=True,
            ).stdout
        except (subprocess.CalledProcessError, OSError):
            pytest.skip(f"sin el tag informe-2026 en {repo_rel}")
        assert hashlib.sha256(contenido).hexdigest() == esperado[clave]["sha256_archivo"], clave
