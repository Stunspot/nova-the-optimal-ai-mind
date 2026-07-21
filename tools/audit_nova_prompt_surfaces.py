#!/usr/bin/env python3
"""Generate or check Nova's complete package-owned prompt-surface ledger."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
PLUGIN = REPO / "plugins" / "nova-the-optimal-ai"
JSON_OUT = REPO / "verification" / "nova-prompt-surface-audit.json"
MD_OUT = REPO / "verification" / "nova-prompt-surface-audit.md"

SKILLS = (
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
)

DIRECT_NOVA_REFS = (
    "nova-persona.md",
    "capability-routing.md",
    "mind-compatibility.md",
    "take-the-tour.md",
    "cd-brand-canon.md",
)

PRIMARY_CHANGED = {
    "plugins/nova-the-optimal-ai/skills/agentic-coding/agents/openai.yaml",
    "plugins/nova-the-optimal-ai/skills/corkboard/agents/openai.yaml",
    "plugins/nova-the-optimal-ai/skills/dunbar/SKILL.md",
    "plugins/nova-the-optimal-ai/skills/dunbar/agents/openai.yaml",
    "plugins/nova-the-optimal-ai/skills/ludis-continuum/SKILL.md",
    "plugins/nova-the-optimal-ai/skills/ludis-continuum/agents/openai.yaml",
    "plugins/nova-the-optimal-ai/skills/nova/SKILL.md",
    "plugins/nova-the-optimal-ai/skills/omnara-deep-research/SKILL.md",
    "plugins/nova-the-optimal-ai/skills/omnara-deep-research/agents/openai.yaml",
    "plugins/nova-the-optimal-ai/skills/retrieval-intelligence/SKILL.md",
    "plugins/nova-the-optimal-ai/skills/retrieval-intelligence/agents/openai.yaml",
    "plugins/nova-the-optimal-ai/skills/signal-loom/SKILL.md",
    "plugins/nova-the-optimal-ai/skills/software-verification/SKILL.md",
    "plugins/nova-the-optimal-ai/skills/nova/references/take-the-tour.md",
}

REVIEW_CLASSES = {
    "primary-retained": "Already concept-first, discriminating, and bounded; retained after direct review.",
    "primary-repaired": "Salience, routing, authority, privacy, or evidence language was surgically repaired.",
    "governed-people-retained": "People context stays user-governed, relevance-gated, layered, and recoverable.",
    "ludis-doctrine-retained": "Choice, consequence, consent, tone, and continuity already form strong creative bearings.",
    "ludis-boundary-repaired": "Curated instruments are creative bearings, never authority or a route to unavailable legacy machinery.",
    "ludis-core-repaired": "The core now leads with the creative transformation and preserves canon, agency, and usable form without framework theater.",
    "ludis-index-repaired": "Routing now distinguishes all 32 creative instruments by the transformation each performs.",
    "ludis-fallback-retained": "Degraded routes preserve choice-shaped usefulness without pretending unavailable capability.",
    "omnara-retained": "Research doctrine remains question-led, source-aware, bounded, and explicit about uncertainty.",
    "omnara-directive-repaired": "The legacy directive was replaced by compact evidence-architecture bearings without quotas or platform assumptions.",
    "retrieval-retained": "Retrieval doctrine cleanly separates corpus evidence, authority, coverage, and truth.",
    "rupert-retained": "Knowledge custody remains organized around authority, provenance, finding journeys, and recovery.",
    "signal-retained": "Visual-story doctrine preserves source boundaries, representation integrity, accessibility, and human publication control.",
    "signal-faculty-repaired": "The optional faculty library now yields to the live stage and evidence, forbidding ornamental data, tool, and platform assumptions.",
    "testforge-retained": "Verification modules remain risk-shaped, oracle-led, evidence-bounded, and explicit about claim scope.",
    "testforge-authority-repaired": "Host overlays now inherit already-granted in-scope change authority while preserving genuine external authority edges.",
}


def rel(path: Path) -> str:
    return path.relative_to(REPO).as_posix()


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def glob_md(path: Path, recursive: bool = False) -> list[Path]:
    method = path.rglob if recursive else path.glob
    return sorted(method("*.md"))


def primary_paths() -> list[tuple[str, Path]]:
    rows: list[tuple[str, Path]] = [("plugin_manifest", PLUGIN / ".codex-plugin" / "plugin.json")]
    for skill in SKILLS:
        root = PLUGIN / "skills" / skill
        rows.extend((("skill_prompt", root / "SKILL.md"), ("openai_discovery_prompt", root / "agents" / "openai.yaml")))
    nova_refs = PLUGIN / "skills" / "nova" / "references"
    rows.extend(("nova_direct_reference", nova_refs / name) for name in DIRECT_NOVA_REFS)
    return rows


def conditional_paths() -> list[Path]:
    skills = PLUGIN / "skills"
    paths: list[Path] = []
    paths += glob_md(skills / "dunbar" / "references")

    ludis = skills / "ludis-continuum"
    paths += [
        ludis / "knowledge" / "canonical-boundaries.md",
        ludis / "knowledge" / "operating-doctrine.md",
        ludis / "knowledge" / "state-and-authority.md",
    ]
    paths += glob_md(ludis / "knowledge" / "instruments")
    paths += glob_md(ludis / "fallbacks")

    omnara = skills / "omnara-deep-research"
    paths += [
        omnara / "personas" / "omnara-investigative-research-intelligence.md",
        omnara / "knowledge" / "source-navigation.md",
    ]
    paths += glob_md(omnara / "references", recursive=True)
    paths += glob_md(omnara / "fallbacks")

    paths += glob_md(skills / "retrieval-intelligence" / "references")
    paths += glob_md(skills / "retrieval-reviewer" / "references")
    paths += glob_md(skills / "rupert-giles-knowledge-steward" / "references")
    paths += glob_md(skills / "signal-loom" / "knowledge")
    paths += glob_md(skills / "signal-loom" / "fallbacks")

    for skill in ("software-verification", "verification-reviewer"):
        root = skills / skill
        paths += glob_md(root / "adapters")
        paths += glob_md(root / "fallback")
        paths += glob_md(root / "references", recursive=True)
    reviewer = skills / "verification-reviewer"
    paths += [reviewer / "adversarial-checks.md", reviewer / "review-rubric.md"]
    return sorted(set(paths))


def classify(path: Path) -> tuple[str, str]:
    p = rel(path)
    if "/dunbar/" in p:
        return "dunbar", "governed-people-retained"
    if "/ludis-continuum/" in p:
        if p.endswith("/knowledge/canonical-boundaries.md"):
            return "ludis-continuum", "ludis-boundary-repaired"
        if "/knowledge/instruments/" in p:
            if p.endswith("/index.md"):
                return "ludis-continuum", "ludis-index-repaired"
            return "ludis-continuum", "ludis-core-repaired"
        if "/fallbacks/" in p:
            return "ludis-continuum", "ludis-fallback-retained"
        return "ludis-continuum", "ludis-doctrine-retained"
    if "/omnara-deep-research/" in p:
        if p.endswith("/references/canonical/inquiry-engine-v1.md"):
            return "omnara-deep-research", "omnara-directive-repaired"
        return "omnara-deep-research", "omnara-retained"
    if "/retrieval-intelligence/" in p or "/retrieval-reviewer/" in p:
        return "retrieval", "retrieval-retained"
    if "/rupert-giles-knowledge-steward/" in p:
        return "rupert-giles-knowledge-steward", "rupert-retained"
    if "/signal-loom/" in p:
        if p.endswith("/knowledge/infographic-toolkit-v2-canonical.md"):
            return "signal-loom", "signal-faculty-repaired"
        return "signal-loom", "signal-retained"
    if "/software-verification/" in p or "/verification-reviewer/" in p:
        if "/adapters/" in p and path.name in {"claude-code.md", "codex.md"}:
            return "testforge", "testforge-authority-repaired"
        return "testforge", "testforge-retained"
    raise ValueError(f"Unclassified conditional prompt: {p}")


def build() -> tuple[dict, str]:
    primaries = primary_paths()
    conditionals = conditional_paths()
    if len(primaries) != 30 or len(conditionals) != 128:
        raise ValueError(f"Prompt inventory drift: primary={len(primaries)}, conditional={len(conditionals)}")
    all_paths = [path for _, path in primaries] + conditionals
    missing = [rel(path) for path in all_paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing prompt modules: {missing}")
    if len(set(all_paths)) != 158:
        raise ValueError("Prompt inventory contains overlaps")

    primary_rows = []
    for index, (kind, path) in enumerate(primaries, 1):
        p = rel(path)
        decision = "changed" if p in PRIMARY_CHANGED else "unchanged"
        primary_rows.append({
            "id": f"PS-{index:03d}",
            "kind": kind,
            "path": p,
            "sha256": digest(path),
            "decision": decision,
            "review_class": "primary-repaired" if decision == "changed" else "primary-retained",
        })

    by_hash: dict[str, list[Path]] = defaultdict(list)
    for path in conditionals:
        by_hash[digest(path)].append(path)
    groups = []
    ordered_groups = sorted(by_hash.items(), key=lambda item: min(rel(path) for path in item[1]))
    for index, (sha, paths) in enumerate(ordered_groups, 1):
        classes = {classify(path) for path in paths}
        if len(classes) != 1:
            raise ValueError(f"Hash-equivalent files crossed review classes: {[rel(path) for path in paths]}")
        category, review_class = classes.pop()
        groups.append({
            "id": f"CP-{index:03d}",
            "category": category,
            "sha256": sha,
            "physical_count": len(paths),
            "paths": sorted(rel(path) for path in paths),
            "decision": "changed" if review_class.endswith("-repaired") else "unchanged",
            "review_class": review_class,
        })
    if len(groups) != 97:
        raise ValueError(f"Conditional equivalence-group drift: {len(groups)}")
    duplicate_groups = [group for group in groups if group["physical_count"] > 1]
    if len(duplicate_groups) != 31 or any(group["physical_count"] != 2 or group["category"] != "testforge" for group in duplicate_groups):
        raise ValueError("Unexpected conditional duplicate topology")

    ludis_core_paths = [
        path for path in conditionals
        if "/ludis-continuum/knowledge/instruments/" in rel(path) and path.name != "index.md"
    ]
    if len(ludis_core_paths) != 32:
        raise ValueError(f"Expected 32 Ludis cores, found {len(ludis_core_paths)}")

    package_files = sorted(path for path in PLUGIN.rglob("*") if path.is_file())
    included = set(all_paths)
    excluded = [path for path in package_files if path not in included]
    if (len(package_files), len(included), len(excluded)) != (296, 158, 138):
        raise ValueError(
            f"Package boundary drift: package={len(package_files)}, included={len(included)}, excluded={len(excluded)}"
        )
    excluded_extensions = dict(sorted(Counter(path.suffix.lower() or "[none]" for path in excluded).items()))

    physical_changed = sum(row["decision"] == "changed" for row in primary_rows) + sum(
        group["physical_count"] for group in groups if group["decision"] == "changed"
    )
    unit_changed = sum(row["decision"] == "changed" for row in primary_rows) + sum(
        group["decision"] == "changed" for group in groups
    )
    if (physical_changed, unit_changed) != (54, 52):
        raise ValueError(f"Decision-count drift: physical={physical_changed}, units={unit_changed}")

    inventory_lines = sorted(f"{rel(path)}\t{digest(path)}" for path in all_paths)
    inventory_sha = hashlib.sha256(("\n".join(inventory_lines) + "\n").encode("utf-8")).hexdigest()
    category_physical = Counter(classify(path)[0] for path in conditionals)
    category_units = Counter(group["category"] for group in groups)

    audit = {
        "format": "cd-nova-prompt-surface-audit/v2",
        "product": "Nova the Optimal AI 1.0.0",
        "audit_date": "2026-07-21",
        "status": "PASS",
        "doctrine": "Pith times puissance: put the most semantically load-bearing conceptual frame first, then add only distinctions that steer behavior or preserve a real boundary.",
        "scope": {
            "inclusion_rule": "Every package-owned file whose contents can be loaded as procedural, persona, or discovery instruction under Nova, whether the load is direct, conditional, or delegated.",
            "included": {
                "primary_physical": 30,
                "conditional_physical": 128,
                "total_physical": 158,
                "primary_review_units": 30,
                "conditional_sha256_equivalence_groups": 97,
                "total_review_units": 127,
                "ludis_instrument_cores": 32,
            },
            "package_files": 296,
            "excluded_physical": 138,
            "exclusion_rule": "Exclude machine-executed code and CI; schemas, manifests, receipts, and structured data not presented as instruction; factual dossiers, source catalogs, and knowledge-base records; output/data templates; static assets; and examples not loaded as instruction. Directory names alone never decide scope.",
            "excluded_by_extension": excluded_extensions,
        },
        "summary": {
            "physical_surfaces_reviewed": 158,
            "physical_changed": physical_changed,
            "physical_unchanged_after_review": 158 - physical_changed,
            "review_units": 127,
            "review_units_changed": unit_changed,
            "review_units_unchanged_after_review": 127 - unit_changed,
            "unreviewed_in_scope": 0,
            "high_or_medium_findings_remaining": 0,
            "included_inventory_sha256": inventory_sha,
        },
        "conditional_categories": {
            name: {"physical": category_physical[name], "review_units": category_units[name]}
            for name in sorted(category_physical)
        },
        "equivalence_policy": "Only byte-identical conditional modules share a review unit. Thirty-one TestForge operator/reviewer mirror pairs are each represented by one SHA-256 group while retaining both physical paths.",
        "review_classes": REVIEW_CLASSES,
        "validation": {
            "strict_skill_validator": "PASS: all 12 shipping skill roots, Codex profile, zero findings",
            "ludis_curator": "PASS: 32 curated cores; explicit regeneration changed zero core hashes",
            "ludis_self_check": "PASS: 32/32",
            "ludis_residue_scan": "PASS: zero targeted legacy prompt-residue matches",
            "audit_check": "PASS when python -X utf8 tools/audit_nova_prompt_surfaces.py --check exits zero",
            "boundary": "Static review establishes current prompt bytes, semantic review disposition, package shape, and validation hygiene. It does not by itself establish live routing or response quality.",
        },
        "primary_surfaces": primary_rows,
        "conditional_equivalence_groups": groups,
    }

    md = f"""# Nova prompt-surface audit

Status: **PASS**

Nova 1.0.0 has **158 package-owned model-facing prompt modules** under the audit's semantic boundary: 30 primary surfaces and 128 conditionally loaded procedural modules. Every physical path has a current SHA-256 in the JSON ledger. The 128 conditional modules collapse to 97 review units only where bytes are identical; the 31 deduplications are TestForge operator/reviewer mirror pairs, and both physical paths remain recorded.

This includes all **32 Ludis instrument cores** and their routing index. It also includes conditional doctrine, adapters, fallbacks, personas, and faculty instructions wherever Nova or one of her shipping skills can load them. A directory named `knowledge` was not excluded merely because of its name.

## Boundary

Included means package-owned content that can act as procedural, persona, or discovery instruction under Nova, whether loaded directly, conditionally, or through a delegated skill. Excluded means machine-executed code and CI; schemas, manifests, receipts, and structured data not presented as instruction; factual dossiers, source catalogs, and knowledge-base records; output/data templates; static assets; and examples not loaded as instruction. The plugin contains 296 files: 158 are included and 138 are excluded by that rule.

## Result

- Physical modules reviewed: **158**
- Physical modules repaired: **{physical_changed}**
- Physical modules retained after review: **{158 - physical_changed}**
- SHA-equivalence review units: **127**
- Review units repaired: **{unit_changed}**
- Review units retained after review: **{127 - unit_changed}**
- Unreviewed in scope: **0**
- High- or medium-severity prompt findings remaining: **0**

The repairs put conceptual homes and desired transformations before procedure; removed obsolete framework theater and accidental tool assumptions from Ludis; tightened Dunbar activation and privacy truth; collapsed Nova's duplicated route map; repaired OMNARA's legacy inquiry directive; made Signal Loom's optional faculty library evidence- and stage-governed; and made TestForge host overlays inherit already-granted in-scope authority.

## Category coverage

| Conditional category | Physical modules | Review units |
|---|---:|---:|
""" + "\n".join(
        f"| {name} | {category_physical[name]} | {category_units[name]} |" for name in sorted(category_physical)
    ) + f"""

## Verification

All 12 shipping skill roots pass the strict Codex validator with zero findings. Ludis passes curator validation and its shipping self-check at 32/32; explicit regeneration changes no curated core; the targeted legacy-residue scan returns zero matches. The full included path-and-hash inventory receipt is `{inventory_sha}`.

Run `python -X utf8 tools/audit_nova_prompt_surfaces.py --check` to prove that the human-readable report, JSON ledger, live file set, all 158 hashes, counts, decisions, and equivalence topology still agree.

This is static evidence about current prompt bytes, review disposition, and package hygiene. Live skill selection, routing, response quality, creative quality, and table performance require behavioral evidence rather than a greener shade of paperwork.
"""
    return audit, md


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail if generated artifacts differ from the live package")
    args = parser.parse_args()
    audit, md = build()
    json_text = json.dumps(audit, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        failures = []
        if not JSON_OUT.is_file() or JSON_OUT.read_text(encoding="utf-8") != json_text:
            failures.append(str(JSON_OUT.relative_to(REPO)))
        if not MD_OUT.is_file() or MD_OUT.read_text(encoding="utf-8") != md:
            failures.append(str(MD_OUT.relative_to(REPO)))
        if failures:
            print("FAIL: stale prompt-surface artifacts: " + ", ".join(failures))
            return 1
        print("PASS: 158 physical prompt modules; 127 review units; hashes and reports current")
        return 0
    JSON_OUT.write_text(json_text, encoding="utf-8", newline="\n")
    MD_OUT.write_text(md, encoding="utf-8", newline="\n")
    print("WROTE: 158 physical prompt modules; 127 review units")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
