"""Validate native shape and optional declared consistency; never physical truth."""
from pathlib import Path
import argparse
import json
import math
import sys

SCHEMA = Path(__file__).resolve().parents[1] / "schemas/it-case.schema.json"
KINDS = {"reported", "observed", "measured", "retrieved", "assumed"}

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

def object_pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f"Duplicate JSON key: {key}")
        out[key] = value
    return out

def finite_values(value):
    """Reject non-finite values in extension fields as well as schema fields."""
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("Non-finite JSON number; current record has not been changed")
    if isinstance(value, dict):
        for child in value.values():
            finite_values(child)
    elif isinstance(value, list):
        for child in value:
            finite_values(child)
    return value

def load_json(text):
    def invalid_constant(value):
        raise ValueError(f"Non-finite JSON value: {value}")
    return finite_values(json.loads(text, object_pairs_hook=object_pairs, parse_constant=invalid_constant))

def validate_data(data):
    finite_values(data)
    check(data, json.loads(SCHEMA.read_text(encoding="utf-8")))
    for collection in ("evidence", "hypotheses", "tests", "changes", "sources"):
        seen = set()
        for index, item in enumerate(data[collection]):
            value = item["id"]
            if value in seen:
                raise ValueError(f"$.{collection}[{index}].id duplicates {value}")
            seen.add(value)
            for key in ("evidence_ids", "hypothesis_ids", "test_ids", "source_ids"):
                refs = item.get(key, [])
                if len(refs) != len(set(refs)):
                    raise ValueError(f"$.{collection}[{index}].{key} contains duplicate IDs")
    return data

def populated(value):
    return isinstance(value, str) and bool(value.strip()) and value.strip().lower() not in {
        "unknown", "not-recorded", "not recorded", "not-examined", "not examined", "none", "n/a", "tbd", "pending", "not run", "not performed"}

def consistency_issues(data):
    """Check explicit declarations only. No inferred diagnosis or permission."""
    issues = []
    refs_to = {"evidence_ids": "evidence", "hypothesis_ids": "hypotheses", "test_ids": "tests", "source_ids": "sources"}
    identities = {key: {item["id"] for item in data[key]} for key in ("evidence", "hypotheses", "tests", "changes", "sources")}
    aliases = {"kind": "state", "claim": "value", "action": "test", "status": "state"}
    for collection in identities:
        for index, item in enumerate(data[collection]):
            location = f"$.{collection}[{index}]"
            pairs = {"kind": "state", "claim": "value"} if collection == "evidence" else {"status": "state", **({"action": "test"} if collection == "tests" else {})}
            for current, legacy in pairs.items():
                if current in item and legacy in item and item[current] != item[legacy]:
                    issues.append(f"{location}: {current} conflicts with legacy {legacy}; inspect both")
            for field, target in refs_to.items():
                for value in item.get(field, []):
                    if value not in identities[target]:
                        issues.append(f"{location}.{field}: missing {target} ID {value}")
    for index, test in enumerate(data["tests"]):
        location = f"$.tests[{index}]"
        state = test.get("status", test.get("state"))
        if test.get("performed") is True:
            for field in ("result", "result_source"):
                if not populated(test.get(field)):
                    issues.append(f"{location}.{field}: performed test needs an actual recorded observation and source")
            if test.get("result_basis") not in KINDS - {"assumed"}:
                issues.append(f"{location}.result_basis: performed result needs reported/observed/measured/retrieved provenance")
            if state == "test-planned":
                issues.append(f"{location}: performed=true conflicts with test-planned")
        elif state == "test-run":
            issues.append(f"{location}: test-run lacks explicit performed=true; execution remains unconfirmed")
        elif test.get("performed") is False and populated(test.get("result")) and not test["result"].strip().lower().startswith(("not run", "not performed", "pending", "awaiting")):
            issues.append(f"{location}: result text is present while performed=false; retain and reconcile the conflicting declaration")
    v = data["verification"]
    resolved = v["disposition"] == "verified-resolved" or data["status"] == "verification-passed"
    if v.get("stale"):
        issues.append("$.verification: retained verification is stale; reconcile it against the current case")
    if resolved:
        if data["status"] == "verification-failed" or v["disposition"] != "verified-resolved":
            issues.append("$.verification: case status and resolution disposition conflict")
        if v["original_envelope_retested"] is not True:
            issues.append("$.verification.original_envelope_retested: resolution requires a recorded original-envelope retest")
        groups = [("results", True), ("adjacent_checks", not populated(v.get("adjacent_not_applicable")))]
        for field, required in groups:
            values = v[field]
            if required and not values:
                issues.append(f"$.verification.{field}: missing recorded checks" + (" or reason adjacent checks do not apply" if field == "adjacent_checks" else ""))
            for index, result in enumerate(values):
                location = f"$.verification.{field}[{index}]"
                if not isinstance(result, dict):
                    issues.append(f"{location}: narrative retained; cannot check outcome, observation, source and conditions mechanically")
                    continue
                if result.get("outcome") != "passed" or not all(populated(result.get(key)) for key in ("observation", "source", "conditions")):
                    issues.append(f"{location}: resolution needs passed outcome with actual observation, source and test conditions")
        if not populated(v.get("reopen_condition")):
            issues.append("$.verification.reopen_condition: resolution needs a usable recurrence/stop condition")
    return issues

def validate(path):
    data = load_json(Path(path).read_text(encoding="utf-8-sig"))
    return validate_data(data)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", type=Path)
    parser.add_argument("--consistency", action="store_true", help="Also fail on contradictory or incomplete evidence declarations")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        data = validate(args.case)
        issues = consistency_issues(data)
        result = {"structure_valid": True, "consistency_issues": issues, "scope": "Recorded structure and bounded declared consistency only; no truth, execution, authority or repair certification."}
    except (OSError, ValueError, RecursionError) as exc:
        result = {"structure_valid": False, "errors": [str(exc)], "consistency_issues": []}
    valid = result["structure_valid"] and (not args.consistency or not result["consistency_issues"])
    if args.json:
        print(json.dumps({"valid": valid, **result}, ensure_ascii=False))
    else:
        print(("PASS " if valid else "FAIL ") + ("DECLARED CONSISTENCY " if args.consistency else "STRUCTURE ") + str(args.case))
        for issue in result.get("errors", []) + result.get("consistency_issues", []):
            print("REVIEW " + issue)
        print("No physical diagnosis, execution, permission or repair is established.")
    return 0 if valid else 1

if __name__ == "__main__":
    raise SystemExit(main())
