"""Transformación pura de derivación (spec 2026-07-25 §Mapa de overrides,
§Reescritura de identidad y rutas)."""
from __future__ import annotations

from pathlib import Path

import pytest

from eovrt_webconsole.experiment_deriver import DeriveError, derive_payloads

TARGET = Path("/repo/experiments/nuevo")

SRC_MANIFEST = {
    "schema_version": "experiment.manifest.v1",
    "slug": "ebe_oakd_live",
    "experiment_id": "exp_vieja_corrida",
    "runs": {
        "media": {
            "service": "media-plane",
            "config": "/repo/experiments/ebe_oakd_live/media.yaml",
            "mode": "run",
        },
        "control": {
            "service": "control-plane",
            "config": "/repo/experiments/ebe_oakd_live/control.yaml",
            "mode": "live",
        },
    },
    "sequencing": "control_first",
    "report": {},
    "frozen": {},
}

SRC_MEDIA = {
    "ingest": {"plugin": "oak_d", "config": {"url": "169.254.31.137", "fps": 30, "warmup_frames": 20}},
    "prompts": {"set_inline": {"id": "viejo", "classes": []}, "active_ids": ["person"]},
    "run": {"name": "ebe_oakd_live", "save_previews": True, "stride": 2},
}

SRC_CONTROL = {
    "run": {"id": None, "scenario": "EBE", "name": "control_ebe_oakd_live"},
    "patterns": {"file": "/patterns/cr01_cr02_v2.yaml", "active_ids": ["CR-01", "CR-02"]},
    "input": {"bus": {"endpoint": "tcp://127.0.0.1:5557"}},
}


def _derive(overrides, **kw):
    return derive_payloads(
        source_manifest=SRC_MANIFEST,
        source_media=SRC_MEDIA,
        source_control=SRC_CONTROL,
        new_slug="nuevo",
        changes="prueba",
        overrides=overrides,
        target_dir=TARGET,
        camera=kw.get("camera"),
        prompt_set=kw.get("prompt_set"),
    )


def test_reescribe_identidad_y_rutas():
    """El fallo silencioso que este test previene: si runs.*.config no se
    reapunta, el manifiesto derivado carga los payloads del ORIGINAL y corre
    con la config vieja sin avisar."""
    manifest, media, control = _derive({})
    assert manifest["slug"] == "nuevo"
    assert manifest["runs"]["media"]["config"] == "/repo/experiments/nuevo/media.yaml"
    assert manifest["runs"]["control"]["config"] == "/repo/experiments/nuevo/control.yaml"
    assert media["run"]["name"] == "nuevo"
    assert control["run"]["name"] == "control_nuevo"


def test_registra_procedencia_y_limpia_experiment_id():
    manifest, _, _ = _derive({})
    assert manifest["derives_from"] == "ebe_oakd_live"
    assert manifest["changes"] == "prueba"
    # el derivado nunca hereda la corrida del fuente
    assert manifest["experiment_id"] is None


def test_no_muta_los_payloads_fuente():
    _derive({"warmup_frames": 99})
    assert SRC_MEDIA["ingest"]["config"]["warmup_frames"] == 20


def test_override_captura():
    _, media, _ = _derive({"warmup_frames": 30, "fps": 15})
    assert media["ingest"]["config"]["warmup_frames"] == 30
    assert media["ingest"]["config"]["fps"] == 15


def test_override_limites():
    _, media, _ = _derive({"max_units": 600})
    assert media["run"]["max_units"] == 600
    assert media["run"]["stride"] == 2  # ausente => conserva


def test_null_borra_el_campo():
    """Sin esta semántica no habría forma de volver un campo a su default."""
    _, media, _ = _derive({"stride": None})
    assert "stride" not in media["run"]


def test_override_patrones():
    _, _, control = _derive(
        {"pattern_set_file": "/patterns/otro.yaml", "pattern_active_ids": ["CR-01"]}
    )
    assert control["patterns"]["file"] == "/patterns/otro.yaml"
    assert control["patterns"]["active_ids"] == ["CR-01"]


def test_override_camara_reconstruye_ingest():
    camera = {"id": "rtsp_dvr_1", "plugin": "rtsp", "config": {"url": "rtsp://1.2.3.4:554/s"}}
    _, media, _ = _derive({"camera_id": "rtsp_dvr_1"}, camera=camera)
    assert media["ingest"]["plugin"] == "rtsp"
    assert media["ingest"]["config"]["url"] == "rtsp://1.2.3.4:554/s"
    # warmup_frames sobrevive al cambio de cámara (no está en el preset)
    assert media["ingest"]["config"]["warmup_frames"] == 20
    # fps era de la OAK-D, no del preset nuevo: no se arrastra
    assert "fps" not in media["ingest"]["config"]


def test_override_prompts_expande_inline():
    ps = {"id": "cr01_cr02_v2_short", "classes": [{"id": "person", "phrasings": {"default": ["person"]}}]}
    _, media, _ = _derive({"prompt_set_id": "cr01_cr02_v2_short"}, prompt_set=ps)
    assert media["prompts"]["set_inline"] == ps
    assert media["prompts"]["set_inline"]["id"] == "cr01_cr02_v2_short"


def test_camara_con_credenciales_embebidas_falla():
    """experiments/ ESTÁ versionado y cameras/ está gitignoreado justamente porque
    los presets llevan credenciales en claro. Volcar el preset tal cual al
    media.yaml derivado las publicaría en git. Misma invariante que
    translation.py:146 ("nunca escribir credenciales de cámara a disco"), pero acá
    se falla en vez de redactar: una url redactada no conecta, así que el
    manifiesto derivado sería inservible y el fallo aparecería recién en la toma."""
    camera = {
        "id": "rtsp_dvr_1",
        "plugin": "rtsp",
        "config": {"url": "rtsp://usuario:clave@169.254.31.140:554/s"},
    }
    with pytest.raises(DeriveError, match="credenciales"):
        _derive({"camera_id": "rtsp_dvr_1"}, camera=camera)


def test_camara_sin_credenciales_pasa():
    """La OAK-D (url sin userinfo) tiene que seguir derivándose normal."""
    camera = {"id": "oak_d_lab", "plugin": "oak_d", "config": {"url": "169.254.31.137"}}
    _, media, _ = _derive({"camera_id": "oak_d_lab"}, camera=camera)
    assert media["ingest"]["config"]["url"] == "169.254.31.137"


def test_prompt_set_nuevo_con_active_ids_huerfano_falla():
    """SRC_MEDIA hereda active_ids=["person"]. Un set que no declara `person`
    deja el manifiesto derivado inválido para el media-plane (get_active_classes
    tira ValueError al lanzar) y `active_ids` no es clave de override, así que el
    usuario no tendría cómo arreglarlo desde la UI."""
    ps = {"id": "solo_casco", "classes": [{"id": "helmet", "phrasings": {"default": ["helmet"]}}]}
    with pytest.raises(DeriveError, match="person"):
        _derive({"prompt_set_id": "solo_casco"}, prompt_set=ps)


def test_prompt_set_nuevo_que_cubre_los_active_ids_pasa():
    ps = {
        "id": "cubre",
        "classes": [
            {"id": "person", "phrasings": {"default": ["person"]}},
            {"id": "helmet", "phrasings": {"default": ["helmet"]}},
        ],
    }
    _, media, _ = _derive({"prompt_set_id": "cubre"}, prompt_set=ps)
    assert media["prompts"]["active_ids"] == ["person"]


def test_campo_desconocido_en_ingest_config_falla():
    with pytest.raises(DeriveError, match="ingest.config"):
        _derive({"camera_id": "x"}, camera={"id": "x", "plugin": "oak_d",
                                            "config": {"url": "1.2.3.4", "inventado": 1}})


def test_warmup_frames_en_fuente_no_viva_falla():
    """schemas.py:239 del media-plane lo rechaza; queremos fallar acá, no con un
    422 en medio de una toma."""
    camera = {"id": "arch", "plugin": "video_file", "config": {"path": "/v.mp4"}}
    with pytest.raises(DeriveError, match="warmup_frames"):
        _derive({"camera_id": "arch"}, camera=camera)


def test_override_desconocido_falla():
    with pytest.raises(DeriveError, match="override"):
        _derive({"parametro_que_no_existe": 1})
