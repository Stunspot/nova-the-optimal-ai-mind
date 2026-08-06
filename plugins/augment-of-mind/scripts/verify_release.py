#!/usr/bin/env python3
"""Verify an extracted MIND customer release with only the standard library."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import sys
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlparse
import zipfile


MANIFEST_NAME = "RELEASE-MANIFEST.json"
MANIFEST_FORMAT = "cd-mind-release-manifest/v1"
PRODUCT = "augment-of-mind"
MARKETPLACE_NAME = "collaborative-dynamics-mind"
MARKETPLACE_DISPLAY_NAME = "Collaborative Dynamics: MIND"
PLUGIN_VERSION = "2.1.2"
CORE_NAME = "cd-mind-core"
CORE_VERSION = "0.2.0"
ARCHIVE_ROOT = f"{PRODUCT}-v{PLUGIN_VERSION}"
ROOT_DOCUMENTS = (
    "README.md",
    "START-HERE.md",
    "INSTALL-CODEX.md",
    "QUICK-START.md",
    "USER-GUIDE.md",
    "OPTIONAL-CORE.md",
    "HOST-COMPATIBILITY.md",
    "CAPABILITIES-AND-LIMITS.md",
    "CAPABILITY-REMINDERS.md",
    "DATA-AND-PRIVACY.md",
    "SECURITY.md",
    "TROUBLESHOOTING.md",
    "SUPPORT.md",
    "TERMS-OF-USE.md",
    "NOTICE.md",
    "RELEASE-NOTES.md",
    "PACKAGE-REFERENCE.md",
    "LICENSE.md",
)
ASSET_NAMES = (
    "mind-icon-1024.png",
    "mind-hero-1600x900.png",
    "mind-capability-card-1080x1350.png",
)
RUNTIME_SCRIPT_NAMES = (
    "build_associative_assets.py",
    "query_associative_field.py",
)
SKILL_ALLOWED_ROOT_FILES = {"SKILL.md", "manifest.json", "activation-examples.md", "output-contract.md", "adversarial-checks.md", "review-rubric.md"}
SKILL_ALLOWED_DIRECTORIES = {
    "adapters",
    "agents",
    "assets",
    "examples",
    "fallback",
    "fallbacks",
    "personas",
    "references",
    "scripts",
}
SKILL_EXCLUDED_SEGMENTS = {"evals", "tests", "__pycache__", ".pytest_cache"}
SKILL_EXCLUDED_FILES = {"agentic-eros/scripts/validate_package.py"}
EXPECTED_WHEEL_NAME = "cd_mind_core-0.2.0-py3-none-any.whl"
TEXT_SUFFIXES = {
    ".css", ".html", ".json", ".md", ".py", ".toml", ".txt", ".yaml", ".yml"
}
FORBIDDEN_TOP_LEVEL = {".git", ".github", "artifacts", "release-v0.2.0", "tests"}
FORBIDDEN_MCP_PATHS = {
    ".mcp.json",
    "scripts/mind_mcp_server.py",
    "mind_core/mcp_server.py",
}
PRIVATE_PATH = re.compile(
    rb"(?:[A-Za-z]:\\Users\\[^\\\s\[\](){}|]+\\|"
    rb"[A-Za-z]:\\(?:Github|Indranet|Projects)\\|"
    rb"/Users/[^/\s\[\](){}|]+/|/home/[^/\s\[\](){}|]+/)",
    re.IGNORECASE,
)
SECRET_NAME = re.compile(
    r"(?:^|[._-])(credential|password|private[-_]?key|secret|token)(?:[._-]|$)",
    re.IGNORECASE,
)
MARKDOWN_LINK = re.compile(r"!?(?:\[[^\]]*\])\(([^)]+)\)")
SHA256_LINE = re.compile(r"^([a-f0-9]{64})  (.+)$")


class ReleaseError(RuntimeError):
    """Raised when release bytes violate the public contract."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_relative(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if not value or not path.parts or "\\" in value or path.is_absolute() or ".." in path.parts:
        raise ReleaseError(f"unsafe manifest path: {value!r}")
    return path


def validate_payload_path(value: str) -> None:
    path = safe_relative(value)
    parts = path.parts
    if value in FORBIDDEN_MCP_PATHS:
        raise ReleaseError(f"MCP payload is forbidden: {value}")
    if value in ROOT_DOCUMENTS or value in {
        ".codex-plugin/plugin.json",
        ".agents/plugins/marketplace.json",
        "COMPONENT-SHA256SUMS.txt",
        "verify-release.py",
    }:
        return
    if len(parts) == 2 and parts[0] == "assets" and parts[1] in ASSET_NAMES:
        return
    if len(parts) == 2 and parts[0] == "scripts" and parts[1] in RUNTIME_SCRIPT_NAMES:
        return
    if len(parts) == 2 and parts[0] == "hooks" and parts[1] in {"hooks.json", "mind_prompt_submit.py"}:
        return
    if len(parts) >= 2 and parts[0] == "mind_core" and PurePosixPath(value).suffix.lower() in {".py", ".sql"}:
        return
    if parts == ("optional-core", EXPECTED_WHEEL_NAME):
        return
    if len(parts) >= 3 and parts[0] == "skills":
        inner = parts[2:]
        if any(segment in SKILL_EXCLUDED_SEGMENTS for segment in inner):
            raise ReleaseError(f"development skill payload is not allowed: {value}")
        if PurePosixPath(value).suffix.lower() in {".pyc", ".pyo"}:
            raise ReleaseError(f"skill cache payload is not allowed: {value}")
        if len(inner) == 1 and inner[0] in SKILL_ALLOWED_ROOT_FILES:
            return
        if len(inner) >= 2 and inner[0] in SKILL_ALLOWED_DIRECTORIES:
            return
    raise ReleaseError(f"path is outside the customer payload allowlist: {value}")


def regular_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ReleaseError(f"symlink is not allowed: {path.relative_to(root).as_posix()}")
        if path.is_file():
            files.append(path)
    return sorted(files, key=lambda item: item.relative_to(root).as_posix())


def file_records(root: Path, *, exclude: set[str] | None = None) -> list[dict[str, object]]:
    excluded = exclude or set()
    records: list[dict[str, object]] = []
    for path in regular_files(root):
        relative = path.relative_to(root).as_posix()
        if relative in excluded:
            continue
        records.append(
            {
                "path": relative,
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return records


def tree_sha256(root: Path, records: list[dict[str, object]]) -> str:
    digest = hashlib.sha256()
    for record in records:
        relative = str(record["path"])
        data = (root / Path(relative)).read_bytes()
        encoded = relative.encode("utf-8")
        digest.update(struct.pack(">Q", len(encoded)))
        digest.update(encoded)
        digest.update(struct.pack(">Q", len(data)))
        digest.update(data)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ReleaseError(f"cannot read valid JSON: {path.name}: {error}") from error
    if not isinstance(value, dict):
        raise ReleaseError(f"JSON root must be an object: {path.name}")
    return value


def verify_markdown_links(root: Path, paths: set[str]) -> None:
    for relative in sorted(paths):
        path = root / Path(relative)
        if path.suffix.lower() != ".md":
            continue
        text = path.read_text(encoding="utf-8-sig")
        for raw_target in MARKDOWN_LINK.findall(text):
            target = raw_target.strip().strip("<>")
            if not target or target.startswith("#"):
                continue
            without_fragment = target.split("#", 1)[0]
            parsed = urlparse(without_fragment)
            if parsed.scheme:
                continue
            candidate = (path.parent / Path(unquote(without_fragment))).resolve()
            try:
                candidate.relative_to(root)
            except ValueError as error:
                raise ReleaseError(f"relative link escapes release: {relative}: {target}") from error
            if not candidate.exists():
                raise ReleaseError(f"broken relative link: {relative}: {target}")


def metadata_value(text: str, key: str) -> str:
    match = re.search(rf"^{re.escape(key)}:\s*(.+)$", text, re.MULTILINE | re.IGNORECASE)
    if not match:
        raise ReleaseError(f"wheel metadata is missing {key}")
    return match.group(1).strip()


def verify_wheel(root: Path, expected_path: str) -> dict[str, str]:
    wheel = root / Path(expected_path)
    if not wheel.is_file():
        raise ReleaseError(f"optional Core wheel is missing: {expected_path}")
    try:
        with zipfile.ZipFile(wheel) as archive:
            metadata_names = [name for name in archive.namelist() if name.endswith(".dist-info/METADATA")]
            if len(metadata_names) != 1:
                raise ReleaseError("Core wheel must contain exactly one METADATA file")
            metadata = archive.read(metadata_names[0]).decode("utf-8")
    except (OSError, UnicodeDecodeError, zipfile.BadZipFile) as error:
        raise ReleaseError(f"cannot inspect Core wheel: {error}") from error
    name = metadata_value(metadata, "Name")
    version = metadata_value(metadata, "Version")
    requires_python = metadata_value(metadata, "Requires-Python")
    if name != CORE_NAME or version != CORE_VERSION:
        raise ReleaseError(f"unexpected Core wheel identity: {name} {version}")
    if requires_python != ">=3.11":
        raise ReleaseError(f"unexpected Requires-Python: {requires_python}")
    return {"name": name, "version": version, "requires_python": requires_python}


def verify_component_sums(root: Path, wheel_path: str) -> None:
    sums_path = root / "COMPONENT-SHA256SUMS.txt"
    try:
        lines = [line for line in sums_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except (OSError, UnicodeDecodeError) as error:
        raise ReleaseError(f"cannot read component checksums: {error}") from error
    parsed: dict[str, str] = {}
    for line in lines:
        match = SHA256_LINE.fullmatch(line)
        if not match:
            raise ReleaseError(f"invalid component checksum line: {line!r}")
        parsed[match.group(2)] = match.group(1)
    expected = sha256_file(root / Path(wheel_path))
    if parsed != {wheel_path: expected}:
        raise ReleaseError("component checksum set does not match the optional Core wheel")


def verify_marketplace(marketplace: dict[str, object]) -> None:
    interface = marketplace.get("interface")
    entries = marketplace.get("plugins")
    if (
        marketplace.get("name") != MARKETPLACE_NAME
        or not isinstance(interface, dict)
        or interface.get("displayName") != MARKETPLACE_DISPLAY_NAME
        or not isinstance(entries, list)
        or len(entries) != 1
    ):
        raise ReleaseError("marketplace identity, display metadata, or membership is wrong")
    entry = entries[0]
    if not isinstance(entry, dict) or entry.get("name") != PRODUCT:
        raise ReleaseError("marketplace plugin identity is wrong")
    source = entry.get("source")
    if not isinstance(source, dict) or source.get("source") != "local" or source.get("path") != "./":
        raise ReleaseError("marketplace must resolve the plugin at its own root")


def verify(root: Path) -> dict[str, object]:
    root = root.resolve()
    if not root.is_dir():
        raise ReleaseError(f"release root is not a directory: {root}")
    if root.name != ARCHIVE_ROOT:
        raise ReleaseError(f"release root must be named {ARCHIVE_ROOT}")

    manifest = load_json(root / MANIFEST_NAME)
    if manifest.get("format") != MANIFEST_FORMAT:
        raise ReleaseError(f"manifest format must be {MANIFEST_FORMAT}")
    if manifest.get("product") != PRODUCT or manifest.get("plugin_version") != PLUGIN_VERSION:
        raise ReleaseError("manifest product or plugin version is wrong")
    if manifest.get("core_version") != CORE_VERSION or manifest.get("archive_root") != ARCHIVE_ROOT:
        raise ReleaseError("manifest Core version or archive root is wrong")
    if not isinstance(manifest.get("source_revision"), str) or not re.fullmatch(
        r"[a-f0-9]{40}", str(manifest["source_revision"])
    ):
        raise ReleaseError("manifest source revision must be a full lowercase Git object ID")
    if not isinstance(manifest.get("source_material_sha256"), str) or not re.fullmatch(
        r"[a-f0-9]{64}", str(manifest["source_material_sha256"])
    ):
        raise ReleaseError("manifest source material digest must be lowercase SHA-256")
    if manifest.get("manifest_scope") != f"All customer files except {MANIFEST_NAME} itself":
        raise ReleaseError("manifest scope is wrong")

    declared = manifest.get("files")
    if not isinstance(declared, list) or not declared:
        raise ReleaseError("manifest files must be a non-empty list")
    declared_by_path: dict[str, dict[str, object]] = {}
    for item in declared:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            raise ReleaseError("every manifest file record needs a path")
        relative = item["path"]
        safe = safe_relative(relative)
        if safe.parts[0] in FORBIDDEN_TOP_LEVEL:
            raise ReleaseError(f"forbidden top-level payload: {relative}")
        if safe.parts[:2] == ("docs", "architecture"):
            raise ReleaseError(f"development architecture is not customer payload: {relative}")
        validate_payload_path(relative)
        if relative in declared_by_path:
            raise ReleaseError(f"duplicate manifest path: {relative}")
        declared_by_path[relative] = item

    actual_records = file_records(root, exclude={MANIFEST_NAME})
    actual_by_path = {str(item["path"]): item for item in actual_records}
    if set(actual_by_path) != set(declared_by_path):
        missing = sorted(set(declared_by_path) - set(actual_by_path))
        extra = sorted(set(actual_by_path) - set(declared_by_path))
        raise ReleaseError(f"manifest membership mismatch; missing={missing}; extra={extra}")
    for relative, expected in declared_by_path.items():
        observed = actual_by_path[relative]
        if expected.get("bytes") != observed["bytes"] or expected.get("sha256") != observed["sha256"]:
            raise ReleaseError(f"manifest digest mismatch: {relative}")

    observed_tree = tree_sha256(root, actual_records)
    if manifest.get("file_count") != len(actual_records) or manifest.get("tree_sha256") != observed_tree:
        raise ReleaseError("manifest count or tree digest does not match release bytes")

    for forbidden in FORBIDDEN_MCP_PATHS:
        if forbidden in actual_by_path:
            raise ReleaseError(f"MCP payload is forbidden: {forbidden}")

    for relative in sorted(actual_by_path):
        path = root / Path(relative)
        if SECRET_NAME.search(path.name):
            raise ReleaseError(f"secret-like filename is not allowed: {relative}")
        if path.suffix.lower() in {".db", ".pyc", ".sqlite", ".sqlite3"}:
            raise ReleaseError(f"runtime data or cache is not allowed: {relative}")
        if path.suffix.lower() in TEXT_SUFFIXES and PRIVATE_PATH.search(path.read_bytes()):
            raise ReleaseError(f"absolute private workstation path found: {relative}")

    plugin = load_json(root / ".codex-plugin" / "plugin.json")
    if plugin.get("name") != PRODUCT or plugin.get("version") != PLUGIN_VERSION:
        raise ReleaseError("plugin manifest identity does not match the release")
    if "mcpServers" in plugin:
        raise ReleaseError("plugin manifest must not register MCP servers")
    skills = sorted((root / "skills").glob("*/SKILL.md"))
    if len(skills) != 20:
        raise ReleaseError(f"expected 20 skill entrypoints, found {len(skills)}")
    interface = plugin.get("interface")
    if not isinstance(interface, dict):
        raise ReleaseError("plugin interface metadata is missing")
    for key in ("composerIcon", "logo", "logoDark"):
        value = str(interface.get(key, "")).removeprefix("./")
        if not value or value not in actual_by_path:
            raise ReleaseError(f"plugin asset is missing: {key}")
    screenshots = interface.get("screenshots")
    if not isinstance(screenshots, list) or len(screenshots) != 2:
        raise ReleaseError("plugin must declare the hero and capability-card screenshots")
    for value in screenshots:
        relative = str(value).removeprefix("./")
        if relative not in actual_by_path:
            raise ReleaseError(f"plugin screenshot is missing: {relative}")

    if not (root / "hooks" / "hooks.json").is_file() or not (root / "hooks" / "mind_prompt_submit.py").is_file():
        raise ReleaseError("MIND prompt-submit hook payload is missing")

    marketplace = load_json(root / ".agents" / "plugins" / "marketplace.json")
    verify_marketplace(marketplace)

    wheel_paths = [path for path in actual_by_path if path.startswith("optional-core/") and path.endswith(".whl")]
    if len(wheel_paths) != 1:
        raise ReleaseError("release must contain exactly one optional Core wheel")
    wheel_metadata = verify_wheel(root, wheel_paths[0])
    verify_component_sums(root, wheel_paths[0])
    verify_markdown_links(root, set(actual_by_path))

    return {
        "ok": True,
        "format": MANIFEST_FORMAT,
        "product": PRODUCT,
        "plugin_version": PLUGIN_VERSION,
        "core_version": CORE_VERSION,
        "file_count": len(actual_records),
        "tree_sha256": observed_tree,
        "skill_count": len(skills),
        "wheel": wheel_metadata,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".", type=Path)
    args = parser.parse_args(argv)
    try:
        result = verify(args.root)
    except ReleaseError as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
