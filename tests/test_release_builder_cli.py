from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "tools" / "build_release.py"
VERIFIER = ROOT / "tools" / "verify_package.py"
BUILDER_SPEC = importlib.util.spec_from_file_location("nova_release_builder", BUILDER)
assert BUILDER_SPEC is not None and BUILDER_SPEC.loader is not None
BUILDER_MODULE = importlib.util.module_from_spec(BUILDER_SPEC)
BUILDER_SPEC.loader.exec_module(BUILDER_MODULE)
VERIFIER_SPEC = importlib.util.spec_from_file_location("nova_package_verifier", VERIFIER)
assert VERIFIER_SPEC is not None and VERIFIER_SPEC.loader is not None
VERIFIER_MODULE = importlib.util.module_from_spec(VERIFIER_SPEC)
VERIFIER_SPEC.loader.exec_module(VERIFIER_MODULE)
OUTPUTS = (
    ROOT / "dist",
    ROOT / "release" / f"{BUILDER_MODULE.KIT_NAME}.zip",
    ROOT / "release" / f"{BUILDER_MODULE.KIT_NAME}.zip.sha256",
    ROOT / "release" / f"{BUILDER_MODULE.KIT_NAME}.build-receipt.json",
)


def digest(path: Path) -> str | None:
    if not path.exists():
        return None
    sha = hashlib.sha256()
    files = [path] if path.is_file() else sorted(item for item in path.rglob("*") if item.is_file())
    for item in files:
        relative = item.name if path.is_file() else item.relative_to(path).as_posix()
        sha.update(relative.encode("utf-8"))
        sha.update(b"\0")
        sha.update(hashlib.sha256(item.read_bytes()).digest())
    return sha.hexdigest()


class ReleaseBuilderCliTests(unittest.TestCase):
    def test_help_is_non_mutating(self) -> None:
        before = {str(path): digest(path) for path in OUTPUTS}
        result = subprocess.run(
            [sys.executable, "-B", str(BUILDER), "--help"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        after = {str(path): digest(path) for path in OUTPUTS}
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage:", result.stdout)
        self.assertEqual(before, after)

    def test_builder_requires_committed_tracked_source(self) -> None:
        text = BUILDER.read_text(encoding="utf-8")
        self.assertIn('"--untracked-files=no"', text)
        self.assertIn("tracked source changes must be committed", text)
        self.assertIn('parser.add_argument(\n        "--replace"', text)
        self.assertIn('"--output-root"', text)
        self.assertIn("_assert_payload_is_tracked(tracked)", text)
        self.assertIn("_assert_tracked_bytes_match_revision(tracked, revision)", text)
        self.assertIn("key=windows_stable_ordinal_key", text)
        self.assertIn("require_same_release(dist)", text)
        self.assertIn('"source_revision": revision', text)
        self.assertIn('"source_material_sha256": source_digest', text)

    def test_builder_rejects_clean_but_byte_different_worktree(self) -> None:
        with mock.patch.object(
            BUILDER_MODULE,
            "git_batch_output",
            side_effect=[
                ["same-object", "worktree-object"],
                ["same-object", "revision-object"],
            ],
        ):
            with self.assertRaisesRegex(RuntimeError, "raw tracked worktree bytes differ"):
                BUILDER_MODULE._assert_tracked_bytes_match_revision(
                    {"alpha.txt", "beta.txt"},
                    "a" * 40,
                )

    def test_source_digest_order_is_windows_stable_with_exact_case_tiebreak(self) -> None:
        paths = {"alpha/Z.md", "Alpha/z.md", "alpha/z.md", "beta.md"}
        self.assertEqual(
            sorted(paths, key=BUILDER_MODULE.windows_stable_ordinal_key),
            ["Alpha/z.md", "alpha/Z.md", "alpha/z.md", "beta.md"],
        )
        self.assertEqual(
            BUILDER_MODULE.windows_stable_ordinal_key("Alpha/z.md"),
            ("alpha/z.md", "Alpha/z.md"),
        )

    def test_build_receipt_environment_is_reproducibility_scoped(self) -> None:
        environment = BUILDER_MODULE.reproducibility_environment()
        self.assertEqual(set(environment), {"python", "zlib", "platform"})
        self.assertEqual(
            set(environment["python"]),
            {"implementation", "version"},
        )
        self.assertEqual(
            set(environment["zlib"]),
            {"compile_version", "runtime_version"},
        )
        self.assertEqual(
            set(environment["platform"]),
            {"os_name", "sys_platform", "system", "release", "version", "machine"},
        )
        self.assertTrue(all(environment["python"].values()))
        self.assertTrue(all(environment["zlib"].values()))
        self.assertNotIn("node", environment["platform"])
        self.assertNotIn("environment", environment)
        self.assertIn(
            '"reproducibility_environment": reproducibility_environment()',
            BUILDER.read_text(encoding="utf-8"),
        )

    def test_payload_rejects_and_never_copies_untracked_files(self) -> None:
        original = (
            BUILDER_MODULE.ROOT,
            BUILDER_MODULE.PACKAGED_DIRECTORIES,
            BUILDER_MODULE.PACKAGED_FILES,
        )
        try:
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                payload = root / "payload"
                payload.mkdir()
                (payload / "tracked.txt").write_text("tracked", encoding="utf-8")
                (payload / "untracked.txt").write_text("untracked", encoding="utf-8")
                BUILDER_MODULE.ROOT = root
                BUILDER_MODULE.PACKAGED_DIRECTORIES = ("payload",)
                BUILDER_MODULE.PACKAGED_FILES = ()
                tracked = {"payload/tracked.txt"}
                with self.assertRaisesRegex(RuntimeError, "not bound to the Git revision"):
                    BUILDER_MODULE._assert_payload_is_tracked(tracked)
                (payload / "untracked.txt").unlink()
                BUILDER_MODULE._assert_payload_is_tracked(tracked)
                target = root / "output"
                BUILDER_MODULE.copytree(payload, target, tracked)
                self.assertEqual((target / "tracked.txt").read_text(encoding="utf-8"), "tracked")
                self.assertEqual([path.name for path in target.iterdir()], ["tracked.txt"])
        finally:
            (
                BUILDER_MODULE.ROOT,
                BUILDER_MODULE.PACKAGED_DIRECTORIES,
                BUILDER_MODULE.PACKAGED_FILES,
            ) = original

    def test_output_root_may_not_be_a_filesystem_root(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "filesystem root"):
            BUILDER_MODULE.validate_output_root(Path(Path.cwd().anchor))

    def test_replace_refuses_a_different_release_dist(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            dist = Path(directory) / "dist"
            dist.mkdir()
            manifest = dist / "release-manifest.json"
            manifest.write_text(json.dumps({"version": "different"}), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "different-version|refused to replace dist version"):
                BUILDER_MODULE.require_same_release(dist)
            manifest.write_text(json.dumps({"version": BUILDER_MODULE.VERSION}), encoding="utf-8")
            BUILDER_MODULE.require_same_release(dist)

    def test_builder_derives_the_customer_archive_mind_link(self) -> None:
        text = BUILDER.read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn(
            'source_mind_link = "plugins/augment-of-mind/USER-GUIDE.md"',
            text,
        )
        self.assertIn(
            'packaged_mind_link = "codex/plugins/augment-of-mind/USER-GUIDE.md"',
            text,
        )
        self.assertIn("packaged_readme_text.count(source_mind_link) != 1", text)
        self.assertEqual(readme.count("plugins/augment-of-mind/USER-GUIDE.md"), 1)
        self.assertTrue((ROOT / "plugins" / "augment-of-mind" / "USER-GUIDE.md").is_file())

    def test_builder_packages_linked_design_evidence(self) -> None:
        text = BUILDER.read_text(encoding="utf-8")
        self.assertIn('design_target = dist / "design"', text)
        self.assertIn('("FREE-NOVA-PACKAGE-MAP.md", "source-lock.json")', text)
        self.assertTrue((ROOT / "design" / "FREE-NOVA-PACKAGE-MAP.md").is_file())
        self.assertTrue((ROOT / "design" / "source-lock.json").is_file())

    def test_verifier_help_exposes_external_release_root_without_mutation(self) -> None:
        before = {str(path): digest(path) for path in OUTPUTS}
        result = subprocess.run(
            [sys.executable, "-B", str(VERIFIER), "--help"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        after = {str(path): digest(path) for path in OUTPUTS}
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--release-root DIST_PATH", result.stdout)
        self.assertEqual(before, after)

    def test_external_release_root_implies_release_and_is_resolved(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            external_dist = Path(directory) / "candidate" / "dist"
            evidence = {"status": "PASS"}
            with mock.patch.object(
                VERIFIER_MODULE,
                "verify",
                return_value=evidence,
            ) as verifier, contextlib.redirect_stdout(io.StringIO()):
                result = VERIFIER_MODULE.main(["--release-root", str(external_dist)])
            self.assertEqual(result, 0)
            verifier.assert_called_once_with(True, external_dist.resolve())

    def test_external_release_errors_use_package_relative_display_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            external_dist = Path(directory) / "dist"
            errors: list[str] = []
            VERIFIER_MODULE.verify_release(errors, external_dist)
            self.assertIn(
                "release path missing: codex/plugins/nova-the-optimal-ai",
                errors,
            )
            self.assertTrue(all(str(external_dist.resolve()) not in error for error in errors))

    def test_builder_runs_release_verifier_before_archive_sealing(self) -> None:
        text = BUILDER.read_text(encoding="utf-8")
        verify_call = 'str(ROOT / "tools" / "verify_package.py")'
        seal_call = "write_zip(dist, archive_output, KIT_NAME)"
        self.assertIn(verify_call, text)
        self.assertIn('"--release-root"', text)
        self.assertLess(text.index(verify_call), text.index(seal_call))

    def test_directory_parity_rejects_mutated_and_missing_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            expected = root / "expected"
            observed = root / "observed"
            expected.mkdir()
            observed.mkdir()
            (expected / "kept.txt").write_bytes(b"canonical")
            (expected / "omitted.txt").write_bytes(b"required")
            (observed / "kept.txt").write_bytes(b"corrupt")
            errors: list[str] = []
            VERIFIER_MODULE.compare_directory_bytes(
                errors, expected, observed, "adversarial parity"
            )
            self.assertTrue(any("file set mismatch" in error for error in errors))
            self.assertTrue(any("byte mismatch" in error for error in errors))

    def test_zip_parity_rejects_unsafe_omitted_and_mutated_members(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = root / "skill"
            folder.mkdir()
            (folder / "SKILL.md").write_bytes(b"canonical")
            (folder / "required.txt").write_bytes(b"required")
            archive = root / "skill.zip"
            with zipfile.ZipFile(archive, "w") as bundle:
                bundle.writestr("skill/SKILL.md", b"corrupt")
                bundle.writestr("../escape.txt", b"unsafe")
            errors: list[str] = []
            VERIFIER_MODULE.verify_zip_folder_parity(
                errors, archive, folder, "skill", root
            )
            self.assertTrue(any("unsafe member path" in error for error in errors))
            self.assertTrue(any("member set mismatch" in error for error in errors))
            self.assertTrue(any("byte mismatch" in error for error in errors))

    def test_staged_checksums_reject_mutation_and_omission(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "payload.bin").write_bytes(b"mutated")
            (root / "SHA256SUMS.txt").write_text(
                f'{"0" * 64}  payload.bin\n',
                encoding="utf-8",
            )
            errors: list[str] = []
            VERIFIER_MODULE.verify_staged_checksums(
                errors, root, {"payload.bin", "required.bin"}
            )
            self.assertTrue(any("target set mismatch" in error for error in errors))
            self.assertTrue(any("checksum mismatch" in error for error in errors))

    def test_release_manifest_rejects_false_claims(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "release-manifest.json"
            manifest.write_text(
                json.dumps({"version": "wrong"}),
                encoding="utf-8",
            )
            errors: list[str] = []
            VERIFIER_MODULE.verify_release_manifest(
                errors,
                manifest,
                {"version": BUILDER_MODULE.VERSION},
            )
            self.assertIn(
                "release manifest claims do not match staged contents and source state",
                errors,
            )

    def test_ci_installs_standalone_mind_build_requirements(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "verify-package.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("Install deterministic build requirements", workflow)
        self.assertIn('python -m pip install "setuptools>=69.2" wheel', workflow)


if __name__ == "__main__":
    unittest.main()
