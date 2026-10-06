"""Regression checks for native schema validation and launch identity."""
import copy, hashlib, json, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path
import host

ROOT = Path(__file__).resolve().parent
SAMPLE = json.loads((ROOT/"sample.json").read_text(encoding="utf-8"))
SCHEMA = json.loads((ROOT.parent/"schemas/it-case.schema.json").read_text(encoding="utf-8"))

class CaseSemantics(unittest.TestCase):
    def test_sample_and_unknown_fields_are_valid_and_unchanged(self):
        sample = copy.deepcopy(SAMPLE)
        sample["owner_extension"] = {"unicode": "café", "nested": [None, False, 0, {"keep": True}]}
        before = copy.deepcopy(sample)
        self.assertEqual(host.validate_record(sample), [])
        self.assertEqual(sample, before)

    def test_all_required_top_level_fields_are_enforced(self):
        for key in SCHEMA["required"]:
            with self.subTest(key=key):
                sample = copy.deepcopy(SAMPLE)
                del sample[key]
                self.assertTrue(host.validate_record(sample))

    def test_all_required_nested_fields_are_enforced(self):
        for key, spec in SCHEMA["properties"].items():
            for field in spec.get("required", []):
                with self.subTest(key=key, field=field):
                    sample = copy.deepcopy(SAMPLE)
                    del sample[key][field]
                    self.assertTrue(host.validate_record(sample))

    def test_empty_identity_and_updated_time_are_rejected(self):
        for key in ("case_id", "updated_at"):
            for value in ("", "  ", None, 42, []):
                with self.subTest(key=key, value=value):
                    sample = copy.deepcopy(SAMPLE)
                    sample[key] = value
                    self.assertTrue(host.validate_record(sample))

    def test_objects_arrays_and_collection_members_are_checked(self):
        for key in ("device", "complaint", "custody", "verification", "next_move"):
            sample = copy.deepcopy(SAMPLE)
            sample[key] = []
            self.assertTrue(host.validate_record(sample), key)
        for key in ("evidence", "hypotheses", "tests", "changes", "sources"):
            for value in ({}, [None], [17], ["text"], [[]]):
                sample = copy.deepcopy(SAMPLE)
                sample[key] = value
                self.assertTrue(host.validate_record(sample), key)

    def test_invalid_controlled_states_fail_without_a_traceback(self):
        for value in ("invented", [], {}, None):
            sample = copy.deepcopy(SAMPLE)
            sample["status"] = value
            errors = host.validate_record(sample)
            self.assertTrue(errors)
            self.assertNotIn("Traceback", "\n".join(errors))
        sample = copy.deepcopy(SAMPLE)
        sample["verification"]["disposition"] = "guessed-fixed"
        self.assertTrue(host.validate_record(sample))
        sample = copy.deepcopy(SAMPLE)
        sample["verification"]["original_envelope_retested"] = "false"
        self.assertTrue(host.validate_record(sample))

    def test_empty_next_action_is_rejected(self):
        sample = copy.deepcopy(SAMPLE)
        sample["next_move"]["action"] = ""
        self.assertTrue(host.validate_record(sample))

    def test_runtime_identity_changes_with_interface_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)/"skill"
            shutil.copytree(ROOT.parent, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            workspace = target/"workspace"
            command = [sys.executable, "-B", "-c", "import host; print(host.RUNTIME_SHA)"]
            before = subprocess.check_output(command, cwd=workspace, text=True).strip()
            page = workspace/"index.html"
            page.write_bytes(page.read_bytes()+b"\n<!-- identity fixture -->\n")
            after = subprocess.check_output(command, cwd=workspace, text=True).strip()
            self.assertNotEqual(before, after)
            self.assertEqual(before, host.RUNTIME_SHA)

if __name__ == "__main__":
    unittest.main()
