"""User-triggered native folder chooser. No picker is opened at startup."""
import sys
try:
    import tkinter as tk
    from tkinter import filedialog
    root=tk.Tk();root.withdraw();root.attributes("-topmost",True)
    selected=filedialog.askdirectory(title="Choose the Dennis project-record estate",initialdir=(sys.argv[1] if len(sys.argv)>1 else None),mustexist=True)
    root.destroy()
    if selected:sys.stdout.write(selected)
except Exception as exc:
    sys.stderr.write(str(exc));sys.exit(1)

