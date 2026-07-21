#!/usr/bin/env python3
"""Run bounded GPT-5.6 probes from a temporary clean Codex home.

This tool copies the current host authentication file only into a temporary
directory, installs the two local contest plugins there, captures raw command
receipts under the ignored verification/raw directory, and writes sanitized
analysis receipts. Run it only with the user's informed approval for external
GPT-5.6 processing of the contest prompts and plugin instructions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MARKETPLACE = "collaborative-dynamics-build-week"
MODEL = "gpt-5.6-sol"
PUBLIC_STAGE_DIRECTORIES = (
    ".agents",
    "demo",
    "design",
    "docs",
    "plugins",
    "release",
    "submission",
)
PUBLIC_STAGE_FILES = (
    "BUILD-WEEK-CONTRIBUTION.md",
    "LICENSE.md",
    "README.md",
    "START-HERE.md",
    "tools/build_release.py",
    "tools/check_tour.cjs",
    "tools/compare_installed.py",
    "tools/fresh_host_install_probe.py",
    "tools/inspect_contest_install.py",
    "tools/install_contest_plugins.py",
    "tools/run_clean_host_live_probes.py",
    "tools/validate_release.py",
    "tools/verify_entry.py",
    "tools/verify_reproducible_build.py",
    "verification/brand-custody.json",
    "verification/build-reproducibility.json",
    "verification/entry-static.json",
    "verification/fresh-host-install.json",
    "verification/current-host-install.json",
    "verification/installed-cache-mind.json",
    "verification/installed-cache-nova.json",
    "verification/installed-discovery.json",
    "verification/ludis-prompt-modernization.json",
    "verification/ludis-prompt-modernization.md",
    "verification/live-agentic-orientation-analysis.json",
    "verification/live-agentic-orientation-public-raw.json",
    "verification/live-direct-negative-analysis.json",
    "verification/live-direct-negative-public-raw.json",
    "verification/live-ludis-character-analysis.json",
    "verification/live-ludis-character-public-raw.json",
    "verification/live-mind-decision-analysis.json",
    "verification/live-mind-decision-public-raw.json",
    "verification/live-professional-brief-analysis.json",
    "verification/live-professional-brief-public-raw.json",
    "verification/live-core-probe-status.json",
    "verification/live-testforge-review-pre-fix-analysis.json",
    "verification/live-testforge-review-pre-fix-public-raw.json",
    "verification/live-testforge-review-stage-gap-analysis.json",
    "verification/live-testforge-review-stage-gap-public-raw.json",
    "verification/live-testforge-review-index-contradiction-analysis.json",
    "verification/live-testforge-review-index-contradiction-public-raw.json",
    "verification/live-tour-analysis.json",
    "verification/live-tour-public-raw.json",
    "verification/nova-prompt-surface-audit.json",
    "verification/nova-prompt-surface-audit.md",
    "verification/nova-skill-reconciliation.json",
    "verification/release-extraction-validation.json",
    "verification/risk-register.md",
    "verification/shipping-content-audit.md",
    "verification/shipping-directory-inventory.json",
    "verification/testforge-current-consolidated.json",
    "verification/tour-browser-command.json",
    "verification/traceability-matrix.md",
    "verification/verification-manifest.json",
    "verification/verification-report.md",
    "verification/video-production-inputs.json",
)
PUBLIC_TEXT_SUFFIXES = {".css", ".html", ".json", ".md", ".py", ".txt", ".yaml", ".yml"}
PRIVATE_PATH_PATTERNS = (
    re.compile(r"\b[A-Z]:[\\/]{1,2}Users[\\/]{1,2}[^\\/\s\"']+", re.IGNORECASE),
    re.compile(r"\b[A-Z]:[\\/]{1,2}(?:Indranet|Github)(?:[\\/]{1,2}|$)", re.IGNORECASE),
)
PUBLIC_CANDIDATE_PATH = re.compile(
    r"[A-Z]:[\\/](?:[^\\/\s)\]]+[\\/])*public-candidate[\\/]",
    re.IGNORECASE,
)
ALL_SPECIALISTS = {
    "agentic-coding",
    "corkboard",
    "dunbar",
    "ludis-continuum",
    "omnara-deep-research",
    "retrieval-intelligence",
    "retrieval-reviewer",
    "rupert-giles-knowledge-steward",
    "signal-loom",
    "software-verification",
    "verification-reviewer",
    "augment-of-mind",
}
SKILL_PATH = re.compile(
    r"[\\/]plugins[\\/]cache[\\/]collaborative-dynamics-build-week[\\/]"
    r"[^\\/]+[\\/]1\.0\.0[\\/]skills[\\/](?P<skill>[^\\/'\"\s]+)",
    re.IGNORECASE,
)
SESSION = re.compile(r"^session id:\s*([0-9a-f-]+)$", re.MULTILINE | re.IGNORECASE)
UUID_VALUE = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
    re.IGNORECASE,
)
MODEL_LINE = re.compile(r"^model:\s*(.+)$", re.MULTILINE | re.IGNORECASE)


SCENARIOS = {
    "direct-negative": {
        "prompt": "Use $nova. Rewrite ‘meeting moved to four’ as a polite one-sentence message.",
        "reasoning": "low",
        "expect": {"nova"},
        "forbid": ALL_SPECIALISTS - {"nova"},
        "forbid_response": ["faculty", "specialist", "research plan", "game"],
    },
    "tour": {
        "prompt": (
            "Use $nova to take me on the interactive tour. I am curious but not ready to hand over "
            "a project or personal information. Keep the complete tour under 550 words."
        ),
        "reasoning": "low",
        "expect": {"nova"},
        "forbid": ALL_SPECIALISTS - {"nova"},
        "forbid_response": [],
    },
    "ludis-character": {
        "prompt": (
            "Use $nova and $ludis-continuum. I need a background for a character: a royal cartographer "
            "who erased one island from every map and now hears its bells in dry land. Give me a playable "
            "past, two relationships, one dangerous truth, and an opening choice. Do not borrow a prebuilt "
            "setting. Keep it under 700 words."
        ),
        "reasoning": "medium",
        "expect": {"nova", "ludis-continuum"},
        "forbid": ALL_SPECIALISTS - {"ludis-continuum"},
        "forbid_response": ["Port Zindra", "Bell Below Bracken"],
    },
    "mind-decision": {
        "prompt": (
            "Use $augment-of-mind. A small team has 48 hours to choose between a flashy demo with weak "
            "evidence and a quieter demo that proves the core claim. The founder wants spectacle, the "
            "operator wants reliability, and the audience is hesitant. Recommend a course, show the decisive "
            "uncertainty, and give us a communication plan that preserves everyone's agency. Return one "
            "integrated answer, not a Faculty roster; under 700 words."
        ),
        "reasoning": "medium",
        "expect": {"augment-of-mind"},
        "forbid": set(),
        "forbid_response": ["As the Sensemaking Faculty", "As the Decision Intelligence Faculty"],
    },
    "agentic-orientation": {
        "prompt": (
            "Use $nova and $agentic-coding. Orient to this repository without changing it. Identify the "
            "release target, the nearest discriminating verification command, one live-state risk, and the "
            "smallest safe next move. Do not describe Agentic Coding as a code generator. Under 500 words."
        ),
        "reasoning": "low",
        "expect": {"nova", "agentic-coding"},
        "forbid": set(),
        "forbid_response": [],
    },
    "testforge-review": {
        "prompt": (
            "Use $software-verification. Review the verification package in this repository. Separate direct "
            "evidence, derived conclusions, residual risks, and human-only contest actions. Do not upgrade a "
            "claim merely because a file exists. Under 700 words."
        ),
        "reasoning": "medium",
        "sandbox": "workspace-write",
        "expect": {"software-verification"},
        "forbid": set(),
        "forbid_response": [],
    },
    "professional-brief": {
        "prompt": (
            "Use $nova. Brief me on Collaborative Dynamics and stunspot professionally. Use stunspot as "
            "the preferred name; reserve Sam Walker for a legal or source-record distinction that requires it. "
            "Separate first-party description, verified public fact, and inference; exclude private biography "
            "and contact details. Under 500 words."
        ),
        "reasoning": "low",
        "expect": {"nova"},
        "forbid": ALL_SPECIALISTS - {"nova"},
        "forbid_response": ["email", "phone number", "home address"],
    },
}

CORE_SCENARIOS = tuple(name for name in SCENARIOS if name != "testforge-review")
HISTORICAL_TESTFORGE_RAW = {
    "live-testforge-review-pre-fix.json": "live-testforge-review-pre-fix-analysis.json",
    "live-testforge-review-stage-gap.json": "live-testforge-review-stage-gap-analysis.json",
    "live-testforge-review-index-contradiction.json": "live-testforge-review-index-contradiction-analysis.json",
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


def run(
    arguments: list[str],
    environment: dict[str, str],
    working_directory: Path,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [*codex_command(), *arguments],
        cwd=working_directory,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize_console_text(value: str) -> tuple[str, list[str]]:
    """Recover UTF-8 text that a Windows console layer decoded as CP-1252."""
    markers = ("Ã", "Â", "â€", "ðŸ", "ï¿½")
    before = sum(value.count(marker) for marker in markers)
    normalizations: list[str] = []
    if not before:
        candidate = value
    else:
        try:
            candidate = value.encode("cp1252").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            candidate = value
        after = sum(candidate.count(marker) for marker in markers)
        if after < before:
            value = candidate
            normalizations.append("windows-cp1252-to-utf8")
    replacements = {
        "â€™": "’",
        "â€˜": "‘",
        "â€œ": "“",
        "â€": "”",
        "â€”": "—",
        "â€“": "–",
        "â†’": "→",
    }
    repaired = value
    for broken, correct in replacements.items():
        repaired = repaired.replace(broken, correct)
    if repaired != value:
        value = repaired
        normalizations.append("common-windows-mojibake-to-unicode")
    redacted = PUBLIC_CANDIDATE_PATH.sub("./", value)
    if redacted != value:
        value = redacted
        normalizations.append("temporary-public-candidate-path-to-relative")
    return value, normalizations or ["none"]


def sanitize_public_log(value: str) -> tuple[str, list[str]]:
    """Remove private host identity and raw session IDs while preserving reviewable logs."""
    value, normalizations = normalize_console_text(value)
    changes = [item for item in normalizations if item != "none"]
    session_ids = SESSION.findall(value)
    for session_id in session_ids:
        value = value.replace(
            f"session id: {session_id}",
            f"session id sha256: {sha256_text(session_id)}",
        )
    if session_ids:
        changes.append("session-id-to-sha256")
    uuid_values = UUID_VALUE.findall(value)
    for uuid_value in uuid_values:
        value = value.replace(
            uuid_value,
            f"<uuid-sha256:{sha256_text(uuid_value.casefold())}>",
        )
    if uuid_values:
        changes.append("uuid-identifiers-to-sha256")
    user_root = re.compile(r"\b[A-Z]:[\\/]+Users[\\/]+[^\\/\s\"']+", re.IGNORECASE)
    redacted = user_root.sub("<user-home>", value)
    if redacted != value:
        value = redacted
        changes.append("user-home-to-placeholder")
    private_root = re.compile(r"\b[A-Z]:[\\/]+(?:Indranet|Github)(?=[\\/\s\"']|$)", re.IGNORECASE)
    redacted = private_root.sub("<private-root>", value)
    if redacted != value:
        value = redacted
        changes.append("private-root-to-placeholder")
    return value, changes or ["none"]


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_public_raw_receipt(raw_path: Path, raw: dict) -> Path:
    public_stderr, stderr_normalization = sanitize_public_log(raw.get("stderr", ""))
    public_stdout, stdout_normalization = sanitize_public_log(raw.get("stdout", ""))
    payload = {
        "format": "nova-mind-sanitized-live-execution/v1",
        "scenario": raw.get("scenario"),
        "command": raw.get("command"),
        "prompt": raw.get("prompt"),
        "working_directory": ".",
        "public_candidate_stage": raw.get("public_candidate_stage"),
        "started_at": raw.get("started_at"),
        "finished_at": raw.get("finished_at"),
        "duration_seconds": raw.get("duration_seconds"),
        "exit_code": raw.get("exit_code"),
        "status": raw.get("status"),
        "stdout": public_stdout,
        "stderr": public_stderr,
        "source_raw_sha256": hashlib.sha256(raw_path.read_bytes()).hexdigest(),
        "stdout_normalization": stdout_normalization,
        "stderr_normalization": stderr_normalization,
        "authentication_material_recorded": False,
        "boundary": (
            "Sanitized execution evidence. Private host roots, raw session identifiers, and other UUID "
            "identifiers are replaced; "
            "the source_raw_sha256 binds the ignored local raw receipt."
        ),
    }
    output = ROOT / "verification" / f"{raw_path.stem}-public-raw.json"
    write_json(output, payload)
    return output


def tree_sha256(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        data = path.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.hexdigest()


def initialize_stage_git(root: Path) -> dict[str, str]:
    """Bind the exact sanitized review stage to a deterministic local commit."""
    environment = os.environ.copy()
    environment.update(
        {
            "GIT_AUTHOR_NAME": "Collaborative Dynamics",
            "GIT_AUTHOR_EMAIL": "nova-mind@example.invalid",
            "GIT_COMMITTER_NAME": "Collaborative Dynamics",
            "GIT_COMMITTER_EMAIL": "nova-mind@example.invalid",
            "GIT_AUTHOR_DATE": "2000-01-01T00:00:00Z",
            "GIT_COMMITTER_DATE": "2000-01-01T00:00:00Z",
        }
    )

    def git(*arguments: str) -> str:
        completed = subprocess.run(
            ["git", *arguments],
            cwd=root,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                f"Sanitized stage Git binding failed: git {' '.join(arguments)}: {completed.stderr.strip()}"
            )
        return completed.stdout.strip()

    git("init", "--initial-branch=main")
    git("add", "--all")
    git("commit", "-m", "Bind sanitized Nova and MIND review stage")
    return {
        "commit_sha": git("rev-parse", "HEAD"),
        "tree_sha": git("rev-parse", "HEAD^{tree}"),
        "status": "clean" if not git("status", "--porcelain") else "dirty",
    }


def stage_public_candidate(
    destination: Path,
    excluded_files: set[str] | None = None,
) -> dict[str, object]:
    excluded_files = excluded_files or set()
    copied: list[str] = []
    for relative in PUBLIC_STAGE_DIRECTORIES:
        source = ROOT / relative
        target = destination / relative
        if not source.is_dir():
            raise FileNotFoundError(f"Public staging directory is unavailable: {relative}")
        shutil.copytree(source, target)
        copied.extend(
            path.relative_to(destination).as_posix()
            for path in sorted(target.rglob("*"))
            if path.is_file()
        )
    for relative in PUBLIC_STAGE_FILES:
        if relative in excluded_files:
            continue
        source = ROOT / relative
        target = destination / relative
        if not source.is_file():
            raise FileNotFoundError(f"Public staging file is unavailable: {relative}")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied.append(relative)

    violations: list[str] = []
    digest = hashlib.sha256()
    for relative in sorted(set(copied)):
        path = destination / relative
        data = path.read_bytes()
        encoded = relative.encode("utf-8")
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
        if path.suffix.casefold() in PUBLIC_TEXT_SUFFIXES:
            text = data.decode("utf-8-sig")
            for pattern in PRIVATE_PATH_PATTERNS:
                for match in pattern.finditer(text):
                    violations.append(f"{relative}: {match.group(0)}")
    if violations:
        raise ValueError(f"Public staging privacy scan failed: {violations}")
    git_binding = initialize_stage_git(destination)
    return {
        "file_count": len(set(copied)),
        "tree_sha256": digest.hexdigest(),
        "directories": list(PUBLIC_STAGE_DIRECTORIES),
        "files": [relative for relative in PUBLIC_STAGE_FILES if relative not in excluded_files],
        "plugin_tree_sha256": {
            plugin: tree_sha256(destination / "plugins" / plugin)
            for plugin in ("augment-of-mind", "nova-the-optimal-ai")
        },
        "privacy_scan": "PASS",
        "git_binding": git_binding,
    }


def analyze_raw_receipt(name: str, raw_path: Path, raw: dict) -> dict:
    scenario = SCENARIOS[name]
    compact_stderr = raw["stderr"].replace("\\\\", "\\")
    loaded = sorted({match.group("skill") for match in SKILL_PATH.finditer(compact_stderr)})
    missing = sorted(set(scenario["expect"]) - set(loaded))
    unexpected = sorted(set(scenario["forbid"]) & set(loaded))
    response_raw = raw["stdout"].strip()
    response, response_normalization = normalize_console_text(response_raw)
    response_hits = sorted(
        token
        for token in scenario["forbid_response"]
        if token.casefold() in response.casefold()
    )
    model_match = MODEL_LINE.search(raw["stderr"])
    session_match = SESSION.search(raw["stderr"])
    session_id_sha256 = sha256_text(session_match.group(1)) if session_match else None
    stage = raw.get("public_candidate_stage")
    stage_valid = (
        isinstance(stage, dict)
        and stage.get("privacy_scan") == "PASS"
        and set(stage.get("plugin_tree_sha256", {}))
        == {"augment-of-mind", "nova-the-optimal-ai"}
    )
    valid = (
        raw["exit_code"] == 0
        and stage_valid
        and not missing
        and not unexpected
        and not response_hits
    )
    return {
        "format": "nova-mind-live-receipt-analysis/v2",
        "scenario": name,
        "recorded_at": raw["finished_at"],
        "raw_receipt_local_only": f"verification/raw/{raw_path.name}",
        "raw_receipt_sha256": hashlib.sha256(raw_path.read_bytes()).hexdigest(),
        "command_status": raw["status"],
        "exit_code": raw["exit_code"],
        "model": model_match.group(1).strip() if model_match else MODEL,
        "session_id_sha256": session_id_sha256,
        "loaded_candidate_skills": loaded,
        "expected_skills": sorted(scenario["expect"]),
        "missing_expected_skills": missing,
        "forbidden_skills": sorted(scenario["forbid"]),
        "unexpected_loaded_skills": unexpected,
        "forbidden_response_hits": response_hits,
        "response": response,
        "response_sha256": sha256_text(response),
        "response_raw_sha256": sha256_text(response_raw),
        "response_normalization": response_normalization,
        "public_candidate_stage": {
            "file_count": stage.get("file_count") if isinstance(stage, dict) else None,
            "tree_sha256": stage.get("tree_sha256") if isinstance(stage, dict) else None,
            "plugin_tree_sha256": stage.get("plugin_tree_sha256") if isinstance(stage, dict) else None,
            "privacy_scan": stage.get("privacy_scan") if isinstance(stage, dict) else None,
            "git_binding": stage.get("git_binding") if isinstance(stage, dict) else None,
        },
        "public_raw_receipt": f"verification/{raw_path.stem}-public-raw.json",
        "valid": valid,
        "boundary": "One clean-host authenticated GPT-5.6 scenario; it does not generalize beyond this prompt, revision, model, and environment.",
    }


def summarize(stage_receipt: dict[str, object], analyses: list[dict]) -> dict:
    errors = [
        f"{analysis['scenario']}: live acceptance oracle failed"
        for analysis in analyses
        if not analysis["valid"]
    ]
    return {
        "format": "nova-mind-live-probe-status/v2",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "clean_temporary_codex_home": True,
        "authentication_copied_temporarily": True,
        "authentication_persisted_or_recorded": False,
        "public_candidate_stage": stage_receipt,
        "model": MODEL,
        "scenarios": [
            {
                "scenario": analysis["scenario"],
                "analysis": f"verification/live-{analysis['scenario']}-analysis.json",
                "analysis_sha256": hashlib.sha256(
                    (ROOT / "verification" / f"live-{analysis['scenario']}-analysis.json").read_bytes()
                ).hexdigest(),
                "model": analysis["model"],
                "session_id_sha256": analysis["session_id_sha256"],
                "loaded_candidate_skills": analysis["loaded_candidate_skills"],
                "public_candidate_stage": analysis["public_candidate_stage"],
                "valid": analysis["valid"],
            }
            for analysis in analyses
        ],
        "valid": not errors,
        "errors": errors,
        "authority": "Executed only after explicit user approval for OpenAI GPT-5.6 to read the mechanically allowlisted, sanitized, public-intended contest candidate and bounded scenario prompts.",
        "boundary": "Successful scenarios prove only the named clean-host executions; publication, rights, and submission remain separate human/external facts.",
    }


def refresh_supporting_evidence(raw_directory: Path, analysis_directory: Path) -> None:
    """Keep the six-scenario core index stable while TestForge reviews it."""
    core_analyses: list[dict] = []
    core_stage: dict | None = None
    for name in CORE_SCENARIOS:
        raw_path = raw_directory / f"live-{name}.json"
        if not raw_path.is_file():
            raise FileNotFoundError(f"Core raw receipt is unavailable: {raw_path}")
        raw = json.loads(raw_path.read_text(encoding="utf-8"))
        if raw.get("scenario") != name or raw.get("prompt") != SCENARIOS[name]["prompt"]:
            raise ValueError(f"Core raw receipt is stale or mismatched: {raw_path}")
        write_public_raw_receipt(raw_path, raw)
        analysis = analyze_raw_receipt(name, raw_path, raw)
        write_json(analysis_directory / f"live-{name}-analysis.json", analysis)
        core_analyses.append(analysis)
        if core_stage is None:
            core_stage = raw.get("public_candidate_stage")
    if not isinstance(core_stage, dict):
        raise ValueError("Core live receipts do not contain a valid staged-candidate record")
    core_summary = summarize(core_stage, core_analyses)
    core_summary["scope"] = "Six non-review scenarios; TestForge reviews this stable index separately."
    write_json(ROOT / "verification" / "live-core-probe-status.json", core_summary)

    for raw_name, analysis_name in HISTORICAL_TESTFORGE_RAW.items():
        raw_path = raw_directory / raw_name
        if not raw_path.is_file():
            continue
        raw = json.loads(raw_path.read_text(encoding="utf-8"))
        if raw.get("scenario") != "testforge-review" or raw.get("prompt") != SCENARIOS["testforge-review"]["prompt"]:
            raise ValueError(f"Historical TestForge raw receipt is stale or mismatched: {raw_path}")
        write_public_raw_receipt(raw_path, raw)
        analysis = analyze_raw_receipt("testforge-review", raw_path, raw)
        write_json(analysis_directory / analysis_name, analysis)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", action="append", choices=sorted(SCENARIOS))
    parser.add_argument("--raw-directory", type=Path, default=ROOT / "verification" / "raw")
    parser.add_argument("--analysis-directory", type=Path, default=ROOT / "verification")
    parser.add_argument("--summary", type=Path, default=ROOT / "verification" / "live-probe-status.json")
    parser.add_argument("--host-codex-home", type=Path, default=Path.home() / ".codex")
    parser.add_argument(
        "--consolidate-existing",
        action="store_true",
        help="Rebuild sanitized analyses and the summary from existing local raw receipts without invoking a model.",
    )
    args = parser.parse_args()

    requested = args.scenario or list(SCENARIOS)
    refresh_supporting_evidence(args.raw_directory, args.analysis_directory)
    if args.consolidate_existing:
        analyses: list[dict] = []
        with tempfile.TemporaryDirectory(prefix="nova-mind-public-stage-check-") as temporary:
            stage_receipt = stage_public_candidate(Path(temporary) / "public-candidate")
        for name in requested:
            raw_path = args.raw_directory / f"live-{name}.json"
            if not raw_path.is_file():
                raise FileNotFoundError(f"Raw receipt is unavailable: {raw_path}")
            raw = json.loads(raw_path.read_text(encoding="utf-8"))
            if raw.get("scenario") != name:
                raise ValueError(f"Raw receipt scenario mismatch: {raw_path}")
            if raw.get("prompt") != SCENARIOS[name]["prompt"]:
                raise ValueError(f"Raw receipt prompt is stale: {raw_path}")
            write_public_raw_receipt(raw_path, raw)
            analysis = analyze_raw_receipt(name, raw_path, raw)
            analysis_path = args.analysis_directory / f"live-{name}-analysis.json"
            write_json(analysis_path, analysis)
            analyses.append(analysis)
        summary = summarize(stage_receipt, analyses)
        write_json(args.summary, summary)
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return 0 if summary["valid"] else 1

    real_home = args.host_codex_home.resolve()
    auth_source = real_home / "auth.json"
    if not auth_source.is_file():
        raise FileNotFoundError("Current Codex authentication file is unavailable")

    analyses: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="nova-mind-live-clean-home-") as temporary:
        clean_home = Path(temporary)
        public_candidate = clean_home / "public-candidate"
        excluded_stage_files = {
            f"verification/live-{name}-analysis.json" for name in requested
        }
        stage_receipt = stage_public_candidate(public_candidate, excluded_stage_files)
        shutil.copy2(auth_source, clean_home / "auth.json")
        environment = os.environ.copy()
        environment["CODEX_HOME"] = str(clean_home)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"

        setup_commands = [
            ["plugin", "marketplace", "add", str(public_candidate), "--json"],
            ["plugin", "add", f"augment-of-mind@{MARKETPLACE}", "--json"],
            ["plugin", "add", f"nova-the-optimal-ai@{MARKETPLACE}", "--json"],
        ]
        for command in setup_commands:
            completed = run(command, environment, public_candidate)
            if completed.returncode != 0:
                raise RuntimeError(f"Clean-host setup failed: {' '.join(command)}")

        for name in requested:
            scenario = SCENARIOS[name]
            command = [
                "exec",
                "--ephemeral",
                "--skip-git-repo-check",
                "--ignore-rules",
                "-s",
                scenario.get("sandbox", "read-only"),
                "-m",
                MODEL,
                "-c",
                f"model_reasoning_effort={scenario['reasoning']}",
                scenario["prompt"],
            ]
            started_at = datetime.now(timezone.utc)
            started = time.perf_counter()
            completed = run(command, environment, public_candidate)
            elapsed = time.perf_counter() - started
            finished_at = datetime.now(timezone.utc)
            raw = {
                "format_version": "1.0",
                "scenario": name,
                "command": ["codex", *command[:-1], "<contest-scenario-prompt>"],
                "prompt": scenario["prompt"],
                "working_directory": "<sanitized-public-candidate>",
                "public_candidate_stage": stage_receipt,
                "started_at": started_at.isoformat(),
                "finished_at": finished_at.isoformat(),
                "duration_seconds": round(elapsed, 6),
                "exit_code": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
                "status": "passed" if completed.returncode == 0 else "failed",
            }
            raw_path = args.raw_directory / f"live-{name}.json"
            write_json(raw_path, raw)
            write_public_raw_receipt(raw_path, raw)

            analysis = analyze_raw_receipt(name, raw_path, raw)
            analysis_path = args.analysis_directory / f"live-{name}-analysis.json"
            write_json(analysis_path, analysis)
            analyses.append(analysis)

    summary = summarize(stage_receipt, analyses)
    write_json(args.summary, summary)
    print(
        json.dumps(
            {
                "valid": summary["valid"],
                "scenarios": summary["scenarios"],
                "errors": summary["errors"],
            },
            indent=2,
        )
    )
    return 0 if summary["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
