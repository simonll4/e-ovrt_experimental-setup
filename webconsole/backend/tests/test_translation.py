from pathlib import Path

import pytest
import yaml

from eovrt_webconsole.translation import (
    Composition,
    UnknownPromptSetError,
    composition_to_manifest,
    composition_to_run_request,
    manifest_to_composition,
)

# Raíz REAL del repo (tests corren desde webconsole/backend): ida-y-vuelta sobre
# los manifiestos reales de experiments/ (incluida la matriz bench_v2/).
REPO_ROOT = Path(__file__).resolve().parents[3]


def _is_run_manifest(path: Path) -> bool:
    """Un manifiesto de corrida del webconsole tiene una sección ``source``.

    experiments/ también aloja otros yaml que NO son manifiestos de corrida y
    no round-trippean por ``manifest_to_composition``: bundles de orquestación
    (``experiment.manifest.v1``), payloads RunRequest (``media.yaml``) y configs
    del control-plane. Se los excluye por forma, no por nombre de carpeta.
    """
    try:
        doc = yaml.safe_load(path.read_text())
    except yaml.YAMLError:
        return False
    return isinstance(doc, dict) and "source" in doc


REAL_MANIFESTS = sorted(
    p for p in (REPO_ROOT / "experiments").rglob("*.yaml") if _is_run_manifest(p)
)


def _composition(**overrides) -> Composition:
    body = {
        "ingest": {"plugin": "image_folder", "config": {"dataset": "demo_v2"}},
        "prompts": {"set_id": "demo_set", "active_ids": ["person"]},
        "run": {"stride": 2, "max_units": 10, "save_annotated_video": True},
    }
    body.update(overrides)
    return Composition(**body)


def test_composition_to_run_request(repo):
    raw = composition_to_run_request(_composition(), repo / "prompts")
    assert "model" not in raw  # el modelo NUNCA viaja (422 del servicio)
    assert raw["ingest"] == {"plugin": "image_folder", "config": {"dataset": "demo_v2"}}
    assert raw["prompts"]["set_inline"]["id"] == "demo_set"
    assert raw["prompts"]["active_ids"] == ["person"]
    assert raw["run"]["stride"] == 2
    assert raw["run"]["max_units"] == 10
    assert raw["run"]["save_annotated_video"] is True
    assert raw["run"]["save_previews"] is True


def test_composition_to_run_request_set_inexistente(repo):
    comp = _composition(prompts={"set_id": "nope", "active_ids": None})
    with pytest.raises(UnknownPromptSetError):
        composition_to_run_request(comp, repo / "prompts")


def test_manifest_to_composition_dataset_ref():
    manifest = {
        "run": {"scenario": "DBE", "name": "x"},
        "source": {"ref": "bench_v2_test"},
        "rate_control": {"stride": 3},
        "model": {"ref": "yoloe/yoloe-26l", "device": "cuda"},
        "prompts": {"ref": "frozen_set", "active_ids": ["person"]},
        "outputs": {"save_annotated_video": True},
    }
    comp = manifest_to_composition(manifest)
    assert comp.ingest.config == {"dataset": "bench_v2_test"}
    assert comp.prompts.set_id == "frozen_set"
    assert comp.run.stride == 3
    assert comp.run.name == "x"
    assert comp.run.save_annotated_video is True
    assert comp.manifest_model_ref == "yoloe/yoloe-26l"


def test_manifest_sin_source_falla():
    with pytest.raises(ValueError, match="source"):
        manifest_to_composition({"prompts": {"ref": "x"}})


def test_manifest_sin_prompts_ref_falla():
    with pytest.raises(ValueError, match="prompts"):
        manifest_to_composition({"source": {"ref": "demo_v2"}})


@pytest.mark.parametrize("path", REAL_MANIFESTS, ids=lambda p: p.stem)
def test_ida_y_vuelta_sobre_manifiestos_reales(path):
    original = yaml.safe_load(path.read_text())
    comp = manifest_to_composition(original)
    regenerated = composition_to_manifest(comp, target_model_ref="ignored/target")
    # Subconjunto que la traducción posee (device/description/scenario no se preservan):
    assert regenerated["source"] == {
        k: v for k, v in original["source"].items() if k in ("ref", "type", "path")
    } or regenerated["source"] == original["source"]
    assert regenerated["prompts"]["ref"] == original["prompts"]["ref"]
    assert regenerated["prompts"].get("active_ids") == original["prompts"].get("active_ids")
    assert regenerated.get("rate_control") == original.get("rate_control")
    assert regenerated["model"]["ref"] == original["model"]["ref"]
    assert regenerated.get("outputs", {}).get("save_annotated_video", False) == bool(
        original.get("outputs", {}).get("save_annotated_video", False)
    )
    assert regenerated["run"].get("name") == original.get("run", {}).get("name")


@pytest.mark.parametrize("original_type", ["video", "video_frame", "video_file"])
def test_ida_y_vuelta_preserva_source_type_de_video(original_type):
    # video/video_frame/video_file mapean todos al plugin video_file; el
    # round-trip debe devolver el MISMO string, no colapsarlo a "video_file"
    # (deuda: la consola reescribía manifiestos curados hechos a mano).
    manifest = {
        "run": {"scenario": "DBE"},
        "source": {"type": original_type, "path": "/data/x.mp4"},
        "prompts": {"ref": "frozen_set"},
        "model": {"ref": "yoloe/yoloe-26l"},
    }
    comp = manifest_to_composition(manifest)
    regenerated = composition_to_manifest(comp, target_model_ref="ignored/target")
    assert regenerated["source"]["type"] == original_type
    assert regenerated["source"]["path"] == "/data/x.mp4"


def test_composition_de_formulario_sin_source_type_usa_el_del_plugin(repo):
    # Una composición armada por el formulario (sin source_type) debe seguir
    # derivando el type desde el plugin al guardar el manifiesto.
    comp = _composition(ingest={"plugin": "video_file", "config": {"path": "/v.mp4"}})
    manifest = composition_to_manifest(comp, target_model_ref="t/t")
    assert manifest["source"]["type"] == "video_file"
    assert manifest["source"]["path"] == "/v.mp4"


def test_composition_to_manifest_usa_target_si_no_hay_ref(repo):
    manifest = composition_to_manifest(_composition(), target_model_ref="grounding-dino/gdino-tiny")
    assert manifest["model"] == {"ref": "grounding-dino/gdino-tiny"}
    assert manifest["source"] == {"ref": "demo_v2"}
    assert manifest["rate_control"] == {"stride": 2}
    assert manifest["run"]["max_units"] == 10
    assert manifest["outputs"] == {"save_annotated_video": True}


def test_run_request_rtsp_lleva_url_real(repo):
    comp = _composition(ingest={"plugin": "rtsp", "config": {"url": "rtsp://u:p@10.0.0.5:554/s"}})
    raw = composition_to_run_request(comp, repo / "prompts")
    assert raw["ingest"] == {"plugin": "rtsp", "config": {"url": "rtsp://u:p@10.0.0.5:554/s"}}


def test_manifest_rtsp_redacta_credenciales(repo):
    comp = _composition(ingest={"plugin": "rtsp", "config": {"url": "rtsp://u:p@10.0.0.5:554/s"}})
    manifest = composition_to_manifest(comp, target_model_ref="t/t")
    assert manifest["source"]["type"] == "rtsp"
    assert manifest["source"]["url"] == "rtsp://***:***@10.0.0.5:554/s"


def test_manifest_rtsp_sin_credenciales_no_cambia(repo):
    comp = _composition(ingest={"plugin": "rtsp", "config": {"url": "rtsp://10.0.0.5:554/s"}})
    manifest = composition_to_manifest(comp, target_model_ref="t/t")
    assert manifest["source"]["url"] == "rtsp://10.0.0.5:554/s"


def test_round_trip_manifiesto_rtsp_redactado():
    manifest = {
        "run": {"scenario": "DBE"},
        "source": {"type": "rtsp", "url": "rtsp://***:***@10.0.0.5:554/s"},
        "prompts": {"ref": "frozen_set"},
        "model": {"ref": "yoloe/yoloe-26l"},
    }
    comp = manifest_to_composition(manifest)
    assert comp.ingest.plugin == "rtsp"
    assert comp.ingest.config == {"url": "rtsp://***:***@10.0.0.5:554/s"}
    regenerated = composition_to_manifest(comp, target_model_ref="ignored/target")
    assert regenerated["source"]["type"] == "rtsp"
    assert regenerated["source"]["url"] == "rtsp://***:***@10.0.0.5:554/s"


@pytest.mark.parametrize("url,expected", [
    ("RTSP://u:p@10.0.0.5:554/s", "RTSP://***:***@10.0.0.5:554/s"),   # esquema en mayúsculas
    ("rtsps://u:p@10.0.0.5:554/s", "rtsps://***:***@10.0.0.5:554/s"),  # RTSP sobre TLS
    ("rtsp://u:p@ss@10.0.0.5:554/s", "rtsp://***:***@10.0.0.5:554/s"), # '@' sin escapar en el password
])
def test_manifest_rtsp_redacta_esquemas_y_arroba(repo, url, expected):
    comp = _composition(ingest={"plugin": "rtsp", "config": {"url": url}})
    manifest = composition_to_manifest(comp, target_model_ref="t/t")
    assert manifest["source"]["url"] == expected
