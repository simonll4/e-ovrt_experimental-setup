#!/usr/bin/env python3
"""Run the frozen YOLOE-26s T1 linear-probing recipe inside the T1 bundle."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

EXPECTED_SCHEMA = "eovrt.finetuning-config.v1"
EXPECTED_CLASSES = {0: "person", 1: "helmet", 2: "vest", 3: "bare head"}
EXPECTED_TRAINABLE_SCOPE = "fused_class_projection_only"
EFFECTIVE_PROFILE_KEYS = (
    "epochs",
    "batch",
    "workers",
    "imgsz",
    "seed",
    "deterministic",
    "val",
    "plots",
    "save",
    "save_period",
    "fraction",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def load_config(path: Path) -> dict[str, object]:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ValueError("T1 config must be a mapping")
    if config.get("schema_version") != EXPECTED_SCHEMA:
        raise ValueError(f"config schema must be {EXPECTED_SCHEMA}")
    vocabulary = [
        (int(key), value) for key, value in config["model"]["fixed_vocabulary"].items()
    ]
    if vocabulary != list(EXPECTED_CLASSES.items()):
        raise ValueError(
            f"ordered fixed vocabulary {vocabulary!r} != {list(EXPECTED_CLASSES.items())!r}"
        )
    trainer = config["trainer"]
    if trainer["checkpoint_policy"] != "best_metrics_mAP50-95_B_all_four_val_classes":
        raise ValueError("unexpected checkpoint policy")
    if trainer.get("freeze_guard") != "eovrt.fused_class_projection_only.v1":
        raise ValueError("T1 must enforce the fused class projection freeze guard")
    names = trainer.get("expected_trainable_names")
    if not isinstance(names, list) or len(names) != len(set(names)):
        raise ValueError("T1 expected trainable names must be a unique ordered list")
    if int(trainer.get("expected_trainable_tensors", 0)) != len(names):
        raise ValueError("T1 expected trainable tensor count differs from its name inventory")
    if int(trainer.get("expected_trainable_parameters", 0)) <= 0:
        raise ValueError("T1 expected trainable parameter count must be positive")
    if int(trainer["epochs"]) != 10 or not trainer["retain_last"]:
        raise ValueError("T1 must retain last.pt across the frozen 10-epoch schedule")
    return config


def resolve_profile(config: dict[str, object], profile: str) -> dict[str, object]:
    trainer = dict(config["trainer"])
    if profile == "smoke":
        trainer["epochs"] = int(config["smoke"]["epochs"])
        trainer["fraction"] = float(config["smoke"]["fraction"])
    elif profile == "full":
        trainer["fraction"] = 1.0
    else:
        raise ValueError(f"unknown profile: {profile}")
    return trainer


def _bundle_path(bundle: Path, relative: str) -> Path:
    target = (bundle / relative).resolve()
    try:
        target.relative_to(bundle.resolve())
    except ValueError as error:
        raise ValueError(f"bundle path escapes root: {relative}") from error
    if not target.exists():
        raise FileNotFoundError(target)
    return target


def validate_bundle(config: dict[str, object], bundle: Path) -> dict[str, Path]:
    paths = {
        "base_weight": _bundle_path(bundle, config["model"]["base_weight"]),
        "text_encoder": _bundle_path(bundle, config["model"]["text_encoder"]),
        "data_yaml": _bundle_path(bundle, config["data"]["yaml"]),
        "data_manifest": _bundle_path(bundle, config["data"]["manifest"]),
    }
    data = yaml.safe_load(paths["data_yaml"].read_text(encoding="utf-8"))
    names = [(int(key), value) for key, value in data["names"].items()]
    if names != list(EXPECTED_CLASSES.items()) or int(data["nc"]) != 4:
        raise ValueError(f"data.yaml ordered vocabulary is not frozen T1 vocabulary: {names!r}")
    payload = json.loads((paths["data_yaml"].parent / "payload.json").read_text(encoding="utf-8"))
    expected_images = {
        "train": int(config["data"]["train_images"]),
        "val": int(config["data"]["val_images"]),
    }
    if payload["images"] != expected_images:
        raise ValueError(f"payload image counts {payload['images']} != {expected_images}")
    weights = json.loads(
        (bundle / "manifests" / "t1_base_weights.json").read_text(encoding="utf-8")
    )
    by_name = {item["filename"]: item for item in weights["artifacts"]}
    for key in ("base_weight", "text_encoder"):
        path = paths[key]
        record = by_name[path.name]
        if path.stat().st_size != int(record["size_bytes"]) or sha256_file(path) != record["sha256"]:
            raise ValueError(f"base asset integrity failure: {path.name}")
    return paths


def _best_epoch(results_csv: Path) -> dict[str, object]:
    with results_csv.open(encoding="utf-8", newline="") as handle:
        rows = [{key.strip(): value for key, value in row.items()} for row in csv.DictReader(handle)]
    metric = "metrics/mAP50-95(B)"
    if not rows or metric not in rows[0]:
        raise ValueError(f"{results_csv} does not contain {metric}")
    best = max(rows, key=lambda row: float(row[metric]))
    return {"epoch": int(best["epoch"]), "metric": metric, "value": float(best[metric])}


def _read_trainer_results_csv(results_csv: Path) -> dict[str, list[object]]:
    """Read Ultralytics results without requiring a CPU-specific Polars wheel."""
    columns: dict[str, list[object]] = {}
    with results_csv.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            for raw_key, raw_value in row.items():
                key = raw_key.strip()
                value = raw_value.strip()
                if value == "":
                    parsed: object = None
                else:
                    try:
                        number = float(value)
                    except ValueError:
                        parsed = value
                    else:
                        parsed = int(number) if key == "epoch" else number
                columns.setdefault(key, []).append(parsed)
    return columns


def _validate_epoch_schedule(results_csv: Path, expected_epochs: int) -> list[int]:
    epochs = _read_trainer_results_csv(results_csv).get("epoch", [])
    expected = list(range(1, expected_epochs + 1))
    if epochs != expected:
        raise ValueError(f"results epoch schedule {epochs!r} != {expected!r}")
    return expected


def _freeze_fused_class_projection(model: object) -> dict[str, object]:
    """Freeze YOLOE and retain only the fused per-class projection convolutions."""
    named_parameters = list(model.named_parameters())
    names_by_id = {id(parameter): name for name, parameter in named_parameters}
    head = model.model[-1]
    selected_ids: set[int] = set()
    for branch_name in ("cv3", "one2one_cv3"):
        branch = getattr(head, branch_name, None)
        if branch is None:
            continue
        for scale_index, block in enumerate(branch):
            if len(block) <= 2:
                raise RuntimeError(f"{branch_name}[{scale_index}] has no fused projection")
            projection = block[2]
            parameters = list(projection.parameters())
            if not parameters:
                raise RuntimeError(f"{branch_name}[{scale_index}][2] has no parameters")
            selected_ids.update(id(parameter) for parameter in parameters)

    selected_names = sorted(names_by_id[parameter_id] for parameter_id in selected_ids)
    if not selected_names:
        raise RuntimeError("T1 freeze guard found no fused class projection parameters")
    for _, parameter in named_parameters:
        parameter.requires_grad_(id(parameter) in selected_ids)
    actual_names = sorted(name for name, parameter in named_parameters if parameter.requires_grad)
    if actual_names != selected_names:
        raise RuntimeError("T1 freeze guard could not isolate the fused class projection")
    parameter_count = sum(
        parameter.numel() for _, parameter in named_parameters if parameter.requires_grad
    )
    return {
        "scope": "fused_class_projection_only",
        "tensor_count": len(actual_names),
        "parameter_count": parameter_count,
        "names": actual_names,
    }


def _trainer_contract(trainer: object | None) -> dict[str, object] | None:
    if trainer is None:
        return None
    contract = getattr(trainer, "eovrt_trainable_contract", None)
    if not isinstance(contract, dict):
        return None
    return dict(contract)


def _current_trainable_contract(model: object) -> dict[str, object]:
    trainable = [
        (name, parameter)
        for name, parameter in model.named_parameters()
        if parameter.requires_grad
    ]
    return {
        "scope": EXPECTED_TRAINABLE_SCOPE,
        "tensor_count": len(trainable),
        "parameter_count": sum(parameter.numel() for _, parameter in trainable),
        "names": sorted(name for name, _ in trainable),
    }


def validate_trainable_contract(
    contract: dict[str, object], trainer_config: dict[str, object], *, require_optimizer: bool
) -> None:
    expected = {
        "scope": EXPECTED_TRAINABLE_SCOPE,
        "tensor_count": int(trainer_config["expected_trainable_tensors"]),
        "parameter_count": int(trainer_config["expected_trainable_parameters"]),
        "names": list(trainer_config["expected_trainable_names"]),
    }
    actual = {key: contract.get(key) for key in expected}
    if actual != expected:
        raise RuntimeError(f"T1 trainable contract {actual!r} != frozen {expected!r}")
    optimizer_count = contract.get("optimizer_parameter_count")
    if require_optimizer and optimizer_count != expected["parameter_count"]:
        raise RuntimeError(
            "T1 optimizer parameter count "
            f"{optimizer_count!r} != frozen {expected['parameter_count']}"
        )


def expected_effective_profile(profile: dict[str, object]) -> dict[str, object]:
    expected = {key: profile[key] for key in EFFECTIVE_PROFILE_KEYS}
    expected["device"] = str(profile["device"])
    expected["task"] = "detect"
    expected["mode"] = "train"
    return expected


def audit_optimizer_checkpoint(
    checkpoint: Path,
    *,
    expected_epoch: int,
    expected_profile: dict[str, object],
    expected_parameter_tensors: int,
) -> dict[str, object]:
    import torch

    saved = torch.load(checkpoint, map_location="cpu", weights_only=False)
    if int(saved.get("epoch", -1)) != expected_epoch:
        raise RuntimeError(
            f"optimizer checkpoint epoch {saved.get('epoch')!r} != {expected_epoch}"
        )
    optimizer = saved.get("optimizer")
    if not isinstance(optimizer, dict):
        raise RuntimeError("periodic checkpoint does not retain optimizer state")
    groups = optimizer.get("param_groups")
    state = optimizer.get("state")
    if not isinstance(groups, list) or not isinstance(state, dict):
        raise RuntimeError("periodic checkpoint optimizer payload is malformed")
    parameter_indices = {
        index
        for group in groups
        for index in group.get("params", [])
    }
    state_indices = set(state)
    if len(parameter_indices) != expected_parameter_tensors:
        raise RuntimeError(
            f"optimizer checkpoint exposes {len(parameter_indices)} tensors "
            f"!= {expected_parameter_tensors}"
        )
    if state_indices != parameter_indices:
        raise RuntimeError("optimizer state indices differ from optimizer parameter groups")
    train_args = saved.get("train_args")
    if not isinstance(train_args, dict):
        raise RuntimeError("periodic checkpoint lacks effective train_args")
    effective = {key: train_args.get(key) for key in expected_effective_profile(expected_profile)}
    expected = expected_effective_profile(expected_profile)
    if effective != expected:
        raise RuntimeError(f"effective trainer profile {effective!r} != frozen {expected!r}")
    return {
        "checkpoint": checkpoint.name,
        "checkpoint_sha256": sha256_file(checkpoint),
        "size_bytes": checkpoint.stat().st_size,
        "epoch_zero_based": expected_epoch,
        "optimizer_param_groups": len(groups),
        "optimizer_group_tensor_counts": [len(group.get("params", [])) for group in groups],
        "optimizer_parameter_tensors": len(parameter_indices),
        "optimizer_state_tensors": len(state_indices),
        "state_indices_match_parameter_groups": True,
        "effective_profile": effective,
    }


def _runtime_versions() -> dict[str, object]:
    import torch
    import ultralytics

    return {
        "python": sys.version,
        "platform": platform.platform(),
        "torch": torch.__version__,
        "torch_cuda": torch.version.cuda,
        "ultralytics": ultralytics.__version__,
        "cuda_available": torch.cuda.is_available(),
        "cuda_device_count": torch.cuda.device_count(),
        "cuda_device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
    }


def _checkpoint_inference_smoke(
    *, checkpoint: Path, data_yaml: Path, device: int, imgsz: int
) -> dict[str, object]:
    from ultralytics import YOLOE

    data = yaml.safe_load(data_yaml.read_text(encoding="utf-8"))
    val_root = (data_yaml.parent / data["val"]).resolve()
    image = next(
        (
            path
            for path in sorted(val_root.rglob("*"))
            if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
        ),
        None,
    )
    if image is None:
        raise ValueError(f"validation payload has no image under {val_root}")
    checkpoint_model = YOLOE(str(checkpoint))
    names_value = checkpoint_model.names
    names_items = [
        (int(key), value)
        for key, value in (
            names_value.items() if isinstance(names_value, dict) else enumerate(names_value)
        )
    ]
    if names_items != list(EXPECTED_CLASSES.items()):
        raise ValueError(
            f"checkpoint ordered vocabulary {names_items!r} "
            f"!= {list(EXPECTED_CLASSES.items())!r}"
        )
    names = dict(names_items)
    predictions = checkpoint_model.predict(
        source=str(image), device=device, imgsz=imgsz, verbose=False, save=False
    )
    if len(predictions) != 1:
        raise ValueError(f"checkpoint inference returned {len(predictions)} results")
    class_ids = [int(value) for value in predictions[0].boxes.cls.cpu().tolist()]
    if any(class_id not in EXPECTED_CLASSES for class_id in class_ids):
        raise ValueError(f"checkpoint emitted invalid class ids: {class_ids}")
    return {
        "status": "passed",
        "checkpoint": checkpoint.name,
        "checkpoint_sha256": sha256_file(checkpoint),
        "sample_image": image.relative_to(data_yaml.parent).as_posix(),
        "vocabulary": names,
        "detections": len(class_ids),
        "class_ids": class_ids,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--profile", choices=("smoke", "full"), default="smoke")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--run-name", required=True)
    checks = parser.add_mutually_exclusive_group()
    checks.add_argument("--check-only", action="store_true")
    checks.add_argument("--check-freeze", action="store_true")
    parser.add_argument("--allow-cpu", action="store_true")
    args = parser.parse_args(argv)
    if args.allow_cpu and not (args.check_only or args.check_freeze):
        parser.error(
            "--allow-cpu solo es valido junto a --check-only/--check-freeze "
            "(D-100.1: el entrenamiento nunca corre fuera del cluster)"
        )

    bundle = args.bundle.resolve()
    config_path = args.config.resolve()
    config = load_config(config_path)
    paths = validate_bundle(config, bundle)
    profile = resolve_profile(config, args.profile)
    versions = _runtime_versions()
    if versions["ultralytics"] != str(config["trainer"]["ultralytics"]):
        raise RuntimeError(
            f"ultralytics {versions['ultralytics']} != frozen {config['trainer']['ultralytics']}"
        )
    if not versions["cuda_available"] and not args.allow_cpu:
        raise RuntimeError("CUDA is not available inside the training runtime")

    from ultralytics import YOLOE
    from ultralytics.models.yolo.yoloe import YOLOEPETrainer

    class EOVRTYOLOEPETrainer(YOLOEPETrainer):
        """YOLOE linear probe with an explicit freeze and portable CSV serializer."""

        def _build_train_pipeline(self) -> None:
            contract = _freeze_fused_class_projection(self.model)
            validate_trainable_contract(
                contract, config["trainer"], require_optimizer=False
            )
            self.eovrt_trainable_contract = contract
            super()._build_train_pipeline()

        def build_optimizer(self, model, *args, **kwargs):
            optimizer = super().build_optimizer(model, *args, **kwargs)
            allowed = {id(parameter) for parameter in model.parameters() if parameter.requires_grad}
            for group in optimizer.param_groups:
                group["params"] = [
                    parameter for parameter in group["params"] if id(parameter) in allowed
                ]
            optimized = {
                id(parameter)
                for group in optimizer.param_groups
                for parameter in group["params"]
            }
            if optimized != allowed:
                raise RuntimeError("optimizer parameters differ from the T1 freeze guard")
            self.eovrt_trainable_contract["optimizer_parameter_count"] = sum(
                parameter.numel()
                for group in optimizer.param_groups
                for parameter in group["params"]
            )
            return optimizer

        def _model_train(self) -> None:
            from torch import nn

            super()._model_train()
            current = _current_trainable_contract(self.model)
            validate_trainable_contract(current, config["trainer"], require_optimizer=False)
            allowed = {
                id(parameter) for parameter in self.model.parameters() if parameter.requires_grad
            }
            optimized = {
                id(parameter)
                for group in self.optimizer.param_groups
                for parameter in group["params"]
            }
            if optimized != allowed:
                raise RuntimeError("optimizer drifted from the T1 freeze guard")
            for module in self.model.modules():
                if isinstance(module, nn.modules.batchnorm._BatchNorm):
                    module.eval()

        def read_results_csv(self) -> dict[str, list[object]]:
            return _read_trainer_results_csv(Path(self.csv))

    if args.check_only:
        print(json.dumps({"status": "preflight_ok", "versions": versions}, sort_keys=True))
        return 0
    if args.check_freeze:
        previous_cwd = Path.cwd()
        os.chdir(paths["text_encoder"].parent)
        try:
            wrapper = YOLOE(config["model"]["architecture"]).load(
                str(paths["base_weight"])
            )
            trainer = object.__new__(EOVRTYOLOEPETrainer)
            trainer.data = {"channels": 3, "nc": 4, "names": EXPECTED_CLASSES}
            freeze_model = trainer.get_model(
                cfg=wrapper.model.yaml, weights=wrapper.model, verbose=False
            )
            contract = _freeze_fused_class_projection(freeze_model)
        finally:
            os.chdir(previous_cwd)
        validate_trainable_contract(contract, config["trainer"], require_optimizer=False)
        print(json.dumps({"status": "freeze_ok", "contract": contract}, sort_keys=True))
        return 0

    output = args.output.resolve()
    run_dir = output / args.run_name
    if run_dir.exists():
        raise FileExistsError(f"refusing to reuse run directory: {run_dir}")
    output.mkdir(parents=True, exist_ok=True)
    started_at = datetime.now(timezone.utc)
    launch = {
        "schema_version": "eovrt.t1-run.v1",
        "status": "running",
        "profile": args.profile,
        "run_name": args.run_name,
        "started_at": started_at.isoformat(),
        "hostname": socket.gethostname(),
        "slurm": {
            key: os.environ.get(key)
            for key in (
                "SLURM_JOB_ID",
                "SLURM_JOB_NAME",
                "SLURM_JOB_NODELIST",
                "SLURM_JOB_PARTITION",
                "SLURM_CPUS_PER_TASK",
                "SLURM_MEM_PER_NODE",
                "SLURM_GPUS_ON_NODE",
            )
        },
        "config_sha256": sha256_file(config_path),
        "bundle_manifest_sha256": sha256_file(bundle / "bundle.sha256"),
        "data_yaml_sha256": sha256_file(paths["data_yaml"]),
        "data_manifest_sha256": sha256_file(paths["data_manifest"]),
        "base_weight_sha256": sha256_file(paths["base_weight"]),
        "text_encoder_sha256": sha256_file(paths["text_encoder"]),
        "container_image_sha256": os.environ.get("EOVRT_IMAGE_SHA256"),
        "versions": versions,
        "trainer": profile,
    }
    write_json(output / f"{args.run_name}.launch.json", launch)

    model = None
    previous_cwd = Path.cwd()
    os.chdir(paths["text_encoder"].parent)
    try:
        model = YOLOE(config["model"]["architecture"]).load(str(paths["base_weight"]))
        result = model.train(
            data=str(paths["data_yaml"]),
            trainer=EOVRTYOLOEPETrainer,
            epochs=int(profile["epochs"]),
            fraction=float(profile["fraction"]),
            batch=int(profile["batch"]),
            workers=int(profile["workers"]),
            imgsz=int(profile["imgsz"]),
            seed=int(profile["seed"]),
            deterministic=bool(profile["deterministic"]),
            device=int(profile["device"]),
            project=str(output),
            name=args.run_name,
            exist_ok=False,
            plots=bool(profile["plots"]),
            val=bool(profile["val"]),
            save=bool(profile["save"]),
            save_period=int(profile["save_period"]),
        )
    except BaseException as error:
        trainable_contract = _trainer_contract(getattr(model, "trainer", None))
        launch.update(
            {
                "status": "failed",
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "error_type": type(error).__name__,
                "error": str(error),
            }
        )
        if trainable_contract is not None:
            launch["trainable_contract"] = trainable_contract
        write_json(output / f"{args.run_name}.launch.json", launch)
        raise
    finally:
        os.chdir(previous_cwd)

    try:
        actual_run_dir = Path(result.save_dir).resolve()
        checkpoints = actual_run_dir / "weights"
        best = checkpoints / "best.pt"
        last = checkpoints / "last.pt"
        results_csv = actual_run_dir / "results.csv"
        optimizer_checkpoint = checkpoints / f"epoch{int(profile['epochs']) - 1}.pt"
        for required in (best, last, results_csv, optimizer_checkpoint):
            if not required.is_file():
                raise FileNotFoundError(
                    f"training completed without required artifact: {required}"
                )
        epoch_schedule = _validate_epoch_schedule(results_csv, int(profile["epochs"]))
        trainable_contract = _trainer_contract(getattr(model, "trainer", None))
        if trainable_contract is None:
            raise RuntimeError("training completed without the T1 trainable-parameter contract")
        validate_trainable_contract(
            trainable_contract, config["trainer"], require_optimizer=True
        )
        optimizer_evidence = audit_optimizer_checkpoint(
            optimizer_checkpoint,
            expected_epoch=int(profile["epochs"]) - 1,
            expected_profile=profile,
            expected_parameter_tensors=int(
                config["trainer"]["expected_trainable_tensors"]
            ),
        )
        checkpoint_smoke = _checkpoint_inference_smoke(
            checkpoint=best,
            data_yaml=paths["data_yaml"],
            device=int(profile["device"]),
            imgsz=int(profile["imgsz"]),
        )
        write_json(actual_run_dir / "checkpoint_smoke.json", checkpoint_smoke)
        launch.update(
            {
                "status": "succeeded",
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "elapsed_seconds": (datetime.now(timezone.utc) - started_at).total_seconds(),
                "run_dir": str(actual_run_dir),
                "completed_epochs": epoch_schedule,
                "trainable_contract": trainable_contract,
                "optimizer_evidence": optimizer_evidence,
                "best_epoch": _best_epoch(results_csv),
                "checkpoint_inference_smoke": checkpoint_smoke,
                "artifacts": {
                    "best.pt": {
                        "sha256": sha256_file(best),
                        "size_bytes": best.stat().st_size,
                    },
                    "last.pt": {
                        "sha256": sha256_file(last),
                        "size_bytes": last.stat().st_size,
                    },
                    "results.csv": {
                        "sha256": sha256_file(results_csv),
                        "size_bytes": results_csv.stat().st_size,
                    },
                    optimizer_checkpoint.name: {
                        "sha256": sha256_file(optimizer_checkpoint),
                        "size_bytes": optimizer_checkpoint.stat().st_size,
                    },
                },
            }
        )
        write_json(output / f"{args.run_name}.launch.json", launch)
        write_json(actual_run_dir / "eovrt_run_manifest.json", launch)
    except BaseException as error:
        launch.update(
            {
                "status": "failed_postcheck",
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "error_type": type(error).__name__,
                "error": str(error),
            }
        )
        write_json(output / f"{args.run_name}.launch.json", launch)
        raise
    print(f"T1_{args.profile.upper()}_OK run_dir={actual_run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
