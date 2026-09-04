from __future__ import annotations

import hashlib
import json
import re
import sys
import subprocess
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
TRELLIS_CONTRACTS = {
    "model_set": "cd-model-agnosticism-model-set/v2",
    "observation_sequence": "cd-model-agnosticism-observation-sequence/v2",
    "analysis_receipt": "cd-model-agnosticism-inference-run/v2",
    "validation_receipt": "cd-model-agnosticism-validation/v2",
    "error_receipt": "cd-model-agnosticism-error/v2",
    "receipt_envelope": "cd-model-agnosticism-receipt-envelope/v2",
}
TRELLIS_ASSETS = [
    "skills/nova/assets/model-agnosticism/model-set.schema.json",
    "skills/nova/assets/model-agnosticism/observation-sequence.schema.json",
    "skills/nova/assets/model-agnosticism/inference-run.schema.json",
    "skills/nova/assets/model-agnosticism/example-model-set.json",
    "skills/nova/assets/model-agnosticism/example-observation-sequence.json",
]


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

    def test_mind_is_novas_edition_invariant_architecture(self) -> None:
        contract = json.loads((REPO / "design" / "product-contract.json").read_text(encoding="utf-8"))
        self.assertEqual(contract["mind"]["identity"], "nova_edition_invariant_cognitive_architecture")
        self.assertEqual(contract["mind"]["product_status"], "not_a_separate_product")
        self.assertEqual(
            contract["mind"]["edition_variability"],
            "capabilities_services_and_distribution_not_basic_mind",
        )
        nova = (self.plugin / "skills" / "nova" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("MIND is Nova's edition-invariant cognitive architecture", nova)
        self.assertIn("not a separate product, persona, or optional sibling", nova)
        agnosticism = contract["mind"]["model_agnosticism"]
        self.assertEqual(agnosticism["ambient_mode"], "qualitative_proportionate")
        self.assertEqual(agnosticism["formal_instrument"], "optional_stateless_trellis")
        self.assertFalse(agnosticism["automatic_numerical_invocation"])
        self.assertEqual(
            agnosticism["formal_lanes"],
            ["evidence_update", "assumption_stress_test"],
        )
        self.assertEqual(agnosticism["invocation_owner"], "any_capability_meeting_the_formal_gate")
        self.assertEqual(agnosticism["authority_effect"], "none")
        self.assertIn("do not manufacture proposition ledgers", nova)
        self.assertIn("any invoking capability may assemble explicit inputs backstage", nova)

    def test_model_agnosticism_trellis_binding_is_exact_and_packaged(self) -> None:
        product = json.loads((REPO / "design" / "product-contract.json").read_text(encoding="utf-8"))
        product_agnosticism = product["mind"]["model_agnosticism"]
        loadout_agnosticism = self.loadout["topology"]["model_agnosticism"]
        self.assertEqual(loadout_agnosticism, product_agnosticism)

        binding = product_agnosticism["trellis_binding"]
        self.assertEqual(binding["engine_id"], "cd-model-agnosticism-trellis")
        self.assertEqual(binding["engine_version"], "1.1.0")
        self.assertEqual(binding["path_base"], "plugin_root")
        self.assertEqual(binding["entrypoint"], "skills/nova/scripts/model_agnosticism_trellis.py")
        self.assertEqual(binding["contracts"], TRELLIS_CONTRACTS)
        self.assertEqual(binding["required_asset_count"], 5)
        self.assertEqual(binding["required_assets"], TRELLIS_ASSETS)
        self.assertEqual(len(set(binding["required_assets"])), binding["required_asset_count"])

        entrypoint = self.plugin / binding["entrypoint"]
        self.assertTrue(entrypoint.is_file())
        engine_text = entrypoint.read_text(encoding="utf-8")
        expected_constants = {
            "ENGINE_ID": binding["engine_id"],
            "ENGINE_VERSION": binding["engine_version"],
            "MODEL_SET_CONTRACT": TRELLIS_CONTRACTS["model_set"],
            "SEQUENCE_CONTRACT": TRELLIS_CONTRACTS["observation_sequence"],
            "RUN_CONTRACT": TRELLIS_CONTRACTS["analysis_receipt"],
            "VALIDATION_CONTRACT": TRELLIS_CONTRACTS["validation_receipt"],
            "ERROR_CONTRACT": TRELLIS_CONTRACTS["error_receipt"],
            "RECEIPT_ENVELOPE": TRELLIS_CONTRACTS["receipt_envelope"],
        }
        for name, expected in expected_constants.items():
            match = re.search(rf'(?m)^{name} = "([^"]+)"$', engine_text)
            self.assertIsNotNone(match, name)
            self.assertEqual(match.group(1), expected, name)

        for relative in TRELLIS_ASSETS:
            self.assertTrue((self.plugin / relative).is_file(), relative)
        model_schema = json.loads((self.plugin / TRELLIS_ASSETS[0]).read_text(encoding="utf-8"))
        sequence_schema = json.loads((self.plugin / TRELLIS_ASSETS[1]).read_text(encoding="utf-8"))
        receipt_schema = json.loads((self.plugin / TRELLIS_ASSETS[2]).read_text(encoding="utf-8"))
        model_example = json.loads((self.plugin / TRELLIS_ASSETS[3]).read_text(encoding="utf-8"))
        sequence_example = json.loads((self.plugin / TRELLIS_ASSETS[4]).read_text(encoding="utf-8"))
        self.assertEqual(model_schema["properties"]["contract"]["const"], TRELLIS_CONTRACTS["model_set"])
        self.assertEqual(sequence_schema["properties"]["contract"]["const"], TRELLIS_CONTRACTS["observation_sequence"])
        self.assertEqual(model_example["contract"], TRELLIS_CONTRACTS["model_set"])
        self.assertEqual(sequence_example["contract"], TRELLIS_CONTRACTS["observation_sequence"])
        receipt_text = json.dumps(receipt_schema, ensure_ascii=False)
        for key in ("analysis_receipt", "validation_receipt", "error_receipt", "receipt_envelope"):
            self.assertIn(TRELLIS_CONTRACTS[key], receipt_text, key)

    def test_trellis_route_and_v2_only_upgrade_boundary_are_explicit(self) -> None:
        nova = self.plugin / "skills" / "nova"
        skill = (nova / "SKILL.md").read_text(encoding="utf-8")
        doctrine = (nova / "references" / "mind" / "model-agnosticism.md").read_text(encoding="utf-8")
        validate_command = "python scripts/model_agnosticism_trellis.py validate MODEL_SET.json OBSERVATION_SEQUENCE.json"
        analyze_command = "python scripts/model_agnosticism_trellis.py analyze MODEL_SET.json OBSERVATION_SEQUENCE.json [--decode] [--smooth]"
        for text in (skill, doctrine):
            self.assertIn(validate_command, text)
            self.assertIn(analyze_command, text)
            self.assertIn("Exit 2", text)
            self.assertIn("Exit 3", text)
            self.assertIn("qualitative Model Agnosticism", text)
        self.assertIn(TRELLIS_CONTRACTS["validation_receipt"], doctrine)
        self.assertIn(TRELLIS_CONTRACTS["analysis_receipt"], doctrine)
        self.assertIn("engine version `1.1.0`", doctrine)

        for relative in ("docs/UPGRADE.md", "docs/upgrade.html"):
            text = (REPO / relative).read_text(encoding="utf-8").casefold()
            self.assertIn("trellis 1.1.0", text, relative)
            self.assertIn("no automatic v1-to-v2 trellis migration", text, relative)
            self.assertIn(TRELLIS_CONTRACTS["model_set"], text, relative)
            self.assertIn(TRELLIS_CONTRACTS["observation_sequence"], text, relative)
            self.assertIn("historical receipt", text, relative)

    def test_trellis_v2_interpretation_disclosures_are_explicit(self) -> None:
        nova = self.plugin / "skills" / "nova"
        doctrine = (nova / "references" / "mind" / "model-agnosticism.md").read_text(encoding="utf-8")
        decision = (REPO / "design" / "DEC-MODEL-AGNOSTICISM-CALLABLE.md").read_text(encoding="utf-8")
        release = (REPO / "RELEASE-NOTES.md").read_text(encoding="utf-8")
        skill = (nova / "SKILL.md").read_text(encoding="utf-8")

        doctrine_tokens = (
            "`known_at` is strictly increasing",
            "Equal knowledge timestamps",
            "one through six digits",
            "microsecond precision",
            "posterior_log_probabilities",
            "posterior_finite_log_underflow_state_indices",
            "posterior_structural_zero_state_indices",
            "weight_status: underflow",
            "linear_weights_complete",
            "evidence_gate",
            "conditional_evidence_update",
            "diagnostic_only",
            "scenario_only",
            "{kind, fixed_before_sequence, basis, source_refs}",
            "calibration_target_digest",
            "declared_threshold_arithmetic",
            "DUPLICATE_COMPARISON_UNIT",
            "DUPLICATE_PREDICTIVE_KERNEL",
            "general_observational_equivalence_validated",
            "parameter_provenance_truth_validated",
            "candidate_selection_truth_validated",
            "stopping_rule_truth_validated",
            "observation_independence_validated",
            "semantic_truth_certified",
        )
        for token in doctrine_tokens:
            self.assertIn(token, doctrine, token)

        shared_tokens = (
            "`known_at`",
            "underflow",
            "structural zero",
            "evidence_gate",
            "diagnostic_only",
            "scenario_only",
            "calibration_target_digest",
            "comparison_unit_id",
            "observational equivalence",
            "false",
        )
        for label, text in (("decision", decision), ("release", release)):
            for token in shared_tokens:
                self.assertIn(token, text, f"{label}: {token}")

        for token in (
            "comparison.effective_interpretation",
            "finite log probabilities",
            "structural zero",
            "equal batch timestamps are retrospective",
            "semantic false flag",
        ):
            self.assertIn(token, skill, token)


    def test_absent_behavioral_fixtures_are_not_claimed_as_current_evidence(self) -> None:
        ledger = json.loads(
            (self.plugin / "skills" / "nova" / "references" / "mind" / "core-adaptation-ledger.json").read_text(
                encoding="utf-8"
            )
        )
        epistemic = next(row for row in ledger["cores"] if row["id"] == "epistemic-regulation")
        self.assertEqual(epistemic["author_review"]["actor"], "Nova")
        self.assertIn("user_direction", epistemic["author_review"])
        self.assertIn("callable", epistemic["author_review"]["user_direction"])

        for row in ledger["cores"]:
            qualification = row["behavioral_qualification"]
            fixture = qualification.get("fixture")
            if fixture and not (REPO / fixture).is_file():
                self.assertEqual(
                    qualification.get("fixture_reference_state"),
                    "recorded_reference_only_file_absent_from_current_source_tree",
                    row["id"],
                )
            self.assertNotIn("cases exist but have not run", qualification["evidence_boundary"], row["id"])

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

    def test_mind_core_registry_and_custody_ledger_are_relationally_consistent(self) -> None:
        nova = self.plugin / "skills" / "nova"
        mind = nova / "references" / "mind"
        registry = json.loads((mind / "core-registry.json").read_text(encoding="utf-8"))
        ledger_path = mind / "core-adaptation-ledger.json"
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        product = json.loads((REPO / "design" / "product-contract.json").read_text(encoding="utf-8"))

        self.assertEqual(registry["component_version"], product["mind"]["version"])
        self.assertEqual(ledger["component_version"], product["mind"]["version"])
        registry_rows = {row["id"]: row for row in registry["cores"]}
        ledger_rows = {row["id"]: row for row in ledger["cores"]}
        actual = {path.stem.removesuffix(".core") for path in (mind / "faculty-cores").glob("*.core.md")}
        self.assertEqual(len(registry_rows), registry["core_count"])
        self.assertEqual(len(ledger_rows), ledger["core_count"])
        self.assertEqual(set(registry_rows), set(ledger_rows))
        self.assertEqual(set(registry_rows), actual)

        ledger_digest = hashlib.sha256(ledger_path.read_bytes()).hexdigest().upper()
        for core_id in sorted(actual):
            registered = registry_rows[core_id]
            recorded = ledger_rows[core_id]
            expected_path = f"references/mind/faculty-cores/{core_id}.core.md"
            self.assertEqual(registered["core_path"], expected_path)
            core_bytes = (nova / expected_path).read_bytes()
            core_digest = hashlib.sha256(core_bytes).hexdigest().upper()
            self.assertEqual(registered["core_sha256"], core_digest)
            self.assertEqual(registered["core_bytes"], len(core_bytes))
            self.assertEqual(recorded["core"]["sha256"], core_digest)
            self.assertEqual(recorded["core"]["bytes"], len(core_bytes))
            self.assertEqual(registered["upstream_coordinate"], recorded["upstream"]["coordinate"])
            self.assertEqual(registered["upstream_sha256"], recorded["upstream"]["sha256"])
            self.assertEqual(registered["author_review_state"], recorded["author_review"]["state"])
            self.assertEqual(
                registered["independent_prompt_review_state"],
                recorded["independent_prompt_review"]["state"],
            )
            self.assertEqual(
                registered["behavioral_qualification_state"],
                recorded["behavioral_qualification"]["state"],
            )
            self.assertEqual(registered["custody_ledger_path"], "references/mind/core-adaptation-ledger.json")
            self.assertEqual(registered["custody_ledger_sha256"], ledger_digest)
    def test_source_lock_matches_imported_bytes(self) -> None:
        self.assertEqual(len(self.lock["records"]), 27)
        for record in self.lock["records"]:
            imported = REPO / record["imported_path"]
            self.assertEqual(tree_digest(imported), record["imported_tree"], record["id"])
        self.assertEqual(tree_digest(self.plugin / "skills"), self.lock["plugin_skill_tree"])

    def test_nova_source_pin_resolves_to_the_exact_current_skill_tree(self) -> None:
        source_map = json.loads((REPO / "design" / "source-map.json").read_text(encoding="utf-8"))
        source = next(record for record in source_map["records"] if record["id"] == "nova")
        locked = next(record for record in self.lock["records"] if record["id"] == "nova")

        def git_object(specification: str) -> str:
            return subprocess.check_output(
                ["git", "rev-parse", specification],
                cwd=REPO,
                text=True,
                encoding="utf-8",
            ).strip()

        self.assertEqual(source["source_state"], "git_commit")
        self.assertEqual(source["edition_overlays"], [])
        self.assertEqual(locked["overlay_state"], "exact_selected_source")
        self.assertEqual(git_object(source["source_commit"] + "^{tree}"), source["source_commit_tree"])
        pinned_skill_tree = git_object(source["source_commit"] + ":" + source["source_path"])
        self.assertEqual(pinned_skill_tree, source["source_git_tree"])
        self.assertEqual(pinned_skill_tree, git_object("HEAD:" + source["source_path"]))
        self.assertEqual(source["source_file_count"], locked["imported_tree"]["file_count"])
        self.assertEqual(source["source_tree_sha256"], locked["imported_tree"]["tree_sha256"])
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
            self.assertEqual(manifest["rights_status"], "public-inclusion-authorized-for-nova-free-3.1.2")
            self.assertIn("Nova Free 3.1.2 public split license", manifest["license"])
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
