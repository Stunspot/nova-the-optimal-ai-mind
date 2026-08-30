from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("nova_site_checker", REPO / "docs" / "check_site.py")
assert SPEC and SPEC.loader
SITE_CHECKER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SITE_CHECKER)


class SiteCheckerBoundaryTests(unittest.TestCase):
    def test_rejects_existing_link_outside_deployed_docs_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            docs = root / "docs"
            docs.mkdir()
            (root / "SECURITY.md").write_text("outside deployment", encoding="utf-8")
            page = docs / "index.html"
            page.write_text(
                "<!doctype html><html lang='en'><body>"
                "<a class='skip-link' href='#main'>Skip</a>"
                "<nav aria-label='Primary'><a href='../SECURITY.md'>Security</a></nav>"
                "<main id='main'><h1>Test</h1></main>"
                "</body></html>",
                encoding="utf-8",
            )
            original_docs = SITE_CHECKER.DOCS
            SITE_CHECKER.DOCS = docs.resolve()
            try:
                failures = SITE_CHECKER.check_page(page)
            finally:
                SITE_CHECKER.DOCS = original_docs
            self.assertIn("link escapes deployed docs artifact: ../SECURITY.md", failures)


if __name__ == "__main__":
    unittest.main()