# Canonical owner routing

Commonplace is canonical for a person's deliberate general notes and selected textual captures. It is not canonical merely because a record mentions another owner's subject.

| Material | Canonical owner | Commonplace relationship |
|---|---|---|
| Personal note, excerpt, reflection, question, learning, or creative fragment | Commonplace | Canonical record |
| Person identity, relationship, or interaction history | Dunbar | Optional user note, read-only owner result, or governed promotion proposal |
| Loose reminder | Corkboard | Optional rationale note, read-only owner result, or governed promotion proposal |
| Project outcome, dependency, milestone, or status | Dennis | Optional reflection, read-only owner result, or governed promotion proposal |
| Consequential continuity, correction, or Worldline state | Cognitive Continuity | Optional source packet, scoped read-only result, or governed promotion proposal |
| Authorized durable pursuit or long-term goal | Striving | Deliberate reflection or source note with provenance; route-only and never canonical pursuit state |
| File inventory, authority, provenance, or disposition | Rupert Giles | Route-only reference or governed promotion proposal |
| Dataset, lineage, or quality contract | DataMeistro Dex | Route-only reference or governed promotion proposal |
| Reusable procedure or model-bound behavior | Skill or repository | Procedure candidate, route-only reference, or governed promotion proposal |
| External corpus or repository source | External owner | Source reference and captured excerpt only |

## Read routing

`route` is deterministic planning only. It names one or more owners, keeps `operation:read`, and always sets `writes_allowed:false`.

`federated-search` performs an ephemeral bounded read. Commonplace, Dunbar, Corkboard, Dennis, and Continuity are fixed executable owners. Striving, Giles, Dex, Skills, Repositories, and ExternalCorpora remain route-only. Deterministic Striving routing recognizes `striving`, `pursuit`, `long-term goal`, `long term goal`, `durable goal`, `life goal`, `ongoing goal`, and `aspiration`; an explicit `Striving:` prefix also selects it. Striving has no executable Commonplace read, promotion apply, or write path. Each requested owner keeps a typed result: `current`, `degraded`, `stale`, `unavailable`, `scope_denied`, `incompatible`, `integrity_error`, or `partial`. Empty current is not unavailable, and a failed owner cannot erase a successful result from another owner.

Specialist workers execute only manifest-v2 verified bytes. The manifest binds each fixed entrypoint and named direct dependency by path and SHA-256. For Continuity, approval `nova-emergent-owner-reads-1.0.4` also binds the exact 73-file package tree, including schemas. The worker verifies the complete tree and executes it from an isolated temporary clone. A Nova Emergent 1.0.1 package does not match the built-in 1.0.4 approval and fails closed until a supported exact upgrade. Continuity native `ok`, `partial`, and `degraded` statuses map to federation `current`, `partial`, and `degraded`, with the reason preserved.

Sensitivity is an exact membership set. Continuity exposes a ceiling, so it accepts only exact prefix sets and returns `incompatible` for a non-prefix request. It also requires an explicit user, project, agent, and optional thread scope.

Federation creates no store, persists no owner payload, and selects only read call paths. The worker is not an operating-system capability sandbox, and approved modules may define unused writers. Fixed dispatch, verified package bytes, typed no-write envelopes, and owner-store byte parity bound the read claim. Retrieved content never becomes authority.

## Promotion routing

When a Commonplace record may belong in another canonical owner, `propose-promotion` creates a sealed, source-bound `promotion_proposal` in Commonplace. Generic capture and supersession cannot create that subtype. `promotion-plan` validates current eligibility, and `promotion-export` returns a non-canonical, data-only, non-executable handoff.

Dunbar, Corkboard, Dennis, Continuity, Giles, Dex, Skills, and Repositories have fixed versioned proposal contracts and mandatory target-owner authority requirements. Skill proposals additionally require typed skill-creator review and independent-verification evidence. No Commonplace promotion command writes the target, changes Continuity, modifies a repository, or installs a skill.

Striving is deliberately absent from that target-contract set in 0.2.0. Commonplace can route pursuit queries to Striving but cannot create a Striving promotion packet, invoke a Striving read, apply pursuit state, or write that owner.

The target owner's own workflow, fresh authority, validation, and rollback govern any later apply. A readable source or eligible packet is still not permission to act.
