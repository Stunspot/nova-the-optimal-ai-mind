from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

from release_lib import files, sha256_file, tree_digest

EXPECTED_ROOTS = {
    "nova", "nova-operations", "cognitive-continuity", "agent-striving",
    "agent-swarm-orchestration", "answerlayer", "current-intelligence-observatory",
    "retrieval-intelligence", "retrieval-reviewer", "rupert-giles-knowledge-steward",
    "promptcraft", "agentic-coding", "software-verification", "verification-reviewer",
    "beryl-it-tech", "it-work-reviewer", "corkboard", "dunbar", "privacy-redline",
    "lex-foster-language-companion", "job-application-builder", "interview-trainer",
    "omnara-deep-research", "owen-burnett-officecraft", "officecraft-reviewer",
}
REQUIRED_DOCS = {
    "README.md", "START-HERE.md", "LICENSE.md", "SECURITY.md", "SUPPORT.md",
    "THIRD-PARTY-NOTICES.md", "RELEASE-NOTES.md", "RELEASE-MANIFEST.json",
    "SHA256SUMS.txt",
}
REQUIRED_PACKAGE_PATHS = {
    "docs/CAPABILITY-GUIDE.md", "docs/HOST-MATRIX.md", "docs/INSTALL-CLAUDE.md",
    "docs/INSTALL-CODEX.md", "docs/MAINTAINER-GUIDE.md", "docs/PRIVACY-AND-TRUST.md",
    "docs/TROUBLESHOOTING.md", "docs/UPGRADE.md", "docs/VERIFICATION.md",
    "docs/index.html", "docs/style.css", "docs/assets/nova-mind-readme-hero.png",
    "design/FREE-NOVA-PACKAGE-MAP.md", "design/product-contract.json",
    "design/source-lock.json", "design/source-map.json",
    "codex/plugins/nova-the-optimal-ai/LOADOUT-MANIFEST.json",
    "claude/nova-the-optimal-ai/LOADOUT-MANIFEST.json",
    "codex/plugins/nova-the-optimal-ai/notices/testforge/LICENSE.md",
    "claude/nova-the-optimal-ai/notices/testforge/LICENSE.md",
    "codex/plugins/nova-the-optimal-ai/notices/agent-swarm-orchestration/LICENSE.md",
    "claude/nova-the-optimal-ai/notices/agent-swarm-orchestration/LICENSE.md",
    "codex/plugins/nova-the-optimal-ai/notices/job-application-builder/LICENSE-STATUS.md",
    "claude/nova-the-optimal-ai/notices/interview-trainer/LICENSE-STATUS.md",
}
MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")


class HtmlReferences(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.references: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = {key: value or "" for key, value in attrs}
        for key in ("href", "src"):
            if data.get(key):
                self.references.append(data[key])


def compare_trees(first: Path, second: Path) -> list[str]:
    first_files = {path.relative_to(first).as_posix(): sha256_file(path) for path in files(first)}
    second_files = {path.relative_to(second).as_posix(): sha256_file(path) for path in files(second)}
    return [name for name in sorted(set(first_files) | set(second_files)) if first_files.get(name) != second_files.get(name)]


def resolve_customer_reference(source: Path, reference: str, package: Path) -> str | None:
    value = reference.strip()
    if value.startswith("<") and ">" in value:
        value = value[1:value.index(">")]
    elif " " in value:
        value = value.split(" ", 1)[0]
    split = urlsplit(value)
    if split.scheme or split.netloc or value.startswith(("mailto:", "tel:", "#")):
        return None
    raw = unquote(split.path)
    if not raw:
        return None
    target = (source.parent / raw).resolve()
    try:
        target.relative_to(package.resolve())
    except ValueError:
        return f"reference leaves package: {reference}"
    if not target.exists():
        return f"missing target: {reference}"
    return None


def customer_link_findings(package: Path) -> tuple[list[str], int]:
    findings: list[str] = []
    checked = 0
    markdown = sorted(package.glob("*.md")) + sorted((package / "docs").rglob("*.md"))
    for path in markdown:
        for match in MARKDOWN_LINK.finditer(path.read_text(encoding="utf-8")):
            checked += 1
            problem = resolve_customer_reference(path, match.group(1), package)
            if problem:
                findings.append(f"broken customer Markdown reference {path.relative_to(package).as_posix()}: {problem}")
    for path in sorted((package / "docs").rglob("*.html")):
        parser = HtmlReferences()
        parser.feed(path.read_text(encoding="utf-8"))
        for reference in parser.references:
            checked += 1
            problem = resolve_customer_reference(path, reference, package)
            if problem:
                findings.append(f"broken customer HTML reference {path.relative_to(package).as_posix()}: {problem}")
    return findings, checked


def verify(package: Path) -> dict[str, object]:
    findings: list[str] = []
    if not package.is_dir():
        raise RuntimeError(f"Package directory not found: {package}")
    missing_docs = sorted(name for name in REQUIRED_DOCS if not (package / name).is_file())
    if missing_docs:
        findings.append(f"missing customer documents: {', '.join(missing_docs)}")
    missing_paths = sorted(name for name in REQUIRED_PACKAGE_PATHS if not (package / name).is_file())
    if missing_paths:
        findings.append(f"missing required package paths: {', '.join(missing_paths)}")

    codex_plugin = package / "codex" / "plugins" / "nova-the-optimal-ai"
    claude_plugin = package / "claude" / "nova-the-optimal-ai"
    folders = package / "claude" / "folders"
    codex_roots = {path.name for path in (codex_plugin / "skills").iterdir() if path.is_dir()}
    claude_roots = {path.name for path in (claude_plugin / "skills").iterdir() if path.is_dir()}
    folder_roots = {path.name for path in folders.iterdir() if path.is_dir()}
    for label, observed in (("codex", codex_roots), ("claude plugin", claude_roots), ("claude folders", folder_roots)):
        if observed != EXPECTED_ROOTS:
            findings.append(f"{label} roots differ: missing={sorted(EXPECTED_ROOTS-observed)} extra={sorted(observed-EXPECTED_ROOTS)}")

    codex_manifest = json.loads((codex_plugin / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    claude_manifest = json.loads((claude_plugin / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    if codex_manifest.get("name") != "nova-the-optimal-ai" or codex_manifest.get("version") != "3.0.0":
        findings.append("Codex plugin identity/version mismatch")
    if claude_manifest.get("name") != "nova-the-optimal-ai" or claude_manifest.get("version") != "3.0.0":
        findings.append("Claude plugin identity/version mismatch")
    if (codex_plugin / ".claude-plugin").exists() or (claude_plugin / ".codex-plugin").exists():
        findings.append("host-specific manifest leaked into the other binding")

    for skill_id in sorted(EXPECTED_ROOTS):
        if compare_trees(codex_plugin / "skills" / skill_id, claude_plugin / "skills" / skill_id):
            findings.append(f"Codex/Claude bytes differ for {skill_id}")
        if compare_trees(codex_plugin / "skills" / skill_id, folders / skill_id):
            findings.append(f"Claude folder bytes differ for {skill_id}")
        if not (codex_plugin / "skills" / skill_id / "SKILL.md").is_file():
            findings.append(f"SKILL.md missing for {skill_id}")

    cores = list((codex_plugin / "skills" / "nova" / "references" / "mind" / "faculty-cores").glob("*.core.md"))
    if len(cores) != 16:
        findings.append(f"Expected 16 nested Faculty Cores, found {len(cores)}")

    forbidden_paths: list[str] = []
    for path in files(package):
        relative = path.relative_to(package).as_posix().casefold()
        if any(fragment in relative for fragment in ("plugins/augment-of-mind", "/hooks/", "/mind_core/", "bundle/reminder", "mind_prompt_submit.py")):
            forbidden_paths.append(relative)
        if "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
            forbidden_paths.append(relative)
    if forbidden_paths:
        findings.append(f"forbidden runtime paths present: {forbidden_paths[:8]}")

    ops = (codex_plugin / "skills" / "nova-operations" / "scripts" / "nova_estate.py").read_text(encoding="utf-8")
    selector_block = re.search(r"SELECTOR_KEYS = \((.*?)\)", ops, flags=re.DOTALL)
    if '"project-management"' in ops or selector_block is None or "DENNIS_PROJECT_HOME" in selector_block.group(1):
        findings.append("Free Nova Operations still requires Project Management")
    cork = (codex_plugin / "skills" / "corkboard" / "scripts" / "corkboard.py").read_text(encoding="utf-8")
    dunbar = (codex_plugin / "skills" / "dunbar" / "scripts" / "dunbar.py").read_text(encoding="utf-8")
    if "CODEX_HOME" in cork or "CODEX_HOME" in dunbar:
        findings.append("Stateful service retains CODEX_HOME fallback")

    checksum_path = package / "SHA256SUMS.txt"
    if checksum_path.is_file():
        for line in checksum_path.read_text(encoding="utf-8").splitlines():
            digest, relative = line.split("  ", 1)
            target = package / Path(relative)
            if not target.is_file() or sha256_file(target) != digest:
                findings.append(f"checksum mismatch: {relative}")

    release_manifest = json.loads((package / "RELEASE-MANIFEST.json").read_text(encoding="utf-8"))
    source_lock = json.loads((package / "design" / "source-lock.json").read_text(encoding="utf-8"))
    if release_manifest.get("topology", {}).get("visible_skill_roots") != 25:
        findings.append("release manifest root count mismatch")
    if not release_manifest.get("host_trees", {}).get("codex_claude_skill_bytes_identical"):
        findings.append("release manifest does not establish host skill parity")
    if release_manifest.get("redistribution_state") != "blocked_pending_component_grants":
        findings.append("release manifest does not preserve the redistribution blocker")
    if release_manifest.get("release_blockers") != source_lock.get("release_blockers"):
        findings.append("release manifest blockers differ from the frozen source lock")

    zips_root = package / "claude" / "zips"
    for skill_id in sorted(EXPECTED_ROOTS):
        zip_path = zips_root / f"{skill_id}-3.0.0.zip"
        if not zip_path.is_file():
            findings.append(f"missing Claude skill ZIP: {skill_id}")
            continue
        expected_names = {f"{skill_id}/{path.relative_to(folders / skill_id).as_posix()}" for path in files(folders / skill_id)}
        with zipfile.ZipFile(zip_path) as archive:
            if set(archive.namelist()) != expected_names:
                findings.append(f"Claude skill ZIP inventory mismatch: {skill_id}")

    link_problems, checked_links = customer_link_findings(package)
    findings.extend(link_problems)
    return {
        "schema": "nova-free-package-verification/v3",
        "package": str(package),
        "verdict": "PASS" if not findings else "FAIL",
        "findings": findings,
        "observed": {
            "visible_skill_roots": len(codex_roots),
            "faculty_cores": len(cores),
            "customer_references_checked": checked_links,
            "codex_plugin_tree": tree_digest(codex_plugin),
            "claude_plugin_tree": tree_digest(claude_plugin),
            "redistribution_state": release_manifest.get("redistribution_state"),
        },
        "evidence_boundary": "Static package verification only. Fresh-host installation, discovery, enabled state, invocation, behavior, publication, and outcomes are not established.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Nova the Optimal AI Free package structure and bytes.")
    parser.add_argument("package", type=Path)
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args()
    try:
        result = verify(args.package.resolve())
    except (OSError, RuntimeError, KeyError, ValueError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
        result = {"schema": "nova-free-package-verification/v3", "verdict": "BLOCKED", "error": str(exc)}
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    print(rendered)
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(rendered + "\n", encoding="utf-8", newline="\n")
    return 0 if result.get("verdict") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
