"""Optional Windows icon binding for the existing Oracle Reading launcher."""
import os
from pathlib import Path
import subprocess


def bind_windows(root):
    root = Path(root).resolve()
    if os.name != "nt":
        return {"status": "not_applicable", "platform": os.name}
    if not (root / "Launch Oracle Reading.cmd").is_file() or not (root / "skills/oracle-reading/assets/oracle.ico").is_file():
        return {"status": "unavailable", "platform": "windows", "detail": "Native launcher or icon asset missing"}
    def quote(value):
        return "'" + str(value).replace("'", "''") + "'"
    script = (
        "$ErrorActionPreference='Stop';$taskShell=New-Object -ComObject WScript.Shell;"
        "$taskShortcut=$taskShell.CreateShortcut(" + quote(root / "Launch Oracle Reading.lnk") + ");"
        "$taskShortcut.TargetPath=" + quote(root / "Launch Oracle Reading.cmd") + ";"
        "$taskShortcut.WorkingDirectory=" + quote(root) + ";"
        "$taskShortcut.IconLocation=" + quote(str(root / "skills/oracle-reading/assets/oracle.ico") + ",0") + ";"
        "$taskShortcut.Description='Oracle Reading visual table';$taskShortcut.Save()"
    )
    try:
        shell = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32/WindowsPowerShell/v1.0/powershell.exe"
        subprocess.run([str(shell), "-NoProfile", "-NonInteractive", "-Command", script],
                       check=True, capture_output=True, timeout=10,
                       creationflags=subprocess.CREATE_NO_WINDOW)
        return {"status": "bound", "platform": "windows", "entry": str(root / "Launch Oracle Reading.lnk")}
    except (OSError, subprocess.TimeoutExpired, subprocess.CalledProcessError) as error:
        return {"status": "unavailable", "platform": "windows", "detail": str(error)[:240]}
