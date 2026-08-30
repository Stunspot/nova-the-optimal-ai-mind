from __future__ import annotations

import hashlib
import json
import re
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))
from release_lib import sha256_file, tree_digest

EXPECTED = {
    "nova", "nova-operations", "cognitive-continuity", "agent-striving",
    "agent-swarm-orchestration", "agentic-coding", "answerlayer", "beryl-it-tech",
    "corkboard", "current-intelligence-observatory", "dunbar", "interview-trainer",
    "it-work-reviewer", "job-application-builder", "lex-foster-language-companion",
    "officecraft-reviewer", "omnara-deep-research", "owen-burnett-officecraft",
    "privacy-redline", "promptcraft", "retrieval-intelligence", "retrieval-reviewer",
    "rupert-giles-knowledge-steward", "software-verification", "verification-reviewer",
}


class ProductContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.plugin = REPO / "plugins" / "nova-the-optimal-ai"
        cls.loadout = json.loads((cls.plugin / "LOADOUT-MANIFEST.json").read_text(encoding="utf-8"))
        cls.lock = json.loads((REPO / "design" / "source-lock.json").read_text(encoding="utf-8"))

    def test_exact_one_plugin_and_twenty_five_roots(self) -> None:
        marketplace = json.loads((REPO / ".agents" / "plugins" / "marketplace.json").read_text(encoding="utf-8"))
        self.assertEqual([item["name"] for item in marketplace["plugins"]], ["nova-the-optimal-ai"])
        roots = {path.name for path in (self.plugin / "skills").iterdir() if path.is_dir()}
        self.assertEqual(roots, EXPECTED)
        self.assertEqual(set(self.loadout["roots"]), EXPECTED)
        self.assertEqual(self.loadout["topology"]["visible_skill_roots"], 25)

    def test_skill_frontmatter_names_match_directories(self) -> None:
        for skill_id in sorted(EXPECTED):
            text = (self.plugin / "skills" / skill_id / "SKILL.md").read_text(encoding="utf-8")
            match = re.match(r"^---\s*\n.*?^name:\s*[\"']?([^\"'\n]+)", text, flags=re.MULTILINE | re.DOTALL)
            self.assertIsNotNone(match, skill_id)
            self.assertEqual(match.group(1).strip(), skill_id)

    def test_mind_is_nested_and_persona_is_locked(self) -> None:
        cores = list((self.plugin / "skills" / "nova" / "references" / "mind" / "faculty-cores").glob("*.core.md"))
        self.assertEqual(len(cores), 16)
        self.assertFalse((REPO / "plugins" / "augment-of-mind").exists())
        persona = self.plugin / "skills" / "nova" / "references" / "nova-persona.md"
        self.assertEqual(sha256_file(persona), self.lock["persona_sha256"])

    def test_source_lock_matches_imported_bytes(self) -> None:
        self.assertEqual(len(self.lock["records"]), 25)
        for record in self.lock["records"]:
            imported = REPO / record["imported_path"]
            self.assertEqual(tree_digest(imported), record["imported_tree"], record["id"])
        self.assertEqual(tree_digest(self.plugin / "skills"), self.lock["plugin_skill_tree"])

    def test_required_old_runtime_is_absent(self) -> None:
        forbidden = ("augment-of-mind", "mind_prompt_submit.py", "mind_core", "bundle/reminder")
        observed = [
            path.relative_to(REPO).as_posix()
            for path in REPO.rglob("*")
            if path.is_file() and any(token in path.relative_to(REPO).as_posix().casefold() for token in forbidden)
            and "verification/" not in path.relative_to(REPO).as_posix().casefold()
        ]
        self.assertEqual(observed, [])

    def test_stateful_scripts_have_no_codex_fallback(self) -> None:
        cork = (self.plugin / "skills" / "corkboard" / "scripts" / "corkboard.py").read_text(encoding="utf-8")
        dunbar = (self.plugin / "skills" / "dunbar" / "scripts" / "dunbar.py").read_text(encoding="utf-8")
        operations = (self.plugin / "skills" / "nova-operations" / "scripts" / "nova_estate.py").read_text(encoding="utf-8")
        self.assertNotIn("CODEX_HOME", cork)
        self.assertNotIn("CODEX_HOME", dunbar)
        self.assertNotIn('"project-management"', operations)
        self.assertNotIn('    "DENNIS_PROJECT_HOME",', operations)

    def test_required_notice_files_are_present(self) -> None:
        required = (
            "notices/testforge/LICENSE.md",
            "notices/testforge/NOTICE.md",
            "notices/testforge/ATTRIBUTION.md",
            "notices/testforge/TRADEMARKS.md",
            "notices/agent-swarm-orchestration/LICENSE.md",
            "notices/agent-swarm-orchestration/TERMS-OF-USE.md",
            "notices/job-application-builder/LICENSE-STATUS.md",
            "notices/interview-trainer/LICENSE-STATUS.md",
        )
        for relative in required:
            self.assertTrue((self.plugin / relative).is_file(), relative)


if __name__ == "__main__":
    unittest.main()
