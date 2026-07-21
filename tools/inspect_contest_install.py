from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


sys.dont_write_bytecode = True

MARKETPLACE = "collaborative-dynamics-build-week"
VERSION = "1.0.0"
EXPECTED = {
    "augment-of-mind": {
        "aesthetic-intelligence",
        "agent-dreaming",
        "agent-striving",
        "augment-of-mind",
        "capability-conductor",
        "cognitive-continuity",
        "creative-synthesis",
        "decision-intelligence",
        "deliberative-intelligence",
        "epistemic-regulation",
        "executive-function",
        "instrumental-agency",
        "kairos",
        "measurement-intelligence",
        "prosocial-influence",
        "sensemaking",
    },
    "nova-the-optimal-ai": {
        "agentic-coding",
        "corkboard",
        "dunbar",
        "ludis-continuum",
        "nova",
        "omnara-deep-research",
        "retrieval-intelligence",
        "retrieval-reviewer",
        "rupert-giles-knowledge-steward",
        "signal-loom",
        "software-verification",
        "verification-reviewer",
    },
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect the two installed Build Week contest plugins.")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    completed = subprocess.run(
        [*codex_command(), "plugin", "list", "--json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    errors: list[str] = []
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        payload = {}
        errors.append(f"Codex plugin list did not return valid JSON: {exc}")

    installed_by_id = {item.get("pluginId"): item for item in payload.get("installed", [])}
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    plugins: list[dict] = []
    for plugin, expected_skills in EXPECTED.items():
        plugin_id = f"{plugin}@{MARKETPLACE}"
        record = installed_by_id.get(plugin_id)
        cache = codex_home / "plugins" / "cache" / MARKETPLACE / plugin / VERSION
        actual_skills = (
            {path.name for path in (cache / "skills").iterdir() if path.is_dir() and (path / "SKILL.md").is_file()}
            if (cache / "skills").is_dir()
            else set()
        )
        plugin_errors: list[str] = []
        if record is None:
            plugin_errors.append("plugin selector is absent from Codex plugin list")
        else:
            if record.get("version") != VERSION:
                plugin_errors.append(f"reported version is {record.get('version')!r}")
            if record.get("enabled") is not True:
                plugin_errors.append("plugin is not enabled")
        if not cache.is_dir():
            plugin_errors.append("installed cache directory is absent")
        if actual_skills != expected_skills:
            plugin_errors.append(
                f"skill inventory mismatch: expected={sorted(expected_skills)} actual={sorted(actual_skills)}"
            )
        errors.extend(f"{plugin}: {error}" for error in plugin_errors)
        plugins.append(
            {
                "plugin_id": plugin_id,
                "version": record.get("version") if record else None,
                "enabled": record.get("enabled") if record else None,
                "cache_label": f"$CODEX_HOME/plugins/cache/{MARKETPLACE}/{plugin}/{VERSION}",
                "skill_count": len(actual_skills),
                "skills": sorted(actual_skills),
                "errors": plugin_errors,
            }
        )

    report = {
        "format": "nova-mind-installed-contest-plugins/v1",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "codex_list_exit_code": completed.returncode,
        "marketplace": MARKETPLACE,
        "plugins": plugins,
        "total_skill_handles": sum(item["skill_count"] for item in plugins),
        "errors": errors,
        "valid": completed.returncode == 0 and not errors,
        "boundary": "Observed host registration, enabled state, version, cache presence, and skill-file discovery only; model invocation is separate evidence.",
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
