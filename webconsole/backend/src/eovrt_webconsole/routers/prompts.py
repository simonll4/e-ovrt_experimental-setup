"""Gestión de prompt sets (spec 2026-07-17 §3): CRUD + ciclo de vida sobre prompts/."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel

from eovrt_webconsole import prompt_store as ps

router = APIRouter(prefix="/api/prompt-sets")


def _prompts_dir(request: Request):
    return request.app.state.settings.prompts_dir


def _raise(exc: ps.PromptStoreError) -> None:
    if isinstance(exc, ps.PromptSetNotFound):
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if isinstance(exc, (ps.PromptSetExists, ps.FrozenSetImmutable, ps.InvalidTransition)):
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if isinstance(exc, ps.PromptSetInvalid):
        # pydantic ValidationError.errors() incluye ctx.error con la excepción
        # cruda (no serializable a JSON); jsonable_encoder la reduce a str.
        detail = jsonable_encoder(exc.errors, custom_encoder={Exception: str})
        raise HTTPException(status_code=422, detail=detail) from exc
    raise exc


@router.get("")
def list_prompt_sets(request: Request) -> list[dict]:
    return ps.list_sets(_prompts_dir(request))


@router.get("/{set_id}")
def get_prompt_set(request: Request, set_id: str) -> dict:
    try:
        # Con `diff`: `derives_from` decía de dónde viene el conjunto pero no qué
        # cambió, y `changes` es una nota escrita a mano que puede decir
        # cualquier cosa. El diff calculado es lo auditable.
        return ps.get_set_with_diff(_prompts_dir(request), set_id)
    except ps.PromptStoreError as exc:
        _raise(exc)


@router.post("", status_code=201)
def create_prompt_set(request: Request, payload: dict) -> dict:
    try:
        return ps.create_set(_prompts_dir(request), payload)
    except ps.PromptStoreError as exc:
        _raise(exc)


@router.put("/{set_id}")
def update_prompt_set(request: Request, set_id: str, payload: dict) -> dict:
    try:
        return ps.update_set(_prompts_dir(request), set_id, payload)
    except ps.PromptStoreError as exc:
        _raise(exc)


@router.delete("/{set_id}", status_code=204)
def delete_prompt_set(request: Request, set_id: str) -> Response:
    try:
        ps.delete_set(_prompts_dir(request), set_id)
    except ps.PromptStoreError as exc:
        _raise(exc)
    return Response(status_code=204)


@router.post("/{set_id}/freeze-request")
def freeze_request(request: Request, set_id: str) -> dict:
    try:
        return ps.request_freeze(_prompts_dir(request), set_id)
    except ps.PromptStoreError as exc:
        _raise(exc)


@router.post("/{set_id}/freeze")
def freeze(request: Request, set_id: str) -> dict:
    try:
        return ps.confirm_freeze(_prompts_dir(request), set_id)
    except ps.PromptStoreError as exc:
        _raise(exc)


class DeriveBody(BaseModel):
    new_id: str
    changes: str


@router.post("/{set_id}/derive", status_code=201)
def derive(request: Request, set_id: str, body: DeriveBody) -> dict:
    try:
        return ps.derive_set(_prompts_dir(request), set_id, body.new_id, body.changes)
    except ps.PromptStoreError as exc:
        _raise(exc)
