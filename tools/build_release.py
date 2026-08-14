"""Build deterministic Codex, Claude, and customer-kit artifacts for Nova + MIND Free."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import zipfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "2.1.1"
KIT_NAME = f"nova-mind-free-v{VERSION}"
PLUGIN_NAMES = ("augment-of-mind", "nova-the-optimal-ai")
SKIP_NAMES = {".git", "__pycache__", ".pytest_cache"}
SKIP_SUFFIXES = {".pyc", ".pyo"}
PACKAGED_DIRECTORIES = (
    ".agents",
    "plugins/augment-of-mind",
    "plugins/nova-the-optimal-ai",
    "docs",
    "bundle/reminder",
)
PACKAGED_FILES = (
    "design/FREE-NOVA-PACKAGE-MAP.md",
    "design/source-lock.json",
    "README.md",
    "START-HERE.md",
    "RELEASE-NOTES.md",
    "SUPPORT.md",
    "SECURITY.md",
    "LICENSE.md",
    "install.ps1",
    "verify-install.ps1",
    "assets/nova-emergent.png",
)
FIXED_TIME = (2026, 8, 13, 0, 0, 0)
CLAUDE_DESCRIPTIONS = {
    "answerlayer": "🔄 Answer maintenance as evidence changes.",
    "current-intelligence-observatory": "🛰️ Current intelligence and change tracking.",
    "ludis-continuum": "🎲 Choice-shaped games and fiction continuity.",
    "signal-loom": "📊 Evidence-to-visual story design.",
    "agentic-eros": "🔥 Adult erotic-relational intelligence.",
    "software-verification": "☠️ Adversarial software release verification.",
}

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def windows_stable_ordinal_key(relative: str) -> tuple[str, str]:
    """Return a locale-free Windows ordering with an exact-case tie-break."""
    return relative.casefold(), relative


def reproducibility_environment() -> dict[str, object]:
    """Describe build-affecting runtime details without host or user identity."""
    return {
        "python": {
            "implementation": platform.python_implementation(),
            "version": platform.python_version(),
        },
        "zlib": {
            "compile_version": zlib.ZLIB_VERSION,
            "runtime_version": zlib.ZLIB_RUNTIME_VERSION,
        },
        "platform": {
            "os_name": os.name,
            "sys_platform": sys.platform,
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
        },
    }


def git_output(*arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(ROOT), *arguments],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise RuntimeError(f"Git command failed: {result.stderr.strip()}")
    return result.stdout.strip()


def git_batch_output(arguments: tuple[str, ...], lines: list[str]) -> list[str]:
    if any("\n" in line or "\r" in line for line in lines):
        raise RuntimeError("tracked paths with line breaks are not supported")
    result = subprocess.run(
        ["git", "-C", str(ROOT), *arguments],
        check=False,
        capture_output=True,
        input="".join(f"{line}\n" for line in lines),
        text=True,
        encoding="utf-8",
    )
    if result.returncode:
        raise RuntimeError(f"Git command failed: {result.stderr.strip()}")
    return result.stdout.splitlines()


def _skipped(path: Path) -> bool:
    return any(part in SKIP_NAMES for part in path.parts) or path.suffix in SKIP_SUFFIXES


def _assert_payload_is_tracked(tracked: set[str]) -> None:
    selected: list[Path] = []
    for relative in PACKAGED_DIRECTORIES:
        source = ROOT / relative
        if not source.is_dir():
            raise RuntimeError(f"packaged source directory is missing: {source}")
        selected.extend(path for path in source.rglob("*") if path.is_file() and not _skipped(path.relative_to(ROOT)))
    for relative in PACKAGED_FILES:
        source = ROOT / relative
        if not source.is_file():
            raise RuntimeError(f"packaged source file is missing: {source}")
        selected.append(source)
    untracked = sorted(
        path.relative_to(ROOT).as_posix()
        for path in selected
        if path.relative_to(ROOT).as_posix() not in tracked
    )
    if untracked:
        rendered = ", ".join(untracked[:8])
        suffix = " ..." if len(untracked) > 8 else ""
        raise RuntimeError(
            "packaged payload contains files not bound to the Git revision: "
            + rendered
            + suffix
        )


def _assert_tracked_bytes_match_revision(tracked: set[str], revision: str) -> None:
    paths = sorted(tracked, key=windows_stable_ordinal_key)
    worktree_ids = git_batch_output(
        ("hash-object", "--no-filters", "--stdin-paths"),
        paths,
    )
    revision_ids = git_batch_output(
        ("cat-file", "--batch-check=%(objectname)"),
        [f"{revision}:{relative}" for relative in paths],
    )
    if len(worktree_ids) != len(paths) or len(revision_ids) != len(paths):
        raise RuntimeError("Git byte-parity scan returned an incomplete result")
    mismatches = [
        relative
        for relative, worktree_id, revision_id in zip(paths, worktree_ids, revision_ids)
        if worktree_id != revision_id
    ]
    if mismatches:
        rendered = ", ".join(mismatches[:8])
        suffix = " ..." if len(mismatches) > 8 else ""
        raise RuntimeError(
            "raw tracked worktree bytes differ from the committed revision: "
            + rendered
            + suffix
        )


def source_state() -> tuple[str, int, str, set[str]]:
    tracked_status = git_output("status", "--porcelain", "--untracked-files=no")
    if tracked_status:
        raise RuntimeError("tracked source changes must be committed before building the release")
    revision = git_output("rev-parse", "HEAD")
    if len(revision) != 40:
        raise RuntimeError("git did not return a full source revision")
    tracked = {item.replace("\\", "/") for item in git_output("ls-files", "-z").split("\0") if item}
    _assert_payload_is_tracked(tracked)
    _assert_tracked_bytes_match_revision(tracked, revision)
    digest = hashlib.sha256()
    counted = 0
    for relative in sorted(tracked, key=windows_stable_ordinal_key):
        source = ROOT / relative
        if not source.is_file():
            continue
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(bytes.fromhex(sha256(source)))
        digest.update(b"\n")
        counted += 1
    return revision, counted, digest.hexdigest(), tracked


def validate_output_root(path: Path) -> None:
    anchor = Path(path.anchor).resolve()
    if path.resolve() == anchor:
        raise RuntimeError(f"output root may not be a filesystem root: {path}")


def safe_remove(path: Path, expected_parent: Path) -> None:
    if not path.exists():
        return
    resolved = path.resolve()
    if resolved.parent != expected_parent.resolve():
        raise RuntimeError(f"refused removal outside expected parent: {resolved}")
    shutil.rmtree(resolved)


def require_same_release(dist: Path) -> None:
    manifest_path = dist / "release-manifest.json"
    if not manifest_path.is_file():
        raise RuntimeError(
            f"refused to replace an unrecognized dist tree: {dist}; use a new --output-root"
        )
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"refused to replace invalid dist manifest: {manifest_path}") from exc
    if manifest.get("version") != VERSION:
        raise RuntimeError(
            f"refused to replace dist version {manifest.get('version')!r} with {VERSION}; "
            "use a new version-scoped --output-root"
        )


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def copytree(source: Path, target: Path, tracked: set[str]) -> None:
    if target.exists():
        raise RuntimeError(f"refused to copy into an existing target: {target}")
    source_relative = source.relative_to(ROOT).as_posix()
    prefix = source_relative + "/"
    selected = sorted(
        relative
        for relative in tracked
        if relative.startswith(prefix) and not _skipped(Path(relative))
    )
    if not selected:
        raise RuntimeError(f"packaged source directory has no tracked files: {source}")
    target.mkdir(parents=True)
    for relative in selected:
        source_file = ROOT / relative
        if not source_file.is_file():
            raise RuntimeError(f"tracked packaged source is missing: {source_file}")
        destination = target / source_file.relative_to(source)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_file, destination)


def write_zip(source: Path, archive: Path, top_level: str) -> None:
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for path in sorted(source.rglob("*"), key=lambda item: item.relative_to(source).as_posix()):
            if not path.is_file() or path.name in SKIP_NAMES or path.suffix in SKIP_SUFFIXES:
                continue
            relative = Path(top_level) / path.relative_to(source)
            info = zipfile.ZipInfo(relative.as_posix(), FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            bundle.writestr(info, path.read_bytes())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--replace",
        action="store_true",
        help=f"replace only an existing {VERSION} dist tree and exact {VERSION} release outputs",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        help="write dist/ and release/ below a new version-scoped root (recommended for candidate builds)",
    )
    args = parser.parse_args(argv)

    revision, source_file_count, source_digest, tracked = source_state()
    output_root = args.output_root.expanduser().resolve() if args.output_root else ROOT
    validate_output_root(output_root)
    dist = output_root / "dist"
    release = output_root / "release"
    archive_output = release / f"{KIT_NAME}.zip"
    checksum_output = release / f"{KIT_NAME}.zip.sha256"
    receipt_output = release / f"{KIT_NAME}.build-receipt.json"
    existing = [path for path in (dist, archive_output, checksum_output, receipt_output) if path.exists()]
    if existing and not args.replace:
        rendered = ", ".join(display_path(path) for path in existing)
        raise RuntimeError(f"output exists; rerun with --replace for these exact targets: {rendered}")
    if dist.exists():
        require_same_release(dist)
        safe_remove(dist, output_root)
    for old in (archive_output, checksum_output, receipt_output):
        if old.exists():
            if old.resolve().parent != release.resolve() or not old.is_file():
                raise RuntimeError(f"refused replacement outside the release directory: {old}")
            old.unlink()
    dist.mkdir(parents=True)
    release.mkdir(parents=True, exist_ok=True)

    codex = dist / "codex"
    (codex / "plugins").mkdir(parents=True)
    copytree(ROOT / ".agents", codex / ".agents", tracked)
    for name in PLUGIN_NAMES:
        copytree(ROOT / "plugins" / name, codex / "plugins" / name, tracked)

    claude_folders = dist / "claude" / "folders"
    claude_zips = dist / "claude" / "zips"
    claude_folders.mkdir(parents=True)
    claude_zips.mkdir(parents=True)
    sources: dict[str, Path] = {}
    for plugin in PLUGIN_NAMES:
        for skill in sorted((ROOT / "plugins" / plugin / "skills").iterdir()):
            if not skill.is_dir():
                continue
            if skill.name in sources:
                raise RuntimeError(f"duplicate skill handle across plugins: {skill.name}")
            if not (skill / "SKILL.md").is_file():
                raise RuntimeError(f"skill root lacks SKILL.md: {skill}")
            sources[skill.name] = skill
    for name, source in sorted(sources.items()):
        folder = claude_folders / name
        copytree(source, folder, tracked)
        if name in CLAUDE_DESCRIPTIONS:
            entry = folder / "SKILL.md"
            content = entry.read_text(encoding="utf-8")
            content, count = __import__("re").subn(
                r"(?m)^description:\s*.*$",
                f'description: "{CLAUDE_DESCRIPTIONS[name]}"',
                content,
                count=1,
            )
            if count != 1:
                raise RuntimeError(f"could not derive Claude description: {name}")
            entry.write_text(content, encoding="utf-8", newline="\n")
        write_zip(folder, claude_zips / f"{name}.zip", name)

    docs_target = dist / "docs"
    copytree(ROOT / "docs", docs_target, tracked)
    design_target = dist / "design"
    design_target.mkdir()
    for name in ("FREE-NOVA-PACKAGE-MAP.md", "source-lock.json"):
        shutil.copy2(ROOT / "design" / name, design_target / name)
    for name in ("README.md", "START-HERE.md", "RELEASE-NOTES.md", "SUPPORT.md", "SECURITY.md", "LICENSE.md", "install.ps1", "verify-install.ps1"):
        shutil.copy2(ROOT / name, dist / name)
    packaged_readme = dist / "README.md"
    source_mind_link = "plugins/augment-of-mind/USER-GUIDE.md"
    packaged_mind_link = "codex/plugins/augment-of-mind/USER-GUIDE.md"
    packaged_readme_text = packaged_readme.read_text(encoding="utf-8")
    if packaged_readme_text.count(source_mind_link) != 1:
        raise RuntimeError("could not derive the packaged MIND guide link")
    packaged_readme.write_text(
        packaged_readme_text.replace(source_mind_link, packaged_mind_link),
        encoding="utf-8",
        newline="\n",
    )
    (dist / "assets").mkdir()
    shutil.copy2(ROOT / "assets" / "nova-emergent.png", dist / "assets" / "nova-emergent.png")
    (dist / "bundle").mkdir()
    copytree(ROOT / "bundle" / "reminder", dist / "bundle" / "reminder", tracked)

    manifest = {
        "format": "nova-mind-free-release/v1",
        "product": "Nova + MIND Free",
        "version": VERSION,
        "source_revision": revision,
        "source_material_file_count": source_file_count,
        "source_material_sha256": source_digest,
        "plugin_versions": {"nova-the-optimal-ai": "2.1.0", "augment-of-mind": "2.2.1"},
        "codex_plugins": list(PLUGIN_NAMES),
        "claude_skill_count": len(sources),
        "claude_skills": sorted(sources),
        "mind_faculty_count": 16,
        "mind_attached_testforge_count": 2,
        "reminder_capability_count": 41,
        "reminder_qualification_state": "unqualified",
        "evidence_boundary": "Structural release artifact. Live installation, hook trust, host delivery, behavioral qualification, Claude upload, publication, and commercial approval remain separate.",
    }
    (dist / "release-manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    checksum_targets = [
        *sorted(claude_zips.glob("*.zip")),
        dist / "release-manifest.json",
        dist / "codex" / "plugins" / "nova-the-optimal-ai" / ".codex-plugin" / "plugin.json",
        dist / "codex" / "plugins" / "augment-of-mind" / ".codex-plugin" / "plugin.json",
        dist / "bundle" / "reminder" / "associative-index-qwen3-embedding-0.6b.json",
    ]
    checksum_lines = [f"{sha256(path)}  {path.relative_to(dist).as_posix()}" for path in checksum_targets]
    (dist / "SHA256SUMS.txt").write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")

    write_zip(dist, archive_output, KIT_NAME)
    release_hash = sha256(archive_output)
    checksum_output.write_text(f"{release_hash}  {KIT_NAME}.zip\n", encoding="utf-8")
    receipt = {
        "format": "nova-mind-free-build-receipt/v1",
        "product": "Nova + MIND Free",
        "version": VERSION,
        "source_revision": revision,
        "source_material_file_count": source_file_count,
        "source_material_sha256": source_digest,
        "archive": {
            "name": archive_output.name,
            "bytes": archive_output.stat().st_size,
            "sha256": release_hash,
            "top_level": KIT_NAME,
        },
        "reproducibility_environment": reproducibility_environment(),
        "structural_builder": "PASS",
        "evidence_boundary": "Source custody and structural package construction only; live host behavior remains separate.",
    }
    receipt_output.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps({
        "status": "PASS",
        "codex_plugins": len(PLUGIN_NAMES),
        "claude_skills": len(sources),
        "source_revision": revision,
        "customer_zip": display_path(archive_output),
        "customer_zip_sha256": release_hash,
        "build_receipt": display_path(receipt_output),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
