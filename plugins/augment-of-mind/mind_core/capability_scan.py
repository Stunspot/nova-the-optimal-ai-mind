"""Bounded, host-neutral discovery of ``SKILL.md`` capability candidates.

The scanner reads only explicit directories and ZIP archives.  It produces
metadata suitable for later human reconciliation; it does not infer canonical
identity, ingest Core records, or retain source bodies.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import re
import stat
from typing import Iterable, Literal
import unicodedata
import zipfile

from .errors import ValidationError
from .util import canonical_json, require_identifier, require_text


REPORT_FORMAT = "mind-capability-estate-candidates/v1"
_FRONTMATTER_KEY = re.compile(r"([A-Za-z][A-Za-z0-9_-]*):[ ]*(.*)\Z")
_SKILL_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")
_WINDOWS_PATH = re.compile(r"[A-Za-z]:")
_WINDOWS_REPARSE_POINT = 0x400
_UTF8_BOM = b"\xef\xbb\xbf"


@dataclass(frozen=True)
class EstateSource:
    """One explicitly admitted source; ``path`` is intentionally not reported."""

    source_id: str
    kind: Literal["directory", "readme", "skill", "zip"]
    path: Path
    locator: str


@dataclass(frozen=True)
class ScanLimits:
    max_skill_bytes: int = 1_048_576
    max_frontmatter_bytes: int = 16_384
    max_archive_members: int = 10_000
    max_archive_uncompressed_bytes: int = 64 * 1024 * 1024
    max_description_chars: int = 1_024


DEFAULT_LIMITS = ScanLimits()


def _validate_source(source: EstateSource) -> None:
    require_identifier(source.source_id, "source_id")
    if source.kind not in {"directory", "readme", "skill", "zip"}:
        raise ValidationError("source.kind must be directory, readme, skill, or zip")
    locator = require_text(source.locator, "source.locator", maximum=2048)
    if (
        _WINDOWS_PATH.match(locator)
        or locator.startswith(("/", "\\"))
        or "\\" in locator
        or locator.casefold().startswith("file:")
        or ".." in locator.split("/")
    ):
        raise ValidationError("source.locator must not contain a host filesystem path")
    if not isinstance(source.path, Path):
        raise ValidationError("source.path must be a pathlib.Path")


def _validate_limits(limits: ScanLimits) -> None:
    for field in (
        "max_skill_bytes",
        "max_frontmatter_bytes",
        "max_archive_members",
        "max_archive_uncompressed_bytes",
        "max_description_chars",
    ):
        if not isinstance(getattr(limits, field), int) or getattr(limits, field) < 1:
            raise ValidationError(f"limits.{field} must be a positive integer")


def _member_locator(source: EstateSource, member: str) -> str:
    return f"{source.locator.rstrip('/')}#{member}"


def _diagnostic(
    source: EstateSource, code: str, detail: str, *, member: str | None = None
) -> dict[str, str]:
    record = {
        "source_id": source.source_id,
        "code": code,
        "detail": detail[:512],
    }
    if member is not None:
        record["locator"] = _member_locator(source, member)
    return record


def _safe_zip_member(name: str) -> str | None:
    path = PurePosixPath(name)
    if (
        not name
        or "\\" in name
        or path.is_absolute()
        or ".." in path.parts
        or any(part.endswith(":") for part in path.parts)
    ):
        return None
    return unicodedata.normalize("NFC", path.as_posix())


def _is_linklike(file_stat: object) -> bool:
    mode = getattr(file_stat, "st_mode", 0)
    attributes = getattr(file_stat, "st_file_attributes", 0)
    return stat.S_ISLNK(mode) or bool(attributes & _WINDOWS_REPARSE_POINT)


def _parse_scalar(value: str, field: str) -> str:
    if not value or value.startswith(("|", ">", "&", "*", "!", "[", "{")):
        raise ValueError(f"{field} must be a single scalar")
    if value.startswith('"'):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{field} has invalid quoted text") from exc
        if not isinstance(decoded, str):
            raise ValueError(f"{field} must be text")
        value = decoded
    elif value.startswith("'"):
        if not value.endswith("'") or len(value) < 2:
            raise ValueError(f"{field} has invalid quoted text")
        value = value[1:-1].replace("''", "'")
    if "\n" in value or "\r" in value or not value.strip():
        raise ValueError(f"{field} must be one non-empty line")
    return value


def _decode_utf8(data: bytes, document: str) -> str:
    payload = data
    if payload.startswith(_UTF8_BOM):
        payload = payload[len(_UTF8_BOM) :]
    if _UTF8_BOM in payload:
        raise ValueError(f"{document} has an unexpected BOM")
    try:
        return payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{document} is not valid UTF-8") from exc


def _frontmatter(text: str, limits: ScanLimits) -> tuple[str, str]:
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != "---":
        raise ValueError("SKILL.md must begin with frontmatter delimiter")
    consumed = len(lines[0].encode("utf-8"))
    fields: dict[str, str] = {}
    seen_keys: set[str] = set()
    ignored_block = False
    closed = False
    for line in lines[1:]:
        consumed += len(line.encode("utf-8"))
        if consumed > limits.max_frontmatter_bytes:
            raise ValueError("frontmatter exceeds max_frontmatter_bytes")
        value = line.rstrip("\r\n")
        if value == "---":
            closed = True
            break
        if not value or value.lstrip().startswith("#"):
            continue
        if value[0].isspace():
            if ignored_block:
                continue
            raise ValueError("frontmatter permits multiline content only in ignored metadata")
        match = _FRONTMATTER_KEY.fullmatch(value)
        if match is None:
            raise ValueError("frontmatter permits only top-level scalar fields")
        key, raw = match.groups()
        if key in seen_keys:
            raise ValueError(f"frontmatter repeats {key}")
        seen_keys.add(key)
        ignored_block = key not in {"name", "description"} and not raw
        if key in {"name", "description"}:
            fields[key] = _parse_scalar(raw, key)
    if not closed:
        raise ValueError("frontmatter closing delimiter is missing")
    name = fields.get("name")
    description = fields.get("description")
    if name is None or description is None:
        raise ValueError("frontmatter requires name and description")
    if not _SKILL_NAME.fullmatch(name):
        raise ValueError("frontmatter name is not a bounded skill identifier")
    if len(description) > limits.max_description_chars:
        raise ValueError("frontmatter description exceeds max_description_chars")
    return name, description


def _candidate(
    source: EstateSource, member: str, data: bytes, limits: ScanLimits, transport: str
) -> dict[str, object]:
    if len(data) > limits.max_skill_bytes:
        raise ValueError("SKILL.md exceeds max_skill_bytes")
    text = _decode_utf8(data, "SKILL.md")
    declared_name, description = _frontmatter(text, limits)
    name = _stable_slug(declared_name)
    return {
        "source_id": source.source_id,
        "locator": _member_locator(source, member),
        "transport": transport,
        "member": member,
        "name": name,
        "display_name": declared_name,
        "normalized_name": name.casefold(),
        "description": description,
        "bytes": len(data),
        "sha256": sha256(data).hexdigest(),
        "metadata_state": "declared",
    }


def _read_file_bounded(path: Path, maximum: int) -> bytes:
    with path.open("rb") as stream:
        data = stream.read(maximum + 1)
    if len(data) > maximum:
        raise ValueError("SKILL.md exceeds max_skill_bytes")
    return data


def _plain_markdown(value: str) -> str:
    value = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", value)
    value = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", value)
    value = re.sub(r"<[^>]+>", " ", value)
    value = value.replace("`", "").replace("**", "").replace("__", "")
    return " ".join(value.split()).strip(" #-*_>")


def _stable_slug(value: str) -> str:
    slug = unicodedata.normalize("NFKC", value).casefold().replace("&", " and ")
    slug = re.sub(r"[^a-z0-9._:-]+", "-", slug).strip("-._:")
    if not slug:
        raise ValueError("content identity cannot form a stable capability name")
    slug = slug[:128].rstrip("-._:")
    if not _SKILL_NAME.fullmatch(slug):
        raise ValueError("content identity cannot form a bounded capability name")
    return slug


def _readme_identity(text: str, fallback: str) -> tuple[str, str, str]:
    lines = text.splitlines()
    title = ""
    title_index = -1
    for index, line in enumerate(lines[:200]):
        match = re.match(r"^\s*#\s+(.+?)\s*$", line)
        if match:
            title = _plain_markdown(match.group(1))
            title_index = index
            break
    if not title:
        title = fallback
    try:
        slug = _stable_slug(title)
    except ValueError:
        slug = _stable_slug(fallback)

    description = ""
    paragraph: list[str] = []
    in_fence = False
    for line in lines[title_index + 1 :]:
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if not stripped:
            if paragraph:
                candidate = _plain_markdown(" ".join(paragraph))
                if candidate:
                    description = candidate
                    break
                paragraph = []
            continue
        if (
            stripped.startswith(("#", "!", "<", "[!", "|", "---"))
            or re.fullmatch(r"[-:| ]+", stripped)
        ):
            continue
        paragraph.append(stripped)
    if not description and paragraph:
        description = _plain_markdown(" ".join(paragraph))
    if not description:
        description = f"Repository tool documented by the {title} README."
    return slug, title[:256], description


def _readme_candidate(
    source: EstateSource, member: str, data: bytes, limits: ScanLimits
) -> dict[str, object]:
    if len(data) > limits.max_skill_bytes:
        raise ValueError("README exceeds max_skill_bytes")
    text = _decode_utf8(data, "README")
    name, display_name, description = _readme_identity(
        text, source.path.parent.name
    )
    if len(description) > limits.max_description_chars:
        description = description[: limits.max_description_chars].rstrip()
    return {
        "source_id": source.source_id,
        "locator": _member_locator(source, member),
        "transport": "readme",
        "member": member,
        "name": name,
        "display_name": display_name,
        "normalized_name": name.casefold(),
        "description": description,
        "bytes": len(data),
        "sha256": sha256(data).hexdigest(),
        "metadata_state": "readme_derived",
    }


def _scan_readme(
    source: EstateSource, limits: ScanLimits
) -> tuple[list[dict[str, object]], list[dict[str, str]]]:
    try:
        file_stat = source.path.lstat()
    except OSError:
        return [], [_diagnostic(source, "source-unreadable", "README source could not be read")]
    if _is_linklike(file_stat):
        return [], [_diagnostic(source, "source-symlink", "README source is a symlink")]
    if (
        not stat.S_ISREG(file_stat.st_mode)
        or not source.path.name.casefold().startswith("readme")
    ):
        return [], [_diagnostic(source, "source-not-readme", "README source must be a regular README file")]
    if file_stat.st_size > limits.max_skill_bytes:
        return [], [_diagnostic(source, "readme-oversize", "README exceeds max_skill_bytes", member=source.path.name)]
    try:
        data = _read_file_bounded(source.path, limits.max_skill_bytes)
        return [_readme_candidate(source, source.path.name, data, limits)], []
    except ValueError as exc:
        return [], [_diagnostic(source, "readme-rejected", str(exc), member=source.path.name)]
    except OSError:
        return [], [_diagnostic(source, "readme-rejected", "README could not be read", member=source.path.name)]


def _scan_skill(
    source: EstateSource, limits: ScanLimits
) -> tuple[list[dict[str, object]], list[dict[str, str]]]:
    try:
        file_stat = source.path.lstat()
    except OSError:
        return [], [_diagnostic(source, "source-unreadable", "skill source could not be read")]
    if _is_linklike(file_stat):
        return [], [_diagnostic(source, "source-symlink", "skill source is a symlink")]
    if not stat.S_ISREG(file_stat.st_mode) or source.path.name != "SKILL.md":
        return [], [_diagnostic(source, "source-not-skill", "skill source must be a regular SKILL.md file")]
    if file_stat.st_size > limits.max_skill_bytes:
        return [], [_diagnostic(source, "skill-oversize", "SKILL.md exceeds max_skill_bytes", member="SKILL.md")]
    try:
        data = _read_file_bounded(source.path, limits.max_skill_bytes)
        return [_candidate(source, "SKILL.md", data, limits, "skill")], []
    except ValueError as exc:
        return [], [_diagnostic(source, "skill-rejected", str(exc), member="SKILL.md")]
    except OSError:
        return [], [_diagnostic(source, "skill-rejected", "SKILL.md could not be read", member="SKILL.md")]


def _scan_directory(
    source: EstateSource, limits: ScanLimits
) -> tuple[list[dict[str, object]], list[dict[str, str]]]:
    candidates: list[dict[str, object]] = []
    diagnostics: list[dict[str, str]] = []
    try:
        root_stat = source.path.lstat()
    except OSError:
        return [], [_diagnostic(source, "source-unreadable", "directory source could not be read")]
    if _is_linklike(root_stat):
        return [], [_diagnostic(source, "source-symlink", "directory source is a symlink")]
    if not stat.S_ISDIR(root_stat.st_mode):
        return [], [_diagnostic(source, "source-not-directory", "directory source is not a directory")]

    def visit(directory: Path, prefix: PurePosixPath) -> None:
        try:
            entries = sorted(directory.iterdir(), key=lambda item: item.name)
        except OSError:
            member = prefix.as_posix() or None
            diagnostics.append(
                _diagnostic(
                    source,
                    "directory-unreadable",
                    "directory could not be read",
                    member=member,
                )
            )
            return
        for entry in entries:
            member = (prefix / entry.name).as_posix()
            try:
                entry_stat = entry.lstat()
            except OSError:
                diagnostics.append(_diagnostic(source, "entry-unreadable", "entry could not be read", member=member))
                continue
            if _is_linklike(entry_stat):
                diagnostics.append(_diagnostic(source, "symlink-ignored", "symlink was not followed", member=member))
            elif stat.S_ISDIR(entry_stat.st_mode):
                visit(entry, prefix / entry.name)
            elif stat.S_ISREG(entry_stat.st_mode) and entry.name == "SKILL.md":
                if entry_stat.st_size > limits.max_skill_bytes:
                    diagnostics.append(_diagnostic(source, "skill-oversize", "SKILL.md exceeds max_skill_bytes", member=member))
                    continue
                try:
                    data = _read_file_bounded(entry, limits.max_skill_bytes)
                    candidates.append(_candidate(source, member, data, limits, "directory"))
                except ValueError as exc:
                    diagnostics.append(_diagnostic(source, "skill-rejected", str(exc), member=member))
                except OSError:
                    diagnostics.append(_diagnostic(source, "skill-rejected", "SKILL.md could not be read", member=member))

    visit(source.path, PurePosixPath())
    return candidates, diagnostics


def _scan_zip(
    source: EstateSource, limits: ScanLimits
) -> tuple[list[dict[str, object]], list[dict[str, str]]]:
    candidates: list[dict[str, object]] = []
    diagnostics: list[dict[str, str]] = []
    try:
        archive = zipfile.ZipFile(source.path)
    except (OSError, zipfile.BadZipFile):
        return [], [_diagnostic(source, "archive-unreadable", "archive could not be read")]
    with archive:
        infos = archive.infolist()
        if len(infos) > limits.max_archive_members:
            return [], [_diagnostic(source, "archive-member-limit", "archive exceeds max_archive_members")]
        if sum(info.file_size for info in infos) > limits.max_archive_uncompressed_bytes:
            return [], [_diagnostic(source, "archive-oversize", "archive exceeds max_archive_uncompressed_bytes")]
        normalized: set[str] = set()
        for info in infos:
            member = _safe_zip_member(info.orig_filename)
            if member is None:
                return [], [_diagnostic(source, "archive-unsafe-member", "archive has an unsafe member path")]
            member_key = member.casefold()
            if member_key in normalized:
                return [], [_diagnostic(source, "archive-duplicate-member", "archive repeats a member path")]
            normalized.add(member_key)
            if info.flag_bits & 0x1:
                return [], [_diagnostic(source, "archive-encrypted-member", "archive has an encrypted member")]
            if stat.S_ISLNK(info.external_attr >> 16):
                return [], [_diagnostic(source, "archive-symlink-member", "archive has a symlink member")]
        for info in infos:
            member = _safe_zip_member(info.orig_filename)
            if member is None or member.endswith("/") or PurePosixPath(member).name != "SKILL.md":
                continue
            if info.file_size > limits.max_skill_bytes:
                diagnostics.append(_diagnostic(source, "skill-oversize", "SKILL.md exceeds max_skill_bytes", member=member))
                continue
            try:
                with archive.open(info) as stream:
                    data = stream.read(limits.max_skill_bytes + 1)
                candidates.append(_candidate(source, member, data, limits, "zip"))
            except ValueError as exc:
                diagnostics.append(_diagnostic(source, "skill-rejected", str(exc), member=member))
            except (OSError, zipfile.BadZipFile):
                diagnostics.append(_diagnostic(source, "skill-rejected", "SKILL.md could not be read", member=member))
    return candidates, diagnostics


def _collisions(candidates: list[dict[str, object]]) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for kind, field in (("name", "normalized_name"), ("content", "sha256")):
        groups: dict[str, list[dict[str, object]]] = {}
        for candidate in candidates:
            groups.setdefault(str(candidate[field]), []).append(candidate)
        for value, members in sorted(groups.items()):
            if len(members) > 1:
                result.append(
                    {
                        "kind": kind,
                        "value": value,
                        "locators": sorted(str(member["locator"]) for member in members),
                    }
                )
    return result


def scan_capability_estate(
    sources: Iterable[EstateSource], *, limits: ScanLimits = DEFAULT_LIMITS
) -> dict[str, object]:
    """Scan admitted sources without retaining content or host-specific paths."""

    _validate_limits(limits)
    candidates: list[dict[str, object]] = []
    diagnostics: list[dict[str, str]] = []
    source_records: list[dict[str, str]] = []
    source_ids: set[str] = set()
    for source in sources:
        if not isinstance(source, EstateSource):
            raise ValidationError("sources must contain EstateSource records")
        _validate_source(source)
        if source.source_id in source_ids:
            raise ValidationError("source_id values must be unique")
        source_ids.add(source.source_id)
        source_records.append(
            {"source_id": source.source_id, "kind": source.kind, "locator": source.locator}
        )
        if source.kind == "directory":
            discovered, reported = _scan_directory(source, limits)
        elif source.kind == "readme":
            discovered, reported = _scan_readme(source, limits)
        elif source.kind == "skill":
            discovered, reported = _scan_skill(source, limits)
        else:
            discovered, reported = _scan_zip(source, limits)
        candidates.extend(discovered)
        diagnostics.extend(reported)
    candidates.sort(key=lambda item: (str(item["source_id"]), str(item["member"])))
    diagnostics.sort(key=lambda item: (item["source_id"], item.get("locator", ""), item["code"], item["detail"]))
    source_records.sort(key=lambda item: item["source_id"])
    return {
        "format": REPORT_FORMAT,
        "limits": {
            "max_skill_bytes": limits.max_skill_bytes,
            "max_frontmatter_bytes": limits.max_frontmatter_bytes,
            "max_archive_members": limits.max_archive_members,
            "max_archive_uncompressed_bytes": limits.max_archive_uncompressed_bytes,
            "max_description_chars": limits.max_description_chars,
        },
        "sources": source_records,
        "candidates": candidates,
        "diagnostics": diagnostics,
        "collisions": _collisions(candidates),
        "report_sha256": sha256(
            canonical_json(
                {
                    "format": REPORT_FORMAT,
                    "sources": source_records,
                    "candidates": candidates,
                    "diagnostics": diagnostics,
                    "collisions": _collisions(candidates),
                }
            ).encode("utf-8")
        ).hexdigest(),
    }
