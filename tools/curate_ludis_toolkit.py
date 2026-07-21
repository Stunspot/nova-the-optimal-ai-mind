#!/usr/bin/env python3
"""Remove legacy loader/persona/biography payload from Ludis instruments."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
TARGET = (
    REPO
    / "plugins"
    / "nova-the-optimal-ai"
    / "skills"
    / "ludis-continuum"
    / "knowledge"
    / "canonical"
    / "rpg-toolkit-v2.md"
)
RECEIPT = REPO / "verification" / "ludis-toolkit-curation.json"
START = "# Region Creating Map Builder"
END = "***DO NOT PROCEDE WITH ANY CREATION"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    original = TARGET.read_bytes()
    text = original.decode("utf-8")

    if text.startswith("# Ludis RPG Instruments"):
        print(json.dumps({"status": "already-curated", "sha256": digest(original)}))
        return

    start = text.find(START)
    end = text.find(END)
    if start < 0 or end < 0 or end <= start:
        raise RuntimeError("Expected Ludis toolkit curation markers were not found")

    instruments = text[start:end].rstrip()
    curated = (
        "# Ludis RPG Instruments\n\n"
        "Enter through the user's live creative need. Choose only the instrument that earns its context, "
        "preserve supplied canon and boundaries, and return the result through Nova's voice. "
        "Examples teach form; they are never canon for a new world.\n\n"
        f"{instruments}\n"
    )
    TARGET.write_text(curated, encoding="utf-8", newline="\n")
    result = TARGET.read_bytes()
    receipt = {
        "format": "cd-ludis-toolkit-curation/v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "target": str(TARGET.relative_to(REPO)).replace("\\", "/"),
        "source_sha256": digest(original),
        "curated_sha256": digest(result),
        "retained_from": START,
        "retained_until": END,
        "removed": [
            "legacy auto-loader and forced persona preface",
            "obsolete response-wrapper and wait-state instructions",
            "personal biography",
            "community and Patreon promotion",
            "legacy Nova self-description",
        ],
    }
    RECEIPT.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()

