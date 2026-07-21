from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
MARKETPLACE = "collaborative-dynamics-build-week"
VERSION = "1.0.0"
EXPECTED = {
    "augment-of-mind": 16,
    "nova-the-optimal-ai": 12,
}


def codex_command() -> list[str]:
    if os.name == "nt":
        script = shutil.which("codex.ps1")
        powershell = shutil.which("powershell.exe")
        if script and powershell:
            return [powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", script]
    resolved = shutil.which("codex")
    if resolved:
        return [resolved]
    raise FileNotFoundError("Codex CLI executable is not available")


def run(arguments: list[str], environment: dict[str, str]) -> tuple[subprocess.CompletedProcess[str], dict | None]:
    completed = subprocess.run(
        [*codex_command(), *arguments],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    try:
        parsed = json.loads(completed.stdout)
    except json.JSONDecodeError:
        parsed = None
    return completed, parsed


def file_hashes(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        result[path.relative_to(root).as_posix()] = digest
    return result


def command_record(label: str, completed: subprocess.CompletedProcess[str], parsed: dict | None) -> dict:
    return {
        "command": label,
        "exit_code": completed.returncode,
        "json_output": parsed is not None,
        "stderr_sha256": hashlib.sha256(completed.stderr.encode("utf-8")).hexdigest(),
        "status": "passed" if completed.returncode == 0 and parsed is not None else "failed",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Install Nova + MIND into a temporary empty Codex home.")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    commands: list[dict] = []
    plugins: list[dict] = []
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="nova-mind-clean-codex-home-") as temporary:
        clean_home = Path(temporary)
        environment = os.environ.copy()
        environment["CODEX_HOME"] = str(clean_home)

        add_marketplace, marketplace_json = run(["plugin", "marketplace", "add", str(ROOT), "--json"], environment)
        commands.append(command_record("codex plugin marketplace add <repository> --json", add_marketplace, marketplace_json))
        for plugin in EXPECTED:
            completed, parsed = run(["plugin", "add", f"{plugin}@{MARKETPLACE}", "--json"], environment)
            commands.append(command_record(f"codex plugin add {plugin}@{MARKETPLACE} --json", completed, parsed))
        listed, listed_json = run(["plugin", "list", "--json"], environment)
        commands.append(command_record("codex plugin list --json", listed, listed_json))

        installed_by_id = {
            item.get("pluginId"): item for item in (listed_json or {}).get("installed", [])
        }
        for plugin, expected_skill_count in EXPECTED.items():
            plugin_id = f"{plugin}@{MARKETPLACE}"
            record = installed_by_id.get(plugin_id)
            source = ROOT / "plugins" / plugin
            cache = clean_home / "plugins" / "cache" / MARKETPLACE / plugin / VERSION
            source_files = file_hashes(source)
            cache_files = file_hashes(cache) if cache.is_dir() else {}
            skill_roots = (
                sorted(path.name for path in (cache / "skills").iterdir() if path.is_dir() and (path / "SKILL.md").is_file())
                if (cache / "skills").is_dir()
                else []
            )
            plugin_errors: list[str] = []
            if record is None:
                plugin_errors.append("selector missing from clean-home plugin list")
            else:
                if record.get("version") != VERSION:
                    plugin_errors.append("version mismatch")
                if record.get("enabled") is not True:
                    plugin_errors.append("plugin not enabled")
            if len(skill_roots) != expected_skill_count:
                plugin_errors.append("skill count mismatch")
            if source_files != cache_files:
                plugin_errors.append("installed cache differs from source")
            errors.extend(f"{plugin}: {error}" for error in plugin_errors)
            plugins.append(
                {
                    "plugin_id": plugin_id,
                    "version": record.get("version") if record else None,
                    "enabled": record.get("enabled") if record else None,
                    "skill_count": len(skill_roots),
                    "skills": skill_roots,
                    "source_files": len(source_files),
                    "installed_files": len(cache_files),
                    "cache_matches_source": source_files == cache_files,
                    "errors": plugin_errors,
                }
            )

    if any(command["status"] != "passed" for command in commands):
        errors.append("one or more Codex plugin commands failed")
    report = {
        "format": "nova-mind-temporary-clean-host-install/v1",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "temporary_empty_codex_home": True,
        "authentication_copied": False,
        "model_invocation_attempted": False,
        "commands": commands,
        "plugins": plugins,
        "total_skill_handles": sum(plugin["skill_count"] for plugin in plugins),
        "errors": errors,
        "valid": not errors,
        "boundary": "Proves local marketplace registration, install, enablement, cache equality, and skill-file discovery in an initially empty temporary Codex home. It does not prove authenticated model behavior.",
    }
    rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
