from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

from init_loomfile import initialize  # noqa: E402
from inspect_infographic_html import inspect  # noqa: E402
from package_loomfile import package  # noqa: E402
from validate_loomfile import validate  # noqa: E402


SKILL_ROOT = SCRIPTS.parent


VALID_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta property="og:title" content="Example"><meta name="twitter:card" content="summary_large_image"><title>Example</title><style>@media (prefers-reduced-motion: reduce){*{animation:none!important}}</style></head><body><header><h1>Example</h1></header><main><section><h2>Meaning</h2><p>Text.</p></section></main><footer><p>Sources.</p></footer></body></html>"""


class SignalLoomTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def new_loom(self) -> Path:
        return initialize(self.base / "loom", "Test project")

    def test_initialize_creates_required_state(self) -> None:
        loom = self.new_loom()
        self.assertTrue((loom / "project.yaml").is_file())
        self.assertTrue((loom / "sources" / "originals").is_dir())
        self.assertEqual(json.loads((loom / "project.yaml").read_text())["project_id"], "test-project")

    def test_initialize_rejects_nonempty_destination(self) -> None:
        target = self.base / "loom"
        target.mkdir()
        (target / "keep.txt").write_text("keep")
        with self.assertRaises(ValueError):
            initialize(target, "No overwrite")
        self.assertEqual((target / "keep.txt").read_text(), "keep")

    def test_empty_template_validates(self) -> None:
        errors, _ = validate(self.new_loom())
        self.assertEqual(errors, [])

    def test_publication_status_cannot_claim_published(self) -> None:
        loom = self.new_loom()
        path = loom / "project.yaml"
        data = json.loads(path.read_text())
        data["publication_status"] = "published"
        path.write_text(json.dumps(data))
        errors, _ = validate(loom)
        self.assertTrue(any("manual_only" in error for error in errors))

    def test_export_requires_human_approval(self) -> None:
        loom = self.new_loom()
        path = loom / "project.yaml"
        data = json.loads(path.read_text())
        data["stage"] = "approved_for_export"
        path.write_text(json.dumps(data))
        errors, _ = validate(loom)
        self.assertTrue(any("requires human" in error for error in errors))

    def test_sourced_claim_requires_manifest_source_and_locator(self) -> None:
        loom = self.new_loom()
        (loom / "state" / "claims.jsonl").write_text(json.dumps({"id":"C-001","status":"sourced","currentness":"timeless","source_id":"S-404","locator":""}) + "\n")
        errors, _ = validate(loom)
        self.assertTrue(any("valid source_id" in error for error in errors))
        self.assertTrue(any("lacks a locator" in error for error in errors))

    def test_manifest_hash_mismatch_is_rejected(self) -> None:
        loom = self.new_loom()
        source = loom / "sources" / "originals" / "brief.txt"
        source.write_text("truth")
        manifest = {"manifest_version":"0.1.0","sources":[{"id":"S-001","kind":"original","path":"sources/originals/brief.txt","authority":"supplied","sha256":"0" * 64}]}
        (loom / "sources" / "manifest.json").write_text(json.dumps(manifest))
        errors, _ = validate(loom)
        self.assertTrue(any("hash mismatch" in error for error in errors))

    def test_valid_html_passes(self) -> None:
        path = self.base / "index.html"
        path.write_text(VALID_HTML, encoding="utf-8")
        errors, _ = inspect(path)
        self.assertEqual(errors, [])

    def test_static_html_rejects_external_script_and_event_handler(self) -> None:
        path = self.base / "bad.html"
        path.write_text(VALID_HTML.replace("</main>", '<script src="https://example.invalid/x.js"></script><button onclick="go()">Go</button></main>'), encoding="utf-8")
        errors, _ = inspect(path)
        self.assertTrue(any("external script" in error for error in errors))
        self.assertTrue(any("event handler" in error for error in errors))

    def test_static_html_requires_semantics_and_alt(self) -> None:
        path = self.base / "bad.html"
        path.write_text("<!doctype html><html><head><title>X</title></head><body><h1>X</h1><img src='x.png'></body></html>", encoding="utf-8")
        errors, _ = inspect(path)
        self.assertTrue(any("semantic <main>" in error for error in errors))
        self.assertTrue(any("missing alt" in error for error in errors))

    def test_packager_creates_one_root_and_manifest(self) -> None:
        loom = self.new_loom()
        output = self.base / "loom.zip"
        _, count = package(loom, output)
        self.assertGreater(count, 5)
        with zipfile.ZipFile(output) as archive:
            names = archive.namelist()
        self.assertTrue(names)
        self.assertEqual({name.split("/", 1)[0] for name in names}, {loom.name})
        self.assertTrue((loom / "review" / "release-manifest.json").is_file())

    def test_packager_rejects_secret_like_file(self) -> None:
        loom = self.new_loom()
        (loom / ".env").write_text("SECRET=yes")
        with self.assertRaises(ValueError):
            package(loom, self.base / "bad.zip")

    def test_all_bundled_schemas_parse_as_json(self) -> None:
        schemas = sorted((SKILL_ROOT / "schemas").glob("*.json"))
        self.assertEqual(len(schemas), 5)
        for schema in schemas:
            with self.subTest(schema=schema.name):
                self.assertIsInstance(json.loads(schema.read_text(encoding="utf-8")), dict)


if __name__ == "__main__":
    unittest.main()
