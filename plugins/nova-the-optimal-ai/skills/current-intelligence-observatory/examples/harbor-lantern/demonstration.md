# Harbor Lantern demonstration

Harbor Lantern is a wholly synthetic proof. It begins with two apparently corroborating reports of a three-day terminal closure and transformer fire. The baseline freezes that state as `watch-ready` while preserving two visible cautions: the second source may depend on the first, and two same-name entity candidates cannot be merged.

The update adds a direct terminal notice and a correction. It preserves the original wire capture, records the correction as a superseding capture, proves the roundup explicitly depends on the wire, and quarantines an instruction embedded in the terminal notice. The leading assessment changes from “possible multi-day closure” to “limited Gate B vehicle-entry pause.” It does not manufacture a cause, a precise coordinate, or a responsible person.

The generated `delta.json` distinguishes corrections, new observations, changed objects, unsupported claims, unchanged records, and unresolved items. The generated `projections/` use one semantic record. Every occurrence of an object retains its identifier, type, status, confidence, uncertainty, and provenance references.

The public brief omits both Morgan Vale candidates and the unsupported fire claim. Publication still stops because the human editorial challenge is pending. Passing structural checks would not certify that a comparable real-world case was true, lawful, safe, or publishable.

## Reproduce the bounded mechanics

From the skill root:

```text
python -X utf8 scripts/observatory_guardrail.py validate-case examples/harbor-lantern/case-baseline.json
python -X utf8 scripts/observatory_guardrail.py validate-case examples/harbor-lantern/case-update.json
python -X utf8 scripts/observatory_guardrail.py project examples/harbor-lantern/case-update.json examples/harbor-lantern/projections
python -X utf8 scripts/observatory_guardrail.py delta examples/harbor-lantern/case-baseline.json examples/harbor-lantern/case-update.json examples/harbor-lantern/delta.json
python -X utf8 scripts/observatory_guardrail.py audit-publication examples/harbor-lantern/case-update.json
```

The final command is expected to stop on `BLK-HUMAN-EDITOR`.
