from __future__ import annotations

import gzip
from pathlib import Path

import pytest

from tools.evidence_archive.archive import (
    ArchivePolicy,
    archive_run,
    deterministic_gzip,
    inspect_source_file,
    redact_effective_config,
    validate_archive_tree,
)
from tools.evidence_archive.model import EvidenceError, Relation, ResolvedRun, RunKey


def _policy() -> ArchivePolicy:
    return ArchivePolicy(
        allowed_extensions=frozenset(
            {".json", ".jsonl", ".csv", ".yaml", ".yml", ".txt", ".log", ".md"}
        ),
        excluded_extensions=frozenset(
            {
                ".jpg",
                ".jpeg",
                ".png",
                ".webp",
                ".bmp",
                ".gif",
                ".tif",
                ".tiff",
                ".mp4",
                ".avi",
                ".mkv",
                ".mov",
                ".webm",
                ".m4v",
            }
        ),
        excluded_directories=frozenset(
            {"previews", "frames", "images", "annotated", "videos", "cameras"}
        ),
        max_archive_bytes=95 * 1024 * 1024,
    )


@pytest.mark.parametrize(
    ("relative", "name"),
    [
        (Path("previews/frame.txt"), "frame.txt"),
        (Path("nested/frame.jpg"), "frame.jpg"),
        (Path("nested/clip.mp4"), "clip.mp4"),
    ],
)
def test_media_is_excluded_by_directory_or_extension(
    tmp_path: Path, relative: Path, name: str
) -> None:
    source = tmp_path / relative
    source.parent.mkdir(parents=True)
    source.write_text(name, encoding="utf-8")

    assert inspect_source_file(source, relative, _policy()).action == "exclude"


def test_disguised_png_is_rejected_by_content(tmp_path: Path) -> None:
    source = tmp_path / "looks-safe.txt"
    source.write_bytes(b"\x89PNG\r\n\x1a\n" + b"payload")

    with pytest.raises(EvidenceError, match="contenido multimedia"):
        inspect_source_file(source, Path(source.name), _policy())


def test_effective_config_redacts_uri_userinfo_and_secret_keys() -> None:
    raw = (
        b"source:\n"
        b"  url: rtsp://alice:very-secret@camera/live\n"
        b"  password: another-secret\n"
        b"model:\n"
        b"  ref: gdino\n"
    )

    output, redacted = redact_effective_config(raw)

    assert redacted is True
    assert b"very-secret" not in output
    assert b"another-secret" not in output
    assert output.count(b"'[REDACTED]'") + output.count(b"[REDACTED]") >= 2
    assert b"gdino" in output


def test_non_config_secret_is_rejected_without_echoing_value(tmp_path: Path) -> None:
    source = tmp_path / "summary.json"
    source.write_text('{"api_key":"never-print-this"}\n', encoding="utf-8")

    with pytest.raises(EvidenceError) as raised:
        inspect_source_file(source, Path(source.name), _policy())

    assert "secreto" in str(raised.value)
    assert "never-print-this" not in str(raised.value)


def test_embedded_base64_image_is_rejected(tmp_path: Path) -> None:
    source = tmp_path / "summary.json"
    source.write_text(
        '{"preview":"data:image/png;base64,iVBORw0KGgoAAA"}\n', encoding="utf-8"
    )

    with pytest.raises(EvidenceError, match="imagen embebida"):
        inspect_source_file(source, Path(source.name), _policy())


def test_jsonl_gzip_is_reproducible() -> None:
    payload = b'{"x":1}\n'

    first = deterministic_gzip(payload)
    second = deterministic_gzip(payload)

    assert first == second
    assert gzip.decompress(first) == payload
    assert first[3] == 0


def test_archive_run_copies_text_redacts_config_and_skips_previews(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source/run_a"
    source.mkdir(parents=True)
    (source / "summary.json").write_text('{"status":"ok"}\n', encoding="utf-8")
    (source / "detections.jsonl").write_text('{"frame":1}\n', encoding="utf-8")
    (source / "effective_config.yaml").write_text(
        "source:\n  password: hidden\nmodel:\n  ref: gdino\n", encoding="utf-8"
    )
    previews = source / "previews"
    previews.mkdir()
    (previews / "frame.jpg").write_bytes(b"image")
    resolved = ResolvedRun(
        RunKey("media-plane", "run_a"),
        "copied",
        (Relation("dbe_video", "t1", "campaign_media", "provenance.json"),),
        source_dirs=(source,),
    )
    destination = tmp_path / "archive/artifacts"

    files = archive_run(resolved, destination, _policy())

    run_copy = destination / "media-plane/run_a"
    assert (run_copy / "summary.json").read_bytes() == b'{"status":"ok"}\n'
    assert (
        gzip.decompress((run_copy / "detections.jsonl.gz").read_bytes())
        == b'{"frame":1}\n'
    )
    redacted = (run_copy / "effective_config.redacted.yaml").read_text(encoding="utf-8")
    assert "hidden" not in redacted
    assert "gdino" in redacted
    assert not (run_copy / "previews").exists()
    assert len(files) == 3


def test_validate_archive_tree_rejects_a_media_file_even_if_gitignored(
    tmp_path: Path,
) -> None:
    root = tmp_path / "evidence-runs"
    root.mkdir()
    (root / ".gitignore").write_text("*.jpg\n", encoding="utf-8")
    (root / "leaked.jpg").write_bytes(b"image")

    with pytest.raises(EvidenceError, match="medio prohibido"):
        validate_archive_tree(root, _policy())
