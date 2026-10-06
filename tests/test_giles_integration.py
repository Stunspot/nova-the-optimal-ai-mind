from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PLUGIN = REPO / "plugins/nova-the-optimal-ai"
GILES = PLUGIN / "skills/rupert-giles-knowledge-steward"


class GilesEditionIntegrationTests(unittest.TestCase):
    def test_cli_recognizes_section_and_round_trips_without_source_mutation(self):
        with tempfile.TemporaryDirectory(prefix="free-giles-") as directory:
            base = Path(directory)
            catalog = base / "private/catalog.json"
            source = base / "source"
            (source / "Shemp Studies").mkdir(parents=True)
            text = source / "Shemp Studies/README.md"
            text.write_text("Synthetic fixture: Shemp appeared in these teaching notes.\n", encoding="utf-8")
            original = text.read_bytes()
            prefix = [sys.executable, "-B", "-X", "utf8", "skills/rupert-giles-knowledge-steward/scripts/giles.py", "--catalog", str(catalog)]

            def run(*args):
                result = subprocess.run(prefix + list(args), cwd=PLUGIN, capture_output=True, text=True, encoding="utf-8", check=False)
                self.assertEqual(result.returncode, 0, result.stderr)
                return result.stdout

            self.assertIn("0 catalog matches", run("list"))
            self.assertFalse(catalog.exists(), "Read-only discovery must not initialize storage")
            incoming = base / "incoming.json"
            incoming.write_text(json.dumps({"schema":"giles-knowledge-catalog/v1", "revision":0, "stores":[{
                "id":"three-stooges", "name":"Three Stooges Knowledge Archive", "location":str(source),
                "summary":"Clearly synthetic fixture for archive discovery.", "kind":"folder", "role":"canonical",
                "lifecycle":"current", "inspection":"metadata_only", "owner":"fixture",
                "use_when":["Recover teaching notes about Shemp"], "aliases":["Stooges"], "topics":["film"],
                "entrypoint":"", "provenance":"Test fixture", "favorite":False,
                "sections":[{"id":"shemp", "title":"Shemp Studies", "path":"Shemp Studies/README.md", "summary":"Synthetic study route", "topics":["film"]}]
            }]}), encoding="utf-8")
            self.assertIn("1 stores", run("import", str(incoming)))
            self.assertIn("three-stooges | Three Stooges", run("find", "Stoges"))
            brief = run("brief", "three-stooges", "--section", "shemp", "--question", "What does this fixture cover?")
            route = next(line.removeprefix("Source route: ") for line in brief.splitlines() if line.startswith("Source route: "))
            self.assertEqual(Path(route).resolve(), text.resolve())
            self.assertEqual(Path(route).read_bytes(), original)
            self.assertIn("metadata_only", brief)
            self.assertIn("What does this fixture cover?", brief)
            exported = json.loads(run("export"))
            persisted = json.loads(catalog.read_text(encoding="utf-8"))
            self.assertEqual(exported, persisted)
            self.assertEqual(original, text.read_bytes())
            self.assertEqual([text], [p for p in source.rglob("*") if p.is_file()])


if __name__ == "__main__":
    unittest.main()
