#!/usr/bin/env python3
"""Validate declared profile structure/consistency; never certify language learning."""
from __future__ import annotations
import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

FORMAT = "lex-foster-learner-profile/v1"
EVIDENCE_STATES = {"new", "supported", "independent", "transferred"}
GOAL_STATES = {"active", "paused", "completed", "retired"}
SCHEMA = Path(__file__).resolve().parents[1] / "schemas/learner-profile.schema.json"
CLOCK = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)\Z")

def clock(value):
    if not isinstance(value, str) or not CLOCK.fullmatch(value):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None

def _valid_datetime(value):
    return clock(value) is not None

def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result

def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"), object_pairs_hook=unique_object)

def shape(value, spec, path, errors):
    kind = spec.get("type")
    types = {"object": dict, "array": list, "string": str}
    if kind and not isinstance(value, types[kind]):
        errors.append(f"{path} must be {kind}"); return
    if "const" in spec and value != spec["const"]:
        errors.append(f"{path} must be {spec['const']!r}")
    if "enum" in spec and value not in spec["enum"]:
        errors.append(f"{path} must be one of {spec['enum']}")
    if kind == "string":
        if spec.get("minLength") and not value.strip():
            errors.append(f"{path} must be a non-empty string")
        if spec.get("format") == "date-time" and clock(value) is None:
            errors.append(f"{path} must be a real zoned timestamp: YYYY-MM-DDTHH:MM:SS+HH:MM or Z")
    elif kind == "array":
        if len(value) < spec.get("minItems", 0): errors.append(f"{path} requires an entry")
        for i, entry in enumerate(value): shape(entry, spec["items"], f"{path}[{i}]", errors)
    elif kind == "object":
        props = spec.get("properties", {})
        for key in spec.get("required", []):
            if key not in value: errors.append(f"{path}.{key} is required")
        for key, entry in value.items():
            if key in props: shape(entry, props[key], f"{path}.{key}", errors)
            elif spec.get("additionalProperties") is False: errors.append(f"{path}.{key} is not allowed")

def validate_profile(data):
    errors = []
    try: schema = load_json(SCHEMA)
    except (OSError, ValueError, UnicodeError) as exc: return [f"bundled schema unavailable: {exc}"]
    shape(data, schema, "profile", errors)
    if errors: return errors
    targets = {x["language"].strip().casefold() for x in data["target_languages"]}
    indexes = {}
    for name in ("goals", "evidence"):
        indexes[name] = {}
        for item in data[name]:
            if item["id"] in indexes[name]: errors.append(f"duplicate {name.rstrip('s')} id: {item['id']}")
            indexes[name][item["id"]] = item
    for i, item in enumerate(data["evidence"]):
        label = f"evidence[{i}]"
        if item["target_language"].strip().casefold() not in targets: errors.append(f"{label}.target_language is undeclared")
        if clock(item["observed_at"]) > clock(data["updated_at"]): errors.append(f"{label}.observed_at is after updated_at")
        obs = item.get("observation")
        if obs is None: continue  # readable historical declaration; reported separately, never evidence-qualified
        if obs["goal_id"] not in indexes["goals"]: errors.append(f"{label}.observation.goal_id is unknown")
        if item["state"] in {"independent", "transferred"}:
            if obs["result"] != "met" or obs["support_kind"] != "none":
                errors.append(f"{label}: {item['state']} requires declared criterion met without support")
        if item["state"] == "transferred":
            prior = indexes["evidence"].get(obs.get("prior_evidence_id"))
            if not prior or prior["id"] == item["id"]: errors.append(f"{label}: transfer requires a distinct prior evidence record"); continue
            po = prior.get("observation")
            if not po: errors.append(f"{label}: prior transfer basis has no observation"); continue
            if clock(prior["observed_at"]) >= clock(item["observed_at"]): errors.append(f"{label}: prior observation must be earlier")
            if prior['target_language'].strip().casefold() != item['target_language'].strip().casefold(): errors.append(f"{label}: transfer language differs")
            for key in ("goal_id", "criterion", "modality"):
                if po[key].strip().casefold() != obs[key].strip().casefold(): errors.append(f"{label}: transfer {key} differs from prior basis; record separately")
            if not obs.get("changed_condition", "").strip() or obs['prompt'].strip() == po['prompt'].strip():
                errors.append(f"{label}: transfer requires a declared changed condition and distinct cue")
    for i, item in enumerate(data["retrieval_queue"]):
        if item["evidence_id"] not in indexes["evidence"]: errors.append(f"retrieval_queue[{i}] references unknown evidence")
    return errors

def evidence_notes(data):
    notes = []
    if not isinstance(data, dict) or not isinstance(data.get('evidence'), list): return notes
    for item in data['evidence']:
        if not isinstance(item, dict): continue
        if 'observation' not in item:
            notes.append(f"{item.get('id', '?')}: legacy declaration only; performance basis not recorded, state is unverified")
        else:
            notes.append(f"{item.get('id', '?')}: declared observation; language correctness, meaningful cue change and criterion alignment need human/model review")
    return notes

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('profile', type=Path)
    args = parser.parse_args(argv)
    try: data = load_json(args.profile)
    except (OSError, ValueError, UnicodeError) as exc:
        print(f"FAIL profile input: {exc}", file=sys.stderr); return 1
    errors = validate_profile(data)
    for message in errors: print('ERROR ' + message, file=sys.stderr)
    if errors: return 1
    print('PASS declared structure and consistency only; no learner ability or mastery has been verified.')
    for note in evidence_notes(data): print('NOTE ' + note)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
