---
name: agent-swarm-orchestration
description: "🐝 Design, coordinate, and adapt temporary agent organizations: contributions, relations, information flow, authority, execution, synthesis, and change."
---

# Design the organization the work needs

Hold one user-authorized mission. Shape a temporary organization only when its structure can improve the accepted outcome after startup, duplicated reading, communication, waiting, merge, verification, correction, latency, and token cost. Keep one accountable root responsible for mission truth, authority, shared state, integration, and the final claim.

Treat organizational form as a working hypothesis for the current reasoning horizon. A bucketline, anthill, platoon, boardroom, general staff, complex adaptive system, or any other analogy is useful only for the causal mechanics it contributes. Borrow, hybridize, invert, rename, or invent forms as the task changes. Never mistake the examples for a closed taxonomy.

Start from the work already present. Recover the outcome, acceptance, current evidence, constraints, user corrections, authority, budgets, and live host affordances. Ask only when an unknown changes the goal, risk, architecture, authority, or next consequential move.

Preserve the difference between a stated premise and an absent dependency. If the task states that artifacts, inputs, workers, or returns exist, reason from that premise even when their bytes are not pasted into the prompt; do not reclassify them as missing. If a required source is actually unavailable, stop the dependent slice before designing it. Return only the missing source, the exact method that would identify or read it, the name and objective of the downstream slice held pending that source, and any independent authority conclusion. Do not fill the hold with generic tests, schemas, paths, endpoints, acceptance criteria, sample data, or implementation ideas.

Continue every safe, authorized part of the mission without asking for permission already granted. When one proposed action crosses an authority edge, refuse or reserve that action while completing and reporting the in-bounds analysis, preparation, or comparison. When the user expressly prohibits an action, close that branch; do not draft it, preserve it as a future option, or propose later reauthorization unless the user reopens it. Do not turn a narrow authority limit into a full-task stop.

Distinguish missing authority from a missing source, tool, or execution primitive. Never report `AWAITING AUTHORITY` when the user already authorized the action but the host cannot perform it. If mutation cannot execute, prepare the exact bounded change when its target is known, name the unavailable capability, and report the corresponding truthful degraded state. The absence of live mutation is not authoritative post-state readback: never claim that files, state, or external systems remained unchanged without observing them.

## Load only the doctrine that changes the decision

Read `references/operating-doctrine.md` once per task before any admitted delegation; reload it only after context loss or a material phase change. For a consequential or non-obvious organization, also read `references/organization-design.md` and `references/interaction-resolution-and-adaptation.md`.

Load the smallest additional reference that changes the live work:

- `references/pattern-recipes.md` for worked provocations, borrowed mechanisms, failure modes, and hybridization;
- `references/topology-and-admission.md` for the Direct/Enlist/Assemble/Chain/Recover execution kernel, dependencies, concurrency, and ownership;
- `references/delegation-and-context.md` for contribution cards, worker selection, context forks, packets, isolation, and returns;
- `references/coordination-and-control.md` for live tool semantics, messages, waits, interruption, steering, transitions, and closure;
- `references/evidence-merge-and-review.md` for evidence levels, resolvers, dissent, shared artifacts, verification, and independent challenge;
- `references/cost-authority-and-recovery.md` for whole-organization cost, permissions, sensitive material, stalls, collisions, experiments, and recovery;
- `references/qualification-and-evaluation.md` before promoting a recipe, role, interaction rule, or adaptive policy into a default;
- `references/source-and-currentness-register.md` before relying on volatile host or research claims.

## Shape the organization before spawning it

For the next reasoning horizon, ask:

1. What kinds of contribution could materially change the result?
2. Why might each add a different useful signal—or why is redundancy intentionally valuable?
3. Which contributions should remain independent, and which should interact?
4. What may cross each relation, to whom, when, and for what transformation?
5. By what operation do returns become one result, and who owns that decision?
6. What state is shared, private, append-only, or canonically writable?
7. What observation should recruit, release, rewire, change phase, or stop the organization?

These are coupled thinking lenses, not mandatory form fields. Keep them implicit for light work. Create only the artifacts that retire a live ambiguity, authority, state, interaction, or closure risk; never instantiate the whole toolkit ceremonially. For consequential, ambiguous, long-running, or adaptive work, resolve `assets/organization-sketch.template.md` from this skill root. Use `assets/contribution-card.template.md` only for members whose causal jobs need explicit inspection.

A named persona may make a stance memorable or perturb search usefully. It never by itself establishes competence, independence, evidence, or authority. Every admitted contribution still needs distinct evidence, transformation, capability, error opportunity, containment, check, or justified redundancy and a named consumer.

When affected people or stakeholders matter, use attributable evidence, label modeled positions, and preserve actual participation and reserved value choices for the humans who own them. Agents do not become legitimate representatives by speaking in character.

## Compile one phase into the execution kernel

Choose one literal regime for the next bounded horizon:

- **Direct:** the root acts with no worker.
- **Enlist:** one bounded worker augments root work.
- **Assemble:** at least two independent ready slices run concurrently under explicit ownership and merge.
- **Chain:** at least two sequential stages; each accepted return becomes the next stage's exact input.
- **Recover:** useful state is retained while a failed or stale premise, route, owner, tool, sequence, or verifier changes.

Do not create contradictory labels such as “Direct with a worker.” An organization may move through several regimes over time, but each live phase must have a legible control shape. Cognitive influence may cycle through bounded review rounds; execution and evidence history remain event-ordered and inspectable.

Do not spawn merely because agents are available or a metaphor sounds apt. Compare with a strong Direct route and the nearest simpler organization. Also do not fetishize minimum headcount: purposeful redundancy, independent confirmation, exploration, incubation, or containment can justify apparently duplicate work when the causal reason, cap, and resolver are explicit.

For consequential, multi-turn, or recovery-prone work, build `assets/swarm-plan.template.json` for the current execution horizon and validate it from the packaged skill root:

`python <skill-root>/scripts/validate_swarm_plan.py <swarm-plan.json>`

The v1 plan validates literal regime shape, accepted dependency readiness, authority as a subset of the root grant, non-empty evidence burdens, dependency references and cycles, safely sequenced versus simultaneous write ownership, and terminal consistency. It does not validate synergy, competence, factual correctness, or organizational value. Never present a `cd-agent-swarm-plan/v1` object unless the packaged validator passes. When validation cannot run, use compact prose instead of unchecked structured JSON.

## Give each member a causal contribution

Map dependencies rather than making a shopping list. A ready slice has its required inputs, one coherent transformation, no hidden dependency on another active slice, an explicit consumer, and single-writer ownership for mutable surfaces.

Compose each dispatch from `assets/delegation-packet.template.md`. State the contribution objective and differentiator, exact deliverable, evidence burden, context and visibility, included and excluded scope, authority, read and write surfaces, relationships and consumers, return shape, completion, and release or escalation condition.

Choose the smallest context fork that preserves success. Withhold irrelevant transcript, the coordinator's preferred answer, evaluator oracles, and other workers' conclusions when independence matters. Use fresh context for hostile review and competing hypotheses. Use inherited context when reconstructing settled mission context would be lossier or costlier. Minimize sensitive material in every packet.

For bounded interaction after an independent pass, use `assets/cross-response-packet.template.md`. Expose only named contribution fields, ask for one transformation, identify the output consumer, and cap the round. All-to-all dialogue and complete transcript broadcast require a causal reason.

## Coordinate through the live host contract

Inspect the injected collaboration tools before dispatch. Spawn, message, follow-up, wait, interrupt, context-fork, model-route, nested-delegation, and concurrency behavior are live contracts, not folklore.

Root-owned spawning is the normal control shape because it keeps authority, budget, conflicts, and closure visible. Nested delegation is an option when the host permits it, the parent owns a bounded subproject and child merge, and the root can still observe the control state.

Continue useful root work while workers run. Use messages to change task state: correction, evidence pointer, scope, authority, relation, exposure, or return request. Wait eventfully only when a return blocks the next move; do not poll unchanged state.

When the user adds, corrects, narrows, replaces, pauses, or cancels the mission, update root custody first. Redirect compliant work in place. Interrupt only work whose objective or authority disappeared or cannot be safely narrowed. After redirect or interruption, label prior write and commit state `unknown` until authoritative readback; interruption is not rollback evidence.

## Observe contribution, then reform deliberately

Track what the organization contributes: new evidence, independent errors caught, transformations completed, uncertainty reduced, acceptance advanced, errors introduced, contamination, stalls, latency, cost, and merge loss.

Recruit when a named uncertainty needs a new evidence channel, transformation, capability, containment boundary, or check. Add a round only after a discriminating disagreement, failed check, or unresolved criterion. Release when a contribution is accepted, redundant, dominated, blocked, off the critical path, or no longer authorized. Change exposure or resolver when the current interaction cannot settle the live conflict. Recover from the first unearned edge rather than replaying the whole choreography.

At a material transition, use `assets/organization-transition.template.md`. Record the observation, reform, worker dispositions, authority, next regime, and whether task truth, progress, evidence, scratch, and artifact state are retained, superseded, invalidated, discarded, or re-derived.

## Resolve without inventing an oracle

Receive every worker through `assets/agent-return.template.md` or an equivalent compact return. A return is **agent-reported** until the root observes the cited source, artifact, command result, hash, or external state.

Choose the resolver separately from the communication pattern: union and deduplication, objective test, evidence-weighted selection, critic-guided revision, integrative synthesis, bounded adjudication, root decision, or human decision. Maintain `assets/merge-ledger.template.md` where claims, artifacts, roles, or evidence can conflict.

Preserve minority evidence when it is stronger, unresolved, value-bearing, or capable of exposing common-mode error. Resolve factual conflict with authoritative evidence or a discriminating observation. Return value, priority, risk acceptance, or new authority to its human owner. Agent agreement after shared anchoring is not independent corroboration.

Verify the merged result at the lowest layer that can expose the real failure. Use a fresh independent reviewer when its expected value exceeds its cost, withholding the builder's intended verdict and hidden rubric. Easy successes cannot cancel a failed authority, safety, ownership, source, or indispensable acceptance condition.

## Recover the goal and dissolve the organization

When a member stalls, fails, loses context, overruns, collides, contaminates peers, or returns unusable evidence, preserve the useful delta and failure signature. Change the decomposition, context, contribution, relation, exposure, model, tool, owner, sequence, resolver, or verifier before retrying. Reassign only the unearned edge.

Use truthful degraded states: `PREPARED — NOT DISPATCHED`, `RETURNED — NOT RECONCILED`, `PARTIAL — DEPENDENCY UNAVAILABLE`, `AWAITING AUTHORITY`, `CAPABILITY-LIMITED`, or `CANCELLED`. State exactly what the evidence supports.

Before completion, disposition every created responsibility; reconcile shared state and material claims; verify the integrated result to its stated boundary; release or dissolve members that no longer own work; and return one coherent result in the user's requested form. The temporary organization exists to finish the mission. It is not a tiny bureaucracy seeking immortality.
