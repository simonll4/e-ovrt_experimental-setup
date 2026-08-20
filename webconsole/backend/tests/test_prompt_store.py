from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from eovrt_webconsole import prompt_store as ps

EXPLORATORY = {
    "id": "exp_set",
    "description": "set exploratorio",
    "language": "en",
    "status": "exploratory",
    "track": "core",
    "classes": [
        {"id": "person", "strategy": "canonical_positive",
         "phrasings": {"default": ["person"]}},
    ],
}


@pytest.fixture
def prompts_dir(tmp_path: Path) -> Path:
    d = tmp_path / "prompts"
    d.mkdir()
    return d


def _write(prompts_dir: Path, payload: dict) -> Path:
    path = prompts_dir / f"{payload['id']}.yaml"
    path.write_text(yaml.safe_dump({"prompt_set": payload}, sort_keys=False, allow_unicode=True))
    return path


def test_classes_sha256_matches_convention():
    classes = EXPLORATORY["classes"]
    expected = hashlib.sha256(
        json.dumps(classes, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode()
    ).hexdigest()
    assert ps.classes_sha256(classes) == expected


def test_create_get_list_roundtrip(prompts_dir: Path):
    created = ps.create_set(prompts_dir, EXPLORATORY)
    assert created["id"] == "exp_set"
    assert ps.get_set(prompts_dir, "exp_set")["status"] == "exploratory"
    summaries = ps.list_sets(prompts_dir)
    assert [s["id"] for s in summaries] == ["exp_set"]
    assert summaries[0]["n_classes"] == 1 and summaries[0]["n_phrases"] == 1


def test_create_rejects_existing_and_non_exploratory(prompts_dir: Path):
    ps.create_set(prompts_dir, EXPLORATORY)
    with pytest.raises(ps.PromptSetExists):
        ps.create_set(prompts_dir, EXPLORATORY)
    frozen_payload = {**EXPLORATORY, "id": "otro", "status": "frozen"}
    with pytest.raises(ps.PromptSetInvalid):
        ps.create_set(prompts_dir, frozen_payload)


def test_create_rejects_bad_strategy_and_empty_phrasings(prompts_dir: Path):
    bad = {**EXPLORATORY, "classes": [
        {"id": "x", "strategy": "inventada", "phrasings": {"default": ["x"]}}]}
    with pytest.raises(ps.PromptSetInvalid):
        ps.create_set(prompts_dir, bad)
    empty = {**EXPLORATORY, "classes": [{"id": "x", "phrasings": {"gdino": []}}]}
    with pytest.raises(ps.PromptSetInvalid):
        ps.create_set(prompts_dir, empty)


def test_update_only_exploratory_and_no_status_change(prompts_dir: Path):
    ps.create_set(prompts_dir, EXPLORATORY)
    updated = ps.update_set(prompts_dir, "exp_set", {**EXPLORATORY, "description": "v2"})
    assert updated["description"] == "v2"
    with pytest.raises(ps.PromptSetInvalid):
        ps.update_set(prompts_dir, "exp_set", {**EXPLORATORY, "status": "frozen"})
    _write(prompts_dir, {**EXPLORATORY, "id": "congelado", "status": "frozen",
                         "frozen_sha256": ps.classes_sha256(EXPLORATORY["classes"])})
    with pytest.raises(ps.FrozenSetImmutable):
        ps.update_set(prompts_dir, "congelado", {**EXPLORATORY, "id": "congelado"})


def test_freeze_flow(prompts_dir: Path):
    ps.create_set(prompts_dir, EXPLORATORY)
    pending = ps.request_freeze(prompts_dir, "exp_set")
    assert pending["status"] == "frozen_pending_review"
    with pytest.raises(ps.InvalidTransition):
        ps.request_freeze(prompts_dir, "exp_set")
    frozen = ps.confirm_freeze(prompts_dir, "exp_set")
    assert frozen["status"] == "frozen"
    assert frozen["frozen_sha256"] == ps.classes_sha256(frozen["classes"])
    with pytest.raises(ps.InvalidTransition):
        ps.confirm_freeze(prompts_dir, "exp_set")
    with pytest.raises(ps.FrozenSetImmutable):
        ps.delete_set(prompts_dir, "exp_set")


def test_confirm_freeze_requires_pending(prompts_dir: Path):
    ps.create_set(prompts_dir, EXPLORATORY)
    with pytest.raises(ps.InvalidTransition):
        ps.confirm_freeze(prompts_dir, "exp_set")


def test_derive_from_frozen(prompts_dir: Path):
    ps.create_set(prompts_dir, EXPLORATORY)
    ps.request_freeze(prompts_dir, "exp_set")
    ps.confirm_freeze(prompts_dir, "exp_set")
    derived = ps.derive_set(prompts_dir, "exp_set", "exp_set_v2", changes="prueba de derivación")
    assert derived["status"] == "exploratory"
    assert derived["derives_from"] == "exp_set"
    assert derived["changes"] == "prueba de derivación"
    assert "frozen_sha256" not in derived
    assert (prompts_dir / "exp_set_v2.yaml").is_file()


def test_delete_exploratory(prompts_dir: Path):
    ps.create_set(prompts_dir, EXPLORATORY)
    ps.delete_set(prompts_dir, "exp_set")
    with pytest.raises(ps.PromptSetNotFound):
        ps.get_set(prompts_dir, "exp_set")


def test_create_rejects_path_traversal_id(prompts_dir: Path):
    bad = {**EXPLORATORY, "id": "../evil"}
    with pytest.raises(ps.PromptSetInvalid):
        ps.create_set(prompts_dir, bad)
    assert not (prompts_dir.parent / "evil.yaml").exists()


def test_get_rejects_path_traversal_id(prompts_dir: Path):
    with pytest.raises(ps.PromptSetInvalid):
        ps.get_set(prompts_dir, "../../x")


def test_valid_id_with_underscores_and_digits_still_works(prompts_dir: Path):
    payload = {**EXPLORATORY, "id": "exp_set_2"}
    created = ps.create_set(prompts_dir, payload)
    assert created["id"] == "exp_set_2"
    assert ps.get_set(prompts_dir, "exp_set_2")["id"] == "exp_set_2"


def test_list_sets_skips_corrupt_yaml_but_returns_healthy_ones(prompts_dir: Path):
    ps.create_set(prompts_dir, EXPLORATORY)
    (prompts_dir / "corrupto.yaml").write_text("prompt_set: [invalid: : :\n")
    summaries = ps.list_sets(prompts_dir)
    assert [s["id"] for s in summaries] == ["exp_set"]


def test_get_set_on_corrupt_yaml_raises_prompt_set_invalid(prompts_dir: Path):
    (prompts_dir / "corrupto.yaml").write_text("prompt_set: [invalid: : :\n")
    with pytest.raises(ps.PromptSetInvalid):
        ps.get_set(prompts_dir, "corrupto")


def test_track_retention_es_valido_y_se_congela_fuera_de_la_consola():
    """`retention` es un track válido: arnés de retención de vocabulario abierto (T2).

    Sus sets los genera y congela `finetuning/scripts/build_coco_retention_harness.py`, y
    su freeze se ancla por sha256 del ARCHIVO en `finetuning/manifests/`, no por el hash
    del bloque `classes` que calcula la consola al congelar. Por eso un `retention` frozen
    es válido sin `frozen_sha256`; el resto de los tracks lo sigue exigiendo.
    """
    frozen_retention = {**EXPLORATORY, "id": "coco_like", "track": "retention",
                        "status": "frozen"}
    assert ps.PromptSetModel.model_validate(frozen_retention).track == "retention"

    with pytest.raises(ValidationError):  # track fuera del vocabulario
        ps.PromptSetModel.model_validate({**EXPLORATORY, "track": "inventado"})
    with pytest.raises(ValidationError):  # frozen de consola: el hash sigue siendo obligatorio
        ps.PromptSetModel.model_validate({**EXPLORATORY, "status": "frozen"})


def test_repo_frozen_sets_integrity():
    """Contrato sobre los sets REALES del repo: todo frozen tiene hash válido.

    Excepción declarada: los sets del track `retention` no pasan por el congelamiento de
    la consola (los emite el arnés de fine-tuning y los ancla por sha256 de archivo en
    `finetuning/manifests/`), así que no llevan `frozen_sha256`.
    """
    repo_prompts = Path(__file__).resolve().parents[3] / "prompts"
    for path in sorted(repo_prompts.glob("*.yaml")):
        data = yaml.safe_load(path.read_text())["prompt_set"]
        ps.PromptSetModel.model_validate(data)  # el espejo acepta todos los sets reales
        if data.get("status") == "frozen" and data.get("track") != "retention":
            assert data["frozen_sha256"] == ps.classes_sha256(data["classes"]), path.name
