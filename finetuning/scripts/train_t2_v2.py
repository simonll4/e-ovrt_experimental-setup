#!/usr/bin/env python3
"""T2 v2 — full fine-tuning con optimizador EXPLÍCITO, desde el peso base (D-FT-16).

Reemplaza al job `1167864`, que usó `optimizer: auto` y quedó submuestreado: el heurístico
de ultralytics calcula el LR sólo a partir de `nc` (número de clases), nunca del conteo de
parámetros entrenables, así que le dio el mismo `AdamW(lr=0,00125)` a T1 (3.096 params) y a
T2 (10.350.308, ×3.343). Verificado en el código instalado, no inferido.

Arranca desde el PESO BASE y no desde el `best.pt` de `1167864` porque ese checkpoint es un
punto de partida peor: en la época 1, T1 daba mAP50 0,1507 y T2 sólo 0,0490 —desde el mismo
peso— cayendo a 0,0255 en la época 2. El full FT a ese LR dañó las features desde el primer
paso; continuar obligaría a deshacer el daño antes de aprender, y dejaría una historia de
optimización en dos fases que hay que explicar en un párrafo en vez de en una frase.

Reusa de `train_t2.py` el guard de alcance y la verificación open-vocabulary — es el MISMO
contrato (390 tensores / 10.350.308 params, `reprta`/`savpe` congelados), no se reimplementa.
No modifica `train_t1.py` ni `train_t2.py`: son evidencia de jobs ya corridos.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from train_t1 import (  # noqa: E402
    EFFECTIVE_PROFILE_KEYS,
    _best_epoch,
    _read_trainer_results_csv,
    _runtime_versions,
    sha256_file,
    write_json,
)
from train_t2 import (  # noqa: E402
    EXPECTED_CLASSES,
    apply_scope_guard,
    current_contract,
    validate_scope_contract,
    verify_open_vocabulary,
)

EXPECTED_SCHEMA = "eovrt.finetuning-config.v1"
EXPECTED_SCOPE_GUARD = "eovrt.full_detector_ov_preserved.v1"

# `EFFECTIVE_PROFILE_KEYS` viene de T1, donde el optimizador era `auto` y no había nada que
# declarar. Acá hacen falta además los cuatro parámetros que SON la enmienda D-FT-16.
# Olvidarlos no es un detalle: el perfil quedaría sin ellos y el entrenamiento reventaría
# con KeyError al arrancar, sin llegar a aplicar el optimizador corregido — que es lo único
# que esta corrida existe para probar. (Pasó exactamente eso en la versión de continuación;
# se cazó en revisión crítica antes de que el job corriera.)
V2_PROFILE_KEYS = tuple(EFFECTIVE_PROFILE_KEYS) + ("optimizer", "lr0", "momentum", "patience")
# Todo lo que `main()` lee del perfil. Se valida en `resolve_profile`, así que un olvido
# falla en el PREFLIGHT (segundos, local) y no dos días después con la GPU asignada.
REQUIRED_PROFILE_KEYS = V2_PROFILE_KEYS + ("device", "fraction")


def load_config(path: Path) -> dict[str, object]:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ValueError(f"invalid config: {path}")
    if config.get("schema_version") != EXPECTED_SCHEMA:
        raise ValueError(f"config schema must be {EXPECTED_SCHEMA}")
    if config.get("experiment_id") != "t2_yoloe26s_full_v2":
        raise ValueError("config must declare experiment_id t2_yoloe26s_full_v2")
    classes = {int(k): v for k, v in (config.get("model") or {}).get("training_classes", {}).items()}
    if classes != EXPECTED_CLASSES:
        raise ValueError(f"training classes {classes!r} != frozen {EXPECTED_CLASSES!r}")
    trainer = config.get("trainer") or {}
    if trainer.get("scope_guard") != EXPECTED_SCOPE_GUARD:
        raise ValueError(f"must enforce the scope guard {EXPECTED_SCOPE_GUARD}")
    if trainer.get("implementation") != "ultralytics.models.yolo.yoloe.YOLOETrainer":
        raise ValueError("must use YOLOETrainer: YOLOEPETrainer fuses the text head")
    if trainer.get("optimizer") == "auto":
        raise ValueError(
            "esta corrida existe justamente para NO usar 'auto' "
            "(es ciego al conteo de parámetros entrenables)"
        )
    prefixes = trainer.get("frozen_prefixes")
    if not isinstance(prefixes, list) or not prefixes:
        raise ValueError("must declare the frozen prompt-path prefixes")
    for key in ("optimizer", "lr0", "momentum", "epochs", "patience"):
        if trainer.get(key) in (None, ""):
            raise ValueError(f"se requiere '{key}' explícito, sin defaults implícitos")
    for key in (
        "expected_trainable_tensors",
        "expected_trainable_parameters",
        "expected_frozen_tensors",
        "expected_frozen_parameters",
    ):
        if int(trainer.get(key, 0)) <= 0:
            raise ValueError(f"trainer must declare a positive {key}")
    for key in ("expected_trainable_names_sha256", "expected_frozen_names_sha256"):
        if not isinstance(trainer.get(key), str) or len(trainer[key]) != 64:
            raise ValueError(f"trainer must declare {key} as a sha256 hex digest")
    return config


def resolve_profile(config: dict[str, object]) -> dict[str, object]:
    trainer = dict(config["trainer"])
    resolved = {key: trainer[key] for key in V2_PROFILE_KEYS if key in trainer}
    resolved.setdefault("fraction", 1.0)
    resolved["device"] = trainer["device"]
    missing = [key for key in REQUIRED_PROFILE_KEYS if key not in resolved]
    if missing:
        raise ValueError(
            f"el perfil resuelto no trae {missing!r}: la corrida fallaría al arrancar. "
            "Declararlos en config.trainer o agregarlos a V2_PROFILE_KEYS."
        )
    return resolved


def validate_epochs(results_csv: Path, *, max_epochs: int, patience: int) -> dict[str, object]:
    """Valida el calendario de épocas ACEPTANDO early stopping.

    No se puede reusar `_validate_epoch_schedule` de T1: aquel exige épocas exactamente
    `[1..epochs]` porque T1 no usaba `patience`. Acá `patience` está puesto a propósito para
    que Ultralytics corte al converger — con esa validación, la parada temprana (el
    resultado ESPERADO) se reportaría como fallo de post-chequeo y el manifiesto con hashes
    nunca se escribiría.
    """
    epochs = _read_trainer_results_csv(results_csv).get("epoch", [])
    if not epochs:
        raise ValueError("results.csv no registró ninguna época")
    if epochs != list(range(1, len(epochs) + 1)):
        raise ValueError(f"calendario de épocas no contiguo desde 1: {epochs!r}")
    if len(epochs) > max_epochs:
        raise ValueError(f"corrieron {len(epochs)} épocas, más que el techo {max_epochs}")
    early_stopped = len(epochs) < max_epochs
    # Un corte antes de `patience + 1` es imposible por construcción: sería otra causa
    # (crash, señal, límite de tiempo) disfrazada de convergencia.
    if early_stopped and len(epochs) < patience + 1:
        raise ValueError(
            f"corte en la época {len(epochs)} con patience={patience}: demasiado temprano "
            "para ser early stopping; investigar la causa antes de usar el checkpoint"
        )
    return {
        "completed_epochs": epochs,
        "epochs_run": len(epochs),
        "max_epochs": max_epochs,
        "early_stopped": early_stopped,
        "hit_ceiling": not early_stopped,
    }


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
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
    profile = resolve_profile(config)
    versions = _runtime_versions()
    if versions["ultralytics"] != str(config["trainer"]["ultralytics"]):
        raise RuntimeError(
            f"ultralytics {versions['ultralytics']} != frozen {config['trainer']['ultralytics']}"
        )

    import torch
    from ultralytics import YOLOE
    from ultralytics.models.yolo.yoloe import YOLOETrainer

    if not args.allow_cpu and not torch.cuda.is_available():
        raise RuntimeError("requires CUDA; local runs are preflight only (D-100.1)")

    class EOVRTYOLOEV2Trainer(YOLOETrainer):
        def get_model(self, cfg=None, weights=None, verbose: bool = True):
            model = super().get_model(cfg=cfg, weights=weights, verbose=verbose)
            contract = apply_scope_guard(model, config["trainer"])
            validate_scope_contract(contract, config["trainer"], require_optimizer=False)
            return model

        def _build_train_pipeline(self) -> None:
            # Corre DESPUÉS del bloque de `_setup_train` que re-habilita requires_grad y
            # ANTES de construir el optimizador: único punto donde el alcance queda fijado.
            contract = apply_scope_guard(self.model, config["trainer"])
            validate_scope_contract(contract, config["trainer"], require_optimizer=False)
            self.eovrt_trainable_contract = contract
            prefixes = [str(p) for p in config["trainer"]["frozen_prefixes"]]
            self.freeze_layer_names = list(
                dict.fromkeys(list(getattr(self, "freeze_layer_names", [])) + prefixes)
            )
            super()._build_train_pipeline()

        def build_optimizer(self, model, *fn_args, **fn_kwargs):
            optimizer = super().build_optimizer(model, *fn_args, **fn_kwargs)
            # `BaseTrainer.build_optimizer` agrupa TODOS los parámetros sin mirar
            # requires_grad: hay que podarlo, no sólo verificarlo.
            allowed = {id(p) for p in model.parameters() if p.requires_grad}
            for group in optimizer.param_groups:
                group["params"] = [p for p in group["params"] if id(p) in allowed]
            optimized = {id(p) for group in optimizer.param_groups for p in group["params"]}
            if optimized != allowed:
                raise RuntimeError("optimizer parameters differ from the scope guard")
            self.eovrt_trainable_contract["optimizer_parameter_count"] = sum(
                p.numel() for group in optimizer.param_groups for p in group["params"]
            )
            return optimizer

        def read_results_csv(self) -> dict[str, list[object]]:
            return _read_trainer_results_csv(Path(self.csv))

    if args.check_only:
        print(json.dumps({
            "status": "preflight_ok",
            "versions": versions,
            "optimizer": {
                "name": profile["optimizer"],
                "lr0": profile["lr0"],
                "momentum": profile["momentum"],
                "epochs": profile["epochs"],
                "patience": profile["patience"],
            },
        }, sort_keys=True))
        return 0

    if args.check_scope:
        previous_cwd = Path.cwd()
        os.chdir(paths["text_encoder"].parent)
        try:
            wrapper = YOLOE(config["model"]["architecture"]).load(str(paths["base_weight"]))
            trainer = object.__new__(EOVRTYOLOEV2Trainer)
            trainer.data = {"channels": 3, "nc": 4, "names": EXPECTED_CLASSES}
            scoped = trainer.get_model(cfg=wrapper.model.yaml, weights=wrapper.model, verbose=False)
            contract = current_contract(scoped)
        finally:
            os.chdir(previous_cwd)
        validate_scope_contract(contract, config["trainer"], require_optimizer=False)
        print(json.dumps({"status": "scope_ok", "contract": contract}, sort_keys=True))
        return 0

    # D-100.1: el entrenamiento SÓLO corre en el clúster. Pedir "CUDA disponible" no alcanza
    # —cualquier laptop con GPU lo pasa—; el cerco real es exigir Slurm. Va acá abajo a
    # propósito: los preflight ya retornaron, así que lo único vedado es entrenar de verdad.
    if not os.environ.get("SLURM_JOB_ID") and os.environ.get(
        "EOVRT_ALLOW_NON_SLURM_TRAIN"
    ) != "1":
        raise RuntimeError(
            "T2 v2 training must run inside a Slurm job (D-100.1: nunca entrenar local). "
            "Preflight local: usar --check-only/--check-scope."
        )

    output = args.output.resolve()
    run_dir = output / args.run_name
    if run_dir.exists():
        raise FileExistsError(f"refusing to reuse run directory: {run_dir}")
    output.mkdir(parents=True, exist_ok=True)
    started_at = datetime.now(timezone.utc)
    launch = {
        "schema_version": "eovrt.t2-v2-run.v1",
        "amendment": "D-FT-16",
        "supersedes_run_id": str((config.get("supersedes") or {}).get("run_id", "")),
        "status": "running",
        "run_name": args.run_name,
        "started_at": started_at.isoformat(),
        "hostname": socket.gethostname(),
        "slurm": {
            key: os.environ.get(key)
            for key in (
                "SLURM_JOB_ID", "SLURM_JOB_NAME", "SLURM_JOB_NODELIST",
                "SLURM_JOB_PARTITION", "SLURM_CPUS_PER_TASK", "SLURM_GPUS_ON_NODE",
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
            trainer=EOVRTYOLOEV2Trainer,
            epochs=int(profile["epochs"]),
            patience=int(profile["patience"]),
            optimizer=str(profile["optimizer"]),
            lr0=float(profile["lr0"]),
            momentum=float(profile["momentum"]),
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
        launch.update({
            "status": "failed",
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "error_type": type(error).__name__,
            "error": str(error),
        })
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
        epoch_evidence = validate_epochs(
            results_csv,
            max_epochs=int(profile["epochs"]),
            patience=int(profile["patience"]),
        )
        contract = getattr(getattr(model, "trainer", None), "eovrt_trainable_contract", None)
        if not isinstance(contract, dict):
            raise RuntimeError("training completed without the scope contract")
        validate_scope_contract(dict(contract), config["trainer"], require_optimizer=True)
        probe = [str(name) for name in EXPECTED_CLASSES.values()] + ["dog", "traffic light"]
        ov_evidence = verify_open_vocabulary(best, probe)
        write_json(actual_run_dir / "open_vocabulary_check.json", ov_evidence)
        launch.update({
            "status": "succeeded",
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": (datetime.now(timezone.utc) - started_at).total_seconds(),
            "run_dir": str(actual_run_dir),
            "completed_epochs": epoch_evidence["completed_epochs"],
            # Convergió sola vs se quedó sin techo: es dato científico, no telemetría.
            # `hit_ceiling: true` significa que 60 épocas no agotaron la mejora y el
            # resultado hay que leerlo como "todavía subiendo", no como convergido.
            "epoch_evidence": epoch_evidence,
            "trainable_contract": dict(contract),
            "open_vocabulary_check": ov_evidence,
            "best_epoch": _best_epoch(results_csv),
            "artifacts": {
                path.name: {"sha256": sha256_file(path), "size_bytes": path.stat().st_size}
                for path in (best, last, results_csv)
            },
        })
        write_json(output / f"{args.run_name}.launch.json", launch)
        write_json(actual_run_dir / "eovrt_run_manifest.json", launch)
    except BaseException as error:
        launch.update({
            "status": "failed_postcheck",
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "error_type": type(error).__name__,
            "error": str(error),
        })
        write_json(output / f"{args.run_name}.launch.json", launch)
        raise
    print(f"T2_V2_OK run_dir={actual_run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
