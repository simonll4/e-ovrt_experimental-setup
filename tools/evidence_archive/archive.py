from __future__ import annotations

import gzip
import hashlib
import io
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml

from .model import EvidenceError, ResolvedRun, RunKey

FileAction = Literal["copy", "compress", "redact", "exclude"]
SENSITIVE_KEYS = {
    "password",
    "passwd",
    "token",
    "secret",
    "api_key",
    "private_key",
    "credential",
    "auth",
}
URI_USERINFO = re.compile(
    r"[a-z][a-z0-9+.-]*://[^\s/@:]+(?::[^\s/@]*)?@", re.IGNORECASE
)
PRIVATE_KEY = re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----")
BASE64_IMAGE = re.compile(r"data:image/[a-z0-9.+-]+;base64,", re.IGNORECASE)


@dataclass(frozen=True)
class ArchivePolicy:
    allowed_extensions: frozenset[str]
    excluded_extensions: frozenset[str]
    excluded_directories: frozenset[str]
    max_archive_bytes: int

    @classmethod
    def from_manifest(cls, data: dict[str, object]) -> "ArchivePolicy":
        def string_set(key: str) -> frozenset[str]:
            raw = data.get(key)
            if not isinstance(raw, list) or any(
                not isinstance(item, str) for item in raw
            ):
                raise EvidenceError(
                    f"archive_policy.{key} debe ser una lista de strings"
                )
            return frozenset(item.lower() for item in raw)

        max_mib = data.get("max_archive_mib", 95)
        if not isinstance(max_mib, int) or max_mib <= 0:
            raise EvidenceError(
                "archive_policy.max_archive_mib debe ser un entero positivo"
            )
        return cls(
            allowed_extensions=string_set("allowed_extensions"),
            excluded_extensions=string_set("excluded_extensions"),
            excluded_directories=string_set("excluded_directories"),
            max_archive_bytes=max_mib * 1024 * 1024,
        )


@dataclass(frozen=True)
class FileDecision:
    action: FileAction
    redacted_bytes: bytes | None = None


@dataclass(frozen=True)
class ArchivedFile:
    run_key: RunKey
    source_path: Path
    source_sha256: str
    source_size: int
    archive_path: Path
    archive_sha256: str
    archive_size: int
    compression: Literal["none", "gzip"]
    redaction: bool


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _is_media_content(data: bytes) -> bool:
    return any(
        (
            data.startswith(b"\xff\xd8\xff"),
            data.startswith(b"\x89PNG\r\n\x1a\n"),
            data.startswith((b"GIF87a", b"GIF89a")),
            data.startswith(b"BM"),
            data.startswith((b"II*\x00", b"MM\x00*")),
            len(data) >= 12
            and data.startswith(b"RIFF")
            and data[8:12] in {b"WEBP", b"AVI "},
            len(data) >= 8 and data[4:8] == b"ftyp",
            data.startswith(b"\x1aE\xdf\xa3"),
        )
    )


def _sensitive_value(value: object) -> bool:
    return value not in (None, "", False, 0, [], {}, "[REDACTED]")


def _contains_sensitive_key(value: object) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).strip().lower().replace("-", "_")
            if normalized in SENSITIVE_KEYS and _sensitive_value(child):
                return True
            if _contains_sensitive_key(child):
                return True
    elif isinstance(value, list):
        return any(_contains_sensitive_key(child) for child in value)
    return False


def _parse_structured(text: str, extension: str, relative_path: Path) -> object | None:
    try:
        if extension == ".json":
            return json.loads(text)
        if extension == ".jsonl":
            return [json.loads(line) for line in text.splitlines() if line.strip()]
        if extension in {".yaml", ".yml"}:
            return yaml.safe_load(text)
    except (json.JSONDecodeError, yaml.YAMLError) as exc:
        raise EvidenceError(
            f"archivo estructurado inválido: {relative_path.as_posix()}"
        ) from exc
    return None


def _inspect_text_bytes(data: bytes, extension: str, relative_path: Path) -> str:
    if _is_media_content(data):
        raise EvidenceError(f"contenido multimedia oculto: {relative_path.as_posix()}")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise EvidenceError(
            f"contenido binario no admitido: {relative_path.as_posix()}"
        ) from exc
    if BASE64_IMAGE.search(text):
        raise EvidenceError(f"imagen embebida no admitida: {relative_path.as_posix()}")
    if PRIVATE_KEY.search(text) or URI_USERINFO.search(text):
        raise EvidenceError(f"secreto detectado en {relative_path.as_posix()}")
    structured = _parse_structured(text, extension, relative_path)
    if structured is not None and _contains_sensitive_key(structured):
        raise EvidenceError(f"secreto detectado en {relative_path.as_posix()}")
    return text


def _redact_value(value: object) -> tuple[object, bool]:
    changed = False
    if isinstance(value, dict):
        output: dict[object, object] = {}
        for key, child in value.items():
            normalized = str(key).strip().lower().replace("-", "_")
            if normalized in SENSITIVE_KEYS and _sensitive_value(child):
                output[key] = "[REDACTED]"
                changed = True
            else:
                output[key], child_changed = _redact_value(child)
                changed = changed or child_changed
        return output, changed
    if isinstance(value, list):
        output_list: list[object] = []
        for child in value:
            cleaned, child_changed = _redact_value(child)
            output_list.append(cleaned)
            changed = changed or child_changed
        return output_list, changed
    if isinstance(value, str) and (
        URI_USERINFO.search(value)
        or PRIVATE_KEY.search(value)
        or BASE64_IMAGE.search(value)
    ):
        return "[REDACTED]", True
    return value, False


def redact_effective_config(data: bytes) -> tuple[bytes, bool]:
    try:
        value = yaml.safe_load(data.decode("utf-8"))
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise EvidenceError("effective_config.yaml inválido") from exc
    cleaned, changed = _redact_value(value)
    rendered = yaml.safe_dump(
        cleaned,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
    ).encode("utf-8")
    return rendered, changed


def inspect_source_file(
    path: Path,
    relative_path: Path,
    policy: ArchivePolicy,
) -> FileDecision:
    components = {part.lower() for part in relative_path.parts[:-1]}
    extension = relative_path.suffix.lower()
    if (
        components & policy.excluded_directories
        or extension in policy.excluded_extensions
    ):
        return FileDecision("exclude")
    if extension not in policy.allowed_extensions:
        raise EvidenceError(f"extensión no admitida: {relative_path.as_posix()}")
    if path.is_symlink():
        raise EvidenceError(f"symlink no admitido: {relative_path.as_posix()}")
    data = path.read_bytes()
    if relative_path.name.lower() in {"effective_config.yaml", "effective_config.yml"}:
        if _is_media_content(data):
            raise EvidenceError(
                f"contenido multimedia oculto: {relative_path.as_posix()}"
            )
        redacted, changed = redact_effective_config(data)
        _inspect_text_bytes(redacted, extension, relative_path)
        return FileDecision(
            "redact" if changed else "copy", redacted if changed else None
        )
    _inspect_text_bytes(data, extension, relative_path)
    return FileDecision("compress" if extension == ".jsonl" else "copy")


def deterministic_gzip(data: bytes) -> bytes:
    buffer = io.BytesIO()
    with gzip.GzipFile(
        filename="",
        mode="wb",
        fileobj=buffer,
        compresslevel=9,
        mtime=0,
    ) as compressed:
        compressed.write(data)
    return buffer.getvalue()


def _archived_name(path: Path, decision: FileDecision) -> Path:
    if decision.action == "compress":
        return path.with_name(f"{path.name}.gz")
    if decision.action == "redact":
        return path.with_name(f"{path.stem}.redacted{path.suffix}")
    return path


def _archive_file(
    run_key: RunKey,
    source: Path,
    source_relative: Path,
    target_root: Path,
    archive_root: Path,
    policy: ArchivePolicy,
) -> ArchivedFile | None:
    decision = inspect_source_file(source, source_relative, policy)
    if decision.action == "exclude":
        return None
    source_bytes = source.read_bytes()
    if decision.action == "compress":
        archive_bytes = deterministic_gzip(source_bytes)
    elif decision.action == "redact":
        if decision.redacted_bytes is None:
            raise EvidenceError(f"redacción vacía para {source_relative.as_posix()}")
        archive_bytes = decision.redacted_bytes
    else:
        archive_bytes = source_bytes
    if len(archive_bytes) > policy.max_archive_bytes:
        raise EvidenceError(
            f"archivo versionado supera el límite: {source_relative.as_posix()}"
        )
    archived_relative = _archived_name(source_relative, decision)
    destination = target_root / archived_relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(archive_bytes)
    return ArchivedFile(
        run_key=run_key,
        source_path=source,
        source_sha256=_sha256(source_bytes),
        source_size=len(source_bytes),
        archive_path=destination.relative_to(archive_root),
        archive_sha256=_sha256(archive_bytes),
        archive_size=len(archive_bytes),
        compression="gzip" if decision.action == "compress" else "none",
        redaction=decision.action == "redact",
    )


def archive_run(
    run: ResolvedRun,
    destination: Path,
    policy: ArchivePolicy,
) -> list[ArchivedFile]:
    archive_root = destination.parent
    if run.status == "copied":
        if not run.source_dirs:
            raise EvidenceError(f"run copied sin fuente: {run.key.run_id}")
        source_root = run.source_dirs[0]
        target_root = destination / run.key.plane / run.key.run_id
        source_files = [
            path for path in sorted(source_root.rglob("*")) if path.is_file()
        ]
        pairs = [(path, path.relative_to(source_root)) for path in source_files]
    elif run.status == "archived_only":
        if not run.archived_substitutes:
            raise EvidenceError(f"run archived_only sin sustituto: {run.key.run_id}")
        evidence_id = f"{run.key.plane}--{run.key.run_id}"
        target_root = destination / "archived-only" / evidence_id
        pairs = [(path, Path(path.name)) for path in run.archived_substitutes]
    else:
        raise EvidenceError(
            f"no se puede archivar un run {run.status}: {run.key.run_id}"
        )

    archived: list[ArchivedFile] = []
    for source, relative in pairs:
        item = _archive_file(
            run.key,
            source,
            relative,
            target_root,
            archive_root,
            policy,
        )
        if item is not None:
            archived.append(item)
    if not archived:
        raise EvidenceError(
            f"run sin artefactos textuales archivables: {run.key.run_id}"
        )
    return archived


def validate_archive_tree(root: Path, policy: ArchivePolicy) -> None:
    generated_names = {".gitignore", "files.sha256"}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise EvidenceError(
                f"symlink no admitido en archivo: {path.relative_to(root)}"
            )
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        components = {part.lower() for part in relative.parts[:-1]}
        extension = relative.suffix.lower()
        if (
            components & policy.excluded_directories
            or extension in policy.excluded_extensions
        ):
            raise EvidenceError(f"medio prohibido en archivo: {relative.as_posix()}")
        if relative.name.endswith(".jsonl.gz"):
            try:
                data = gzip.decompress(path.read_bytes())
            except (OSError, EOFError) as exc:
                raise EvidenceError(f"gzip inválido: {relative.as_posix()}") from exc
            pseudo = relative.with_suffix("")
            _inspect_text_bytes(data, ".jsonl", pseudo)
            continue
        if (
            extension not in policy.allowed_extensions
            and relative.name not in generated_names
        ):
            raise EvidenceError(
                f"archivo no admitido en archivo: {relative.as_posix()}"
            )
        _inspect_text_bytes(path.read_bytes(), extension, relative)
