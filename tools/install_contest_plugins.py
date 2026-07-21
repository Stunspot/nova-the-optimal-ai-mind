#!/usr/bin/env python3
"""Refresh only the two Nova contest selectors in the current Codex host."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MARKETPLACE = "collaborative-dynamics-build-week"
PLUGINS = ("augment-of-mind", "nova-the-optimal-ai")


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


def run(arguments: list[str]) -> tuple[subprocess.CompletedProcess[str], dict | None]:
    completed = subprocess.run(
        [*codex_command(), *arguments],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        payload = None
    return completed, payload


def record(label: str, result: subprocess.CompletedProcess[str], payload: dict | None) -> dict[str, object]:
    return {
        "command": label,
        "exit_code": result.returncode,
        "json_output": payload is not None,
        "stderr_sha256": hashlib.sha256(result.stderr.encode("utf-8")).hexdigest(),
        "status": "passed" if result.returncode == 0 and payload is not None else "failed",
    }


def checked(arguments: list[str], label: str, records: list[dict[str, object]]) -> dict:
    completed, payload = run(arguments)
    records.append(record(label, completed, payload))
    if completed.returncode != 0 or payload is None:
        raise RuntimeError(f"{label} failed with exit code {completed.returncode}")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    records: list[dict[str, object]] = []
    errors: list[str] = []
    final_list: dict = {}
    try:
        installed = checked(["plugin", "list", "--json"], "codex plugin list --json (before)", records)
        installed_ids = {item.get("pluginId") for item in installed.get("installed", [])}
        for plugin in PLUGINS:
            selector = f"{plugin}@{MARKETPLACE}"
            if selector in installed_ids:
                checked(
                    ["plugin", "remove", selector, "--json"],
                    f"codex plugin remove {selector} --json",
                    records,
                )

        marketplaces = checked(
            ["plugin", "marketplace", "list", "--json"],
            "codex plugin marketplace list --json (before)",
            records,
        )
        if any(item.get("name") == MARKETPLACE for item in marketplaces.get("marketplaces", [])):
            checked(
                ["plugin", "marketplace", "remove", MARKETPLACE, "--json"],
                f"codex plugin marketplace remove {MARKETPLACE} --json",
                records,
            )

        checked(
            ["plugin", "marketplace", "add", str(ROOT), "--json"],
            "codex plugin marketplace add <contest-repository> --json",
            records,
        )
        for plugin in PLUGINS:
            selector = f"{plugin}@{MARKETPLACE}"
            checked(
                ["plugin", "add", selector, "--json"],
                f"codex plugin add {selector} --json",
                records,
            )
        final_list = checked(["plugin", "list", "--json"], "codex plugin list --json (after)", records)
    except Exception as exc:
        errors.append(str(exc))

    final_ids = {
        item.get("pluginId"): item for item in final_list.get("installed", [])
    }
    for plugin in PLUGINS:
        selector = f"{plugin}@{MARKETPLACE}"
        item = final_ids.get(selector)
        if item is None:
            errors.append(f"final plugin list is missing {selector}")
        elif item.get("version") != "1.0.0" or item.get("enabled") is not True:
            errors.append(f"final plugin state is not enabled version 1.0.0: {selector}")

    report = {
        "format": "nova-mind-current-host-install/v1",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "repository": ".",
        "marketplace": MARKETPLACE,
        "selectors": [f"{plugin}@{MARKETPLACE}" for plugin in PLUGINS],
        "commands": records,
        "valid": not errors,
        "errors": errors,
        "boundary": (
            "This receipt covers current-host marketplace and selector refresh only. "
            "Installed byte equality, skill discovery, and model behavior require separate checks."
        ),
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
