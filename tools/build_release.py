"""Build deterministic Codex, Claude, and customer-kit artifacts for Nova + MIND Free."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
RELEASE = ROOT / "release"
VERSION = "2.0.8"
KIT_NAME = f"nova-mind-free-v{VERSION}"
PLUGIN_NAMES = ("augment-of-mind", "nova-the-optimal-ai")
SKIP_NAMES = {".git", "__pycache__", ".pytest_cache"}
SKIP_SUFFIXES = {".pyc", ".pyo"}
FIXED_TIME = (2026, 8, 4, 0, 0, 0)
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


def source_state() -> tuple[str, int, str]:
    tracked_status = git_output("status", "--porcelain", "--untracked-files=no")
    if tracked_status:
        raise RuntimeError("tracked source changes must be committed before building the release")
    revision = git_output("rev-parse", "HEAD")
    if len(revision) != 40:
        raise RuntimeError("git did not return a full source revision")
    tracked = [item for item in git_output("ls-files", "-z").split("\0") if item]
    digest = hashlib.sha256()
    counted = 0
    for relative in sorted(tracked, key=str.casefold):
        source = ROOT / relative
        if not source.is_file():
            continue
        digest.update(relative.replace("\\", "/").encode("utf-8"))
        digest.update(b"\0")
        digest.update(bytes.fromhex(sha256(source)))
        digest.update(b"\n")
        counted += 1
    return revision, counted, digest.hexdigest()


def safe_remove(path: Path, expected_parent: Path) -> None:
    if not path.exists():
        return
    resolved = path.resolve()
    if resolved.parent != expected_parent.resolve():
        raise RuntimeError(f"refused removal outside expected parent: {resolved}")
    shutil.rmtree(resolved)


def ignore(directory: str, names: list[str]) -> set[str]:
    return {name for name in names if name in SKIP_NAMES or Path(name).suffix in SKIP_SUFFIXES}


def copytree(source: Path, target: Path) -> None:
    shutil.copytree(source, target, ignore=ignore, copy_function=shutil.copy2)


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
        help="replace only the existing dist tree and exact 2.0.8 release outputs",
    )
    args = parser.parse_args(argv)

    revision, source_file_count, source_digest = source_state()
    archive_output = RELEASE / f"{KIT_NAME}.zip"
    checksum_output = RELEASE / f"{KIT_NAME}.zip.sha256"
    receipt_output = RELEASE / f"{KIT_NAME}.build-receipt.json"
    existing = [path for path in (DIST, archive_output, checksum_output, receipt_output) if path.exists()]
    if existing and not args.replace:
        rendered = ", ".join(str(path.relative_to(ROOT)) for path in existing)
        raise RuntimeError(f"output exists; rerun with --replace for these exact targets: {rendered}")
    if DIST.exists():
        safe_remove(DIST, ROOT)
    for old in (archive_output, checksum_output, receipt_output):
        if old.exists():
            if old.resolve().parent != RELEASE.resolve() or not old.is_file():
                raise RuntimeError(f"refused replacement outside the release directory: {old}")
            old.unlink()
    DIST.mkdir()
    RELEASE.mkdir(exist_ok=True)

    codex = DIST / "codex"
    (codex / "plugins").mkdir(parents=True)
    copytree(ROOT / ".agents", codex / ".agents")
    for name in PLUGIN_NAMES:
        copytree(ROOT / "plugins" / name, codex / "plugins" / name)

    claude_folders = DIST / "claude" / "folders"
    claude_zips = DIST / "claude" / "zips"
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
        copytree(source, folder)
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

    docs_target = DIST / "docs"
    copytree(ROOT / "docs", docs_target)
    for name in ("README.md", "START-HERE.md", "RELEASE-NOTES.md", "SUPPORT.md", "SECURITY.md", "LICENSE.md", "install.ps1", "verify-install.ps1"):
        shutil.copy2(ROOT / name, DIST / name)
    packaged_readme = DIST / "README.md"
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
    (DIST / "assets").mkdir()
    shutil.copy2(ROOT / "assets" / "nova-emergent.png", DIST / "assets" / "nova-emergent.png")
    (DIST / "bundle").mkdir()
    copytree(ROOT / "bundle" / "reminder", DIST / "bundle" / "reminder")

    manifest = {
        "format": "nova-mind-free-release/v1",
        "product": "Nova + MIND Free",
        "version": VERSION,
        "source_revision": revision,
        "source_material_file_count": source_file_count,
        "source_material_sha256": source_digest,
        "plugin_versions": {"nova-the-optimal-ai": "2.0.1", "augment-of-mind": "2.1.6"},
        "codex_plugins": list(PLUGIN_NAMES),
        "claude_skill_count": len(sources),
        "claude_skills": sorted(sources),
        "mind_faculty_count": 16,
        "mind_attached_testforge_count": 2,
        "reminder_capability_count": 41,
        "reminder_qualification_state": "unqualified",
        "evidence_boundary": "Structural release artifact. Live installation, hook trust, host delivery, behavioral qualification, Claude upload, publication, and commercial approval remain separate.",
    }
    (DIST / "release-manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    checksum_targets = [
        *sorted(claude_zips.glob("*.zip")),
        DIST / "release-manifest.json",
        DIST / "codex" / "plugins" / "nova-the-optimal-ai" / ".codex-plugin" / "plugin.json",
        DIST / "codex" / "plugins" / "augment-of-mind" / ".codex-plugin" / "plugin.json",
        DIST / "bundle" / "reminder" / "associative-index-qwen3-embedding-0.6b.json",
    ]
    checksum_lines = [f"{sha256(path)}  {path.relative_to(DIST).as_posix()}" for path in checksum_targets]
    (DIST / "SHA256SUMS.txt").write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")

    write_zip(DIST, archive_output, KIT_NAME)
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
        "structural_builder": "PASS",
        "evidence_boundary": "Source custody and structural package construction only; live host behavior remains separate.",
    }
    receipt_output.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps({
        "status": "PASS",
        "codex_plugins": len(PLUGIN_NAMES),
        "claude_skills": len(sources),
        "source_revision": revision,
        "customer_zip": str(archive_output.relative_to(ROOT)),
        "customer_zip_sha256": release_hash,
        "build_receipt": str(receipt_output.relative_to(ROOT)),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
