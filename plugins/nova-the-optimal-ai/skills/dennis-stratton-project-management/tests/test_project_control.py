#!/usr/bin/env python3
from __future__ import annotations

import contextlib
import copy
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "project_control.py"
TEMPLATE = SKILL_ROOT / "assets" / "project-control.template.json"
spec = importlib.util.spec_from_file_location("project_control", SCRIPT)
assert spec and spec.loader
project_control = importlib.util.module_from_spec(spec)
spec.loader.exec_module(project_control)


class ProjectControlTests(unittest.TestCase):
    def record(self):
        return json.loads(TEMPLATE.read_text(encoding="utf-8"))

    def codes(self, record):
        errors, _warnings = project_control.validate_record(record)
        return {item["code"] for item in errors}

    def evidence(self, identifier="EV-001", level="verified"):
        return {
            "id": identifier,
            "claim": "The named completion state was directly observed.",
            "level": level,
            "locator": "local:test",
            "observed_at": "2026-08-13T00:00:00Z",
            "method": "deterministic test fixture",
            "limits": "Structural fixture only.",
            "actor": "test suite",
        }

    def complete_current_unit(self, evidence_level="verified"):
        record = self.record()
        record["project"]["status"] = "active"
        record["hierarchy"][0]["status"] = "active"
        record["hierarchy"][1]["status"] = "complete"
        record["authority"]["grants"][0]["status"] = "active"
        record["work_packages"][0]["status"] = "complete"
        record["exit_criteria"][0]["status"] = "verified"
        record["exit_criteria"][0]["evidence_ids"] = ["EV-001"]
        record["evidence"].append(self.evidence(level=evidence_level))
        for state in record["completion_contract"]["states"]:
            state["status"] = "satisfied"
            state["evidence_ids"] = ["EV-001"]
        record["current"]["posture"] = "complete"
        return record

    def test_maintained_template_is_valid_and_provisional(self):
        record = self.record()
        errors, warnings = project_control.validate_record(record)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])
        self.assertEqual(record["project"]["status"], "proposed")
        self.assertEqual(record["current"]["posture"], "provisional")
        self.assertEqual(record["work_packages"][0]["status"], "planned")
        self.assertEqual(record["authority"]["grants"][0]["status"], "proposed")

    def test_false_complete_posture_is_rejected(self):
        record = self.record()
        record["current"]["posture"] = "complete"
        self.assertIn("FALSE_COMPLETE_POSTURE", self.codes(record))

    def test_false_closed_project_is_rejected(self):
        record = self.record()
        record["project"]["status"] = "closed"
        self.assertIn("PROJECT_CLOSEOUT_TARGET", self.codes(record))

    def test_satisfied_completion_without_evidence_is_rejected(self):
        record = self.record()
        record["completion_contract"]["states"][0]["status"] = "satisfied"
        self.assertIn("SATISFIED_WITHOUT_EVIDENCE", self.codes(record))

    def test_unknown_completion_evidence_is_rejected(self):
        record = self.record()
        state = record["completion_contract"]["states"][0]
        state["status"] = "satisfied"
        state["evidence_ids"] = ["EV-MISSING"]
        self.assertIn("UNKNOWN_COMPLETION_EVIDENCE", self.codes(record))

    def test_rejected_evidence_cannot_support_completion(self):
        record = self.complete_current_unit(evidence_level="rejected")
        codes = self.codes(record)
        self.assertIn("INSUFFICIENT_COMPLETION_EVIDENCE", codes)
        self.assertIn("INSUFFICIENT_CRITERION_EVIDENCE", codes)
        self.assertEqual(project_control.completion_posture(record)[0], "INVALID")

    def test_verified_criterion_requires_evidence(self):
        record = self.record()
        record["exit_criteria"][0]["status"] = "verified"
        self.assertIn("CRITERION_WITHOUT_EVIDENCE", self.codes(record))

    def test_hierarchy_cycle_is_rejected(self):
        record = self.record()
        record["hierarchy"][0]["parent_id"] = "M1"
        self.assertIn("HIERARCHY_CYCLE", self.codes(record))

    def test_dependency_cycle_is_rejected(self):
        record = self.record()
        second = copy.deepcopy(record["work_packages"][0])
        second["id"] = "WP-M1-002"
        second["dependency_ids"] = ["WP-M1-001"]
        record["work_packages"][0]["dependency_ids"] = ["WP-M1-002"]
        record["work_packages"].append(second)
        self.assertIn("DEPENDENCY_CYCLE", self.codes(record))

    def test_complete_work_with_open_criteria_is_rejected(self):
        record = self.record()
        record["work_packages"][0]["status"] = "complete"
        self.assertIn("COMPLETE_WITH_OPEN_CRITERIA", self.codes(record))

    def test_complete_work_with_open_dependency_is_rejected(self):
        record = self.record()
        second = copy.deepcopy(record["work_packages"][0])
        second["id"] = "WP-M1-002"
        second["dependency_ids"] = []
        record["work_packages"].append(second)
        record["work_packages"][0]["dependency_ids"] = ["WP-M1-002"]
        record["work_packages"][0]["status"] = "complete"
        self.assertIn("COMPLETE_WITH_OPEN_DEPENDENCY", self.codes(record))

    def test_evidenced_formally_complete_unit_produces_yes(self):
        record = self.complete_current_unit()
        errors, warnings = project_control.validate_record(record)
        self.assertEqual(errors, [])
        self.assertIn("READY_FOR_CLOSEOUT_REVIEW", {item["code"] for item in warnings})
        self.assertEqual(project_control.completion_posture(record)[0], "YES")

    def test_satisfied_contract_without_formal_closeout_is_no(self):
        record = self.record()
        record["evidence"].append(self.evidence())
        for state in record["completion_contract"]["states"]:
            state["status"] = "satisfied"
            state["evidence_ids"] = ["EV-001"]
        self.assertEqual(project_control.validate_record(record)[0], [])
        self.assertEqual(project_control.completion_posture(record)[0], "NO")

    def test_invalid_record_never_headlines_yes_and_status_exits_two(self):
        record = self.complete_current_unit()
        record["evidence"] = []
        status = project_control.render_status(record)
        self.assertIn("done? INVALID.", status)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.json"
            path.write_text(json.dumps(record), encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                result = project_control.main(["status", str(path)])
        self.assertEqual(result, 2)

    def test_status_answers_governing_questions_first_and_shows_controls(self):
        status = project_control.render_status(self.record())
        self.assertIn("Is the active completion unit done? NO.", status)
        self.assertIn("Current path: Phase 1 > Milestone 1", status)
        self.assertIn("Next action:", status)
        self.assertIn("## Live controls", status)
        self.assertIn("ASM-001", status)
        self.assertIn("STRUCTURAL_DIAGNOSTICS_ONLY", status)

    def test_closed_project_with_open_sibling_is_rejected(self):
        record = self.complete_current_unit()
        sibling = copy.deepcopy(record["hierarchy"][1])
        sibling.update({"id": "M2", "label": "Milestone 2", "status": "planned", "exit_criteria_ids": []})
        record["hierarchy"].append(sibling)
        record["project"]["status"] = "closed"
        record["completion_contract"]["unit_id"] = record["project"]["id"]
        codes = self.codes(record)
        self.assertIn("CLOSED_PROJECT_WITH_OPEN_NODES", codes)

    def test_no_required_completion_state_is_rejected(self):
        record = self.record()
        for state in record["completion_contract"]["states"]:
            state["required"] = False
        self.assertIn("NO_REQUIRED_COMPLETION_STATE", self.codes(record))

    def test_completion_target_must_match_current_unit(self):
        record = self.record()
        record["completion_contract"]["unit_id"] = "PHASE-1"
        self.assertIn("COMPLETION_TARGET_MISMATCH", self.codes(record))

    def test_unconfirmed_agent_safeguard_cannot_be_active(self):
        record = self.record()
        record["authority"]["grants"][0]["kind"] = "agent_safeguard"
        record["authority"]["grants"][0]["status"] = "active"
        record["source_authority"][0]["kind"] = "task_history"
        self.assertIn("UNCONFIRMED_AGENT_SAFEGUARD", self.codes(record))

    def test_schema_rejects_extra_fields(self):
        record = self.record()
        record["surprise"] = "not in the contract"
        self.assertIn("SCHEMA_ADDITIONAL_PROPERTY", self.codes(record))

    def test_schema_rejects_duplicate_id_array_items(self):
        record = self.record()
        record["hierarchy"][1]["exit_criteria_ids"].append("EC-M1-001")
        self.assertIn("SCHEMA_UNIQUE_ITEMS", self.codes(record))

    def test_schema_rejects_malformed_completion_state_name(self):
        record = self.record()
        record["completion_contract"]["states"][0]["name"] = "built?"
        self.assertIn("SCHEMA_PATTERN", self.codes(record))

    def test_malformed_array_produces_diagnostic_not_exception(self):
        record = self.record()
        record["hierarchy"][0]["exit_criteria_ids"] = 7
        self.assertIn("SCHEMA_TYPE", self.codes(record))

    def test_invalid_timestamp_is_rejected(self):
        record = self.record()
        record["checkpoints"][0]["timestamp"] = "not-a-time"
        self.assertIn("INVALID_TIMESTAMP", self.codes(record))

    def test_bootstrap_preserves_source_locator_and_stays_provisional(self):
        record = project_control.bootstrap_record(
            "Example Project", "Example Owner", "Produce a controlled outcome.",
            "example-project", "owner:instruction-17",
        )
        self.assertEqual(record["source_authority"][0]["locator"], "owner:instruction-17")
        self.assertEqual(record["project"]["status"], "proposed")
        self.assertEqual(record["current"]["posture"], "provisional")
        self.assertEqual(project_control.validate_record(record)[0], [])

    def test_fingerprint_is_key_order_independent(self):
        record = self.record()
        reordered = dict(reversed(list(record.items())))
        self.assertEqual(project_control.fingerprint(record), project_control.fingerprint(reordered))

    def test_write_record_refuses_unapproved_overwrite(self):
        record = self.record()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "project-control.json"
            project_control.write_record(path, record, False)
            with self.assertRaises(FileExistsError):
                project_control.write_record(path, record, False)



    def test_v1_migration_is_explicit_valid_and_never_overwrites_source(self):
        legacy = self.record()
        legacy["schema_version"] = "cd-project-control/v1"
        for field in ("justification", "benefits", "governance", "forecast", "capacity", "stakeholders", "commercial_alignment", "transition"):
            legacy.pop(field)
        for control in legacy["controls"]:
            for field in ("objective", "cause_event_effect", "exposure", "treatment", "resource_commitment", "residual_state", "escalation_threshold", "acceptance_decision_id"):
                control.pop(field)
        migrated = project_control.migrate_v1(legacy)
        self.assertEqual(migrated["schema_version"], "cd-project-control/v2")
        self.assertEqual(migrated["justification"]["status"], "proposed")
        self.assertEqual(project_control.validate_record(migrated)[0], [])
        self.assertEqual(legacy["schema_version"], "cd-project-control/v1")

        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            source = temp / "legacy.json"
            output = temp / "migrated.json"
            source.write_text(json.dumps(legacy, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
            original = source.read_bytes()

            success = self.run_cli("migrate", str(source), str(output))
            self.assertEqual(success.returncode, 0, success.stderr)
            self.assertEqual(source.read_bytes(), original)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["schema_version"], "cd-project-control/v2")

            aliases = [source, temp / "unused" / ".." / source.name]
            hardlink = temp / "legacy-hardlink.json"
            try:
                hardlink.hardlink_to(source)
                aliases.append(hardlink)
            except OSError:
                pass
            for alias in aliases:
                with self.subTest(alias=str(alias)):
                    rejected = self.run_cli("migrate", str(source), str(alias), "--force")
                    self.assertEqual(rejected.returncode, 1)
                    self.assertEqual(rejected.stdout, "")
                    self.assertIn("migration output must", rejected.stderr)
                    self.assertEqual(source.read_bytes(), original)

    def test_forecast_lower_bound_cannot_exceed_upper_bound(self):
        record = self.record()
        record["forecast"]["lower"] = 10
        record["forecast"]["upper"] = 2
        self.assertIn("FORECAST_RANGE", self.codes(record))

    def test_wip_limit_exception_is_visible(self):
        record = self.record()
        record["capacity"]["active_wip"] = 2
        errors, warnings = project_control.validate_record(record)
        self.assertEqual(errors, [])
        self.assertIn("WIP_LIMIT_EXCEEDED", {item["code"] for item in warnings})

    def test_v2_evidence_authority_references_and_status_surface(self):
        status = project_control.render_status(self.record())
        self.assertIn("## Continued justification and benefits", status)
        self.assertIn("## Forecast and capacity", status)
        self.assertIn("WIP: 0/1", status)

        def consequential_record(evidence_level, decision_status, reference_id="EV-001", decision_id="DEC-001"):
            record = self.record()
            if evidence_level is not None:
                record["evidence"] = [self.evidence(reference_id, evidence_level)]
            record["benefits"][0]["status"] = "realized"
            record["benefits"][0]["evidence_ids"] = [] if evidence_level is None else [reference_id]
            record["governance"]["gates"][0]["status"] = "approved"
            record["governance"]["gates"][0]["evidence_ids"] = [] if evidence_level is None else [reference_id]
            record["transition"]["acceptance_state"] = "accepted"
            record["transition"]["support_state"] = "accepted"
            record["transition"]["evidence_ids"] = [] if evidence_level is None else [reference_id]
            record["controls"][0]["status"] = "accepted"
            record["controls"][0]["acceptance_decision_id"] = None if decision_status is None else decision_id
            if decision_status is not None:
                record["decisions"] = [{
                    "id": decision_id,
                    "status": decision_status,
                    "decision": "Accept the residual exposure.",
                    "options": ["Treat", "Avoid", "Accept"],
                    "rationale": "The accountable authority accepted the bounded residual exposure.",
                    "authority": "Project owner",
                    "source_id": "SRC-001",
                    "date": "2026-08-15",
                    "supersedes_ids": [],
                }]
            return record

        positive = consequential_record("accepted", "accepted")
        self.assertEqual(project_control.validate_record(positive)[0], [])

        missing_codes = self.codes(consequential_record(None, None))
        self.assertTrue({
            "REALIZED_BENEFIT_WITHOUT_EVIDENCE",
            "DECIDED_GATE_WITHOUT_EVIDENCE",
            "DECIDED_TRANSITION_WITHOUT_EVIDENCE",
            "CONTROL_ACCEPTED_WITHOUT_DECISION",
        }.issubset(missing_codes))

        for level in ("reported", "rejected"):
            with self.subTest(evidence_level=level):
                codes = self.codes(consequential_record(level, "rejected"))
                self.assertTrue({
                    "INSUFFICIENT_BENEFIT_EVIDENCE",
                    "INSUFFICIENT_GATE_EVIDENCE",
                    "INSUFFICIENT_TRANSITION_EVIDENCE",
                    "CONTROL_ACCEPTED_WITHOUT_DECISION",
                }.issubset(codes))

        unknown = consequential_record("accepted", "accepted")
        unknown["benefits"][0]["evidence_ids"] = ["EV-MISSING"]
        unknown["governance"]["gates"][0]["evidence_ids"] = ["EV-MISSING"]
        unknown["transition"]["evidence_ids"] = ["EV-MISSING"]
        unknown["controls"][0]["acceptance_decision_id"] = "DEC-MISSING"
        unknown_codes = self.codes(unknown)
        self.assertTrue({
            "UNKNOWN_BENEFIT_EVIDENCE",
            "UNKNOWN_GATE_EVIDENCE",
            "UNKNOWN_TRANSITION_EVIDENCE",
            "UNKNOWN_CONTROL_ACCEPTANCE_DECISION",
        }.issubset(unknown_codes))

    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, "-B", str(SCRIPT), *args],
            cwd=SKILL_ROOT,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
        )

    def test_store_resolution_precedence_is_explicit_then_environment_and_no_default(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            explicit = root / "explicit"
            environment = root / "environment"
            home = root / "home"
            resolved, source = project_control.resolve_store(explicit, {project_control.STORE_ENV_VAR: str(environment)}, home)
            self.assertEqual((resolved, source), (explicit.resolve(), "explicit"))
            resolved, source = project_control.resolve_store(None, {project_control.STORE_ENV_VAR: str(environment)}, home)
            self.assertEqual((resolved, source), (environment.resolve(), "environment"))
            with self.assertRaisesRegex(ValueError, "DENNIS_PROJECT_HOME is required in Nova Emergent"):
                project_control.resolve_store(None, {}, home)
            self.assertFalse(explicit.exists())
            self.assertFalse(environment.exists())

    def test_locate_missing_store_is_read_only(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Path(directory) / "missing-store"
            result = project_control.locate_in_store(store, project_id="example")
            self.assertFalse(result["found"])
            self.assertFalse(result["store_exists"])
            self.assertFalse(store.exists())

    def test_ensure_creates_central_layout_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Path(directory) / "estate"
            created = project_control.ensure_project(
                store, "Example Project", "Example Owner", "Produce a controlled outcome.",
                "example-project", "owner:instruction-17",
            )
            self.assertTrue(created["created"])
            record_path = Path(created["record"]["path"])
            self.assertTrue((store / "store.json").is_file())
            self.assertTrue(record_path.is_file())
            self.assertTrue(Path(created["records_directory"]).is_dir())
            self.assertEqual(record_path, store / "projects" / "example-project" / "project-control.json")
            before = record_path.read_bytes()

            existing = project_control.ensure_project(
                store, "Example Project", "Example Owner", "Produce a controlled outcome.",
                "example-project", "owner:instruction-17",
            )
            self.assertFalse(existing["created"])
            self.assertEqual(Path(existing["record"]["path"]), record_path)
            self.assertEqual(record_path.read_bytes(), before)

            for selectors in (
                {"project_id": "example-project"},
                {"project_name": "Example Project"},
                {"source_locator": "owner:instruction-17"},
            ):
                with self.subTest(selectors=selectors):
                    located = project_control.locate_in_store(store, **selectors)
                    self.assertTrue(located["found"])
                    self.assertEqual(Path(located["match"]["path"]), record_path)

    def test_ensure_refuses_identity_conflicts_and_invalid_existing_record(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Path(directory) / "estate"
            result = project_control.ensure_project(
                store, "Example Project", "Example Owner", "Outcome.", "example-project", "owner:17"
            )
            with self.assertRaises(ValueError):
                project_control.ensure_project(
                    store, "Renamed Project", "Example Owner", "Outcome.", "example-project", "owner:17"
                )
            record_path = Path(result["record"]["path"])
            invalid = json.loads(record_path.read_text(encoding="utf-8"))
            invalid["current"]["posture"] = "complete"
            record_path.write_text(json.dumps(invalid), encoding="utf-8")
            with self.assertRaises(ValueError):
                project_control.ensure_project(
                    store, "Example Project", "Example Owner", "Outcome.", "example-project", "owner:17"
                )

    def test_locate_refuses_ambiguous_records(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Path(directory) / "estate"
            first = project_control.ensure_project(
                store, "Same Name", "Owner", "Outcome.", "project-one", "owner:one"
            )
            duplicate = json.loads(Path(first["record"]["path"]).read_text(encoding="utf-8"))
            duplicate["project"]["id"] = "project-two"
            duplicate["source_authority"][0]["locator"] = "owner:two"
            second_path = store / "projects" / "project-two" / "project-control.json"
            project_control.write_record(second_path, duplicate, False)
            with self.assertRaises(ValueError):
                project_control.locate_in_store(store, project_name="Same Name")

    def test_adopt_preserves_source_and_rejects_conflicting_content(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = root / "estate"
            source = root / "external-project-control.json"
            record = project_control.bootstrap_record(
                "Imported Project", "Owner", "Outcome.", "imported-project", "owner:import"
            )
            source.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
            before = source.read_bytes()
            adopted = project_control.adopt_project(store, source)
            self.assertTrue(adopted["created"])
            self.assertTrue(adopted["source_preserved"])
            self.assertEqual(source.read_bytes(), before)
            again = project_control.adopt_project(store, source)
            self.assertFalse(again["created"])

            changed = copy.deepcopy(record)
            changed["project"]["outcome"] = "Conflicting outcome."
            source.write_text(json.dumps(changed), encoding="utf-8")
            with self.assertRaises(ValueError):
                project_control.adopt_project(store, source)

    def test_store_cli_paths_and_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Path(directory) / "estate"
            path_result = self.run_cli("store-path", "--store", str(store))
            self.assertEqual(path_result.returncode, 0, path_result.stderr)
            self.assertFalse(store.exists())
            self.assertEqual(json.loads(path_result.stdout)["source"], "explicit")

            missing = self.run_cli("locate", "--store", str(store), "--project-id", "example-project")
            self.assertEqual(missing.returncode, 0, missing.stderr)
            self.assertFalse(json.loads(missing.stdout)["found"])
            self.assertFalse(store.exists())

            ensured = self.run_cli(
                "ensure", "--store", str(store), "--project-id", "example-project",
                "--project-name", "Example Project", "--owner", "Owner",
                "--outcome", "Outcome.", "--source-locator", "owner:17",
            )
            self.assertEqual(ensured.returncode, 0, ensured.stderr)
            self.assertTrue(json.loads(ensured.stdout)["created"])

            located = self.run_cli("locate", "--store", str(store), "--source-locator", "owner:17")
            self.assertEqual(located.returncode, 0, located.stderr)
            self.assertTrue(json.loads(located.stdout)["found"])

            listed = self.run_cli("list-projects", "--store", str(store))
            self.assertEqual(listed.returncode, 0, listed.stderr)
            self.assertEqual(len(json.loads(listed.stdout)["projects"]), 1)

            no_selector = self.run_cli("locate", "--store", str(store))
            self.assertEqual(no_selector.returncode, 1)
            self.assertEqual(no_selector.stdout, "")
            self.assertIn("project_control:", no_selector.stderr)

    def test_cli_exit_contract_for_success_usage_operational_invalid_overwrite_and_warning(self):
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            valid_path = temp / "valid.json"
            invalid_path = temp / "invalid.json"
            malformed_path = temp / "malformed.json"
            non_object_path = temp / "non-object.json"
            missing_path = temp / "missing.json"
            status_path = temp / "status.md"
            warning_path = temp / "warning.json"
            valid_path.write_text(json.dumps(self.record()), encoding="utf-8")
            invalid = self.record()
            invalid["current"]["posture"] = "complete"
            invalid_path.write_text(json.dumps(invalid), encoding="utf-8")
            malformed_path.write_text("{", encoding="utf-8")
            non_object_path.write_text("[]", encoding="utf-8")
            warning = self.record()
            warning["authority"]["grants"][0]["may"] = []
            warning["authority"]["grants"][0]["may_not"] = []
            warning_path.write_text(json.dumps(warning), encoding="utf-8")

            for command in ("bootstrap", "validate", "fingerprint", "status"):
                with self.subTest(command=command, case="usage"):
                    result = self.run_cli(command)
                    self.assertEqual(result.returncode, 2)
                    self.assertEqual(result.stdout, "")
                    self.assertIn("usage:", result.stderr)

            for command in ("validate", "fingerprint", "status"):
                with self.subTest(command=command, case="missing-file"):
                    result = self.run_cli(command, str(missing_path))
                    self.assertEqual(result.returncode, 1)
                    self.assertEqual(result.stdout, "")
                    self.assertIn("project_control:", result.stderr)
                with self.subTest(command=command, case="malformed-json"):
                    result = self.run_cli(command, str(malformed_path))
                    self.assertEqual(result.returncode, 1)
                    self.assertEqual(result.stdout, "")
                    self.assertIn("project_control:", result.stderr)

                with self.subTest(command=command, case="non-object-json"):
                    result = self.run_cli(command, str(non_object_path))
                    self.assertEqual(result.returncode, 1)
                    self.assertEqual(result.stdout, "")
                    self.assertIn("project_control:", result.stderr)
                with self.subTest(command=command, case="unreadable-directory"):
                    result = self.run_cli(command, str(temp))
                    self.assertEqual(result.returncode, 1)
                    self.assertEqual(result.stdout, "")
                    self.assertIn("project_control:", result.stderr)
            validate_success = self.run_cli("validate", str(valid_path))
            self.assertEqual(validate_success.returncode, 0)
            self.assertTrue(validate_success.stdout.startswith("VALID"))
            self.assertEqual(validate_success.stderr, "")

            fingerprint_success = self.run_cli("fingerprint", str(valid_path))
            self.assertEqual(fingerprint_success.returncode, 0)
            self.assertRegex(fingerprint_success.stdout.strip(), r"^[0-9a-f]{64}$")
            self.assertEqual(fingerprint_success.stderr, "")

            status_success = self.run_cli("status", str(valid_path), "--output", str(status_path))
            self.assertEqual(status_success.returncode, 0)
            self.assertEqual(status_success.stdout, "")
            self.assertEqual(status_success.stderr, "")
            self.assertTrue(status_path.is_file())

            for command in ("validate", "status"):
                with self.subTest(command=command, case="invalid-record"):
                    result = self.run_cli(command, str(invalid_path))
                    self.assertEqual(result.returncode, 2)
                    self.assertNotEqual(result.stdout, "")
                    self.assertEqual(result.stderr, "")

            warning_result = self.run_cli("validate", str(warning_path))
            self.assertEqual(warning_result.returncode, 0)
            self.assertIn("WARNING EMPTY_GRANT", warning_result.stdout)
            self.assertEqual(warning_result.stderr, "")

            invalid_bootstrap = self.run_cli(
                "bootstrap", str(temp / "invalid-bootstrap.json"),
                "--project-id", "bad id with spaces",
                "--project-name", "Example Project",
                "--owner", "Example Owner",
                "--outcome", "Produce a controlled outcome.",
            )
            self.assertEqual(invalid_bootstrap.returncode, 1)
            self.assertEqual(invalid_bootstrap.stdout, "")
            self.assertIn("project_control:", invalid_bootstrap.stderr)
            bootstrap_path = temp / "bootstrap.json"
            bootstrap_success = self.run_cli(
                "bootstrap", str(bootstrap_path),
                "--project-name", "Example Project",
                "--owner", "Example Owner",
                "--outcome", "Produce a controlled outcome.",
            )
            self.assertEqual(bootstrap_success.returncode, 0)
            self.assertNotEqual(bootstrap_success.stdout, "")
            self.assertEqual(bootstrap_success.stderr, "")
            overwrite = self.run_cli(
                "bootstrap", str(bootstrap_path),
                "--project-name", "Example Project",
                "--owner", "Example Owner",
                "--outcome", "Produce a controlled outcome.",
            )
            self.assertEqual(overwrite.returncode, 1)
            self.assertEqual(overwrite.stdout, "")
            self.assertIn("project_control:", overwrite.stderr)

            status_path.write_text("preserve", encoding="utf-8")
            status_overwrite = self.run_cli("status", str(valid_path), "--output", str(status_path))
            self.assertEqual(status_overwrite.returncode, 1)
            self.assertEqual(status_overwrite.stdout, "")
            self.assertIn("project_control:", status_overwrite.stderr)

    def test_each_command_missing_required_arguments_exits_two_with_usage(self):
        for command in ("bootstrap", "validate", "fingerprint", "status"):
            with self.subTest(command=command):
                stderr = io.StringIO()
                with contextlib.redirect_stderr(stderr), self.assertRaises(SystemExit) as raised:
                    project_control.build_parser().parse_args([command])
                self.assertEqual(raised.exception.code, 2)
                self.assertIn("usage:", stderr.getvalue())

if __name__ == "__main__":
    unittest.main(verbosity=2)
