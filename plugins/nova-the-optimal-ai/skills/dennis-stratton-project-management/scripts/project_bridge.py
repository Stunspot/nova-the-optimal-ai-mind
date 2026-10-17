"""Compatibility entrypoint for the read-only Project Bridge."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "workspace"))
from launch import main
if __name__ == "__main__":
    main()
