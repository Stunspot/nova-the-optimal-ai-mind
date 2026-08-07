# MIND capability reminders

MIND keeps a local semantic map of durable capabilities so useful praxis can return to attention without requiring the user or model to remember exact names.

Before each submitted prompt, the trusted local hook associates the current prompt and a bounded recent conversation window against the active map. A successful vector query may be supplemented by lexical identity cues. The hook then inserts the returned capability reminders before the model turn beneath this context preface:

```text
**Vector-near semantically related capabilities below**: surfaced from RAG memory for this turn as associative presentation of surveyed capabilities. Consider such reminders as suggested subset of available praxis affordances, not suggested courses of action. Assess contextual relevance and likely utility to task. Integrate with capabilities already present in assembled context. Surveyed memory may extend beyond the current harness.
```

Field, snapshot, mode, vector state, and hash telemetry remains in delivery receipts. If semantic embedding is unavailable, the hook emits its bounded delivery note instead of presenting lexical-only results as vector-near.

When a capability is added, installed, enabled, updated, disabled, removed, or proposed, Capability Promotion keeps one quiet responsibility attached: decide whether its authored reminder representation should change too. MIND does not scan or hash the whole harness on every response.

The hook owns association and delivery. The model consumes the field already present in context rather than rebuilding it. An empty field means only that nothing surfaced inside that association boundary. A delivery failure makes no claim about what capabilities exist or fit.

The public map stores authored descriptions, relations, and semantic representations—not private skill bodies, credentials, personal records, source paths, raw prompts, or conversation transcripts. Raw association text is sent only to the configured local embedding endpoint and is not persisted by MIND Core; receipts retain hashes and delivery evidence. Structural verification does not by itself establish behavioral qualification on every host.
