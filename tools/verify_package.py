"""Verify the Nova + MIND Free source tree and optional release artifacts."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOVA = ROOT / "plugins" / "nova-the-optimal-ai"
MIND = ROOT / "plugins" / "augment-of-mind"
PRODUCT_VERSION = "2.1.0"
NOVA_VERSION = "2.1.0"
MIND_VERSION = "2.2.0"
MIND_CORE_VERSION = "0.2.0"
CONTINUITY_VERSION = "0.2.0"
CONTINUITY_WORKSPACE_SCHEMA_VERSION = 2
MODEL_CONTEXT_CONTRACT = (
    ROOT / "verification" / "associative-smoke" / f"model-context-contract-v{MIND_VERSION}.json"
)

FACULTIES = {
    "aesthetic-intelligence", "agent-dreaming", "agent-striving", "agentic-eros",
    "capability-conductor", "cognitive-continuity", "creative-synthesis",
    "decision-intelligence", "deliberative-intelligence", "epistemic-regulation",
    "executive-function", "instrumental-agency", "kairos", "measurement-intelligence",
    "prosocial-influence", "sensemaking",
}
MIND_SKILLS = FACULTIES | {"augment-of-mind", "capability-promotion", "software-verification", "verification-reviewer"}
NOVA_SKILLS = {
    "nova", "promptcraft", "agentic-coding", "answerlayer", "ai-cognition-cost-optimizer",
    "corkboard", "current-intelligence-observatory", "dunbar", "omnara-deep-research",
    "retrieval-intelligence", "retrieval-reviewer", "rupert-giles-knowledge-steward",
    "privacy-redline", "signal-loom", "owen-burnett-officecraft", "officecraft-reviewer",
    "beryl-it-tech", "it-work-reviewer", "ludis-continuum",
    "lex-foster-language-companion", "gridmason",
}
EXCLUDED = {"aji-go-coach", "agent-arena-competition", "impactful-tom"}
NOVA_PERSONA_SHA256 = "b91b39b4122e76d0b01f9425581d2098c1434d69e851979064ddd4d9cef888c6"
PROMPT_DESIGN_SHA256 = "8de7b3b8f7b3e4a1ab07dc199d3160ba99be513fabf4795f80f679e3372b0afb"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def display_path(path: Path, base: Path = ROOT) -> str:
    """Render a repository- or package-relative path, or a safe absolute fallback."""
    resolved = path.resolve()
    try:
        return resolved.relative_to(base.resolve()).as_posix()
    except ValueError:
        return str(resolved)


def tree_fingerprint(root: Path) -> dict[str, object]:
    files = [
        path
        for path in root.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.suffix.lower() not in {".pyc", ".pyo"}
    ]
    digest = hashlib.sha256()
    for path in sorted(files, key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(relative)
        digest.update(b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return {"file_count": len(files), "tree_sha256": digest.hexdigest()}


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"invalid JSON {display_path(path)}: {exc}") from exc


def skill_metadata(path: Path) -> tuple[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"missing YAML frontmatter: {display_path(path)}")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError(f"unterminated YAML frontmatter: {display_path(path)}")
    frontmatter = text[4:end]
    name_match = re.search(r"(?m)^name:\s*[\"']?([^\"'\n]+)", frontmatter)
    desc_match = re.search(r"(?m)^description:\s*[\"']?(.+?)[\"']?\s*$", frontmatter)
    if not name_match or not desc_match:
        raise ValueError(f"name or description missing: {display_path(path)}")
    return name_match.group(1).strip(), desc_match.group(1).strip().rstrip('"').rstrip("'")


def verify_links(errors: list[str]) -> None:
    documents = [ROOT / "README.md", ROOT / "START-HERE.md", *sorted((ROOT / "docs").glob("*.md"))]
    pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    for document in documents:
        if not document.is_file():
            errors.append(f"required customer document missing: {document.relative_to(ROOT)}")
            continue
        text = document.read_text(encoding="utf-8")
        for raw in pattern.findall(text):
            target = raw.split("#", 1)[0].strip().strip("<>")
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            candidate = (document.parent / target).resolve()
            try:
                candidate.relative_to(ROOT.resolve())
            except ValueError:
                errors.append(f"documentation link escapes repository: {document.relative_to(ROOT)} -> {raw}")
                continue
            if not candidate.exists():
                errors.append(f"broken documentation link: {document.relative_to(ROOT)} -> {raw}")


def verify_release_links(errors: list[str], release_root: Path) -> None:
    documents = [
        release_root / "README.md",
        release_root / "START-HERE.md",
        *sorted((release_root / "docs").glob("*.md")),
    ]
    pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    for document in documents:
        shown_document = display_path(document, release_root)
        if not document.is_file():
            errors.append(f"required release document missing: {shown_document}")
            continue
        text = document.read_text(encoding="utf-8")
        for raw in pattern.findall(text):
            target = raw.split("#", 1)[0].strip().strip("<>")
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            candidate = (document.parent / target).resolve()
            try:
                candidate.relative_to(release_root.resolve())
            except ValueError:
                errors.append(
                    "release documentation link escapes package: "
                    f"{shown_document} -> {raw}"
                )
                continue
            if not candidate.exists():
                errors.append(
                    "broken release documentation link: "
                    f"{shown_document} -> {raw}"
                )


def verify_release(errors: list[str], release_root: Path) -> None:
    release_root = release_root.resolve()
    codex_plugins = release_root / "codex" / "plugins"
    claude_folders = release_root / "claude" / "folders"
    claude_zips = release_root / "claude" / "zips"
    missing = False
    for path in (
        codex_plugins / "nova-the-optimal-ai",
        codex_plugins / "augment-of-mind",
        claude_folders,
        claude_zips,
    ):
        if not path.exists():
            errors.append(f"release path missing: {display_path(path, release_root)}")
            missing = True
    if missing:
        return
    verify_release_links(errors, release_root)
    expected = NOVA_SKILLS | MIND_SKILLS
    folders = {path.name for path in claude_folders.iterdir() if path.is_dir()}
    if folders != expected:
        errors.append(f"Claude folder set mismatch: expected {len(expected)}, found {len(folders)}")
    zips = {path.stem for path in claude_zips.glob("*.zip")}
    if zips != expected:
        errors.append(f"Claude ZIP set mismatch: expected {len(expected)}, found {len(zips)}")
    for name in sorted(expected):
        archive = claude_zips / f"{name}.zip"
        if not archive.is_file():
            continue
        with zipfile.ZipFile(archive) as bundle:
            entries = [item.filename for item in bundle.infolist() if not item.is_dir()]
        if not entries or any(not entry.startswith(f"{name}/") for entry in entries):
            errors.append(
                "Claude ZIP has wrong top-level folder: "
                f"{display_path(archive, release_root)}"
            )
        if f"{name}/SKILL.md" not in entries:
            errors.append(
                f"Claude ZIP lacks direct SKILL.md: {display_path(archive, release_root)}"
            )
        folder_entry = claude_folders / name / "SKILL.md"
        try:
            declared, description = skill_metadata(folder_entry)
            if declared != name:
                errors.append(f"Claude folder name mismatch: {name} declares {declared}")
            if not (1 <= len(description) <= 200):
                errors.append(
                    f"Claude description length invalid ({len(description)}): "
                    f"{display_path(folder_entry, release_root)}"
                )
        except ValueError as exc:
            errors.append(str(exc))


def verify(include_release: bool, release_root: Path | None = None) -> dict:
    errors: list[str] = []
    evidence: dict = {}

    for path in ROOT.rglob("*"):
        if path.is_symlink():
            errors.append(f"symlink not allowed: {path.relative_to(ROOT)}")
        if path.is_file() and (path.suffix == ".pyc" or "__pycache__" in path.parts):
            errors.append(f"cache artifact not allowed: {path.relative_to(ROOT)}")

    nova_manifest = load_json(NOVA / ".codex-plugin" / "plugin.json")
    mind_manifest = load_json(MIND / ".codex-plugin" / "plugin.json")
    if nova_manifest.get("version") != NOVA_VERSION:
        errors.append(f"Nova plugin version must be {NOVA_VERSION}")
    if mind_manifest.get("version") != MIND_VERSION:
        errors.append(f"MIND plugin version must be {MIND_VERSION}")

    mind_version = str(mind_manifest.get("version", ""))
    if "mcpServers" in mind_manifest:
        errors.append("MIND plugin manifest still registers an MCP server")
    for removed_path in (
        MIND / ".mcp.json",
        MIND / "mind_core" / "mcp_server.py",
        MIND / "scripts" / "mind_mcp_server.py",
    ):
        if removed_path.exists():
            errors.append(f"removed MIND runtime path still exists: {removed_path.relative_to(ROOT)}")

    standalone_verifier_text = (MIND / "scripts" / "verify_release.py").read_text(encoding="utf-8")
    standalone_version = re.search(r'(?m)^PLUGIN_VERSION = "([^"]+)"$', standalone_verifier_text)
    if not standalone_version or standalone_version.group(1) != mind_version:
        errors.append("standalone MIND release verifier version does not match the plugin manifest")

    eval_manifest = load_json(MIND / "skills" / "augment-of-mind" / "evals" / "eval-manifest.yaml")
    eval_cases = load_json(MIND / "skills" / "augment-of-mind" / "evals" / "faculty-runtime-cases.yaml")
    registry = load_json(MIND / "skills" / "augment-of-mind" / "references" / "faculty-runtime" / "faculty-registry.json")
    evaluation_baseline = "2.1.1"
    if eval_manifest.get("package_version") != evaluation_baseline or eval_cases.get("package_version") != evaluation_baseline:
        errors.append("MIND Faculty evaluation evidence no longer identifies its 2.1.1 baseline")
    if registry.get("runtime_version") != mind_version:
        errors.append("MIND Faculty registry version does not match the plugin version")
    registered_faculties = {
        item.get("name") for item in registry.get("faculties", []) if isinstance(item, dict)
    }
    if registry.get("faculty_count") != len(FACULTIES) or registered_faculties != FACULTIES:
        errors.append("MIND Faculty registry does not match the sixteen-Faculty contract")
    faculty_return_schema = load_json(
        MIND
        / "skills"
        / "augment-of-mind"
        / "assets"
        / "faculty-runtime"
        / "faculty-return.schema.json"
    )
    return_faculties = set(
        faculty_return_schema.get("properties", {}).get("faculty", {}).get("enum", [])
    )
    if return_faculties != FACULTIES:
        errors.append("MIND Faculty return schema does not cover the sixteen-Faculty registry")

    core_constants_text = (MIND / "mind_core" / "constants.py").read_text(encoding="utf-8")
    core_match = re.search(r'(?m)^RUNTIME_VERSION = "([^"]+)"$', core_constants_text)
    if not core_match or core_match.group(1) != MIND_CORE_VERSION:
        errors.append(f"MIND Core runtime version must remain {MIND_CORE_VERSION}")
    standalone_core_match = re.search(
        r'(?m)^CORE_VERSION = "([^"]+)"$', standalone_verifier_text
    )
    if not standalone_core_match or standalone_core_match.group(1) != MIND_CORE_VERSION:
        errors.append("standalone MIND release verifier Core version is stale")
    core_project = tomllib.loads((MIND / "pyproject.toml").read_text(encoding="utf-8"))
    if core_project.get("project", {}).get("version") != MIND_CORE_VERSION:
        errors.append("MIND Core project version is stale")

    continuity_root = MIND / "skills" / "cognitive-continuity"
    workspace_runtime_text = (
        continuity_root / "scripts" / "workspace_runtime.py"
    ).read_text(encoding="utf-8")
    continuity_match = re.search(
        r'(?m)^IMPLEMENTATION_VERSION = "([^"]+)"$', workspace_runtime_text
    )
    if not continuity_match or continuity_match.group(1) != CONTINUITY_VERSION:
        errors.append(f"Cognitive Continuity implementation version must be {CONTINUITY_VERSION}")
    if 'FORMAT = "cd-cognitive-continuity/v2"' not in workspace_runtime_text:
        errors.append("Cognitive Continuity workspace runtime is not schema v2")
    continuity_manifest_schema = load_json(
        continuity_root / "assets" / "schemas" / "continuity-manifest-v2.schema.json"
    )
    schema_version = (
        continuity_manifest_schema.get("properties", {})
        .get("workspace_schema_version", {})
        .get("const")
    )
    if schema_version != CONTINUITY_WORKSPACE_SCHEMA_VERSION:
        errors.append("Cognitive Continuity manifest schema version is stale")
    worldline_text = (continuity_root / "scripts" / "worldline.py").read_text(encoding="utf-8")
    for required_worldline_phrase in (
        'REQUEST_FORMAT = "cd-worldline-request/v1"',
        'VIEW_FORMAT = "cd-worldline-view/v1"',
        "RUNTIME_VERSION = IMPLEMENTATION_VERSION",
    ):
        if required_worldline_phrase not in worldline_text:
            errors.append(f"Worldline runtime contract is missing: {required_worldline_phrase}")
    faultline_text = (
        continuity_root / "scripts" / "error_neighborhood.py"
    ).read_text(encoding="utf-8")
    for required_faultline_phrase in (
        'POLICY_VERSION = "cd-continuity-eligibility/v2"',
        '"cd-error-neighborhood/v1"',
        "operation_unsupported_v1",
    ):
        if required_faultline_phrase not in faultline_text:
            errors.append(f"Faultline runtime contract is missing: {required_faultline_phrase}")

    fingerprint_path = MIND / "skills" / "augment-of-mind" / "assets" / "integrated-capability-fingerprint.json"
    fingerprint_builder_path = MIND / "scripts" / "build_integrated_fingerprint.py"
    spec = importlib.util.spec_from_file_location("mind_integrated_fingerprint", fingerprint_builder_path)
    if spec is None or spec.loader is None:
        errors.append("cannot load the integrated fingerprint builder")
    else:
        module = importlib.util.module_from_spec(spec)
        prior_dont_write_bytecode = sys.dont_write_bytecode
        try:
            sys.dont_write_bytecode = True
            spec.loader.exec_module(module)
        finally:
            sys.dont_write_bytecode = prior_dont_write_bytecode
        observed_fingerprint = load_json(fingerprint_path)
        expected_fingerprint = module.build()
        expected_capability_versions = {
            item.get("name"): item.get("version")
            for item in expected_fingerprint.get("capabilities", [])
            if isinstance(item, dict)
        }
        if expected_capability_versions.get("cognitive-continuity") != CONTINUITY_VERSION:
            errors.append("integrated fingerprint builder has a stale Cognitive Continuity version")
        if observed_fingerprint != expected_fingerprint:
            errors.append("integrated MIND capability fingerprint is stale")
            evidence["expected_integrated_fingerprint"] = expected_fingerprint
        if observed_fingerprint.get("product_version") != mind_version:
            errors.append("integrated MIND fingerprint version does not match the plugin version")

    hook_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            MIND / "hooks" / "mind_prompt_submit.py",
            MIND / "mind_core" / "hook_context.py",
            MIND / "mind_core" / "hook_delivery.py",
            MIND / "mind_core" / "model_context.py",
        )
    )
    for forbidden_hook_phrase in (
        "do not call MCP tools or resource readers",
        "read_mcp_resource",
        "associate_capabilities",
        "hook-delivered advisory associative disclosure",
        "consider exploring candidate capacities",
        "tools/skills/mcps from harness configuration",
    ):
        if forbidden_hook_phrase in hook_text:
            errors.append(f"obsolete MCP routing instruction remains in the MIND hook: {forbidden_hook_phrase}")
    for required_hook_phrase in (
        "association_context(event)",
        "embed_membranes",
        '"anchor_kind": "turn_context"',
        "**Vector-near semantically related capabilities below**",
        "capabilities already present in assembled context",
        "surveyed memory may extend beyond the current harness",
        "model_context_text",
    ):
        if required_hook_phrase not in hook_text:
            errors.append(f"semantic Arm's Reach hook contract is missing: {required_hook_phrase}")
    for forbidden_hook_phrase in (
        "HookDeferred",
        "CONTEXTUAL ASSOCIATION DEFERRED",
        "ordinary filesystem skill discovery",
        "local association adapter",
        "local H0 query adapter",
    ):
        if forbidden_hook_phrase in hook_text:
            errors.append(f"model-side Arm's Reach retrieval remains in the hook: {forbidden_hook_phrase}")

    delivery_text = (MIND / "mind_core" / "delivery.py").read_text(encoding="utf-8")
    for required_delivery_phrase in (
        "model_context_text(raw_text)",
        "VECTOR_BACKED_MODES",
        "model-facing delivery requires a vector-backed field",
    ):
        if required_delivery_phrase not in delivery_text:
            errors.append(f"portable delivery contract is missing: {required_delivery_phrase}")

    contract = load_json(
        MODEL_CONTEXT_CONTRACT
    )
    if contract.get("mind_version") != mind_version:
        errors.append("recorded model-context contract version does not match MIND")
    if contract.get("header") not in hook_text:
        errors.append("recorded model-context header does not match runtime source")
    if contract.get("nonvector_delivery") != "degraded":
        errors.append("recorded model-context contract does not preserve degraded nonvector delivery")
    if contract.get("catalog_discovery") != "not_prompted":
        errors.append("recorded model-context contract prompts capability-catalog discovery")

    nova_skill_text = (NOVA / "skills" / "nova" / "SKILL.md").read_text(encoding="utf-8")
    mind_skill_text = (MIND / "skills" / "augment-of-mind" / "SKILL.md").read_text(encoding="utf-8")
    for document_name, document_text in (("Nova", nova_skill_text), ("MIND", mind_skill_text)):
        if "hook owns" not in document_text and "hook owns Arm's Reach" not in document_text:
            errors.append(f"{document_name} skill does not assign Arm's Reach retrieval to the hook")
        for stale_phrase in ("local association adapter", "local H0 query adapter"):
            if stale_phrase in document_text:
                errors.append(f"{document_name} skill still requests model-side association: {stale_phrase}")

    release_url = "https://github.com/Stunspot/nova-the-optimal-ai-mind/releases/latest"
    for download_surface in (ROOT / "README.md", ROOT / "START-HERE.md", ROOT / "docs" / "index.html"):
        if release_url not in download_surface.read_text(encoding="utf-8"):
            errors.append(f"current release download is missing: {download_surface.relative_to(ROOT)}")

    package_map_text = (ROOT / "design" / "FREE-NOVA-PACKAGE-MAP.md").read_text(encoding="utf-8")
    if f"Product: **Nova + MIND Free {PRODUCT_VERSION}**" not in package_map_text:
        errors.append("Free Nova package map version is stale")
    if "Canonical repository: `Stunspot/nova-the-optimal-ai-mind`" not in package_map_text:
        errors.append("Free Nova package map points at the wrong canonical repository")

    stale_customer_phrases = {
        ROOT / "docs" / "PRIVACY-AND-TRUST.md": ("association-service code", "reminder service"),
        ROOT / "docs" / "INSTALL-CODEX.md": ("reminder service",),
        MIND / "INSTALL-CODEX.md": ("reminder service",),
        MIND / "HOST-COMPATIBILITY.md": ("reminder service",),
        MIND / "DATA-AND-PRIVACY.md": ("reminder service",),
        MIND / "TROUBLESHOOTING.md": ("reminder service",),
    }
    for document, phrases in stale_customer_phrases.items():
        text = document.read_text(encoding="utf-8")
        for phrase in phrases:
            if phrase in text:
                errors.append(f"stale architecture phrase remains in {document.relative_to(ROOT)}: {phrase}")

    nova_dirs = {path.name for path in (NOVA / "skills").iterdir() if path.is_dir()}
    mind_dirs = {path.name for path in (MIND / "skills").iterdir() if path.is_dir()}
    if nova_dirs != NOVA_SKILLS:
        errors.append(f"Nova skill set mismatch: missing={sorted(NOVA_SKILLS-nova_dirs)}, extra={sorted(nova_dirs-NOVA_SKILLS)}")
    if mind_dirs != MIND_SKILLS:
        errors.append(f"MIND skill set mismatch: missing={sorted(MIND_SKILLS-mind_dirs)}, extra={sorted(mind_dirs-MIND_SKILLS)}")
    if (nova_dirs | mind_dirs) & EXCLUDED:
        errors.append("release-excluded capability found in runtime skill roots")
    if nova_dirs & mind_dirs:
        errors.append(f"duplicate skill handles across plugins: {sorted(nova_dirs & mind_dirs)}")

    for root, names in ((NOVA / "skills", nova_dirs), (MIND / "skills", mind_dirs)):
        for name in sorted(names):
            entry = root / name / "SKILL.md"
            if not entry.is_file():
                errors.append(f"SKILL.md missing: {entry.relative_to(ROOT)}")
                continue
            try:
                declared, description = skill_metadata(entry)
            except ValueError as exc:
                errors.append(str(exc))
                continue
            if declared != name:
                errors.append(f"skill name mismatch: {entry.relative_to(ROOT)} declares {declared}")
            if not (1 <= len(description) <= 1024):
                errors.append(f"source description length invalid ({len(description)}): {entry.relative_to(ROOT)}")

    persona = NOVA / "skills" / "nova" / "references" / "nova-persona.md"
    if sha256(persona) != NOVA_PERSONA_SHA256 or len(persona.read_bytes()) != 3122:
        errors.append("canonical Nova persona bytes changed")
    prompt_design = NOVA / "skills" / "promptcraft" / "references" / "prompt-design.md"
    if sha256(prompt_design) != PROMPT_DESIGN_SHA256:
        errors.append("canonical Promptcraft doctrine bytes changed")
    if "Chapel Perilous" not in (MIND / "skills" / "software-verification" / "SKILL.md").read_text(encoding="utf-8"):
        errors.append("current TestForge policy revision is not present")

    cards = load_json(ROOT / "bundle" / "reminder" / "associative-capability-cards.json")
    bootstrap = load_json(ROOT / "bundle" / "reminder" / "associative-bootstrap.json")
    index = load_json(ROOT / "bundle" / "reminder" / "associative-index-qwen3-embedding-0.6b.json")
    card_handles = {card.get("handle") for card in cards.get("cards", [])}
    if card_handles != NOVA_SKILLS | MIND_SKILLS:
        errors.append("reminder card handles do not match the 41 shipped skills")
    if len(bootstrap.get("capabilities", [])) != 41:
        errors.append("reminder bootstrap must contain 41 capabilities")
    if len(index.get("cards", [])) != 41 or len(index.get("vectors", [])) != 246:
        errors.append("associative index must contain 41 cards and 246 vectors")
    profile = index.get("embedding_profile", {})
    if profile.get("qualification_state") != "unqualified":
        errors.append("expanded profile must remain unqualified until its separate qualification passes")
    if profile.get("radius") != 0.33:
        errors.append("expanded profile radius must match the smoke-tuned 0.33 contract")

    market = load_json(ROOT / ".agents" / "plugins" / "marketplace.json")
    if market.get("name") != "collaborative-dynamics-nova-free":
        errors.append("marketplace name mismatch")
    if {item.get("name") for item in market.get("plugins", [])} != {"nova-the-optimal-ai", "augment-of-mind"}:
        errors.append("marketplace must expose exactly the Nova and MIND plugins")

    runtime_text = "\n".join(path.read_text(encoding="utf-8", errors="ignore").casefold() for base in (NOVA, MIND) for path in base.rglob("*") if path.is_file() and path.suffix.lower() in {".md", ".json", ".py", ".yaml", ".yml"})
    for token in EXCLUDED:
        if token in runtime_text:
            errors.append(f"release-excluded capability named in runtime payload: {token}")

    lock = load_json(ROOT / "design" / "source-lock.json")
    if len(lock.get("records", [])) != 24 or lock.get("contest_repository_mutated") is not False:
        errors.append("source lock does not preserve the 24-record frozen-contest contract")
    expected_tree_algorithm = (
        "sha256 over skill-relative UTF-8 POSIX path in ordinal exact-case order, "
        "one NUL byte, and raw 32-byte file sha256; Python cache files excluded"
    )
    if lock.get("product_version") != PRODUCT_VERSION or lock.get("tree_algorithm") != expected_tree_algorithm:
        errors.append("source lock version or tree algorithm is stale")
    locked_records = {
        item.get("component"): item
        for item in lock.get("records", [])
        if isinstance(item, dict)
    }
    expected_current_sources = {
        "nova": {
            "repository": "https://github.com/Stunspot/nova-the-optimal-ai-mind",
            "commit": "a678d72049f99e999ccd4278ef9596adc0a0743e",
            "source_path": "plugins/nova-the-optimal-ai/skills/nova",
            "imported_path": "plugins/nova-the-optimal-ai/skills/nova",
        },
        "augment-of-mind": {
            "repository": "https://github.com/Stunspot/nova-the-optimal-ai-mind",
            "commit": "a678d72049f99e999ccd4278ef9596adc0a0743e",
            "source_path": "plugins/augment-of-mind/skills",
            "imported_path": "plugins/augment-of-mind/skills",
        },
        "software-verification": {
            "repository": "https://github.com/Stunspot/testforge",
            "commit": "e9a7fb1b88f537f05ef77c921d4d63698e1346a0",
            "source_path": "testforge/skills/software-verification",
            "imported_path": "plugins/augment-of-mind/skills/software-verification",
        },
        "verification-reviewer": {
            "repository": "https://github.com/Stunspot/testforge",
            "commit": "e9a7fb1b88f537f05ef77c921d4d63698e1346a0",
            "source_path": "testforge/skills/verification-reviewer",
            "imported_path": "plugins/augment-of-mind/skills/verification-reviewer",
        },
    }
    for component, expected_source in expected_current_sources.items():
        record = locked_records.get(component)
        if not isinstance(record, dict):
            errors.append(f"source lock lacks current record: {component}")
            continue
        for record_key, expected_key in (
            ("source_repository", "repository"),
            ("source_commit", "commit"),
            ("source_path", "source_path"),
            ("imported_path", "imported_path"),
        ):
            if record.get(record_key) != expected_source[expected_key]:
                errors.append(f"source lock {record_key} is stale: {component}")
        observed_tree = tree_fingerprint(ROOT / expected_source["imported_path"])
        if record.get("imported_tree") != observed_tree:
            errors.append(f"source lock imported tree is stale: {component}")
        if record.get("source_tree") != observed_tree:
            errors.append(f"source lock canonical tree does not match imported bytes: {component}")

    ludis_record = locked_records.get("ludis-continuum")
    expected_ludis = {
        "source_repository": "https://github.com/Stunspot/ludis-continuum",
        "source_commit": "e20d8ee88538e1e5a62ba9f18b5224ebedaa05df",
        "source_path": ".",
        "imported_path": "plugins/nova-the-optimal-ai/skills/ludis-continuum",
        "source_tree": {
            "file_count": 122,
            "tree_sha256": "a79c66757df392747f811331679937b0d1bba534a45a1945286e5b4c295a7a22",
        },
        "selection_excludes": [".github/**", ".editorconfig", ".gitattributes", ".gitignore"],
        "selected_tree": {
            "file_count": 117,
            "tree_sha256": "d013ded89c075bcbf0f80a248635e30f2c94b6a8602ca8330bc7281fa81e77da",
        },
    }
    if not isinstance(ludis_record, dict):
        errors.append("source lock lacks current record: ludis-continuum")
    else:
        for key, expected_value in expected_ludis.items():
            if key in {"selected_tree", "imported_path"}:
                continue
            if ludis_record.get(key) != expected_value:
                errors.append(f"source lock {key} is stale: ludis-continuum")
        observed_ludis_tree = tree_fingerprint(ROOT / expected_ludis["imported_path"])
        if observed_ludis_tree != expected_ludis["selected_tree"]:
            errors.append("embedded Ludis tree does not match the approved 1.1.0 selection")
        if ludis_record.get("selected_tree") != observed_ludis_tree:
            errors.append("source lock selected tree is stale: ludis-continuum")
        if ludis_record.get("imported_tree") != observed_ludis_tree:
            errors.append("source lock imported tree is stale: ludis-continuum")
        if ludis_record.get("imported_path") != expected_ludis["imported_path"]:
            errors.append("source lock imported path is stale: ludis-continuum")

    verify_links(errors)

    site_check = ROOT / "docs" / "check_site.py"
    if not site_check.is_file():
        errors.append("Pages site checker is missing")
    for required_asset in (
        ROOT / "docs" / "assets" / "nova-mind-readme-hero.png",
        ROOT / "docs" / "assets" / "nova-mind-pages-hero.png",
        ROOT / "docs" / "assets" / "nova-mind-social-card.png",
    ):
        if not required_asset.is_file():
            errors.append(f"required presentation asset missing: {required_asset.relative_to(ROOT)}")

    selected_release_root = (
        release_root.expanduser().resolve() if release_root is not None else ROOT / "dist"
    )
    if include_release:
        verify_release(errors, selected_release_root)

    evidence.update({
        "product_version": PRODUCT_VERSION,
        "nova_plugin_version": NOVA_VERSION,
        "mind_plugin_version": MIND_VERSION,
        "mind_core_version": MIND_CORE_VERSION,
        "cognitive_continuity_version": CONTINUITY_VERSION,
        "continuity_workspace_schema_version": CONTINUITY_WORKSPACE_SCHEMA_VERSION,
        "nova_skill_count": len(nova_dirs),
        "mind_skill_count": len(mind_dirs),
        "faculty_count": len(FACULTIES),
        "total_skill_count": len(nova_dirs | mind_dirs),
        "reminder_card_count": len(cards.get("cards", [])),
        "reminder_vector_count": len(index.get("vectors", [])),
        "reminder_radius": profile.get("radius"),
        "reminder_qualification_state": profile.get("qualification_state"),
        "release_checked": include_release,
        "release_root": display_path(selected_release_root) if include_release else None,
        "errors": errors,
        "status": "PASS" if not errors else "FAIL",
    })
    return evidence


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release", action="store_true")
    parser.add_argument(
        "--release-root",
        type=Path,
        metavar="DIST_PATH",
        help="verify release artifacts at DIST_PATH instead of repository dist/; implies --release",
    )
    args = parser.parse_args(argv)
    release_root = args.release_root.expanduser().resolve() if args.release_root else None
    evidence = verify(args.release or release_root is not None, release_root)
    print(json.dumps(evidence, indent=2, ensure_ascii=False))
    return 0 if evidence["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
