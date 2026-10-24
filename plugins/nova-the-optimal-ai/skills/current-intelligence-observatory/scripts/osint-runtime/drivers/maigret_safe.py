"""Run the pinned Maigret CLI with native libcurl decompression disabled."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from safe_http import UnsafeDecoder, install_maigret_transport

def main():
    try:
        install_maigret_transport()
    except (UnsafeDecoder, ImportError) as exc:
        print("Observatory security preflight: " + str(exc), file=sys.stderr)
        return 2
    from maigret.maigret import run
    return run()

if __name__ == "__main__":
    raise SystemExit(main())
