# Faultline and the Error Neighborhood

## Contents

- [Architectural place](#architectural-place)
- [Activation cues and anti-cues](#activation-cues-and-anti-cues)
- [Bounded read view](#bounded-read-view)
- [Evidence and causality boundary](#evidence-and-causality-boundary)
- [Custody and persistence](#custody-and-persistence)
- [Authority and action boundary](#authority-and-action-boundary)
- [Deterministic surface](#deterministic-surface)
- [Acceptance boundary](#acceptance-boundary)

## Architectural place

Faultline is MIND's named bounded error-recall surface. It presents an Error
Neighborhood derived from Cognitive Continuity failure evidence so Nova can
notice a nearby known trap without turning memory into a control system.

Faultline is not a Faculty, attached Augment, capability handle, router, store,
telemetry sink, permission source, causal engine, repair engine, or procedure
installer. It changes no Faculty count. Cognitive Continuity owns the redacted
occurrences, governed failure patterns, lifecycle, source links, expiry,
transactions, and receipts. The originating system owns raw logs and telemetry;
the capability responsible for the failed operation owns diagnosis and repair;
Capability Conductor retains routing custody.

## Activation cues and anti-cues

Compile an Error Neighborhood:

- before a materially similar risky operation; and
- after an error, correction, or resumption, using the current operation and
  environment boundary.

Material similarity requires an operation, tool/provider, error class,
environment, or governed pattern match that could change the next check or
safety posture. Mere complexity, generic risk language, topical resemblance, or
an Arm's Reach association is not enough.

Do not poll Faultline on every turn, turn every failure into a pattern, or retry
an unavailable neighborhood under unchanged conditions. After expiry or a
material scope, source, environment, version, authority, or operation change,
compile a fresh view rather than reusing cards.

## Bounded read view

The read-only view uses `cd-error-neighborhood/v1` and contains zero to three
cards. Every card and the view itself expire; callers select one to sixty
minutes, with ten minutes as the ordinary default. Do not carry an expired card
forward as advice.

Filter before selection by user/project/thread scope, sensitivity ceiling,
source reachability, lifecycle and expiry, environment and version, and the
current operation boundary. Preserve candidate, eligible, and selected counts,
degradation, the empty meaning, and the capability-value boundary. A deadline
produces the typed empty `deadline_exceeded` result rather than an unbounded
search or fabricated advice.

An empty Error Neighborhood means only that no eligible known card survived the
declared scope, filters, source reachability, and time boundary. Empty never
means safe, no prior failure, no unknown risk, or permission to proceed.

## Evidence and causality boundary

Keep two evidence classes visible:

- an occurrence-only card reports a redacted observed failure as a lower-bound
  observation; and
- a governed-pattern card reports a human-accepted failure pattern with its
  trigger, symptom, avoid, do, verify, lifecycle, expiry, source evidence, and
  field-level authority.

Recurrence and similarity never prove cause. Collapse retries of the same
operation/source event; missing identity never increases a recurrence count.
Treat causal state as unknown or hypothesis until separately governed evidence
supports verification. A mitigation that worked once is outcome evidence, not a
universal repair rule.

Do not convert a frequent symptom into a diagnosis, a matched card into proof
that the present event has the same cause, or a quiet neighborhood into a safety
claim.

## Custody and persistence

Never ingest or persist raw logs, transcripts, stack dumps, credentials, tokens,
secrets, private payloads, or unnecessary path-shaped evidence. Leave them in
their originating custody. Capture only a minimal redacted structured occurrence
with scoped source pointers and one-way operation/source-event identities.
Reject or sanitize secret-shaped and path-shaped material before a transaction.

All persistence is a governed Cognitive Continuity v2 operation. Require the
workspace generation, idempotency key, authority, scope, sensitivity, retention,
and source evidence appropriate to the mutation. A pattern proposal is
noncanonical. Applying or transitioning a pattern requires human-governed
authority, selected field acceptance, source reachability, and a mandatory
finite expiry. Preserve conflicts and supersession rather than editing history.

Faultline has no private cache or fallback store. Continuity v1 reports Faultline
as typed unsupported; do not migrate, initialize, or write a workspace merely to
make a card appear. An externally custodied output file is a derivative view,
not canonical failure state.

## Authority and action boundary

Cards are advisory evidence. They may suggest an avoid step, a bounded next
check, or a verification condition only within the authority recorded for that
field. They cannot:

- grant permission or enlarge the user's authorization;
- route a Faculty or capability;
- execute, retry, repair, suppress, or close an operation automatically;
- prove cause, repair, correctness, completion, or safety;
- create a durable objective; or
- promote a pattern into a procedure, SKILL, or Augment.

Route repeated procedural evidence through
`procedural-learning-handoff.md`. Construction, installation, and use retain
their normal human and capability gates.

## Deterministic surface

Use `../scripts/error_neighborhood.py` for the v2 surface:

- `capture` records one redacted structured occurrence;
- `pattern-propose` creates a noncanonical candidate;
- `pattern-apply` accepts selected advice fields under human authority and finite
  expiry;
- `pattern-transition` supersedes a pattern with governed cause, resolution, or
  lifecycle evidence; and
- `neighborhood` compiles the zero-to-three-card read view.

Every mutation requires explicit expected generation, idempotency key, and
authority. Pattern application and transition require human-prefixed authority.
Read `../scripts/README.md` for entry points and use command help for the full
argument set.

## Acceptance boundary

Exercise cue and anti-cue routing; zero, one, and three cards; expiry; deadline;
empty semantics; retry collapse; missing identity; recurrence without causal
overclaim; environment/version mismatch; unreachable sources; sensitivity and
scope isolation; redaction; secret/path rejection; v1 unsupported behavior;
field-level authority; noncanonical proposals; human apply/transition; and
absence of automatic repair, routing, procedure promotion, or permission.

A passing schema alone does not establish those behavioral claims. Keep static,
package, fresh-process, live-host, and external-system evidence separate.
