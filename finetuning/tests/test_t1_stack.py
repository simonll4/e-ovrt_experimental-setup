from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

import pytest
from PIL import Image

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from audit_t1_full import audit_full  # noqa: E402
from materialize_t1_payload import materialize, verify_payload  # noqa: E402
from prepare_t1_full_authorization import create_authorization  # noqa: E402
from prepare_t1_smoke_gate import CRITICAL_FILES, create_gate  # noqa: E402
from train_t1 import (  # noqa: E402
    _freeze_fused_class_projection,
    _read_trainer_results_csv,
    _validate_epoch_schedule,
    expected_effective_profile,
    load_config,
    resolve_profile,
    validate_trainable_contract,
)
from verify_t1_bundle import verify_bundle  # noqa: E402
from verify_t1_full_authorization import verify_authorization  # noqa: E402
from verify_t1_smoke_gate import verify_gate  # noqa: E402


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _frozen_trainable_contract(*, optimizer: bool = True) -> dict[str, object]:
    config_path = Path(__file__).resolve().parents[1] / "configs" / "t1_yoloe26s_lp.yaml"
    trainer = load_config(config_path)["trainer"]
    contract = {
        "scope": "fused_class_projection_only",
        "tensor_count": trainer["expected_trainable_tensors"],
        "parameter_count": trainer["expected_trainable_parameters"],
        "names": trainer["expected_trainable_names"],
    }
    if optimizer:
        contract["optimizer_parameter_count"] = trainer["expected_trainable_parameters"]
    return contract


def _install_real_t1_config(bundle: Path) -> None:
    source = Path(__file__).resolve().parents[1] / "configs" / "t1_yoloe26s_lp.yaml"
    target = bundle / "configs" / "t1_yoloe26s_lp.yaml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(source.read_bytes())


def _synthetic_optimizer_evidence(
    checkpoint: Path, *, epoch: int, profile: dict[str, object]
) -> dict[str, object]:
    return {
        "checkpoint": checkpoint.name,
        "checkpoint_sha256": _sha(checkpoint),
        "size_bytes": checkpoint.stat().st_size,
        "epoch_zero_based": epoch,
        "optimizer_param_groups": 3,
        "optimizer_group_tensor_counts": [3, 3, 6],
        "optimizer_parameter_tensors": 12,
        "optimizer_state_tensors": 12,
        "state_indices_match_parameter_groups": True,
        "effective_profile": expected_effective_profile(profile),
    }


def _source_row(root: Path, *, split: str, name: str, class_id: int) -> dict[str, str]:
    image_relative = Path("datasets/raw/demo") / split / "images" / f"{name}.jpg"
    label_relative = (
        Path("datasets/processed/yolo/canonical_v2/demo/labels") / split / f"{name}.txt"
    )
    image = root / image_relative
    label = root / label_relative
    image.parent.mkdir(parents=True, exist_ok=True)
    label.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (16, 16), (class_id * 40, 10, 20)).save(image)
    label.write_text(f"{class_id} 0.5 0.5 0.5 0.5\n", encoding="utf-8")
    counts = [0, 0, 0, 0]
    counts[class_id] = 1
    return {
        "schema_version": "eovrt.finetuning-split.v1",
        "record_id": f"demo:{split}:{name}",
        "dataset_id": "demo",
        "source_url": "https://example.invalid/demo",
        "source_version": "1",
        "license_spdx": "CC-BY-4.0",
        "source_split": split,
        "image_path": image_relative.as_posix(),
        "label_path": label_relative.as_posix(),
        "label_sha256": _sha(label),
        "sha256": _sha(image),
        "source_key": f"demo:{name}",
        "lineage_id": f"demo:{name}",
        "component_id": f"grp-{name}",
        "ahash64": "0" * 16,
        "dhash64": "0" * 16,
        "included": "true",
        "final_split": split,
        "exclusion_reason": "",
        "instances_person": str(counts[0]),
        "instances_helmet": str(counts[1]),
        "instances_vest": str(counts[2]),
        "instances_bare_head": str(counts[3]),
    }


def test_materializes_portable_payload_and_detects_tampering(tmp_path: Path) -> None:
    datasets = tmp_path / "datasets-repo"
    rows = [
        _source_row(datasets, split="train", name="person", class_id=0),
        _source_row(datasets, split="val", name="bare", class_id=3),
    ]
    split = tmp_path / "split.csv"
    with split.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = tmp_path / "summary.json"
    summary.write_text(
        json.dumps(
            {
                "schema_version": "eovrt.finetuning-summary.v1",
                "split_manifest_sha256": _sha(split),
                "bench_v3_sha256": "a" * 64,
                "test_contract": "bench absent",
                "splits": {
                    "train": {
                        "images": 1,
                        "class_instances": {
                            "person": 1,
                            "helmet": 0,
                            "vest": 0,
                            "bare_head": 0,
                        },
                    },
                    "val": {
                        "images": 1,
                        "class_instances": {
                            "person": 0,
                            "helmet": 0,
                            "vest": 0,
                            "bare_head": 1,
                        },
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "payload"
    manifest = materialize(
        split_manifest=split,
        split_summary=summary,
        datasets_root=datasets,
        output=output,
    )
    assert manifest["images"] == {"train": 1, "val": 1}
    assert not any(path.is_symlink() for path in output.rglob("*"))
    verify_payload(output)
    copied = next((output / "images" / "train").rglob("*.jpg"))
    copied.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="payload hash mismatch"):
        verify_payload(output)


def test_frozen_config_resolves_smoke_without_changing_full_schedule() -> None:
    config_path = Path(__file__).resolve().parents[1] / "configs" / "t1_yoloe26s_lp.yaml"
    config = load_config(config_path)
    smoke = resolve_profile(config, "smoke")
    full = resolve_profile(config, "full")
    assert smoke["epochs"] == 1
    assert smoke["fraction"] == 0.05
    assert full["epochs"] == 10
    assert full["fraction"] == 1.0
    assert (
        config["trainer"]["checkpoint_policy"]
        == "best_metrics_mAP50-95_B_all_four_val_classes"
    )


def test_frozen_config_rejects_semantically_reordered_vocabulary(tmp_path: Path) -> None:
    source = Path(__file__).resolve().parents[1] / "configs" / "t1_yoloe26s_lp.yaml"
    text = source.read_text(encoding="utf-8")
    text = text.replace(
        "    0: person\n    1: helmet\n",
        "    1: helmet\n    0: person\n",
        1,
    )
    reordered = tmp_path / "reordered.yaml"
    reordered.write_text(text, encoding="utf-8")

    with pytest.raises(ValueError, match="ordered fixed vocabulary"):
        load_config(reordered)


def test_reads_trainer_results_without_polars(tmp_path: Path) -> None:
    results = tmp_path / "results.csv"
    results.write_text(
        "epoch,time,metrics/mAP50-95(B),note\n"
        "1,11.622,0.04706,ok\n"
        "2,12.5,0.052,\n",
        encoding="utf-8",
    )

    assert _read_trainer_results_csv(results) == {
        "epoch": [1, 2],
        "time": [11.622, 12.5],
        "metrics/mAP50-95(B)": [0.04706, 0.052],
        "note": ["ok", None],
    }
    assert _validate_epoch_schedule(results, 2) == [1, 2]
    with pytest.raises(ValueError, match="results epoch schedule"):
        _validate_epoch_schedule(results, 10)


class _FakeParameter:
    def __init__(self, size: int) -> None:
        self.size = size
        self.requires_grad = True

    def requires_grad_(self, enabled: bool) -> _FakeParameter:
        self.requires_grad = enabled
        return self

    def numel(self) -> int:
        return self.size


class _FakeProjection:
    def __init__(self, *parameters: _FakeParameter) -> None:
        self._parameters = parameters

    def parameters(self) -> tuple[_FakeParameter, ...]:
        return self._parameters


class _FakeHead:
    def __init__(self, projections: list[_FakeProjection]) -> None:
        self.cv3 = [[None, None, projection] for projection in projections]
        self.one2one_cv3 = None


class _FakeModel:
    def __init__(self) -> None:
        self.backbone = _FakeParameter(100)
        self.projections = [
            (_FakeParameter(4), _FakeParameter(1)),
            (_FakeParameter(8), _FakeParameter(1)),
            (_FakeParameter(16), _FakeParameter(1)),
        ]
        self.model = [_FakeHead([_FakeProjection(*pair) for pair in self.projections])]

    def named_parameters(self):
        yield "model.0.backbone.weight", self.backbone
        for index, pair in enumerate(self.projections):
            yield f"model.0.cv3.{index}.2.weight", pair[0]
            yield f"model.0.cv3.{index}.2.bias", pair[1]


def test_freezes_everything_except_fused_class_projection() -> None:
    model = _FakeModel()
    contract = _freeze_fused_class_projection(model)

    assert model.backbone.requires_grad is False
    assert all(parameter.requires_grad for pair in model.projections for parameter in pair)
    assert contract["scope"] == "fused_class_projection_only"
    assert contract["tensor_count"] == 6
    assert contract["parameter_count"] == 31


def test_rejects_any_trainable_contract_other_than_the_frozen_real_signature() -> None:
    config_path = Path(__file__).resolve().parents[1] / "configs" / "t1_yoloe26s_lp.yaml"
    trainer = load_config(config_path)["trainer"]
    exact = _frozen_trainable_contract()
    validate_trainable_contract(exact, trainer, require_optimizer=True)

    for key, value in (
        ("tensor_count", 6),
        ("parameter_count", 1548),
        ("optimizer_parameter_count", 1548),
        ("names", exact["names"][:-1]),
    ):
        altered = dict(exact)
        altered[key] = value
        with pytest.raises(RuntimeError, match="T1"):
            validate_trainable_contract(altered, trainer, require_optimizer=True)


def test_bundle_verifier_rejects_undeclared_files(tmp_path: Path) -> None:
    declared = tmp_path / "declared.txt"
    declared.write_text("ok\n", encoding="utf-8")
    (tmp_path / "bundle.sha256").write_text(
        f"{_sha(declared)}  declared.txt\n", encoding="utf-8"
    )
    assert verify_bundle(tmp_path) == 1
    (tmp_path / "extra.txt").write_text("extra\n", encoding="utf-8")
    with pytest.raises(ValueError, match="inventory mismatch"):
        verify_bundle(tmp_path)


def test_full_submit_is_cluster_bound_idempotent_and_exact_inventory_guarded() -> None:
    root = Path(__file__).resolve().parents[1]
    submit = (root / "scripts" / "submit_t1_full_mendieta.sh").read_text(encoding="utf-8")
    runner = (root / "slurm" / "run_t1_job.sh").read_text(encoding="utf-8")

    assert '-M "${CLUSTER}"' in submit
    assert 'SUBMISSION_RECEIPT="${ROOT}/full-submission.txt"' in submit
    assert 'SUBMISSION_LOCK="${ROOT}/.submit-t1-full.lock"' in submit
    assert "verify_t1_bundle.py /workspace" in submit
    assert 'FULL_AUTHORIZATION="${ROOT}/full-authorization.json"' in submit
    assert "verify_t1_full_authorization.py" in submit
    assert "technical-smoke-ready.txt" in submit
    assert "TEST_ONLY_T1_10_EPOCHS" in submit
    assert "verify_t1_bundle.py /workspace" in runner
    assert "verify_t1_full_authorization.py" in runner


def test_smoke_gate_binds_critical_files_and_container(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    critical_hashes = {}
    for index, relative in enumerate(CRITICAL_FILES):
        critical = bundle / relative
        critical.parent.mkdir(parents=True, exist_ok=True)
        critical.write_text(f"frozen-{index}\n", encoding="utf-8")
        critical_hashes[relative] = _sha(critical)
    _install_real_t1_config(bundle)
    critical_hashes["configs/t1_yoloe26s_lp.yaml"] = _sha(
        bundle / "configs" / "t1_yoloe26s_lp.yaml"
    )
    image = tmp_path / "runtime.sif"
    image.write_bytes(b"runtime")
    gate = tmp_path / "smoke-ready.json"
    gate.write_text(
        json.dumps(
            {
                "schema_version": "eovrt.t1-smoke-gate.v2",
                    "status": "technical_smoke_ready",
                "experiment_id": "t1_yoloe26s_lp",
                "full_epochs": 10,
                "container_image_sha256": _sha(image),
                "critical_files": critical_hashes,
                "smoke": {
                    "job_id": "123",
                    "run_manifest_sha256": "1" * 64,
                    "bundle_manifest_sha256": "2" * 64,
                    "checkpoint_smoke_sha256": "3" * 64,
                    "best_checkpoint_sha256": "4" * 64,
                    "last_checkpoint_sha256": "5" * 64,
                    "cuda_device": "Synthetic GPU",
                    "elapsed_seconds": 1.0,
                        "trainable_contract": _frozen_trainable_contract(),
                        "optimizer_evidence": {
                            "checkpoint": "epoch0.pt",
                            "checkpoint_sha256": "6" * 64,
                            "size_bytes": 100,
                            "epoch_zero_based": 0,
                            "optimizer_param_groups": 3,
                            "optimizer_group_tensor_counts": [3, 3, 6],
                            "optimizer_parameter_tensors": 12,
                            "optimizer_state_tensors": 12,
                            "state_indices_match_parameter_groups": True,
                            "effective_profile": expected_effective_profile(
                                resolve_profile(
                                    load_config(
                                        bundle / "configs" / "t1_yoloe26s_lp.yaml"
                                    ),
                                    "smoke",
                                )
                            ),
                        },
                },
            }
        ),
        encoding="utf-8",
    )
    assert verify_gate(bundle=bundle, image=image, gate_path=gate)["smoke"]["job_id"] == "123"
    critical = bundle / "scripts" / "train_t1.py"
    critical.write_text("changed\n", encoding="utf-8")
    with pytest.raises(ValueError, match="differs from smoke"):
        verify_gate(bundle=bundle, image=image, gate_path=gate)


def test_creates_gate_from_successful_cuda_smoke_and_archived_bundle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle = tmp_path / "bundle"
    critical_hashes = {}
    for index, relative in enumerate(CRITICAL_FILES):
        target = bundle / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(f"critical-{index}\n".encode())
        critical_hashes[relative] = _sha(target)
    _install_real_t1_config(bundle)
    critical_hashes["configs/t1_yoloe26s_lp.yaml"] = _sha(
        bundle / "configs" / "t1_yoloe26s_lp.yaml"
    )

    archived = tmp_path / "smoke.bundle.sha256"
    archived.write_text(
        "".join(f"{digest}  {relative}\n" for relative, digest in critical_hashes.items()),
        encoding="utf-8",
    )
    image = tmp_path / "runtime.sif"
    image.write_bytes(b"container-image")
    run_dir = tmp_path / "runs" / "smoke-321"
    run_dir.mkdir(parents=True)
    artifacts = {}
    for name in ("best.pt", "last.pt", "results.csv", "epoch0.pt"):
        artifact = run_dir / "weights" / name if name.endswith(".pt") else run_dir / name
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_bytes(f"artifact-{name}".encode())
        artifacts[name] = {"sha256": _sha(artifact), "size_bytes": artifact.stat().st_size}
    checkpoint_smoke = run_dir / "checkpoint_smoke.json"
    checkpoint_smoke.write_text('{"status":"passed"}\n', encoding="utf-8")
    profile = resolve_profile(
        load_config(bundle / "configs" / "t1_yoloe26s_lp.yaml"), "smoke"
    )
    optimizer_evidence = _synthetic_optimizer_evidence(
        run_dir / "weights" / "epoch0.pt", epoch=0, profile=profile
    )
    monkeypatch.setitem(
        create_gate.__globals__,
        "audit_optimizer_checkpoint",
        lambda *_args, **_kwargs: optimizer_evidence,
    )
    run_manifest = run_dir / "eovrt_run_manifest.json"
    run_manifest.write_text(
        json.dumps(
            {
                "schema_version": "eovrt.t1-run.v1",
                "status": "succeeded",
                "profile": "smoke",
                "run_name": "smoke-321",
                "bundle_manifest_sha256": _sha(archived),
                "config_sha256": critical_hashes["configs/t1_yoloe26s_lp.yaml"],
                "data_yaml_sha256": critical_hashes["data/finetuning_v1/data.yaml"],
                "data_manifest_sha256": critical_hashes[
                    "manifests/finetuning_v1.summary.json"
                ],
                "base_weight_sha256": critical_hashes["weights/base/yoloe-26s-seg.pt"],
                "text_encoder_sha256": critical_hashes["weights/base/mobileclip2_b.ts"],
                "container_image_sha256": _sha(image),
                "checkpoint_inference_smoke": {"status": "passed"},
                "versions": {
                    "cuda_available": True,
                    "cuda_device_count": 1,
                    "cuda_device": "Synthetic GPU",
                },
                "slurm": {"SLURM_JOB_ID": "321"},
                "trainer": profile,
                "completed_epochs": [1],
                "trainable_contract": _frozen_trainable_contract(),
                "optimizer_evidence": optimizer_evidence,
                "elapsed_seconds": 12.5,
                "artifacts": artifacts,
            }
        ),
        encoding="utf-8",
    )
    gate_path = tmp_path / "smoke-ready.json"
    gate = create_gate(
        bundle=bundle,
        image=image,
        run_manifest=run_manifest,
        smoke_bundle_hash_manifest=archived,
        output=gate_path,
    )
    assert gate["smoke"]["job_id"] == "321"
    assert len(gate["critical_files"]) == len(CRITICAL_FILES)
    assert verify_gate(bundle=bundle, image=image, gate_path=gate_path) == gate


def test_audits_exact_ten_epoch_full_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle = tmp_path / "bundle"
    config_source = Path(__file__).resolve().parents[1] / "configs" / "t1_yoloe26s_lp.yaml"
    config_path = bundle / "configs" / "t1_yoloe26s_lp.yaml"
    config_path.parent.mkdir(parents=True)
    config_path.write_bytes(config_source.read_bytes())
    inputs = {
        "data_yaml_sha256": bundle / "data" / "finetuning_v1" / "data.yaml",
        "data_manifest_sha256": bundle / "manifests" / "finetuning_v1.summary.json",
        "base_weight_sha256": bundle / "weights" / "base" / "yoloe-26s-seg.pt",
        "text_encoder_sha256": bundle / "weights" / "base" / "mobileclip2_b.ts",
    }
    for key, path in inputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(key.encode())
    (bundle / "bundle.sha256").write_text("synthetic bundle\n", encoding="utf-8")
    image = tmp_path / "runtime.sif"
    image.write_bytes(b"runtime")

    run_dir = tmp_path / "runs" / "full-999"
    weights = run_dir / "weights"
    weights.mkdir(parents=True)
    best = weights / "best.pt"
    last = weights / "last.pt"
    epoch9 = weights / "epoch9.pt"
    best.write_bytes(b"best")
    last.write_bytes(b"last")
    epoch9.write_bytes(b"optimizer")
    results = run_dir / "results.csv"
    results.write_text(
        "epoch,metrics/mAP50-95(B)\n"
        + "".join(f"{epoch},{epoch / 100:.2f}\n" for epoch in range(1, 11)),
        encoding="utf-8",
    )
    checkpoint_smoke = run_dir / "checkpoint_smoke.json"
    checkpoint_smoke.write_text(
        json.dumps(
            {
                "status": "passed",
                "checkpoint_sha256": _sha(best),
                "vocabulary": {str(key): value for key, value in enumerate(
                    ("person", "helmet", "vest", "bare head")
                )},
            }
        ),
        encoding="utf-8",
    )
    artifacts = {
        name: {"sha256": _sha(path), "size_bytes": path.stat().st_size}
        for name, path in {
            "best.pt": best,
            "last.pt": last,
            "results.csv": results,
            "epoch9.pt": epoch9,
        }.items()
    }
    profile = resolve_profile(load_config(config_path), "full")
    optimizer_evidence = _synthetic_optimizer_evidence(
        epoch9, epoch=9, profile=profile
    )
    monkeypatch.setitem(
        audit_full.__globals__,
        "audit_optimizer_checkpoint",
        lambda *_args, **_kwargs: optimizer_evidence,
    )
    launch = {
        "schema_version": "eovrt.t1-run.v1",
        "status": "succeeded",
        "profile": "full",
        "run_name": "full-999",
        "slurm": {"SLURM_JOB_ID": "999"},
        "trainer": profile,
        "completed_epochs": list(range(1, 11)),
        "versions": {"cuda_available": True, "cuda_device_count": 1, "cuda_device": "GPU"},
        "container_image_sha256": _sha(image),
        "bundle_manifest_sha256": _sha(bundle / "bundle.sha256"),
        "config_sha256": _sha(config_path),
        **{key: _sha(path) for key, path in inputs.items()},
        "trainable_contract": _frozen_trainable_contract(),
        "optimizer_evidence": optimizer_evidence,
        "best_epoch": {
            "epoch": 10,
            "metric": "metrics/mAP50-95(B)",
            "value": 0.1,
        },
        "artifacts": artifacts,
        "elapsed_seconds": 60.0,
    }
    manifest = run_dir / "eovrt_run_manifest.json"
    manifest.write_text(json.dumps(launch), encoding="utf-8")
    output = tmp_path / "full-ready-999.json"

    audit = audit_full(
        bundle=bundle,
        image=image,
        run_manifest=manifest,
        job_id="999",
        output=output,
    )

    assert audit["status"] == "full_t1_completed_and_audited"
    assert audit["completed_epochs"] == list(range(1, 11))
    assert json.loads(output.read_text(encoding="utf-8")) == audit


def test_full_authorization_requires_exact_decision_gates_bindings_and_evidence(
    tmp_path: Path,
) -> None:
    bundle_manifest = tmp_path / "bundle.sha256"
    bundle_manifest.write_text("bundle\n", encoding="utf-8")
    smoke_gate = tmp_path / "smoke-ready.json"
    smoke_gate.write_text("{}\n", encoding="utf-8")
    evidence = {}
    gates = {
        "T-FT-005": "fixed_vocabulary_decision_approved",
        "T-FT-023": "provenance_frozen",
        "T-FT-026": "dual_authorization_gate_implemented",
        "T-FT-030": "fixed_vocabulary_serving_passed",
        "T-FT-031": "checkpoint_evaluation_passed",
        "T-FT-032": "bench_v3_baseline_frozen",
        "T-FT-042R": "technical_smoke_passed",
    }
    for task_id in gates:
        path = tmp_path / "evidence" / f"{task_id}.json"
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps({"task": task_id}) + "\n", encoding="utf-8")
        evidence[task_id] = {
            "path": path.relative_to(tmp_path).as_posix(),
            "sha256": _sha(path),
        }
    authorization_path = tmp_path / "full-authorization.json"
    evidence_values = [f"{task_id}={record['path']}" for task_id, record in evidence.items()]
    with pytest.raises(ValueError, match="APPROVE_D_FT_08"):
        create_authorization(
            approval="",
            bundle_manifest=bundle_manifest,
            smoke_gate=smoke_gate,
            evidence_values=evidence_values,
            output=authorization_path,
        )
    authorization = create_authorization(
        approval="APPROVE_D_FT_08",
        bundle_manifest=bundle_manifest,
        smoke_gate=smoke_gate,
        evidence_values=evidence_values,
        output=authorization_path,
    )
    assert (
        verify_authorization(
            authorization_path=authorization_path,
            bundle_manifest=bundle_manifest,
            smoke_gate=smoke_gate,
        )
        == authorization
    )

    authorization["decision"]["status"] = "proposed"
    authorization_path.write_text(json.dumps(authorization), encoding="utf-8")
    with pytest.raises(ValueError, match="D-FT-08"):
        verify_authorization(
            authorization_path=authorization_path,
            bundle_manifest=bundle_manifest,
            smoke_gate=smoke_gate,
        )
