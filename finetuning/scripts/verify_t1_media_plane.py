#!/usr/bin/env python3
"""Exercise a fixed-vocabulary T1 checkpoint through media-plane startup and inference."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib
import json
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

FIXED_VOCABULARY = (
    ("person", "person"),
    ("helmet", "helmet"),
    ("vest", "vest"),
    ("bare_head", "bare head"),
)
MEDIA_SOURCES = (
    "src/eovrt_media/config/schemas.py",
    "src/eovrt_media/models/__init__.py",
    "src/eovrt_media/models/yoloe_adapter.py",
    "src/eovrt_media/service/app.py",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_state(repo: Path) -> dict[str, object]:
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo,
        check=True,
        text=True,
        capture_output=True,
    ).stdout
    return {"revision": revision, "dirty": bool(status.strip())}


def _write_catalog(
    catalog_root: Path, checkpoint: Path, device: str, *, warmup: bool
) -> None:
    model_path = catalog_root / "models" / "yoloe" / "t1-smoke.yaml"
    model_path.parent.mkdir(parents=True)
    model_path.write_text(
        yaml.safe_dump(
            {
                "family": "yoloe",
                "variant": "yoloe-26s",
                "lineage": "finetuned",
                "description": "Ephemeral T1 serving-gate checkpoint",
                "adapter": "yoloe",
                "weights": str(checkpoint),
                "device": device,
                "runtime": {"half_precision": False, "warmup": warmup},
                "confidence_threshold": 0.25,
                "iou_threshold": 0.5,
                "image_size": 640,
                "fixed_vocabulary": [
                    {"id": prompt_id, "text": text}
                    for prompt_id, text in FIXED_VOCABULARY
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


async def _exercise_service(
    *,
    media_plane_root: Path,
    checkpoint: Path,
    sample_image: Path,
    device: str,
    warmup: bool,
) -> dict[str, object]:
    src = media_plane_root / "src"
    sys.path.insert(0, str(src))
    try:
        prompt_module = importlib.import_module("eovrt_media.config.prompt_plan")
        app_module = importlib.import_module("eovrt_media.service.app")
        settings_module = importlib.import_module("eovrt_media.service.settings")
        PromptPhrase = prompt_module.PromptPhrase
        PromptPlan = prompt_module.PromptPlan

        with tempfile.TemporaryDirectory(prefix="eovrt-t1-serving-") as raw_temp:
            temporary = Path(raw_temp)
            catalog = temporary / "catalog"
            _write_catalog(catalog, checkpoint, device, warmup=warmup)
            settings = settings_module.ServiceSettings.from_env(
                {
                    "EOVRT_MODEL_REF": "yoloe/t1-smoke",
                    "EOVRT_MODEL_DEVICE": device,
                    "EOVRT_MEDIA_CATALOG_ROOT": str(catalog),
                    "EOVRT_RUNS_DIR": str(temporary / "runs"),
                    "EOVRT_SHUTDOWN_GRACE_SECONDS": "5",
                }
            )
            app = app_module.create_app(settings)
            started = time.monotonic()
            print("T1_MEDIA_PLANE_STAGE lifespan_enter", file=sys.stderr, flush=True)
            service_result = None
            async with app.router.lifespan_context(app):
                load_seconds = time.monotonic() - started
                print("T1_MEDIA_PLANE_STAGE lifespan_ready", file=sys.stderr, flush=True)
                if not app.state.ready:
                    raise RuntimeError(f"media-plane startup failed: {app.state.load_error}")
                adapter = app.state.adapter
                model_section = app.state.model_section
                configured = tuple(
                    (entry.id, entry.text) for entry in model_section.fixed_vocabulary or []
                )
                if configured != FIXED_VOCABULARY:
                    raise RuntimeError(
                        f"resolved fixed vocabulary {configured!r} != {FIXED_VOCABULARY!r}"
                    )
                if adapter._prompts_set is not None:
                    raise RuntimeError("fixed-vocabulary warmup mutated the dynamic prompt cache")
                plan = PromptPlan(
                    set_id="t1_fixed_vocabulary",
                    backend="yoloe",
                    phrases=tuple(
                        PromptPhrase(index, text, prompt_id, prompt_id)
                        for index, (prompt_id, text) in enumerate(FIXED_VOCABULARY)
                    ),
                )
                original_set_classes = adapter.model.set_classes

                def forbid_set_classes(*_args, **_kwargs):
                    raise RuntimeError("set_classes is forbidden for a fixed-vocabulary checkpoint")

                adapter.model.set_classes = forbid_set_classes
                inference_started = time.monotonic()
                print("T1_MEDIA_PLANE_STAGE inference_start", file=sys.stderr, flush=True)
                try:
                    detections = await asyncio.to_thread(adapter.predict, sample_image, plan)
                finally:
                    adapter.model.set_classes = original_set_classes
                inference_seconds = time.monotonic() - inference_started
                print("T1_MEDIA_PLANE_STAGE inference_done", file=sys.stderr, flush=True)
                allowed = {prompt_id for prompt_id, _ in FIXED_VOCABULARY}
                if any(detection.prompt_id not in allowed for detection in detections):
                    raise RuntimeError("media-plane emitted a detection outside fixed vocabulary")
                service_result = {
                    "ready": True,
                    "model_ref": settings.model_ref,
                    "resolved_device": model_section.device,
                    "ordered_vocabulary": [
                        {"class_id": index, "id": prompt_id, "text": text}
                        for index, (prompt_id, text) in enumerate(FIXED_VOCABULARY)
                    ],
                    "dynamic_prompt_cache_untouched": True,
                    "startup_warmup_enabled": warmup,
                    "set_classes_forbidden_during_inference": True,
                    "warmup_and_load_seconds": load_seconds,
                    "inference_seconds": inference_seconds,
                    "detections": len(detections),
                    "detection_prompt_ids": [detection.prompt_id for detection in detections],
                }
            print("T1_MEDIA_PLANE_STAGE lifespan_shutdown", file=sys.stderr, flush=True)
            if service_result is None:
                raise RuntimeError("media-plane lifespan exited without serving evidence")
            return service_result
    finally:
        if sys.path and sys.path[0] == str(src):
            sys.path.pop(0)


def _exercise_adapter(
    *,
    media_plane_root: Path,
    checkpoint: Path,
    sample_image: Path,
    device: str,
    warmup: bool,
) -> dict[str, object]:
    src = media_plane_root / "src"
    sys.path.insert(0, str(src))
    try:
        prompt_module = importlib.import_module("eovrt_media.config.prompt_plan")
        adapter_module = importlib.import_module("eovrt_media.models.yoloe_adapter")
        PromptPhrase = prompt_module.PromptPhrase
        PromptPlan = prompt_module.PromptPlan
        adapter = adapter_module.YOLOEUltralyticsAdapter(
            weights=str(checkpoint),
            device=device,
            confidence_threshold=0.25,
            iou_threshold=0.5,
            image_size=640,
            half_precision=False,
            warmup=warmup,
            fixed_vocabulary=FIXED_VOCABULARY,
        )
        started = time.monotonic()
        adapter.load()
        load_seconds = time.monotonic() - started
        try:
            if adapter._prompts_set is not None:
                raise RuntimeError("fixed-vocabulary load mutated the dynamic prompt cache")
            plan = PromptPlan(
                set_id="t1_fixed_vocabulary",
                backend="yoloe",
                phrases=tuple(
                    PromptPhrase(index, text, prompt_id, prompt_id)
                    for index, (prompt_id, text) in enumerate(FIXED_VOCABULARY)
                ),
            )
            original_set_classes = adapter.model.set_classes

            def forbid_set_classes(*_args, **_kwargs):
                raise RuntimeError("set_classes is forbidden for a fixed-vocabulary checkpoint")

            adapter.model.set_classes = forbid_set_classes
            inference_started = time.monotonic()
            try:
                detections = adapter.predict(sample_image, plan)
            finally:
                adapter.model.set_classes = original_set_classes
            inference_seconds = time.monotonic() - inference_started
            allowed = {prompt_id for prompt_id, _ in FIXED_VOCABULARY}
            if any(detection.prompt_id not in allowed for detection in detections):
                raise RuntimeError("media-plane emitted a detection outside fixed vocabulary")
            return {
                "ready": True,
                "execution_path": "direct_adapter",
                "resolved_device": adapter.device,
                "ordered_vocabulary": [
                    {"class_id": index, "id": prompt_id, "text": text}
                    for index, (prompt_id, text) in enumerate(FIXED_VOCABULARY)
                ],
                "dynamic_prompt_cache_untouched": True,
                "startup_warmup_enabled": warmup,
                "set_classes_forbidden_during_inference": True,
                "warmup_and_load_seconds": load_seconds,
                "inference_seconds": inference_seconds,
                "detections": len(detections),
                "detection_prompt_ids": [detection.prompt_id for detection in detections],
            }
        finally:
            adapter.close()
    finally:
        if sys.path and sys.path[0] == str(src):
            sys.path.pop(0)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--media-plane-root", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--sample-image", type=Path, required=True)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--mode", choices=("adapter", "service"), default="service")
    parser.add_argument("--warmup", action="store_true")
    parser.add_argument("--timeout-seconds", type=float, default=300.0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    media_plane_root = args.media_plane_root.resolve()
    checkpoint = args.checkpoint.resolve()
    sample_image = args.sample_image.resolve()
    for path in (checkpoint, sample_image):
        if path.is_symlink() or not path.is_file():
            raise FileNotFoundError(f"required regular file is missing: {path}")
    source_hashes = {
        relative: sha256_file(media_plane_root / relative) for relative in MEDIA_SOURCES
    }
    if args.mode == "service":
        service = asyncio.run(
            asyncio.wait_for(
                _exercise_service(
                    media_plane_root=media_plane_root,
                    checkpoint=checkpoint,
                    sample_image=sample_image,
                    device=args.device,
                    warmup=args.warmup,
                ),
                timeout=args.timeout_seconds,
            )
        )
        status = "fixed_vocabulary_serving_passed"
    else:
        service = _exercise_adapter(
                media_plane_root=media_plane_root,
                checkpoint=checkpoint,
                sample_image=sample_image,
                device=args.device,
                warmup=args.warmup,
        )
        status = "fixed_vocabulary_adapter_passed"
    evidence = {
        "schema_version": "eovrt.t1-media-plane-serving-smoke.v1",
        "status": status,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "checkpoint": {
            "filename": checkpoint.name,
            "sha256": sha256_file(checkpoint),
            "size_bytes": checkpoint.stat().st_size,
        },
        "sample": {
            "filename": sample_image.name,
            "sha256": sha256_file(sample_image),
        },
        "media_plane": {**_git_state(media_plane_root), "source_sha256": source_hashes},
        "service": service,
    }
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(output)
    print(f"T1_MEDIA_PLANE_OK output={output} detections={service['detections']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
