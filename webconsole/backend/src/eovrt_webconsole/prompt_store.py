"""Almacén de prompt sets sobre prompts/ — los YAML son la fuente de verdad.

Spec: docs/_archive/superpowers/specs/2026-07-17-prompt-strategy-design.md §2/§3.
PromptSetModel es un ESPEJO MÍNIMO de eovrt_media.config.schemas.PromptSet
(+ campos de ciclo de vida): la consola no depende de eovrt_media; el
validador final sigue siendo el media-plane en POST /api/runs.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ValidationError, model_validator

_SET_ID_RE = re.compile(r"^[a-z0-9_]+$")

STRATEGY_VALUES = frozenset({
    "canonical_positive", "syntactic_negation", "specificity",
    "observable_state", "presence_template",
})

Status = Literal["exploratory", "frozen_pending_review", "frozen"]


class PromptStoreError(Exception):
    pass


class PromptSetNotFound(PromptStoreError):
    pass


class PromptSetExists(PromptStoreError):
    pass


class FrozenSetImmutable(PromptStoreError):
    pass


class InvalidTransition(PromptStoreError):
    pass


class PromptSetInvalid(PromptStoreError):
    def __init__(self, errors: list):
        self.errors = errors
        super().__init__(f"Prompt set inválido: {errors}")


class PromptClassModel(BaseModel):
    id: str
    canonical: str | None = None
    role: str | None = None
    strategy: str | None = None
    condition_id: str | None = None
    enabled_by_default: bool = True
    phrasings: dict[str, list[str]]

    @model_validator(mode="after")
    def _check(self) -> PromptClassModel:
        if self.strategy is not None and self.strategy not in STRATEGY_VALUES:
            raise ValueError(
                f"strategy desconocida: {self.strategy!r} (taxonomía: docs/prompt-strategy.md)"
            )
        if not self.phrasings:
            raise ValueError(f"clase {self.id!r} sin phrasings")
        for backend, phrases in self.phrasings.items():
            if not phrases:
                raise ValueError(f"clase {self.id!r}: phrasings[{backend!r}] vacío")
        return self


class PromptSetModel(BaseModel):
    id: str
    description: str | None = None
    language: str | None = None
    status: Status = "exploratory"
    track: Literal["core", "demo", "comparative"] | None = None
    derives_from: str | None = None
    changes: str | None = None
    frozen_sha256: str | None = None
    classes: list[PromptClassModel]

    @model_validator(mode="after")
    def _check(self) -> PromptSetModel:
        ids = [c.id for c in self.classes]
        if len(ids) != len(set(ids)):
            raise ValueError("ids de clase duplicados")
        if self.status == "frozen" and not self.frozen_sha256:
            raise ValueError("un set frozen requiere frozen_sha256")
        return self


def classes_sha256(classes_raw: list) -> str:
    """Convención única de hash (spec §2.1): sobre el bloque classes CRUDO del YAML."""
    payload = json.dumps(classes_raw, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def _check_set_id(set_id: str) -> None:
    if not _SET_ID_RE.match(set_id):
        raise PromptSetInvalid([{"msg": f"id de set inválido: {set_id!r}"}])


def _path(prompts_dir: Path, set_id: str) -> Path:
    _check_set_id(set_id)
    return prompts_dir / f"{set_id}.yaml"


def _validate(payload: dict) -> dict:
    try:
        PromptSetModel.model_validate(payload)
    except ValidationError as exc:
        raise PromptSetInvalid(exc.errors()) from exc
    return payload


def _read(prompts_dir: Path, set_id: str) -> dict:
    path = _path(prompts_dir, set_id)
    if not path.is_file():
        raise PromptSetNotFound(set_id)
    try:
        data = yaml.safe_load(path.read_text())
    except yaml.YAMLError as exc:
        raise PromptSetInvalid([{"msg": f"YAML ilegible: {path.name}"}]) from exc
    prompt_set = (data or {}).get("prompt_set")
    if not isinstance(prompt_set, dict):
        raise PromptSetNotFound(set_id)
    return prompt_set


def _write(prompts_dir: Path, prompt_set: dict) -> None:
    text = yaml.safe_dump({"prompt_set": prompt_set}, sort_keys=False, allow_unicode=True)
    _path(prompts_dir, prompt_set["id"]).write_text(text)


def list_sets(prompts_dir: Path) -> list[dict]:
    out: list[dict] = []
    if not prompts_dir.is_dir():
        return out
    for path in sorted(prompts_dir.glob("*.yaml")):
        if not path.is_file():
            continue
        try:
            data = yaml.safe_load(path.read_text())
        except yaml.YAMLError:
            continue  # archivo ilegible: se omite del listado
        prompt_set = (data or {}).get("prompt_set") if isinstance(data, dict) else None
        if not isinstance(prompt_set, dict) or "id" not in prompt_set:
            continue
        classes = prompt_set.get("classes", [])
        out.append({
            "id": prompt_set["id"],
            "description": prompt_set.get("description"),
            "status": prompt_set.get("status", "exploratory"),
            "track": prompt_set.get("track"),
            "derives_from": prompt_set.get("derives_from"),
            "n_classes": len(classes),
            "n_phrases": sum(
                len(p) for c in classes for p in (c.get("phrasings") or {}).values()
            ),
        })
    return out


def get_set(prompts_dir: Path, set_id: str) -> dict:
    return _read(prompts_dir, set_id)


def create_set(prompts_dir: Path, payload: dict) -> dict:
    _validate(payload)
    if payload.get("status", "exploratory") != "exploratory":
        raise PromptSetInvalid([{"msg": "un set nuevo nace exploratory"}])
    if _path(prompts_dir, payload["id"]).exists():
        raise PromptSetExists(payload["id"])
    payload = {**payload, "status": "exploratory"}
    _write(prompts_dir, payload)
    return payload


def update_set(prompts_dir: Path, set_id: str, payload: dict) -> dict:
    current = _read(prompts_dir, set_id)
    if current.get("status", "exploratory") != "exploratory":
        raise FrozenSetImmutable(set_id)
    if payload.get("id") != set_id:
        raise PromptSetInvalid([{"msg": "el id no coincide con el set"}])
    if payload.get("status", "exploratory") != "exploratory":
        raise PromptSetInvalid([{"msg": "status solo cambia por acciones explícitas"}])
    _validate(payload)
    _write(prompts_dir, payload)
    return payload


def delete_set(prompts_dir: Path, set_id: str) -> None:
    current = _read(prompts_dir, set_id)
    if current.get("status", "exploratory") != "exploratory":
        raise FrozenSetImmutable(set_id)
    _path(prompts_dir, set_id).unlink()


def request_freeze(prompts_dir: Path, set_id: str) -> dict:
    current = _read(prompts_dir, set_id)
    if current.get("status", "exploratory") != "exploratory":
        raise InvalidTransition(f"{set_id}: {current.get('status')} → frozen_pending_review")
    current["status"] = "frozen_pending_review"
    _write(prompts_dir, current)
    return current


def confirm_freeze(prompts_dir: Path, set_id: str) -> dict:
    current = _read(prompts_dir, set_id)
    if current.get("status") != "frozen_pending_review":
        raise InvalidTransition(f"{set_id}: {current.get('status')} → frozen")
    current["status"] = "frozen"
    current["frozen_sha256"] = classes_sha256(current["classes"])
    _write(prompts_dir, current)
    return current


def derive_set(prompts_dir: Path, source_id: str, new_id: str, changes: str) -> dict:
    source = _read(prompts_dir, source_id)
    if _path(prompts_dir, new_id).exists():
        raise PromptSetExists(new_id)
    if not changes or not changes.strip():
        raise PromptSetInvalid([{"msg": "derivar requiere changes (qué cambia y por qué)"}])
    derived = {k: v for k, v in source.items() if k != "frozen_sha256"}
    derived.update(id=new_id, status="exploratory", derives_from=source_id, changes=changes)
    _validate(derived)
    _write(prompts_dir, derived)
    return derived
