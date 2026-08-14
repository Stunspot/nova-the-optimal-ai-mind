# Worldline Is Project Continuity, Not Another Memory Store

## Contents

- [Architectural place](#architectural-place)
- [Promise and negative space](#promise-and-negative-space)
- [Four operations](#four-operations)
- [Preserve ownership](#preserve-ownership)
- [Use existing Continuity records](#use-existing-continuity-records)
- [Durable and portable delivery](#durable-and-portable-delivery)
- [Runtime acceptance boundary](#runtime-acceptance-boundary)
## Architectural place

Worldline is Nova's named project-continuity service. It belongs to Nova's base
architecture, and every Nova edition preserves the same contract whether it can
read durable Cognitive Continuity state or must declare a degraded mode.

Worldline is not a Faculty, task Augment, attached Augment, capability handle,
routing authority, store, or persistence engine. Cognitive Continuity remains
the capability owner for episodes, typed state, context compilation,
consolidation, correction, forgetting, transfer, validation, and receipts.
Worldline names a bounded user-facing service and read-only view over that
capability.

The Worldline wrapper never performs a canonical write. It cannot turn a view,
including a checkpoint view, into saved state or a persistence receipt. Send any
durable capture through a separate Cognitive Continuity transaction with its own
source, authority, concurrency guard, and receipt.

## Promise and negative space

For one user and project scope, Worldline makes it possible to inspect:

- what consequentially happened and changed;
- what was proposed, decided, and superseded;
- what the user and Nova committed to, with the available completion evidence;
- where the project stands, including blockers and next actions;
- which artifacts matter and where their canonical copies live;
- what a competent future task needs in order to resume.

Worldline is not a transcript archive, generic event log, omniscient life
manager, autonomous project manager, task router, or authority source. Capture
only state whose future absence could change responsible action. A polished
Worldline is a derivative view, never a second source of truth. Base-service
presence does not mean invoke it on every turn or claim durable state in an
ephemeral task.

## Four operations

Every edition exposes or truthfully degrades the same read-only operations:

- **Resume:** validate and compile current scope; prioritize current
  commitments, blockers, next actions, and a resumption pointer; expose material
  conflict or degradation; then let Nova continue the actual task.
- **Status:** return a concise current-state ledger with phase or status, current
  decisions, commitments, blockers, and only the chronology needed to interpret
  them. Status never proves completion and never changes project state.
- **Checkpoint:** return the broadest source-linked portable handoff projection
  that fits the declared budget. It remains ephemeral even when compiled from a
  healthy durable workspace; it is not capture, persistence, or a receipt.
- **Inspect:** prioritize provenance, conflicts, selected and omitted IDs,
  chronology, expiry, and why material surfaced. Inspect audits state rather
  than prescribing Nova's next action.

A request preserves its requested mode, user/project scope, as-of time, expiry,
sensitivity ceiling, budget, deadline, required IDs, and workspace-selector
descriptor. A successful runtime result uses the `cd-worldline-view/v1` contract
and reports the actual durability and source boundary. The exact API and CLI
entry points are documented in `../scripts/README.md`.

After resumption, query Faultline only when its cue applies. The bounded contract
is `faultline-error-neighborhood-contract.md`; Worldline does not absorb failure
records or Error Neighborhood routing.

## Preserve ownership

| Concern | Canonical owner | Worldline treatment |
|---|---|---|
| Episodes, typed records, lifecycle, receipts | Cognitive Continuity | Select and present a project-scoped view; never fork or mutate records. |
| Mission phase, acceptance, closure | Executive Function | Display current governed state without taking control custody. |
| User-authorized durable pursuit | Agent Striving | Reference the pursuit when relevant; do not duplicate it. |
| Loose explicit reminder | Corkboard | Leave the pin in Corkboard and point to it only when relevant. |
| People and relationship context | Dunbar | Leave governed people state in Dunbar and include only permitted context. |
| Artifacts and external sources | Their capability or repository | Keep stable locators and provenance, not unnecessary copies. |
| Raw errors, logs, telemetry, and repair | Their originating systems and capability owners | Leave raw material and repair custody in place; Faultline may expose a redacted advisory view. |

Worldline never turns remembered state into permission, a commitment into
completion, an inference into user truth, an artifact pointer into artifact
custody, or a status view into a routing decision.

## Use existing Continuity records

Map project-continuity concerns onto the existing Cognitive Continuity model:

- begin a consequential occurrence as a sourced episode;
- record an accepted choice as a `decision`;
- record an obligation as a `commitment`;
- express desired project state and operative next steps with `goal` and
  `commitment`;
- express current project interpretation as a sourced `belief`;
- express a blocker or known trap as `failure`, `belief`, or `hypothesis`
  according to what is actually known;
- record artifact significance through content, source IDs, and stable locators
  while the artifact remains with its canonical owner;
- derive a resumption point as a task-shaped context packet.

Do not invent an ad hoc record kind or overload an existing kind to make a view
look complete. If the current schema cannot express a consequential distinction,
preserve the source episode, expose the gap, and route a separately governed
schema proposal.

Keep facts, interpretations, proposals, user decisions, commitments, and
verified completion distinct. Completion requires the evidence named by the
goal or commitment; a confident summary, stale status, or tool attempt cannot
close it.

## Durable and portable delivery

Keep user and project isolation strict. Cross-project synthesis requires an
explicitly permitted scope and must not leak private records merely because they
are semantically related. Thread scope may narrow a view; it does not silently
replace project scope.

In a Nova distribution, resolve the active `NOVA_CONTINUITY_HOME` selector
through the governed registry and preserve Cognitive Continuity's
capability-owned custody. Do not hard-code a developer path or create Nova
continuity, people, reminder, pursuit, MIND, or persona state under `.codex`.
The selector locates policy; its presence does not prove a workspace or wrapper
is healthy.

If a durable source is missing, invalid, unsupported, unavailable, or exceeds
the deadline, any requested mode may return an `unpersisted_portable` checkpoint
only when the caller supplied sufficient source-linked material. Preserve the
requested mode, set `persisted=false` and `save_claim=false`, label the exact lost
guarantee, and issue no persistence receipt. Without sufficient material,
return a typed no-view result rather than an empty or invented project story.

A portable checkpoint is a re-entry artifact. Revalidate it against the durable
source when capability returns; do not silently promote it into canonical state.

## Runtime acceptance boundary

Establish project isolation, false-completion resistance, mode distinctions,
selected/omitted provenance, supersession, correction, export, deletion,
missing and corrupted source handling, deadline behavior, portable fallback,
and fresh-session resumption. Separately establish selector consumption and the
live host behavior being claimed.

This contract does not by itself prove package presence, installation,
discovery, invocation, persistence, or runtime health. Keep those evidence
states separate.
