"""Enforce the shipped IT-case schema without adding a runtime dependency."""
from pathlib import Path
import json, sys

SCHEMA = Path(__file__).resolve().parents[1] / "schemas/it-case.schema.json"

def check(value, spec, location="$"):
    kind = spec.get("type")
    matches = {"object": isinstance(value, dict), "array": isinstance(value, list),
               "string": isinstance(value, str), "boolean": isinstance(value, bool)}
    if kind and not matches.get(kind, False):
        raise ValueError(f"{location} must be {kind}")
    if "enum" in spec and value not in spec["enum"]:
        raise ValueError(f"{location} has invalid value {value!r}")
    if isinstance(value, str) and "minLength" in spec and len(value.strip()) < spec["minLength"]:
        raise ValueError(f"{location} must be a non-empty string")
    if isinstance(value, dict):
        missing = [key for key in spec.get("required", []) if key not in value]
        if missing:
            raise ValueError(f"{location} missing required keys: {', '.join(missing)}")
        for key, child in spec.get("properties", {}).items():
            if key in value:
                check(value[key], child, f"{location}.{key}")
    if isinstance(value, list) and "items" in spec:
        for index, item in enumerate(value):
            check(item, spec["items"], f"{location}[{index}]")

def validate(path):
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    check(data, json.loads(SCHEMA.read_text(encoding="utf-8-sig")))
    if not data["next_move"]["action"]:
        raise ValueError("$.next_move.action must be populated")

def main():
    if len(sys.argv) != 2:
        print("usage: validate_case_file.py <case.json>", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    try:
        validate(path)
    except (OSError, ValueError) as exc:
        print(f"FAIL {path}: {exc}", file=sys.stderr)
        return 1
    print(f"PASS {path}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
