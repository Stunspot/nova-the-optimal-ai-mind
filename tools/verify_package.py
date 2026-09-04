from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

from release_lib import files, sha256_file, tree_digest, zip_filename_findings

EXPECTED_ROOTS = {
    "nova", "nova-operations", "commonplace", "cognitive-continuity",
    "dennis-stratton-project-management", "agent-striving",
    "agent-swarm-orchestration", "answerlayer", "current-intelligence-observatory",
    "retrieval-intelligence", "retrieval-reviewer", "rupert-giles-knowledge-steward",
    "promptcraft", "agentic-coding", "software-verification", "verification-reviewer",
    "beryl-it-tech", "it-work-reviewer", "corkboard", "dunbar", "privacy-redline",
    "lex-foster-language-companion", "job-application-builder", "interview-trainer",
    "omnara-deep-research", "owen-burnett-officecraft", "officecraft-reviewer",
}
RIGHTS_DOCS = (
    "LICENSE.md",
    "ATTRIBUTION.md",
    "NOTICE.md",
    "TRADEMARKS.md",
    "PROVENANCE.md",
    "THIRD-PARTY-NOTICES.md",
)
REQUIRED_DOCS = {
    "README.md", "START-HERE.md", *RIGHTS_DOCS, "SECURITY.md", "SUPPORT.md",
    "RELEASE-NOTES.md", "RELEASE-MANIFEST.json", "SHA256SUMS.txt",
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
    "codex/BUILD-MANIFEST.json", "claude/BUILD-MANIFEST.json",
    "codex/plugins/nova-the-optimal-ai/notices/testforge/LICENSE.md",
    "claude/nova-the-optimal-ai/notices/testforge/LICENSE.md",
    "codex/plugins/nova-the-optimal-ai/notices/agent-swarm-orchestration/LICENSE.md",
    "claude/nova-the-optimal-ai/notices/agent-swarm-orchestration/LICENSE.md",
    "codex/plugins/nova-the-optimal-ai/notices/job-application-builder/INCLUSION-NOTICE.md",
    "claude/nova-the-optimal-ai/notices/interview-trainer/INCLUSION-NOTICE.md",
}
STANDALONE_RIGHTS_DIR = "nova-free-rights"
COMPONENT_NOTICE_MAP = {
    "agent-swarm-orchestration": "agent-swarm-orchestration",
    "software-verification": "testforge",
    "verification-reviewer": "testforge",
    "job-application-builder": "job-application-builder",
    "interview-trainer": "interview-trainer",
}
REDISTRIBUTION_STATE = "permitted_under_included_licenses"
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


def file_map(root: Path, *, exclude_top: set[str] | None = None) -> dict[str, str]:
    excluded = exclude_top or set()
    result = {}
    for path in files(root):
        relative = path.relative_to(root)
        if relative.parts and relative.parts[0] in excluded:
            continue
        result[relative.as_posix()] = sha256_file(path)
    return result


def compare_trees(first: Path, second: Path, *, exclude_second_top: set[str] | None = None) -> list[str]:
    first_files = file_map(first)
    second_files = file_map(second, exclude_top=exclude_second_top)
    return [
        name
        for name in sorted(set(first_files) | set(second_files))
        if first_files.get(name) != second_files.get(name)
    ]


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


def verify_rights_bundle(package: Path, codex_plugin: Path, claude_plugin: Path, findings: list[str]) -> dict[str, str]:
    observed: dict[str, str] = {}
    for name in RIGHTS_DOCS:
        root_path = package / name
        if not root_path.is_file():
            continue
        root_hash = sha256_file(root_path)
        observed[name] = root_hash
        for label, plugin in (("Codex", codex_plugin), ("Claude", claude_plugin)):
            target = plugin / name
            if not target.is_file():
                findings.append(f"{label} plugin missing rights file: {name}")
            elif sha256_file(target) != root_hash:
                findings.append(f"{label} plugin rights file differs from customer root: {name}")
    return observed


def verify_standalone_rights(
    package: Path,
    source_plugin: Path,
    folders: Path,
    findings: list[str],
) -> int:
    complete = 0
    for skill_id in sorted(EXPECTED_ROOTS):
        starting_findings = len(findings)
        folder = folders / skill_id
        rights = folder / STANDALONE_RIGHTS_DIR
        for name in (*RIGHTS_DOCS, "README.md"):
            if not (rights / name).is_file():
                findings.append(f"standalone rights envelope missing for {skill_id}: {name}")
        for name in RIGHTS_DOCS:
            root_doc = package / name
            detached_doc = rights / name
            if root_doc.is_file() and detached_doc.is_file() and root_doc.read_bytes() != detached_doc.read_bytes():
                findings.append(f"standalone rights file differs for {skill_id}: {name}")
        component_notice = COMPONENT_NOTICE_MAP.get(skill_id)
        notice_root = rights / "component-notices"
        if component_notice:
            expected = source_plugin / "notices" / component_notice
            observed = notice_root / component_notice
            if not observed.is_dir():
                findings.append(f"standalone component notice missing for {skill_id}: {component_notice}")
            elif compare_trees(expected, observed):
                findings.append(f"standalone component notice differs for {skill_id}: {component_notice}")
        elif notice_root.exists():
            findings.append(f"unexpected standalone component notice bundle for {skill_id}")
        if len(findings) == starting_findings:
            complete += 1
    return complete


def verify_checksum_inventory(package: Path, findings: list[str]) -> int:
    checksum_path = package / "SHA256SUMS.txt"
    if not checksum_path.is_file():
        return 0
    package_files = sorted(
        (path for path in package.rglob("*") if path.is_file()),
        key=lambda path: path.relative_to(package).as_posix(),
    )
    expected = {
        path.relative_to(package).as_posix(): path
        for path in package_files
        if path != checksum_path
    }
    observed: dict[str, str] = {}
    observed_order: list[str] = []
    for line_number, line in enumerate(checksum_path.read_text(encoding="utf-8").splitlines(), 1):
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        if not match:
            findings.append(f"malformed checksum line {line_number}: {line}")
            continue
        digest, relative = match.groups()
        normalized = PurePosixPath(relative)
        if (
            "\\" in relative
            or normalized.is_absolute()
            or normalized.as_posix() != relative
            or any(part in {"", ".", ".."} for part in normalized.parts)
        ):
            findings.append(f"invalid checksum path on line {line_number}: {relative}")
            continue
        if relative in observed:
            findings.append(f"duplicate checksum path: {relative}")
            continue
        observed[relative] = digest
        observed_order.append(relative)
    if observed_order != sorted(observed_order):
        findings.append("checksum inventory is not in deterministic path order")
    missing = sorted(set(expected) - set(observed))
    extra = sorted(set(observed) - set(expected))
    if missing or extra:
        findings.append(f"checksum inventory differs: missing={missing} extra={extra}")
    for relative in sorted(set(expected) & set(observed)):
        if sha256_file(expected[relative]) != observed[relative]:
            findings.append(f"checksum mismatch: {relative}")
    return len(observed)


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
    if codex_manifest.get("name") != "nova-the-optimal-ai" or codex_manifest.get("version") != "3.1.3":
        findings.append("Codex plugin identity/version mismatch")
    if claude_manifest.get("name") != "nova-the-optimal-ai" or claude_manifest.get("version") != "3.1.3":
        findings.append("Claude plugin identity/version mismatch")
    if "LICENSE.md" not in str(codex_manifest.get("license", "")) or "LICENSE.md" not in str(claude_manifest.get("license", "")):
        findings.append("host plugin metadata does not point to the product license")
    if (codex_plugin / ".claude-plugin").exists() or (claude_plugin / ".codex-plugin").exists():
        findings.append("host-specific manifest leaked into the other binding")

    rights_hashes = verify_rights_bundle(package, codex_plugin, claude_plugin, findings)
    standalone_rights_count = verify_standalone_rights(package, codex_plugin, folders, findings)

    for skill_id in sorted(EXPECTED_ROOTS):
        if compare_trees(codex_plugin / "skills" / skill_id, claude_plugin / "skills" / skill_id):
            findings.append(f"Codex/Claude bytes differ for {skill_id}")
        if compare_trees(
            codex_plugin / "skills" / skill_id,
            folders / skill_id,
            exclude_second_top={STANDALONE_RIGHTS_DIR},
        ):
            findings.append(f"Claude standalone payload bytes differ for {skill_id}")
        if not (codex_plugin / "skills" / skill_id / "SKILL.md").is_file():
            findings.append(f"SKILL.md missing for {skill_id}")

    loadout = json.loads((codex_plugin / "LOADOUT-MANIFEST.json").read_text(encoding="utf-8"))
    if loadout.get("license") != "LICENSE.md" or "MIT" not in str(loadout.get("rights_status", "")) or "CC BY-ND 4.0" not in str(loadout.get("rights_status", "")):
        findings.append("loadout rights status does not declare the public split license")
    answer_manifest = json.loads((codex_plugin / "skills" / "answerlayer" / "manifest.json").read_text(encoding="utf-8"))
    current_manifest = json.loads((codex_plugin / "skills" / "current-intelligence-observatory" / "manifest.json").read_text(encoding="utf-8"))
    for label, manifest in (("AnswerLayer", answer_manifest), ("Current Intelligence", current_manifest)):
        if manifest.get("rights_status") != "public-inclusion-authorized-for-nova-free-3.1.3":
            findings.append(f"{label} rights metadata is not reconciled for Nova Free")
        if "Nova Free 3.1.3 public split license" not in str(manifest.get("license", "")):
            findings.append(f"{label} license metadata is not reconciled for Nova Free")
    for relative in (
        "notices/job-application-builder/LICENSE-STATUS.md",
        "notices/interview-trainer/LICENSE-STATUS.md",
    ):
        if (codex_plugin / relative).exists() or (claude_plugin / relative).exists():
            findings.append(f"stale private-customer license status shipped: {relative}")

    cores = list((codex_plugin / "skills" / "nova" / "references" / "mind" / "faculty-cores").glob("*.core.md"))
    if len(cores) != 17:
        findings.append(f"Expected 17 nested Faculty Cores, found {len(cores)}")

    forbidden_paths: list[str] = []
    for path in sorted(package.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(package).as_posix().casefold()
        if any(fragment in relative for fragment in ("plugins/augment-of-mind", "/hooks/", "/mind_core/", "bundle/reminder", "mind_prompt_submit.py")):
            forbidden_paths.append(relative)
        if "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
            forbidden_paths.append(relative)
    if forbidden_paths:
        findings.append(f"forbidden runtime paths present: {forbidden_paths[:8]}")

    ops = (codex_plugin / "skills" / "nova-operations" / "scripts" / "nova_estate.py").read_text(encoding="utf-8")
    required_operations = (
        '"project-management"',
        '"commonplace"',
        '"DENNIS_PROJECT_HOME"',
        '"NOVA_COMMONPLACE_HOME"',
        '"NOVA_CONCORDANCE_HOME"',
    )
    missing_operations = [token for token in required_operations if token not in ops]
    if missing_operations:
        findings.append(f"Nova Operations lacks current foundation bindings: {missing_operations}")
    cork = (codex_plugin / "skills" / "corkboard" / "scripts" / "corkboard.py").read_text(encoding="utf-8")
    dunbar = (codex_plugin / "skills" / "dunbar" / "scripts" / "dunbar.py").read_text(encoding="utf-8")
    if "CODEX_HOME" in cork or "CODEX_HOME" in dunbar:
        findings.append("Stateful service retains CODEX_HOME fallback")

    checksum_entries = verify_checksum_inventory(package, findings)

    release_manifest_path = package / "RELEASE-MANIFEST.json"
    source_lock_path = package / "design" / "source-lock.json"
    source_map_path = package / "design" / "source-map.json"
    release_manifest = json.loads(release_manifest_path.read_text(encoding="utf-8"))
    source_lock = json.loads(source_lock_path.read_text(encoding="utf-8"))
    release_source = release_manifest.get("source", {})
    source_rights = source_lock.get("rights_bundle", {})
    if source_rights.get("files") != rights_hashes:
        findings.append("source-lock rights hashes differ from the packaged rights bundle")
    if source_rights.get("redistribution_state") != REDISTRIBUTION_STATE or source_rights.get("external_rights_blockers") != []:
        findings.append("source lock does not preserve the approved public rights state")
    if sha256_file(source_map_path) != source_lock.get("source_map_sha256"):
        findings.append("packaged source map differs from the frozen source-lock hash")
    if release_source.get("source_lock") != "design/source-lock.json":
        findings.append("release manifest source-lock path is invalid")
    if release_source.get("source_lock_sha256") != sha256_file(source_lock_path):
        findings.append("release manifest source-lock hash differs from the packaged source lock")
    if release_source.get("source_map_sha256") != source_lock.get("source_map_sha256"):
        findings.append("release manifest source-map hash differs from the frozen source lock")

    lock_records = source_lock.get("records")
    lock_record_by_id: dict[str, dict[str, object]] = {}
    if not isinstance(lock_records, list):
        findings.append("source-lock skill records are missing or malformed")
    else:
        for record in lock_records:
            if not isinstance(record, dict) or not isinstance(record.get("id"), str):
                findings.append("source-lock contains a malformed skill record")
                continue
            skill_id = str(record["id"])
            if skill_id in lock_record_by_id:
                findings.append(f"source-lock contains duplicate skill record: {skill_id}")
                continue
            lock_record_by_id[skill_id] = record
    if set(lock_record_by_id) != EXPECTED_ROOTS:
        findings.append("source-lock skill record inventory differs from the packaged roots")

    actual_codex_skill_tree = tree_digest(codex_plugin / "skills")
    actual_claude_skill_tree = tree_digest(claude_plugin / "skills")
    if source_lock.get("plugin_skill_tree") != actual_codex_skill_tree:
        findings.append("source-lock aggregate skill tree differs from the Codex plugin")
    if source_lock.get("plugin_skill_tree") != actual_claude_skill_tree:
        findings.append("source-lock aggregate skill tree differs from the Claude plugin")
    for skill_id in sorted(EXPECTED_ROOTS):
        expected_tree = lock_record_by_id.get(skill_id, {}).get("imported_tree")
        actual_tree = tree_digest(codex_plugin / "skills" / skill_id)
        if expected_tree != actual_tree:
            findings.append(f"source-lock skill tree mismatch: {skill_id}")

    persona = codex_plugin / "skills" / "nova" / "references" / "nova-persona.md"
    if sha256_file(persona) != source_lock.get("persona_sha256"):
        findings.append("packaged Nova persona differs from the frozen source-lock hash")

    lock_notices = source_lock.get("notices")
    if not isinstance(lock_notices, dict):
        findings.append("source-lock notice records are missing or malformed")
        lock_notices = {}
    for label, plugin in (("Codex", codex_plugin), ("Claude", claude_plugin)):
        notice_root = plugin / "notices"
        actual_notice_ids = {path.name for path in notice_root.iterdir() if path.is_dir()}
        if actual_notice_ids != set(lock_notices):
            findings.append(f"{label} notice inventory differs from the frozen source lock")
        for notice_id in sorted(actual_notice_ids & set(lock_notices)):
            if tree_digest(notice_root / notice_id) != lock_notices[notice_id]:
                findings.append(f"{label} notice tree differs from the frozen source lock: {notice_id}")

    build_states: dict[str, dict[str, object]] = {}
    for binding, manifest_path in (
        ("codex", package / "codex" / "BUILD-MANIFEST.json"),
        ("claude-compatible", package / "claude" / "BUILD-MANIFEST.json"),
    ):
        state = json.loads(manifest_path.read_text(encoding="utf-8"))
        build_states[binding] = state
        if "sealed_candidate" in state:
            findings.append(f"{binding} build manifest prematurely seals the candidate")
        if state.get("candidate_state") != "built_from_frozen_source":
            findings.append(f"{binding} build manifest candidate state is invalid")
        if state.get("independent_review_required") is not True:
            findings.append(f"{binding} build manifest omits independent review requirement")
        if state.get("archive_filename_encoding") != "strict_utf8_local_and_central_headers":
            findings.append(f"{binding} build manifest omits the UTF-8 archive filename contract")
        if state.get("binding") != binding:
            findings.append(f"{binding} build manifest binding mismatch")
        if state.get("source_base_commit") != release_source.get("base_commit"):
            findings.append(f"{binding} build manifest source checkpoint mismatch")
        if state.get("source_lock_sha256") != release_source.get("source_lock_sha256"):
            findings.append(f"{binding} build manifest source-lock hash mismatch")
        if state.get("source_map_sha256") != release_source.get("source_map_sha256"):
            findings.append(f"{binding} build manifest source-map hash mismatch")
        state_rights = state.get("rights", {})
        if state_rights.get("redistribution_state") != REDISTRIBUTION_STATE or state_rights.get("external_rights_blockers") != []:
            findings.append(f"{binding} build manifest rights state is invalid")
        if state.get("publication_state") != "not_published":
            findings.append(f"{binding} build manifest overclaims publication")
    if release_manifest.get("topology", {}).get("visible_skill_roots") != 27:
        findings.append("release manifest root count mismatch")
    host_trees = release_manifest.get("host_trees", {})
    actual_codex_plugin_tree = tree_digest(codex_plugin)
    actual_claude_plugin_tree = tree_digest(claude_plugin)
    if host_trees.get("codex_plugin") != actual_codex_plugin_tree:
        findings.append("release manifest Codex host-tree digest mismatch")
    if host_trees.get("claude_plugin") != actual_claude_plugin_tree:
        findings.append("release manifest Claude host-tree digest mismatch")
    if not host_trees.get("codex_claude_skill_bytes_identical"):
        findings.append("release manifest does not establish host skill parity")
    release_rights = release_manifest.get("rights", {})
    if release_rights.get("redistribution_state") != REDISTRIBUTION_STATE:
        findings.append("release manifest does not preserve the approved redistribution state")
    if release_rights.get("external_rights_blockers") != [] or release_manifest.get("release_blockers") != []:
        findings.append("release manifest still contains external rights blockers")
    if release_rights.get("rights_bundle") != rights_hashes:
        findings.append("release manifest rights hashes differ from packaged rights files")
    if release_manifest.get("open_evidence_boundaries") != source_lock.get("open_evidence_boundaries"):
        findings.append("release manifest evidence boundaries differ from the frozen source lock")
    if release_manifest.get("publication_state") != "not_published":
        findings.append("release manifest overclaims publication")
    if release_manifest.get("archive_filename_encoding") != "strict_utf8_local_and_central_headers":
        findings.append("release manifest omits the UTF-8 archive filename contract")

    zips_root = package / "claude" / "zips"
    release_skill_records = release_manifest.get("skills")
    record_by_id: dict[str, dict[str, object]] = {}
    if not isinstance(release_skill_records, list):
        findings.append("release manifest skill records are missing or malformed")
    else:
        for record in release_skill_records:
            if not isinstance(record, dict) or not isinstance(record.get("id"), str):
                findings.append("release manifest contains a malformed skill record")
                continue
            skill_id = str(record["id"])
            if skill_id in record_by_id:
                findings.append(f"release manifest contains duplicate skill record: {skill_id}")
                continue
            record_by_id[skill_id] = record
    if set(record_by_id) != EXPECTED_ROOTS:
        findings.append("release manifest skill record inventory differs from the packaged roots")
    for skill_id in sorted(EXPECTED_ROOTS):
        zip_path = zips_root / f"{skill_id}-3.1.3.zip"
        if not zip_path.is_file():
            findings.append(f"missing Claude skill ZIP: {skill_id}")
            continue
        expected_files = files(folders / skill_id)
        expected_names = {f"{skill_id}/{path.relative_to(folders / skill_id).as_posix()}" for path in expected_files}
        name_problems = zip_filename_findings(zip_path, sorted(expected_names))
        for problem in name_problems:
            findings.append(f"Claude skill ZIP filename encoding failed for {skill_id}: {problem}")
        if not name_problems:
            with zipfile.ZipFile(zip_path) as archive:
                if set(archive.namelist()) != expected_names:
                    findings.append(f"Claude skill ZIP inventory mismatch: {skill_id}")
                else:
                    for path in expected_files:
                        name = f"{skill_id}/{path.relative_to(folders / skill_id).as_posix()}"
                        if archive.read(name) != path.read_bytes():
                            findings.append(f"Claude skill ZIP bytes differ from folder: {skill_id}/{path.relative_to(folders / skill_id).as_posix()}")
                            break
        record = record_by_id.get(skill_id, {})
        actual_payload_tree = tree_digest(codex_plugin / "skills" / skill_id)
        if record.get("payload_tree") != actual_payload_tree:
            findings.append(f"release manifest skill payload-tree mismatch: {skill_id}")
        if record.get("claude_zip") != f"claude/zips/{skill_id}-3.1.3.zip":
            findings.append(f"Claude skill ZIP path record mismatch: {skill_id}")
        if record.get("claude_zip_sha256") != sha256_file(zip_path):
            findings.append(f"Claude skill ZIP hash record mismatch: {skill_id}")
        if record.get("standalone_rights_envelope") != STANDALONE_RIGHTS_DIR:
            findings.append(f"Claude skill rights-envelope record missing: {skill_id}")
        if record.get("component_notice_bundle") != COMPONENT_NOTICE_MAP.get(skill_id):
            findings.append(f"Claude skill component-notice record mismatch: {skill_id}")

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
            "redistribution_state": release_rights.get("redistribution_state"),
            "external_rights_blockers": release_rights.get("external_rights_blockers"),
            "standalone_rights_envelopes": standalone_rights_count,
            "checksum_entries": checksum_entries,
            "candidate_states": {binding: state.get("candidate_state") for binding, state in build_states.items()},
            "publication_state": release_manifest.get("publication_state"),
        },
        "evidence_boundary": "Static package and rights-custody verification only. Fresh-host installation, discovery, enabled state, invocation, behavior, publication, and outcomes are not established.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Nova the Optimal AI Free package structure, bytes, and rights custody.")
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
