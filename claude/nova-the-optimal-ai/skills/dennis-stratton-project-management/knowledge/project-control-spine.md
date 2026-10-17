# Project control spine

## Purpose

The control spine is the minimum durable structure that keeps a project intelligible across time, people, agents, repositories, and handoffs. It is not the project itself. It exists so reality can correct the plan without erasing authority or history.

Use the `cd-project-control/v2` record for substantial work when durable files are available. Keep one canonical record in the project's chosen custody. Render views from it; do not maintain rival hand-edited summaries as competing truth.

## Source authority

Rank sources explicitly by scope. A useful default inside an authorized project is:

1. current explicit owner decisions and corrections;
2. signed or accepted decision/change records;
3. the canonical project charter and roadmap for their declared scope;
4. the live repository and runtime for observable implementation facts;
5. current evidence and verification receipts;
6. prior task history and handoffs;
7. derived summaries, reports, or forecasts.

This is not a replacement for host/system instruction precedence. It is a project evidence rule. Two sources can both be authoritative for different scopes. Record freshness and scope instead of declaring a universal winner.

When sources conflict:

1. stop mutations that depend on the disputed fact;
2. identify each claim, source, scope, observation date, and consequence;
3. prefer current direct evidence for observable state and the named authority for decisions;
4. preserve unresolved disagreement;
5. ask the owner only if the remaining choice changes a material boundary.

## Hierarchy grammar

Represent the work as a stable parent chain:

`Project -> Phase or Stage -> Milestone -> Workstream -> Work package or Task`

Not every project needs every level. Every level used must earn a distinct planning or governance function.

Rules:

- IDs are stable even if labels improve.
- Every non-root node names one parent.
- A new naming system declares how it relates to the old one before use.
- Renaming, splitting, merging, or reparenting is a decision/change, not casual prose.
- Parallel workstreams may coexist, but the active status response names the relevant path.
- A plan that omits its parent does not erase the parent.
- The active commitment belongs to a hierarchy node and has one observable outcome.

At phase changes, long interruptions, corrections, and deep technical transitions, restate the path and purpose before continuing.

## Completion contract

Define done before execution. Select only the states relevant to the project, but never collapse states that change the owner's decision.

Common states:

- `PLANNED`: scope and acceptance exist; execution has not begun.
- `BUILT`: the intended artifact or change exists.
- `SOURCE_VALID`: canonical source meets its local structural contract.
- `VERIFIED`: named evidence supports the declared claim.
- `LOCALLY_CHECKPOINTED`: an authorized durable local checkpoint exists and its identity is known.
- `REMOTE_SYNCHRONIZED`: the intended remote contains the exact checkpoint.
- `DEPLOYED` or `INSTALLED`: an external/runtime placement occurred.
- `OPERATIONAL`: the deployed system performed the required live behavior.
- `ACCEPTED`: the authorized owner accepted the exact baseline and residual conditions.
- `COMPLETE`: every state required by the agreed completion contract is satisfied.

A milestone may be complete locally while remote synchronization remains pending only if the completion contract permits that. State the qualifier in the noun phrase; do not hide it in paragraph seven.

Before starting, surface any reserved action that will make the requested completion state unreachable. Do not wait until the closing report to unveil the trapdoor.

## Authority ledger

Every consequential constraint records:

- identifier and author;
- authority source and scope;
- exact actions permitted and reserved;
- rationale and risk addressed;
- effective date;
- expiry or reconsideration trigger;
- current status.

Classify a constraint as owner policy, external requirement, repository rule, technical limitation, or agent safeguard. Agent safeguards may guide reversible behavior, but they do not silently acquire owner authority. If a safeguard blocks the user's requested terminal state, surface it and ask for the necessary decision before the project burns time around it.

## Evidence and claim discipline

Track claims separately from artifacts. Each consequential claim names:

- claim text;
- level: proposed, reported, observed, verified, accepted, or rejected;
- locator and method;
- observation date;
- verifier or accepter when relevant;
- limits and missing guarantees.

Activity evidence answers what happened. Delivery evidence answers what became true. Acceptance answers who agreed to own the residual state. Value evidence answers whether the project produced the intended benefit.

## Control cadence

Use the least cadence that protects flow and truth:

- entry/re-entry: reconcile purpose, path, authority, and evidence;
- commitment start: state outcome, criteria, dependencies, and authority;
- short control interval: inspect blockers, WIP, evidence, and changed assumptions;
- correction/surprise: stop, diagnose, update the map, then resume;
- status moment: answer the governing question and request a decision if needed;
- milestone closeout: audit criteria, checkpoint, custody, residuals, and next location;
- project closure: confirm operations/benefits handoff and durable learning.

## Purpose re-anchor

For every active work package, be able to complete this sentence:

> This work enables [project outcome] by making [specific capability/state] true; its proof is [evidence].

If the answer becomes merely “because the plan says so” or “because the test is red,” stop and restore the connection. The implementation is not the product, and the dashboard is not the weather.