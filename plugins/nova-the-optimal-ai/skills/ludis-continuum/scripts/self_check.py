from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
REQUIRED = (
    "SKILL.md",
    "agents/openai.yaml",
    "knowledge/operating-doctrine.md",
    "knowledge/state-and-authority.md",
    "knowledge/canonical-boundaries.md",
    "knowledge/instruments/index.md",
    "knowledge/instruments/manifest.json",
    "assets/campaign.template/campaign-ledger.json",
    "schemas/campaign-ledger.schema.json",
    "scripts/init_campaign.py",
    "scripts/validate_ledger.py",
    "scripts/promote_object.py",
    "scripts/roll_table.py",
    "scripts/export_player_safe.py",
    "scripts/snapshot_campaign.py",
)

REMOVED = (
    "knowledge/canonical/rpg-toolkit-v2.md",
    "knowledge/canonical/rpg-game-design-key-ideas.md",
)
FORBIDDEN_RUNTIME_MARKERS = (
    chr(0x1F4A0) + "\u200d" + chr(0x1F310),
    chr(0x27E8),
    chr(0x1F929),
)
SPEAKER_RESIDUE = re.compile(r"\b" + "nova" + r"\b|ludis (?:initiates|deploys|at your service)", re.IGNORECASE)
FORBIDDEN_PROMPT_RESIDUE = (
    re.compile(r"```"),
    re.compile(r"\bdall[- ]?e\b|\bmidjourney\b|\bgemini\b|\bstable diffusion\b", re.IGNORECASE),
    re.compile(r"image generation tool|default to 16x9|go right ahead", re.IGNORECASE),
    re.compile(r"art prompt alchemist|heroic backstory weaver|instant npc creator", re.IGNORECASE),
    re.compile(r"optional (?:details|.*parameters)\??", re.IGNORECASE),
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    errors = [f"missing: {rel}" for rel in REQUIRED if not (ROOT / rel).is_file()]
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    metadata = (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
    if not skill.startswith("---\n"):
        errors.append("frontmatter missing")
    if "$ludis-continuum" not in metadata:
        errors.append("agent invocation missing")
    if "rpg-toolkit-v2.md" in skill or "rpg-game-design-key-ideas.md" in skill:
        errors.append("removed monolith referenced by SKILL.md")

    for rel in (
        "schemas/campaign-ledger.schema.json",
        "assets/campaign.template/campaign-ledger.json",
    ):
        try:
            json.loads((ROOT / rel).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"invalid JSON {rel}: {exc}")

    if any(path.is_symlink() for path in ROOT.rglob("*")):
        errors.append("symlink present")

    for rel in REMOVED:
        if (ROOT / rel).exists():
            errors.append(f"removed monolith present: {rel}")

    manifest_path = ROOT / "knowledge/instruments/manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"invalid instrument manifest: {exc}")
        manifest = {}
    cores = manifest.get("cores", [])
    if manifest.get("format") != "cd-ludis-instrument-manifest/v2":
        errors.append("instrument manifest format mismatch")
    if manifest.get("derivation_status") != "semantically_rewritten_derivative":
        errors.append("instrument derivation status mismatch")
    if manifest.get("legacy_source_role") != "provenance evidence only; never a regeneration input":
        errors.append("legacy source role mismatch")
    if len(cores) != 32:
        errors.append(f"instrument count is {len(cores)}, expected 32")
    for item in cores:
        rel = item.get("path")
        if not isinstance(rel, str) or Path(rel).name != rel:
            errors.append(f"unsafe instrument path: {rel!r}")
            continue
        path = ROOT / "knowledge/instruments" / rel
        if not path.is_file():
            errors.append(f"missing instrument core: {rel}")
            continue
        if item.get("sha256") != sha256(path):
            errors.append(f"instrument hash mismatch: {rel}")
        if item.get("bytes") != path.stat().st_size:
            errors.append(f"instrument byte count mismatch: {rel}")
        text = path.read_text(encoding="utf-8")
        if re.search(r"(?mi)^#{1,3}\s+example\b", text):
            errors.append(f"worked example survived: {rel}")
        folded = text.casefold()
        if any(token in folded for token in FORBIDDEN_RUNTIME_MARKERS):
            errors.append(f"legacy runtime marker survived: {rel}")
        if SPEAKER_RESIDUE.search(text):
            errors.append(f"speaker residue survived: {rel}")
        for pattern in FORBIDDEN_PROMPT_RESIDUE:
            if pattern.search(text):
                errors.append(f"prompt residue survived in {rel}: {pattern.pattern}")
    index = ROOT / "knowledge/instruments/index.md"
    if manifest.get("index_sha256") != sha256(index):
        errors.append("instrument index hash mismatch")

    for error in errors:
        print("ERROR:", error)
    if errors:
        print(f"FAIL: {len(errors)} error(s)")
        return 1
    print(f"PASS: Ludis Continuum curated-runtime self-check ({len(cores)} instrument cores)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
