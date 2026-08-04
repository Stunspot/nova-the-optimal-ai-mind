#!/usr/bin/env python3
"""Build the deterministic, allowlisted MIND customer archive."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from importlib import metadata as importlib_metadata
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import sys
import tempfile
import tomllib
import zipfile

from verify_release import (
    ARCHIVE_ROOT,
    ASSET_NAMES,
    CORE_VERSION,
    MANIFEST_FORMAT,
    MANIFEST_NAME,
    PLUGIN_VERSION,
    PRODUCT,
    ROOT_DOCUMENTS,
    RUNTIME_SCRIPT_NAMES,
    SKILL_ALLOWED_DIRECTORIES,
    SKILL_ALLOWED_ROOT_FILES,
    SKILL_EXCLUDED_FILES,
    SKILL_EXCLUDED_SEGMENTS,
    file_records,
    sha256_file,
    tree_sha256,
    verify,
)


FIXED_ZIP_TIME = (2026, 1, 1, 0, 0, 0)
SOURCE_DATE_EPOCH = "1767225600"


class BuildError(RuntimeError):
    """Raised when the release cannot be constructed honestly."""


def run(command: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        encoding="utf-8",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if completed.returncode:
        rendered = " ".join(command)
        raise BuildError(f"command failed ({completed.returncode}): {rendered}\n{completed.stdout}")
    return completed.stdout


def source_material_sha256(repo: Path, paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda item: item.relative_to(repo).as_posix()):
        relative = path.relative_to(repo).as_posix().encode("utf-8")
        data = path.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.hexdigest()


def source_revision(repo: Path, selected_sources: list[Path]) -> tuple[str, str]:
    revision = run(["git", "rev-parse", "HEAD"], cwd=repo).strip()
    if len(revision) != 40:
        raise BuildError("git did not return a full source revision")
    tracked_status = run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=repo).strip()
    if tracked_status:
        raise BuildError("tracked source changes must be committed before building the release")
    tracked = set(run(["git", "ls-files", "-z"], cwd=repo).split("\0"))
    untracked_selected = sorted(
        path.relative_to(repo).as_posix()
        for path in selected_sources
        if path.relative_to(repo).as_posix() not in tracked
    )
    if untracked_selected:
        raise BuildError(f"selected release sources are not tracked by the source revision: {untracked_selected}")
    return revision, source_material_sha256(repo, selected_sources)


def validate_versions(repo: Path) -> None:
    plugin = json.loads((repo / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    project = tomllib.loads((repo / "pyproject.toml").read_text(encoding="utf-8"))
    if plugin.get("name") != PRODUCT or plugin.get("version") != PLUGIN_VERSION:
        raise BuildError("plugin manifest version does not match the release builder")
    if "mcpServers" in plugin:
        raise BuildError("plugin manifest must not register MCP servers")
    package = project.get("project", {})
    if package.get("name") != "cd-mind-core" or package.get("version") != CORE_VERSION:
        raise BuildError("Core project version does not match the release builder")


def copy_regular(source: Path, target: Path) -> None:
    if source.is_symlink() or not source.is_file():
        raise BuildError(f"allowlisted source is not a regular file: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


def skill_release_files(source: Path) -> list[Path]:
    if source.is_symlink() or not source.is_dir():
        raise BuildError(f"skills source is not a directory: {source}")
    selected: list[Path] = []
    for skill in sorted(source.iterdir()):
        if skill.is_symlink() or not skill.is_dir():
            raise BuildError(f"unexpected item at skills root: {skill}")
        if not (skill / "SKILL.md").is_file():
            raise BuildError(f"skill is missing SKILL.md: {skill.name}")
        for path in sorted(skill.rglob("*")):
            if path.is_symlink():
                raise BuildError(f"symlink is not allowed in skill source: {path}")
            if not path.is_file():
                continue
            relative = path.relative_to(source)
            inner = relative.parts[1:]
            if relative.as_posix() in SKILL_EXCLUDED_FILES:
                continue
            if any(segment in SKILL_EXCLUDED_SEGMENTS for segment in inner):
                continue
            if path.suffix.lower() in {".pyc", ".pyo"}:
                continue
            if len(inner) == 1 and inner[0] in SKILL_ALLOWED_ROOT_FILES:
                selected.append(path)
                continue
            if len(inner) >= 2 and inner[0] in SKILL_ALLOWED_DIRECTORIES:
                selected.append(path)
                continue
            raise BuildError(f"unclassified skill content requires a release decision: {relative.as_posix()}")
    return selected


def core_source_files(repo: Path) -> list[Path]:
    source = repo / "mind_core"
    selected: list[Path] = []
    for path in sorted(source.rglob("*")):
        if path.is_symlink():
            raise BuildError(f"symlink is not allowed in Core source: {path}")
        if not path.is_file():
            continue
        relative = path.relative_to(source)
        if any(segment in {"__pycache__", ".pytest_cache"} for segment in relative.parts):
            continue
        if path.suffix.lower() in {".pyc", ".pyo"}:
            continue
        if path.suffix.lower() not in {".py", ".sql"}:
            raise BuildError(f"unclassified Core content requires a release decision: {relative.as_posix()}")
        selected.append(path)
    if not selected:
        raise BuildError("Core source selection is empty")
    return selected


def copy_core_source(repo: Path, root: Path) -> None:
    for path in core_source_files(repo):
        copy_regular(path, root / path.relative_to(repo))


def selected_source_files(repo: Path) -> list[Path]:
    paths = [
        repo / ".codex-plugin" / "plugin.json",
        repo / ".agents" / "plugins" / "marketplace.json",
        repo / "pyproject.toml",
        repo / "scripts" / "build_release.py",
        repo / "scripts" / "verify_release.py",
    ]
    paths.extend(repo / "scripts" / name for name in RUNTIME_SCRIPT_NAMES)
    paths.extend((repo / "hooks" / "hooks.json", repo / "hooks" / "mind_prompt_submit.py"))
    paths.extend(skill_release_files(repo / "skills"))
    paths.extend(repo / "assets" / name for name in ASSET_NAMES)
    paths.extend(repo / name for name in ROOT_DOCUMENTS)
    paths.extend(core_source_files(repo))
    unique = {path.resolve(): path for path in paths}
    selected = sorted(unique.values(), key=lambda item: item.relative_to(repo).as_posix())
    missing = [path for path in selected if not path.is_file() or path.is_symlink()]
    if missing:
        raise BuildError(f"selected release source is missing or not regular: {missing}")
    return selected


def copy_selected_skills(source: Path, target: Path) -> None:
    for path in skill_release_files(source):
        copy_regular(path, target / path.relative_to(source))


def build_wheel(repo: Path, destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env.update(
        {
            "SOURCE_DATE_EPOCH": SOURCE_DATE_EPOCH,
            "PYTHONHASHSEED": "0",
            "PIP_DISABLE_PIP_VERSION_CHECK": "1",
            "PIP_NO_INDEX": "1",
        }
    )
    run(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            "--no-deps",
            "--no-build-isolation",
            "--no-cache-dir",
            "--wheel-dir",
            str(destination),
            str(repo),
        ],
        cwd=repo,
        env=env,
    )
    wheels = sorted(destination.glob("*.whl"))
    if len(wheels) != 1:
        raise BuildError(f"expected one Core wheel, found {len(wheels)}")
    return wheels[0]


def stage_release(
    repo: Path,
    root: Path,
    wheel: Path,
    revision: str,
    source_digest: str,
) -> dict[str, object]:
    copy_regular(repo / ".codex-plugin" / "plugin.json", root / ".codex-plugin" / "plugin.json")
    copy_regular(repo / "hooks" / "hooks.json", root / "hooks" / "hooks.json")
    copy_regular(repo / "hooks" / "mind_prompt_submit.py", root / "hooks" / "mind_prompt_submit.py")
    copy_core_source(repo, root)
    copy_regular(
        repo / ".agents" / "plugins" / "marketplace.json",
        root / ".agents" / "plugins" / "marketplace.json",
    )
    copy_selected_skills(repo / "skills", root / "skills")
    for name in ASSET_NAMES:
        copy_regular(repo / "assets" / name, root / "assets" / name)
    for name in ROOT_DOCUMENTS:
        copy_regular(repo / name, root / name)
    copy_regular(repo / "scripts" / "verify_release.py", root / "verify-release.py")
    for name in RUNTIME_SCRIPT_NAMES:
        copy_regular(repo / "scripts" / name, root / "scripts" / name)
    wheel_target = root / "optional-core" / wheel.name
    copy_regular(wheel, wheel_target)
    wheel_relative = wheel_target.relative_to(root).as_posix()
    (root / "COMPONENT-SHA256SUMS.txt").write_text(
        f"{sha256_file(wheel_target)}  {wheel_relative}\n",
        encoding="utf-8",
        newline="\n",
    )

    records = file_records(root, exclude={MANIFEST_NAME})
    manifest = {
        "format": MANIFEST_FORMAT,
        "product": PRODUCT,
        "plugin_version": PLUGIN_VERSION,
        "core_version": CORE_VERSION,
        "archive_root": ARCHIVE_ROOT,
        "source_revision": revision,
        "source_material_sha256": source_digest,
        "manifest_scope": f"All customer files except {MANIFEST_NAME} itself",
        "file_count": len(records),
        "tree_sha256": tree_sha256(root, records),
        "files": records,
    }
    (root / MANIFEST_NAME).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return manifest


def build_zip(root: Path, output: Path) -> None:
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        archive.comment = b""
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            relative = path.relative_to(root).as_posix()
            info = zipfile.ZipInfo(PurePosixPath(ARCHIVE_ROOT, relative).as_posix(), FIXED_ZIP_TIME)
            info.create_system = 3
            info.create_version = 20
            info.extract_version = 20
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            info.internal_attr = 0
            info.extra = b""
            info.comment = b""
            archive.writestr(info, path.read_bytes())


def safe_extract(archive_path: Path, destination: Path) -> Path:
    with zipfile.ZipFile(archive_path) as archive:
        members = archive.infolist()
        names = [member.filename for member in members]
        if not members:
            raise BuildError("archive is empty")
        if len(names) != len(set(names)):
            raise BuildError("archive contains duplicate member names")
        for member in members:
            name = member.filename
            if not name or "\\" in name or not name.startswith(f"{ARCHIVE_ROOT}/"):
                raise BuildError(f"unsafe archive member: {name!r}")
            path = PurePosixPath(name)
            if (
                path.is_absolute()
                or ".." in path.parts
                or len(path.parts) < 2
                or path.parts[0] != ARCHIVE_ROOT
                or member.is_dir()
            ):
                raise BuildError(f"unsafe archive member: {name}")
            file_type = (member.external_attr >> 16) & 0o170000
            if member.create_system == 3 and file_type not in {0, stat.S_IFREG}:
                raise BuildError(f"non-regular archive member: {name}")
        archive.extractall(destination)
    return destination / ARCHIVE_ROOT


def compare_trees(expected: Path, observed: Path) -> None:
    expected_records = file_records(expected)
    observed_records = file_records(observed)
    expected_map = {str(item["path"]): item["sha256"] for item in expected_records}
    observed_map = {str(item["path"]): item["sha256"] for item in observed_records}
    if expected_map != observed_map:
        raise BuildError("extracted archive tree does not match staged release bytes")


def ensure_targets(paths: list[Path], replace: bool) -> None:
    existing = [path for path in paths if path.exists()]
    if existing and not replace:
        rendered = ", ".join(path.name for path in existing)
        raise BuildError(f"output exists; use --replace for these exact targets: {rendered}")
    for path in existing:
        if not path.is_file():
            raise BuildError(f"refusing to replace a non-file output: {path}")
        path.unlink()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("dist"))
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args(argv)

    repo = Path(__file__).resolve().parent.parent
    output_dir = args.output_dir.resolve()
    archive_output = output_dir / f"{ARCHIVE_ROOT}.zip"
    checksum_output = output_dir / f"{ARCHIVE_ROOT}.zip.sha256"
    receipt_output = output_dir / f"{ARCHIVE_ROOT}.build-receipt.json"
    targets = [archive_output, checksum_output, receipt_output]

    try:
        validate_versions(repo)
        selected_sources = selected_source_files(repo)
        revision, source_digest = source_revision(repo, selected_sources)
        output_dir.mkdir(parents=True, exist_ok=True)
        ensure_targets(targets, args.replace)
        with tempfile.TemporaryDirectory(prefix="mind-release-") as temporary:
            work = Path(temporary)
            wheel_a = build_wheel(repo, work / "wheel-a")
            wheel_b = build_wheel(repo, work / "wheel-b")
            wheel_sha256 = sha256_file(wheel_a)
            if wheel_a.name != wheel_b.name or wheel_sha256 != sha256_file(wheel_b):
                raise BuildError("two fixed-source-date Core wheel builds were not byte-identical")

            release_root = work / ARCHIVE_ROOT
            release_root.mkdir()
            manifest = stage_release(repo, release_root, wheel_a, revision, source_digest)
            staged_verification = verify(release_root)
            candidate_zip = work / "archive-a" / archive_output.name
            candidate_zip.parent.mkdir()
            comparison_zip = work / "archive-b" / archive_output.name
            comparison_zip.parent.mkdir()
            build_zip(release_root, candidate_zip)
            build_zip(release_root, comparison_zip)
            archive_sha256 = sha256_file(candidate_zip)
            if archive_sha256 != sha256_file(comparison_zip) or candidate_zip.read_bytes() != comparison_zip.read_bytes():
                raise BuildError("two archive builds from the staged tree were not byte-identical")
            extracted_root = safe_extract(candidate_zip, work / "extracted")
            extracted_verification = verify(extracted_root)
            compare_trees(release_root, extracted_root)

            shutil.copyfile(candidate_zip, archive_output)
            checksum_output.write_text(
                f"{archive_sha256}  {archive_output.name}\n",
                encoding="utf-8",
                newline="\n",
            )
            receipt = {
                "format": "cd-mind-release-build-receipt/v1",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "product": PRODUCT,
                "plugin_version": PLUGIN_VERSION,
                "core_version": CORE_VERSION,
                "source_revision": revision,
                "source_material": {
                    "file_count": len(selected_sources),
                    "sha256": source_digest,
                },
                "build_environment": {
                    "python": sys.version,
                    "setuptools": importlib_metadata.version("setuptools"),
                    "determinism_scope": "same selected source bytes and qualified build environment",
                },
                "archive": {
                    "name": archive_output.name,
                    "bytes": archive_output.stat().st_size,
                    "sha256": archive_sha256,
                    "top_level": ARCHIVE_ROOT,
                    "reproducible_rebuild": True,
                },
                "wheel": {
                    "name": wheel_a.name,
                    "sha256": wheel_sha256,
                    "reproducible_rebuild": True,
                },
                "manifest": {
                    "file_count": manifest["file_count"],
                    "tree_sha256": manifest["tree_sha256"],
                },
                "verification": {
                    "staged": staged_verification,
                    "extracted": extracted_verification,
                    "tree_comparison": "PASS",
                },
            }
            receipt_output.write_text(
                json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
                newline="\n",
            )
        print(json.dumps(receipt, ensure_ascii=False, indent=2))
        return 0
    except (BuildError, OSError, ValueError, json.JSONDecodeError, zipfile.BadZipFile) as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
