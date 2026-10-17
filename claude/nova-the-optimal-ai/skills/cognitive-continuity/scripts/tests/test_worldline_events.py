from __future__ import annotations
import argparse
import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import continuity_store_v2 as store
import workspace_runtime as runtime
import worldline_domain as domain
from schema_validation import SchemaCatalog

def inventory(root):
    return runtime.tree_digest(root)

class WorldlineMutationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir="E:/" if os.name == "nt" and Path("E:/").exists() else None)
        self.base = Path(self.tmp.name).resolve()
        self.root = self.base / "workspace"
        runtime.initialize_workspace(str(self.root), user="user", project="*", agent="nova", thread=None,
                                     sensitivity="ordinary", retention="until-user-forgets")
        self.scope = {"user": "user", "agent": "nova", "project": None, "thread": None}
        self.choice = {"selection_mode": "generic_explicit", "path": str(self.root), "grant_id": None}

    def tearDown(self):
        self.tmp.cleanup()

    def generation(self):
        return runtime.read_json(self.root / "manifest.json")["generation"]

    def rows(self):
        return runtime.read_jsonl(self.root / "episodes" / "events.jsonl")

    def event(self, title="Explored the shape of memory"):
        return {"format": "cd-worldline-event/v2", "title": title, "kind": "exploration",
                "disposition": "recorded", "occurred_at": (datetime.now(timezone.utc)-timedelta(hours=1)).isoformat(),
                "ended_at": None, "time_basis": "observed", "time_precision": "instant",
                "sources": [{"kind": "artifact", "locator": r"E:\Notes\worldline-0123456789abcdef0123456789.md",
                             "label": "Source conversation", "owner": "user"}],
                "topics": ["memory"], "related_ids": [], "supersedes": []}

    def request(self, key="event-1", **changes):
        result = {"format": "cd-worldline-capture/v2", "scope": dict(self.scope), "workspace": self.choice,
                  "event": self.event(), "source_kind": "agent", "authority": "user-explicit",
                  "sensitivity": "ordinary", "retention": "until-user-forgets", "expires_at": None,
                  "expected_generation": self.generation(), "idempotency_key": key,
                  "capture_mode": "explicit", "retention_guard": False}
        result.update(changes)
        return result

    def policy(self, mode="ordinary", key=None):
        request = {"format": "cd-worldline-policy-request/v1", "scope": dict(self.scope), "workspace": self.choice,
                   "authority": "user-explicit", "expected_generation": self.generation(),
                   "idempotency_key": key or "policy-"+mode,
                   "policy": {"format": "cd-worldline-policy/v1", "mode": mode, "authority_source": "task:owner-directive"}}
        return store.set_worldline_policy(request)

    def capture(self, key="event-1", **changes):
        request = self.request(key, **changes)
        return store.capture_worldline(request)

    def test_native_persistence_replay_and_payload_conflict(self):
        request = self.request()
        receipt = store.capture_worldline(request)
        before = inventory(self.root)
        replay = store.capture_worldline(request)
        self.assertEqual(receipt["id"], replay["id"])
        self.assertEqual("duplicate_committed", replay["status"])
        self.assertEqual(before, inventory(self.root))
        rows = self.rows()
        self.assertEqual(1, len(rows))
        self.assertEqual("*", rows[0]["scope"]["project"])
        self.assertEqual(request["event"]["sources"][0]["locator"], rows[0]["source"]["locator"])
        changed = copy.deepcopy(request)
        changed["event"]["title"] = "A different occurrence"
        with self.assertRaises(runtime.ContinuityError):
            store.capture_worldline(changed)
        self.assertEqual(before, inventory(self.root))
        output = subprocess.check_output([sys.executable, "-B", "-c",
            "import sys,json;sys.path.insert(0,sys.argv[1]);import workspace_runtime as r;from pathlib import Path;print(json.dumps(r.read_jsonl(Path(sys.argv[2])/'episodes'/'events.jsonl')))",
            str(SCRIPTS), str(self.root)], text=True)
        self.assertEqual(receipt["episode_id"], json.loads(output)[0]["id"])

    def test_unconfigured_off_no_retention_and_nonordinary_are_noops(self):
        before = inventory(self.root)
        with self.assertRaisesRegex(runtime.ContinuityError, "capture_suppressed"):
            self.capture(capture_mode="routine")
        self.assertEqual(before, inventory(self.root))
        self.policy()
        self.policy("off")
        for changes in ({"capture_mode":"routine"}, {"retention_guard":True},
                        {"capture_mode":"routine","sensitivity":"sensitive"}):
            before = inventory(self.root)
            with self.assertRaisesRegex(runtime.ContinuityError, "capture_suppressed"):
                self.capture(**changes)
            self.assertEqual(before, inventory(self.root))
        # An explicit user capture still works while routine policy is off.
        self.capture("explicit-off")

    def test_policy_precedence_uses_committed_order_with_clock_regression(self):
        with mock.patch.object(store, "utc_now", return_value="2026-08-20T10:00:00Z"):
            self.policy()
        with mock.patch.object(store, "utc_now", return_value="2026-08-19T10:00:00Z"):
            self.policy("off")
        value = domain.effective_policy(self.rows(), {"user":"user","agent":"nova","project":"*","thread":None},
                                        datetime.now(timezone.utc))
        self.assertEqual("off", value["mode"])
        self.assertEqual(self.rows()[-1]["id"], value["id"])
        with self.assertRaisesRegex(runtime.ContinuityError, "capture_suppressed"):
            self.capture(capture_mode="routine")

    def test_forgetting_policy_history_cannot_restore_an_old_grant(self):
        self.policy()
        self.policy("off")
        rows = self.rows()
        selected = {rows[-1]["id"]}
        plan = store.build_forget_plan(self.root, list(selected))
        self.assertTrue({row["id"] for row in rows} <= set(plan["removed_ids"]))
        surviving = [store._tombstone(row, runtime.utc_now()) for row in rows]
        domain.validate_episode_graph(surviving)
        result = domain.effective_policy(surviving,
            {"user":"user","agent":"nova","project":"*","thread":None}, datetime.now(timezone.utc))
        self.assertEqual("unconfigured", result["mode"])
        self.assertFalse(any("worldline_policy" in row for row in surviving))

    def test_routine_policy_rechecked_inside_lock(self):
        self.policy()
        request = self.request(capture_mode="routine")
        before = inventory(self.root)
        original = domain.effective_policy
        observed = []
        def changing(rows, scope, now):
            observed.append(len(observed))
            if len(observed) == 1:
                return original(rows, scope, now)
            return {"mode":"off","id":"policy-off","authority":"user-explicit"}
        with mock.patch.object(domain, "effective_policy", side_effect=changing):
            with self.assertRaisesRegex(runtime.ContinuityError, "capture_suppressed"):
                store.capture_worldline(request)
        self.assertEqual(2, len(observed))
        self.assertEqual(before, inventory(self.root))

    def test_correction_inherits_privacy_rejects_branch_and_retraction_is_explicit(self):
        root = self.capture(sensitivity="sensitive")["episode_id"]
        event = self.event("Corrected source label")
        event["supersedes"] = [root]
        corrected = self.capture("correction", event=event)["episode_id"]
        self.assertEqual("sensitive", self.rows()[-1]["sensitivity"])
        with self.assertRaisesRegex(runtime.ContinuityError, "correction_conflict"):
            self.capture("branch", event=event)
        retracted = self.event("Occurrence was misidentified")
        retracted["supersedes"] = [corrected]
        retracted["disposition"] = "retracted"
        self.capture("retract", event=retracted)
        self.assertEqual("retracted", self.rows()[-1]["worldline_event"]["disposition"])
        ordinary = self.event("Lower the classification with explicit authority")
        ordinary["supersedes"] = [self.rows()[-1]["id"]]
        self.capture("reclassify", event=ordinary, privacy_change_authorized=True)
        self.assertEqual("ordinary", self.rows()[-1]["sensitivity"])

    def test_bad_scope_secret_future_and_pointer_are_prewrite_noops(self):
        cases = []
        request = self.request()
        request["scope"]["user"] = "other"
        # A wildcard workspace allows multiple owners, but the event cannot reference their evidence.
        self.capture("root")
        event = self.event()
        event["related_ids"] = [self.rows()[0]["id"]]
        request["event"] = event
        cases.append(request)
        event = self.event()
        event["sources"][0]["locator"] = "https://example.test/?access_token=private-value"
        cases.append(self.request("secret", event=event))
        event = self.event()
        event["sources"][0]["locator"] = "javascript:alert(1)"
        cases.append(self.request("unsafe", event=event))
        event = self.event()
        event["occurred_at"] = (datetime.now(timezone.utc)+timedelta(days=1)).isoformat()
        cases.append(self.request("future", event=event))
        for request in cases:
            before = inventory(self.root)
            with self.assertRaises(runtime.ContinuityError):
                store.capture_worldline(request)
            self.assertEqual(before, inventory(self.root))

    def test_forget_expands_family_and_severs_only_associations(self):
        left = self.capture("left")["episode_id"]
        middle_event = self.event("Middle episode")
        middle_event["related_ids"] = [left]
        middle = self.capture("middle", event=middle_event)["episode_id"]
        revision = self.event("Middle corrected")
        revision["supersedes"] = [middle]
        middle_revision = self.capture("middle-revision", event=revision)["episode_id"]
        right_event = self.event("Right independent episode")
        right_event["related_ids"] = [middle]
        right = self.capture("right", event=right_event)["episode_id"]
        from worldline_timeline import render_worldline
        projection = self.root / "projections" / "worldline.html"
        render_worldline({"workspace":self.choice,"scope":self.scope,"deadline_ms":30000},projection)
        projection_bytes = projection.read_bytes()
        plan = store.build_forget_plan(self.root, [middle_revision])
        removed = set(plan["removed_ids"])
        self.assertTrue({middle,middle_revision} <= removed)
        self.assertNotIn(left, removed)
        self.assertNotIn(right, removed)
        self.assertEqual(1, plan["counts"]["associative_edges_severed"])
        self.assertEqual(1, plan["counts"]["worldline_projection_files"])
        survivors = [domain.sever_associations(row, removed) for row in self.rows() if row["id"] not in removed]
        self.assertEqual([], next(row for row in survivors if row["id"] == right)["worldline_event"]["related_ids"])
        self.assertEqual(2, len(survivors))
        domain.validate_episode_graph(survivors)
        old = next(row for row in self.rows() if row["id"] == middle)
        tombstone = store._tombstone(old, runtime.utc_now())
        self.assertNotIn("worldline_event", tombstone)
        self.assertIsNone(tombstone["source"]["locator"])
        self.assertEqual(["forgotten"], tombstone["tags"])
        self.assertNotIn("Middle", json.dumps(tombstone))
        self.assertEqual([], SchemaCatalog(SCRIPTS.parent/"assets"/"schemas").validate(tombstone,"episode-v2.schema.json"))
        # Exercise the public governed plan/apply route, not just graph helpers.
        plan_path = self.base / "forget-plan.json"
        expiry = (datetime.now(timezone.utc)+timedelta(days=2)).isoformat()
        plan_args = store.parser().parse_args(["forget-plan",str(self.root),"--ids",middle_revision,
            "--authority","user-explicit","--mode","tombstone","--plan-output",str(plan_path),
            "--retention-until",expiry,"--destruction-owner","user-explicit","--access-owner","user-explicit",
            "--encryption-disposition","not-required"])
        store.cmd_forget_plan(plan_args)
        reviewed = json.loads(plan_path.read_text())
        key = self.base / "backup.key"
        key.write_bytes(b"K"*48)
        apply_args = store.parser().parse_args(["forget",str(self.root),"--plan",str(plan_path),
            "--plan-digest",reviewed["plan_digest"],"--backup-output",str(self.base/"backup"),
            "--backup-auth-key-file",str(key),"--retention-until",expiry,
            "--destruction-owner","user-explicit","--access-owner","user-explicit",
            "--encryption-disposition","not-required","--authority","user-explicit",
            "--idempotency-key","forget-family","--expected-generation",str(self.generation())])
        result = store.cmd_forget(apply_args)
        self.assertEqual("forgotten",result["kind"])
        self.assertFalse(projection.exists())
        self.assertEqual(projection_bytes,(self.base/"backup"/"snapshot"/"projections"/"worldline.html").read_bytes())
        self.assertTrue(result["lifecycle_outcomes"]["deleted_from_named_continuity_custody"])
        self.assertEqual(1,len(result["worldline_projection_deletion_receipts"]))
        self.assertEqual("application_deleted",json.loads(Path(result["worldline_projection_deletion_receipts"][0]).read_text())["status"])
        active = self.rows()
        self.assertEqual([],next(row for row in active if row["id"]==right)["worldline_event"]["related_ids"])
        for row in active:
            if row["id"] in {middle,middle_revision}:
                self.assertNotIn("worldline_event",row)
                self.assertIsNone(row["source"]["locator"])
        domain.validate_episode_graph(active)


    def projection_forget_args(self, identifier, key="projection"):
        expiry = (datetime.now(timezone.utc)+timedelta(days=2)).isoformat()
        plan_path = self.base / (key+"-plan.json")
        store.cmd_forget_plan(store.parser().parse_args(["forget-plan",str(self.root),"--ids",identifier,
            "--authority","user-explicit","--mode","tombstone","--plan-output",str(plan_path),
            "--retention-until",expiry,"--destruction-owner","user-explicit","--access-owner","user-explicit",
            "--encryption-disposition","not-required"]))
        plan = json.loads(plan_path.read_text())
        auth = self.base / (key+".key")
        auth.write_bytes(b"K"*48)
        args = store.parser().parse_args(["forget",str(self.root),"--plan",str(plan_path),
            "--plan-digest",plan["plan_digest"],"--backup-output",str(self.base/(key+"-backup")),
            "--backup-auth-key-file",str(auth),"--retention-until",expiry,
            "--destruction-owner","user-explicit","--access-owner","user-explicit",
            "--encryption-disposition","not-required","--authority","user-explicit",
            "--idempotency-key",key+"-forget","--expected-generation",str(self.generation())])
        return plan,args

    def test_changed_generated_view_is_stale_and_edited_template_is_unsupported(self):
        from worldline_timeline import render_worldline
        identifier = self.capture()["episode_id"]
        projection = self.root/"projections"/"worldline.html"
        render_worldline({"workspace":self.choice,"scope":self.scope,"deadline_ms":30000},projection)
        plan,args = self.projection_forget_args(identifier)
        self.assertTrue(plan["apply_supported"])
        projection.write_bytes(projection.read_bytes()+b"<!-- edited -->")
        before = inventory(self.root)
        with self.assertRaisesRegex(runtime.ContinuityError,"stale|changed"):
            store.cmd_forget(args)
        self.assertEqual(before,inventory(self.root))
        self.assertFalse((self.base/"projection-backup").exists())
        changed,_ = self.projection_forget_args(identifier,"changed")
        self.assertFalse(changed["apply_supported"])
        self.assertIn("delete_named_derivatives_with_governed_adapter",changed["blocking_reasons"])

    def test_interrupted_projection_cleanup_never_claims_forget_commit(self):
        from worldline_timeline import render_worldline
        identifier = self.capture()["episode_id"]
        projection = self.root/"projections"/"worldline.html"
        render_worldline({"workspace":self.choice,"scope":self.scope,"deadline_ms":30000},projection)
        plan,args = self.projection_forget_args(identifier)
        generation = self.generation()
        with mock.patch.dict(os.environ,{"CONTINUITY_LIFECYCLE_FAIL_POINT":"after_quarantine"}):
            with self.assertRaisesRegex(runtime.ContinuityError,"recovery_required"):
                store.cmd_forget(args)
        self.assertEqual(generation,self.generation())
        self.assertTrue(any(row.get("worldline_event") for row in self.rows()))
        self.assertFalse(projection.exists())
        self.assertEqual(1,len(list(projection.parent.glob(".worldline.html.cd-lifecycle-*"))))
        self.assertTrue((self.base/"projection-backup"/"snapshot"/"projections"/"worldline.html").exists())
        self.assertTrue(list(self.base.glob("*.quarantined.json")))
        self.assertFalse(list(self.base.glob("projection-backup.*.projection-receipt.json")))

    def export_args(self, output, timeline=False, sensitivity="limited"):
        return argparse.Namespace(workspace=str(self.root), output=str(output), authority="user-explicit",
            user=None, agent=None, project=None, thread=None, from_time=None, to_time=None,
            sensitivity=sensitivity, environment=None, environment_version=None, unreachable_source_ids=None,
            exclude_episodes=False, exclude_state=False, exclude_proposals=False, worldline_timeline=timeline)

    def test_native_and_timeline_exports_preserve_links_and_quarantine_only(self):
        self.policy()
        event = self.event()
        self.capture(event=event)
        for timeline in (False, True):
            path = self.base / ("timeline.json" if timeline else "native.json")
            before = inventory(self.root)
            store.cmd_export(self.export_args(path,timeline))
            self.assertEqual(before, inventory(self.root))
            bundle = json.loads(path.read_text())
            native = [row for row in bundle["episodes"] if row.get("worldline_event")][0]
            self.assertEqual(event["sources"][0]["locator"], native["source"]["locator"])
            self.assertEqual(event, native["worldline_event"])
            if timeline:
                self.assertFalse(any("worldline_policy" in row for row in bundle["episodes"]))
            quarantine = self.base / ("quarantine-"+path.name)
            rows_before = self.rows()
            result = store.cmd_import(argparse.Namespace(workspace=str(self.root), input=str(path),
                quarantine_output=str(quarantine), authority="user-explicit", idempotency_key="import-"+path.name,
                expected_generation=self.generation()))
            self.assertFalse(result["canonical_state_changed"])
            self.assertEqual(rows_before, self.rows())
            self.assertEqual(path.read_bytes(),quarantine.read_bytes())

    def test_sensitive_correction_cannot_export_old_ordinary_revision(self):
        original = self.capture()["episode_id"]
        event = self.event("Sensitive corrected recognition")
        event["supersedes"] = [original]
        self.capture("sensitive-correction",event=event,sensitivity="sensitive",privacy_change_authorized=True)
        for timeline in (False,True):
            path = self.base / ("filtered-"+str(timeline)+".json")
            store.cmd_export(self.export_args(path,timeline,sensitivity="ordinary"))
            text = path.read_text()
            self.assertNotIn("Explored the shape",text)
            self.assertNotIn("Sensitive corrected",text)
            self.assertEqual([],json.loads(text)["episodes"])

    def test_declassified_view_does_not_export_a_denied_required_ancestor(self):
        from worldline_timeline import select_worldline_rows
        original = self.capture(sensitivity="sensitive")["episode_id"]
        event = self.event("Public corrected recognition")
        event["supersedes"] = [original]
        self.capture("declassification",event=event,sensitivity="ordinary",privacy_change_authorized=True)
        manifest = runtime.read_json(self.root/"manifest.json")
        entries, _, _ = select_worldline_rows(manifest,self.rows(),
            {"scope":self.scope,"sensitivity_ceiling":"ordinary"},datetime.now(timezone.utc))
        self.assertEqual(["Public corrected recognition"],[item["title"] for item in entries])
        for timeline in (False,True):
            path = self.base / ("declassified-"+str(timeline)+".json")
            store.cmd_export(self.export_args(path,timeline,sensitivity="ordinary"))
            bundle = json.loads(path.read_text())
            self.assertEqual([],bundle["episodes"])
            omissions = (bundle["worldline_selection"]["coverage"]["omissions"] if timeline
                         else bundle["selection"]["omission_counts"])
            self.assertEqual(1,omissions["revision_ancestry_privacy"])

    def test_new_metadata_fails_old_episode_schema_without_mutation(self):
        self.capture()
        old_schema = json.loads((Path(__file__).parent/"fixtures"/"episode-pre-0.3.0.schema.json").read_text())
        schema_dir = self.base / "old-schemas"
        schema_dir.mkdir()
        for source in (SCRIPTS.parent/"assets"/"schemas").glob("*.json"):
            (schema_dir/source.name).write_bytes(source.read_bytes())
        (schema_dir/"episode-v2.schema.json").write_text(json.dumps(old_schema))
        before = inventory(self.root)
        errors = SchemaCatalog(schema_dir).validate(self.rows()[0],"episode-v2.schema.json")
        self.assertTrue(errors)
        self.assertEqual(before,inventory(self.root))

    def test_workspace_validator_accepts_native_and_control_graph(self):
        self.policy()
        self.capture()
        result = subprocess.run([sys.executable,"-B",str(SCRIPTS/"validate_continuity_v2.py"),str(self.root)],
                                text=True,capture_output=True)
        self.assertEqual(0,result.returncode,result.stdout+result.stderr)

if __name__ == "__main__":
    unittest.main()

