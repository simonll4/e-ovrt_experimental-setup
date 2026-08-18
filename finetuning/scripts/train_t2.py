#!/usr/bin/env python3
"""Run the frozen YOLOE-26s T2 full fine-tuning recipe inside the T2 bundle.

T2 (D-FT-14/D-FT-15) entrena el detector completo conservando la interfaz
open-vocabulary. Difiere de T1 en UNA variable: el alcance entrenable.

  T1  YOLOEPETrainer  ->  `del savpe` + `fuse(model.pe)`: los embeddings de texto
                          quedan fusionados en el head. Vocabulario fijo (D-FT-08).
                          12 tensores / 3.096 parámetros.
  T2  YOLOETrainer    ->  sin fusión: `reprta` y `savpe` sobreviven y el checkpoint
                          sigue aceptando `set_classes`. 390 tensores /
                          10.350.308 parámetros (x3.343 la capacidad de T1).

`reprta`/`savpe` se congelan a propósito: así la erosión que mida COCO (D-FT-04) es
deriva de features y no colapso de la proyección de texto hacia 4 clases.

Este script NO modifica `train_t1.py` — lo importa. Aquel está congelado por hash en
el protocolo T1 y su inmutabilidad es parte de la evidencia.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from train_t1 import (  # noqa: E402  (import tras ajustar sys.path, a propósito)
    EFFECTIVE_PROFILE_KEYS,
    _best_epoch,
    _read_trainer_results_csv,
    _runtime_versions,
    _validate_epoch_schedule,
    sha256_file,
    write_json,
)

EXPECTED_SCHEMA = "eovrt.finetuning-config.v1"
EXPECTED_CLASSES = {0: "person", 1: "helmet", 2: "vest", 3: "bare head"}
EXPECTED_SCOPE_GUARD = "eovrt.full_detector_ov_preserved.v1"
EXPECTED_TRAINABLE_SCOPE = "full_detector_ov_preserved"


def load_config(path: Path) -> dict[str, object]:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ValueError(f"invalid T2 config: {path}")
    if config.get("schema_version") != EXPECTED_SCHEMA:
        raise ValueError(f"T2 config schema must be {EXPECTED_SCHEMA}")
    if config.get("experiment_id") != "t2_yoloe26s_full":
        raise ValueError("T2 config must declare experiment_id t2_yoloe26s_full")
    classes = {int(k): v for k, v in (config.get("model") or {}).get("training_classes", {}).items()}
    if classes != EXPECTED_CLASSES:
        raise ValueError(f"T2 training classes {classes!r} != frozen {EXPECTED_CLASSES!r}")
    trainer = config.get("trainer") or {}
    if trainer.get("scope_guard") != EXPECTED_SCOPE_GUARD:
        raise ValueError(f"T2 must enforce the scope guard {EXPECTED_SCOPE_GUARD}")
    if trainer.get("implementation") != "ultralytics.models.yolo.yoloe.YOLOETrainer":
        raise ValueError("T2 must use YOLOETrainer: YOLOEPETrainer fuses the text head")
    prefixes = trainer.get("frozen_prefixes")
    if not isinstance(prefixes, list) or not prefixes:
        raise ValueError("T2 must declare the frozen prompt-path prefixes")
    for key in (
        "expected_trainable_tensors",
        "expected_trainable_parameters",
        "expected_frozen_tensors",
        "expected_frozen_parameters",
    ):
        if int(trainer.get(key, 0)) <= 0:
            raise ValueError(f"T2 trainer must declare a positive {key}")
    for key in ("expected_trainable_names_sha256", "expected_frozen_names_sha256"):
        if not isinstance(trainer.get(key), str) or len(trainer[key]) != 64:
            raise ValueError(f"T2 trainer must declare {key} as a sha256 hex digest")
    return config


def resolve_profile(config: dict[str, object], profile: str) -> dict[str, object]:
    trainer = dict(config["trainer"])
    resolved = {key: trainer[key] for key in EFFECTIVE_PROFILE_KEYS if key in trainer}
    resolved.setdefault("fraction", 1.0)
    resolved["device"] = trainer["device"]
    if profile == "smoke":
        smoke = config.get("smoke") or {}
        resolved["epochs"] = int(smoke.get("epochs", 1))
        resolved["fraction"] = float(smoke.get("fraction", 0.05))
    return resolved


def _bundle_path(bundle: Path, relative: str) -> Path:
    candidate = (bundle / relative).resolve()
    if not str(candidate).startswith(str(bundle.resolve())):
        raise ValueError(f"path escapes the bundle: {relative}")
    if not candidate.exists():
        raise FileNotFoundError(f"missing bundle artifact: {candidate}")
    return candidate


def validate_bundle(config: dict[str, object], bundle: Path) -> dict[str, Path]:
    model = config["model"]
    data = config["data"]
    return {
        "base_weight": _bundle_path(bundle, str(model["base_weight"])),
        "text_encoder": _bundle_path(bundle, str(model["text_encoder"])),
        "data_yaml": _bundle_path(bundle, str(data["yaml"])),
        "data_manifest": _bundle_path(bundle, str(data["manifest"])),
    }


def _names_digest(names: list[str]) -> str:
    return hashlib.sha256("\n".join(sorted(names)).encode("utf-8")).hexdigest()


def apply_scope_guard(model: object, trainer_config: dict[str, object]) -> dict[str, object]:
    """Freeze the prompt paths and leave the rest of the detector trainable."""
    prefixes = tuple(str(prefix) for prefix in trainer_config["frozen_prefixes"])
    named = list(model.named_parameters())
    if not named:
        raise RuntimeError("T2 scope guard found no parameters")
    for name, parameter in named:
        parameter.requires_grad_(not name.startswith(prefixes))
    trainable = [(n, p) for n, p in named if p.requires_grad]
    frozen = [(n, p) for n, p in named if not p.requires_grad]
    if not trainable:
        raise RuntimeError("T2 scope guard left nothing trainable")
    if not frozen:
        raise RuntimeError("T2 scope guard froze no prompt path: OV retention would be moot")
    return _contract(trainable, frozen)


def _contract(trainable: list, frozen: list) -> dict[str, object]:
    return {
        "scope": EXPECTED_TRAINABLE_SCOPE,
        "tensor_count": len(trainable),
        "parameter_count": sum(p.numel() for _, p in trainable),
        "names_sha256": _names_digest([n for n, _ in trainable]),
        "frozen_tensor_count": len(frozen),
        "frozen_parameter_count": sum(p.numel() for _, p in frozen),
        "frozen_names_sha256": _names_digest([n for n, _ in frozen]),
    }


def current_contract(model: object) -> dict[str, object]:
    named = list(model.named_parameters())
    return _contract(
        [(n, p) for n, p in named if p.requires_grad],
        [(n, p) for n, p in named if not p.requires_grad],
    )


def validate_scope_contract(
    contract: dict[str, object], trainer_config: dict[str, object], *, require_optimizer: bool
) -> None:
    expected = {
        "scope": EXPECTED_TRAINABLE_SCOPE,
        "tensor_count": int(trainer_config["expected_trainable_tensors"]),
        "parameter_count": int(trainer_config["expected_trainable_parameters"]),
        "names_sha256": str(trainer_config["expected_trainable_names_sha256"]),
        "frozen_tensor_count": int(trainer_config["expected_frozen_tensors"]),
        "frozen_parameter_count": int(trainer_config["expected_frozen_parameters"]),
        "frozen_names_sha256": str(trainer_config["expected_frozen_names_sha256"]),
    }
    actual = {key: contract.get(key) for key in expected}
    if actual != expected:
        raise RuntimeError(f"T2 scope contract {actual!r} != frozen {expected!r}")
    optimized = contract.get("optimizer_parameter_count")
    if require_optimizer and optimized != expected["parameter_count"]:
        raise RuntimeError(
            f"T2 optimizer parameter count {optimized!r} != frozen {expected['parameter_count']}"
        )


def verify_open_vocabulary(checkpoint: Path, probe_names: list[str]) -> dict[str, object]:
    """Prove the trained checkpoint still serves an arbitrary vocabulary.

    Es la evidencia que hace medible la retención OV de D-FT-04: si el head hubiera
    quedado fusionado (como en T1), esto falla acá y no en la evaluación de COCO.
    """
    import torch
    from ultralytics.nn.tasks import YOLOEModel

    loaded = torch.load(checkpoint, map_location="cpu", weights_only=False)
    model = loaded["model"] if isinstance(loaded, dict) else loaded
    model = model.float().eval()
    if getattr(model.model[-1], "savpe", None) is None:
        raise RuntimeError("T2 checkpoint lost savpe: the head was fused, OV is gone")
    if not hasattr(model, "get_text_pe"):
        raise RuntimeError("T2 checkpoint has no text path: OV retention is undefined")
    with torch.no_grad():
        embeddings = model.get_text_pe(probe_names)
        model.set_classes(probe_names, embeddings)
        model(torch.zeros(1, 3, 640, 640))
    return {
        "status": "open_vocabulary_preserved",
        "probe_class_count": len(probe_names),
        "probe_names_sha256": _names_digest(probe_names),
        "savpe_present": True,
        "text_path_present": True,
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
    checks.add_argument("--check-scope", action="store_true")
    parser.add_argument("--allow-cpu", action="store_true")
    args = parser.parse_args(argv)

    if args.allow_cpu and not (args.check_only or args.check_scope):
        parser.error("--allow-cpu is restricted to --check-only/--check-scope preflight")

    bundle = args.bundle.resolve()
    config_path = args.config.resolve()
    config = load_config(config_path)
    paths = validate_bundle(config, bundle)
    profile = resolve_profile(config, args.profile)
    versions = _runtime_versions()

    import torch
    from ultralytics import YOLOE
    from ultralytics.models.yolo.yoloe import YOLOETrainer

    if not args.allow_cpu and not torch.cuda.is_available():
        raise RuntimeError("T2 requires CUDA; local runs are preflight only (D-100.1)")

    class EOVRTYOLOETrainer(YOLOETrainer):
        """YOLOETrainer con el guard de alcance de T2 aplicado y verificado."""

        def get_model(self, cfg=None, weights=None, verbose: bool = True):
            model = super().get_model(cfg=cfg, weights=weights, verbose=verbose)
            # Preflight: deja el contrato observable en --check-scope. NO alcanza para el
            # entrenamiento — `_setup_train` re-habilita requires_grad en todo lo que no
            # esté en su lista `freeze`, y nuestras rutas de prompt son submódulos del
            # head, no capas enteras. El guard efectivo va en _build_train_pipeline.
            contract = apply_scope_guard(model, config["trainer"])
            validate_scope_contract(contract, config["trainer"], require_optimizer=False)
            return model

        def _build_train_pipeline(self) -> None:
            # Corre DESPUÉS del bloque que re-habilita y ANTES de construir el optimizador:
            # es el único punto donde el alcance queda fijado para el entrenamiento real.
            contract = apply_scope_guard(self.model, config["trainer"])
            validate_scope_contract(contract, config["trainer"], require_optimizer=False)
            self.eovrt_trainable_contract = contract
            prefixes = [str(prefix) for prefix in config["trainer"]["frozen_prefixes"]]
            self.freeze_layer_names = list(
                dict.fromkeys(list(getattr(self, "freeze_layer_names", [])) + prefixes)
            )
            super()._build_train_pipeline()

        def build_optimizer(self, model, *fn_args, **fn_kwargs):
            optimizer = super().build_optimizer(model, *fn_args, **fn_kwargs)
            # `BaseTrainer.build_optimizer` agrupa TODOS los parámetros, sin mirar
            # requires_grad: hay que podarlo, no sólo verificarlo.
            allowed = {id(p) for p in model.parameters() if p.requires_grad}
            for group in optimizer.param_groups:
                group["params"] = [p for p in group["params"] if id(p) in allowed]
            optimized = {
                id(p) for group in optimizer.param_groups for p in group["params"]
            }
            if optimized != allowed:
                raise RuntimeError("T2 optimizer parameters differ from the scope guard")
            self.eovrt_trainable_contract["optimizer_parameter_count"] = sum(
                p.numel() for group in optimizer.param_groups for p in group["params"]
            )
            return optimizer

        def _model_train(self) -> None:
            super()._model_train()
            validate_scope_contract(
                current_contract(self.model), config["trainer"], require_optimizer=False
            )

        def read_results_csv(self) -> dict[str, list[object]]:
            return _read_trainer_results_csv(Path(self.csv))

    if args.check_only:
        print(json.dumps({"status": "preflight_ok", "versions": versions}, sort_keys=True))
        return 0

    if args.check_scope:
        previous_cwd = Path.cwd()
        os.chdir(paths["text_encoder"].parent)
        try:
            wrapper = YOLOE(config["model"]["architecture"]).load(str(paths["base_weight"]))
            trainer = object.__new__(EOVRTYOLOETrainer)
            trainer.data = {"channels": 3, "nc": 4, "names": EXPECTED_CLASSES}
            scoped = trainer.get_model(
                cfg=wrapper.model.yaml, weights=wrapper.model, verbose=False
            )
            contract = current_contract(scoped)
        finally:
            os.chdir(previous_cwd)
        validate_scope_contract(contract, config["trainer"], require_optimizer=False)
        print(json.dumps({"status": "scope_ok", "contract": contract}, sort_keys=True))
        return 0

    # D-100.1: el entrenamiento SÓLO corre en el clúster, y este es el cerco que lo
    # garantiza. Pedir "CUDA disponible" NO alcanza —cualquier laptop con GPU lo pasa, y
    # así se entrenó local por error el 2026-08-17, tumbando WSL por global_oom tres
    # veces—. Va acá abajo a propósito: --check-only/--check-scope ya retornaron, así que
    # el preflight local sigue funcionando y lo único vedado es entrenar de verdad.
    # Escotilla explícita para un host de cómputo sin Slurm; jamás para "probar rápido".
    if not os.environ.get("SLURM_JOB_ID") and os.environ.get(
        "EOVRT_ALLOW_NON_SLURM_TRAIN"
    ) != "1":
        raise RuntimeError(
            "T2 training must run inside a Slurm job (D-100.1: nunca entrenar local). "
            "Preflight local: usar --check-only/--check-scope."
        )

    output = args.output.resolve()
    run_dir = output / args.run_name
    if run_dir.exists():
        raise FileExistsError(f"refusing to reuse run directory: {run_dir}")
    output.mkdir(parents=True, exist_ok=True)
    started_at = datetime.now(timezone.utc)
    launch = {
        "schema_version": "eovrt.t2-run.v1",
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
            trainer=EOVRTYOLOETrainer,
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
        launch.update(
            {
                "status": "failed",
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "error_type": type(error).__name__,
                "error": str(error),
            }
        )
        contract = getattr(getattr(model, "trainer", None), "eovrt_trainable_contract", None)
        if isinstance(contract, dict):
            launch["trainable_contract"] = dict(contract)
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
        for required in (best, last, results_csv):
            if not required.is_file():
                raise FileNotFoundError(f"training completed without required artifact: {required}")
        epoch_schedule = _validate_epoch_schedule(results_csv, int(profile["epochs"]))
        contract = getattr(getattr(model, "trainer", None), "eovrt_trainable_contract", None)
        if not isinstance(contract, dict):
            raise RuntimeError("training completed without the T2 scope contract")
        validate_scope_contract(dict(contract), config["trainer"], require_optimizer=True)
        probe = [str(name) for name in EXPECTED_CLASSES.values()] + ["dog", "traffic light"]
        ov_evidence = verify_open_vocabulary(best, probe)
        write_json(actual_run_dir / "open_vocabulary_check.json", ov_evidence)
        launch.update(
            {
                "status": "succeeded",
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "elapsed_seconds": (datetime.now(timezone.utc) - started_at).total_seconds(),
                "run_dir": str(actual_run_dir),
                "completed_epochs": epoch_schedule,
                "trainable_contract": dict(contract),
                "open_vocabulary_check": ov_evidence,
                "best_epoch": _best_epoch(results_csv),
                "artifacts": {
                    path.name: {"sha256": sha256_file(path), "size_bytes": path.stat().st_size}
                    for path in (best, last, results_csv)
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
    print(f"T2_{args.profile.upper()}_OK run_dir={actual_run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
