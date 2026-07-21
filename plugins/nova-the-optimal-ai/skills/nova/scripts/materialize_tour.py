from __future__ import annotations

import argparse
import hashlib
import shutil
from pathlib import Path


ASSET = Path(__file__).resolve().parents[1] / "assets" / "nova-tour.html"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Copy Nova's offline interactive tour to an explicit destination."
    )
    parser.add_argument("output", type=Path, help="Destination .html file")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace an existing destination file",
    )
    args = parser.parse_args()

    output = args.output.expanduser().resolve()
    if output.suffix.lower() != ".html":
        parser.error("output must end in .html")
    if output.exists() and not args.overwrite:
        parser.error("output already exists; pass --overwrite to replace it")

    if not ASSET.is_file():
        parser.error(f"bundled tour asset is missing: {ASSET}")

    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ASSET, output)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    print(f"tour={output}")
    print(f"sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
