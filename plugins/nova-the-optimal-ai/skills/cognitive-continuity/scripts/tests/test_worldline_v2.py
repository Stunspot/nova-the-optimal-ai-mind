from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

import worldline
from workspace_runtime import ContinuityError, initialize_workspace, transaction, tree_digest

WORLDLINE = SCRIPTS / "worldline.py"
LEGACY_STORE = SCRIPTS / "continuity_store.py"
AT = "2026-08-13T10:00:00Z"
AS_OF = "2026-08-14T00:00:00Z"
BASE_SCOPE = {"user": "demo-user", "project": "demo-project", "agent": "nova", "thread": None}


def episode(
    identifier: str,
    content: str,
    *,
    event_type: str = "assertion",
    scope: dict | None = None,
    source_kind: str = "user",
    locator: str | None = None,
) -> dict:
    return {
        "id": identifier,
        "type": event_type,
        "recorded_at": AT,
        "valid_from": AT,
        "valid_to": None,
        "expires_at": None,
        "scope": dict(scope or BASE_SCOPE),
        "source": {"kind": source_kind, "locator": locator, "authority": "user-test"},
        "content": content,
        "sensitivity": "ordinary",
        "retention": "until-user-changes",
        "tags": [],
    }


def record(
    identifier: str,
    kind: str,
    content: str,
    source_ids: list[str],
    *,
    scope: dict | None = None,
    status: str = "current",
    tags: list[str] | None = None,
    supersedes: list[str] | None = None,
    conflicts: list[str] | None = None,
    valid_to: str | None = None,
) -> dict:
    return {
        "id": identifier,
        "kind": kind,
        "status": status,
        "scope": dict(scope or BASE_SCOPE),
        "content": content,
        "recorded_at": AT,
        "valid_from": AT,
        "valid_to": valid_to,
        "source_ids": source_ids,
        "source_class": "episode-linked",
        "authority": "user-test",
        "confidence": "source-supported",
        "sensitivity": "ordinary",
        "retention": "until-user-changes",
        "expires_at": None,
        "supersedes": supersedes or [],
        "conflicts_with": conflicts or [],
        "derived_from": [],
        "tags": tags or [],
        "governance": {"operation": "recorded", "authority": "user-test", "at": AT, "proposal_id": None},
    }


class WorldlineV2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name).resolve()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def workspace(
        self,
        name: str,
        episodes: list[dict],
        records: list[dict],
        *,
        manifest_project: str = "demo-project",
    ) -> Path:
        root = self.base / name
        initialize_workspace(
            str(root),
            user="demo-user",
            project=manifest_project,
            agent="nova",
            thread=None,
            sensitivity="ordinary",
            retention="until-user-changes",
        )
        with transaction(
            root,
            "worldline-test-fixture",
            expected_generation=0,
            selector="generic_explicit",
            authority="user-test",
            idempotency_key=f"fixture-{name}",
            request_payload={"fixture": name},
            source_ids=[row["id"] for row in episodes],
        ) as tx:
            tx.write_jsonl(root / "episodes" / "events.jsonl", episodes)
            tx.write_jsonl(root / "state" / "records.jsonl", records)
            tx.finish("fixture-written", {"episode_count": len(episodes), "record_count": len(records)})
        return root

    def request(
        self,
        root: Path,
        mode: str = "resume",
        *,
        task: str = "Continue the demo project",
        project: str = "demo-project",
        thread: str | None = None,
        budget: int = 12000,
        portable: dict | None = None,
    ) -> dict:
        value = {
            "format": "cd-worldline-request/v1",
            "request_id": f"REQ-{mode}",
            "correlation_id": "CORR-worldline-test",
            "operation": "worldline.compile",
            "mode": mode,
            "task": task,
            "scope": {"user": "demo-user", "project": project, "agent": "nova", "thread": thread},
            "authority": "user-test-read",
            "sensitivity_ceiling": "limited",
            "as_of": AS_OF,
            "expiry_minutes": 30,
            "budget": budget,
            "deadline_ms": 10000,
            "required_ids": [],
            "workspace": {"selection_mode": "generic_explicit", "path": str(root.resolve()), "grant_id": None},
            "environment": {"name": None, "version": None},
            "unreachable_source_ids": [],
        }
        if portable is not None:
            value["portable_material"] = portable
        return value

    def portable_material(self) -> dict:
        return {
            "source_ids": ["CALLER-1"],
            "decisions": [],
            "commitments": [{
                "id": "PORT-COMMIT-1",
                "statement": "Continue from the portable handoff",
                "source_ids": ["CALLER-1"],
                "authority": "user-test",
                "recorded_at": AT,
                "conflicts_with": [],
            }],
            "blockers": [],
            "next_actions": [{
                "id": "PORT-NEXT-1",
                "statement": "Run the next disposable probe",
                "source_ids": ["CALLER-1"],
                "authority": "user-test",
                "recorded_at": AT,
                "conflicts_with": [],
            }],
            "artifact_locators": [],
            "chronology": [{
                "id": "PORT-EVENT-1",
                "at": AT,
                "event_type": "caller_handoff",
                "summary": "A caller supplied this bounded handoff",
                "source_ids": ["CALLER-1"],
            }],
            "conflicts": [],
            "resumption_pointer": {
                "text": "Run the next disposable probe",
                "source_ids": ["CALLER-1"],
                "record_ids": ["PORT-NEXT-1"],
            },
        }


    def test_100_plus_distractors_and_project_thread_isolation(self) -> None:
        target_scope = {**BASE_SCOPE, "project": "atlas", "thread": "thread-a"}
        episodes = [
            episode("EP-TARGET", "OAuth recovery decision for Worldline", scope=target_scope),
            episode("EP-OTHER-PROJECT", "PRIVATE OTHER PROJECT DECISION", scope={**BASE_SCOPE, "project": "borealis", "thread": "thread-a"}),
            episode("EP-OTHER-THREAD", "PRIVATE OTHER THREAD DECISION", scope={**BASE_SCOPE, "project": "atlas", "thread": "thread-b"}),
        ]
        records = [
            record("ST-TARGET", "decision", "Use the OAuth recovery decision", ["EP-TARGET"], scope=target_scope),
            record("ST-OTHER-PROJECT", "decision", "PRIVATE OTHER PROJECT DECISION", ["EP-OTHER-PROJECT"], scope={**BASE_SCOPE, "project": "borealis", "thread": "thread-a"}),
            record("ST-OTHER-THREAD", "decision", "PRIVATE OTHER THREAD DECISION", ["EP-OTHER-THREAD"], scope={**BASE_SCOPE, "project": "atlas", "thread": "thread-b"}),
        ]
        for index in range(105):
            identifier = f"{index:03d}"
            episodes.append(episode(f"EP-D{identifier}", f"Unrelated archive ledger {identifier}", scope=target_scope))
            records.append(record(f"ST-D{identifier}", "decision", f"Unrelated archive ledger {identifier}", [f"EP-D{identifier}"], scope=target_scope))
        root = self.workspace("distractors", episodes, records, manifest_project="*")
        view = worldline.compile_worldline(self.request(
            root, task="Resume OAuth recovery", project="atlas", thread="thread-a", budget=6000,
        ))
        selected = {item["id"] for item in view["decisions"]}
        rendered = json.dumps(view)
        self.assertIn("ST-TARGET", selected)
        self.assertNotIn("PRIVATE OTHER PROJECT", rendered)
        self.assertNotIn("PRIVATE OTHER THREAD", rendered)
        self.assertGreaterEqual(view["counts"]["candidate_records"], 108)
        self.assertIn("ST-OTHER-PROJECT", view["omitted_ids"])
        self.assertIn("ST-OTHER-THREAD", view["omitted_ids"])

    def test_specific_project_withholds_highly_matching_global_operative_state(self) -> None:
        global_scope = {**BASE_SCOPE, "project": "*"}
        target_scope = {**BASE_SCOPE, "project": "atlas"}
        episodes = [
            episode("EP-GLOBAL-GOAL", "Resume Atlas OAuth migration immediately", scope=global_scope),
            episode("EP-GLOBAL-COMMIT", "Resume Atlas OAuth migration immediately", scope=global_scope),
            episode("EP-GLOBAL-BLOCK", "Atlas OAuth migration is blocked globally", scope=global_scope),
            episode("EP-GLOBAL-STATUS", "Status: Atlas OAuth migration active", scope=global_scope),
            episode("EP-GLOBAL-PHASE", "Phase: Atlas OAuth migration", scope=global_scope),
            episode("EP-ATLAS-NEXT", "Review the Atlas project control", scope=target_scope),
        ]
        records = [
            record("ST-GLOBAL-GOAL", "goal", "Resume Atlas OAuth migration immediately", ["EP-GLOBAL-GOAL"], scope=global_scope),
            record("ST-GLOBAL-COMMIT", "commitment", "Resume Atlas OAuth migration immediately", ["EP-GLOBAL-COMMIT"], scope=global_scope),
            record("ST-GLOBAL-BLOCK", "belief", "Atlas OAuth migration is blocked globally", ["EP-GLOBAL-BLOCK"], scope=global_scope, tags=["blocker"]),
            record("ST-GLOBAL-STATUS", "belief", "Status: Atlas OAuth migration active", ["EP-GLOBAL-STATUS"], scope=global_scope, tags=["status"]),
            record("ST-GLOBAL-PHASE", "belief", "Phase: Atlas OAuth migration", ["EP-GLOBAL-PHASE"], scope=global_scope, tags=["phase"]),
            record("ST-ATLAS-NEXT", "goal", "Review the Atlas project control", ["EP-ATLAS-NEXT"], scope=target_scope),
        ]
        root = self.workspace("global-operative-competition", episodes, records, manifest_project="*")
        view = worldline.compile_worldline(self.request(
            root,
            task="Resume Atlas OAuth migration immediately",
            project="atlas",
        ))
        selected_ids = {
            item["id"]
            for category in ("commitments", "blockers", "next_actions")
            for item in view[category]
        }
        if view["current_status"]:
            selected_ids.add(view["current_status"]["id"])
        if view["current_phase"]:
            selected_ids.add(view["current_phase"]["id"])
        self.assertEqual(["ST-ATLAS-NEXT"], [item["id"] for item in view["next_actions"]])
        self.assertEqual(["ST-ATLAS-NEXT"], view["resumption_pointer"]["record_ids"])
        for identifier in (
            "ST-GLOBAL-GOAL", "ST-GLOBAL-COMMIT", "ST-GLOBAL-BLOCK",
            "ST-GLOBAL-STATUS", "ST-GLOBAL-PHASE",
        ):
            self.assertIn(identifier, view["omitted_ids"])
            self.assertNotIn(identifier, selected_ids)
        self.assertEqual(5, view["omission_counts"]["global_operative_scope"])
        self.assertIn("global_operative_scope_withheld", view["degradation"])
        self.assertNotIn("project_scope_unrepresented", view["degradation"])

    def test_ineligible_global_operative_state_keeps_original_eligibility_reason(self) -> None:
        global_scope = {**BASE_SCOPE, "project": "*"}
        protected_episode = episode("EP-GLOBAL-PROTECTED", "Continue the Atlas project", scope=global_scope)
        protected_episode["sensitivity"] = "restricted"
        protected_record = record(
            "ST-GLOBAL-PROTECTED", "goal", "Continue the Atlas project",
            ["EP-GLOBAL-PROTECTED"], scope=global_scope,
        )
        protected_record["sensitivity"] = "restricted"
        root = self.workspace(
            "ineligible-global-operative", [protected_episode], [protected_record], manifest_project="*",
        )
        view = worldline.compile_worldline(self.request(root, project="atlas"))
        self.assertEqual(2, view["omission_counts"]["sensitivity_denied"])
        self.assertNotIn("global_operative_scope", view["omission_counts"])
        self.assertNotIn("global_operative_scope_withheld", view["degradation"])
        self.assertIn("project_scope_unrepresented", view["degradation"])
        self.assertEqual("unavailable", view["resumption_pointer"]["state"])

    def test_global_only_operative_state_cannot_create_project_resumption(self) -> None:
        global_scope = {**BASE_SCOPE, "project": "*"}
        episodes = [episode("EP-GLOBAL-ONLY", "Continue the demo project", scope=global_scope)]
        records = [record(
            "ST-GLOBAL-ONLY", "goal", "Continue the demo project", ["EP-GLOBAL-ONLY"], scope=global_scope,
        )]
        root = self.workspace("global-only-operative", episodes, records, manifest_project="*")
        view = worldline.compile_worldline(self.request(root, project="atlas"))
        self.assertEqual([], view["next_actions"])
        self.assertEqual([], view["commitments"])
        self.assertEqual([], view["blockers"])
        self.assertIsNone(view["current_phase"])
        self.assertIsNone(view["current_status"])
        self.assertEqual("unavailable", view["resumption_pointer"]["state"])
        self.assertIn("global_operative_scope_withheld", view["degradation"])
        self.assertIn("project_scope_unrepresented", view["degradation"])
        self.assertEqual("degraded", view["status"])

    def test_superseded_decision_and_corrected_status(self) -> None:
        episodes = [
            episode("EP-OLD-DEC", "Choose the stale approach", event_type="decision"),
            episode("EP-NEW-DEC", "Correction: choose the current approach", event_type="correction"),
            episode("EP-OLD-STATUS", "Status was ready"),
            episode("EP-NEW-STATUS", "Status corrected to blocked", event_type="correction"),
        ]
        records = [
            record("ST-OLD-DEC", "decision", "Choose the stale approach", ["EP-OLD-DEC"], status="superseded", valid_to=AT),
            record("ST-NEW-DEC", "decision", "Choose the current approach", ["EP-NEW-DEC"], supersedes=["ST-OLD-DEC"]),
            record("ST-OLD-STATUS", "belief", "Status: ready", ["EP-OLD-STATUS"], status="superseded", valid_to=AT, tags=["status"]),
            record("ST-NEW-STATUS", "belief", "Status: blocked on review", ["EP-NEW-STATUS"], supersedes=["ST-OLD-STATUS"], tags=["status"]),
        ]
        root = self.workspace("corrected", episodes, records)
        view = worldline.compile_worldline(self.request(root, mode="status", task="Inspect corrected project status"))
        self.assertEqual("ST-NEW-STATUS", view["current_status"]["id"])
        self.assertEqual({"ST-NEW-DEC"}, {item["id"] for item in view["decisions"]})
        self.assertIn("ST-OLD-DEC", view["omitted_ids"])
        self.assertIn("ST-OLD-STATUS", view["omitted_ids"])

    def test_incomplete_tool_attempt_is_not_completion(self) -> None:
        episodes = [episode("EP-ATTEMPT", "Ran the publish command", event_type="tool_action", source_kind="tool")]
        records = [record(
            "ST-FALSE-COMPLETE", "belief", "Status: release complete", ["EP-ATTEMPT"], tags=["status"],
        )]
        root = self.workspace("false-completion", episodes, records)
        view = worldline.compile_worldline(self.request(root, mode="status", task="Check release status"))
        self.assertIsNone(view["current_status"])
        self.assertIn("completion_claim_withheld:ST-FALSE-COMPLETE", view["degradation"])
        self.assertIn("ST-FALSE-COMPLETE", view["omitted_ids"])
        self.assertTrue(any(item["id"] == "EP-ATTEMPT" for item in view["chronology"]))

    def test_conflicting_state_and_artifact_pointer_custody(self) -> None:
        episodes = [
            episode("EP-CONFLICT-A", "Deployment target A"),
            episode("EP-CONFLICT-B", "Deployment target B"),
            episode("EP-ARTIFACT", "Canonical build artifact", source_kind="file", locator="repo://dist/build.zip"),
        ]
        records = [
            record("ST-CONFLICT-A", "belief", "Target is A", ["EP-CONFLICT-A"], status="conflicted", conflicts=["ST-CONFLICT-B"]),
            record("ST-CONFLICT-B", "belief", "Target is B", ["EP-CONFLICT-B"], status="conflicted", conflicts=["ST-CONFLICT-A"]),
        ]
        root = self.workspace("conflict-artifact", episodes, records)
        view = worldline.compile_worldline(self.request(root, mode="inspect", task="Inspect deployment conflict and artifact"))
        conflict_ids = {identifier for item in view["conflicts"] for identifier in item["record_ids"]}
        self.assertTrue({"ST-CONFLICT-A", "ST-CONFLICT-B"}.issubset(conflict_ids))
        artifact = next(item for item in view["artifact_locators"] if item["source_ids"] == ["EP-ARTIFACT"])
        self.assertEqual("repo://dist/build.zip", artifact["locator"])
        self.assertEqual("source_owned", artifact["custody"])
        self.assertEqual("file", artifact["owner"])

    def test_all_four_modes_are_read_only_derived_views(self) -> None:
        episodes = [
            episode("EP-STATUS", "Current implementation status"),
            episode("EP-NEXT", "Run the held-out tests", event_type="commitment"),
        ]
        records = [
            record("ST-STATUS", "belief", "Status: implementation active", ["EP-STATUS"], tags=["status"]),
            record("ST-NEXT", "commitment", "Run the held-out tests", ["EP-NEXT"], tags=["next-action"]),
        ]
        root = self.workspace("modes", episodes, records)
        before = tree_digest(root)
        for mode in ("resume", "status", "checkpoint", "inspect"):
            view = worldline.compile_worldline(self.request(root, mode=mode))
            self.assertEqual("cd-worldline-view/v1", view["format"])
            self.assertEqual(mode, view["requested_mode"])
            self.assertFalse(view["durability"]["view_persisted"])
            self.assertFalse(view["durability"]["save_claim"])
        self.assertEqual(before, tree_digest(root))


    def test_missing_and_corrupt_store_require_sufficient_portable_material(self) -> None:
        missing = self.base / "missing"
        with self.assertRaises(ContinuityError) as missing_error:
            worldline.compile_worldline(self.request(missing))
        self.assertEqual("workspace_missing", missing_error.exception.code)

        portable_view = worldline.compile_worldline(self.request(missing, mode="checkpoint", portable=self.portable_material()))
        self.assertTrue(portable_view["durability"]["portable"])
        self.assertFalse(portable_view["durability"]["view_persisted"])
        self.assertFalse(portable_view["durability"]["save_claim"])
        self.assertEqual("caller_material_only", portable_view["durability"]["source_state"])
        self.assertEqual("missing", portable_view["workspace"]["availability"])
        self.assertIn("No durable Continuity write", portable_view["durability"]["guarantee_lost"])
        self.assertEqual("Run the next disposable probe", portable_view["resumption_pointer"]["text"])

        corrupt = self.base / "corrupt"
        corrupt.mkdir()
        (corrupt / "manifest.json").write_text("{not valid json", encoding="utf-8")
        corrupt_view = worldline.compile_worldline(self.request(corrupt, mode="resume", portable=self.portable_material()))
        self.assertEqual("invalid", corrupt_view["workspace"]["availability"])
        self.assertIn("workspace_invalid", corrupt_view["degradation"])

        insufficient = self.portable_material()
        insufficient["commitments"] = []
        insufficient["next_actions"] = []
        with self.assertRaises(ContinuityError):
            worldline.compile_worldline(self.request(missing, portable=insufficient))

    def test_no_writable_store_uses_portable_material_without_save_claim(self) -> None:
        root = self.workspace(
            "readonly",
            [episode("EP-READONLY", "Durable source remains readable")],
            [record("ST-READONLY", "commitment", "Use portable handoff if needed", ["EP-READONLY"])],
        )
        manifest = root / "manifest.json"
        original_mode = manifest.stat().st_mode
        try:
            manifest.chmod(stat.S_IREAD)
            view = worldline.compile_worldline(self.request(root, mode="checkpoint", portable=self.portable_material()))
        finally:
            manifest.chmod(original_mode | stat.S_IWRITE)
        self.assertTrue(view["durability"]["portable"])
        self.assertEqual("caller_material_only", view["durability"]["source_state"])
        self.assertFalse(view["durability"]["save_claim"])
        self.assertIn("workspace_not_writable", view["degradation"])

    def test_fresh_process_exact_resume(self) -> None:
        root = self.workspace(
            "fresh-process",
            [episode("EP-FRESH", "Resume by running the fresh process probe", event_type="commitment")],
            [record("ST-FRESH", "commitment", "Run the fresh process probe", ["EP-FRESH"], tags=["next-action"])],
        )
        request_path = self.base / "request.json"
        request_path.write_text(json.dumps(self.request(root, mode="resume"), sort_keys=True), encoding="utf-8")
        command = [sys.executable, "-B", str(WORLDLINE), "--request", str(request_path)]
        first = subprocess.run(command, text=True, capture_output=True, check=False)
        second = subprocess.run(command, text=True, capture_output=True, check=False)
        self.assertEqual(0, first.returncode, first.stderr)
        self.assertEqual(0, second.returncode, second.stderr)
        self.assertEqual(first.stdout, second.stdout)
        view = json.loads(first.stdout)
        self.assertEqual("Run the fresh process probe", view["resumption_pointer"]["text"])
        self.assertEqual(1, view["workspace"]["generation"])

    def test_v1_is_read_only_and_explicitly_degraded(self) -> None:
        root = self.base / "legacy"
        def run(*args: str) -> dict:
            result = subprocess.run(
                [sys.executable, "-B", str(LEGACY_STORE), *args],
                text=True, capture_output=True, check=False,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            return json.loads(result.stdout)
        run("init", str(root), "--user", "demo-user", "--project", "*", "--agent", "nova")
        source = run(
            "episode", str(root), "--type", "commitment", "--content", "Resume legacy work",
            "--source-kind", "user", "--authority", "user-test", "--valid-from", "2000-01-01",
        )["episode_id"]
        record_id = run(
            "record", str(root), "--kind", "commitment", "--content", "Resume legacy work",
            "--source-ids", source, "--authority", "user-test", "--valid-from", "2000-01-01",
        )["record_id"]
        manifest_path = root / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["version"] = "0.2.0"
        manifest["policies"]["scope_model"] = "harness-global"
        manifest["capabilities"]["transactional_init"] = True
        manifest_path.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        before = tree_digest(root)
        view = worldline.compile_worldline(self.request(root, mode="resume", project="*"))
        self.assertEqual("v1_read_only", view["workspace"]["compatibility_mode"])
        self.assertEqual("durable_v1_read_only", view["durability"]["source_state"])
        self.assertIn("v1_read_only_compatibility", view["degradation"])
        self.assertEqual([record_id], [item["id"] for item in view["commitments"]])
        self.assertEqual("Resume legacy work", view["resumption_pointer"]["text"])
        self.assertEqual([record_id], view["resumption_pointer"]["record_ids"])
        self.assertEqual(1, view["counts"]["eligible_episodes"])
        self.assertEqual(1, view["counts"]["eligible_records"])
        self.assertNotIn("time_malformed", view["omission_counts"])
        self.assertEqual(before, tree_digest(root))


if __name__ == "__main__":
    unittest.main()
