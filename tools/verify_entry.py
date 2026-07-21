from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
PLUGINS = ROOT / "plugins"
EXPECTED_SKILLS = {
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
EXPECTED_BRAND_SHA256 = "85725355c5c7ac1516a156d3cc37ca74e1dee314418bc300252d8436d0ce2ce6"
EXPECTED_BRAND_COLOR = "#48CBE8"
EXPECTED_LICENSE = "MIT"
TEXT_SUFFIXES = {".css", ".html", ".json", ".md", ".py", ".txt", ".yaml", ".yml"}
FORBIDDEN_SUFFIXES = {".7z", ".db", ".dll", ".env", ".gz", ".pkl", ".pyc", ".sqlite", ".sqlite3", ".tar", ".zip"}
FORBIDDEN_TEXT = {
    "port zindra": "worked campaign",
    "the bell below bracken": "worked example world",
    "patreon.com": "promotional funnel",
    "discord.gg": "promotional/community funnel",
    "stunspot@": "personal contact address",
    "wraps all responses": "forced legacy response wrapper",
    "use every tx all contexts": "legacy universal persona directive",
    "stunspot design studio": "prior-project root prompt",
    "universal sam": "user-specific assumption",
    "💠‍🌐": "obsolete Nova sigil order",
    "[todo": "unfinished scaffold",
}
PRIVATE_PATH = re.compile(
    r"(?:[A-Za-z]:\\(?:Users|Documents and Settings|Indranet|Github)\\|/Users/[^/\s]+/|/home/[^/\s]+/)",
    re.IGNORECASE,
)
EMAIL = re.compile(r"(?<![/\w])[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
REQUIRED_REPOSITORY_FILES = {
    "BUILD-WEEK-CONTRIBUTION.md",
    "README.md",
    "START-HERE.md",
    "LICENSE.md",
    "docs/JUDGE-GUIDE.md",
    "demo/DEMO-PROMPTS.md",
    "demo/SHOT-LIST.md",
    "demo/STUDIO-CASE.json",
    "demo/VIDEO-SCRIPT.md",
    "submission/DEVPOST-COPY.md",
    "submission/HUMAN-ACTIONS.md",
    "release/augment-of-mind-1.0.0.zip",
    "release/nova-the-optimal-ai-1.0.0.zip",
    "release/release-receipt.json",
    "release/SHA256SUMS",
    "verification/verification-manifest.json",
    "verification/traceability-matrix.md",
    "verification/risk-register.md",
    "verification/verification-report.md",
    "verification/shipping-content-audit.md",
    "verification/shipping-directory-inventory.json",
    "verification/release-extraction-validation.json",
    "verification/installed-discovery.json",
    "verification/fresh-host-install.json",
    "verification/live-core-probe-status.json",
    "verification/live-probe-status.json",
    "verification/brand-custody.json",
    "verification/build-reproducibility.json",
    "verification/ludis-prompt-modernization.json",
    "verification/ludis-prompt-modernization.md",
    "verification/nova-prompt-surface-audit.json",
    "verification/nova-prompt-surface-audit.md",
    "verification/nova-skill-reconciliation.json",
    "verification/nova-skill-reconciliation.md",
    "verification/tour-browser-command.json",
    "verification/video-production-inputs.json",
}

REQUIRED_PASSING_EVIDENCE = {
    "verification/build-reproducibility.json": ("valid", True),
    "verification/ludis-prompt-modernization.json": ("status", "PASS"),
    "verification/nova-prompt-surface-audit.json": ("status", "PASS"),
    "verification/nova-skill-reconciliation.json": ("status", "PASS"),
    "verification/tour-browser-command.json": ("status", "passed"),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def coverage_rules() -> tuple[set[str], list[str]]:
    payload = load_json(ROOT / "verification" / "transformation-map.json")
    exact: set[str] = set()
    prefixes: list[str] = []
    for rule in payload["rules"]:
        exact.update(rule.get("paths", []))
        if rule.get("prefix"):
            prefixes.append(rule["prefix"])
    return exact, prefixes


def covered(path: str, exact: set[str], prefixes: list[str]) -> bool:
    return path in exact or any(path.startswith(prefix) for prefix in prefixes)


def verify_repository_files(errors: list[str], evidence: dict) -> None:
    missing = sorted(path for path in REQUIRED_REPOSITORY_FILES if not (ROOT / path).is_file())
    if missing:
        errors.append(f"required repository files are missing: {missing}")

    checked_links = 0
    for markdown in sorted(ROOT.rglob("*.md")):
        if ".git" in markdown.parts:
            continue
        text = markdown.read_text(encoding="utf-8-sig")
        for raw_target in MARKDOWN_LINK.findall(text):
            target = raw_target.strip().split(maxsplit=1)[0].strip("<>")
            if not target or target.startswith(("#", "http://", "https://", "mailto:")):
                continue
            checked_links += 1
            local = (markdown.parent / target.split("#", 1)[0]).resolve()
            try:
                local.relative_to(ROOT.resolve())
            except ValueError:
                errors.append(f"markdown link leaves repository in {relative(markdown)}: {target}")
                continue
            if not local.exists():
                errors.append(f"broken local markdown link in {relative(markdown)}: {target}")

    evidence["repository_files"] = {
        "required": len(REQUIRED_REPOSITORY_FILES),
        "missing": missing,
        "local_markdown_links_checked": checked_links,
    }


def verify_required_evidence(errors: list[str], evidence: dict) -> None:
    observed: dict[str, object] = {}
    for relative_path, (field, expected) in REQUIRED_PASSING_EVIDENCE.items():
        path = ROOT / relative_path
        if not path.is_file():
            observed[relative_path] = {"missing": True}
            continue
        try:
            payload = load_json(path)
        except Exception as exc:
            errors.append(f"invalid required evidence {relative_path}: {exc}")
            observed[relative_path] = {"invalid": True}
            continue
        actual = payload.get(field)
        observed[relative_path] = {"field": field, "expected": expected, "actual": actual}
        if actual != expected:
            errors.append(
                f"required evidence is not passing: {relative_path} {field}={actual!r}, expected {expected!r}"
            )
    evidence["required_passing_evidence"] = observed


def verify_repository_hygiene(errors: list[str], evidence: dict) -> None:
    debris: list[str] = []
    for current, directories, names in os.walk(ROOT, followlinks=False):
        current_path = Path(current)
        directories[:] = [
            name
            for name in directories
            if name != ".git"
            and not (name == "raw" and current_path == ROOT / "verification")
        ]
        if current_path.name == "__pycache__":
            debris.append(relative(current_path) + "/")
        for name in names:
            path = current_path / name
            if path.suffix.casefold() in {".pyc", ".pyo"} or name in {".DS_Store", "Thumbs.db"}:
                debris.append(relative(path))
    if debris:
        errors.append(f"generated or host debris remains in repository: {sorted(debris)}")
    evidence["repository_hygiene"] = {"debris": sorted(debris)}


def verify_brand(errors: list[str], evidence: dict) -> None:
    logo_paths = {
        "augment-of-mind": "./skills/augment-of-mind/assets/collaborative-dynamics-logo.png",
        "nova-the-optimal-ai": "./skills/nova/assets/collaborative-dynamics-logo.png",
    }
    logo_hashes: dict[str, str] = {}
    for plugin_name, manifest_logo in logo_paths.items():
        plugin_root = PLUGINS / plugin_name
        logo = plugin_root / manifest_logo.removeprefix("./")
        if not logo.is_file():
            errors.append(f"canonical brand logo is missing: {relative(logo)}")
            continue
        logo_hashes[plugin_name] = sha256(logo)
        if logo_hashes[plugin_name] != EXPECTED_BRAND_SHA256:
            errors.append(f"canonical brand logo hash mismatch: {relative(logo)}")
        manifest = load_json(plugin_root / ".codex-plugin" / "plugin.json")
        interface = manifest.get("interface", {})
        if interface.get("brandColor") != EXPECTED_BRAND_COLOR:
            errors.append(f"plugin brand color mismatch: {plugin_name}")
        for field in ("composerIcon", "logo", "logoDark"):
            if interface.get(field) != manifest_logo:
                errors.append(f"plugin brand asset mismatch: {plugin_name} interface.{field}")

    nova_manifest = load_json(PLUGINS / "nova-the-optimal-ai" / ".codex-plugin" / "plugin.json")
    expected_screenshots = ["./assets/nova-tour-preview.png", "./assets/nova-tour-mobile.png"]
    if nova_manifest.get("interface", {}).get("screenshots") != expected_screenshots:
        errors.append("Nova plugin screenshot inventory mismatch")
    for raw_path in expected_screenshots:
        screenshot = PLUGINS / "nova-the-optimal-ai" / raw_path.removeprefix("./")
        if not screenshot.is_file() or not screenshot.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"):
            errors.append(f"Nova plugin screenshot is missing or not PNG: {relative(screenshot)}")

    tour_path = PLUGINS / "nova-the-optimal-ai" / "skills" / "nova" / "assets" / "nova-tour.html"
    tour = tour_path.read_text(encoding="utf-8")
    embedded = re.findall(r'src="data:image/png;base64,([A-Za-z0-9+/=]+)"', tour)
    if len(embedded) != 1:
        errors.append("tour must embed exactly one canonical brand logo")
        embedded_logo_hash = None
    else:
        try:
            embedded_logo_hash = hashlib.sha256(base64.b64decode(embedded[0], validate=True)).hexdigest()
        except Exception as exc:
            embedded_logo_hash = None
            errors.append(f"tour brand logo data URI is invalid: {exc}")
        if embedded_logo_hash != EXPECTED_BRAND_SHA256:
            errors.append("tour embedded brand logo hash mismatch")

    brand_reference = (
        PLUGINS / "nova-the-optimal-ai" / "skills" / "nova" / "references" / "cd-brand-canon.md"
    ).read_text(encoding="utf-8")
    missing_palette = [
        color for color in ("#48CBE8", "#193449", "#CCDCE4", "#FAFAFA") if color not in brand_reference
    ]
    if missing_palette:
        errors.append(f"brand canon omits exact palette colors: {missing_palette}")

    evidence["brand"] = {
        "canonical_logo_sha256": EXPECTED_BRAND_SHA256,
        "shipping_logo_hashes": logo_hashes,
        "tour_embedded_logo_sha256": embedded_logo_hash,
        "plugin_brand_color": EXPECTED_BRAND_COLOR,
        "screenshots": [path.removeprefix("./") for path in expected_screenshots],
    }


def verify() -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    evidence: dict = {}

    marketplace_path = ROOT / ".agents" / "plugins" / "marketplace.json"
    try:
        marketplace = load_json(marketplace_path)
    except Exception as exc:
        marketplace = {}
        errors.append(f"invalid marketplace JSON: {exc}")
    if marketplace.get("name") != "collaborative-dynamics-build-week":
        errors.append("marketplace name mismatch")
    marketplace_names = {item.get("name") for item in marketplace.get("plugins", [])}
    if marketplace_names != set(EXPECTED_SKILLS):
        errors.append(f"marketplace plugin set mismatch: {sorted(marketplace_names)}")

    total_skills = 0
    for plugin_name, expected in EXPECTED_SKILLS.items():
        plugin_root = PLUGINS / plugin_name
        manifest_path = plugin_root / ".codex-plugin" / "plugin.json"
        try:
            manifest = load_json(manifest_path)
        except Exception as exc:
            manifest = {}
            errors.append(f"invalid {relative(manifest_path)}: {exc}")
        if manifest.get("name") != plugin_name:
            errors.append(f"plugin name mismatch: {plugin_name}")
        if manifest.get("version") != "1.0.0":
            errors.append(f"plugin version is not 1.0.0: {plugin_name}")
        if manifest.get("license") != EXPECTED_LICENSE:
            errors.append(f"plugin license is not {EXPECTED_LICENSE}: {plugin_name}")
        actual = {path.name for path in (plugin_root / "skills").iterdir() if path.is_dir()}
        if actual != expected:
            errors.append(
                f"skill inventory mismatch for {plugin_name}: expected={sorted(expected)} actual={sorted(actual)}"
            )
        total_skills += len(actual)
    if total_skills != 28:
        errors.append(f"combined handle count is {total_skills}, expected 28")
    evidence["skill_count"] = total_skills
    license_text = (ROOT / "LICENSE.md").read_text(encoding="utf-8-sig")
    if not license_text.startswith("# MIT License\n") or "Copyright (c) 2026 Collaborative Dynamics" not in license_text:
        errors.append("repository MIT license text or copyright holder mismatch")
    evidence["license"] = {
        "repository": "MIT",
        "plugin_manifests": EXPECTED_LICENSE,
        "copyright_holder": "Collaborative Dynamics",
    }

    file_count = 0
    byte_count = 0
    for current, dirs, names in os.walk(PLUGINS, followlinks=False):
        current_path = Path(current)
        for directory in list(dirs):
            candidate = current_path / directory
            if candidate.is_symlink():
                errors.append(f"symlink directory: {relative(candidate)}")
            if directory in {"__pycache__", ".git"}:
                errors.append(f"forbidden directory: {relative(candidate)}")
        for name in names:
            path = current_path / name
            rel = relative(path)
            file_count += 1
            byte_count += path.stat().st_size
            if path.is_symlink():
                errors.append(f"symlink file: {rel}")
                continue
            if path.suffix.casefold() in FORBIDDEN_SUFFIXES:
                errors.append(f"forbidden file type: {rel}")
            if path.suffix.casefold() == ".json":
                try:
                    load_json(path)
                except Exception as exc:
                    errors.append(f"invalid JSON {rel}: {exc}")
            if path.suffix.casefold() == ".py":
                try:
                    compile(path.read_text(encoding="utf-8-sig"), rel, "exec")
                except Exception as exc:
                    errors.append(f"invalid Python {rel}: {exc}")
            if path.suffix.casefold() not in TEXT_SUFFIXES:
                continue
            try:
                text = path.read_text(encoding="utf-8-sig")
            except UnicodeError as exc:
                errors.append(f"non-UTF-8 text {rel}: {exc}")
                continue
            folded = text.casefold()
            for token, reason in FORBIDDEN_TEXT.items():
                if token in folded:
                    errors.append(f"{reason} in {rel}: {token}")
            if path.name != "verify_package.py" and PRIVATE_PATH.search(text):
                errors.append(f"private absolute path in {rel}")
            if EMAIL.search(text):
                errors.append(f"email address in {rel}")

    evidence["plugin_file_count"] = file_count
    evidence["plugin_bytes"] = byte_count

    verify_repository_files(errors, evidence)
    verify_required_evidence(errors, evidence)
    verify_repository_hygiene(errors, evidence)
    verify_brand(errors, evidence)

    tour = (PLUGINS / "nova-the-optimal-ai" / "skills" / "nova" / "assets" / "nova-tour.html").read_text(
        encoding="utf-8"
    )
    for forbidden in ("fetch(", "xmlhttprequest", "websocket", "localstorage", "sessionstorage", "<iframe"):
        if forbidden in tour.casefold():
            errors.append(f"tour is not fully offline/stateless: {forbidden}")
    external_resource = re.compile(
        r"(?:<(?:script|link|img|audio|video)\b[^>]*(?:src|href)\s*=\s*['\"]https?://|url\(\s*['\"]?https?://)",
        re.IGNORECASE,
    )
    if external_resource.search(tour):
        errors.append("tour loads an external network resource")
    if "connect-src 'none'" not in tour.casefold():
        errors.append("tour CSP does not deny network connections")
    if "prefers-reduced-motion" not in tour:
        errors.append("tour lacks reduced-motion handling")
    if "<noscript>" not in tour.casefold():
        errors.append("tour lacks no-JavaScript fallback")

    ledger = load_json(ROOT / "verification" / "source-import-ledger.json")
    imported = {item["destination"]: item for item in ledger["imported"]}
    changed: list[str] = []
    removed: list[str] = []
    for destination, item in imported.items():
        path = ROOT / destination
        if not path.is_file():
            removed.append(destination)
        elif sha256(path) != item["imported_sha256"]:
            changed.append(destination)
    current_files = {relative(path) for path in PLUGINS.rglob("*") if path.is_file()}
    added = sorted(current_files - set(imported))
    exact, prefixes = coverage_rules()
    unexpected = sorted(
        path for path in set(changed) | set(removed) | set(added) if not covered(path, exact, prefixes)
    )
    if unexpected:
        errors.append(f"source-ledger changes lack transformation custody: {unexpected}")
    evidence["source_custody"] = {
        "initial_imported": len(imported),
        "changed_after_import": sorted(changed),
        "removed_after_import": sorted(removed),
        "new_after_import": added,
        "unexpected": unexpected,
    }

    return {
        "format": "nova-mind-entry-verification/v1",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "evidence": evidence,
        "boundary": "Static repository and custody verification only; live install, discovery, interaction, video publication, repository access, feedback, and submission require separate evidence.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the Nova + MIND contest repository.")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = verify()
    rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
