"""Visible startup errors for the Windows shortcut; no console window is needed."""
import ctypes,sys,tempfile
from pathlib import Path

# Windows importlib needs extended paths for neighboring modules in deep extractions.
import sys
from pathlib import Path
def _module_path(value):
    value = str(Path(value).resolve())
    if sys.platform == "win32" and not value.startswith("\\\\?\\"):
        value = ("\\\\?\\UNC\\" + value[2:]) if value.startswith("\\\\") else ("\\\\?\\" + value)
    return value
sys.path.insert(0, _module_path(Path(__file__).parent))

from launch import main
if __name__=="__main__":
    try:main()
    except (Exception,SystemExit) as error:
        if isinstance(error,SystemExit) and error.code in (0,None):raise
        if "--no-browser" in sys.argv:
            (Path(tempfile.gettempdir())/"beryl-startup-test-error.txt").write_text(str(error),"utf-8")
            sys.exit(1)
        ctypes.windll.user32.MessageBoxW(None,"Beryl Repair Companion could not open.\n\n"+str(error)+"\n\nYour saved documents have not been removed.","Beryl Repair Companion",0x10)
        sys.exit(1)
