from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.evidence_archive.model import EvidenceError
from tools.evidence_archive.workflow import check, sync


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inventario de runs de evidencia DBE/EBE"
    )
    parser.add_argument("command", nargs="?", choices=("sync",))
    parser.add_argument("--check", action="store_true", help="verificar sin escribir")
    parser.add_argument(
        "--archive-only",
        action="store_true",
        help="validar una copia sin comparar contra los runs originales",
    )
    parser.add_argument("--repo-root", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--manifest", type=Path, help="manifiesto alternativo")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.check and args.command:
        parser.error("sync y --check son mutuamente excluyentes")
    if args.archive_only and not args.check:
        parser.error("--archive-only requiere --check")
    if not args.check and args.command != "sync":
        parser.error("indique sync o --check")
    repo_root = (args.repo_root or Path(__file__).resolve().parents[1]).resolve()
    manifest = (args.manifest or repo_root / "results/evidence-runs.yaml").resolve()
    try:
        report = (
            check(repo_root, manifest, archive_only=args.archive_only)
            if args.check
            else sync(repo_root, manifest)
        )
    except EvidenceError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    for message in report.messages:
        print(message)
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
