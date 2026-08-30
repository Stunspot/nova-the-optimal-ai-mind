from __future__ import annotations

import argparse
import errno
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import continuity_store_v2 as store
import workspace_runtime as runtime

STORE = SCRIPTS / "continuity_store_v2.py"
VALIDATE = SCRIPTS / "validate_continuity_v2.py"


def temporary_parent() -> str | None:
    candidate = Path("E:/")
    return str(candidate) if os.name == "nt" and candidate.is_dir() else None


class AdapterSeamTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(dir=temporary_parent())
        self.base = Path(self.temporary.name).resolve()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def windows_observation(
        *,
        filesystem: str = "NTFS",
        flags: int = 0,
        drive_type: int = 3,
    ):
        return lambda _probe: {
            "filesystem": filesystem,
            "flags": flags,
            "drive_type": drive_type,
            "volume_path": "X:\\",
        }

    @staticmethod
    def darwin_observation(*, filesystem: str = "apfs", flags: int = runtime._DARWIN_MNT_LOCAL):
        return lambda _probe: {"filesystem": filesystem, "flags": flags}

    @staticmethod
    def linux_observation(
        *,
        filesystem: str = "ext4",
        readonly: bool = False,
        remote: bool = False,
        ephemeral: bool = False,
        volatile: bool = False,
    ):
        return lambda _probe: {
            "filesystem": filesystem,
            "readonly": readonly,
            "remote": remote,
            "ephemeral": ephemeral,
            "volatile": volatile,
            "mount_id": "41",
            "device": "0:47",
        }

    @staticmethod
    def no_op_capability(_root: Path, _probe: Path) -> None:
        return None

    def test_darwin_filesystem_names_are_diagnostic_not_admission(self) -> None:
        self.assertEqual(runtime.ctypes.sizeof(runtime._DarwinStatfs), 2168)
        root = self.base / "workspace"
        expected = "darwin-fcntl-flock-fsync-F_FULLFSYNC-when-available-rename-parent-fsync/v2"
        for filesystem in ("apfs", "hfs", "zfs", "futurefs"):
            with self.subTest(filesystem=filesystem):
                adapter = runtime._filesystem_adapter(
                    root,
                    lexical_root=root,
                    platform_name="darwin",
                    darwin_observer=self.darwin_observation(filesystem=filesystem),
                    posix_capability_probe=self.no_op_capability,
                )
                self.assertEqual(adapter, expected)

    def test_darwin_adapter_rejects_nonlocal_readonly_and_missing_primitives(self) -> None:
        root = self.base / "workspace"
        for flags in (0, runtime._DARWIN_MNT_LOCAL | runtime._DARWIN_MNT_RDONLY):
            with self.subTest(flags=flags):
                with self.assertRaises(runtime.ContinuityError) as caught:
                    runtime._filesystem_adapter(
                        root,
                        lexical_root=root,
                        platform_name="darwin",
                        darwin_observer=self.darwin_observation(flags=flags),
                        posix_capability_probe=self.no_op_capability,
                    )
                self.assertEqual(caught.exception.code, "filesystem_semantics_unsupported")

        def fail_probe(_root: Path, _probe: Path) -> None:
            raise OSError(errno.EINVAL, "directory fsync unavailable")

        with self.assertRaises(runtime.ContinuityError) as caught:
            runtime._filesystem_adapter(
                root,
                lexical_root=root,
                platform_name="darwin",
                darwin_observer=self.darwin_observation(filesystem="futurefs"),
                posix_capability_probe=fail_probe,
            )
        self.assertEqual(caught.exception.code, "filesystem_semantics_unsupported")

    def test_windows_filesystem_names_are_diagnostic_not_admission(self) -> None:
        root = self.base / "workspace"
        expected = "windows-LockFileEx-MoveFileExW-write-through/v2"
        for filesystem in ("NTFS", "ReFS", "exFAT", "FutureFS"):
            with self.subTest(filesystem=filesystem):
                adapter = runtime._filesystem_adapter(
                    root,
                    lexical_root=root,
                    platform_name="win32",
                    windows_observer=self.windows_observation(filesystem=filesystem),
                    windows_capability_probe=self.no_op_capability,
                )
                self.assertEqual(adapter, expected)

    def test_windows_adapter_rejects_readonly_and_topology_hazards(self) -> None:
        root = self.base / "workspace"
        cases = (
            self.windows_observation(flags=runtime._WINDOWS_FILE_READ_ONLY_VOLUME),
            self.windows_observation(drive_type=0),
            self.windows_observation(drive_type=1),
            self.windows_observation(drive_type=4),
            self.windows_observation(drive_type=5),
            self.windows_observation(drive_type=6),
        )
        for observer in cases:
            with self.subTest(observer=observer):
                with self.assertRaises(runtime.ContinuityError) as caught:
                    runtime._filesystem_adapter(
                        root,
                        lexical_root=root,
                        platform_name="win32",
                        windows_observer=observer,
                        windows_capability_probe=self.no_op_capability,
                    )
                self.assertEqual(caught.exception.code, "filesystem_semantics_unsupported")

    def test_linux_filesystem_names_are_diagnostic_not_admission(self) -> None:
        root = self.base / "workspace"
        expected = "linux-fcntl-flock-fsync-rename-parent-fsync/v1"
        for filesystem in ("ext4", "xfs", "btrfs", "zfs", "futurefs"):
            with self.subTest(filesystem=filesystem):
                adapter = runtime._filesystem_adapter(
                    root,
                    lexical_root=root,
                    platform_name="linux",
                    linux_observer=self.linux_observation(filesystem=filesystem),
                    posix_capability_probe=self.no_op_capability,
                )
                self.assertEqual(adapter, expected)

    def test_linux_adapter_rejects_readonly_remote_ephemeral_volatile_and_missing_primitives(self) -> None:
        root = self.base / "workspace"
        cases = (
            self.linux_observation(readonly=True),
            self.linux_observation(filesystem="nfs"),
            self.linux_observation(filesystem="tmpfs"),
            self.linux_observation(filesystem="overlay", volatile=True),
        )
        for observer in cases:
            with self.subTest(observer=observer):
                with self.assertRaises(runtime.ContinuityError) as caught:
                    runtime._filesystem_adapter(
                        root,
                        lexical_root=root,
                        platform_name="linux",
                        linux_observer=observer,
                        posix_capability_probe=self.no_op_capability,
                    )
                self.assertEqual(caught.exception.code, "filesystem_semantics_unsupported")

        def fail_probe(_root: Path, _probe: Path) -> None:
            raise OSError(errno.ENOTSUP, "flock unavailable")

        with self.assertRaises(runtime.ContinuityError) as caught:
            runtime._filesystem_adapter(
                root,
                lexical_root=root,
                platform_name="linux",
                linux_observer=self.linux_observation(filesystem="futurefs"),
                posix_capability_probe=fail_probe,
            )
        self.assertEqual(caught.exception.code, "filesystem_semantics_unsupported")

    def test_linux_adapter_fails_closed_on_incomplete_mount_observations(self) -> None:
        root = self.base / "workspace"
        cases = (
            {"readonly": False, "mount_id": "41", "device": "0:47"},
            {"filesystem": "ext4", "readonly": False, "device": "0:47"},
            {"filesystem": "ext4", "readonly": False, "mount_id": "41"},
            {"filesystem": "", "readonly": False, "mount_id": "41", "device": "0:47"},
            {"filesystem": "ext4", "readonly": False, "mount_id": "", "device": "0:47"},
            {"filesystem": "ext4", "readonly": False, "mount_id": "41", "device": ""},
        )
        for observation in cases:
            with self.subTest(observation=observation):
                capability_probe = mock.Mock()
                with self.assertRaises(runtime.ContinuityError) as caught:
                    runtime._filesystem_adapter(
                        root,
                        lexical_root=root,
                        platform_name="linux",
                        linux_observer=lambda _probe, value=observation: value,
                        posix_capability_probe=capability_probe,
                    )
                self.assertEqual(caught.exception.code, "filesystem_semantics_unsupported")
                capability_probe.assert_not_called()

    def test_known_remote_and_shared_linux_filesystems_reject(self) -> None:
        root = self.base / "workspace"
        known_shared = (
            "fuse.glusterfs",
            "gfs2",
            "ocfs2",
            "virtiofs",
            "vboxsf",
            "fuse.vmhgfs-fuse",
        )
        for filesystem in known_shared:
            with self.subTest(filesystem=filesystem):
                observed = runtime._parse_linux_mountinfo(
                    "41",
                    f"41 30 0:47 / /srv/shared rw - {filesystem} shared-source rw",
                )
                self.assertTrue(observed["remote"])
                capability_probe = mock.Mock()
                with self.assertRaises(runtime.ContinuityError) as caught:
                    runtime._filesystem_adapter(
                        root,
                        lexical_root=root,
                        platform_name="linux",
                        linux_observer=self.linux_observation(filesystem=filesystem),
                        posix_capability_probe=capability_probe,
                    )
                self.assertEqual(caught.exception.code, "filesystem_semantics_unsupported")
                capability_probe.assert_not_called()

    def test_linux_observer_failures_normalize_to_typed_semantics_errors(self) -> None:
        root = self.base / "workspace"
        for failure in (
            OSError(errno.EIO, "mount observation failed"),
            UnicodeError("mount observation was not decodable"),
            TypeError("mount observation had the wrong shape"),
            ValueError("mount observation was invalid"),
        ):
            with self.subTest(failure=type(failure).__name__):
                observer = mock.Mock(side_effect=failure)
                capability_probe = mock.Mock()
                with self.assertRaises(runtime.ContinuityError) as caught:
                    runtime._filesystem_adapter(
                        root,
                        lexical_root=root,
                        platform_name="linux",
                        linux_observer=observer,
                        posix_capability_probe=capability_probe,
                    )
                self.assertEqual(caught.exception.code, "filesystem_semantics_unsupported")
                observer.assert_called_once()
                capability_probe.assert_not_called()
    def test_windows_adapter_rejects_capability_probe_failure(self) -> None:
        root = self.base / "workspace"

        def fail_probe(_root: Path, _probe: Path) -> None:
            raise OSError(errno.ENOTSUP, "required primitive unavailable")

        with self.assertRaises(runtime.ContinuityError) as caught:
            runtime._filesystem_adapter(
                root,
                lexical_root=root,
                platform_name="win32",
                windows_observer=self.windows_observation(filesystem="FutureFS"),
                windows_capability_probe=fail_probe,
            )
        self.assertEqual(caught.exception.code, "filesystem_semantics_unsupported")

    def test_regular_file_lock_probe_treats_busy_as_supported(self) -> None:
        lock_path = self.base / "workspace.lock"
        lock_path.write_bytes(b"\0")
        with (
            mock.patch.object(runtime, "_try_os_lock", return_value=(False, None)) as attempt,
            mock.patch.object(runtime, "_unlock_os_lock") as unlock,
        ):
            runtime._probe_regular_file_lock(lock_path)
        attempt.assert_called_once()
        unlock.assert_not_called()

    def test_regular_file_lock_probe_requires_independent_exclusion(self) -> None:
        lock_path = self.base / "exclusive-workspace.lock"
        lock_path.write_bytes(b"\0")
        with (
            mock.patch.object(
                runtime,
                "_try_os_lock",
                side_effect=[(True, "primary"), (False, None)],
            ) as attempt,
            mock.patch.object(runtime, "_unlock_os_lock") as unlock,
        ):
            runtime._probe_regular_file_lock(lock_path)
        self.assertEqual(attempt.call_count, 2)
        self.assertEqual(unlock.call_count, 1)
        self.assertEqual(unlock.call_args.args[1], "primary")

    def test_regular_file_lock_probe_rejects_nonexclusive_primitive(self) -> None:
        lock_path = self.base / "nonexclusive-workspace.lock"
        lock_path.write_bytes(b"\0")
        with (
            mock.patch.object(
                runtime,
                "_try_os_lock",
                side_effect=[(True, "primary"), (True, "challenger")],
            ) as attempt,
            mock.patch.object(runtime, "_unlock_os_lock") as unlock,
        ):
            with self.assertRaises(OSError):
                runtime._probe_regular_file_lock(lock_path)
        self.assertEqual(attempt.call_count, 2)
        self.assertEqual(unlock.call_count, 2)
        self.assertEqual(
            {call.args[1] for call in unlock.call_args_list},
            {"primary", "challenger"},
        )
    def test_existing_workspace_capability_probe_uses_permanent_lock_and_replacement(self) -> None:
        root = self.base / "workspace"
        locks = root / "locks"
        locks.mkdir(parents=True)
        lock_path = locks / "workspace.lock"
        lock_path.write_bytes(b"\0")
        replacements: list[tuple[Path, Path]] = []

        def replace_operation(source: Path, destination: Path) -> None:
            replacements.append((source, destination))
            os.replace(source, destination)

        original_probe = runtime._probe_regular_file_lock
        with (
            mock.patch.object(runtime, "_probe_regular_file_lock", wraps=original_probe) as probe_lock,
            mock.patch.object(runtime, "_exclusive_rename", wraps=runtime._exclusive_rename) as exclusive_rename,
            mock.patch.object(runtime, "_fsync_directory") as sync_directory,
        ):
            runtime._filesystem_capability_probe(
                root,
                root,
                replace_operation,
                workspace_root=True,
            )
        self.assertEqual(probe_lock.call_args_list[0].args[0], lock_path)
        self.assertEqual(len(probe_lock.call_args_list), 2)
        self.assertEqual(len(replacements), 1)
        self.assertEqual(exclusive_rename.call_count, 2)
        self.assertEqual(sync_directory.call_args_list[-1].args[0], root)
        self.assertEqual(list(locks.glob(".cc-filesystem-probe-*")), [])

    def test_busy_workspace_lock_performs_no_probe_or_metadata_mutation(self) -> None:
        root = self.base / "busy-lock-workspace"
        stable = {
            "adapter": "test-adapter/v1",
            "platform": sys.platform,
            "device": 17,
            "critical_directory_count": 5,
        }
        with (
            mock.patch.object(runtime, "_filesystem_adapter", return_value="test-adapter/v1"),
            mock.patch.object(runtime, "_filesystem_qualification_witness", return_value=stable),
        ):
            runtime.initialize_workspace(
                str(root),
                user="user",
                project="project",
                agent="nova",
                thread=None,
                sensitivity="ordinary",
                retention="until-user-changes",
            )

        def snapshot() -> dict[str, tuple[str, int, int, bytes | None]]:
            observed: dict[str, tuple[str, int, int, bytes | None]] = {}
            for item in sorted(root.rglob("*"), key=lambda path: path.as_posix()):
                metadata = item.stat()
                observed[item.relative_to(root).as_posix()] = (
                    "directory" if item.is_dir() else "file",
                    int(metadata.st_size),
                    int(metadata.st_mtime_ns),
                    item.read_bytes() if item.is_file() else None,
                )
            return observed

        before = snapshot()
        witness_calls: list[bool] = []

        def observe_witness(
            _root: Path,
            *,
            lexical_root: Path | None = None,
            perform_capability_probe: bool = True,
        ) -> dict[str, object]:
            self.assertEqual(_root, root)
            self.assertEqual(lexical_root, root)
            witness_calls.append(perform_capability_probe)
            return stable

        with (
            mock.patch.object(runtime, "_filesystem_qualification_witness", side_effect=observe_witness),
            mock.patch.object(runtime, "_filesystem_capability_probe") as capability_probe,
            mock.patch.object(runtime, "_try_os_lock", return_value=(False, None)),
        ):
            with self.assertRaises(runtime.ContinuityError) as caught:
                with runtime.workspace_lock(root):
                    self.fail("busy lock unexpectedly entered")
        self.assertEqual(caught.exception.code, "lock_busy")
        self.assertEqual(witness_calls, [False])
        capability_probe.assert_not_called()
        self.assertEqual(snapshot(), before)
        self.assertFalse((root / "locks" / "workspace-owner.json").exists())
    def test_existing_external_targets_probe_their_filesystem_without_residue(self) -> None:
        source = self.base / "source"
        source.mkdir()
        key = self.base / "backup.key"
        key.write_bytes(b"k" * 48)
        directory = self.base / "external-directory"
        directory.mkdir()
        payload = directory / "payload.txt"
        payload.write_text("unchanged", encoding="utf-8")

        with mock.patch.object(runtime, "_filesystem_adapter", wraps=runtime._filesystem_adapter) as adapter:
            resolved_key = runtime.validate_external_target(source, str(key), "Backup key")
            resolved_directory = runtime.validate_external_target(source, str(directory), "Backup directory")

        self.assertEqual(resolved_key, key.resolve())
        self.assertEqual(resolved_directory, directory.resolve())
        self.assertEqual([call.args[0] for call in adapter.call_args_list], [self.base.resolve(), self.base.resolve()])
        self.assertEqual(key.read_bytes(), b"k" * 48)
        self.assertEqual(payload.read_text(encoding="utf-8"), "unchanged")
        self.assertEqual(list(self.base.rglob(".cc-filesystem-probe-*")), [])

    @unittest.skipUnless(
        sys.platform == "win32" or sys.platform == "darwin" or sys.platform.startswith("linux"),
        "qualified mutation host required",
    )
    def test_read_only_external_roles_skip_disposable_probe_while_write_roles_require_it(self) -> None:
        source = self.base / "source"
        source.mkdir()
        key = self.base / "backup-auth.key"
        key_bytes = b"k" * 48
        key.write_bytes(key_bytes)
        output = self.base / "write-output.json"

        def forbidden_probe(*_args: object, **_kwargs: object) -> None:
            raise AssertionError("read-only external input invoked the disposable capability probe")

        read_cases = (
            (
                "direct_read_role",
                lambda: runtime.validate_external_target(
                    source,
                    str(key),
                    "Backup authentication key",
                    require_mutation=False,
                ),
            ),
            (
                "backup_auth_key",
                lambda: store._load_backup_auth_key(source, str(key)),
            ),
        )
        for role, operation in read_cases:
            with self.subTest(role=role):
                before = key.read_bytes()
                with mock.patch.object(
                    runtime,
                    "_filesystem_capability_probe",
                    side_effect=forbidden_probe,
                ) as capability_probe:
                    operation()
                capability_probe.assert_not_called()
                self.assertEqual(key.read_bytes(), before)

        write_cases = (
            (
                "direct_write_role",
                lambda: runtime.validate_external_target(
                    source,
                    str(output),
                    "Write output",
                    must_be_absent=True,
                    require_mutation=True,
                ),
            ),
            (
                "store_write_role",
                lambda: store._outside_source(
                    source,
                    str(output),
                    "Write output",
                    must_be_absent=True,
                ),
            ),
        )
        for role, operation in write_cases:
            with self.subTest(role=role):
                with mock.patch.object(runtime, "_filesystem_capability_probe") as capability_probe:
                    operation()
                capability_probe.assert_called()
    def test_absent_only_external_target_rejects_occupancy_before_probe(self) -> None:
        source = self.base / "source-occupied"
        source.mkdir()
        target = self.base / "already-present.json"
        target.write_text("unowned", encoding="utf-8")
        with mock.patch.object(
            runtime,
            "_filesystem_adapter",
            side_effect=AssertionError("occupied target must be rejected before probing"),
        ) as adapter:
            with self.assertRaises(runtime.ContinuityError) as caught:
                runtime.validate_external_target(
                    source,
                    str(target),
                    "Write output",
                    must_be_absent=True,
                    require_mutation=True,
                )
        self.assertEqual(caught.exception.code, "protected_target_denied")
        adapter.assert_not_called()
        self.assertEqual(target.read_text(encoding="utf-8"), "unowned")

    def test_external_absent_target_race_is_preserved_without_clobber(self) -> None:
        source = self.base / "external-source"
        source.mkdir()
        target = self.base / "racing-output.json"
        with mock.patch.object(runtime, "_filesystem_adapter", return_value="test-adapter/v1"):
            resolved = runtime.validate_external_target(
                source,
                str(target),
                "External output",
                must_be_absent=True,
                require_mutation=True,
            )
        self.assertEqual(resolved, target.resolve())
        racing_bytes = b'{"owner":"racer"}\n'
        target.write_bytes(racing_bytes)
        with self.assertRaises(runtime.ContinuityError) as caught:
            runtime.atomic_new_json(target, {"owner": "continuity"})
        self.assertEqual(caught.exception.code, "protected_target_denied")
        self.assertEqual(target.read_bytes(), racing_bytes)
        self.assertEqual(list(self.base.glob(f".{target.name}.*")), [])
    def test_atomic_no_clobber_publication_preserves_racing_destination(self) -> None:
        source = self.base / "publication-source"
        destination = self.base / "publication-destination"
        source.mkdir()
        (source / "owned.txt").write_text("owned", encoding="utf-8")

        def collide(_source: Path, target: Path) -> None:
            target.mkdir()
            (target / "unowned.txt").write_text("unowned", encoding="utf-8")
            raise FileExistsError(errno.EEXIST, "simulated publication race", str(target))

        with mock.patch.object(runtime, "_exclusive_rename", side_effect=collide):
            with self.assertRaises(runtime.ContinuityError) as caught:
                runtime._publish_directory(source, destination)
        self.assertEqual(caught.exception.code, "recovery_required")
        self.assertEqual((source / "owned.txt").read_text(encoding="utf-8"), "owned")
        self.assertEqual((destination / "unowned.txt").read_text(encoding="utf-8"), "unowned")
    def test_workspace_role_requires_a_direct_permanent_lock(self) -> None:
        root = self.base / "workspace"
        locks = root / "locks"
        locks.mkdir(parents=True)
        with self.assertRaises(OSError):
            runtime._filesystem_capability_probe(
                root,
                root,
                os.replace,
                workspace_root=True,
            )

        external = self.base / "external.lock"
        external.write_bytes(b"\0")
        lock_path = locks / "workspace.lock"
        try:
            lock_path.symlink_to(external)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"host cannot create a symlink for this check: {exc}")
        with self.assertRaises(OSError):
            runtime._filesystem_capability_probe(
                root,
                root,
                os.replace,
                workspace_root=True,
            )
    def test_linux_witness_rejects_missing_and_split_mount_identity(self) -> None:
        root = self.base / "workspace"
        root.mkdir()
        for name in runtime._CRITICAL_FILESYSTEM_DIRECTORIES:
            (root / name).mkdir()

        incomplete = {"filesystem": "futurefs", "readonly": False}
        with (
            mock.patch.object(runtime, "_filesystem_adapter", return_value="linux-test/v1"),
            mock.patch.object(runtime, "_has_reparse_component", return_value=False),
            mock.patch.object(runtime.sys, "platform", "linux"),
            mock.patch.object(runtime, "_linux_filesystem_observation", return_value=incomplete),
        ):
            with self.assertRaises(runtime.ContinuityError) as caught:
                runtime._filesystem_qualification_witness(root)
        self.assertEqual(caught.exception.code, "filesystem_semantics_unsupported")

        def split_observation(path: Path) -> dict[str, object]:
            return {
                "filesystem": "futurefs",
                "readonly": False,
                "mount_id": "42" if Path(path).name == "quarantine" else "41",
                "device": "8:1",
            }

        with (
            mock.patch.object(runtime, "_filesystem_adapter", return_value="linux-test/v1"),
            mock.patch.object(runtime, "_has_reparse_component", return_value=False),
            mock.patch.object(runtime.sys, "platform", "linux"),
            mock.patch.object(runtime, "_linux_filesystem_observation", side_effect=split_observation),
        ):
            with self.assertRaises(runtime.ContinuityError) as caught:
                runtime._filesystem_qualification_witness(root)
        self.assertEqual(caught.exception.code, "filesystem_semantics_unsupported")

    def test_critical_directory_zero_and_nondistinct_identities_reject(self) -> None:
        root = self.base / "critical-file-id-workspace"
        root.mkdir()
        for name in runtime._CRITICAL_FILESYSTEM_DIRECTORIES:
            (root / name).mkdir()
        (root / "locks" / "workspace.lock").write_bytes(b"\0")
        base_inodes = {
            ".": 101,
            "locks": 102,
            "transactions": 103,
            "generations": 104,
            "quarantine": 105,
        }
        cases = (
            ("zero", {**base_inodes, "transactions": 0}),
            ("nondistinct", {**base_inodes, "transactions": base_inodes["locks"]}),
        )
        for label, inodes in cases:
            with self.subTest(case=label):
                def observed_stat(path: str | os.PathLike[str], *_args: object, **_kwargs: object) -> object:
                    candidate = Path(path)
                    key = "." if candidate == root else candidate.name
                    return mock.Mock(
                        st_mode=stat.S_IFDIR | 0o700,
                        st_dev=9,
                        st_ino=inodes[key],
                    )

                with (
                    mock.patch.object(runtime, "_filesystem_adapter", return_value="test-adapter/v1"),
                    mock.patch.object(runtime, "_has_reparse_component", return_value=False),
                    mock.patch.object(runtime, "_direct_regular_file_identity", return_value=(9, 999)),
                    mock.patch.object(runtime.sys, "platform", "test-platform"),
                    mock.patch.object(runtime.os, "stat", side_effect=observed_stat),
                ):
                    with self.assertRaises(runtime.ContinuityError) as caught:
                        runtime._filesystem_qualification_witness(root)
                self.assertEqual(caught.exception.code, "filesystem_semantics_unsupported")

    def test_zero_file_identity_rejects_the_permanent_lock(self) -> None:
        lock_path = self.base / "zero-id-workspace.lock"
        lock_path.write_bytes(b"\0")
        zero_identity = mock.Mock(
            st_mode=stat.S_IFREG | 0o600,
            st_dev=9,
            st_ino=0,
        )
        with (
            mock.patch.object(runtime.os, "lstat", return_value=zero_identity),
            mock.patch.object(runtime, "_has_reparse_component", return_value=False),
        ):
            with self.assertRaises(OSError):
                runtime._direct_regular_file_identity(lock_path)
    def test_critical_filesystem_observer_failures_are_normalized(self) -> None:
        root = self.base / "critical-observer-workspace"
        root.mkdir()
        for name in runtime._CRITICAL_FILESYSTEM_DIRECTORIES:
            (root / name).mkdir()
        (root / "locks" / "workspace.lock").write_bytes(b"\0")
        observers = (
            ("win32", "_windows_filesystem_observation"),
            ("darwin", "_darwin_filesystem_observation"),
            ("linux", "_linux_filesystem_observation"),
        )
        failures = (
            OSError(errno.EIO, "critical mount observation failed"),
            UnicodeError("critical mount observation was not decodable"),
            TypeError("critical mount observation had the wrong shape"),
        )
        for platform_name, observer_name in observers:
            for failure in failures:
                with self.subTest(
                    platform=platform_name,
                    failure=type(failure).__name__,
                ):
                    with (
                        mock.patch.object(runtime, "_filesystem_adapter", return_value=f"{platform_name}-test/v1"),
                        mock.patch.object(runtime, "_has_reparse_component", return_value=False),
                        mock.patch.object(runtime.sys, "platform", platform_name),
                        mock.patch.object(runtime, observer_name, side_effect=failure),
                    ):
                        with self.assertRaises(runtime.ContinuityError) as caught:
                            runtime._filesystem_qualification_witness(root)
                    self.assertEqual(caught.exception.code, "filesystem_semantics_unsupported")

    def test_nonregular_and_indirect_transaction_journals_reject(self) -> None:
        root = self.base / "journal-custody-workspace"
        stable = {
            "adapter": "test-adapter/v1",
            "platform": sys.platform,
            "device": 23,
            "critical_directory_count": 5,
        }
        with (
            mock.patch.object(runtime, "_filesystem_adapter", return_value="test-adapter/v1"),
            mock.patch.object(runtime, "_filesystem_qualification_witness", return_value=stable),
        ):
            runtime.initialize_workspace(
                str(root),
                user="user",
                project="project",
                agent="nova",
                thread=None,
                sensitivity="ordinary",
                retention="until-user-changes",
            )
        direct_entry = root / "transactions" / "TX-direct-journal"
        direct_entry.write_text(
            json.dumps({"format": runtime.TRANSACTION_FORMAT, "state": "intent_recorded"}) + "\n",
            encoding="utf-8",
        )
        with self.assertRaises(runtime.ContinuityError) as direct_entry_error:
            runtime.pending_transactions(root)
        self.assertEqual(direct_entry_error.exception.code, "recovery_required")
        direct_entry.unlink()

        transaction_root = root / "transactions" / "TX-hostile"
        transaction_root.mkdir()
        journal = transaction_root / "journal.json"
        journal.mkdir()
        with self.assertRaises(runtime.ContinuityError) as nonregular:
            runtime.pending_transactions(root)
        self.assertEqual(nonregular.exception.code, "recovery_required")

        journal.rmdir()
        journal.write_text(
            json.dumps({"format": runtime.TRANSACTION_FORMAT, "state": "intent_recorded"}) + "\n",
            encoding="utf-8",
        )
        original_reparse_check = runtime._has_reparse_component

        def indirect_journal(path: Path, boundary: Path | None = None) -> bool:
            if Path(path) == journal:
                return True
            return original_reparse_check(path, boundary)

        with mock.patch.object(runtime, "_has_reparse_component", side_effect=indirect_journal):
            with self.assertRaises(runtime.ContinuityError) as indirect:
                runtime.pending_transactions(root)
        self.assertEqual(indirect.exception.code, "recovery_required")
    def test_transaction_rejects_witness_change_after_lock_without_journal(self) -> None:
        root = self.base / "witness-entry-workspace"
        stable = {
            "adapter": "test-adapter/v1",
            "platform": sys.platform,
            "device": 11,
            "critical_directory_count": 5,
        }
        changed = {**stable, "device": 12}
        with (
            mock.patch.object(runtime, "_filesystem_adapter", return_value="test-adapter/v1"),
            mock.patch.object(runtime, "_filesystem_qualification_witness", return_value=stable),
        ):
            runtime.initialize_workspace(
                str(root),
                user="user",
                project="project",
                agent="nova",
                thread=None,
                sensitivity="ordinary",
                retention="until-user-changes",
            )

        with (
            mock.patch.object(runtime, "_filesystem_adapter", return_value="test-adapter/v1"),
            mock.patch.object(runtime, "_filesystem_qualification_witness", side_effect=[stable, changed]),
        ):
            with self.assertRaises(runtime.ContinuityError) as caught:
                with runtime.transaction(
                    root,
                    "witness-entry",
                    expected_generation=0,
                    selector=str(root),
                    authority="user-stunspot",
                    idempotency_key="witness-entry",
                    request_payload={"purpose": "witness-entry"},
                ):
                    self.fail("transaction entered after a changed filesystem witness")
        self.assertEqual(caught.exception.code, "filesystem_identity_changed")
        self.assertEqual(runtime._read_json_path(root / "manifest.json")["generation"], 0)
        self.assertEqual(list((root / "transactions").iterdir()), [])

    def test_missing_generations_parent_is_not_recreated_during_finish(self) -> None:
        root = self.base / "missing-generations-workspace"
        stable = {
            "adapter": "test-adapter/v1",
            "platform": sys.platform,
            "device": 29,
            "critical_directory_count": 5,
        }
        with (
            mock.patch.object(runtime, "_filesystem_adapter", return_value="test-adapter/v1"),
            mock.patch.object(runtime, "_filesystem_qualification_witness", return_value=stable),
        ):
            runtime.initialize_workspace(
                str(root),
                user="user",
                project="project",
                agent="nova",
                thread=None,
                sensitivity="ordinary",
                retention="until-user-changes",
            )

        def remove_generations(point: str) -> None:
            if point == "before_bundle_publish":
                shutil.rmtree(root / "generations")

        with (
            mock.patch.object(runtime, "_filesystem_qualification_witness", return_value=stable),
            mock.patch.object(runtime, "_crash", side_effect=remove_generations),
        ):
            with self.assertRaises(runtime.ContinuityError) as caught:
                with runtime.transaction(
                    root,
                    "missing-generations",
                    expected_generation=0,
                    selector=str(root),
                    authority="user-stunspot",
                    idempotency_key="missing-generations",
                    request_payload={"purpose": "missing-generations"},
                ) as transaction:
                    transaction.finish(
                        "missing-generations",
                        {"purpose": "missing-generations"},
                    )
        self.assertEqual(caught.exception.code, "filesystem_identity_changed")
        self.assertFalse((root / "generations").exists())
        journals = list((root / "transactions").glob("*/journal.json"))
        self.assertEqual(len(journals), 1)
        self.assertEqual(runtime._read_json_path(journals[0])["state"], "bundle_staged")

    def test_visible_manifest_with_sync_failure_requires_explicit_recovery(self) -> None:
        root = self.base / "manifest-sync-uncertain-workspace"
        stable = {
            "adapter": "test-adapter/v1",
            "platform": sys.platform,
            "device": 37,
            "critical_directory_count": 5,
        }
        with (
            mock.patch.object(runtime, "_filesystem_adapter", return_value="test-adapter/v1"),
            mock.patch.object(runtime, "_filesystem_qualification_witness", return_value=stable),
        ):
            runtime.initialize_workspace(
                str(root),
                user="user",
                project="project",
                agent="nova",
                thread=None,
                sensitivity="ordinary",
                retention="until-user-changes",
            )

        def visible_then_sync_failure(source: Path, destination: Path) -> str:
            os.replace(source, destination)
            raise OSError(errno.EIO, "manifest parent sync failed after visible replace")

        transaction_id = ""
        with (
            mock.patch.object(runtime, "_filesystem_qualification_witness", return_value=stable),
            mock.patch.object(runtime, "_replace_manifest", side_effect=visible_then_sync_failure),
        ):
            with self.assertRaises(runtime.ContinuityError) as caught:
                with runtime.transaction(
                    root,
                    "manifest-sync-uncertain",
                    expected_generation=0,
                    selector=str(root),
                    authority="user-stunspot",
                    idempotency_key="manifest-sync-uncertain",
                    request_payload={"purpose": "manifest-sync-uncertain"},
                ) as transaction:
                    transaction_id = transaction.id
                    transaction.finish(
                        "manifest-sync-uncertain",
                        {"purpose": "manifest-sync-uncertain"},
                    )
        self.assertEqual(caught.exception.code, "manifest_durability_uncertain")
        self.assertEqual(runtime._read_json_path(root / "manifest.json")["generation"], 1)
        self.assertFalse((root / "manifest.next").exists())
        journal_path = root / "transactions" / transaction_id / "journal.json"
        self.assertEqual(runtime._read_json_path(journal_path)["state"], "commit_ready")

        with mock.patch.object(
            runtime,
            "_filesystem_qualification_witness",
            return_value=stable,
        ):
            recovered = runtime.recover_transactions(root)
        self.assertEqual(recovered, [transaction_id])
        recovered_journal = runtime._read_json_path(journal_path)
        self.assertEqual(recovered_journal["state"], "finalized")
        self.assertTrue(recovered_journal["recovery_manifest_republished"])
        self.assertEqual(runtime._read_json_path(root / "manifest.json")["generation"], 1)
        self.assertEqual(runtime.pending_transactions(root), [])
    def test_transaction_revalidates_before_intent_and_generation_publication(self) -> None:
        stable = {
            "adapter": "test-adapter/v1",
            "platform": sys.platform,
            "device": 41,
            "critical_directory_count": 5,
        }
        changed = {**stable, "device": 42}
        cases = (
            ("intent", [stable, stable, stable, changed], None),
            ("generation", [stable, stable, stable, stable, changed], "bundle_staged"),
        )
        for phase, witnesses, expected_state in cases:
            with self.subTest(phase=phase):
                root = self.base / f"witness-{phase}-workspace"
                with (
                    mock.patch.object(runtime, "_filesystem_adapter", return_value="test-adapter/v1"),
                    mock.patch.object(runtime, "_filesystem_qualification_witness", return_value=stable),
                ):
                    runtime.initialize_workspace(
                        str(root),
                        user="user",
                        project="project",
                        agent="nova",
                        thread=None,
                        sensitivity="ordinary",
                        retention="until-user-changes",
                    )
                with (
                    mock.patch.object(runtime, "_filesystem_adapter", return_value="test-adapter/v1"),
                    mock.patch.object(runtime, "_filesystem_qualification_witness", side_effect=witnesses),
                ):
                    with self.assertRaises(runtime.ContinuityError) as caught:
                        with runtime.transaction(
                            root,
                            f"witness-{phase}",
                            expected_generation=0,
                            selector=str(root),
                            authority="user-stunspot",
                            idempotency_key=f"witness-{phase}",
                            request_payload={"purpose": phase},
                        ) as transaction:
                            transaction.finish(f"witness-{phase}", {"purpose": phase})
                self.assertEqual(caught.exception.code, "filesystem_identity_changed")
                journals = list((root / "transactions").glob("*/journal.json"))
                if expected_state is None:
                    self.assertEqual(journals, [])
                else:
                    self.assertEqual(len(journals), 1)
                    self.assertEqual(runtime._read_json_path(journals[0])["state"], expected_state)
                    self.assertFalse((root / "generations" / "g-00000000000000000001").exists())

    def test_transaction_normalizes_witness_errors_and_defers_exit_recovery(self) -> None:
        stable = {
            "adapter": "test-adapter/v1",
            "platform": sys.platform,
            "device": 43,
            "critical_directory_count": 5,
        }
        failures = (
            (
                "semantics",
                runtime.ContinuityError(
                    "filesystem observation failed",
                    "filesystem_semantics_unsupported",
                ),
            ),
            (
                "reparse",
                runtime.ContinuityError(
                    "filesystem custody changed",
                    "custody_reparse_escape",
                ),
            ),
            (
                "oserror",
                OSError(errno.ESTALE, "filesystem witness unavailable"),
            ),
        )
        for label, failure in failures:
            with self.subTest(failure=label):
                root = self.base / f"witness-error-{label}"
                with (
                    mock.patch.object(runtime, "_filesystem_adapter", return_value="test-adapter/v1"),
                    mock.patch.object(runtime, "_filesystem_qualification_witness", return_value=stable),
                ):
                    runtime.initialize_workspace(
                        str(root),
                        user="user",
                        project="project",
                        agent="nova",
                        thread=None,
                        sensitivity="ordinary",
                        retention="until-user-changes",
                    )

                observed: BaseException | None = None
                with mock.patch.object(
                    runtime,
                    "_filesystem_qualification_witness",
                    side_effect=[stable, stable, stable, stable, failure],
                ):
                    try:
                        with runtime.transaction(
                            root,
                            f"witness-error-{label}",
                            expected_generation=0,
                            selector=str(root),
                            authority="user-stunspot",
                            idempotency_key=f"witness-error-{label}",
                            request_payload={"purpose": label},
                        ) as transaction:
                            transaction.finish(
                                f"witness-error-{label}",
                                {"purpose": label},
                            )
                    except BaseException as exc:
                        observed = exc

                journals = list((root / "transactions").glob("*/journal.json"))
                self.assertEqual(len(journals), 1)
                self.assertEqual(
                    runtime._read_json_path(journals[0])["state"],
                    "bundle_staged",
                )
                self.assertIsInstance(observed, runtime.ContinuityError)
                self.assertEqual(
                    getattr(observed, "code", None),
                    "filesystem_identity_changed",
                )
                self.assertEqual(
                    runtime._read_json_path(root / "manifest.json")["generation"],
                    0,
                )
                self.assertFalse(
                    (root / "generations" / "g-00000000000000000001").exists()
                )
    def test_witness_binds_each_critical_directory_identity(self) -> None:
        root = self.base / "critical-identity-workspace"
        root.mkdir()
        for name in runtime._CRITICAL_FILESYSTEM_DIRECTORIES:
            (root / name).mkdir()
        (root / "locks" / "workspace.lock").write_bytes(b"\0")

        observation = {
            "filesystem": "futurefs",
            "readonly": False,
            "remote": False,
            "ephemeral": False,
            "volatile": False,
            "mount_id": "41",
            "device": "0:47",
        }
        with (
            mock.patch.object(runtime, "_filesystem_adapter", return_value="linux-test/v1"),
            mock.patch.object(runtime.sys, "platform", "linux"),
            mock.patch.object(runtime, "_linux_filesystem_observation", return_value=observation),
        ):
            before = runtime._filesystem_qualification_witness(root)
            original = root / "transactions-original"
            (root / "transactions").rename(original)
            (root / "transactions").mkdir()
            after = runtime._filesystem_qualification_witness(root)

        self.assertEqual(before["device"], after["device"])
        self.assertNotEqual(
            before["critical_directory_identities"]["transactions"],
            after["critical_directory_identities"]["transactions"],
        )
        self.assertNotEqual(before, after)

    def test_exit_recovery_defers_on_changed_witness_even_for_unrelated_error(self) -> None:
        root = self.base / "exit-witness-workspace"
        stable = {
            "adapter": "test-adapter/v1",
            "platform": sys.platform,
            "device": 61,
            "critical_directory_count": 5,
        }
        changed = {**stable, "device": 62}
        with (
            mock.patch.object(runtime, "_filesystem_adapter", return_value="test-adapter/v1"),
            mock.patch.object(runtime, "_filesystem_qualification_witness", return_value=stable),
        ):
            runtime.initialize_workspace(
                str(root),
                user="user",
                project="project",
                agent="nova",
                thread=None,
                sensitivity="ordinary",
                retention="until-user-changes",
            )

        observed: BaseException | None = None
        with (
            mock.patch.object(runtime, "_filesystem_adapter", return_value="test-adapter/v1"),
            mock.patch.object(
                runtime,
                "_filesystem_qualification_witness",
                side_effect=[stable, stable, stable, stable, changed],
            ),
        ):
            try:
                with runtime.transaction(
                    root,
                    "exit-witness",
                    expected_generation=0,
                    selector=str(root),
                    authority="user-stunspot",
                    idempotency_key="exit-witness",
                    request_payload={"purpose": "exit-witness"},
                ) as transaction:
                    transaction._record_intent()
                    raise ValueError("unrelated failure")
            except BaseException as exc:
                observed = exc

        self.assertIsInstance(observed, runtime.ContinuityError)
        self.assertEqual(getattr(observed, "code", None), "filesystem_identity_changed")
        journals = list((root / "transactions").glob("*/journal.json"))
        self.assertEqual(len(journals), 1)
        self.assertEqual(runtime._read_json_path(journals[0])["state"], "intent_recorded")
        self.assertEqual(runtime._read_json_path(root / "manifest.json")["generation"], 0)
    def test_committed_journal_binds_the_exact_filesystem_witness(self) -> None:
        root = self.base / "witness-journal-workspace"
        stable = {
            "adapter": "test-adapter/v1",
            "platform": sys.platform,
            "device": 51,
            "critical_directory_count": 5,
            "mount_identity": "controlled-test",
        }
        with (
            mock.patch.object(runtime, "_filesystem_adapter", return_value="test-adapter/v1"),
            mock.patch.object(runtime, "_filesystem_qualification_witness", return_value=stable),
        ):
            runtime.initialize_workspace(
                str(root),
                user="user",
                project="project",
                agent="nova",
                thread=None,
                sensitivity="ordinary",
                retention="until-user-changes",
            )
            with runtime.transaction(
                root,
                "witness-journal",
                expected_generation=0,
                selector=str(root),
                authority="user-stunspot",
                idempotency_key="witness-journal",
                request_payload={"purpose": "witness-journal"},
            ) as transaction:
                transaction.finish("witness-journal", {"purpose": "witness-journal"})
        journals = list((root / "transactions").glob("*/journal.json"))
        self.assertEqual(len(journals), 1)
        journal = runtime._read_json_path(journals[0])
        self.assertEqual(journal["state"], "finalized")
        self.assertEqual(journal["runtime_identities"]["filesystem_witness"], stable)
    def test_transaction_rejects_witness_change_before_manifest_and_recovers(self) -> None:
        root = self.base / "witness-commit-workspace"
        stable = {
            "adapter": "test-adapter/v1",
            "platform": sys.platform,
            "device": 21,
            "critical_directory_count": 5,
        }
        changed = {**stable, "device": 22}
        with (
            mock.patch.object(runtime, "_filesystem_adapter", return_value="test-adapter/v1"),
            mock.patch.object(runtime, "_filesystem_qualification_witness", return_value=stable),
        ):
            runtime.initialize_workspace(
                str(root),
                user="user",
                project="project",
                agent="nova",
                thread=None,
                sensitivity="ordinary",
                retention="until-user-changes",
            )

        with (
            mock.patch.object(runtime, "_filesystem_adapter", return_value="test-adapter/v1"),
            mock.patch.object(
                runtime,
                "_filesystem_qualification_witness",
                side_effect=[stable, stable, stable, stable, stable, changed],
            ),
        ):
            with self.assertRaises(runtime.ContinuityError) as caught:
                with runtime.transaction(
                    root,
                    "witness-commit",
                    expected_generation=0,
                    selector=str(root),
                    authority="user-stunspot",
                    idempotency_key="witness-commit",
                    request_payload={"purpose": "witness-commit"},
                ) as transaction:
                    transaction.finish("witness-commit", {"purpose": "witness-commit"})
        self.assertEqual(caught.exception.code, "filesystem_identity_changed")
        manifest = runtime._read_json_path(root / "manifest.json")
        self.assertEqual(manifest["generation"], 0)
        journals = list((root / "transactions").glob("*/journal.json"))
        self.assertEqual(len(journals), 1)
        self.assertEqual(runtime._read_json_path(journals[0])["state"], "commit_ready")
        self.assertTrue((root / "manifest.next").is_file())
        self.assertTrue((root / "generations" / "g-00000000000000000001").is_dir())

        journal_before = journals[0].read_bytes()
        manifest_next_before = (root / "manifest.next").read_bytes()
        published_before = runtime.tree_digest(
            root / "generations" / "g-00000000000000000001"
        )
        with (
            mock.patch.object(runtime, "_filesystem_adapter", return_value="test-adapter/v1"),
            mock.patch.object(runtime, "_filesystem_qualification_witness", return_value=changed),
        ):
            with self.assertRaises(runtime.ContinuityError) as automatic:
                with runtime.transaction(
                    root,
                    "automatic-recovery-must-not-rebind",
                    expected_generation=0,
                    selector=str(root),
                    authority="user-stunspot",
                    idempotency_key="automatic-recovery-must-not-rebind",
                    request_payload={"purpose": "automatic-recovery-must-not-rebind"},
                ):
                    self.fail("automatic recovery should reject before entering")
        self.assertEqual(automatic.exception.code, "filesystem_identity_changed")
        self.assertEqual(journals[0].read_bytes(), journal_before)
        self.assertEqual((root / "manifest.next").read_bytes(), manifest_next_before)
        self.assertEqual(
            runtime.tree_digest(root / "generations" / "g-00000000000000000001"),
            published_before,
        )

        with (
            mock.patch.object(runtime, "_filesystem_adapter", return_value="test-adapter/v1"),
            mock.patch.object(runtime, "_filesystem_qualification_witness", return_value=changed),
        ):
            recovered = runtime.recover_transactions(root)
        self.assertEqual(len(recovered), 1)
        self.assertEqual(runtime._read_json_path(root / "manifest.json")["generation"], 0)
        self.assertFalse((root / "manifest.next").exists())
        self.assertFalse((root / "generations" / "g-00000000000000000001").exists())
        recovered_journal = runtime._read_json_path(journals[0])
        self.assertEqual(recovered_journal["state"], "aborted")
        self.assertTrue(recovered_journal["filesystem_witness_rebound"])
        self.assertEqual(recovered_journal["original_filesystem_witness"], stable)
        self.assertEqual(recovered_journal["recovery_filesystem_witness"], changed)
        self.assertTrue(any((root / "quarantine").rglob("*")))

    def test_failed_root_parent_sync_removes_incomplete_initialization(self) -> None:
        root = self.base / "root-publication-workspace"
        stable = {
            "adapter": "test-adapter/v1",
            "platform": sys.platform,
            "device": 31,
            "critical_directory_count": 5,
        }
        original_sync = runtime._fsync_directory

        def fail_parent_publication(path: Path) -> None:
            if Path(path) == root.parent:
                raise OSError(errno.EIO, "root parent sync failed")
            original_sync(path)

        with (
            mock.patch.object(runtime, "_filesystem_adapter", return_value="test-adapter/v1"),
            mock.patch.object(runtime, "_filesystem_qualification_witness", return_value=stable),
            mock.patch.object(runtime, "_fsync_directory", side_effect=fail_parent_publication),
        ):
            with self.assertRaises(runtime.ContinuityError) as caught:
                runtime.initialize_workspace(
                    str(root),
                    user="user",
                    project="project",
                    agent="nova",
                    thread=None,
                    sensitivity="ordinary",
                    retention="until-user-changes",
                )
        self.assertEqual(caught.exception.code, "recovery_required")
        self.assertFalse(root.exists())
        retained = list(self.base.glob(f".{root.name}.cc-initialize-*"))
        self.assertEqual(len(retained), 1)
        self.assertTrue((retained[0] / "manifest.json").is_file())
    def test_initialize_and_migrate_preserve_unowned_racing_destinations(self) -> None:
        stable = {
            "adapter": "test-adapter/v1",
            "platform": sys.platform,
            "device": 71,
            "critical_directory_count": 5,
        }
        original_publish = runtime._publish_directory

        initialization_root = self.base / "initialization-race-workspace"

        def race_initialization(source: Path, destination: Path) -> str:
            if Path(destination) == initialization_root:
                destination.mkdir()
                (destination / "unowned.txt").write_text("initialization-racer", encoding="utf-8")
            return original_publish(source, destination)

        with (
            mock.patch.object(runtime, "_filesystem_adapter", return_value="test-adapter/v1"),
            mock.patch.object(runtime, "_filesystem_qualification_witness", return_value=stable),
            mock.patch.object(runtime, "_publish_directory", side_effect=race_initialization),
        ):
            with self.assertRaises(runtime.ContinuityError) as initialization_error:
                runtime.initialize_workspace(
                    str(initialization_root),
                    user="user",
                    project="project",
                    agent="nova",
                    thread=None,
                    sensitivity="ordinary",
                    retention="until-user-changes",
                )
        self.assertEqual(
            (initialization_root / "unowned.txt").read_text(encoding="utf-8"),
            "initialization-racer",
        )
        self.assertEqual(initialization_error.exception.code, "recovery_required")
        retained_initializations = list(
            self.base.glob(f".{initialization_root.name}.cc-initialize-*")
        )
        self.assertEqual(len(retained_initializations), 1)
        self.assertTrue((retained_initializations[0] / "manifest.json").is_file())

        legacy = self.base / "migration-race-source"
        initialized = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "continuity_store.py"),
                "init",
                str(legacy),
                "--user",
                "user",
                "--project",
                "project",
                "--agent",
                "nova",
            ],
            text=True,
            capture_output=True,
            timeout=30,
        )
        self.assertEqual(initialized.returncode, 0, initialized.stderr)
        source_digest = runtime.tree_digest(legacy)
        migration_destination = self.base / "migration-race-workspace"

        def race_migration(source: Path, destination: Path) -> str:
            if Path(destination) == migration_destination:
                destination.mkdir()
                (destination / "unowned.txt").write_text("migration-racer", encoding="utf-8")
            return original_publish(source, destination)

        with (
            mock.patch.object(runtime, "_filesystem_adapter", return_value="test-adapter/v1"),
            mock.patch.object(runtime, "_filesystem_qualification_witness", return_value=stable),
            mock.patch.object(runtime, "_publish_directory", side_effect=race_migration),
        ):
            with self.assertRaises(runtime.ContinuityError) as migration_error:
                runtime.migrate_copy(
                    str(legacy),
                    str(migration_destination),
                    authority="user-stunspot",
                    expected_source_tree_sha256=source_digest,
                )
        self.assertEqual(
            (migration_destination / "unowned.txt").read_text(encoding="utf-8"),
            "migration-racer",
        )
        self.assertEqual(migration_error.exception.code, "recovery_required")
        retained_migrations = list(
            self.base.glob(f".{migration_destination.name}.cc-migrate-*")
        )
        self.assertEqual(len(retained_migrations), 1)
        self.assertTrue((retained_migrations[0] / "manifest.json").is_file())
        self.assertEqual(runtime.tree_digest(legacy), source_digest)
    def test_initialize_and_migrate_require_an_existing_exact_parent(self) -> None:
        initialization_ancestor = self.base / "missing-initialize-ancestor"
        initialization_root = initialization_ancestor / "nested" / "workspace"
        initialization_error: BaseException | None = None
        with mock.patch.object(runtime, "_filesystem_adapter", return_value="test-adapter/v1"):
            try:
                runtime.initialize_workspace(
                    str(initialization_root),
                    user="user",
                    project="project",
                    agent="nova",
                    thread=None,
                    sensitivity="ordinary",
                    retention="until-user-changes",
                )
            except BaseException as exc:
                initialization_error = exc
        with self.subTest(operation="initialize", assertion="typed_failure"):
            self.assertIsInstance(initialization_error, runtime.ContinuityError)
        with self.subTest(operation="initialize", assertion="zero_ancestor_creation"):
            self.assertFalse(initialization_ancestor.exists())

        legacy = self.base / "legacy-source"
        initialized = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "continuity_store.py"),
                "init",
                str(legacy),
                "--user",
                "user",
                "--project",
                "project",
                "--agent",
                "nova",
            ],
            text=True,
            capture_output=True,
            timeout=30,
        )
        self.assertEqual(initialized.returncode, 0, initialized.stderr)
        legacy_manifest_path = legacy / "manifest.json"
        legacy_manifest = json.loads(legacy_manifest_path.read_text(encoding="utf-8"))
        legacy_manifest["version"] = "0.2.0"
        legacy_manifest["policies"]["scope_model"] = "harness-global"
        legacy_manifest["capabilities"]["transactional_init"] = True
        legacy_manifest_path.write_text(
            json.dumps(legacy_manifest, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        source_digest = runtime.tree_digest(legacy)
        migration_ancestor = self.base / "missing-migration-ancestor"
        migration_destination = migration_ancestor / "nested" / "workspace"
        migration_error: BaseException | None = None
        with (
            mock.patch.object(runtime, "_filesystem_adapter", return_value="test-adapter/v1"),
            mock.patch.object(
                runtime,
                "_filesystem_qualification_witness",
                return_value={
                    "adapter": "test-adapter/v1",
                    "platform": sys.platform,
                    "device": 47,
                    "critical_directory_count": 5,
                },
            ),
        ):
            try:
                runtime.migrate_copy(
                    str(legacy),
                    str(migration_destination),
                    authority="user-stunspot",
                    expected_source_tree_sha256=source_digest,
                )
            except BaseException as exc:
                migration_error = exc
        with self.subTest(operation="migrate", assertion="typed_failure"):
            self.assertIsInstance(migration_error, runtime.ContinuityError)
        with self.subTest(operation="migrate", assertion="zero_ancestor_creation"):
            self.assertFalse(migration_ancestor.exists())
        self.assertEqual(runtime.tree_digest(legacy), source_digest)
    def test_unknown_linux_filesystem_still_obeys_observed_hazards(self) -> None:
        root = self.base / "workspace"
        for hazard in ("remote", "ephemeral", "volatile"):
            with self.subTest(hazard=hazard):
                options = {hazard: True}
                with self.assertRaises(runtime.ContinuityError) as caught:
                    runtime._filesystem_adapter(
                        root,
                        lexical_root=root,
                        platform_name="linux",
                        linux_observer=self.linux_observation(filesystem="futurefs", **options),
                        posix_capability_probe=self.no_op_capability,
                    )
                self.assertEqual(caught.exception.code, "filesystem_semantics_unsupported")

    def test_linux_mountinfo_parser_classifies_volatile_remote_and_ephemeral_mounts(self) -> None:
        for option, location in (
            ("volatile", "mount"),
            ("fsync=volatile", "mount"),
            ("fsync=off", "mount"),
            ("volatile", "super"),
            ("fsync=volatile", "super"),
            ("fsync=off", "super"),
        ):
            with self.subTest(option=option, location=location):
                mount_options = f"rw,{option}" if location == "mount" else "rw"
                super_options = f"rw,{option}" if location == "super" else "rw"
                line = f"41 30 0:45 / / {mount_options} - overlay overlay {super_options}"
                observed = runtime._parse_linux_mountinfo("41", line)
                self.assertTrue(observed["volatile"])
                self.assertEqual(observed["mount_id"], "41")
                self.assertEqual(observed["device"], "0:45")

        nfs = runtime._parse_linux_mountinfo(
            "42",
            "42 30 0:46 / /mnt/nfs rw - nfs server:/export rw",
        )
        tmpfs = runtime._parse_linux_mountinfo(
            "43",
            "43 30 0:47 / /run/cache rw - tmpfs tmpfs rw",
        )
        future = runtime._parse_linux_mountinfo(
            "44",
            "44 30 8:1 / /srv/data rw - futurefs /dev/example rw",
        )
        self.assertTrue(nfs["remote"])
        self.assertTrue(tmpfs["ephemeral"])
        self.assertFalse(future["remote"])
        self.assertFalse(future["ephemeral"])
        self.assertFalse(future["volatile"])

    def test_windows_and_darwin_witnesses_reject_critical_mount_identity_splits(self) -> None:
        root = self.base / "workspace"
        root.mkdir()
        for name in runtime._CRITICAL_FILESYSTEM_DIRECTORIES:
            (root / name).mkdir()

        def windows_observation(path: Path) -> dict[str, object]:
            return {
                "filesystem": "FutureFS",
                "flags": 0,
                "drive_type": 3,
                "volume_path": "X:\\",
                "volume_serial": 202 if Path(path).name == "quarantine" else 101,
            }

        with (
            mock.patch.object(runtime, "_filesystem_adapter", return_value="windows-test/v1"),
            mock.patch.object(runtime, "_has_reparse_component", return_value=False),
            mock.patch.object(runtime.sys, "platform", "win32"),
            mock.patch.object(runtime, "_windows_filesystem_observation", side_effect=windows_observation),
        ):
            with self.assertRaises(runtime.ContinuityError) as caught:
                runtime._filesystem_qualification_witness(root)
        self.assertEqual(caught.exception.code, "filesystem_semantics_unsupported")

        def darwin_observation(path: Path) -> dict[str, object]:
            return {
                "filesystem": "futurefs",
                "flags": runtime._DARWIN_MNT_LOCAL,
                "fsid": (8, 2) if Path(path).name == "quarantine" else (8, 1),
                "mount_point": "/continuity",
                "mounted_from": "/dev/example",
            }

        with (
            mock.patch.object(runtime, "_filesystem_adapter", return_value="darwin-test/v1"),
            mock.patch.object(runtime, "_has_reparse_component", return_value=False),
            mock.patch.object(runtime.sys, "platform", "darwin"),
            mock.patch.object(runtime, "_darwin_filesystem_observation", side_effect=darwin_observation),
        ):
            with self.assertRaises(runtime.ContinuityError) as caught:
                runtime._filesystem_qualification_witness(root)
        self.assertEqual(caught.exception.code, "filesystem_semantics_unsupported")
    def test_cloud_brand_in_path_does_not_override_observed_capabilities(self) -> None:
        root = self.base / "Dropbox" / "OneDrive" / "Box" / "workspace"
        adapter = runtime._filesystem_adapter(
            root,
            lexical_root=root,
            platform_name="linux",
            linux_observer=self.linux_observation(filesystem="futurefs"),
            posix_capability_probe=self.no_op_capability,
        )
        self.assertEqual(adapter, "linux-fcntl-flock-fsync-rename-parent-fsync/v1")

    def test_mutation_support_exposes_linux_qualification(self) -> None:
        root = self.base / "workspace"
        support = runtime.mutation_filesystem_support(
            root,
            lexical_root=root,
            platform_name="linux",
            linux_observer=self.linux_observation(filesystem="futurefs"),
            posix_capability_probe=self.no_op_capability,
        )
        self.assertEqual(
            support,
            {
                "status": "preflight_supported",
                "adapter": "linux-fcntl-flock-fsync-rename-parent-fsync/v1",
                "transaction_probe_required": True,
            },
        )

    def test_adapter_checks_lexical_path_before_resolved_identity(self) -> None:
        root = self.base / "resolved" / "workspace"
        lexical = self.base / "alias" / "workspace"
        with (
            mock.patch.object(runtime, "_has_reparse_component", side_effect=lambda path, boundary=None: Path(path) == lexical),
            mock.patch.object(runtime, "_same_path_identity", return_value=True),
        ):
            with self.assertRaises(runtime.ContinuityError) as caught:
                runtime._filesystem_adapter(
                    root,
                    lexical_root=lexical,
                    platform_name="darwin",
                    darwin_observer=self.darwin_observation(),
                    posix_capability_probe=self.no_op_capability,
                )
        self.assertEqual(caught.exception.code, "custody_reparse_escape")

    def test_broken_symlink_is_an_indirect_edge_when_host_allows_creation(self) -> None:
        target = self.base / "missing-target"
        link = self.base / "broken-link"
        try:
            link.symlink_to(target, target_is_directory=True)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"host cannot create a symlink for this check: {exc}")
        self.assertTrue(runtime._has_reparse_component(link))

    def test_full_fsync_seam_uses_darwin_command_and_has_typed_fallback(self) -> None:
        fcntl_module = mock.Mock()
        self.assertTrue(runtime._darwin_full_fsync(17, fcntl_module))
        fcntl_module.fcntl.assert_called_once_with(17, runtime._F_FULLFSYNC)

        interrupted = mock.Mock()
        interrupted.fcntl.side_effect = [OSError(errno.EINTR, "interrupted"), 0]
        self.assertTrue(runtime._darwin_full_fsync(18, interrupted))
        self.assertEqual(interrupted.fcntl.call_count, 2)

        unavailable = mock.Mock()
        unavailable.fcntl.side_effect = OSError(errno.EINVAL, "not supported")
        self.assertFalse(runtime._darwin_full_fsync(19, unavailable))

    def test_manifest_publication_orders_fullfsync_before_rename_and_parent_fsync(self) -> None:
        source = self.base / "manifest.next"
        destination = self.base / "manifest.json"
        source.write_text('{"generation": 1}\n', encoding="utf-8")
        destination.write_text('{"generation": 0}\n', encoding="utf-8")
        events: list[str] = []

        def full_fsync(_descriptor: int) -> bool:
            events.append("F_FULLFSYNC")
            return True

        def replace(left: Path, right: Path) -> None:
            events.append("rename")
            os.replace(left, right)

        def sync_directory(_path: Path) -> None:
            events.append("parent_fsync")

        adapter = runtime._replace_manifest(
            source,
            destination,
            platform_name="darwin",
            full_fsync_operation=full_fsync,
            replace_operation=replace,
            directory_sync=sync_directory,
        )
        self.assertEqual(events, ["F_FULLFSYNC", "rename", "parent_fsync"])
        self.assertEqual(adapter, "darwin-F_FULLFSYNC-rename-parent-fsync/v1")
        self.assertEqual(json.loads(destination.read_text(encoding="utf-8"))["generation"], 1)

    def test_initial_manifest_is_validated_before_atomic_root_publication(self) -> None:
        root = self.base / "initial-sync-workspace"
        events: list[Path] = []
        events_before_publication: list[Path] = []
        publication: list[tuple[Path, Path]] = []
        original_publish = runtime._publish_directory

        def record_publication(source: Path, destination: Path) -> str:
            events_before_publication.extend(events)
            publication.append((Path(source), Path(destination)))
            return original_publish(source, destination)

        with (
            mock.patch.object(runtime, "_filesystem_adapter", return_value="test-adapter/v1"),
            mock.patch.object(runtime, "_fsync_directory", side_effect=lambda path: events.append(Path(path))),
            mock.patch.object(runtime, "_publish_directory", side_effect=record_publication),
        ):
            runtime.initialize_workspace(
                str(root),
                user="user",
                project="project",
                agent="nova",
                thread=None,
                sensitivity="ordinary",
                retention="until-user-changes",
            )
        self.assertEqual(len(publication), 1)
        construction, destination = publication[0]
        self.assertEqual(destination, root)
        generation_root = construction / "generations" / "g-00000000000000000000"
        expected_syncs = (
            [generation_root, generation_root.parent, construction.parent]
            if sys.platform == "win32"
            else [generation_root, generation_root.parent, construction, construction.parent]
        )
        self.assertEqual(events_before_publication[-len(expected_syncs):], expected_syncs)
        self.assertTrue((root / "manifest.json").is_file())
        self.assertFalse(construction.exists())
        self.assertEqual(list(self.base.glob(".initial-sync-workspace.cc-initialize-*")), [])
    def test_generation_publication_precedes_manifest_replacement(self) -> None:
        root = self.base / "transaction-sync-workspace"
        with mock.patch.object(runtime, "_filesystem_adapter", return_value="test-adapter/v1"):
            runtime.initialize_workspace(
                str(root),
                user="user",
                project="project",
                agent="nova",
                thread=None,
                sensitivity="ordinary",
                retention="until-user-changes",
            )
            token = runtime.open_workspace(str(root), writable=False)[1]
            events: list[str] = []
            original_publish = runtime._publish_directory
            original_replace = runtime._replace_manifest

            def record_publish(source: Path, destination: Path) -> str:
                event = "generation_publish" if Path(destination).parent == root / "generations" else "intent_publish"
                events.append(event)
                return original_publish(source, destination)

            def record_replace(*args: object, **kwargs: object) -> str:
                events.append("manifest_replace")
                return original_replace(*args, **kwargs)

            with (
                mock.patch.object(runtime, "_publish_directory", side_effect=record_publish),
                mock.patch.object(runtime, "_replace_manifest", side_effect=record_replace),
            ):
                with runtime.transaction(
                    root,
                    "sync-order",
                    expected_generation=0,
                    selector=token,
                    authority="user-stunspot",
                    idempotency_key="sync-order",
                    request_payload={"purpose": "sync-order"},
                ) as tx:
                    tx.finish("sync-order", {"purpose": "sync-order"})
        self.assertEqual(events, ["intent_publish", "generation_publish", "manifest_replace"])

    def test_posix_directory_publication_syncs_destination_then_source_parent(self) -> None:
        source_parent = self.base / "source-parent"
        destination_parent = self.base / "destination-parent"
        source_parent.mkdir()
        destination_parent.mkdir()
        source = source_parent / "stage"
        destination = destination_parent / "published"
        source.mkdir()
        events: list[tuple[str, Path | None]] = []
        original_rename = os.rename

        def exclusive_rename(left: Path, right: Path) -> None:
            events.append(("exclusive_rename", None))
            original_rename(left, right)

        def sync(path: Path) -> None:
            events.append(("sync", Path(path)))

        with (
            mock.patch.object(runtime.sys, "platform", "linux"),
            mock.patch.object(runtime, "_exclusive_rename", side_effect=exclusive_rename),
            mock.patch.object(runtime, "_fsync_directory", side_effect=sync),
        ):
            adapter = runtime._publish_directory(source, destination)
        self.assertEqual(adapter, "linux-renameat2-RENAME_NOREPLACE-parent-fsync/v1")
        self.assertEqual(
            events,
            [("exclusive_rename", None), ("sync", destination_parent), ("sync", source_parent)],
        )
    def test_lifecycle_quarantine_and_delete_each_sync_the_parent(self) -> None:
        parent = self.base / "lifecycle-parent"
        target = parent / "artifact"
        target.mkdir(parents=True)
        (target / "payload.txt").write_text("payload", encoding="utf-8")
        receipt_path = parent / "receipt.json"
        receipt = store._lifecycle_receipt_base(
            operation="delete-named-custody",
            authority="user-stunspot",
            workspace_id="CCW-test",
            plan_id="FGP-test",
            plan_digest="a" * 64,
            target_class="quarantine",
            target=target,
            target_digest=store._artifact_digest(target),
            receipt_output=receipt_path,
        )
        events: list[Path] = []

        def emit_phase(path: Path, value: dict[str, object]) -> tuple[int, int]:
            value["updated_at"] = runtime.utc_now()
            path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")
            metadata = path.stat()
            return int(metadata.st_dev), int(metadata.st_ino)

        with (
            mock.patch.object(store, "_emit_lifecycle_receipt", side_effect=emit_phase),
            mock.patch.object(runtime, "_fsync_directory", side_effect=lambda path: events.append(Path(path))),
            mock.patch.object(store, "_fsync_directory", side_effect=lambda path: events.append(Path(path))),
        ):
            result = store._execute_lifecycle_delete(target, receipt_path, receipt)
        self.assertFalse(target.exists())
        self.assertEqual(events, [parent, parent])
        self.assertTrue(result["lifecycle_outcomes"]["deleted_from_named_continuity_custody"])
    def test_access_report_separates_read_support_from_mutation_qualification(self) -> None:
        root = self.base / "workspace"
        selector = runtime.ResolutionToken(
            mode="generic_explicit",
            selected_root=str(root),
            selected_lexical=str(root),
            provenance="generic_explicit",
        )
        unsupported = {"status": "unsupported", "reason_code": "filesystem_semantics_unsupported"}
        with mock.patch.object(store, "mutation_filesystem_support", return_value=unsupported):
            v2 = store.workspace_access_support(root, selector, runtime.FORMAT)
        self.assertEqual(v2["read"]["status"], "supported")
        self.assertFalse(v2["read"]["mutation_qualification_required"])
        self.assertEqual(v2["mutation"], unsupported)

        qualified = {"status": "qualified", "adapter": "test-adapter/v1"}
        with mock.patch.object(store, "mutation_filesystem_support", return_value=qualified):
            v1 = store.workspace_access_support(root, selector, runtime.LEGACY_FORMAT)
        self.assertEqual(v1["read"]["status"], "supported")
        self.assertEqual(v1["mutation"]["status"], "unsupported")
        self.assertEqual(v1["mutation"]["reason_code"], "migration_required_for_mutation")
        self.assertEqual(v1["mutation"]["filesystem_qualification"], qualified)

    @unittest.skipUnless(
        sys.platform == "win32" or sys.platform == "darwin" or sys.platform.startswith("linux"),
        "qualified mutation host required",
    )
    def test_open_report_is_read_only_and_reports_mutation_preflight_separately(self) -> None:
        root = self.base / "workspace"
        runtime.initialize_workspace(
            str(root),
            user="user",
            project="project",
            agent="nova",
            thread=None,
            sensitivity="ordinary",
            retention="until-user-changes",
        )
        before = runtime.tree_digest(root)
        report = store.cmd_open(argparse.Namespace(workspace=str(root)))
        self.assertEqual(report["access_support"]["read"]["status"], "supported")
        self.assertEqual(report["access_support"]["mutation"]["status"], "preflight_supported")
        self.assertTrue(report["access_support"]["mutation"]["transaction_probe_required"])
        self.assertEqual(report["capabilities"]["capture"], "supported_with_transaction_probe")
        self.assertFalse(report["source_mutated"])
        self.assertEqual(runtime.tree_digest(root), before)

    @unittest.skipUnless(
        sys.platform == "win32" or sys.platform == "darwin" or sys.platform.startswith("linux"),
        "qualified mutation host required",
    )
    def test_open_and_mutation_support_never_run_disposable_probe_or_change_tree(self) -> None:
        root = self.base / "read-only-open-workspace"
        runtime.initialize_workspace(
            str(root),
            user="user",
            project="project",
            agent="nova",
            thread=None,
            sensitivity="ordinary",
            retention="until-user-changes",
        )

        def exact_tree() -> list[tuple[str, int, int, int, bytes | None]]:
            entries: list[tuple[str, int, int, int, bytes | None]] = []
            for path in [root, *sorted(root.rglob("*"))]:
                metadata = path.lstat()
                relative = "." if path == root else path.relative_to(root).as_posix()
                content = path.read_bytes() if path.is_file() else None
                entries.append(
                    (
                        relative,
                        metadata.st_mode,
                        metadata.st_size,
                        metadata.st_mtime_ns,
                        content,
                    )
                )
            return entries

        def forbidden_probe(*_args: object, **_kwargs: object) -> None:
            raise AssertionError("read-only support invoked the disposable capability probe")

        operations = (
            (
                "mutation_support",
                lambda: runtime.mutation_filesystem_support(root, lexical_root=root),
            ),
            (
                "open",
                lambda: store.cmd_open(argparse.Namespace(workspace=str(root))),
            ),
        )
        for operation_name, operation in operations:
            with self.subTest(operation=operation_name):
                before = exact_tree()
                with mock.patch.object(
                    runtime,
                    "_filesystem_capability_probe",
                    side_effect=forbidden_probe,
                ) as capability_probe:
                    result = operation()
                capability_probe.assert_not_called()
                self.assertEqual(exact_tree(), before)
                if operation_name == "mutation_support":
                    self.assertEqual(result["status"], "preflight_supported")
                    self.assertTrue(result["transaction_probe_required"])
                else:
                    self.assertEqual(
                        result["access_support"]["mutation"]["status"],
                        "preflight_supported",
                    )
                    self.assertTrue(
                        result["access_support"]["mutation"]["transaction_probe_required"]
                    )
                    self.assertEqual(
                        result["capabilities"]["capture"],
                        "supported_with_transaction_probe",
                    )
                    self.assertFalse(result["source_mutated"])

        before = exact_tree()
        with mock.patch.object(
            runtime,
            "_filesystem_qualification_witness",
            side_effect=OSError(errno.EIO, "observation failed"),
        ):
            unsupported = runtime.mutation_filesystem_support(root, lexical_root=root)
        self.assertEqual(
            unsupported,
            {"status": "unsupported", "reason_code": "filesystem_semantics_unsupported"},
        )
        self.assertEqual(exact_tree(), before)

    @unittest.skipUnless(sys.platform == "win32", "Windows compatibility assertion")
    def test_windows_live_adapter_uses_capabilities_not_filesystem_name(self) -> None:
        self.assertEqual(
            runtime._filesystem_adapter(self.base / "future-workspace", lexical_root=self.base / "future-workspace"),
            "windows-LockFileEx-MoveFileExW-write-through/v2",
        )

@unittest.skipUnless(sys.platform == "win32", "native Windows live smoke")
class WindowsLiveSmokeTests(unittest.TestCase):
    def run_json(self, script: Path, *args: object) -> dict:
        completed = subprocess.run(
            [sys.executable, str(script), *[str(value) for value in args]],
            text=True,
            capture_output=True,
            timeout=90,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        stream = completed.stdout if completed.stdout.strip() else completed.stderr
        return json.loads(stream) if stream.strip().startswith("{") else {"text": stream.strip()}

    def test_native_lock_replace_and_directory_publication_round_trip(self) -> None:
        with tempfile.TemporaryDirectory(dir=temporary_parent()) as temporary:
            root = Path(temporary).resolve() / "workspace"
            initialized = self.run_json(
                STORE,
                "init",
                root,
                "--user",
                "user",
                "--project",
                "windows-smoke",
                "--agent",
                "nova",
            )
            self.assertEqual(initialized["kind"], "initialized")
            mutated = self.run_json(
                STORE,
                "episode",
                root,
                "--type",
                "tool_result",
                "--content",
                "native Windows durability smoke",
                "--source-kind",
                "tool",
                "--authority",
                "user-stunspot",
                "--idempotency-key",
                "windows-live-smoke",
                "--expected-generation",
                0,
            )
            self.assertEqual(mutated["generation_after"], 1)
            validated = self.run_json(VALIDATE, root)
            self.assertIn("VALID:", validated["text"])
            opened = self.run_json(STORE, "open", root)
            self.assertEqual(opened["access_support"]["mutation"]["status"], "preflight_supported")
            self.assertTrue(opened["access_support"]["mutation"]["transaction_probe_required"])
            self.assertEqual(
                opened["access_support"]["mutation"]["adapter"],
                "windows-LockFileEx-MoveFileExW-write-through/v2",
            )
            journals = [
                json.loads(path.read_text(encoding="utf-8"))
                for path in (root / "transactions").glob("*/journal.json")
            ]
            commit_adapters = [journal.get("commit_adapter") for journal in journals if journal.get("commit_adapter")]
            self.assertIn("windows-MoveFileExW-replace-write-through/v1", commit_adapters)
            witnesses = [journal["runtime_identities"]["filesystem_witness"] for journal in journals]
            self.assertTrue(all(isinstance(witness.get("volume_serial"), int) for witness in witnesses))
            self.assertEqual(list(Path(temporary).glob(".workspace.cc-initialize-*")), [])

@unittest.skipUnless(sys.platform == "darwin", "native Darwin live smoke")
class DarwinLiveSmokeTests(unittest.TestCase):
    def run_json(self, script: Path, *args: object) -> dict:
        completed = subprocess.run(
            [sys.executable, str(script), *[str(value) for value in args]],
            text=True,
            capture_output=True,
            timeout=60,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        stream = completed.stdout if completed.stdout.strip() else completed.stderr
        return json.loads(stream) if stream.strip().startswith("{") else {"text": stream.strip()}

    def test_native_apfs_flock_fullfsync_manifest_publication_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve() / "workspace"
            initialized = self.run_json(
                STORE,
                "init",
                root,
                "--user",
                "user",
                "--project",
                "darwin-smoke",
                "--agent",
                "nova",
            )
            self.assertEqual(initialized["kind"], "initialized")
            mutated = self.run_json(
                STORE,
                "episode",
                root,
                "--type",
                "tool_result",
                "--content",
                "native Darwin durability smoke",
                "--source-kind",
                "tool",
                "--authority",
                "user-stunspot",
                "--idempotency-key",
                "darwin-live-smoke",
                "--expected-generation",
                0,
            )
            self.assertEqual(mutated["generation_after"], 1)
            validated = self.run_json(VALIDATE, root)
            self.assertIn("VALID:", validated["text"])
            opened = self.run_json(STORE, "open", root)
            self.assertEqual(opened["access_support"]["mutation"]["status"], "preflight_supported")
            self.assertTrue(opened["access_support"]["mutation"]["transaction_probe_required"])
            self.assertEqual(opened["access_support"]["mutation"]["adapter"], "darwin-fcntl-flock-fsync-F_FULLFSYNC-when-available-rename-parent-fsync/v2")
            journals = [json.loads(path.read_text(encoding="utf-8")) for path in (root / "transactions").glob("*/journal.json")]
            commit_adapters = [journal.get("commit_adapter") for journal in journals if journal.get("commit_adapter")]
            self.assertIn("darwin-F_FULLFSYNC-rename-parent-fsync/v1", commit_adapters)


@unittest.skipUnless(sys.platform.startswith("linux"), "native Linux live smoke")
class LinuxLiveSmokeTests(unittest.TestCase):
    def run_json(self, script: Path, *args: object) -> dict:
        completed = subprocess.run(
            [sys.executable, str(script), *[str(value) for value in args]],
            text=True,
            capture_output=True,
            timeout=60,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        stream = completed.stdout if completed.stdout.strip() else completed.stderr
        return json.loads(stream) if stream.strip().startswith("{") else {"text": stream.strip()}

    def test_native_flock_fsync_manifest_publication_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve() / "workspace"
            initialized = self.run_json(
                STORE,
                "init",
                root,
                "--user",
                "user",
                "--project",
                "linux-smoke",
                "--agent",
                "nova",
            )
            self.assertEqual(initialized["kind"], "initialized")
            mutated = self.run_json(
                STORE,
                "episode",
                root,
                "--type",
                "tool_result",
                "--content",
                "native Linux durability smoke",
                "--source-kind",
                "tool",
                "--authority",
                "user-stunspot",
                "--idempotency-key",
                "linux-live-smoke",
                "--expected-generation",
                0,
            )
            self.assertEqual(mutated["generation_after"], 1)
            validated = self.run_json(VALIDATE, root)
            self.assertIn("VALID:", validated["text"])
            opened = self.run_json(STORE, "open", root)
            self.assertEqual(opened["access_support"]["mutation"]["status"], "preflight_supported")
            self.assertTrue(opened["access_support"]["mutation"]["transaction_probe_required"])
            self.assertEqual(
                opened["access_support"]["mutation"]["adapter"],
                "linux-fcntl-flock-fsync-rename-parent-fsync/v1",
            )
            journals = [
                json.loads(path.read_text(encoding="utf-8"))
                for path in (root / "transactions").glob("*/journal.json")
            ]
            commit_adapters = [
                journal.get("commit_adapter")
                for journal in journals
                if journal.get("commit_adapter")
            ]
            self.assertIn("posix-rename-parent-fsync/v1", commit_adapters)

if __name__ == "__main__":
    unittest.main()
