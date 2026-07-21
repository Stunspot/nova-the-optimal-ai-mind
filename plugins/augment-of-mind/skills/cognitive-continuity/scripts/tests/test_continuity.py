from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1]
STORE = SCRIPTS / "continuity_store.py"
COMPILE = SCRIPTS / "compile_context.py"
VALIDATE = SCRIPTS / "validate_continuity.py"


class ContinuityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / ".continuity"
        self.run_store("init", str(self.root), "--user", "demo-user", "--project", "demo-project", "--agent", "demo-agent")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_script(self, script: Path, *args: str, expected: int = 0) -> subprocess.CompletedProcess[str]:
        result = subprocess.run([sys.executable, str(script), *args], text=True, capture_output=True, check=False)
        self.assertEqual(expected, result.returncode, msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}")
        return result

    def run_store(self, *args: str, expected: int = 0) -> dict:
        result = self.run_script(STORE, *args, expected=expected)
        return json.loads(result.stdout) if result.stdout.strip().startswith("{") else {}

    def episode(self, content: str, kind: str = "assertion") -> str:
        receipt = self.run_store("episode", str(self.root), "--type", kind, "--content", content, "--source-kind", "user", "--authority", "user-explicit")
        return receipt["episode_id"]

    def records(self) -> list[dict]:
        path = self.root / "state" / "records.jsonl"
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]

    def proposals(self) -> list[dict]:
        path = self.root / "proposals" / "proposals.jsonl"
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]

    def test_explicit_state_and_freshness_supersession(self) -> None:
        first_ep = self.episode("The delivery address is 10 Old Road.")
        first = self.run_store("record", str(self.root), "--kind", "user_model", "--content", "Delivery address: 10 Old Road", "--source-ids", first_ep, "--authority", "user-explicit")
        second_ep = self.episode("Correction: the delivery address is 22 New Street.", "correction")
        second = self.run_store("record", str(self.root), "--kind", "user_model", "--content", "Delivery address: 22 New Street", "--source-ids", second_ep, "--authority", "user-explicit", "--supersedes", first["record_id"])
        by_id = {row["id"]: row for row in self.records()}
        self.assertEqual("superseded", by_id[first["record_id"]]["status"])
        self.assertEqual("current", by_id[second["record_id"]]["status"])

    def test_compiler_excludes_superseded_state(self) -> None:
        old_ep = self.episode("Publication is allowed.", "permission")
        old = self.run_store("record", str(self.root), "--kind", "permission", "--content", "Publication is allowed", "--source-ids", old_ep, "--authority", "user-explicit")
        new_ep = self.episode("Publication permission is revoked.", "permission")
        self.run_store("record", str(self.root), "--kind", "permission", "--content", "Publication permission is revoked", "--source-ids", new_ep, "--authority", "user-explicit", "--supersedes", old["record_id"])
        output = self.root / "contexts" / "launch.md"
        self.run_script(COMPILE, str(self.root), "--task", "Prepare the launch", "--output", str(output), "--budget", "4000")
        text = output.read_text(encoding="utf-8")
        metadata = json.loads(output.with_suffix(".md.json").read_text(encoding="utf-8"))
        self.assertIn("revoked", text)
        self.assertNotIn(old["record_id"], metadata["selected_ids"])
        self.assertIn("do not override typed current state", text)

    def test_compiler_accepts_date_only_valid_from(self) -> None:
        episode = self.run_store(
            "episode", str(self.root), "--type", "assertion",
            "--content", "Date-only effective state", "--source-kind", "user",
            "--authority", "user-explicit", "--valid-from", "2000-01-01",
        )["episode_id"]
        record = self.run_store(
            "record", str(self.root), "--kind", "belief",
            "--content", "Date-only effective state", "--source-ids", episode,
            "--authority", "user-explicit", "--valid-from", "2000-01-01",
        )
        output = self.root / "contexts" / "date-only.md"
        self.run_script(COMPILE, str(self.root), "--task", "Use date-only state", "--output", str(output))
        selected = json.loads(output.with_suffix(".md.json").read_text(encoding="utf-8"))["selected_ids"]
        self.assertIn(record["record_id"], selected)

    def test_dream_proposal_cannot_self_apply(self) -> None:
        ep = self.episode("A launch exception reversed the normal onboarding order.", "outcome")
        proposal = self.run_store("propose", str(self.root), "--origin", "dream", "--operation", "add", "--kind", "hypothesis", "--content", "Reversing onboarding may remove the bottleneck", "--source-ids", ep, "--rationale", "Incubation linked the exception to the stuck plan", "--authority-required", "waking-review", "--risk", "consequential")
        result = self.run_script(STORE, "apply", str(self.root), "--proposal-id", proposal["proposal_id"], "--authority", "agent", expected=2)
        self.assertIn("waking review", result.stderr)
        self.assertEqual([], self.records())

    def test_waking_review_allows_authorized_dream_proposal(self) -> None:
        ep = self.episode("A launch exception reversed the normal onboarding order.", "outcome")
        proposal = self.run_store("propose", str(self.root), "--origin", "dream", "--operation", "add", "--kind", "hypothesis", "--content", "Test reversed onboarding", "--source-ids", ep, "--rationale", "Bounded incubation", "--authority-required", "user-review", "--risk", "consequential", "--waking-review-id", "WR-001")
        applied = self.run_store("apply", str(self.root), "--proposal-id", proposal["proposal_id"], "--authority", "user-approved", "--waking-approved")
        self.assertTrue(applied["waking_approved"])
        self.assertEqual("hypothesis", self.records()[0]["kind"])

    def test_forgetting_traverses_state_proposals_and_derived_files(self) -> None:
        ep = self.episode("Client Juniper uses the private codename Cedar.")
        state = self.run_store("record", str(self.root), "--kind", "relationship", "--content", "Juniper codename is Cedar", "--source-ids", ep, "--authority", "user-explicit")
        self.run_store("propose", str(self.root), "--origin", "consolidation", "--operation", "add", "--kind", "belief", "--content", "Juniper may prefer private codenames", "--source-ids", ep, "--rationale", "Derived pattern", "--authority-required", "user-review", "--risk", "sensitive")
        derived = self.root / "contexts" / "juniper.md"
        derived.write_text(f"uses {state['record_id']} from {ep}\n", encoding="utf-8")
        receipt = self.run_store("forget", str(self.root), "--ids", ep)
        self.assertGreaterEqual(receipt["removed_id_count"], 3)
        self.assertEqual([], self.records())
        self.assertEqual([], self.proposals())
        self.assertFalse(derived.exists())
        self.run_script(VALIDATE, str(self.root))

    def test_export_is_checksum_bound_and_import_is_quarantined(self) -> None:
        ep = self.episode("Continue the demo project from the current private draft.")
        self.run_store("record", str(self.root), "--kind", "goal", "--content", "Continue the demo project from private draft", "--source-ids", ep, "--authority", "user-explicit")
        export_path = Path(self.temp.name) / "demo-export.json"
        self.run_store("export", str(self.root), "--output", str(export_path))
        destination = Path(self.temp.name) / "destination"
        self.run_store("init", str(destination), "--user", "demo-user", "--project", "demo-project", "--agent", "destination-agent")
        receipt = self.run_store("import", str(destination), "--input", str(export_path))
        self.assertFalse(receipt["canonical_state_changed"])
        self.assertTrue((destination / receipt["quarantine"]).exists())
        self.assertEqual([], [json.loads(line) for line in (destination / "state" / "records.jsonl").read_text(encoding="utf-8").splitlines() if line])

    def test_validator_detects_cross_scope_corruption(self) -> None:
        ep = self.episode("Scope test")
        self.run_store("record", str(self.root), "--kind", "belief", "--content", "Scope test", "--source-ids", ep, "--authority", "user-explicit")
        rows = self.records()
        rows[0]["scope"]["project"] = "other-project"
        (self.root / "state" / "records.jsonl").write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
        result = self.run_script(VALIDATE, str(self.root), expected=1)
        self.assertIn("crosses manifest scope", result.stdout)

    def test_validator_reports_unavailable_semantic_ranking_as_capability_note(self) -> None:
        result = self.run_script(VALIDATE, str(self.root), "--json")
        report = json.loads(result.stdout)
        note = "semantic ranking is unavailable or disabled; deterministic compilation remains valid, and packets without caller-supplied ranked IDs record semantic relevance as unexercised"
        self.assertEqual("valid", report["status"])
        self.assertNotIn(note, report["warnings"])
        self.assertEqual([note], report["capability_notes"])

        text_result = self.run_script(VALIDATE, str(self.root))
        self.assertIn(f"CAPABILITY NOTE: {note}", text_result.stdout)
        self.assertNotIn(f"WARNING: {note}", text_result.stdout)

    def test_harness_global_store_accepts_scoped_records_and_compiles_visible_layers(self) -> None:
        root = Path(self.temp.name) / "harness-continuity"
        self.run_store("init", str(root), "--user", "demo-user", "--project", "*", "--agent", "demo-agent")

        def add(content: str, *scope_args: str) -> str:
            episode = self.run_store(
                "episode", str(root), "--type", "decision", "--content", content,
                "--source-kind", "user", "--authority", "user-explicit", *scope_args,
            )["episode_id"]
            return self.run_store(
                "record", str(root), "--kind", "decision", "--content", content,
                "--source-ids", episode, "--authority", "user-explicit", *scope_args,
            )["record_id"]

        global_id = add("Global preference")
        project_id = add("Atlas project decision", "--project", "atlas")
        thread_id = add("Atlas thread decision", "--project", "atlas", "--thread", "thread-1")
        other_project_id = add("Borealis project decision", "--project", "borealis")
        other_thread_id = add("Other Atlas thread", "--project", "atlas", "--thread", "thread-2")

        self.run_script(VALIDATE, str(root))
        output = root / "contexts" / "atlas.md"
        self.run_script(
            COMPILE, str(root), "--task", "Continue Atlas", "--output", str(output),
            "--budget", "5000", "--project", "atlas", "--thread", "thread-1",
        )
        selected = set(json.loads(output.with_suffix(".md.json").read_text(encoding="utf-8"))["selected_ids"])
        self.assertTrue({global_id, project_id, thread_id}.issubset(selected))
        self.assertNotIn(other_project_id, selected)
        self.assertNotIn(other_thread_id, selected)


if __name__ == "__main__":
    unittest.main()
