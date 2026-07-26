"""Derivación de manifiestos paraguas: transformación pura de los tres payloads.

Espejo de `prompt_store.derive_set` para experimentos (spec
docs/superpowers/specs/2026-07-25-derivar-experimentos-design.md).

Sin I/O y sin FastAPI a propósito: las reglas sutiles viven acá (semántica del
`null`, reescritura de rutas absolutas) y se testean en aislamiento. El llamador
resuelve los catálogos y persiste el resultado.
"""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from eovrt_webconsole.redact import has_rtsp_credentials

# Copiado de e-ovrt_media-plane/src/eovrt_media/config/schemas.py:145. El
# warm-up de lente solo tiene sentido en fuentes vivas.
LIVE_PLUGINS: tuple[str, ...] = ("rtsp", "oak_d")

# Campos válidos de `ingest.config`, copiados de SourceSection.model_fields
# (e-ovrt_media-plane/src/eovrt_media/config/schemas.py) + "dataset", que
# run_request.py:93 acepta y traduce a source.ref.
#
# Se hardcodean a propósito: `eovrt_media` NO es importable desde el venv del
# BFF (repos y venvs separados), así que importarlo para leer el schema en vivo
# degradaría siempre a "no validar" y el guard sería letra muerta. Si el
# media-plane suma un campo de fuente, hay que actualizar esta tupla.
SOURCE_CONFIG_FIELDS: frozenset[str] = frozenset({
    "dataset", "dataset_id", "description", "extensions", "fps", "isp_scale",
    "kind", "orientation", "path", "prefilter", "reconnect_delay_ms",
    "reconnect_retries", "ref", "resolution", "source_id", "split", "type",
    "url", "view", "vocabulary", "warmup_frames", "xlink_chunk_size",
})

# Claves aceptadas en `overrides`. Lista cerrada: un typo es un error explícito,
# no un campo que se ignora en silencio.
_MEDIA_INGEST_KEYS = frozenset({"warmup_frames", "fps"})
_MEDIA_RUN_KEYS = frozenset({"stride", "max_units"})
_OTHER_KEYS = frozenset({"camera_id", "prompt_set_id", "pattern_set_file", "pattern_active_ids"})
_ALLOWED = _MEDIA_INGEST_KEYS | _MEDIA_RUN_KEYS | _OTHER_KEYS

_SENTINEL = object()


class DeriveError(ValueError):
    """Override inválido o payload derivado inconsistente."""


def _apply(target: dict, key: str, value: Any) -> None:
    """Semántica de overrides: `None` explícito borra, cualquier otro valor asigna."""
    if value is None:
        target.pop(key, None)
    else:
        target[key] = value


def derive_payloads(
    *,
    source_manifest: dict,
    source_media: dict,
    source_control: dict,
    new_slug: str,
    changes: str | None,
    overrides: dict,
    target_dir: Path,
    camera: dict | None = None,
    prompt_set: dict | None = None,
) -> tuple[dict, dict, dict]:
    """Devuelve (manifest, media, control) derivados. No muta los originales."""
    unknown = set(overrides) - _ALLOWED
    if unknown:
        raise DeriveError(f"override desconocido: {sorted(unknown)}")

    manifest = copy.deepcopy(source_manifest)
    media = copy.deepcopy(source_media)
    control = copy.deepcopy(source_control)

    ingest = media.setdefault("ingest", {})
    config = dict(ingest.get("config") or {})

    # Cámara: reconstruye plugin+config desde el preset. `warmup_frames` no vive
    # en el preset, así que se preserva del fuente; el resto de la config vieja
    # (p. ej. `fps` de la OAK-D) NO se arrastra a una cámara distinta.
    if "camera_id" in overrides:
        if camera is None:
            raise DeriveError(f"cámara no resuelta: {overrides['camera_id']!r}")
        camera_url = (camera.get("config") or {}).get("url")
        if isinstance(camera_url, str) and has_rtsp_credentials(camera_url):
            # `cameras/` está gitignoreado justamente porque los presets llevan
            # credenciales en claro; `experiments/` NO lo está y tiene remote.
            # Volcar el preset tal cual publicaría usuario y clave en git. Misma
            # invariante que translation.py:146, pero acá se rechaza en vez de
            # redactar: una url redactada no conecta, así que el manifiesto
            # derivado sería inservible y el fallo aparecería en medio de la toma.
            raise DeriveError(
                f"la cámara {overrides['camera_id']!r} tiene credenciales embebidas en la url y "
                "experiments/ es un directorio versionado: derivar hacia ella las publicaría en "
                "git. Es a propósito, no un bug. Usá un preset sin credenciales en la url (p. ej. "
                "la OAK-D) o sacá el userinfo del preset y pasá las credenciales por fuera del "
                "manifiesto."
            )
        previous_warmup = config.get("warmup_frames", _SENTINEL)
        ingest["plugin"] = camera["plugin"]
        config = dict(camera.get("config") or {})
        if previous_warmup is not _SENTINEL:
            config["warmup_frames"] = previous_warmup

    for key in _MEDIA_INGEST_KEYS:
        if key in overrides:
            _apply(config, key, overrides[key])

    plugin = ingest.get("plugin")
    if config.get("warmup_frames", 0) and plugin not in LIVE_PLUGINS:
        raise DeriveError(
            f"warmup_frames solo aplica a fuentes vivas ({', '.join(LIVE_PLUGINS)}); "
            f"plugin={plugin!r}"
        )

    unknown_config = set(config) - SOURCE_CONFIG_FIELDS
    if unknown_config:
        raise DeriveError(f"campo desconocido en ingest.config: {sorted(unknown_config)}")

    ingest["config"] = config

    if "prompt_set_id" in overrides:
        if prompt_set is None:
            raise DeriveError(f"prompt set no resuelto: {overrides['prompt_set_id']!r}")
        prompts = media.setdefault("prompts", {})
        prompts["set_inline"] = copy.deepcopy(prompt_set)
        # `active_ids` se hereda del fuente y NO es clave de override: si el set
        # nuevo no declara alguna de esas clases, el manifiesto derivado queda
        # roto para el media-plane (get_active_classes tira "Prompt ID no
        # encontrado en el set" al lanzar) y el usuario no tiene forma de
        # arreglarlo desde la UI. Se falla al derivar, no en medio de una toma.
        active_ids = prompts.get("active_ids")
        if active_ids:
            disponibles = {
                c.get("id") for c in (prompt_set.get("classes") or []) if isinstance(c, dict)
            }
            sobran = [cid for cid in active_ids if cid not in disponibles]
            if sobran:
                raise DeriveError(
                    f"el prompt set {prompt_set.get('id')!r} no declara "
                    f"{sobran} — heredados de prompts.active_ids del manifiesto fuente; "
                    f"clases disponibles: {sorted(d for d in disponibles if d)}"
                )

    run = media.setdefault("run", {})
    for key in _MEDIA_RUN_KEYS:
        if key in overrides:
            _apply(run, key, overrides[key])

    patterns = control.setdefault("patterns", {})
    if "pattern_set_file" in overrides:
        _apply(patterns, "file", overrides["pattern_set_file"])
    if "pattern_active_ids" in overrides:
        _apply(patterns, "active_ids", overrides["pattern_active_ids"])

    # Identidad y rutas. Sin esto el derivado apunta a los payloads del fuente.
    manifest["slug"] = new_slug
    manifest["experiment_id"] = None
    manifest["derives_from"] = source_manifest.get("slug")
    manifest["changes"] = changes
    manifest["runs"]["media"]["config"] = str(target_dir / "media.yaml")
    manifest["runs"]["control"]["config"] = str(target_dir / "control.yaml")
    run["name"] = new_slug
    control.setdefault("run", {})["name"] = f"control_{new_slug}"

    return manifest, media, control
