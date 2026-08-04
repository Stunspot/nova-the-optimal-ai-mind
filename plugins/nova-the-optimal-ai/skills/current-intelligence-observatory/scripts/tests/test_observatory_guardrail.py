from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from observatory_guardrail import (  # noqa: E402
    canonical_url,
    delta_report,
    project_case,
    publication_blockers,
    receipt,
    validate_case,
    verify_projection_invariants,
)


COLLECTIONS = ("sources", "captures", "observations", "claims", "events", "entities", "relations", "inferences", "hypotheses", "contradictions", "assessments", "recommendations", "decisions", "outcomes", "artifacts", "checks", "blockers", "history")


def case() -> dict:
    value = {
        "format": "cd-observatory-case/v1", "case_id": "CASE-1", "title": "Case",
        "phase": "challenged", "posture": "reviewable", "question": "What changed?",
        "audience_or_decision": "Editor", "time_horizon": "48 hours", "scope": "Synthetic fixture",
        "collection_authority": "Local supplied files", "harm_model": "No real people",
        "evidence_burden": "Two independent sources", "stop_condition": "Question answered or blocked",
        "next_action": {"action": "Review", "owner": "Human", "advance_when": "Checks pass"},
    }
    value.update({name: [] for name in COLLECTIONS})
    value["sources"] = [{"id": "SRC-1", "status": "available", "confidence": "unrated", "uncertainty": "authorship not independently verified"}]
    value["captures"] = [{"id": "CAP-1", "source_ids": ["SRC-1"], "original_url": "https://example.test/report?utm_source=x", "canonical_url": "https://example.test/report", "retrieved_at": "2026-07-19T12:00:00Z", "artifact_path": "report.txt", "sha256": "A" * 64, "preservation_status": "preserved", "status": "preserved"}]
    value["claims"] = [{"id": "CLM-1", "statement": "A provisional claim", "capture_ids": ["CAP-1"], "status": "provisional", "confidence": "low", "uncertainty": "single source", "provenance_ids": ["CAP-1"], "first_seen_at": "2026-07-19T12:00:00Z"}]
    value["history"] = [{"id": "HIST-1", "status": "recorded", "summary": "Case opened"}]
    return value


class GuardrailTests(unittest.TestCase):
    def test_valid_case(self):
        self.assertEqual(validate_case(case()), [])

    def test_url_canonicalization_removes_tracking_and_fragment(self):
        self.assertEqual(canonical_url("HTTPS://Example.Test:443/a?b=2&utm_x=1&a=3#x"), "https://example.test/a?a=3&b=2")

    def test_url_rejects_credentials(self):
        with self.assertRaises(ValueError):
            canonical_url("https://person:secret@example.test/a")

    def test_duplicate_id(self):
        value = case(); value["events"] = [{"id": "SRC-1"}]
        self.assertIn("duplicate id: SRC-1", validate_case(value))

    def test_dangling_reference(self):
        value = case(); value["claims"][0]["capture_ids"] = ["MISSING"]
        self.assertTrue(any("dangling" in error for error in validate_case(value)))

    def test_capture_normalization_mismatch(self):
        value = case(); value["captures"][0]["canonical_url"] = "https://example.test/wrong"
        self.assertTrue(any("canonical_url" in error for error in validate_case(value)))

    def test_time_conflict(self):
        value = case(); value["events"] = [{"id": "EV-1", "event_start": "2026-07-20T00:00:00Z", "event_end": "2026-07-19T00:00:00Z"}]
        self.assertTrue(any("event_start is after" in error for error in validate_case(value)))

    def test_coordinate_range(self):
        value = case(); value["events"] = [{"id": "EV-1", "location": {"latitude": 91, "longitude": 0}}]
        self.assertTrue(any("latitude" in error for error in validate_case(value)))

    def test_uncertain_location_can_use_region(self):
        value = case(); value["events"] = [{"id": "EV-1", "location": {"region": "North harbor area", "precision": "regional"}}]
        self.assertEqual(validate_case(value), [])

    def test_watch_ready_requires_spec_and_checks(self):
        value = case(); value["posture"] = "watch-ready"
        errors = validate_case(value)
        self.assertTrue(any("watch specification" in error for error in errors))
        self.assertTrue(any("baseline-integrity" in error for error in errors))

    def test_publication_ready_requires_named_checks(self):
        value = case(); value["posture"] = "publication-ready"
        self.assertTrue(any("publication-ready requires passed" in error for error in validate_case(value)))

    def test_material_identity_collision_blocks_publication(self):
        value = case(); value["entities"] = [{"id": "ENT-1", "resolution_status": "collision", "material_to_publication": True}]
        self.assertEqual(publication_blockers(value), ["ENT-1"])

    def test_high_risk_claim_needs_human_approval(self):
        value = case(); value["claims"][0]["high_risk"] = True
        self.assertIn("CLM-1", publication_blockers(value))

    def test_projection_preserves_epistemic_invariants(self):
        value = case(); projections = project_case(value)
        self.assertEqual(verify_projection_invariants(value, projections), [])
        ledger_claim = next(item for item in projections["ledger"]["items"] if item["id"] == "CLM-1")
        self.assertEqual(ledger_claim["status"], "provisional")
        self.assertEqual(ledger_claim["confidence"], "low")

    def test_projection_tamper_is_detected(self):
        value = case(); projections = project_case(value)
        next(item for item in projections["ledger"]["items"] if item["id"] == "CLM-1")["confidence"] = "high"
        self.assertTrue(any("changed invariant confidence" in error for error in verify_projection_invariants(value, projections)))

    def test_delta_categories_correction_and_new_item(self):
        before = case(); after = copy.deepcopy(before)
        after["claims"][0]["status"] = "corrected"; after["claims"][0]["supersedes_ids"] = ["CLM-1"]
        after["observations"] = [{"id": "OBS-NEW", "status": "candidate"}]
        classes = delta_report(before, after)["classes"]
        self.assertIn("CLM-1", classes["corrected_or_superseded"])
        self.assertIn("OBS-NEW", classes["newly_observed"])

    def test_delta_retrieval_time_only_is_unchanged(self):
        before = case(); after = copy.deepcopy(before)
        after["captures"][0]["retrieved_at"] = "2026-07-19T13:00:00Z"
        self.assertIn("CAP-1", delta_report(before, after)["classes"]["unchanged"])

    def test_capture_receipt_hashes_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "source.txt"; path.write_bytes(b"known bytes")
            value = receipt(path, "SRC-X", "CAP-X", "https://example.test/a?utm_source=x", None, "2026-07-19T12:00:00Z")
            self.assertEqual(value["canonical_url"], "https://example.test/a")
            self.assertEqual(len(value["sha256"]), 64)
            self.assertEqual(value["preservation_status"], "preserved")


if __name__ == "__main__":
    unittest.main()
