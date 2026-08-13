from __future__ import annotations

import argparse
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from exportlib import (
    ExportError,
    canonical_json_bytes,
    exclusive_output_locks,
    freeze_file,
    pretty_json_bytes,
    recheck_frozen_files,
    sha256_bytes,
    write_deterministic_zip,
)


@dataclass(frozen=True)
class _SnapshotSource:
    relative_path: str
    frozen: object


def _enumerate_sources(
    root: Path,
    explicit_output: Path | None,
    *,
    excluded_paths: Iterable[Path] = (),
    excluded_roots: Iterable[Path] = (),
) -> list[tuple[str, Path]]:
    sources: list[tuple[str, Path]] = []
    seen: set[str] = set()
    excluded_path_keys = {os.path.normcase(str(path.resolve())) for path in excluded_paths}
    excluded_root_values = tuple(path.resolve() for path in excluded_roots)
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ExportError(f"snapshot refuses symlink or reparse point: {path.relative_to(root).as_posix()}")
        try:
            attributes = path.lstat().st_file_attributes
        except AttributeError:
            attributes = 0
        if attributes & 0x400:
            raise ExportError(f"snapshot refuses symlink or reparse point: {path.relative_to(root).as_posix()}")
        if not path.is_file():
            continue
        resolved = path.resolve(strict=True)
        if os.path.normcase(str(resolved)) in excluded_path_keys:
            continue
        if any(resolved == excluded or resolved.is_relative_to(excluded) for excluded in excluded_root_values):
            continue
        rel = path.relative_to(root).as_posix()
        if rel.split("/", 1)[0].casefold() == "checkpoints":
            continue
        if explicit_output is not None and resolved == explicit_output:
            continue
        key = rel.casefold()
        if key in seen:
            raise ExportError(f"snapshot source path collision: {rel}")
        seen.add(key)
        sources.append((rel, resolved))
    return sources


def _recheck_source_inventory(
    root: Path,
    explicit_output: Path | None,
    expected: Iterable[tuple[str, Path]],
    *,
    excluded_paths: Iterable[Path] = (),
    excluded_roots: Iterable[Path] = (),
) -> None:
    current = _enumerate_sources(
        root,
        explicit_output,
        excluded_paths=excluded_paths,
        excluded_roots=excluded_roots,
    )
    expected_pairs = [(name, str(path)) for name, path in expected]
    current_pairs = [(name, str(path)) for name, path in current]
    if current_pairs != expected_pairs:
        raise ExportError("campaign source inventory changed before snapshot completed")


def _publish_if_absent(staged: Path, destination: Path) -> None:
    """Atomically publish a same-volume staged file without replacing an occupant."""
    try:
        os.link(staged, destination)
    except FileExistsError as exc:
        staged_digest = sha256_bytes(staged.read_bytes())
        base_name = f".{destination.name}.{staged_digest[:16]}.ludis-unpublished"
        recovery: Path | None = None
        for sequence in range(1, 1001):
            candidate = destination.with_name(base_name if sequence == 1 else f"{base_name}.{sequence}")
            try:
                os.link(staged, candidate)
            except FileExistsError:
                try:
                    existing = candidate.read_bytes()
                except OSError:
                    continue
                if sha256_bytes(existing) == staged_digest and existing == staged.read_bytes():
                    recovery = candidate
                    break
                continue
            except OSError as recovery_error:
                conflict = ExportError(
                    f"immutable snapshot path became occupied; external file preserved, but no-replace snapshot recovery failed: {destination}"
                )
                if hasattr(conflict, "add_note"):
                    conflict.add_note(str(recovery_error))
                raise conflict from recovery_error
            else:
                recovery = candidate
                break
        if recovery is None:
            raise ExportError(
                f"immutable snapshot path became occupied; external file preserved, but no free recovery name was found: {destination}"
            ) from exc
        staged.unlink()
        raise ExportError(
            f"immutable snapshot path became occupied; external file preserved and completed snapshot retained at {recovery}"
        ) from exc
    except OSError as exc:
        raise ExportError(f"atomic no-replace snapshot publication failed: {destination}") from exc
    staged.unlink()

def build_snapshot(campaign: Path, output: Path | None = None) -> tuple[Path, str, str]:
    root = campaign.resolve(strict=True)
    if root.is_symlink():
        raise ExportError("campaign root may not be a symlink or reparse point")
    try:
        root_attributes = root.lstat().st_file_attributes
    except AttributeError:
        root_attributes = 0
    if root_attributes & 0x400:
        raise ExportError("campaign root may not be a symlink or reparse point")
    if not (root / "campaign-ledger.json").is_file():
        raise ExportError("campaign-ledger.json is missing")

    explicit_output = output.resolve() if output is not None else None
    source_inventory = _enumerate_sources(root, explicit_output)
    frozen_sources: list[_SnapshotSource] = []
    files: dict[str, bytes] = {}
    for relative_path, source in source_inventory:
        frozen = freeze_file(source, f"snapshot source {relative_path}")
        frozen_sources.append(_SnapshotSource(relative_path, frozen))
        files[relative_path] = frozen.data

    _recheck_source_inventory(root, explicit_output, source_inventory)
    recheck_frozen_files((item.frozen for item in frozen_sources), action="snapshot capture")

    entries = [
        {"path": name, "bytes": len(data), "sha256": sha256_bytes(data)}
        for name, data in sorted(files.items())
    ]
    content_digest = sha256_bytes(canonical_json_bytes(entries))
    manifest = {
        "format": "cd-ludis-snapshot/v2",
        "content_digest": content_digest,
        "files": entries,
        "recovery": "Extract into an empty directory, then run validate_ledger.py on campaign-ledger.json.",
    }
    files["snapshot-manifest.json"] = pretty_json_bytes(manifest)
    destination = explicit_output or (root / "checkpoints" / f"ludis-snapshot-{content_digest[:16]}.zip")
    destination = destination.resolve()
    with exclusive_output_locks((destination,)) as owned_locks:
        if destination.exists():
            raise ExportError(f"immutable snapshot path already exists: {destination}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".ludis-snapshot-", dir=str(destination.parent)) as temporary_name:
            temporary = Path(temporary_name).resolve()
            staged = temporary / destination.name
            archive_digest = write_deterministic_zip(staged, files)
            _recheck_source_inventory(
                root,
                explicit_output,
                source_inventory,
                excluded_paths=owned_locks,
                excluded_roots=(temporary,),
            )
            recheck_frozen_files((item.frozen for item in frozen_sources), action="snapshot publication")
            _publish_if_absent(staged, destination)
    return destination, archive_digest, content_digest


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a deterministic, hashed Ludis campaign snapshot.")
    parser.add_argument("campaign", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        output, archive_digest, content_digest = build_snapshot(args.campaign, args.output)
    except (ExportError, OSError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 2
    print(f"PASS: {output}")
    print(f"CONTENT SHA256: {content_digest.upper()}")
    print(f"ARCHIVE SHA256: {archive_digest.upper()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
