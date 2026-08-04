from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "corkboard.py"
SPEC = importlib.util.spec_from_file_location("corkboard", SCRIPT)
assert SPEC and SPEC.loader
corkboard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(corkboard)


class CorkboardTests(unittest.TestCase):
    def test_reading_absent_board_does_not_initialize_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "missing"
            self.assertEqual([], corkboard.list_pins(home))
            self.assertFalse(home.exists())

    def test_pin_round_trips_unicode_context_and_tags(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            created = corkboard.pin(
                home,
                text="Check the permissions border after the contest. 🧷",
                cue="When contest work winds down",
                tags="permissions, contest, permissions",
            )
            records = corkboard.list_pins(home)
            self.assertEqual(created["id"], records[0]["id"])
            self.assertEqual("Check the permissions border after the contest. 🧷", records[0]["text"])
            self.assertEqual(["permissions", "contest"], records[0]["tags"])

    def test_concepts_preserve_utility_order_and_frontload_retrieval_text(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            created = corkboard.pin(
                home,
                text="Try the free Kimi web tier.",
                cue="When comparing hosted models",
                concepts=["hosted model evaluation", "Kimi K3", "free tier"],
                tags=["Kimi", "evaluation"],
            )
            record = corkboard.list_pins(home)[0]
            self.assertEqual(created["concepts"], record["concepts"])
            self.assertEqual(
                ["hosted model evaluation", "Kimi K3", "free tier"],
                record["concepts"],
            )
            self.assertTrue(
                corkboard.retrieval_text(record).startswith(
                    "hosted model evaluation · Kimi K3 · free tier —"
                )
            )

    def test_relevance_prefers_matching_pin_and_excludes_noise(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            corkboard.pin(
                home,
                text="Audit Nova's permissions border.",
                cue="After the contest or while changing harness permissions",
                tags="Nova, permissions, audit",
            )
            corkboard.pin(
                home,
                text="Look at the box of spare curtain hooks.",
                cue="During housecleaning",
                tags="house, cleaning",
            )
            records = corkboard.list_pins(home, query="harness permission audit", limit=3)
            self.assertEqual(1, len(records))
            self.assertIn("permissions", str(records[0]["text"]))

    def test_concept_position_changes_retrieval_priority(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            first = corkboard.pin(
                home,
                text="Review the hosted route.",
                concepts=["privacy", "billing"],
            )
            corkboard.pin(
                home,
                text="Review the hosted route.",
                concepts=["billing", "privacy"],
            )
            corpus = corkboard.rag_corpus(home, query="privacy")
            self.assertEqual(first["id"], corpus["documents"][0]["id"])

    def test_rag_returns_every_eligible_pin_and_preserves_project_scope(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            kimi = corkboard.pin(
                home,
                text="Try the free Kimi web tier.",
                concepts=["hosted model evaluation", "Kimi K3"],
            )
            corkboard.pin(home, text="Look at the spare curtain hooks.")
            corkboard.pin(home, text="Alpha-only reminder.", project="alpha")
            corkboard.pin(home, text="Beta-only reminder.", project="beta")
            corpus = corkboard.rag_corpus(
                home,
                query="compare a hosted long-context model",
                project="alpha",
            )
            self.assertEqual(3, corpus["corpus_size"])
            self.assertEqual(kimi["id"], corpus["documents"][0]["id"])
            self.assertEqual(
                {"Try the free Kimi web tier.", "Look at the spare curtain hooks.", "Alpha-only reminder."},
                {document["text"] for document in corpus["documents"]},
            )

    def test_project_filter_includes_global_and_matching_project(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            corkboard.pin(home, text="Global pin")
            corkboard.pin(home, text="Alpha pin", project="alpha")
            corkboard.pin(home, text="Beta pin", project="beta")
            records = corkboard.list_pins(home, project="alpha")
            self.assertEqual({"Global pin", "Alpha pin"}, {record["text"] for record in records})

    def test_unscoped_recall_hides_project_pins_unless_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            corkboard.pin(home, text="Global pin")
            corkboard.pin(home, text="Alpha pin", project="alpha")
            self.assertEqual(["Global pin"], [record["text"] for record in corkboard.list_pins(home)])
            self.assertEqual(
                {"Global pin", "Alpha pin"},
                {record["text"] for record in corkboard.list_pins(home, all_projects=True)},
            )

    def test_unpin_deletes_instead_of_creating_task_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            created = corkboard.pin(home, text="Temporary pin")
            self.assertTrue(corkboard.unpin(home, pin_id=str(created["id"])))
            self.assertEqual([], corkboard.list_pins(home))
            self.assertFalse(corkboard.unpin(home, pin_id=str(created["id"])))
            connection = sqlite3.connect(home / corkboard.DB_NAME)
            self.assertEqual(0, connection.execute("SELECT COUNT(*) FROM pin_fts").fetchone()[0])
            connection.close()

    def test_blank_pin_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, "must not be blank"):
                corkboard.pin(Path(temp), text="   ")

    def test_cli_json_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--home",
                    temp,
                    "pin",
                    "--stdin-json",
                    "--json",
                ],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                input='{"text":"Remember the odd hinge.","cue":"During housecleaning","tags":["hinge"]}\n',
            )
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertIn('"id": "PIN-', result.stdout)
            listed = subprocess.run(
                [sys.executable, str(SCRIPT), "--home", temp, "list", "--json"],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            self.assertEqual(0, listed.returncode, listed.stderr)
            self.assertIn("Remember the odd hinge.", listed.stdout)

    def test_cli_relevance_accepts_query_on_stdin(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            corkboard.pin(home, text="Remember the odd hinge.", cue="During housecleaning")
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--home",
                    temp,
                    "relevant",
                    "--stdin-json",
                    "--json",
                ],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                input='{"query":"housecleaning hinge"}\n',
            )
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertIn("Remember the odd hinge.", result.stdout)

    def test_cli_rag_returns_full_corpus(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            corkboard.pin(home, text="Remember the odd hinge.", concepts=["house repair", "hinge"])
            corkboard.pin(home, text="Try the Kimi web tier.", concepts=["model evaluation", "Kimi"])
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--home",
                    temp,
                    "rag",
                    "--stdin-json",
                    "--json",
                ],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                input='{"query":"repair a cabinet hinge"}\n',
            )
            self.assertEqual(0, result.returncode, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual("cd-corkboard-rag/v1", payload["format"])
            self.assertEqual(2, payload["corpus_size"])
            self.assertEqual("Remember the odd hinge.", payload["documents"][0]["text"])

    def test_hostile_shell_text_round_trips_without_side_effect(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "board"
            canary = Path(temp) / "shell-canary.txt"
            hostile = f'"; New-Item -ItemType File -Path "{canary}"; $(); `whoami`; | & > < #'
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--home",
                    str(home),
                    "pin",
                    "--stdin-json",
                    "--json",
                ],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                input=json.dumps({"text": hostile}) + "\n",
            )
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual(hostile, json.loads(result.stdout)["text"])
            self.assertFalse(canary.exists())

    def test_hostile_project_scope_round_trips_without_side_effect(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "board"
            canary = Path(temp) / "project-canary.txt"
            project = f'alpha"; New-Item -ItemType File -Path "{canary}"; #'
            pinned = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--home",
                    str(home),
                    "pin",
                    "--stdin-json",
                    "--json",
                ],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                input=json.dumps({"text": "Scoped pin", "project": project}) + "\n",
            )
            self.assertEqual(0, pinned.returncode, pinned.stderr)
            listed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--home",
                    str(home),
                    "list",
                    "--stdin-json",
                    "--json",
                ],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                input=json.dumps({"project": project}) + "\n",
            )
            self.assertEqual(0, listed.returncode, listed.stderr)
            self.assertEqual("Scoped pin", json.loads(listed.stdout)[0]["text"])
            self.assertFalse(canary.exists())

    def test_future_schema_is_refused_without_downgrade(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            database = home / corkboard.DB_NAME
            connection = sqlite3.connect(database)
            connection.execute("PRAGMA user_version = 3")
            connection.commit()
            connection.close()
            with self.assertRaisesRegex(RuntimeError, "unsupported corkboard schema version 3"):
                corkboard.pin(home, text="Must not write")
            check = sqlite3.connect(database)
            self.assertEqual(3, check.execute("PRAGMA user_version").fetchone()[0])
            tables = check.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
            check.close()
            self.assertEqual([], tables)

    def test_v1_migration_preserves_pin_and_builds_rag_index(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            database = home / corkboard.DB_NAME
            connection = sqlite3.connect(database)
            connection.executescript(
                """
                CREATE TABLE pins (
                    id TEXT PRIMARY KEY,
                    text TEXT NOT NULL CHECK (length(trim(text)) > 0),
                    cue TEXT NOT NULL DEFAULT '',
                    tags TEXT NOT NULL DEFAULT '[]',
                    project TEXT,
                    source TEXT NOT NULL DEFAULT 'user',
                    created_at TEXT NOT NULL
                );
                CREATE INDEX pins_created_at ON pins(created_at DESC);
                PRAGMA user_version = 1;
                """
            )
            connection.execute(
                "INSERT INTO pins VALUES(?, ?, ?, ?, ?, ?, ?)",
                (
                    "PIN-0123456789ab",
                    "Try the free Kimi web tier.",
                    "When comparing hosted models",
                    '["Kimi", "model-evaluation"]',
                    None,
                    "user",
                    "2026-07-21T00:00:00Z",
                ),
            )
            connection.commit()
            connection.close()

            receipt = corkboard.migrate_board(home)
            self.assertTrue(receipt["migrated"])
            self.assertEqual(1, receipt["schema_before"])
            self.assertEqual(2, receipt["schema_after"])
            self.assertTrue(Path(str(receipt["backup"])).is_file())
            self.assertEqual(1, receipt["pin_count"])

            records = corkboard.list_pins(home)
            self.assertEqual("Try the free Kimi web tier.", records[0]["text"])
            self.assertEqual(["Kimi", "model-evaluation"], records[0]["concepts"][:2])
            corpus = corkboard.rag_corpus(home, query="hosted model evaluation")
            self.assertEqual(1, corpus["corpus_size"])
            check = sqlite3.connect(database)
            self.assertEqual(2, check.execute("PRAGMA user_version").fetchone()[0])
            self.assertEqual(1, check.execute("SELECT COUNT(*) FROM pin_fts").fetchone()[0])
            check.close()

    def test_migrating_absent_board_does_not_initialize_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "missing"
            receipt = corkboard.migrate_board(home)
            self.assertFalse(receipt["migrated"])
            self.assertFalse(home.exists())

    def test_relevance_uses_tokens_not_substring_noise(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            corkboard.pin(home, text="Check supplies in the warehouse")
            self.assertEqual([], corkboard.list_pins(home, query="house cleaning"))


if __name__ == "__main__":
    unittest.main()
