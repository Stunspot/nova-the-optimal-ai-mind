"""Compatibility entrypoint; maintained implementation is answerlayer.py."""
import sys
from answerlayer import main
if __name__ == "__main__":
    raise SystemExit(main(['recheck', *sys.argv[1:]]))
