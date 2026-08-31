from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PLUGIN = REPO / "plugins" / "nova-the-optimal-ai"
SELECTORS = (
    "NOVA_DATA_ROOT", "NOVA_CONTINUITY_HOME", "DUNBAR_STORE", "CORKBOARD_HOME",
    "DENNIS_PROJECT_HOME", "NOVA_COMMONPLACE_HOME", "NOVA_CONCORDANCE_HOME",
)
MANAGED = SELECTORS + ("MIND_CORE_DATABASE", "MIND_HOOK_RECEIPT_DIRECTORY")

SERVICE = """from __future__ import annotations
import json
import os
import sys
from pathlib import Path
kind = Path(__file__).name
args = sys.argv[1:]
if kind == "continuity_store_v2.py" and args and args[0] == "init":
    if os.environ.get("FAKE_INIT_FAIL") == "1":
        print("deliberate init failure", file=sys.stderr)
        raise SystemExit(9)
    target = Path(args[1])
    target.mkdir(parents=True, exist_ok=False)
    (target / "manifest.json").write_text("{}\\n", encoding="utf-8")
    print(json.dumps({"format": "fake-continuity-init/v1", "target": str(target)}))
    raise SystemExit(0)
print(json.dumps({
    "script": kind,
    "argv": args,
    "selectors": {key: os.environ.get(key) for key in %r},
    "dennis_present": "DENNIS_PROJECT_HOME" in os.environ,
    "mind_core_present": "MIND_CORE_DATABASE" in os.environ,
    "mind_hook_present": "MIND_HOOK_RECEIPT_DIRECTORY" in os.environ,
}))
""" % (SELECTORS,)

VALIDATOR = """import json
print(json.dumps({"format": "fake-validation/v1", "valid": True}))
"""

RUNTIME = """import os
def mutation_filesystem_support(root, *, lexical_root=None):
    if os.environ.get("FAKE_MUTATION_UNSUPPORTED") == "1":
        return {"status": "unsupported", "reason_code": "filesystem_semantics_unsupported"}
    return {"status": "qualified", "adapter": "fake-qualified/v1"}
"""


class NovaOperationsFreeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="nova-operations-free-")
        self.base = Path(self.temp.name)
        self.skills = self.base / "package" / "skills"
        ops = self.skills / "nova-operations" / "scripts"
        ops.mkdir(parents=True)
        source = PLUGIN / "skills" / "nova-operations" / "scripts"
        shutil.copy2(source / "nova_estate.py", ops / "nova_estate.py")
        shutil.copy2(source / "probe_continuity_mutation.py", ops / "probe_continuity_mutation.py")
        self.cli = ops / "nova_estate.py"
        shutil.copytree(PLUGIN / "skills" / "commonplace", self.skills / "commonplace")
        scripts = {
            self.skills / "cognitive-continuity" / "scripts" / "continuity_store_v2.py": SERVICE,
            self.skills / "cognitive-continuity" / "scripts" / "worldline.py": SERVICE,
            self.skills / "cognitive-continuity" / "scripts" / "validate_continuity_v2.py": VALIDATOR,
            self.skills / "cognitive-continuity" / "scripts" / "workspace_runtime.py": RUNTIME,
            self.skills / "dunbar" / "scripts" / "dunbar.py": SERVICE,
            self.skills / "corkboard" / "scripts" / "corkboard.py": SERVICE,
            self.skills / "dennis-stratton-project-management" / "scripts" / "project_control.py": SERVICE,
        }
        for path, content in scripts.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def environment(self, **updates: str) -> dict[str, str]:
        env = os.environ.copy()
        env.update({
            "PYTHONDONTWRITEBYTECODE": "1",
            "LOCALAPPDATA": str(self.base / "platform"),
            "HOME": str(self.base / "home"),
            "XDG_DATA_HOME": str(self.base / "xdg-data"),
            "XDG_CONFIG_HOME": str(self.base / "xdg-config"),
        })
        for key in MANAGED:
            env.pop(key, None)
        env.update(updates)
        return env

    def run_cli(self, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-B", "-X", "utf8", str(self.cli), *args],
            env=env or self.environment(),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )

    @staticmethod
    def layout(root: Path) -> dict[str, str]:
        return {
            "NOVA_DATA_ROOT": str(root.resolve()),
            "NOVA_CONTINUITY_HOME": str((root / "memory" / "continuity-v2").resolve()),
            "DUNBAR_STORE": str((root / "memory" / "dunbar" / "people.sqlite3").resolve()),
            "CORKBOARD_HOME": str((root / "memory" / "corkboard").resolve()),
            "DENNIS_PROJECT_HOME": str((root / "projects" / "project-records").resolve()),
            "NOVA_COMMONPLACE_HOME": str((root / "memory" / "commonplace").resolve()),
            "NOVA_CONCORDANCE_HOME": str((root / "derived" / "concordance").resolve()),
        }

    def configure(self, root: Path, *, extra_dennis: bool = False) -> dict[str, str]:
        values = self.layout(root)
        Path(values["NOVA_CONTINUITY_HOME"]).mkdir(parents=True)
        Path(values["DUNBAR_STORE"]).parent.mkdir(parents=True)
        Path(values["CORKBOARD_HOME"]).mkdir(parents=True)
        Path(values["DENNIS_PROJECT_HOME"]).mkdir(parents=True)
        Path(values["NOVA_COMMONPLACE_HOME"]).mkdir(parents=True)
        Path(values["NOVA_CONCORDANCE_HOME"]).mkdir(parents=True)
        active = dict(values)
        estate = root / "estate"
        estate.mkdir(parents=True)
        (estate / "path-selectors.json").write_text(json.dumps({
            "format": "nova-path-selectors/v1",
            "active_values": {**active, "MIND_CORE_DATABASE": None, "MIND_HOOK_RECEIPT_DIRECTORY": None},
        }) + "\n", encoding="utf-8")
        (estate / "manifest.json").write_text(json.dumps({
            "format": "nova-estate-manifest/v1",
            "product": "Older Nova Edition",
            "product_version": "1.0.3",
            "services": {
                "continuity": "memory/continuity-v2",
                "dunbar": "memory/dunbar/people.sqlite3",
                "corkboard": "memory/corkboard",
                "project_management": "projects/project-records",
                "commonplace": "memory/commonplace",
                "concordance": "derived/concordance",
            },
        }) + "\n", encoding="utf-8")
        return values

    def test_init_has_all_current_foundation_selectors(self) -> None:
        root = self.base / "estate"
        result = self.run_cli("init", "--root", str(root), "--user", "tester")
        self.assertEqual(result.returncode, 0, result.stderr)
        registry = json.loads((root / "estate" / "path-selectors.json").read_text(encoding="utf-8"))
        self.assertEqual({key for key, value in registry["active_values"].items() if value is not None}, set(SELECTORS))
        self.assertTrue((root / "projects" / "project-records").is_dir())
        self.assertTrue((root / "memory" / "commonplace" / "CURRENT.json").is_file())
        self.assertTrue((root / "derived" / "concordance").is_dir())
        manifest = json.loads((root / "estate" / "manifest.json").read_text(encoding="utf-8"))
        self.assertIn("project_management", manifest["services"])
        self.assertIn("commonplace", manifest["services"])
        self.assertIn("concordance", manifest["services"])
        self.assertEqual(manifest["product"], "Nova the Optimal AI Free")

    def test_launcher_injects_core_registry_and_strips_extra_selectors(self) -> None:
        root = self.base / "estate"
        values = self.configure(root, extra_dennis=True)
        stale = {key: str(self.base / "wrong" / key) for key in MANAGED}
        for service in ("continuity", "dunbar", "corkboard"):
            result = self.run_cli("run", "--root", str(root), service, "--", "alpha", env=self.environment(**stale))
            self.assertEqual(result.returncode, 0, result.stderr)
            observed = json.loads(result.stdout)
            self.assertEqual(observed["selectors"], values)
            self.assertTrue(observed["dennis_present"])
            self.assertFalse(observed["mind_core_present"])
            self.assertFalse(observed["mind_hook_present"])

    def test_upgrade_preserves_current_foundation_selectors(self) -> None:
        root = self.base / "estate"
        self.configure(root, extra_dennis=True)
        registry_path = root / "estate" / "path-selectors.json"
        before = json.loads(registry_path.read_text(encoding="utf-8"))["active_values"]["DENNIS_PROJECT_HOME"]
        result = self.run_cli("upgrade", "--root", str(root))
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads(result.stdout)
        self.assertIn(receipt["state"], ("upgraded", "already_current"))
        self.assertEqual(receipt["added_selectors"], [])
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        self.assertEqual(registry["active_values"]["DENNIS_PROJECT_HOME"], before)
        self.assertEqual(set(receipt["selectors"]), set(SELECTORS))

    def test_failed_init_leaves_no_estate_or_stage(self) -> None:
        root = self.base / "parent" / "estate"
        result = self.run_cli("init", "--root", str(root), env=self.environment(FAKE_INIT_FAIL="1"))
        self.assertEqual(result.returncode, 2)
        self.assertFalse(root.exists())
        self.assertFalse((self.base / "parent").exists())

    def test_doctor_separates_read_and_mutation_support(self) -> None:
        root = self.base / "estate"
        self.configure(root)
        result = self.run_cli("doctor", "--root", str(root), env=self.environment(FAKE_MUTATION_UNSUPPORTED="1"))
        self.assertEqual(result.returncode, 2, result.stderr)
        doctor = json.loads(result.stdout)
        self.assertEqual(doctor["operating_mode"], "read_only")
        self.assertTrue(doctor["continuity_read_support"]["supported"])
        self.assertFalse(doctor["continuity_mutation_support"]["supported"])

    def test_status_accepts_current_foundation_registry(self) -> None:
        root = self.base / "estate"
        self.configure(root)
        result = self.run_cli("status", "--root", str(root))
        self.assertEqual(result.returncode, 0, result.stderr)
        status = json.loads(result.stdout)
        self.assertTrue(status["configured"])
        self.assertNotEqual(status["state"], "upgrade_required")


class StatefulFallbackTests(unittest.TestCase):
    def clean_environment(self, root: Path | None = None) -> dict[str, str]:
        env = os.environ.copy()
        for key in MANAGED + ("CODEX_HOME",):
            env.pop(key, None)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        if root is not None:
            env["NOVA_DATA_ROOT"] = str(root)
        return env

    def test_absent_estate_fails_cleanly_without_traceback(self) -> None:
        cork = PLUGIN / "skills" / "corkboard" / "scripts" / "corkboard.py"
        dunbar = PLUGIN / "skills" / "dunbar" / "scripts" / "dunbar.py"
        for command in (
            [sys.executable, "-B", "-X", "utf8", str(cork), "list", "--json"],
            [sys.executable, "-B", "-X", "utf8", str(dunbar), "check"],
        ):
            result = subprocess.run(command, env=self.clean_environment(), capture_output=True, text=True, encoding="utf-8", check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn("Traceback", result.stderr)
            self.assertIn("Nova Operations", result.stderr)

    def test_nova_root_fallback_stays_outside_codex_and_does_not_initialize_on_path(self) -> None:
        with tempfile.TemporaryDirectory(prefix="nova-state-root-") as directory:
            root = Path(directory)
            dunbar = PLUGIN / "skills" / "dunbar" / "scripts" / "dunbar.py"
            result = subprocess.run(
                [sys.executable, "-B", "-X", "utf8", str(dunbar), "path"],
                env=self.clean_environment(root), capture_output=True, text=True, encoding="utf-8", check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(Path(payload["store"]), (root / "memory" / "dunbar" / "people.sqlite3").resolve())
            self.assertFalse((root / "memory" / "dunbar" / "people.sqlite3").exists())


if __name__ == "__main__":
    unittest.main()
