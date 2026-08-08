"""Verify the Nova + MIND Free source tree and optional release artifacts."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOVA = ROOT / "plugins" / "nova-the-optimal-ai"
MIND = ROOT / "plugins" / "augment-of-mind"

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


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"invalid JSON {path.relative_to(ROOT)}: {exc}") from exc


def skill_metadata(path: Path) -> tuple[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"missing YAML frontmatter: {path.relative_to(ROOT)}")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError(f"unterminated YAML frontmatter: {path.relative_to(ROOT)}")
    frontmatter = text[4:end]
    name_match = re.search(r"(?m)^name:\s*[\"']?([^\"'\n]+)", frontmatter)
    desc_match = re.search(r"(?m)^description:\s*[\"']?(.+?)[\"']?\s*$", frontmatter)
    if not name_match or not desc_match:
        raise ValueError(f"name or description missing: {path.relative_to(ROOT)}")
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


def verify_release_links(errors: list[str]) -> None:
    release_root = ROOT / "dist"
    documents = [
        release_root / "README.md",
        release_root / "START-HERE.md",
        *sorted((release_root / "docs").glob("*.md")),
    ]
    pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    for document in documents:
        if not document.is_file():
            errors.append(
                f"required release document missing: {document.relative_to(ROOT)}"
            )
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
                    f"{document.relative_to(ROOT)} -> {raw}"
                )
                continue
            if not candidate.exists():
                errors.append(
                    "broken release documentation link: "
                    f"{document.relative_to(ROOT)} -> {raw}"
                )

def verify_release(errors: list[str]) -> None:
    release_root = ROOT / "dist"
    codex_plugins = release_root / "codex" / "plugins"
    claude_folders = release_root / "claude" / "folders"
    claude_zips = release_root / "claude" / "zips"
    for path in (codex_plugins / "nova-the-optimal-ai", codex_plugins / "augment-of-mind", claude_folders, claude_zips):
        if not path.exists():
            errors.append(f"release path missing: {path.relative_to(ROOT)}")
    if errors:
        return
    verify_release_links(errors)
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
            errors.append(f"Claude ZIP has wrong top-level folder: {archive.relative_to(ROOT)}")
        if f"{name}/SKILL.md" not in entries:
            errors.append(f"Claude ZIP lacks direct SKILL.md: {archive.relative_to(ROOT)}")
        folder_entry = claude_folders / name / "SKILL.md"
        try:
            declared, description = skill_metadata(folder_entry)
            if declared != name:
                errors.append(f"Claude folder name mismatch: {name} declares {declared}")
            if not (1 <= len(description) <= 200):
                errors.append(f"Claude description length invalid ({len(description)}): {folder_entry.relative_to(ROOT)}")
        except ValueError as exc:
            errors.append(str(exc))


def verify(include_release: bool) -> dict:
    errors: list[str] = []
    evidence: dict = {}

    for path in ROOT.rglob("*"):
        if path.is_symlink():
            errors.append(f"symlink not allowed: {path.relative_to(ROOT)}")
        if path.is_file() and (path.suffix == ".pyc" or "__pycache__" in path.parts):
            errors.append(f"cache artifact not allowed: {path.relative_to(ROOT)}")

    nova_manifest = load_json(NOVA / ".codex-plugin" / "plugin.json")
    mind_manifest = load_json(MIND / ".codex-plugin" / "plugin.json")
    if nova_manifest.get("version") != "2.0.1":
        errors.append("Nova plugin version must be 2.0.1")
    if mind_manifest.get("version") != "2.1.5":
        errors.append("MIND plugin version must be 2.1.5")

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
        ROOT / "verification" / "associative-smoke" / "model-context-contract-v2.1.5.json"
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
    if "Product: **Nova + MIND Free 2.0.7**" not in package_map_text:
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

    verify_links(errors)
    if include_release:
        verify_release(errors)

    evidence.update({
        "nova_skill_count": len(nova_dirs),
        "mind_skill_count": len(mind_dirs),
        "faculty_count": len(FACULTIES),
        "total_skill_count": len(nova_dirs | mind_dirs),
        "reminder_card_count": len(cards.get("cards", [])),
        "reminder_vector_count": len(index.get("vectors", [])),
        "reminder_radius": profile.get("radius"),
        "reminder_qualification_state": profile.get("qualification_state"),
        "release_checked": include_release,
        "errors": errors,
        "status": "PASS" if not errors else "FAIL",
    })
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release", action="store_true")
    args = parser.parse_args()
    evidence = verify(args.release)
    print(json.dumps(evidence, indent=2, ensure_ascii=False))
    return 0 if evidence["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
