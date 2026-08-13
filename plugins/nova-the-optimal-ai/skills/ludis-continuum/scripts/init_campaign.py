from __future__ import annotations

import argparse
import json
from pathlib import Path

from ledgerlib import campaign_id_from_seed, is_valid_id, validate

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a new Ludis v2 campaign workspace without overwriting existing state.")
    parser.add_argument("destination", type=Path)
    identity = parser.add_mutually_exclusive_group(required=True)
    identity.add_argument("--campaign-id", help="Stable lowercase campaign id chosen by the owner.")
    identity.add_argument("--campaign-seed", help="Owner-supplied phrase used to derive a stable id.")
    parser.add_argument("--title", help="Optional campaign title.")
    args = parser.parse_args()

    campaign_id = args.campaign_id or campaign_id_from_seed(args.campaign_seed)
    if not is_valid_id(campaign_id):
        print("FAIL: campaign id must use lowercase letters, digits, dots, underscores, or hyphens")
        return 2
    destination = args.destination.resolve()
    if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
        print(f"FAIL: destination is not an empty directory: {destination}")
        return 2
    template = ROOT / "assets" / "campaign.template" / "campaign-ledger.json"
    try:
        ledger = json.loads(template.read_text(encoding="utf-8"))
        ledger["campaign"]["id"] = campaign_id
        if args.title is not None:
            ledger["campaign"]["title"] = args.title
        errors = validate(ledger)
        if errors:
            print("FAIL: initialized ledger would be invalid: " + "; ".join(errors))
            return 1
        destination.mkdir(parents=True, exist_ok=True)
        ledger_path = destination / "campaign-ledger.json"
        with ledger_path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}")
        return 2
    print(f"PASS: initialized {destination}")
    print(f"CAMPAIGN ID: {campaign_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())