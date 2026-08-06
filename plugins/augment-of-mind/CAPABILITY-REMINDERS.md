# MIND capability reminders

MIND keeps a local semantic map of durable capabilities so useful praxis can return to attention without requiring the user or model to remember exact names.

Before each submitted prompt, the trusted local hook associates the current prompt and a bounded recent conversation window against the active map. The resulting Arm's Reach field is inserted before the model turn as a small advisory cue set: nearby capabilities and relations that might be handy. It is not a command, ranking, recommendation, selection, activation, installation check, health check, completeness claim, permission, authority grant, or proof of fit.

When a capability is added, installed, enabled, updated, disabled, removed, or proposed, Capability Promotion keeps one quiet responsibility attached: decide whether its authored reminder representation should change too. MIND does not scan or hash the whole harness on every response.

The hook owns association and delivery. The model consumes the field already present in context; it does not call another tool, resource reader, server, or adapter to fetch or rebuild it. An empty field means only that nothing surfaced inside that association boundary. A delivery failure makes no claim about what capabilities exist or fit.

The public map stores authored descriptions, relations, and semantic representations—not private skill bodies, credentials, personal records, source paths, raw prompts, or conversation transcripts. Raw association text is sent only to the configured local embedding endpoint and is not persisted by MIND Core; receipts retain hashes and delivery evidence. Structural verification does not by itself establish behavioral qualification on every host.
