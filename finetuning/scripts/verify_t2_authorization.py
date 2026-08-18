#!/usr/bin/env python3
"""Verifica la puerta del full T2 antes de permitir el RUN (T-FT-063).

Análogo a `verify_t1_full_authorization.py`, con la diferencia de que T2 no tiene un
contrato de vocabulario fijo que atar: lo que hay que atar acá es que **la vara existía
antes que el resultado**. Comprueba, por hash y sin excepciones:

  1. el protocolo T2 está en `frozen_pre_result` y sus guards previos son coherentes;
  2. todos los insumos congelados coinciden con su sha256 declarado;
  3. D-FT-15 figura firmada, y firmada antes de cualquier resultado tuned;
  4. la baseline de retención OV está congelada y su umbral derivado es correcto;
  5. el smoke técnico pasó.

Sale 0 sólo si todo eso se cumple. Cualquier fallo aborta el envío: es la diferencia
entre un experimento pre-registrado y un número buscado.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

PROTOCOL_SCHEMA = "eovrt.t2-protocol.v1"
REQUIRED_FALSE_GUARDS = ("tuned_checkpoint_observed", "tuned_evaluation_executed",
                         "bench_used_for_training_or_validation")
REQUIRED_TRUE_GUARDS = ("margins_signed", "ov_retention_baseline_frozen",
                        "technical_smoke_passed")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify(*, protocol_path: Path, finetuning_root: Path, experiment_root: Path) -> dict:
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    if protocol.get("schema_version") != PROTOCOL_SCHEMA:
        raise RuntimeError(f"protocolo inesperado: {protocol.get('schema_version')}")
    if protocol.get("status") != "frozen_pre_result":
        raise RuntimeError(f"el protocolo T2 no está congelado: {protocol.get('status')}")

    guards = protocol.get("pre_result_guards") or {}
    for key in REQUIRED_TRUE_GUARDS:
        if guards.get(key) is not True:
            raise RuntimeError(f"guard previo incumplido: {key} debe ser true")
    for key in REQUIRED_FALSE_GUARDS:
        if guards.get(key) is not False:
            raise RuntimeError(
                f"guard previo incumplido: {key} debe ser false — ya se observó el brazo tuned"
            )

    gate = protocol.get("go_no_go") or {}
    if gate.get("decision_id") != "D-FT-15":
        raise RuntimeError("el protocolo no referencia D-FT-15")
    if not gate.get("signed_by_user_at"):
        raise RuntimeError("D-FT-15 sin fecha de firma: no se corre sin márgenes firmados")
    if gate.get("signed_before_any_tuned_result") is not True:
        raise RuntimeError("D-FT-15 debe declararse firmada antes de todo resultado tuned")
    if not (gate.get("preregistered_expectation") or {}).get("overall"):
        raise RuntimeError("falta la expectativa pre-registrada")

    verified = {}
    for relative, expected in (protocol.get("frozen_inputs_sha256") or {}).items():
        # Los prompt sets viven en el repo del experimento, pero el bundle los lleva
        # adentro para que la puerta sea verificable en el clúster sin ese repo.
        candidate = finetuning_root / relative
        if not candidate.is_file() and relative.startswith("prompts/"):
            candidate = experiment_root / relative
        if not candidate.is_file():
            raise FileNotFoundError(f"insumo congelado ausente: {candidate}")
        actual = sha256_file(candidate)
        if actual != expected:
            raise RuntimeError(f"insumo alterado: {relative}\n  esperado {expected}\n  actual   {actual}")
        verified[relative] = actual

    retention = ((protocol.get("arms") or {}).get("open_vocabulary_retention") or {}).get(
        "baseline_frozen"
    ) or {}
    frozen_path = finetuning_root / str(retention.get("path", "")).replace("finetuning/", "", 1)
    if not frozen_path.is_file():
        raise FileNotFoundError(f"baseline de retención ausente: {frozen_path}")
    if sha256_file(frozen_path) != retention.get("sha256"):
        raise RuntimeError("la baseline de retención OV congelada fue alterada")
    frozen = json.loads(frozen_path.read_text(encoding="utf-8"))
    if frozen.get("status") != "frozen_before_t2_training":
        raise RuntimeError("la baseline de retención no declara haberse congelado antes de entrenar")
    baseline_map50 = float(frozen["headline_results"]["mAP50"])
    ov_gate = gate["retention_open_vocabulary_gate"]
    expected_threshold = round(baseline_map50 * (1 - float(ov_gate["max_relative_regression"])), 6)
    if abs(expected_threshold - float(ov_gate["no_go_threshold_map50"])) > 1e-6:
        raise RuntimeError(
            f"umbral de retención OV incoherente: {ov_gate['no_go_threshold_map50']} != {expected_threshold}"
        )

    smoke = (protocol.get("training") or {}).get("technical_smoke") or {}
    if smoke.get("state") != "COMPLETED":
        raise RuntimeError("el smoke técnico de T2 no figura COMPLETED")

    return {
        "status": "t2_authorization_ok",
        "protocol_id": protocol["protocol_id"],
        "decision": gate["decision_id"],
        "signed_at": gate["signed_by_user_at"],
        "frozen_inputs_verified": len(verified),
        "ov_retention_baseline_map50": baseline_map50,
        "ov_retention_no_go_threshold": expected_threshold,
        "technical_smoke_job": smoke.get("slurm_job_id"),
    }


def main(argv: list[str] | None = None) -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=root / "manifests" / "t2_yoloe26s_protocol.json")
    parser.add_argument("--finetuning-root", type=Path, default=root)
    parser.add_argument("--experiment-root", type=Path, default=root.parent)
    args = parser.parse_args(argv)
    result = verify(
        protocol_path=args.protocol.resolve(),
        finetuning_root=args.finetuning_root.resolve(),
        experiment_root=args.experiment_root.resolve(),
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
