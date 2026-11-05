"""Demo: los modos de prompts de `modos.yaml` (✎ 2026-11-01, enmienda de la spec de la demo).

Un modo que no es el campeón manda otro par prompt set + pattern set, pero no uno cualquiera: el
que midió su prueba de la generación 2. Estos tests fijan esa garantía (la huella del payload es
la de results/gen2) y que el modo cambie SOLO los prompts y el pattern set.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from eovrt_webconsole.demo import config as demo_config
from eovrt_webconsole.demo import modos as demo_modos
from eovrt_webconsole.settings import ConsoleSettings
from tests.demo_fixtures import MODELO_OK, REPO_REAL, agregar_modo_exploratorio
from tests.demo_fixtures import repo_demo as _repo_demo

# La prueba de la generación 2 que midió cada modo y la corrida cuyo payload es el del modo.
MEDIDO = {"edir": ("ALR-04", None), "clase_nueva": ("EXT-01", "obra_val")}


def _configs(repo: Path, modo: dict | None = None) -> dict:
    settings = ConsoleSettings(service_url="http://localhost:8080", repo_root=repo,
                               frozen_set_ids=frozenset(), control_service_url="http://localhost:8081",
                               compose_dir=repo / "infra" / "platform")
    desp = demo_config.despliegue(settings, None, env={})
    return demo_config.resolver_configs(repo, "oakd", desp, modo=modo)


def test_la_lista_es_cerrada_y_el_campeon_no_cambia_nada(tmp_path):
    repo = _repo_demo(tmp_path)
    datos = demo_modos.cargar(repo)
    assert datos["default"] == "campeon"
    assert list(datos["modos"]) == ["campeon", "edir", "clase_nueva", "reflective"]
    assert demo_modos.resolver(repo, None) is None
    assert demo_modos.resolver(repo, "campeon") is None
    with pytest.raises(demo_config.ConfigDemoError, match="fuera de la lista"):
        demo_modos.resolver(repo, "bare_head")
    # Sin modo, las configs son exactamente las de siempre (y pasan lo congelado).
    assert _configs(repo) == _configs(repo, None)
    assert demo_config.verificar_congelado(repo, _configs(repo), MODELO_OK)["ok"]


@pytest.mark.parametrize("modo", ["edir", "clase_nueva"])
def test_cada_modo_manda_exactamente_el_payload_que_midio_su_prueba(tmp_path, modo):
    """La huella declarada en modos.yaml es la de results/gen2/<prueba>/configuracion.json, y la
    del payload que arma la consola coincide con ella."""
    repo = _repo_demo(tmp_path)
    resuelto = demo_modos.resolver(repo, modo)
    configs = _configs(repo, resuelto)
    assert configs["media"]["prompts"] == demo_modos.payload(resuelto)
    assert demo_modos.huella_prompts(configs["media"]["prompts"]) == resuelto["payload_sha256"]
    prueba, corrida = MEDIDO[modo]
    assert resuelto["medido_en"] == prueba
    constancia = REPO_REAL / "results" / "gen2" / prueba / "configuracion.json"
    assert resuelto["payload_sha256_medido"] == resuelto["payload_sha256"]
    prompts = json.loads(constancia.read_text(encoding="utf-8"))["prompts"]
    medido = (prompts[corrida] if corrida else prompts)["payload_sha256"]
    assert resuelto["payload_sha256"] == medido


def test_edir_cambia_solo_los_prompts_y_el_pattern_set(tmp_path):
    repo = _repo_demo(tmp_path)
    edir = demo_modos.resolver(repo, "edir")
    campeon, modo = _configs(repo), _configs(repo, edir)
    assert modo["media"]["prompts"]["active_ids"] == ["person", "cr01_spec", "cr02_obs"]
    frases = {c["id"]: c["phrasings"]["default"] for c in modo["media"]["prompts"]["set_inline"]["classes"]}
    assert frases["cr01_spec"] == ["construction worker without safety helmet"]
    assert modo["control"]["patterns"]["file"].endswith("/e-ovrt_control-plane/configs/patterns/cr01_cr02_edir_v1.yaml")
    assert modo["control"]["patterns"]["active_ids"] == campeon["control"]["patterns"]["active_ids"]
    def sin(c):
        return {**c, "media": {k: v for k, v in c["media"].items() if k != "prompts"},
                "control": {k: v for k, v in c["control"].items() if k != "patterns"}}

    assert sin(modo) == sin(campeon)  # cámara, bus, escena, distribución: lo mismo


@pytest.mark.parametrize(("modo", "cambia"), [
    ("edir", ["prompt_set_enviado", "pattern_set"]),
    ("clase_nueva", ["prompt_set_enviado"]),
])
def test_un_modo_no_es_lo_congelado_pero_si_lo_medido(tmp_path, modo, cambia):
    repo = _repo_demo(tmp_path)
    resuelto = demo_modos.resolver(repo, modo)
    configs = _configs(repo, resuelto)
    congelado = demo_config.verificar_congelado(repo, configs, MODELO_OK)
    assert [i["id"] for i in congelado["items"] if not i["ok"]] == cambia
    verificacion = demo_modos.verificar(configs, resuelto, congelado)
    assert verificacion["ok"], verificacion["items"]
    assert [i["id"] for i in verificacion["items"]] == ["modo_prompts", "modo_constancia", "modo_patrones",
                                                        "modo_resto"]


def test_verificar_detecta_una_frase_cambiada_un_pattern_set_tocado_y_otro_modelo(tmp_path):
    repo = _repo_demo(tmp_path)
    edir = demo_modos.resolver(repo, "edir")
    configs = _configs(repo, edir)

    def fallan(cfg, modelo=MODELO_OK):
        congelado = demo_config.verificar_congelado(repo, cfg, modelo)
        return [i["id"] for i in demo_modos.verificar(cfg, edir, congelado)["items"] if not i["ok"]]

    assert fallan(configs) == []
    otra = json.loads(json.dumps(configs))
    otra["media"]["prompts"]["set_inline"]["classes"][1]["phrasings"]["default"] = ["person without hard hat"]
    assert fallan(otra) == ["modo_prompts"]
    assert fallan(configs, {"ref": "grounding-dino/gdino-base-560", "thresholds": {"box": 0.3, "text": 0.25}}) \
        == ["modo_resto"]
    patron = Path(configs["control"]["patterns"]["file"])
    patron.write_text(patron.read_text(encoding="utf-8") + "\n# tocado\n", encoding="utf-8")
    assert fallan(configs) == ["modo_patrones"]


def test_un_set_reescrito_despues_de_medido_ya_no_es_el_modo(tmp_path):
    """Si alguien cambia una frase en prompts/, el modo arma otro payload y la huella ya no es la
    medida: el chequeo previo lo pone en rojo (lo prueba test_demo_sesion)."""
    repo = _repo_demo(tmp_path)
    archivo = repo / "prompts" / "edir_v1.yaml"
    datos = yaml.safe_load(archivo.read_text(encoding="utf-8"))
    for clase in datos["prompt_set"]["classes"]:
        if clase["id"] == "cr02_obs":
            clase["phrasings"]["default"] = ["person in a dark t-shirt"]
    archivo.write_text(yaml.safe_dump(datos, sort_keys=False), encoding="utf-8")
    edir = demo_modos.resolver(repo, "edir")
    assert demo_modos.huella_prompts(demo_modos.payload(edir)) != edir["payload_sha256"]


def test_describir_trae_las_frases_y_las_cifras_de_la_generacion_2(tmp_path):
    repo = _repo_demo(tmp_path)
    lista = demo_modos.describir(repo)
    assert lista["default"] == "campeon"
    por_id = {m["id"]: m for m in lista["modos"]}
    assert [m["id"] for m in lista["modos"]] == ["campeon", "edir", "clase_nueva", "reflective"]
    assert por_id["campeon"]["por_defecto"] and not por_id["edir"]["por_defecto"]
    assert [(c["id"], c["frases"]) for c in por_id["campeon"]["clases"]] == [
        ("person", ["person"]), ("helmet", ["helmet"]), ("vest", ["vest"])]
    assert [c["id"] for c in por_id["clase_nueva"]["clases"]][-2:] == ["machinery", "vehicle"]
    assert {(c["prueba"], c["clave"]) for c in por_id["edir"]["cifras"]} >= {
        ("ALR-04", "f1"), ("PER-01", "bench_obra/CR-01/f1_edir")}
    # Sin results/gen2 en el workspace sintético: pendientes, nunca un número escrito a mano.
    assert all(c["pendiente"] and c["valor"] is None for m in lista["modos"] for c in m["cifras"])

    # Con los resultados de la generación 2, los valores salen de resultado.json.
    for prueba in ("ALR-01", "ALR-04", "EXT-01"):
        destino = repo / "results" / "gen2" / prueba
        destino.mkdir(parents=True, exist_ok=True)
        (destino / "resultado.json").write_text(
            (REPO_REAL / "results" / "gen2" / prueba / "resultado.json").read_text(encoding="utf-8"),
            encoding="utf-8")
    por_id = {m["id"]: m for m in demo_modos.describir(repo)["modos"]}
    f1 = {c["prueba"]: c["valor"] for m in por_id.values() for c in m["cifras"] if c["clave"] == "f1"}
    assert f1 == {"ALR-01": pytest.approx(0.84058), "ALR-04": pytest.approx(0.162162)}
    machinery = next(c for c in por_id["clase_nueva"]["cifras"] if c["clave"] == "ap50_machinery_obra")
    assert machinery["valor"] == pytest.approx(0.6618) and machinery["fuente"] == "results/gen2/EXT-01/resultado.json"


def test_un_modo_roto_se_lista_con_su_error_y_el_campeon_sigue(tmp_path):
    repo = _repo_demo(tmp_path)
    (repo / "prompts" / "clase_nueva_v1.yaml").unlink()
    por_id = {m["id"]: m for m in demo_modos.describir(repo)["modos"]}
    assert por_id["clase_nueva"]["error"] and por_id["clase_nueva"]["clases"] == []
    assert por_id["campeon"]["error"] is None
    with pytest.raises(demo_config.ConfigDemoError):
        demo_modos.resolver(repo, "clase_nueva")


def test_modos_yaml_no_toca_lo_congelado_ni_la_exploracion():
    """El modo vive en su propio archivo: congelado.yaml y exploracion.yaml no lo nombran."""
    base = REPO_REAL / "experiments" / "demo_defensa"
    for archivo in ("congelado.yaml", "exploracion.yaml"):
        assert "modo" not in (yaml.safe_load((base / archivo).read_text(encoding="utf-8")) or {})
    congelado = yaml.safe_load((base / "congelado.yaml").read_text(encoding="utf-8"))
    campeon = demo_modos.cargar(REPO_REAL)["modos"]["campeon"]
    assert campeon["prompts"]["set_id"] == congelado["prompt_set"]["id"]
    assert campeon["patrones"]["id"] == congelado["pattern_set"]["id"]


def test_sin_la_constancia_de_la_medicion_el_modo_queda_en_rojo(tmp_path):
    """La huella declarada en modos.yaml no alcanza: se compara en cada chequeo contra la que quedó
    en results/gen2/<prueba>/configuracion.json. Si la constancia falta o dice otra cosa, rojo."""
    repo = _repo_demo(tmp_path)
    constancia = repo / "results" / "gen2" / "ALR-04" / "configuracion.json"
    datos = json.loads(constancia.read_text(encoding="utf-8"))
    datos["prompts"]["payload_sha256"] = "0" * 64
    constancia.write_text(json.dumps(datos), encoding="utf-8")

    def fallan():
        edir = demo_modos.resolver(repo, "edir")
        configs = _configs(repo, edir)
        congelado = demo_config.verificar_congelado(repo, configs, MODELO_OK)
        return [i["id"] for i in demo_modos.verificar(configs, edir, congelado)["items"] if not i["ok"]]

    assert fallan() == ["modo_constancia"]
    constancia.unlink()
    assert fallan() == ["modo_constancia"]


def test_las_etiquetas_dicen_que_representa_cada_modo_no_si_la_evidencia_es_buena():
    lista = {m: d["evidencia"] for m, d in demo_modos.cargar(REPO_REAL)["modos"].items()}
    assert lista == {"campeon": "congelada", "edir": "descartada", "clase_nueva": "extension",
                     "reflective": "exploratoria"}


def test_reflective_es_el_campeon_con_una_sola_frase_cambiada(tmp_path):
    """✎ 2026-11-05 (doc 134 §13.19): el primer exploratorio real. Mismas clases e ids que el campeón,
    el chaleco pedido como «reflective vest», el pattern set oficial, sin cifras ni constancia; la huella
    declarada en modos.yaml es la del payload que arma la consola (la convención del driver)."""
    repo = _repo_demo(tmp_path)
    resuelto = demo_modos.resolver(repo, "reflective")
    assert resuelto["evidencia"] == "exploratoria" and resuelto["medido_en"] is None
    assert [(c["id"], c["frases"]) for c in resuelto["clases"]] == [
        ("person", ["person"]), ("helmet", ["helmet"]), ("vest", ["reflective vest"])]
    configs = _configs(repo, resuelto)
    assert demo_modos.huella_prompts(configs["media"]["prompts"]) == resuelto["payload_sha256"]
    assert configs["control"]["patterns"]["file"].endswith("/cr01_cr02_v2.yaml")
    v = demo_modos.verificar(configs, resuelto, demo_config.verificar_congelado(repo, configs, MODELO_OK))
    assert v["ok"] is True and v["exploratorio"] is True
    descrito = {m["id"]: m for m in demo_modos.describir(repo)["modos"]}["reflective"]
    assert descrito["cifras"] == [] and descrito["error"] is None


def test_un_modo_exploratorio_se_verifica_por_huella_sin_constancia(tmp_path):
    """✎ 2026-11-04 (doc 134 §13.18): sin medición todavía, pero lo que se manda es exactamente lo
    declarado; no hay ítem de constancia, y un exploratorio no puede decir que lo midió una prueba."""
    repo = _repo_demo(tmp_path)
    agregar_modo_exploratorio(repo)
    lista = {m["id"]: m for m in demo_modos.describir(repo)["modos"]}
    assert lista["distractora"]["evidencia"] == "exploratoria" and lista["distractora"]["cifras"] == []
    assert [c["id"] for c in lista["distractora"]["clases"]] == ["person", "helmet", "vest", "t_shirt"]
    resuelto = demo_modos.resolver(repo, "distractora")
    assert resuelto["medido_en"] is None and resuelto["payload_sha256_medido"] is None
    configs = _configs(repo, resuelto)
    v = demo_modos.verificar(configs, resuelto, demo_config.verificar_congelado(repo, configs, MODELO_OK))
    assert v["ok"] is True and v["exploratorio"] is True
    assert [i["id"] for i in v["items"]] == ["modo_prompts", "modo_patrones", "modo_resto"]
    # La distractora no la lee ninguna regla: el pattern set es el oficial.
    assert configs["control"]["patterns"]["file"].endswith("/cr01_cr02_v2.yaml")

    archivo = repo / "experiments" / "demo_defensa" / "modos.yaml"
    datos = yaml.safe_load(archivo.read_text(encoding="utf-8"))
    datos["modos"]["distractora"]["prompts"]["medido_en"] = "ALR-01"
    archivo.write_text(yaml.safe_dump(datos, allow_unicode=True), encoding="utf-8")
    with pytest.raises(demo_config.ConfigDemoError, match="exploratorio"):
        demo_modos.resolver(repo, "distractora")
