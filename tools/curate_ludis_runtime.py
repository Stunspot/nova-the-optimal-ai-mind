from __future__ import annotations

"""Validate or explicitly regenerate Ludis instrument custody artifacts.

The curated core files are authoritative runtime inputs. The removed legacy
monolith is provenance evidence only and is never an input to core generation.
"""

import argparse
import hashlib
import json
import re
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = (
    REPO
    / "plugins"
    / "nova-the-optimal-ai"
    / "skills"
    / "ludis-continuum"
    / "knowledge"
    / "instruments"
)
DEFAULT_RECEIPT = REPO / "verification" / "ludis-toolkit-curation.json"

INSTRUMENTS = (
    ("Region Creating Map Builder", "Region as Consequence Map", "region-map.md", "regions, travel, or map logic"),
    ("Lost Civilization Lore Creator", "An Argument in Ruins", "lost-civilization.md", "ruins, lost cultures, or archaeological mystery"),
    ("Secret Society Generator", "The Hidden Institution", "secret-society.md", "covert groups, agendas, or hidden influence"),
    ("Faction Allegiance Matrix", "Allegiance Under Pressure", "faction-allegiance.md", "faction relationships, leverage, or changing loyalties"),
    ("Dimensional Gateway Locator", "A Threshold That Changes Both Sides", "dimensional-gateway.md", "portals, planes, or threshold locations"),
    ("Prophecy Maker", "Prophecy as Interpretive Pressure", "prophecy.md", "prophecy, omen, or ambiguous future pressure"),
    ("Impossible Invention Speculator", "One Impossible Premise, Rigor Downstream", "impossible-invention.md", "speculative invention or impossible technology"),
    ("Obscure Magic System Blueprint", "Magic as Culture, Practice, and Cost", "magic-system.md", "a magic system, costs, limits, or cultural integration"),
    ("Homebrew Mechanic Refiner", "A Rule Under Play", "homebrew-mechanics.md", "a proposed rule, procedure, or subsystem"),
    ("Settlement and City Builder", "A Settlement in Motion", "settlement-city.md", "a settlement, city, districts, or civic pressure"),
    ("Fantasy Tavern Menu Maker", "A Menu That Remembers the Place", "tavern-menu.md", "food, hospitality, or a small social texture"),
    ("Rumor Mill and Tabloid Headline Maker", "Rumor as Social Action", "rumors-headlines.md", "rumors, public chatter, or competing reports"),
    ("Big Bad Evil Guy (BBEG) Maker", "An Antagonist Who Can Act Now", "villain.md", "an antagonist with pressure, motive, and counterplay"),
    ("Villain’s Scheme Outliner", "A Scheme That Moves When Touched", "villain-scheme.md", "an antagonist plan, escalation, or counterplay"),
    ("Intrigue Web Generator", "Secrets That Change Relationships", "intrigue-web.md", "secrets, social conflict, or overlapping interests"),
    ("Dynamic Quest Generator", "A Charged Situation, Not a Plot", "quest.md", "a quest with choices, clues, and consequences"),
    ("Encounter Chain Composer", "Consequence in Rhythm", "encounter-chain.md", "a sequence of encounters or escalating situations"),
    ("Dungeon Architect", "A Place Players Can Learn", "dungeon.md", "a dungeon, exploration structure, or keyed location"),
    ("Urban Dungeon Generator", "The City Beneath Its Public Face", "urban-dungeon.md", "an urban exploration site or layered city threat"),
    ("Puzzle and Trap Maker", "A Legible Obstacle with Teeth", "puzzle-trap.md", "a puzzle, trap, or hybrid obstacle"),
    ("Creature Crucible Monster Maker", "A Creature Readable Before It Is Dangerous", "creature.md", "a creature with ecology, behavior, and play pressure"),
    ("Cursed Item Lore Generator", "A Bargain That Learns Your Reasons", "cursed-item.md", "a cursed object and its consequences"),
    ("Legendary Artifact Forger", "An Artifact That Reorganizes the World", "legendary-artifact.md", "a consequential artifact, history, or tradeoff"),
    ("Spell Scriber", "A Spell That Creates a Decision", "spell.md", "a system-aware spell or magical effect"),
    ("Arcane Language Lexicon", "A Language That Makes a Worldview Playable", "arcane-language.md", "a naming system, symbolic language, or lexicon"),
    ("Party Creator Tool", "The Party as a Relationship Engine", "party.md", "a party, ensemble, or relationship-ready cast"),
    ("Heroic Backstory Weaver", "A Playable Past with Its Hand on the Door", "backstory.md", "a playable character history and future pressure"),
    ("Instant NPC Creator", "Someone Halfway Through a Decision", "npc.md", "an NPC with immediate table utility"),
    ("Boxtext Description Forge", "What the Characters Perceive Now", "boxtext.md", "a concise, speakable scene description"),
    ("Instant Myth Generator", "A Story a Culture Lives By", "myth.md", "a myth, belief, or cultural story"),
    ("Art Prompt Alchemist", "A Visual Brief with Narrative Weight", "art-prompt.md", "an art brief or visual prompt"),
    ("Campaign Builder Workflow", "A Campaign Already in Motion", "campaign-workflow.md", "campaign framing, prep, or session advancement"),
)

EXCLUDED = (
    "worked examples and worked worlds",
    "named settings, campaigns, parties, and factions",
    "legacy speaker wrappers, promotion, and persona residue",
    "automatic tool calls, platform assumptions, and sibling-prompt dependencies",
    "rigid menus, arbitrary output quotas, and generic input boilerplate",
)

FORBIDDEN = (
    r"port zindra",
    r"bell below bracken",
    r"patreon",
    r"discord\.gg",
    r"\bnova\b",
    r"ludis initiates",
    r"ludis deploys",
    r"ludis at your service",
    r"⟨",
    r"🤩",
    r"```",
    r"\bdall[- ]?e\b",
    r"\bmidjourney\b",
    r"\bgemini\b",
    r"\bstable diffusion\b",
    r"image generation tool",
    r"art prompt alchemist",
    r"heroic backstory weaver",
    r"instant npc creator",
    r"default to 16x9",
    r"go right ahead",
    r"optional (?:details|.*parameters)\??",
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=True) + "\n").encode("utf-8")


def validate_core(text: str, path: Path, expected_title: str) -> None:
    first_line = text.splitlines()[0] if text.splitlines() else ""
    if first_line != f"# {expected_title}":
        raise ValueError(f"unexpected title in {path.name}: {first_line!r}")
    for pattern in FORBIDDEN:
        if re.search(pattern, text, re.IGNORECASE):
            raise ValueError(f"forbidden legacy or prompt residue in {path.name}: {pattern}")
    if re.search(r"(?mi)^#{1,3}\s+example\b", text):
        raise ValueError(f"worked example heading survived in {path.name}")


def render_index(rows: list[dict[str, object]]) -> str:
    lines = [
        "# Ludis Instrument Index",
        "",
        "Choose the instrument whose conceptual home matches the transformation the user needs. Each core is a compact performance seed, not a form to complete. Load no second core unless the first cannot produce the artifact without a genuinely different creative motion. Campaign state, consent, rules authority, and canon custody remain with the main skill.",
        "",
        "| Need | Load |",
        "|---|---|",
    ]
    lines.extend(f"| {row['when']} | `knowledge/instruments/{row['path']}` |" for row in rows)
    lines.extend(
        (
            "",
            "Enter through the user's live material. Preserve supplied canon, keep invention provisional where appropriate, and return a usable table, play, or fiction artifact without narrating the instrument. A core supplies creative bearings; it is never settled canon, authoritative rules, or a worked setting.",
            "",
        )
    )
    return "\n".join(lines)


def load_provenance(receipt_path: Path) -> dict[str, object]:
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    required = ("source", "source_sha256", "source_bytes")
    missing = [field for field in required if field not in receipt]
    if missing:
        raise ValueError(f"curation receipt lacks provenance fields: {', '.join(missing)}")
    return receipt


def verify_evidence(path: Path, expected_sha256: str, expected_bytes: int, label: str) -> None:
    if sha256(path) != expected_sha256 or path.stat().st_size != expected_bytes:
        raise ValueError(f"{label} does not match recorded provenance: {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="curated instrument directory")
    parser.add_argument("--receipt", type=Path, default=DEFAULT_RECEIPT, help="curation receipt")
    parser.add_argument("--legacy-source", type=Path, help="optional source evidence to verify; never used to write cores")
    parser.add_argument("--discarded-reference", type=Path, help="optional discarded-source evidence to verify")
    parser.add_argument("--write", action="store_true", help="explicitly regenerate index, manifest, and receipt")
    args = parser.parse_args()

    output = args.output.resolve()
    receipt_path = args.receipt.resolve()
    provenance = load_provenance(receipt_path)
    source_sha256 = str(provenance["source_sha256"])
    source_bytes = int(provenance["source_bytes"])
    if args.legacy_source:
        verify_evidence(args.legacy_source, source_sha256, source_bytes, "legacy source")

    discarded = provenance.get("discarded_reference")
    if args.discarded_reference:
        if not isinstance(discarded, dict):
            raise ValueError("receipt lacks discarded-reference provenance")
        verify_evidence(
            args.discarded_reference,
            str(discarded["source_sha256"]),
            int(discarded["source_bytes"]),
            "discarded reference",
        )

    rows: list[dict[str, object]] = []
    core_bytes = 0
    for legacy_title, title, filename, when in INSTRUMENTS:
        path = output / filename
        if not path.is_file():
            raise ValueError(f"missing curated core: {filename}")
        text = path.read_text(encoding="utf-8")
        validate_core(text, path, title)
        size = path.stat().st_size
        core_bytes += size
        rows.append(
            {
                "title": title,
                "legacy_title": legacy_title,
                "path": filename,
                "when": when,
                "sha256": sha256(path),
                "bytes": size,
            }
        )

    index_bytes = render_index(rows).encode("utf-8")
    manifest = {
        "format": "cd-ludis-instrument-manifest/v2",
        "source": str(provenance["source"]),
        "source_sha256": source_sha256,
        "derivation_status": "semantically_rewritten_derivative",
        "legacy_selection": "top-level instrument cores before first Example heading",
        "runtime_authority": "the 32 curated core files listed here",
        "legacy_source_role": "provenance evidence only; never a regeneration input",
        "excluded": list(EXCLUDED),
        "cores": rows,
        "index_sha256": sha256_bytes(index_bytes),
    }
    manifest_bytes = json_bytes(manifest)
    output_bytes = core_bytes + len(index_bytes) + len(manifest_bytes)
    receipt: dict[str, object] = {
        "format": "cd-ludis-toolkit-curation/v3",
        "source": str(provenance["source"]),
        "source_sha256": source_sha256,
        "source_bytes": source_bytes,
        "runtime_output": "knowledge/instruments/",
        "manifest_sha256": sha256_bytes(manifest_bytes),
        "core_count": len(rows),
        "core_bytes": core_bytes,
        "output_bytes": output_bytes,
        "derivation_status": "semantically_rewritten_derivative",
        "legacy_selection": "top-level instrument cores before first Example heading",
        "runtime_authority": "curated core files",
        "legacy_overwrite_prohibited": True,
        "regeneration_scope": ["index.md", "manifest.json", "this receipt"],
        "excluded": list(EXCLUDED),
    }
    if isinstance(discarded, dict):
        receipt["discarded_reference"] = discarded
    receipt_bytes = json_bytes(receipt)

    expected = {
        output / "index.md": index_bytes,
        output / "manifest.json": manifest_bytes,
        receipt_path: receipt_bytes,
    }
    if args.write:
        for path, data in expected.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        status = "regenerated"
    else:
        drift = [str(path) for path, data in expected.items() if not path.is_file() or path.read_bytes() != data]
        if drift:
            print(json.dumps({"status": "drift", "paths": drift, "repair": "rerun with --write"}, indent=2))
            return 1
        status = "validated"

    print(
        json.dumps(
            {
                "status": status,
                "cores": len(rows),
                "core_bytes": core_bytes,
                "output_bytes": output_bytes,
                "manifest_sha256": sha256_bytes(manifest_bytes),
                "legacy_source_used_to_generate_cores": False,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
