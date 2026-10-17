# Typed State Prevents Fluent Amnesia

One summary cannot safely carry every kind of continuity. Type records by the future behavior they govern.

| Kind | What it preserves | Decisive fields or treatment |
|---|---|---|
| identity | the Agent's assigned role and behavioral contract | owner, scope, version, authority; persona alone is insufficient |
| user_model | explicit preferences, stable working constraints, and user-provided context | distinguish direct assertion from inference; minimize sensitive inference |
| relationship | how this Agent and user collaborate | interaction pattern, history anchors, boundaries; never imply subjective attachment |
| permission | what action is authorized | grantor, scope, action, target, expiry, revocation, conditions |
| goal | desired world-change | owner, state, priority, dependencies, success evidence |
| commitment | an obligation to act or refrain | promisor, beneficiary, due condition, status, completion evidence |
| belief | current working conclusion | claim, entitlement, evidence, alternatives, confidence, valid time |
| decision | selected course and rationale | decision owner, alternatives, rationale, date, reopening condition |
| procedure | reusable method or external SKILL reference | provenance, preconditions, outputs, validators, failures; candidate is not installation |
| failure | known trap, failed path, or override | trigger, observed consequence, recovery, scope, verification |
| hypothesis | live possibility | source anchors, leap beyond evidence, counterevidence, test, expiry |

## Record spine

Every consequential record carries:

- stable `id`, `kind`, and `status`;
- `scope` for user, project, Agent, and optional thread;
- concise `content` native to its kind;
- `valid_from`, optional `valid_to`, and `recorded_at`;
- `source_ids`, source class, and source locator;
- contextual `authority` and `confidence` or `entitlement`;
- `sensitivity`, retention, and optional expiry;
- `supersedes`, `conflicts_with`, and `derived_from` links;
- governance metadata recording the last accepted operation.

## State is not an answer key

Current means authorized for ordinary use, not universally true. Beliefs may remain uncertain. Decisions may later reopen. Permissions may expire or be revoked. Commitments may be completed or released. A record's kind determines what evidence and authority can change it.

Preserve one canonical machine-readable record and derive Markdown views. Do not let a polished report become a second source of truth.
