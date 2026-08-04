# First-value demonstration

This synthetic packet demonstrates AnswerLayer’s restraint and state model. It is not a real market, legal, compliance, or operational analysis.

The baseline concerns a fictional `Northstar API` vendor decision. Six candidates exercise rejection, watch, fuzz, acceptance, patching, probes, traps, and approval boundaries.

Run from the skill directory:

```text
python scripts/validate_reality_ledger.py examples/first-value/reality-ledger.json
python scripts/detect_conflicts.py examples/first-value/reality-ledger.json
python scripts/build_citation_manifest.py examples/first-value/reality-ledger.json citation-manifest.json
```

The example contains a proposed patch, not an approved baseline mutation.
