from __future__ import annotations

import base64
import csv
import hashlib
import html
import io
import json
import os
import re
import stat
import tempfile
import zipfile
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping

from ledgerlib import LEDGER_FORMAT_V2, detect_format, validate as validate_ledger


PACK_FORMAT = "cd-ludis-pack/v1"
FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)
EXPORTABLE_STATUSES = {"proposed", "active_canon", "disputed", "superseded"}
PLAYER_VISIBILITY = "player_safe"


class ExportError(ValueError):
    """A user-correctable campaign export failure."""


@contextmanager
def exclusive_output_lock(anchor: Path):
    """Serialize Ludis commits for one output path without overwriting another run."""
    resolved = anchor.resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    lock_path = resolved.with_name("." + resolved.name + ".ludis-lock")
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    descriptor: int | None = None
    identity: tuple[int, int] | None = None
    created = False
    operation_error: BaseException | None = None
    try:
        try:
            descriptor = os.open(lock_path, flags, 0o600)
        except FileExistsError as exc:
            raise ExportError(
                "another Ludis operation is using this output path (or a stale lock remains): {}".format(lock_path)
            ) from exc
        created = True
        descriptor_state = os.fstat(descriptor)
        identity = (descriptor_state.st_dev, descriptor_state.st_ino)
        path_state = lock_path.lstat()
        if (path_state.st_dev, path_state.st_ino) != identity:
            raise ExportError(f"output lock identity changed during setup: {lock_path}")
        payload = ("pid={}\noutput={}\n".format(os.getpid(), resolved)).encode("utf-8")
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise OSError(f"failed to write output lock metadata: {lock_path}")
            offset += written
        yield lock_path
    except BaseException as exc:
        operation_error = exc
        raise
    finally:
        cleanup_error: BaseException | None = None
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError as exc:
                cleanup_error = exc
        if created:
            try:
                current = lock_path.lstat()
                current_identity = (current.st_dev, current.st_ino)
                if identity is None:
                    cleanup_error = cleanup_error or ExportError(
                        f"cannot safely remove output lock without descriptor identity: {lock_path}"
                    )
                elif current_identity == identity:
                    lock_path.unlink()
                else:
                    cleanup_error = cleanup_error or ExportError(
                        f"output lock identity changed before cleanup; replacement preserved: {lock_path}"
                    )
            except FileNotFoundError:
                pass
            except OSError as exc:
                if cleanup_error is None:
                    cleanup_error = exc
        if cleanup_error is not None:
            message = f"output lock cleanup failed: {cleanup_error}"
            if operation_error is not None:
                if hasattr(operation_error, "add_note"):
                    operation_error.add_note(message)
            else:
                raise ExportError(
                    f"operation may have completed, but {message}; inspect outputs before retrying"
                ) from cleanup_error


@contextmanager
def exclusive_output_locks(anchors: Iterable[Path]):
    """Reserve every path an operation may publish, releasing partial setup on failure."""
    unique: dict[str, Path] = {}
    for anchor in anchors:
        resolved = anchor.resolve()
        unique.setdefault(os.path.normcase(str(resolved)), resolved)
    ordered = [unique[key] for key in sorted(unique)]
    with ExitStack() as stack:
        locks = tuple(stack.enter_context(exclusive_output_lock(anchor)) for anchor in ordered)
        yield locks


def publish_file_if_absent(staged: Path, destination: Path, label: str) -> None:
    """Atomically publish staged bytes without replacing an existing path."""
    try:
        os.link(staged, destination)
    except FileExistsError as exc:
        raise ExportError(f"immutable {label} path became occupied: {destination}") from exc
    except OSError as exc:
        raise ExportError(
            f"could not publish immutable {label} without replacement: {destination}: {exc}"
        ) from exc
    staged.unlink()


@dataclass(frozen=True)
class CapturedCampaign:
    root: Path
    ledger_path: Path
    ledger: dict[str, Any]
    source_digest: str
    assets: dict[str, Path]
    capture_manifest: dict[str, Any]


@dataclass(frozen=True)
class _CapturedSourceEvidence:
    relative_path: str
    source: Path
    signature: tuple[int, int, int, int]
    sha256: str

@dataclass(frozen=True)
class FrozenFile:
    """One exact input generation retained for an approval transaction."""

    path: Path
    label: str
    data: bytes
    signature: tuple[int, int, int, int]
    sha256: str


@dataclass(frozen=True)
class BuildResult:
    artifact: Path
    artifact_sha256: str
    audit: Path
    preview: Path
    audience: str
    finalized: bool


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def pretty_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_archive_member_names(names: Iterable[str]) -> None:
    """Reject archive member names whose raw spelling is unsafe or ambiguous."""
    seen: dict[str, str] = {}
    for name in names:
        if not isinstance(name, str) or not name:
            raise ExportError("archive member path must be a non-empty string")
        if "\\" in name or ":" in name or name.endswith("/"):
            raise ExportError(f"unsafe archive member path: {name!r}")
        raw_parts = name.split("/")
        if any(part in {"", ".", ".."} for part in raw_parts):
            raise ExportError(f"unsafe archive member path: {name!r}")
        path = PurePosixPath(name)
        canonical = path.as_posix()
        if path.is_absolute() or canonical != name:
            raise ExportError(f"non-canonical archive member path: {name!r}")
        key = canonical.casefold()
        previous = seen.get(key)
        if previous is not None:
            raise ExportError(
                f"normalized or case-insensitive archive member collision: {previous!r} and {name!r}"
            )
        seen[key] = name


def _is_reparse(path: Path) -> bool:
    try:
        attributes = path.lstat().st_file_attributes
    except AttributeError:
        return path.is_symlink()
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def _safe_source(root: Path, value: str) -> tuple[PurePosixPath, Path]:
    if not isinstance(value, str) or not value.strip():
        raise ExportError("asset path must be a non-empty string")
    if "\\" in value:
        raise ExportError(f"asset path must use forward slashes: {value}")
    rel = PurePosixPath(value)
    if rel.is_absolute() or any(part in {"", ".", ".."} for part in rel.parts):
        raise ExportError(f"unsafe asset path: {value}")
    current = root
    for part in rel.parts:
        current = current / part
        if current.exists() and (current.is_symlink() or _is_reparse(current)):
            raise ExportError(f"asset path crosses a symlink or reparse point: {value}")
    if not current.is_file():
        raise ExportError(f"asset file missing: {value}")
    resolved_root = root.resolve(strict=True)
    resolved = current.resolve(strict=True)
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise ExportError(f"asset escapes campaign root: {value}") from exc
    return rel, current


def _source_signature(path: Path) -> tuple[int, int, int, int]:
    state = path.stat()
    return (state.st_dev, state.st_ino, state.st_size, state.st_mtime_ns)


def freeze_file(path: Path, label: str) -> FrozenFile:
    """Capture bytes and identity from one regular, non-linked input file."""
    source = Path(path)
    try:
        if not source.is_file() or source.is_symlink() or _is_reparse(source):
            raise ExportError(f"{label} must be a regular, non-linked file: {source}")
        resolved = source.resolve(strict=True)
        signature_before = _source_signature(resolved)
        data = resolved.read_bytes()
        signature_after = _source_signature(resolved)
    except OSError as exc:
        raise ExportError(f"could not capture {label}: {source}") from exc
    if signature_before != signature_after or len(data) != signature_after[2]:
        raise ExportError(f"{label} changed while approval inputs were captured")
    return FrozenFile(resolved, label, data, signature_after, sha256_bytes(data))


def recheck_frozen_files(files: Iterable[FrozenFile], action: str = "approval") -> None:
    """Fail if any named input no longer matches the generation retained above."""
    for frozen in files:
        try:
            path = frozen.path
            if not path.is_file() or path.is_symlink() or _is_reparse(path):
                raise ExportError(f"{frozen.label} changed type")
            signature_before = _source_signature(path)
            data = path.read_bytes()
            signature_after = _source_signature(path)
        except (OSError, ExportError) as exc:
            raise ExportError(f"{frozen.label} changed before {action} completed") from exc
        if (
            signature_before != frozen.signature
            or signature_after != frozen.signature
            or len(data) != frozen.signature[2]
            or sha256_bytes(data) != frozen.sha256
        ):
            raise ExportError(f"{frozen.label} changed before {action} completed")


def _capture_one(
    source: Path,
    destination: Path,
    relative_path: str,
) -> tuple[dict[str, Any], _CapturedSourceEvidence]:
    signature_before = _source_signature(source)
    data = source.read_bytes()
    signature_after = _source_signature(source)
    if signature_before != signature_after or len(data) != signature_after[2]:
        raise ExportError(f"source changed while it was being captured: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    if destination.read_bytes() != data:
        raise ExportError(f"captured copy failed verification: {source}")
    digest = sha256_bytes(data)
    entry = {"bytes": len(data), "sha256": digest}
    evidence = _CapturedSourceEvidence(relative_path, source, signature_after, digest)
    return entry, evidence


def _recheck_captured_source_set(
    source_root: Path,
    evidence: Iterable[_CapturedSourceEvidence],
) -> None:
    """Verify every declared source still matches when capture is complete."""
    for captured in evidence:
        try:
            if captured.relative_path == "campaign-ledger.json":
                current = source_root / captured.relative_path
                if not current.is_file() or current.is_symlink() or _is_reparse(current):
                    raise ExportError("campaign-ledger.json changed type during capture")
            else:
                _, current = _safe_source(source_root, captured.relative_path)
            signature_before = _source_signature(current)
            data = current.read_bytes()
            signature_after = _source_signature(current)
        except (OSError, ExportError) as exc:
            raise ExportError(
                f"source changed before capture completed: {captured.relative_path}"
            ) from exc
        if (
            current != captured.source
            or signature_before != captured.signature
            or signature_after != captured.signature
            or len(data) != captured.signature[2]
            or sha256_bytes(data) != captured.sha256
        ):
            raise ExportError(f"source changed before capture completed: {captured.relative_path}")


def capture_campaign(campaign_root: Path, capture_root: Path) -> CapturedCampaign:
    source_root = campaign_root.resolve(strict=True)
    if source_root.is_symlink() or _is_reparse(source_root):
        raise ExportError("campaign root may not be a symlink or reparse point")
    ledger_source = source_root / "campaign-ledger.json"
    if not ledger_source.is_file():
        raise ExportError("campaign-ledger.json is missing")
    if ledger_source.is_symlink() or _is_reparse(ledger_source):
        raise ExportError("campaign-ledger.json may not be a symlink or reparse point")

    frozen_root = capture_root / "source"
    ledger_destination = frozen_root / "campaign-ledger.json"
    ledger_entry, ledger_evidence = _capture_one(
        ledger_source,
        ledger_destination,
        "campaign-ledger.json",
    )
    try:
        ledger = json.loads(ledger_destination.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ExportError(f"campaign ledger is not valid UTF-8 JSON: {exc}") from exc
    if not isinstance(ledger, dict):
        raise ExportError("campaign ledger root must be an object")
    ledger_format = detect_format(ledger)
    if ledger_format != LEDGER_FORMAT_V2:
        if ledger_format == "legacy_v0_1":
            raise ExportError("campaign export requires ledger v2; run migrate_ledger.py first")
        raise ExportError("campaign ledger format is not recognized")
    ledger_errors = validate_ledger(ledger)
    if ledger_errors:
        raise ExportError("campaign ledger is invalid: " + "; ".join(ledger_errors))

    captured_assets: dict[str, Path] = {}
    source_evidence = [ledger_evidence]
    files = [{"path": "campaign-ledger.json", **ledger_entry}]
    seen_paths: set[str] = set()
    for index, asset in enumerate(ledger.get("assets", [])):
        if not isinstance(asset, dict):
            raise ExportError(f"assets[{index}] must be an object")
        asset_id = asset.get("id")
        path_value = asset.get("path")
        if not isinstance(asset_id, str) or not asset_id:
            raise ExportError(f"assets[{index}].id is required")
        if asset_id in captured_assets:
            raise ExportError(f"duplicate asset id: {asset_id}")
        rel, source = _safe_source(source_root, path_value)
        rel_text = rel.as_posix()
        if rel_text.casefold() in seen_paths:
            raise ExportError(f"asset path collision: {rel_text}")
        seen_paths.add(rel_text.casefold())
        destination = frozen_root.joinpath(*rel.parts)
        entry, captured_evidence = _capture_one(source, destination, rel_text)
        declared_digest = asset.get("sha256")
        if declared_digest is not None and declared_digest != entry["sha256"]:
            raise ExportError(f"asset digest does not match ledger declaration: {asset_id}")
        captured_assets[asset_id] = destination
        source_evidence.append(captured_evidence)
        files.append({"path": rel_text, **entry})

    _recheck_captured_source_set(source_root, source_evidence)
    files.sort(key=lambda item: item["path"])
    manifest = {
        "format": "cd-ludis-capture/v1",
        "files": files,
        "source_digest": sha256_bytes(canonical_json_bytes(files)),
    }
    manifest_path = capture_root / "capture-manifest.json"
    manifest_path.write_bytes(pretty_json_bytes(manifest))
    return CapturedCampaign(
        root=frozen_root,
        ledger_path=ledger_destination,
        ledger=ledger,
        source_digest=manifest["source_digest"],
        assets=captured_assets,
        capture_manifest=manifest,
    )


def _object_links(obj: Mapping[str, Any]) -> list[str]:
    links: list[str] = []
    for value in obj.get("links", []):
        if isinstance(value, str):
            links.append(value)
        elif isinstance(value, dict) and isinstance(value.get("target_id"), str):
            links.append(value["target_id"])
    return links


def _object_asset_ids(obj: Mapping[str, Any]) -> list[str]:
    values = obj.get("asset_ids", [])
    if not isinstance(values, list):
        return []
    return [value for value in values if isinstance(value, str)]


def project_ledger(ledger: dict[str, Any], audience: str, object_ids: Iterable[str] | None = None) -> dict[str, Any]:
    if audience not in {"gm", "player"}:
        raise ExportError("audience must be gm or player")
    objects = ledger.get("objects", [])
    assets = ledger.get("assets", [])
    if not isinstance(objects, list) or not isinstance(assets, list):
        raise ExportError("ledger objects and assets must be arrays")
    by_id = {obj.get("id"): obj for obj in objects if isinstance(obj, dict) and isinstance(obj.get("id"), str)}
    if len(by_id) != len([obj for obj in objects if isinstance(obj, dict)]):
        raise ExportError("objects must have unique string ids")
    requested = set(object_ids or [])
    missing = sorted(requested - set(by_id))
    if missing:
        raise ExportError("unknown requested object id(s): " + ", ".join(missing))

    selected: list[dict[str, Any]] = []
    for obj in objects:
        if not isinstance(obj, dict):
            raise ExportError("every ledger object must be an object")
        if requested and obj.get("id") not in requested:
            continue
        if obj.get("status", "active_canon") not in EXPORTABLE_STATUSES:
            continue
        if obj.get("export_eligibility") != "eligible":
            continue
        if audience == "player" and obj.get("visibility") != PLAYER_VISIBILITY:
            continue
        if audience == "player":
            public_fields = {"id", "kind", "title", "name", "content", "text", "data", "links", "asset_ids", "tags"}
            selected.append({key: value for key, value in obj.items() if key in public_fields})
        else:
            selected.append(obj)

    selected_ids = {obj["id"] for obj in selected}
    for obj in selected:
        for target in _object_links(obj):
            linked = by_id.get(target)
            if linked is None:
                raise ExportError(f"broken object link in export: {obj['id']} -> {target}")
            if audience == "player" and linked.get("visibility") != PLAYER_VISIBILITY:
                raise ExportError(f"player export would reveal a GM-only link: {obj['id']} -> {target}")
            if target not in selected_ids:
                raise ExportError(f"selected export omits linked object: {obj['id']} -> {target}")

    asset_by_id = {asset.get("id"): asset for asset in assets if isinstance(asset, dict) and isinstance(asset.get("id"), str)}
    selected_asset_ids: set[str] = set()
    for obj in selected:
        for asset_id in _object_asset_ids(obj):
            asset = asset_by_id.get(asset_id)
            if asset is None:
                raise ExportError(f"object {obj['id']} references missing asset {asset_id}")
            if audience == "player" and asset.get("visibility") != PLAYER_VISIBILITY:
                raise ExportError(f"player export would reveal GM-only asset {asset_id}")
            selected_asset_ids.add(asset_id)
    selected_assets = [asset for asset in assets if isinstance(asset, dict) and asset.get("id") in selected_asset_ids]
    return {
        "audience": audience,
        "campaign": ledger.get("campaign", {}),
        "table_contract": ledger.get("table_contract", {}),
        "objects": selected,
        "assets": selected_assets,
    }


def _slug(value: str, fallback: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", value).strip("-._").lower()
    return (slug or fallback)[:80]


def _reserve_asset_path(output_name: str, used: set[str]) -> str:
    """Return a deterministic, case-insensitively unique asset member path."""
    candidate = f"assets/{output_name}"
    if candidate.casefold() not in used:
        used.add(candidate.casefold())
        return candidate
    suffix = PurePosixPath(output_name).suffix
    stem = output_name[:-len(suffix)] if suffix else output_name
    sequence = 2
    while True:
        candidate = f"assets/{stem}-{sequence}{suffix}"
        if candidate.casefold() not in used:
            used.add(candidate.casefold())
            return candidate
        sequence += 1


def _object_markdown(obj: Mapping[str, Any]) -> str:
    title = str(obj.get("title") or obj.get("name") or obj.get("id") or "Untitled")
    kind = str(obj.get("kind") or "campaign object")
    content = obj.get("content")
    if not isinstance(content, str):
        content = obj.get("text")
    if not isinstance(content, str):
        data = obj.get("data")
        content = "```json\n" + json.dumps(data if data is not None else {}, ensure_ascii=False, sort_keys=True, indent=2) + "\n```"
    return f"# {title}\n\nType: {kind}\n\n{content.rstrip()}\n"


def _write_csv(rows: list[dict[str, Any]], columns: list[str]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({column: row.get(column, "") for column in columns})
    return stream.getvalue().encode("utf-8")


def _validate_uvtt(data: bytes, asset_id: str) -> None:
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ExportError(f"UVTT asset {asset_id} is not valid UTF-8 JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ExportError(f"UVTT asset {asset_id} must contain a JSON object")
    required = {"format", "resolution", "line_of_sight", "portals", "lights"}
    missing = sorted(required - set(value))
    if missing:
        raise ExportError(f"UVTT asset {asset_id} is missing: {', '.join(missing)}")
    resolution = value.get("resolution")
    if not isinstance(resolution, dict) or not all(key in resolution for key in ("map_size", "pixels_per_grid")):
        raise ExportError(f"UVTT asset {asset_id} has invalid resolution metadata")


def render_generic_pack(captured: CapturedCampaign, projection: dict[str, Any], audience: str) -> dict[str, bytes]:
    campaign = projection.get("campaign", {})
    title = str(campaign.get("title") or "Untitled campaign") if isinstance(campaign, dict) else "Untitled campaign"
    objects = projection["objects"]
    assets = projection["assets"]
    files: dict[str, bytes] = {}

    files["README.md"] = (
        f"# {title}: {audience.title()} Tonight Pack\n\n"
        "This is a derived, offline play packet. The campaign ledger remains canonical.\n\n"
        "Start with `handouts/index.md`; structured data lives under `data/`; supplied media lives under `assets/`.\n"
    ).encode("utf-8")

    handout_lines = [f"# {title}", "", f"Audience: {audience}", "", "## Contents", ""]
    used_names: set[str] = set()
    object_rows: list[dict[str, Any]] = []
    table_rows: list[dict[str, Any]] = []
    scenes: list[dict[str, Any]] = []
    tokens: list[dict[str, Any]] = []
    audio: list[dict[str, Any]] = []
    for number, obj in enumerate(objects, start=1):
        oid = str(obj["id"])
        base = f"{number:03d}-{_slug(str(obj.get('kind') or 'object'), 'object')}"
        name = base + ".md"
        if name.casefold() in used_names:
            name = base + "-" + _slug(oid, "id") + ".md"
        used_names.add(name.casefold())
        files[f"handouts/{name}"] = _object_markdown(obj).encode("utf-8")
        handout_lines.append(f"- [{obj.get('title') or obj.get('name') or oid}]({name})")
        object_rows.append({"id": oid, "kind": obj.get("kind"), "title": obj.get("title") or obj.get("name"), "file": f"handouts/{name}"})
        kind = str(obj.get("kind") or "").casefold().replace("_", "-")
        data = obj.get("data") if isinstance(obj.get("data"), dict) else {}
        if kind in {"table", "roll-table", "random-table", "rumor-table"}:
            for entry_number, entry in enumerate(data.get("entries", []), start=1):
                if isinstance(entry, str):
                    entry = {"text": entry}
                if isinstance(entry, dict):
                    table_rows.append({"table_id": oid, "entry": entry_number, "weight": entry.get("weight", 1), "text": entry.get("text") or entry.get("result") or ""})
        if kind in {"scene", "map", "battle-map", "region-map"}:
            scenes.append({"id": oid, "title": obj.get("title") or obj.get("name"), "data": data, "asset_ids": _object_asset_ids(obj)})
        if kind in {"token", "npc", "character", "creature"} and data.get("token") is not None:
            tokens.append({"id": oid, "title": obj.get("title") or obj.get("name"), "token": data.get("token")})
        if kind in {"audio", "audio-cue", "soundscape"}:
            audio.append({"id": oid, "title": obj.get("title") or obj.get("name"), "data": data, "asset_ids": _object_asset_ids(obj)})

    files["handouts/index.md"] = ("\n".join(handout_lines) + "\n").encode("utf-8")
    files["data/objects.json"] = pretty_json_bytes(objects)
    files["data/object-index.csv"] = _write_csv(object_rows, ["id", "kind", "title", "file"])
    files["data/tables.json"] = pretty_json_bytes(table_rows)
    files["data/tables.csv"] = _write_csv(table_rows, ["table_id", "entry", "weight", "text"])
    files["data/scenes.json"] = pretty_json_bytes(scenes)
    files["data/tokens.json"] = pretty_json_bytes(tokens)
    files["data/audio-cues.json"] = pretty_json_bytes(audio)

    asset_index: list[dict[str, Any]] = []
    loss_items: list[dict[str, Any]] = []
    used_asset_paths: set[str] = set()
    for asset_number, asset in enumerate(sorted(assets, key=lambda item: str(item.get("id"))), start=1):
        asset_id = str(asset["id"])
        source = captured.assets.get(asset_id)
        if source is None:
            raise ExportError(f"captured bytes missing for asset {asset_id}")
        data = source.read_bytes()
        original_name = PurePosixPath(str(asset["path"])).name
        extension = PurePosixPath(original_name).suffix
        safe_extension = extension if re.fullmatch(r"\.[A-Za-z0-9]{1,10}", extension) else ""
        output_name = f"asset-{asset_number:03d}{safe_extension.lower()}" if audience == "player" else _slug(asset_id, "asset") + "-" + _slug(original_name, "file")
        output_path = _reserve_asset_path(output_name, used_asset_paths)
        kind = str(asset.get("kind") or "").casefold()
        if original_name.casefold().endswith(".uvtt") or kind in {"uvtt", "universal-vtt"}:
            _validate_uvtt(data, asset_id)
        files[output_path] = data
        asset_entry = {
            "id": asset_id,
            "pack_path": output_path,
            "kind": asset.get("kind"),
            "media_type": asset.get("media_type"),
            "alt_text": asset.get("alt_text"),
            "rights": asset.get("rights", {"status": "unknown"}),
            "sha256": sha256_bytes(data),
        }
        if audience == "gm":
            asset_entry["source_path"] = asset.get("path")
        asset_index.append(asset_entry)
        rights = asset.get("rights")
        if not isinstance(rights, dict) or rights.get("status") in {None, "unknown"}:
            loss_items.append({"severity": "warning", "source_id": asset_id, "code": "unknown_rights", "message": "Asset rights need human review before public distribution."})
    pack_paths = [str(item["pack_path"]) for item in asset_index]
    if len(pack_paths) != len({path.casefold() for path in pack_paths}):
        raise ExportError("generic asset index contains duplicate pack_path values")
    files["data/assets.json"] = pretty_json_bytes(asset_index)

    loss_report = {
        "format": "cd-ludis-loss-report/v1",
        "adapter": "generic",
        "items": loss_items,
        "summary": {"blocked": 0, "warnings": len(loss_items)},
    }
    files["reports/loss-report.json"] = pretty_json_bytes(loss_report)
    member_inventory = [
        {"path": name, "bytes": len(data), "sha256": sha256_bytes(data)}
        for name, data in sorted(files.items())
    ]
    manifest = {
        "format": PACK_FORMAT,
        "audience": audience,
        "campaign": {"id": campaign.get("id"), "title": title} if isinstance(campaign, dict) else {"id": None, "title": title},
        "source": {"capture_digest": captured.source_digest, "ledger_sha256": sha256_file(captured.ledger_path)},
        "object_ids": [obj["id"] for obj in objects],
        "asset_ids": [asset["id"] for asset in assets],
        "adapter": {"id": "generic", "version": "1"},
        "human_review_required": audience == "player",
        "members": member_inventory,
        "manifest_self_hash": "intentionally omitted because a file cannot contain its own cryptographic digest",
    }
    files["ludis-pack.json"] = canonical_json_bytes(manifest)
    return files


def write_deterministic_zip(path: Path, files: Mapping[str, bytes]) -> str:
    validate_archive_member_names(files)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    if temporary.exists():
        temporary.unlink()
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as archive:
            for name in sorted(files):
                info = zipfile.ZipInfo(name, FIXED_ZIP_TIME)
                info.compress_type = zipfile.ZIP_STORED
                info.create_system = 3
                info.external_attr = (0o100644 & 0xFFFF) << 16
                info.flag_bits |= 0x800
                archive.writestr(info, files[name])
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()
    return sha256_file(path)


def verify_pack(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ExportError(f"pack does not exist: {path}")
    with zipfile.ZipFile(path, "r") as archive:
        names = archive.namelist()
        validate_archive_member_names(names)
        if "ludis-pack.json" not in names:
            raise ExportError("ludis-pack.json is missing")
        try:
            manifest = json.loads(archive.read("ludis-pack.json").decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ExportError(f"invalid ludis-pack.json: {exc}") from exc
        if manifest.get("format") != PACK_FORMAT:
            raise ExportError("unsupported Ludis Pack format")
        declared = {item.get("path"): item for item in manifest.get("members", []) if isinstance(item, dict)}
        actual = set(names) - {"ludis-pack.json"}
        if set(declared) != actual:
            raise ExportError("pack member inventory does not match archive members")
        for name, item in declared.items():
            data = archive.read(name)
            if item.get("bytes") != len(data) or item.get("sha256") != sha256_bytes(data):
                raise ExportError(f"pack member digest mismatch: {name}")
    return {"path": str(path), "sha256": sha256_file(path), "format": PACK_FORMAT, "audience": manifest.get("audience"), "members": len(names)}


def _preview_html(files: Mapping[str, bytes], projection: dict[str, Any], audience: str) -> bytes:
    campaign = projection.get("campaign", {})
    title = campaign.get("title") if isinstance(campaign, dict) else "Untitled campaign"
    rows = "".join(
        f"<tr><td>{html.escape(name)}</td><td>{len(data)}</td><td><code>{sha256_bytes(data)}</code></td></tr>"
        for name, data in sorted(files.items())
    )
    object_sections = "".join(
        "<article><h2>" + html.escape(str(obj.get("title") or obj.get("name") or obj.get("id"))) + "</h2><pre>" +
        html.escape(_object_markdown(obj)) + "</pre></article>"
        for obj in projection["objects"]
    )
    alt_by_path: dict[str, str] = {}
    try:
        asset_index = json.loads(files.get("data/assets.json", b"[]").decode("utf-8"))
        alt_by_path = {
            str(item.get("pack_path")): str(item.get("alt_text") or f"Preview of exported image asset {item.get('id')}")
            for item in asset_index
            if isinstance(item, dict) and isinstance(item.get("pack_path"), str)
        }
    except (UnicodeDecodeError, json.JSONDecodeError):
        alt_by_path = {}
    image_types = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp", ".gif": "image/gif"}
    image_sections = []
    for name, data in sorted(files.items()):
        media_type = image_types.get(PurePosixPath(name).suffix.casefold())
        if media_type is None:
            continue
        encoded = base64.b64encode(data).decode("ascii")
        image_sections.append(
            '<section><h2>{}</h2><img src="data:{};base64,{}" alt="{}"></section>'.format(
                html.escape(name), media_type, encoded, html.escape(alt_by_path.get(name, f"Preview of exported image asset {name}"), quote=True)
            )
        )
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Ludis player-pack preview</title>
<style>body{{font:16px/1.5 system-ui;max-width:80rem;margin:auto;padding:2rem}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #777;padding:.4rem;text-align:left;vertical-align:top}}code{{overflow-wrap:anywhere}}pre{{white-space:pre-wrap}}img{{max-width:100%;height:auto;border:2px solid #555}}section{{margin-block:2rem}}</style></head>
<body><main><h1>{html.escape(str(title))}: {html.escape(audience)} pack preview</h1>
<p>This preview is one required review surface, not the whole candidate. Before approval, extract the candidate into a new directory, compare every member in this inventory with the candidate and audit, inspect or listen to every member not rendered here, and treat bundled code as text without executing it. Semantic spoiler review remains human work.</p>
<table><thead><tr><th scope="col">Member</th><th scope="col">Bytes</th><th scope="col">SHA-256</th></tr></thead><tbody>{rows}</tbody></table>{object_sections}{''.join(image_sections)}</main></body></html>
"""
    return document.encode("utf-8")


def _sidecar(path: Path, label: str) -> Path:
    return path.with_name(path.name + f".{label}.json")


def _preview_path(path: Path) -> Path:
    return path.with_name(path.name + ".preview.html")


def build_pack(campaign_root: Path, output: Path, audience: str, object_ids: Iterable[str] | None = None) -> BuildResult:
    reserved_output = output.resolve()
    reserved_preview = _preview_path(reserved_output)
    reserved_audit = _sidecar(reserved_output, "audit")
    with exclusive_output_locks((reserved_output, reserved_preview, reserved_audit)):
        return _build_pack_reserved(campaign_root, reserved_output, audience, object_ids)


def _build_pack_reserved(campaign_root: Path, output: Path, audience: str, object_ids: Iterable[str] | None = None) -> BuildResult:
    if audience == "player" and not output.name.endswith(".candidate.zip"):
        raise ExportError("player output must end in .candidate.zip; approve it separately after review")
    if audience == "gm" and output.name.endswith(".candidate.zip"):
        raise ExportError("GM output should be a final .zip, not a player candidate")
    output = output.resolve()
    preview = _preview_path(output)
    audit = _sidecar(output, "audit")
    occupied = [path for path in (output, preview, audit) if path.exists()]
    if occupied:
        raise ExportError("immutable export path already exists: " + ", ".join(str(path) for path in occupied))
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".ludis-build-", dir=str(output.parent)) as temporary_name:
        temporary = Path(temporary_name)
        captured = capture_campaign(campaign_root, temporary / "capture")
        projection = project_ledger(captured.ledger, audience, object_ids)
        files = render_generic_pack(captured, projection, audience)
        staged_artifact = temporary / output.name
        artifact_sha = write_deterministic_zip(staged_artifact, files)
        verification = verify_pack(staged_artifact)
        verification["path"] = output.name
        preview_bytes = _preview_html(files, projection, audience)
        staged_preview = temporary / preview.name
        staged_preview.write_bytes(preview_bytes)
        audit_data = {
            "format": "cd-ludis-export-audit/v1",
            "state": "approval_required" if audience == "player" else "finalized",
            "audience": audience,
            "candidate_sha256" if audience == "player" else "artifact_sha256": artifact_sha,
            "preview_sha256": sha256_bytes(preview_bytes),
            "source_capture_digest": captured.source_digest,
            "object_ids": [obj["id"] for obj in projection["objects"]],
            "asset_ids": [asset["id"] for asset in projection["assets"]],
            "pack_verification": verification,
            "automated_checks": ["archive_paths", "member_inventory", "member_digests", "audience_visibility", "link_visibility", "asset_visibility"],
            "human_checks_required": ["semantic_spoilers", "rights_and_credits", "complete_member_inspection", "non_rendered_media_review", "code_review_as_text_without_execution", "target_import_result"],
        }
        staged_audit = temporary / audit.name
        staged_audit.write_bytes(pretty_json_bytes(audit_data))
        # Sidecars appear before the artifact. A crash cannot leave a final-looking
        # ZIP without the evidence needed to inspect or approve it.
        publish_file_if_absent(staged_preview, preview, "preview")
        publish_file_if_absent(staged_audit, audit, "audit")
        publish_file_if_absent(staged_artifact, output, "artifact")
    return BuildResult(output, artifact_sha, audit, preview, audience, audience == "gm")


def approve_candidate(candidate: Path, asserted_by: str, final: Path | None = None) -> tuple[Path, Path]:
    resolved_candidate = candidate.resolve()
    audit = _sidecar(resolved_candidate, "audit")
    preview = _preview_path(resolved_candidate)
    if final is None and resolved_candidate.name.endswith(".candidate.zip"):
        reserved_final = resolved_candidate.with_name(resolved_candidate.name[: -len(".candidate.zip")] + ".zip")
    elif final is not None:
        reserved_final = final.resolve()
    else:
        reserved_final = resolved_candidate.with_name(resolved_candidate.name + ".final")
    reserved_receipt = reserved_final.with_name(reserved_final.name + ".approval.json")
    with exclusive_output_locks((resolved_candidate, audit, preview, reserved_final, reserved_receipt)):
        return _approve_candidate_reserved(resolved_candidate, asserted_by, reserved_final if final is not None else None)


def _approve_candidate_reserved(candidate: Path, asserted_by: str, final: Path | None = None) -> tuple[Path, Path]:
    if not asserted_by.strip():
        raise ExportError("asserted_by is required")
    candidate = candidate.resolve()
    if not candidate.name.endswith(".candidate.zip"):
        raise ExportError("approval input must end in .candidate.zip")
    audit_path = _sidecar(candidate, "audit")
    preview_path = _preview_path(candidate)
    if not audit_path.is_file() or not preview_path.is_file():
        raise ExportError("candidate audit and preview sidecars are required")

    frozen_candidate = freeze_file(candidate, "candidate")
    frozen_preview = freeze_file(preview_path, "preview")
    frozen_audit = freeze_file(audit_path, "audit")
    frozen_inputs = (frozen_candidate, frozen_preview, frozen_audit)
    try:
        audit = json.loads(frozen_audit.data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ExportError(f"candidate audit is invalid: {exc}") from exc
    candidate_sha = frozen_candidate.sha256
    preview_sha = frozen_preview.sha256
    if audit.get("format") != "cd-ludis-export-audit/v1" or audit.get("state") != "approval_required" or audit.get("audience") != "player":
        raise ExportError("audit does not describe an approval-ready player candidate")
    if audit.get("candidate_sha256") != candidate_sha:
        raise ExportError("candidate bytes changed after audit; rebuild and review again")
    if audit.get("preview_sha256") != preview_sha:
        raise ExportError("preview bytes changed after audit; rebuild and review again")

    if final is None:
        final = candidate.with_name(candidate.name[: -len(".candidate.zip")] + ".zip")
    final = final.resolve()
    receipt = final.with_name(final.name + ".approval.json")
    if final in {candidate, preview_path, audit_path} or receipt in {candidate, preview_path, audit_path}:
        raise ExportError("final and approval receipt paths must not overlap candidate evidence")

    final.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".ludis-finalize-", dir=str(final.parent)) as temporary_name:
        temporary = Path(temporary_name)
        staged_input = temporary / "frozen-player.candidate.zip"
        staged_input.write_bytes(frozen_candidate.data)
        verified = verify_pack(staged_input)
        if verified.get("audience") != "player":
            raise ExportError("candidate verification did not confirm a player pack")
        recheck_frozen_files(frozen_inputs)

        limitations = "Ludis binds this local assertion to exact frozen candidate, preview, and audit bytes; it does not authenticate the operator identity."
        if final.exists() or receipt.exists():
            if not (final.is_file() and receipt.is_file()):
                raise ExportError("partial prior finalization exists; preserve it and choose a new --final path")
            frozen_final = freeze_file(final, "prior final artifact")
            frozen_receipt = freeze_file(receipt, "prior approval receipt")
            try:
                previous = json.loads(frozen_receipt.data.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ExportError("prior approval receipt is unreadable; preserve it and choose a new --final path") from exc
            expected_keys = {
                "format", "state", "artifact", "artifact_sha256", "candidate", "candidate_sha256",
                "preview", "preview_sha256", "audit", "audit_sha256", "asserted_by",
                "assertion_type", "approved_at", "ledger_approval_record", "limitations",
            }
            approved_at = previous.get("approved_at")
            valid_timestamp = False
            if isinstance(approved_at, str) and approved_at.endswith("Z"):
                try:
                    datetime.fromisoformat(approved_at[:-1] + "+00:00")
                    valid_timestamp = True
                except ValueError:
                    pass
            previous_operator = previous.get("asserted_by")
            expected_approval_record = {
                "id": "approval-" + candidate_sha[:24],
                "action": "exact_candidate_approved",
                "run_id": "export-" + candidate_sha[:24],
                "audience": "player",
                "candidate_sha256": candidate_sha,
                "preview_sha256": preview_sha,
                "asserted_by": previous_operator,
                "asserted_at": approved_at,
            }
            same_evidence = (
                frozen_final.sha256 == candidate_sha
                and frozen_receipt.data == pretty_json_bytes(previous)
                and set(previous) == expected_keys
                and previous.get("format") == "cd-ludis-local-approval/v1"
                and previous.get("state") == "finalized"
                and previous.get("artifact") == final.name
                and previous.get("artifact_sha256") == candidate_sha
                and previous.get("candidate") == candidate.name
                and previous.get("candidate_sha256") == candidate_sha
                and previous.get("preview") == preview_path.name
                and previous.get("preview_sha256") == preview_sha
                and previous.get("audit") == audit_path.name
                and previous.get("audit_sha256") == frozen_audit.sha256
                and isinstance(previous_operator, str)
                and bool(previous_operator.strip())
                and previous.get("assertion_type") == "unauthenticated_local_operator_attestation"
                and valid_timestamp
                and previous.get("ledger_approval_record") == expected_approval_record
                and previous.get("limitations") == limitations
            )
            if not same_evidence:
                raise ExportError(f"final path already contains different evidence: {final}")
            if previous_operator != asserted_by:
                raise ExportError("candidate was already finalized under a different local operator assertion")
            recheck_frozen_files((frozen_final, frozen_receipt))
            return final, receipt

        asserted_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        run_id = "export-" + candidate_sha[:24]
        approval_record = {
            "id": "approval-" + candidate_sha[:24],
            "action": "exact_candidate_approved",
            "run_id": run_id,
            "audience": "player",
            "candidate_sha256": candidate_sha,
            "preview_sha256": preview_sha,
            "asserted_by": asserted_by,
            "asserted_at": asserted_at,
        }
        receipt_data = {
            "format": "cd-ludis-local-approval/v1",
            "state": "finalized",
            "artifact": final.name,
            "artifact_sha256": candidate_sha,
            "candidate": candidate.name,
            "candidate_sha256": candidate_sha,
            "preview": preview_path.name,
            "preview_sha256": preview_sha,
            "audit": audit_path.name,
            "audit_sha256": frozen_audit.sha256,
            "asserted_by": asserted_by,
            "assertion_type": "unauthenticated_local_operator_attestation",
            "approved_at": asserted_at,
            "ledger_approval_record": approval_record,
            "limitations": limitations,
        }
        staged_final = temporary / final.name
        staged_receipt = temporary / receipt.name
        staged_final.write_bytes(frozen_candidate.data)
        if sha256_file(staged_final) != candidate_sha:
            raise ExportError("final copy failed digest verification")
        staged_receipt.write_bytes(pretty_json_bytes(receipt_data))
        recheck_frozen_files(frozen_inputs)
        # The receipt arrives first; the approved artifact becomes visible last.
        publish_file_if_absent(staged_receipt, receipt, "approval receipt")
        publish_file_if_absent(staged_final, final, "approved artifact")
    if sha256_file(final) != candidate_sha:
        raise ExportError("final artifact does not equal the approved candidate")
    return final, receipt
