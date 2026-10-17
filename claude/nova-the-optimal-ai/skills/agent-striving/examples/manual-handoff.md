# A portable handoff when no governed store can carry the boundary

Use the existing project or continuity owner whenever it can carry the work. This example is for the exceptional portable handoff; it is not a new ledger or a file required for every task.

From this skill directory, run `python scripts/validate_pursuit_state.py examples/manual-handoff.json --json`. Python3.10+ runs the validator without added packages. The accompanying JSON is explicitly fictional: its receipt and retrieval URI do not resolve to a real service. A passing result demonstrates declared structure only. It does not prove storage, current permission, scheduler activity or resumed execution.

For a real handoff, copy the incomplete asset template to the actual authorized handoff location, replace the identifiers/direction/timestamp with current facts, and retain an actual owner-issued receipt only if storage was confirmed. A manual retrieval cue requires a person or later task to invoke it. No unattended continuation follows from the word manual. Prepared or unavailable persistence uses a null receipt and describes the actual lost guarantee with a concrete explanation, not a placeholder. Never fill an unknown receipt with none, N/A, unknown or a guessed address.

Timestamps use a deliberately bounded RFC3339 profile: Gregorian years0001–9999, uppercase T and Z, seconds00–59 and valid numeric hour/minute offset components. Leap seconds are unsupported; use a supported timestamp for the observation rather than silently normalizing invalid input. Calendar dates must actually exist. JSON Schema clients must enable appropriate format validation; the included Python validator checks the calendar itself.

After a real write, recover the owner's current record before continuing. A saved old revision is useful history but cannot overrule a later pause, correction or cancellation. Retain evidence of any unavailable goal mutation and use the [host gap example](host-goal-mutation-gap.md) for that distinction.
