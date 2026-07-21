from __future__ import annotations

import argparse
import hashlib
import json
import stat
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath


sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "release"
EXPECTED = ("augment-of-mind", "nova-the-optimal-ai")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sanitize_text(value: str, replacements: dict[str, str]) -> str:
    for source, label in sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True):
        variants = {source, source.replace("\\", "/"), source.replace("\\", "\\\\")}
        for variant in variants:
            value = value.replace(variant, label)
    return value


def run(command: list[str], cwd: Path, replacements: dict[str, str]) -> dict:
    completed = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return {
        "command": [sanitize_text(item, replacements) for item in command],
        "exit_code": completed.returncode,
        "stdout": sanitize_text(completed.stdout.strip(), replacements),
        "stderr": sanitize_text(completed.stderr.strip(), replacements),
        "status": "passed" if completed.returncode == 0 else "failed",
    }


def safe_extract(archive_path: Path, destination: Path, expected_root: str) -> list[str]:
    extracted: list[str] = []
    with zipfile.ZipFile(archive_path, "r") as archive:
        if archive.testzip() is not None:
            raise ValueError(f"CRC failure in {archive_path.name}")
        for info in archive.infolist():
            member = PurePosixPath(info.filename)
            if member.is_absolute() or not member.parts or member.parts[0] != expected_root:
                raise ValueError(f"unsafe or unexpected archive root: {info.filename}")
            if any(part in {"", ".", ".."} for part in member.parts):
                raise ValueError(f"unsafe archive path: {info.filename}")
            mode = info.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise ValueError(f"symlink archive member: {info.filename}")
            target = destination.joinpath(*member.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(info))
            extracted.append(info.filename)
    return extracted


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the deterministic Nova + MIND release archives.")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    codex_home = Path.home() / ".codex"
    plugin_validator = codex_home / "skills" / ".system" / "plugin-creator" / "scripts" / "validate_plugin.py"
    skill_validator = codex_home / "skills" / ".system" / "skill-creator" / "scripts" / "quick_validate.py"
    package_validator = (
        ROOT / "plugins" / "nova-the-optimal-ai" / "skills" / "software-verification" / "scripts" / "verify_package.py"
    )
    required_tools = [plugin_validator, skill_validator, package_validator]
    missing_tools = [path.name for path in required_tools if not path.is_file()]
    receipt = json.loads((RELEASE / "release-receipt.json").read_text(encoding="utf-8"))
    receipt_archives = {record["plugin"]: record for record in receipt["archives"]}
    checksum_lines = (RELEASE / "SHA256SUMS").read_text(encoding="ascii").splitlines()
    checksums = {line.split(maxsplit=1)[1].strip(): line.split(maxsplit=1)[0] for line in checksum_lines if line.strip()}

    report = {
        "format": "nova-mind-extracted-release-validation/v1",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "target": "release/augment-of-mind-1.0.0.zip and release/nova-the-optimal-ai-1.0.0.zip",
        "validator_labels": {
            "plugin": "$CODEX_HOME/skills/.system/plugin-creator/scripts/validate_plugin.py",
            "skill": "$CODEX_HOME/skills/.system/skill-creator/scripts/quick_validate.py",
            "testforge": "plugins/nova-the-optimal-ai/skills/software-verification/scripts/verify_package.py",
        },
        "missing_validator_tools": missing_tools,
        "archives": [],
        "valid": False,
    }
    if missing_tools:
        rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
        print(rendered, end="")
        return 1

    all_valid = True
    with tempfile.TemporaryDirectory(prefix="nova-mind-release-validation-") as temporary:
        temporary_root = Path(temporary)
        replacements = {
            str(temporary_root): "<temporary-extraction>",
            str(plugin_validator): "<plugin-validator>",
            str(skill_validator): "<skill-validator>",
            str(package_validator): "<testforge-validator>",
            str(ROOT): "<contest-repository>",
            str(Path.home()): "<user-home>",
            str(Path(sys.executable)): "<python>",
        }
        for plugin in EXPECTED:
            archive_path = RELEASE / f"{plugin}-1.0.0.zip"
            expected_record = receipt_archives[plugin]
            archive_hash = sha256(archive_path)
            hash_valid = (
                archive_hash == expected_record["archive_sha256"]
                and archive_hash == checksums.get(archive_path.name)
            )
            extracted = safe_extract(archive_path, temporary_root, plugin)
            plugin_root = temporary_root / plugin
            plugin_check = run(
                [sys.executable, "-B", "-X", "utf8", str(plugin_validator), str(plugin_root)],
                ROOT,
                replacements,
            )
            skill_checks = []
            for skill_root in sorted((plugin_root / "skills").iterdir(), key=lambda path: path.name):
                if skill_root.is_dir():
                    check = run(
                        [sys.executable, "-B", "-X", "utf8", str(skill_validator), str(skill_root)],
                        ROOT,
                        replacements,
                    )
                    check["skill"] = skill_root.name
                    skill_checks.append(check)
            package_check = run(
                [sys.executable, "-B", "-X", "utf8", str(package_validator), str(plugin_root)],
                ROOT,
                replacements,
            )
            archive_valid = (
                hash_valid
                and len(extracted) == expected_record["member_count"]
                and plugin_check["status"] == "passed"
                and all(check["status"] == "passed" for check in skill_checks)
                and package_check["status"] == "passed"
            )
            all_valid = all_valid and archive_valid
            report["archives"].append(
                {
                    "plugin": plugin,
                    "archive": f"release/{archive_path.name}",
                    "sha256": archive_hash,
                    "hash_matches_receipt_and_checksums": hash_valid,
                    "members_extracted": len(extracted),
                    "expected_members": expected_record["member_count"],
                    "plugin_validator": plugin_check,
                    "skill_validators": skill_checks,
                    "testforge_validator": package_check,
                    "valid": archive_valid,
                }
            )

    report["valid"] = all_valid
    rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        destination = args.output if args.output.is_absolute() else ROOT / args.output
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if all_valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
