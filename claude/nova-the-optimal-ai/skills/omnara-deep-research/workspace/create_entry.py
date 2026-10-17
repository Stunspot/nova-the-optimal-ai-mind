#!/usr/bin/env python3
"""Create an optional no-clobber native entry for the Omnara Campaign Room."""
from __future__ import annotations
import argparse
import os
import plistlib
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

NAME = "OMNARA"
WORKSPACE = Path(__file__).absolute().parent
VERSION = (WORKSPACE.parent / "VERSION").read_text(encoding="utf-8").strip()

def local_path(value: str | Path, directory: bool = False) -> Path:
    path = Path(os.path.abspath(os.path.expanduser(str(value))))
    for part in [path, *path.parents]:
        info = part.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 1024):
            raise ValueError("Linked paths are not supported")
    if directory and not path.is_dir():
        raise ValueError("Choose an existing destination directory")
    if not directory and not path.is_file():
        raise ValueError("Required viewer or icon file is missing")
    return path

def ps_quote(path: Path | str) -> str:
    return "'" + str(path).replace("'", "''") + "'"

def create_entry(directory: str | Path, platform: str) -> Path:
    directory = local_path(directory, directory=True)
    workspace = local_path(WORKSPACE, directory=True)
    target = local_path(workspace.parent / ("Open.cmd" if platform == "windows" else "Open.command"))
    if platform not in ("windows", "mac"):
        raise ValueError("Platform must be windows or mac")
    icon = local_path(workspace / "assets" / ("omnara.ico" if platform == "windows" else "omnara.icns"))
    entry = directory / (NAME + (".lnk" if platform == "windows" else ".app"))
    if entry.exists() or entry.is_symlink():
        raise ValueError("Entry already exists; it was not replaced")
    if platform == "windows":
        if sys.platform != "win32":
            raise ValueError("Windows shortcut creation requires Windows")
        powershell = shutil.which("powershell.exe")
        if not powershell:
            raise ValueError("Windows PowerShell is unavailable")
        with tempfile.TemporaryDirectory(prefix=".omnara-entry-", dir=directory) as scratch:
            temp = Path(scratch) / "entry.lnk"
            command = "$ErrorActionPreference='Stop';$shell=New-Object -ComObject WScript.Shell;$link=$shell.CreateShortcut(" + ps_quote(temp) + ");$link.TargetPath=" + ps_quote(target) + ";$link.Arguments='';$link.WorkingDirectory=" + ps_quote(workspace) + ";$link.IconLocation=" + ps_quote(str(icon) + ",0") + ";$link.Description='Omnara Campaign Room';$link.Save()"
            subprocess.run([powershell, "-NoProfile", "-NonInteractive", "-Command", command], check=True, capture_output=True, text=True)
            with entry.open("xb") as output:
                output.write(temp.read_bytes())
    else:
        entry.mkdir()
        try:
            contents = entry / "Contents"
            macos = contents / "MacOS"
            resources = contents / "Resources"
            macos.mkdir(parents=True)
            resources.mkdir()
            shutil.copy2(icon, resources / "omnara.icns")
            plist = {"CFBundleName": NAME, "CFBundleDisplayName": NAME, "CFBundleIdentifier": "com.collaborative-dynamics.omnara", "CFBundlePackageType": "APPL", "CFBundleExecutable": "OmnaraRoom", "CFBundleIconFile": "omnara.icns", "CFBundleShortVersionString": VERSION, "CFBundleVersion": VERSION}
            (contents / "Info.plist").write_bytes(plistlib.dumps(plist))
            relative = os.path.relpath(target, macos).replace(os.sep, "/")
            script = '#!/bin/sh\nset -eu\nHERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"\nexec /usr/bin/open "$HERE"/' + shlex.quote(relative) + '\n'
            launcher = macos / "OmnaraRoom"
            launcher.write_bytes(script.encode("utf-8"))
            launcher.chmod(0o755)
        except BaseException:
            # Preserve the failed new bundle for inspection; never remove another entry.
            raise
    return entry

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", required=True, type=Path, help="Existing directory where you want the optional entry")
    parser.add_argument("--platform", choices=("windows", "mac"), default="windows" if sys.platform == "win32" else "mac")
    args = parser.parse_args(argv)
    try:
        print(create_entry(args.directory, args.platform))
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(str(error), file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
