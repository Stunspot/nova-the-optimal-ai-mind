from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))
from release_lib import sha256_file, tree_digest
from check_documentation import inspect as inspect_documentation

EXPECTED = {
    "nova", "nova-operations", "commonplace", "cognitive-continuity",
    "dennis-stratton-project-management", "agent-striving",
    "agent-swarm-orchestration", "agentic-coding", "answerlayer", "beryl-it-tech",
    "corkboard", "current-intelligence-observatory", "dunbar", "interview-trainer",
    "it-work-reviewer", "job-application-builder", "lex-foster-language-companion",
    "officecraft-reviewer", "omnara-deep-research", "owen-burnett-officecraft",
    "privacy-redline", "promptcraft", "retrieval-intelligence", "retrieval-reviewer",
    "rupert-giles-knowledge-steward", "software-verification", "verification-reviewer",
}
RIGHTS_DOCS = (
    "LICENSE.md", "ATTRIBUTION.md", "NOTICE.md", "TRADEMARKS.md",
    "PROVENANCE.md", "THIRD-PARTY-NOTICES.md",
)


class ProductContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.plugin = REPO / "plugins" / "nova-the-optimal-ai"
        cls.loadout = json.loads((cls.plugin / "LOADOUT-MANIFEST.json").read_text(encoding="utf-8"))
        cls.lock = json.loads((REPO / "design" / "source-lock.json").read_text(encoding="utf-8"))

    def test_exact_one_plugin_and_twenty_seven_roots(self) -> None:
        marketplace = json.loads((REPO / ".agents" / "plugins" / "marketplace.json").read_text(encoding="utf-8"))
        self.assertEqual([item["name"] for item in marketplace["plugins"]], ["nova-the-optimal-ai"])
        roots = {path.name for path in (self.plugin / "skills").iterdir() if path.is_dir()}
        self.assertEqual(roots, EXPECTED)
        self.assertEqual(set(self.loadout["roots"]), EXPECTED)
        self.assertEqual(self.loadout["topology"]["visible_skill_roots"], 27)

    def test_skill_frontmatter_names_match_directories(self) -> None:
        for skill_id in sorted(EXPECTED):
            text = (self.plugin / "skills" / skill_id / "SKILL.md").read_text(encoding="utf-8")
            match = re.match(r"^---\s*\n.*?^name:\s*[\"']?([^\"'\n]+)", text, flags=re.MULTILINE | re.DOTALL)
            self.assertIsNotNone(match, skill_id)
            self.assertEqual(match.group(1).strip(), skill_id)

    def test_mind_is_nested_and_persona_is_locked(self) -> None:
        cores = list((self.plugin / "skills" / "nova" / "references" / "mind" / "faculty-cores").glob("*.core.md"))
        self.assertEqual(len(cores), 17)
        self.assertFalse((REPO / "plugins" / "augment-of-mind").exists())
        persona = self.plugin / "skills" / "nova" / "references" / "nova-persona.md"
        self.assertEqual(sha256_file(persona), self.lock["persona_sha256"])

    def test_source_lock_matches_imported_bytes(self) -> None:
        self.assertEqual(len(self.lock["records"]), 27)
        for record in self.lock["records"]:
            imported = REPO / record["imported_path"]
            self.assertEqual(tree_digest(imported), record["imported_tree"], record["id"])
        self.assertEqual(tree_digest(self.plugin / "skills"), self.lock["plugin_skill_tree"])

    def test_public_split_license_and_rights_bundle_are_bound(self) -> None:
        self.assertEqual(self.loadout["license"], "LICENSE.md")
        self.assertIn("MIT", self.loadout["rights_status"])
        self.assertIn("CC BY-ND 4.0", self.loadout["rights_status"])
        rights = self.lock["rights_bundle"]
        self.assertEqual(rights["state"], "public_split_license_applied")
        self.assertEqual(rights["redistribution_state"], "permitted_under_included_licenses")
        self.assertEqual(rights["external_rights_blockers"], [])
        for name in RIGHTS_DOCS:
            root = REPO / name
            plugin = self.plugin / name
            self.assertTrue(root.is_file(), name)
            self.assertTrue(plugin.is_file(), name)
            self.assertEqual(root.read_bytes(), plugin.read_bytes(), name)
            self.assertEqual(sha256_file(root), rights["files"][name], name)
        license_text = (REPO / "LICENSE.md").read_text(encoding="utf-8")
        self.assertIn("standard Collaborative Dynamics public-Augment split license", license_text)
        self.assertIn("CC-BY-ND-4.0", license_text)

    def test_same_owner_component_metadata_is_reconciled(self) -> None:
        answer = json.loads((self.plugin / "skills" / "answerlayer" / "manifest.json").read_text(encoding="utf-8"))
        current = json.loads((self.plugin / "skills" / "current-intelligence-observatory" / "manifest.json").read_text(encoding="utf-8"))
        for manifest in (answer, current):
            self.assertEqual(manifest["rights_status"], "public-inclusion-authorized-for-nova-free-3.1.1")
            self.assertIn("Nova Free 3.1.1 public split license", manifest["license"])
        source_map = json.loads((REPO / "design" / "source-map.json").read_text(encoding="utf-8"))
        records = {record["id"]: record for record in source_map["records"]}
        self.assertEqual(
            records["answerlayer"]["edition_overlays"],
            ["README.md", "knowledge/canonical-source-boundaries.md", "manifest.json"],
        )
        self.assertEqual(records["current-intelligence-observatory"]["edition_overlays"], ["manifest.json"])

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
        self.assertIn('"project-management"', operations)
        self.assertIn('    "DENNIS_PROJECT_HOME",', operations)
        self.assertIn('    "NOVA_COMMONPLACE_HOME",', operations)
        self.assertIn('    "NOVA_CONCORDANCE_HOME",', operations)

    def test_github_workflows_are_manual_and_bounded(self) -> None:
        workflows = sorted((REPO / ".github" / "workflows").glob("*.yml"))
        self.assertTrue(workflows)
        for path in workflows:
            text = path.read_text(encoding="utf-8")
            self.assertRegex(text, r"(?m)^  workflow_dispatch:\s*$", path.name)
            self.assertNotRegex(text, r"(?m)^  (?:push|pull_request|schedule):", path.name)
            self.assertIn("timeout-minutes:", text, path.name)

    def test_maintained_documentation_contains_no_control_characters(self) -> None:
        result = inspect_documentation(REPO)
        control_findings = [
            finding for finding in result["findings"]
            if "control character" in str(finding["problem"])
        ]
        self.assertEqual(control_findings, [])

    def test_component_notice_custody_is_current(self) -> None:
        required = (
            "notices/testforge/LICENSE.md",
            "notices/testforge/NOTICE.md",
            "notices/testforge/ATTRIBUTION.md",
            "notices/testforge/TRADEMARKS.md",
            "notices/agent-swarm-orchestration/LICENSE.md",
            "notices/agent-swarm-orchestration/TERMS-OF-USE.md",
            "notices/job-application-builder/INCLUSION-NOTICE.md",
            "notices/interview-trainer/INCLUSION-NOTICE.md",
        )
        for relative in required:
            self.assertTrue((self.plugin / relative).is_file(), relative)
        self.assertFalse((self.plugin / "notices/job-application-builder/LICENSE-STATUS.md").exists())
        self.assertFalse((self.plugin / "notices/interview-trainer/LICENSE-STATUS.md").exists())


if __name__ == "__main__":
    unittest.main()
