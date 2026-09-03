from __future__ import annotations

import copy
import json
import runpy
import subprocess
import sys
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
NOVA_SKILL_ROOT = (
    ROOT / "plugins" / "nova-the-optimal-ai" / "skills" / "nova"
)
SCHEMA_PATH = (
    NOVA_SKILL_ROOT / "assets" / "faculty-runtime" / "mission-capsule.schema.json"
)
TEMPLATE_PATH = SCHEMA_PATH.with_name("mission-capsule.template.json")
LEGACY_SCHEMA_PATH = SCHEMA_PATH.with_name("mission-capsule-v1.schema.json")
MIGRATOR_PATH = NOVA_SKILL_ROOT / "scripts" / "migrate_mission_capsule.py"
LEGACY_FIXTURE = ROOT / "tests" / "fixtures" / "mission-capsule-v1.json"
MIND_SKILL = NOVA_SKILL_ROOT / "SKILL.md"
RUNTIME = NOVA_SKILL_ROOT / "references" / "mind" / "faculty-runtime.md"

def open_pursuit() -> dict[str, object]:
    return {
        "schema": "collaborative-dynamics-mission-capsule/v2",
        "mission_id": "humane-ai-inquiry",
        "current_direction": (
            "Stay with the question of what a humane personal-AI relationship could become, "
            "preserving earned distinctions without forcing an early product or finish line."
        ),
        "phase": "model",
        "authority": {
            "granted": ["Continue the inquiry and preserve consequential state."],
            "reserved": ["Do not turn the inquiry into a product commitment."],
        },
        "active_coalition": [],
        "unresolved_transformations": [
            "Understand which forms of continuity feel supportive rather than coercive."
        ],
        "closure": {"status": "open"},
    }


class NovaMissionCapsuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(cls.schema)
        cls.validator = Draft202012Validator(cls.schema)
        cls.legacy_schema = json.loads(LEGACY_SCHEMA_PATH.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(cls.legacy_schema)
        cls.legacy_validator = Draft202012Validator(cls.legacy_schema)
        cls.migrator = runpy.run_path(str(MIGRATOR_PATH))

    def assert_valid(self, value: object) -> None:
        self.assertEqual([], list(self.validator.iter_errors(value)))

    def assert_invalid(self, value: object) -> None:
        self.assertTrue(list(self.validator.iter_errors(value)))

    def assert_legacy_valid(self, value: object) -> None:
        self.assertEqual([], list(self.legacy_validator.iter_errors(value)))

    def test_current_direction_is_required_and_substantive(self) -> None:
        missing = open_pursuit()
        del missing["current_direction"]
        self.assert_invalid(missing)

        blank = open_pursuit()
        blank["current_direction"] = "   "
        self.assert_invalid(blank)

    def test_schema_versions_keep_distinct_read_identity(self) -> None:
        self.assertEqual(
            "https://collaborative-dynamics.com/schemas/faculty-runtime/mission-capsule.schema.json",
            self.legacy_schema["$id"],
        )
        self.assertEqual(
            "https://collaborative-dynamics.com/schemas/faculty-runtime/mission-capsule-v2.schema.json",
            self.schema["$id"],
        )

    def test_open_pursuit_needs_no_acceptance_contract(self) -> None:
        capsule = open_pursuit()
        self.assertNotIn("acceptance", capsule)
        self.assert_valid(capsule)

    def test_public_template_models_sparse_open_direction(self) -> None:
        template = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
        self.assertEqual("collaborative-dynamics-mission-capsule/v2", template["schema"])
        self.assertIn("current_direction", template)
        self.assertNotIn("desired_state", template)
        self.assertNotIn("acceptance", template)
        self.assertEqual(set(self.schema["required"]), set(template))
        self.assert_valid(template)

    def test_bounded_acceptance_preserves_basis_without_forcing_evidence(self) -> None:
        for basis in ("supplied", "ratified", "inherent_to_bounded_task"):
            capsule = open_pursuit()
            capsule["acceptance"] = [
                {
                    "criterion": "The reported failure no longer reproduces.",
                    "basis": basis,
                    "status": "unmet",
                }
            ]
            with self.subTest(basis=basis):
                self.assert_valid(capsule)

        capsule["acceptance"][0]["evidence_required"] = (
            "Run the focused regression against the reported input."
        )
        self.assert_valid(capsule)

    def test_acceptance_cannot_be_empty_or_unattributed(self) -> None:
        empty = open_pursuit()
        empty["acceptance"] = []
        self.assert_invalid(empty)

        missing_basis = open_pursuit()
        missing_basis["acceptance"] = [
            {"criterion": "The repair works.", "status": "unmet"}
        ]
        self.assert_invalid(missing_basis)

        invented_basis = copy.deepcopy(missing_basis)
        invented_basis["acceptance"][0]["basis"] = "inferred"
        self.assert_invalid(invented_basis)

    def test_complete_needs_no_fabricated_acceptance_but_honors_every_recorded_criterion(self) -> None:
        no_acceptance = open_pursuit()
        no_acceptance["phase"] = "closed"
        no_acceptance["closure"] = {"status": "complete"}
        self.assert_valid(no_acceptance)

        incomplete = open_pursuit()
        incomplete["acceptance"] = [
            {
                "criterion": "The requested repair is present.",
                "basis": "inherent_to_bounded_task",
                "status": "unmet",
            }
        ]
        incomplete["phase"] = "closed"
        incomplete["closure"] = {"status": "complete"}
        self.assert_invalid(incomplete)

        mixed = copy.deepcopy(incomplete)
        mixed["acceptance"][0]["status"] = "met"
        mixed["acceptance"].append(
            {
                "criterion": "The focused regression passes.",
                "basis": "ratified",
                "status": "partially_met",
            }
        )
        self.assert_invalid(mixed)

        complete = copy.deepcopy(mixed)
        complete["acceptance"][1]["status"] = "met"
        self.assert_valid(complete)

    def test_phase_and_closure_cannot_claim_conflicting_terminal_state(self) -> None:
        complete_in_model_phase = open_pursuit()
        complete_in_model_phase["closure"] = {"status": "complete"}
        self.assert_invalid(complete_in_model_phase)

        cancelled_in_model_phase = open_pursuit()
        cancelled_in_model_phase["closure"] = {"status": "cancelled"}
        self.assert_invalid(cancelled_in_model_phase)

        closed_but_open = open_pursuit()
        closed_but_open["phase"] = "closed"
        self.assert_invalid(closed_but_open)

        cancelled = open_pursuit()
        cancelled["phase"] = "closed"
        cancelled["closure"] = {"status": "cancelled"}
        self.assert_valid(cancelled)

    def test_legacy_desired_state_is_not_silently_treated_as_v2(self) -> None:
        legacy = json.loads(LEGACY_FIXTURE.read_text(encoding="utf-8"))
        self.assert_legacy_valid(legacy)
        self.assert_invalid(legacy)

    def test_v1_fixture_migrates_without_losing_direction_or_claiming_authority(self) -> None:
        legacy = json.loads(LEGACY_FIXTURE.read_text(encoding="utf-8"))
        original = copy.deepcopy(legacy)
        migrated = self.migrator["migrate_v1_to_v2"](legacy)

        self.assertEqual(original, legacy)
        self.assertEqual("collaborative-dynamics-mission-capsule/v2", migrated["schema"])
        self.assertEqual(original["desired_state"], migrated["current_direction"])
        self.assertNotIn("desired_state", migrated)
        self.assertEqual("legacy_v1", migrated["acceptance"][0]["basis"])
        self.assertEqual(
            original["acceptance"][0]["evidence_required"],
            migrated["acceptance"][0]["evidence_required"],
        )
        self.assertNotIn("reopening_condition", migrated["closure"])
        self.assert_valid(migrated)

    def test_v1_terminal_migration_normalizes_phase_without_faking_completion(self) -> None:
        legacy = json.loads(LEGACY_FIXTURE.read_text(encoding="utf-8"))
        legacy["acceptance"][0]["status"] = "met"
        legacy["phase"] = "verify"
        legacy["closure"]["status"] = "complete"
        migrated = self.migrator["migrate_v1_to_v2"](legacy)
        self.assertEqual("closed", migrated["phase"])
        self.assert_valid(migrated)

        legacy["acceptance"][0]["status"] = "unmet"
        with self.assertRaisesRegex(
            self.migrator["CapsuleMigrationError"], "acceptance remains unmet"
        ):
            self.migrator["migrate_v1_to_v2"](legacy)

    def test_v1_cli_is_deterministic_and_read_only_by_default(self) -> None:
        command = [sys.executable, "-B", str(MIGRATOR_PATH), str(LEGACY_FIXTURE)]
        first = subprocess.run(command, check=True, capture_output=True, text=True)
        second = subprocess.run(command, check=True, capture_output=True, text=True)
        self.assertEqual(first.stdout, second.stdout)
        self.assertEqual(
            self.migrator["migrate_v1_to_v2"](
                json.loads(LEGACY_FIXTURE.read_text(encoding="utf-8"))
            ),
            json.loads(first.stdout),
        )

    def test_resting_is_an_honest_nonterminal_disposition(self) -> None:
        capsule = open_pursuit()
        capsule["closure"] = {"status": "resting"}
        self.assert_valid(capsule)

    def test_reopening_condition_is_optional_but_meaningful_when_present(self) -> None:
        capsule = open_pursuit()
        capsule["closure"] = {
            "status": "resting",
            "reopening_condition": "Resume when the user returns to the inquiry.",
        }
        self.assert_valid(capsule)
        capsule["closure"]["reopening_condition"] = "   "
        self.assert_invalid(capsule)

    def test_model_facing_guidance_matches_the_sparse_contract(self) -> None:
        skill = MIND_SKILL.read_text(encoding="utf-8")
        runtime = RUNTIME.read_text(encoding="utf-8")
        self.assertIn("may omit acceptance entirely", skill)
        self.assertIn("Omit `acceptance` for an emerging", runtime)
        self.assertIn("Let an open pursuit rest", skill)
        self.assertIn("Let an intentionally ongoing pursuit rest", runtime)
        self.assertIn("absence is not waiver", skill)
        self.assertIn("omission is not waiver", runtime)
        self.assertIn("without manufacturing acceptance", skill)
        self.assertIn("without manufactured acceptance", runtime)
        self.assertIn("every recorded criterion is `met`", skill)
        self.assertIn("every recorded criterion to be `met`", runtime)
        self.assertIn("legacy_v1", skill)
        self.assertIn("legacy_v1", runtime)



if __name__ == "__main__":
    unittest.main()
