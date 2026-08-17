#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path

from talert_campaign.aggregate import aggregate_attempt, write_candidate
from talert_campaign.config import CampaignConfig
from talert_campaign.corpus import load_corpus, stage_alerts, validate_alerts
from talert_campaign.integrated import run_camera_smoke, run_integrated_video
from talert_campaign.model import GateViolation
from talert_campaign.render import rebuild_curated_metrics, render_evidence
from talert_campaign.workflows import (
    invalidate_attempt,
    load_attempt,
    prepare_attempt,
    run_live_series,
    run_preflight_dbe,
)


def _inventory(config_path: Path, repo_root: Path) -> dict:
    config = CampaignConfig.load(config_path, repo_root)
    corpus = load_corpus(config)
    runs = Counter(run.series for run in corpus)
    events: Counter[str] = Counter()
    nonempty: Counter[str] = Counter()
    all_alert_ids: set[str] = set()
    with tempfile.TemporaryDirectory(prefix="eovrt-talert-inventory-") as temporary:
        staging = Path(temporary)
        for run in corpus:
            stats = validate_alerts(stage_alerts(run, staging))
            events[run.series] += stats.valid
            if stats.valid:
                nonempty[run.series] += 1
            duplicates = all_alert_ids.intersection(stats.alert_ids)
            if duplicates:
                raise GateViolation(
                    f"duplicate alert_id across runs: {min(duplicates)}"
                )
            all_alert_ids.update(stats.alert_ids)

    actual = {
        "primary_dbe": {
            "runs": runs["primary_dbe"],
            "nonempty_runs": nonempty["primary_dbe"],
            "events": events["primary_dbe"],
        },
        "primary_ebe": {
            "runs": runs["primary_ebe"],
            "nonempty_runs": nonempty["primary_ebe"],
            "events": events["primary_ebe"],
        },
        "supplemental": {
            "runs": runs["supplemental"],
            "nonempty_runs": nonempty["supplemental"],
            "events": events["supplemental"],
        },
    }
    primary = {
        key: actual["primary_dbe"][key] + actual["primary_ebe"][key]
        for key in ("runs", "nonempty_runs", "events")
    }
    total = {
        "copied_runs": primary["runs"] + actual["supplemental"]["runs"],
        "nonempty_runs": primary["nonempty_runs"] + actual["supplemental"]["nonempty_runs"],
        "events": primary["events"] + actual["supplemental"]["events"],
    }
    expected = config.corpus
    gates = {
        "primary": primary
        == {
            "runs": expected.primary.runs,
            "nonempty_runs": expected.primary.nonempty_runs,
            "events": expected.primary.events,
        },
        "supplemental": actual["supplemental"]
        == {
            "runs": expected.supplemental.runs,
            "nonempty_runs": expected.supplemental.nonempty_runs,
            "events": expected.supplemental.events,
        },
        "total": total
        == {
            "copied_runs": expected.expected.runs,
            "nonempty_runs": expected.expected.nonempty_runs,
            "events": expected.expected.events,
        },
        "unique_alert_ids": len(all_alert_ids) == total["events"],
    }
    if not all(gates.values()):
        failed = ", ".join(name for name, passed in gates.items() if not passed)
        raise GateViolation(f"inventory drift: {failed}")
    return {
        "schema_version": "talert_notification_corpus_inventory.v1",
        "series": actual,
        "primary": primary,
        "total": total,
        "unique_alert_ids": len(all_alert_ids),
        "gates": gates,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="t_alert_notification_campaign")
    subparsers = parser.add_subparsers(dest="command", required=True)
    inventory = subparsers.add_parser("inventory")
    inventory.add_argument(
        "--config", type=Path, default=Path("experiments/t_alert_notification/campaign.yaml")
    )
    inventory.add_argument("--repo-root", type=Path, default=Path.cwd())
    prepare = subparsers.add_parser("prepare")
    prepare.add_argument(
        "--config", type=Path, default=Path("experiments/t_alert_notification/campaign.yaml")
    )
    prepare.add_argument("--repo-root", type=Path, default=Path.cwd())
    prepare.add_argument("--attempt-id", required=True)
    preflight = subparsers.add_parser("preflight-dbe")
    preflight.add_argument(
        "--config", type=Path, default=Path("experiments/t_alert_notification/campaign.yaml")
    )
    preflight.add_argument("--repo-root", type=Path, default=Path.cwd())
    preflight.add_argument("--attempt-id", required=True)
    preflight.add_argument("--sample", action="append", default=[])
    live = subparsers.add_parser("run-live")
    live.add_argument(
        "--config", type=Path, default=Path("experiments/t_alert_notification/campaign.yaml")
    )
    live.add_argument("--repo-root", type=Path, default=Path.cwd())
    live.add_argument("--attempt-id", required=True)
    live.add_argument("--series", choices=("primary", "supplemental"), required=True)
    live.add_argument("--sample", action="append", default=[])
    invalidate = subparsers.add_parser("invalidate")
    invalidate.add_argument(
        "--config", type=Path, default=Path("experiments/t_alert_notification/campaign.yaml")
    )
    invalidate.add_argument("--repo-root", type=Path, default=Path.cwd())
    invalidate.add_argument("--attempt-id", required=True)
    invalidate.add_argument("--reason", required=True)
    verify = subparsers.add_parser("verify")
    verify.add_argument(
        "--config", type=Path, default=Path("experiments/t_alert_notification/campaign.yaml")
    )
    verify.add_argument("--repo-root", type=Path, default=Path.cwd())
    verify.add_argument("--attempt-id", required=True)
    verify.add_argument(
        "--allow-completed",
        action="store_true",
        help=(
            "re-agrega un intento ya publicado; sólo para regenerar el candidato "
            "cuando cambió el propio agregador (las fases de origen son inmutables)"
        ),
    )
    rebuild = subparsers.add_parser("rebuild-curated")
    rebuild.add_argument(
        "--config", type=Path, default=Path("experiments/t_alert_notification/campaign.yaml")
    )
    rebuild.add_argument("--repo-root", type=Path, default=Path.cwd())
    rebuild.add_argument("--attempt-id", required=True)
    integrated = subparsers.add_parser("run-integrated-video")
    integrated.add_argument(
        "--config", type=Path, default=Path("experiments/t_alert_notification/campaign.yaml")
    )
    integrated.add_argument("--repo-root", type=Path, default=Path.cwd())
    integrated.add_argument("--attempt-id", required=True)
    integrated.add_argument("--phase-id", default="integrated-video")
    camera = subparsers.add_parser("run-camera-smoke")
    camera.add_argument(
        "--config", type=Path, default=Path("experiments/t_alert_notification/campaign.yaml")
    )
    camera.add_argument("--repo-root", type=Path, default=Path.cwd())
    camera.add_argument("--attempt-id", required=True)
    camera.add_argument("--preset", type=Path, required=True)
    camera.add_argument("--phase-id", default="camera-smoke")
    render = subparsers.add_parser("render")
    render.add_argument(
        "--config", type=Path, default=Path("experiments/t_alert_notification/campaign.yaml")
    )
    render.add_argument("--repo-root", type=Path, default=Path.cwd())
    render.add_argument("--attempt-id", required=True)
    render.add_argument("--integrated-phase", default="integrated-video-02")
    render.add_argument(
        "--camera-status",
        choices=("hardware_source_not_connected",),
        required=True,
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "inventory":
            result = _inventory(args.config, args.repo_root)
        elif args.command == "prepare":
            config = CampaignConfig.load(args.config, args.repo_root)
            result = prepare_attempt(config, args.attempt_id)
        elif args.command == "preflight-dbe":
            config = CampaignConfig.load(args.config, args.repo_root)
            attempt = load_attempt(
                config.repo_root / "runs/t-alert-notification", args.attempt_id
            )
            result = run_preflight_dbe(config, attempt, sample=tuple(args.sample))
        elif args.command == "run-live":
            config = CampaignConfig.load(args.config, args.repo_root)
            attempt = load_attempt(
                config.repo_root / "runs/t-alert-notification", args.attempt_id
            )
            result = run_live_series(
                config,
                attempt,
                series=args.series,
                sample=tuple(args.sample),
            )
        elif args.command == "invalidate":
            config = CampaignConfig.load(args.config, args.repo_root)
            attempt = load_attempt(
                config.repo_root / "runs/t-alert-notification", args.attempt_id
            )
            result = invalidate_attempt(attempt, args.reason)
        elif args.command == "verify":
            config = CampaignConfig.load(args.config, args.repo_root)
            attempt = load_attempt(
                config.repo_root / "runs/t-alert-notification",
                args.attempt_id,
                allow_completed=args.allow_completed,
            )
            result, rows = aggregate_attempt(
                attempt, allow_completed=args.allow_completed
            )
            write_candidate(attempt, result, rows)
        elif args.command == "rebuild-curated":
            config = CampaignConfig.load(args.config, args.repo_root)
            attempt = load_attempt(
                config.repo_root / "runs/t-alert-notification",
                args.attempt_id,
                allow_completed=True,
            )
            result = rebuild_curated_metrics(
                attempt, config.repo_root / "results/realtime/t_alert_notification"
            )
        elif args.command == "run-integrated-video":
            config = CampaignConfig.load(args.config, args.repo_root)
            attempt = load_attempt(
                config.repo_root / "runs/t-alert-notification", args.attempt_id
            )
            result = run_integrated_video(config, attempt, phase_id=args.phase_id)
        elif args.command == "run-camera-smoke":
            config = CampaignConfig.load(args.config, args.repo_root)
            attempt = load_attempt(
                config.repo_root / "runs/t-alert-notification", args.attempt_id
            )
            result = run_camera_smoke(
                config,
                attempt,
                preset_path=args.preset,
                phase_id=args.phase_id,
            )
        elif args.command == "render":
            config = CampaignConfig.load(args.config, args.repo_root)
            attempt = load_attempt(
                config.repo_root / "runs/t-alert-notification", args.attempt_id
            )
            result = render_evidence(
                config,
                attempt,
                integrated_phase=args.integrated_phase,
                camera_status=args.camera_status,
            )
        else:  # pragma: no cover - argparse owns this branch
            raise GateViolation(f"unsupported command: {args.command}")
    except GateViolation as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
