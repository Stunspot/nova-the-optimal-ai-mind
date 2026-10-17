"""Isolated executable checks for the known Personal AI Archive reader."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("archive_reader_test", Path(__file__).resolve().parents[1] / "scripts/archive_reader.py")
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)


def fixture(root, content="alpha beta café 世界 💠 — a source quotation."):
    path = Path(root) / "rag" / "archive-current.sqlite3"
    path.parent.mkdir(parents=True)
    connection = sqlite3.connect(path)
    connection.executescript('''
        CREATE TABLE documents(id INTEGER PRIMARY KEY, source TEXT, external_id TEXT, title TEXT,
            created_at TEXT, source_path TEXT, metadata_json TEXT, ingested_at TEXT);
        CREATE TABLE chunks(id INTEGER PRIMARY KEY, document_id INTEGER, ordinal INTEGER,
            role TEXT, created_at TEXT, content TEXT);
        CREATE VIRTUAL TABLE chunks_fts USING fts5(content, content='chunks', content_rowid='id');
    ''')
    connection.execute("INSERT INTO documents VALUES (?,?,?,?,?,?,?,?)",
        (7, "chatgpt", "conv-世界", "A preserved conversation", "2026-09-01T10:00:00Z", "originals/export.json", json.dumps({"origin": "fixture"}), "2026-09-02T11:00:00Z"))
    connection.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?)", (91, 7, 3, "assistant", "2026-09-01T10:02:00Z", content))
    connection.execute("INSERT INTO chunks_fts(chunks_fts) VALUES ('rebuild')")
    connection.commit()
    connection.close()
    return path


class ArchiveReaderTests(unittest.TestCase):
    def setUp(self):
        reader._clear_cache()
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "archive"
        self.database = fixture(self.root)
        self.original = self.database.read_bytes()
        self.original_entries = sorted(p.relative_to(self.root).as_posix() for p in self.root.rglob('*'))
        self.addCleanup(self.temporary.cleanup)
        self.addCleanup(reader._clear_cache)

    def assert_source_unchanged(self):
        self.assertEqual(self.database.read_bytes(), self.original)
        self.assertEqual(sorted(p.relative_to(self.root).as_posix() for p in self.root.rglob('*')), self.original_entries)

    def test_detect_is_exact_and_does_not_scan_or_initialize_other_locations(self):
        self.assertEqual(reader.detect(self.root), self.database)
        missing = Path(self.temporary.name) / "missing"
        self.assertIsNone(reader.detect(missing))
        self.assertFalse(missing.exists())
        self.assertIsNone(reader.detect(self.database))
        with self.assertRaisesRegex(reader.ArchiveReadError, "no supported"):
            reader.summary(missing)
        self.assert_source_unchanged()

    def test_detect_rejects_a_linked_rag_or_database_component(self):
        real_linked = reader._linked
        for blocked in (self.root, self.root / "rag", self.database):
            with patch.object(reader, "_linked", side_effect=lambda path: path == blocked or real_linked(path)):
                self.assertIsNone(reader.detect(self.root))
        self.assert_source_unchanged()

    @unittest.skipUnless(os.name == "nt", "native Windows junction check")
    def test_detect_rejects_an_actual_windows_rag_junction(self):
        other = Path(self.temporary.name) / "junction-root"
        other.mkdir()
        junction = other / "rag"
        created = subprocess.run(["cmd", "/c", "mklink", "/J", str(junction), str(self.root / "rag")], capture_output=True)
        self.assertEqual(created.returncode, 0, created.stderr.decode(errors="replace"))
        try:
            self.assertTrue(reader._linked(junction))
            self.assertIsNone(reader.detect(other))
            with self.assertRaises(reader.ArchiveReadError):
                reader.summary(other)
            self.assert_source_unchanged()
        finally:
            junction.rmdir()

    def test_explicit_snapshot_with_removed_source_is_stale(self):
        token = reader.summary(self.root)["snapshot"]
        self.database.unlink()
        with self.assertRaisesRegex(reader.ArchiveStaleError, "unavailable"):
            reader.search(self.root, "alpha", snapshot=token)

    def test_summary_has_real_counts_identity_time_and_reuses_a_valid_snapshot(self):
        result = reader.summary(self.root)
        self.assertEqual(result["document_count"], 1)
        self.assertEqual(result["chunk_count"], 1)
        self.assertEqual(result["snapshot_identity"], hashlib.sha256(self.original).hexdigest())
        self.assertEqual(result["source_database"], str(self.database))
        self.assertIn("+00:00", result["snapshot_created_at"])
        self.assertIn("+00:00", result["source_modified_at"])
        self.assertEqual(reader.summary(self.root)["snapshot"], result["snapshot"])
        self.assert_source_unchanged()

    def test_unicode_search_exposes_content_and_stable_owner_locator(self):
        result = reader.search(self.root, "café 世界")
        self.assertEqual(len(result["hits"]), 1)
        hit = result["hits"][0]
        self.assertEqual(hit["locator"], {"source": "chatgpt", "external_id": "conv-世界", "ordinal": 3})
        self.assertIn("café 世界", hit["snippet"])
        self.assertEqual(hit["title"], "A preserved conversation")
        self.assertEqual(hit["role"], "assistant")
        self.assertEqual(hit["created_at"], "2026-09-01T10:02:00Z")
        self.assertEqual(hit["document_created_at"], "2026-09-01T10:00:00Z")
        self.assertEqual(hit["recorded_source_path"], "originals/export.json")
        self.assertNotIn("id", hit)
        self.assertNotIn("id", hit["locator"])
        record = reader.record(self.root, **hit["anchor"])
        self.assertIn("source quotation", record["content"])
        self.assertEqual(record["locator"], hit["locator"])
        self.assertEqual(record["snapshot"], result["snapshot"])
        self.assert_source_unchanged()

    def test_search_quotes_and_operators_are_literal_parameterized_terms(self):
        self.assertEqual(len(reader.search(self.root, '"alpha"')["hits"]), 1)
        self.assertEqual(reader.search(self.root, 'alpha" OR "unfindable')["hits"], [])
        self.assertEqual(reader.search(self.root, 'alpha NEAR(beta)')["hits"], [])
        self.assertEqual(reader.search(self.root, '"; DROP TABLE chunks; --')["hits"], [])
        self.assertEqual(reader.search(self.root, '"')["hits"], [])
        self.assertEqual(reader.summary(self.root)["chunk_count"], 1)
        self.assert_source_unchanged()

    def test_blank_search_browses_real_recent_records_with_a_bounded_limit(self):
        result = reader.search(self.root, "", limit=1)
        self.assertEqual(len(result["hits"]), 1)
        self.assertIn("source quotation", result["hits"][0]["snippet"])
        for limit in (True, 0, 101, 1.5, "20"):
            with self.assertRaises(reader.ArchiveReadError):
                reader.search(self.root, "alpha", limit)
        with self.assertRaises(reader.ArchiveReadError):
            reader.search(self.root, "alpha " * 33)
        with self.assertRaises(reader.ArchiveReadError):
            reader.search(self.root, "a" * 2049)

    def test_record_fingerprints_exact_text_and_separates_the_recorded_source_path(self):
        record = reader.record(self.root, "chatgpt", "conv-世界", 3)
        self.assertEqual(record["format"], "archive")
        self.assertEqual(record["source_fingerprint"], hashlib.sha256(self.original).hexdigest())
        digest = hashlib.sha256(record["content"].encode("utf-8")).hexdigest()
        self.assertEqual(record["sample_sha256"], digest)
        self.assertEqual(record["content_fingerprint"], digest)
        self.assertEqual(record["full_char_count"], len(record["content"]))
        self.assertIsNone(record["next_offset"])
        self.assertEqual(record["offset"], 0)
        self.assertEqual(record["recorded_source_path"], "originals/export.json")
        self.assertNotEqual(record["recorded_source_path"], record["source_database"])
        self.assertEqual(reader.record(self.root, **record["anchor"])["sample_sha256"], digest)
        self.assert_source_unchanged()

    def test_full_long_record_pagination_preserves_unicode_and_terminal_state(self):
        long_root = Path(self.temporary.name) / "long"
        content = ("💠 café 世界 e\u0301\x00end " * 7000) + "FINISH"
        fixture(long_root, content)
        offset = 0
        assembled = []
        snapshot = None
        while True:
            result = reader.record(long_root, "chatgpt", "conv-世界", 3, offset, snapshot)
            snapshot = result["snapshot"]
            self.assertEqual(result["offset"], offset)
            self.assertLessEqual(len(result["content"]), 32768)
            self.assertEqual(result["full_char_count"], len(content))
            self.assertEqual(result["content_fingerprint"], hashlib.sha256(content.encode()).hexdigest())
            self.assertEqual(result["sample_sha256"], hashlib.sha256(result["content"].encode()).hexdigest())
            assembled.append(result["content"])
            if result["next_offset"] is None:
                self.assertFalse(result["truncated"])
                break
            self.assertTrue(result["truncated"])
            offset = result["next_offset"]
        self.assertEqual("".join(assembled), content)
        self.assertEqual(reader.record(long_root, "chatgpt", "conv-世界", 3, len(content), snapshot)["content"], "")
        with self.assertRaisesRegex(reader.ArchiveReadError, "beyond"):
            reader.record(long_root, "chatgpt", "conv-世界", 3, len(content) + 1, snapshot)

    def test_record_lookup_uses_stable_keys_after_internal_row_ids_change(self):
        first = reader.search(self.root, "alpha")["hits"][0]
        token = first["anchor"]["snapshot"]
        connection = sqlite3.connect(self.database)
        connection.execute("UPDATE documents SET id=107 WHERE id=7")
        connection.execute("UPDATE chunks SET id=901,document_id=107 WHERE id=91")
        connection.execute("INSERT INTO chunks_fts(chunks_fts) VALUES ('rebuild')")
        connection.commit()
        connection.close()
        with self.assertRaises(reader.ArchiveStaleError):
            reader.record(self.root, **first["anchor"])
        refreshed = reader.search(self.root, "alpha")
        self.assertNotEqual(refreshed["snapshot"], token)
        self.assertEqual(refreshed["hits"][0]["locator"], first["locator"])
        record = reader.record(self.root, **refreshed["hits"][0]["anchor"])
        self.assertIn("source quotation", record["content"])

    def test_nonempty_wal_and_journal_are_rejected_without_touching_them(self):
        for suffix in ("-wal", "-journal"):
            sidecar = Path(str(self.database) + suffix)
            sidecar.write_bytes(b"live writes owned elsewhere")
            before = sidecar.read_bytes()
            with self.assertRaisesRegex(reader.ArchiveReadError, "nonempty"):
                reader.summary(self.root)
            self.assertEqual(sidecar.read_bytes(), before)
            self.assertEqual(self.database.read_bytes(), self.original)
            sidecar.unlink()
        self.assert_source_unchanged()

    def test_live_sqlite_wal_writer_is_refused_even_with_a_cached_snapshot(self):
        token = reader.summary(self.root)["snapshot"]
        connection = sqlite3.connect(self.database)
        try:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("UPDATE chunks SET content='writer owns these bytes'")
            connection.commit()
            self.assertGreater(Path(str(self.database) + "-wal").stat().st_size, 0)
            with self.assertRaisesRegex(reader.ArchiveReadError, "nonempty wal"):
                reader.search(self.root, "alpha", snapshot=token)
        finally:
            connection.close()

    def test_source_overwrite_invalidates_an_explicit_token_and_can_be_refreshed(self):
        first = reader.summary(self.root)
        original_stat = self.database.stat()
        self.database.write_bytes(self.original)
        os.utime(self.database, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns + 1_000_000_000))
        with self.assertRaisesRegex(reader.ArchiveStaleError, "changed"):
            reader.search(self.root, "alpha", snapshot=first["snapshot"])
        second = reader.summary(self.root)
        self.assertNotEqual(first["snapshot"], second["snapshot"])
        self.assertEqual(first["snapshot_identity"], second["snapshot_identity"])
        self.assertEqual(len(reader.search(self.root, "alpha", snapshot=second["snapshot"])["hits"]), 1)

    def test_snapshot_cache_is_bounded_and_eviction_expires_old_tokens(self):
        token = reader.summary(self.root)["snapshot"]
        private_copy = reader._CACHE[token].copied
        for index in range(2):
            other = Path(self.temporary.name) / f"other-{index}"
            fixture(other)
            reader.summary(other)
        self.assertEqual(len(reader._CACHE), 2)
        self.assertFalse(private_copy.exists())
        with self.assertRaisesRegex(reader.ArchiveStaleError, "no longer cached"):
            reader.search(self.root, "alpha", snapshot=token)
        self.assert_source_unchanged()

    def test_snapshot_cannot_be_reused_for_another_registered_root(self):
        token = reader.summary(self.root)["snapshot"]
        other = Path(self.temporary.name) / "different"
        fixture(other)
        with self.assertRaisesRegex(reader.ArchiveStaleError, "different registered root"):
            reader.record(other, "chatgpt", "conv-世界", 3, snapshot=token)

    def test_private_copy_digest_tampering_is_rejected_and_deliberate_refresh_recovers(self):
        token = reader.summary(self.root)["snapshot"]
        copied = reader._CACHE[token].copied
        original = copied.read_bytes()
        copied.write_bytes(original + b"modified")
        with self.assertRaisesRegex(reader.ArchiveStaleError, "Private archive snapshot changed"):
            reader.search(self.root, "alpha", snapshot=token)
        refreshed = reader.summary(self.root)
        self.assertNotEqual(refreshed["snapshot"], token)
        self.assertEqual(refreshed["snapshot_identity"], hashlib.sha256(self.original).hexdigest())
        self.assert_source_unchanged()

    def test_copy_size_bound_and_concurrent_source_change_reject_before_any_read(self):
        with patch.object(reader, "MAX_DATABASE_BYTES", self.database.stat().st_size - 1):
            with self.assertRaisesRegex(reader.ArchiveReadError, "256 MB"):
                reader.summary(self.root)
        before = reader._stat_signature(self.database)
        altered = before[:3] + (before[3] + 1_000_000_000,) + before[4:]
        with patch.object(reader, "_stat_signature", side_effect=[before, before, altered]):
            with self.assertRaisesRegex(reader.ArchiveStaleError, "changed while being copied"):
                reader.summary(self.root)
        self.assertEqual(len(reader._CACHE), 0)
        self.assert_source_unchanged()

    def test_source_change_during_a_read_invalidates_the_result_before_return(self):
        token = reader.summary(self.root)["snapshot"]
        before = reader._stat_signature(self.database)
        after = before[:3] + (before[3] + 1_000_000_000,) + before[4:]
        with patch.object(reader, "_stat_signature", side_effect=[before, after]):
            with self.assertRaisesRegex(reader.ArchiveStaleError, "changed"):
                reader.record(self.root, "chatgpt", "conv-世界", 3, snapshot=token)
        self.assert_source_unchanged()

    def test_known_schema_only_and_read_connection_cannot_write(self):
        malformed = Path(self.temporary.name) / "generic"
        path = malformed / "rag/archive-current.sqlite3"
        path.parent.mkdir(parents=True)
        connection = sqlite3.connect(path)
        connection.execute("CREATE TABLE assets (content TEXT)")
        connection.commit()
        connection.close()
        original = path.read_bytes()
        with self.assertRaisesRegex(reader.ArchiveReadError, "Unsupported archive schema"):
            reader.summary(malformed)
        self.assertEqual(path.read_bytes(), original)
        result = reader.summary(self.root)
        connection = reader._connect(reader._CACHE[result["snapshot"]].copied)
        try:
            self.assertEqual(connection.execute("PRAGMA query_only").fetchone()[0], 1)
            with self.assertRaises(sqlite3.OperationalError):
                connection.execute("DELETE FROM chunks")
        finally:
            connection.close()
        self.assert_source_unchanged()

    def test_missing_ambiguous_and_invalid_record_anchors_fail_usefully(self):
        for args in [("chatgpt", "missing", 3), ("chatgpt", "conv-世界", True), ("chatgpt", "conv-世界", -1), ("", "conv-世界", 3)]:
            with self.assertRaises(reader.ArchiveReadError):
                reader.record(self.root, *args)
        with self.assertRaises(reader.ArchiveReadError):
            reader.record(self.root, "chatgpt", "conv-世界", 3, offset=True)
        connection = sqlite3.connect(self.database)
        connection.execute("INSERT INTO documents SELECT 8,source,external_id,title,created_at,source_path,metadata_json,ingested_at FROM documents WHERE id=7")
        connection.execute("INSERT INTO chunks SELECT 92,8,ordinal,role,created_at,content FROM chunks WHERE id=91")
        connection.commit()
        connection.close()
        with self.assertRaisesRegex(reader.ArchiveReadError, "ambiguous"):
            reader.record(self.root, "chatgpt", "conv-世界", 3)


if __name__ == "__main__":
    unittest.main()

# Added direct document/conversation browsing coverage.
class ArchiveBrowseTests(unittest.TestCase):
    setUp=ArchiveReaderTests.setUp
    assert_source_unchanged=ArchiveReaderTests.assert_source_unchanged
    def test_titles_and_messages_are_browsable_without_a_query(self):
        titles=reader.browse_documents(self.root,limit=1)
        self.assertEqual(titles['total'],1)
        self.assertEqual(titles['documents'][0]['title'],'A preserved conversation')
        self.assertEqual(titles['documents'][0]['part_count'],1)
        parts=reader.document_records(self.root,'chatgpt','conv-世界',snapshot=titles['snapshot'])
        self.assertEqual(parts['hits'][0]['locator']['ordinal'],3)
        self.assertIn('café',parts['hits'][0]['snippet'])
        self.assert_source_unchanged()
    def test_browse_positions_are_bounded_and_document_identity_is_exact(self):
        for offset in (-1,True):
            with self.assertRaises(reader.ArchiveReadError):
                reader.browse_documents(self.root,offset=offset)
        with self.assertRaises(reader.ArchiveReadError):
            reader.document_records(self.root,'chatgpt','missing')
        self.assert_source_unchanged()

