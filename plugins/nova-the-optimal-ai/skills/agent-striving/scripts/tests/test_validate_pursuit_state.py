from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


SCRIPT = Path(__file__).resolve().parents[1] / "validate_pursuit_state.py"
ASSETS = Path(__file__).resolve().parents[2] / "assets"
TEMPLATE = ASSETS / "pursuit-state.template.json"
SCHEMA = ASSETS / "pursuit-state.schema.json"
SPEC = importlib.util.spec_from_file_location("validate_pursuit_state", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)

FORMAT_CHECKER = FormatChecker()


@FORMAT_CHECKER.checks("date-time", raises=(TypeError, ValueError))
def is_rfc3339_datetime(value: object) -> bool:
    if not isinstance(value, str) or not MODULE.TIMESTAMP_RE.fullmatch(value):
        return False
    datetime.fromisoformat(value.replace("Z", "+00:00"))
    return True


def valid_handoff() -> dict[str, object]:
    return {
        "format": "cd-agent-striving-handoff/v2",
        "pursuit_ref": "striving-repair",
        "authority_source": "User request in the current task",
        "current_direction": (
            "Repair Agent Striving until its goal language creates intelligent forward pull, "
            "its custody claims survive interruption honestly, and the affected Nova editions agree."
        ),
        "disposition": "live",
        "current_state_ref": "project://striving-repair/current",
        "foreground": {
            "settled": ["PromptCraft governs the model-facing goal directive."],
            "actual_state": "The canonical repair is under construction.",
            "blockers": [],
            "likely_continuation": "Finish the validator and exercise re-entry behavior.",
        },
        "continuity": {
            "persistence": "confirmed",
            "persistence_receipt": "continuity://striving-repair/revision/2",
            "reactivation": "manual",
            "reactivation_cue": "Load revision 2 by pursuit_ref before continuing.",
            "lost_guarantee": None,
        },
        "supersedes": "continuity://striving-repair/revision/1",
        "updated_at": "2026-09-02T12:00:00-05:00",
    }


def set_path(state: dict[str, object], path: tuple[str, ...], value: object) -> None:
    target = state
    for segment in path[:-1]:
        target = target[segment]
    target[path[-1]] = value


class PursuitStateValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(cls.schema)
        cls.schema_validator = Draft202012Validator(
            cls.schema,
            format_checker=FORMAT_CHECKER,
        )

    def assert_contract_result(self, state: object, expected_valid: bool) -> None:
        python_valid = not MODULE.validate(state)
        schema_valid = not list(self.schema_validator.iter_errors(state))
        self.assertEqual(
            python_valid,
            expected_valid,
            f"Python validator mismatch for {state!r}: {MODULE.validate(state)}",
        )
        self.assertEqual(
            schema_valid,
            expected_valid,
            f"JSON Schema mismatch for {state!r}",
        )

    def test_explicit_sparse_handoff_is_valid(self) -> None:
        self.assert_contract_result(valid_handoff(), True)

        sparse = valid_handoff()
        for field in ("current_state_ref", "supersedes"):
            sparse.pop(field)
        sparse["foreground"] = {"actual_state": "One transferable fact is known."}
        self.assert_contract_result(sparse, True)

        no_foreground = copy.deepcopy(sparse)
        no_foreground.pop("foreground")
        self.assert_contract_result(no_foreground, True)

    def test_public_template_is_deliberately_incomplete(self) -> None:
        template = json.loads(TEMPLATE.read_text(encoding="utf-8"))
        errors = MODULE.validate(template)
        self.assertIn("pursuit_ref must be a non-empty string", errors)
        self.assertIn("current_direction must be a non-empty string", errors)
        self.assertIn("incomplete continuity requires a lost_guarantee", errors)
        self.assert_contract_result(template, False)

    def test_schema_and_validator_share_declared_contract(self) -> None:
        self.assertEqual(set(self.schema["required"]), MODULE.REQUIRED)
        self.assertEqual(set(self.schema["properties"]), MODULE.REQUIRED | MODULE.OPTIONAL)
        self.assertEqual(self.schema["properties"]["format"]["const"], MODULE.FORMAT)
        self.assertEqual(
            tuple(self.schema["properties"]["disposition"]["enum"]),
            MODULE.DISPOSITIONS,
        )
        foreground = self.schema["properties"]["foreground"]
        self.assertEqual(set(foreground["properties"]), MODULE.FOREGROUND_FIELDS)
        self.assertNotIn("required", foreground)
        continuity = self.schema["properties"]["continuity"]
        self.assertEqual(set(continuity["required"]), MODULE.CONTINUITY_FIELDS)
        self.assertEqual(set(continuity["properties"]), MODULE.CONTINUITY_FIELDS)
        self.assertEqual(
            tuple(continuity["properties"]["persistence"]["enum"]),
            MODULE.PERSISTENCE,
        )
        self.assertEqual(
            tuple(continuity["properties"]["reactivation"]["enum"]),
            MODULE.REACTIVATION,
        )

    def test_shared_mutation_corpus_has_schema_runtime_parity(self) -> None:
        invalid_mutations = [
            ("missing required", lambda s: s.pop("current_direction")),
            ("unexpected root field", lambda s: s.update({"acceptance_criteria": []})),
            ("wrong format", lambda s: s.update({"format": "old"})),
            ("whitespace pursuit", lambda s: s.update({"pursuit_ref": " \t "})),
            ("whitespace authority", lambda s: s.update({"authority_source": "  "})),
            ("whitespace direction", lambda s: s.update({"current_direction": "\n"})),
            ("wrong disposition", lambda s: s.update({"disposition": "paused"})),
            ("null state ref", lambda s: s.update({"current_state_ref": None})),
            ("whitespace supersedes", lambda s: s.update({"supersedes": " "})),
            ("empty foreground", lambda s: s.update({"foreground": {}})),
            (
                "unknown foreground property",
                lambda s: s.update({"foreground": {"next_action": "ship"}}),
            ),
            (
                "whitespace actual state",
                lambda s: s.update({"foreground": {"actual_state": " "}}),
            ),
            (
                "whitespace list item",
                lambda s: s.update({"foreground": {"settled": ["ok", " "]}}),
            ),
            (
                "bad persistence enum",
                lambda s: set_path(s, ("continuity", "persistence"), "stored"),
            ),
            (
                "whitespace receipt",
                lambda s: set_path(s, ("continuity", "persistence_receipt"), " "),
            ),
            (
                "missing continuity field",
                lambda s: s["continuity"].pop("reactivation_cue"),
            ),
            (
                "released continuation",
                lambda s: s.update(
                    {
                        "disposition": "released",
                        "foreground": {"likely_continuation": "Continue anyway."},
                    }
                ),
            ),
            ("empty timestamp", lambda s: s.update({"updated_at": ""})),
            (
                "timestamp without timezone",
                lambda s: s.update({"updated_at": "2026-09-02T12:00:00"}),
            ),
            (
                "impossible date",
                lambda s: s.update({"updated_at": "2026-02-30T12:00:00Z"}),
            ),
        ]
        for name, mutate in invalid_mutations:
            state = valid_handoff()
            mutate(state)
            with self.subTest(name=name):
                self.assert_contract_result(state, False)

    def test_legacy_prd_fields_are_rejected(self) -> None:
        state = valid_handoff()
        state["acceptance_criteria"] = ["Everything passes"]
        state["budgets"] = {"limits": {}, "used": {}}
        errors = MODULE.validate(state)
        self.assertIn("unexpected fields: acceptance_criteria, budgets", errors)

    def test_every_json_root_type_is_safe(self) -> None:
        for value in (None, True, 4, "goal", [], ["goal"]):
            with self.subTest(value=value):
                self.assert_contract_result(value, False)

    def test_wrong_nested_types_return_errors_without_raising(self) -> None:
        for field, value, expected in (
            ("foreground", [], "foreground must contain one or more"),
            ("continuity", [], "continuity must contain exactly"),
            ("disposition", [], "disposition must be one of"),
        ):
            state = valid_handoff()
            state[field] = value
            with self.subTest(field=field):
                self.assertTrue(any(expected in error for error in MODULE.validate(state)))
                self.assert_contract_result(state, False)

    def test_confirmed_persistence_and_available_reactivation_require_proof(self) -> None:
        missing_receipt = valid_handoff()
        missing_receipt["continuity"]["persistence_receipt"] = None
        self.assertIn(
            "confirmed persistence requires a persistence_receipt",
            MODULE.validate(missing_receipt),
        )
        self.assert_contract_result(missing_receipt, False)

        missing_cue = valid_handoff()
        missing_cue["continuity"]["reactivation_cue"] = None
        self.assertIn(
            "available reactivation requires a reactivation_cue",
            MODULE.validate(missing_cue),
        )
        self.assert_contract_result(missing_cue, False)

    def test_prepared_state_names_the_lost_guarantee(self) -> None:
        state = valid_handoff()
        state["continuity"].update(
            {
                "persistence": "prepared",
                "persistence_receipt": None,
                "lost_guarantee": "No state owner confirmed a durable write.",
            }
        )
        self.assert_contract_result(state, True)
        state["continuity"]["lost_guarantee"] = None
        self.assertIn("incomplete continuity requires a lost_guarantee", MODULE.validate(state))
        self.assert_contract_result(state, False)

    def test_released_pursuit_omits_likely_continuation(self) -> None:
        state = valid_handoff()
        state["disposition"] = "released"
        self.assertIn("released pursuit cannot retain a likely continuation", MODULE.validate(state))
        self.assert_contract_result(state, False)
        state["foreground"].pop("likely_continuation")
        self.assert_contract_result(state, True)

    def run_cli(self, raw: bytes) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "handoff.json"
            path.write_bytes(raw)
            return subprocess.run(
                [sys.executable, str(SCRIPT), str(path), "--json"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )

    def assert_cli_rejection(self, raw: bytes) -> None:
        result = self.run_cli(raw)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(json.loads(result.stdout)["valid"])
        self.assertEqual(result.stderr, "")

    def test_cli_reports_invalid_json_and_utf8_as_json(self) -> None:
        for raw in (b"{", b"\xff"):
            with self.subTest(raw=raw):
                self.assert_cli_rejection(raw)

    def test_cli_rejects_duplicate_keys_and_nonstandard_numbers(self) -> None:
        for raw in (b'{"format":"a","format":"b"}', b'{"value":NaN}'):
            with self.subTest(raw=raw):
                self.assert_cli_rejection(raw)

    def test_cli_contains_pathological_parser_failures(self) -> None:
        for raw in (
            b'{"number":' + (b"9" * 5000) + b"}",
            (b"[" * 20000) + (b"]" * 20000),
        ):
            with self.subTest(size=len(raw)):
                self.assert_cli_rejection(raw)

    def test_cli_reports_missing_file_as_json(self) -> None:
        missing = Path(tempfile.gettempdir()) / "striving-handoff-does-not-exist.json"
        result = subprocess.run(
            [sys.executable, str(SCRIPT), str(missing), "--json"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        self.assertEqual(result.returncode, 1)
        self.assertFalse(json.loads(result.stdout)["valid"])


if __name__ == "__main__":
    unittest.main()
