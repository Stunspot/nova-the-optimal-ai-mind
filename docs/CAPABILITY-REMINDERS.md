# How MIND remembers capabilities

Installing useful praxis is not enough if the agent never remembers it exists. Nova + MIND Free includes a local semantic reminder layer that can bring capabilities back within reach without requiring the user or model to know their names.

## What happens before a turn

For each submitted prompt, the trusted MIND hook builds a bounded association anchor from the current prompt and recent conversation context. It embeds that anchor through the configured local `qwen3-embedding:0.6b` endpoint, compares it with the active capability estate, adds explicit lexical identity cues when present, and injects the resulting Arm's Reach field before the model turn.

The field says only: **this praxis is associatively nearby and might be handy.** It is not a command, ranking, recommendation, selection, activation, installation or health check, completeness claim, permission, authority grant, or proof of fit. Nova may use, ignore, combine, investigate, or outgrow any reminder according to the live work.

The hook owns association and delivery. Nova does not call a second tool, resource reader, server, or adapter to fetch or rebuild the field. An empty field means only that nothing surfaced inside that boundary; a delivery failure says nothing about which capabilities exist or fit.

## What happens when capability changes

When a durable skill, plugin, tool, program, or other capability is added, installed, enabled, replaced, disabled, removed, or proposed, Capability Promotion keeps the reminder estate in the same completion path. The capability is represented by its useful transformation, fitting situations, natural cues, characteristic correction, negative boundary, concrete example, relations, and canonical entrypoint.

MIND does not scan or hash the whole harness on every turn. Capability Promotion updates authored representations when the capability ecology changes; the prompt hook associates against the active estate when work arrives.

## Privacy and evidence

The public estate contains authored descriptions, relations, and semantic representations. It does not contain private skill bodies, credentials, personal records, private source paths, raw prompts, or conversation transcripts. Association text is sent only to the configured local embedding endpoint and is not persisted by MIND Core; delivery receipts retain hashes and bounded evidence.

The included profile is structurally verified and remains explicitly unqualified pending broader behavioral qualification. Hook installation, trust, successful execution, delivery, model attention, use, and fit remain distinct evidence states.
