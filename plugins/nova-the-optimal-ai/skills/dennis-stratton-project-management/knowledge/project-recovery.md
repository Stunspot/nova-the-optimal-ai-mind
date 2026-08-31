# Project recovery and reconciliation

## Trigger conditions

Enter recovery or reconciliation when any of these occur:

- the user or team cannot say where the project is;
- Phase, milestone, version, or completion labels conflict;
- status claims contradict repository or runtime evidence;
- a model-authored constraint blocks the owner's intended outcome;
- repeated failures are being patched without a causal diagnosis;
- the project is persistently late, over budget, blocked, or losing stakeholder trust;
- the plan's purpose has disappeared beneath implementation machinery;
- leadership, authority, or core assumptions changed;
- work resumes after an interruption long enough for state to drift.

## Immediate rule: stop deepening ambiguity

Pause mutations whose correctness depends on the disputed state. Do not keep coding, committing, scheduling, or messaging while reconstructing the map. Preserve work already earned.

State the recovery question plainly: what must be reconciled before safe progress resumes?

## Reconciliation sequence

### 1. Reconstruct authority and purpose

Identify the project owner, current explicit corrections, accepted decisions, canonical charter/roadmap, and the product outcome. Separate user policy, repository rule, external constraint, technical limitation, and agent safeguard.

### 2. Reconstruct hierarchy

List every active naming system. Map each label to Project -> Phase/Stage -> Milestone -> Workstream/Task. Locate missing parents, duplicates, renames, and abandoned labels. Do not guess away a consequential ambiguity.

### 3. Reconstruct observable state

Inspect the live repository, artifacts, tests, runtime, external systems, and evidence receipts within authority. Distinguish:

- planned versus attempted;
- created versus valid;
- verified versus accepted;
- local checkpoint versus remote synchronization;
- deployed versus healthy;
- output versus outcome.

### 4. Reconstruct the completion contract

Find what done was supposed to mean. If it was never agreed, propose the smallest explicit contract that matches the user's intended terminal state and current evidence. Surface any reserved action that makes it unreachable.

### 5. State the discrepancy

Use a compact table or prose:

- prior shared belief;
- current evidence;
- authoritative correction;
- affected scope;
- unaffected earned work;
- decision required.

### 6. Restore one location

Produce one sentence such as:

> Project Atlas is in Phase 4; M0 is verified and locally checkpointed; remote synchronization is pending; M1 has not started.

Update the canonical control record and terminology/decision log when authorized. Resume only from that shared location.

## Troubled-project triage

After reconciliation, decide among:

- continue with a bounded corrective action;
- recover under a temporary control cadence;
- re-contract scope, authority, resources, schedule, or benefits;
- pause pending an external condition;
- cancel because remaining cost/risk exceeds value or the purpose is invalid.

Do not assume every project deserves rescue. Sunk cost is historical evidence, not a hostage negotiator.

## Recovery operating cycle

### Understand and audit

Inspect the baseline, evidence, dependencies, architecture/integration, resource reality, stakeholder incentives, contract constraints, controls, and current work. Interview relevant actors when authorized. Identify causal mechanisms, not blame targets.

### Stabilize

Freeze or defer non-critical changes, reduce WIP, protect the bottleneck, eliminate useless meetings/reports, establish a short control interval, resolve decision rights, and create a recovery checkpoint. Preserve safety and mandatory obligations.

### Reset and rebaseline

Define must-have outcomes, re-estimate from demonstrated throughput and current constraints, sequence the highest-risk interfaces early, assign owners, fund treatments, update scope and forecasts, and obtain authorization for the new baseline. A rebaseline without an owner decision is merely schedule slippage with nicer typography.

### Execute and hand over

Run short evidence-bearing commitments, record causes of misses, adapt the next interval, and monitor truthfulness as well as output. When flow stabilizes, return controls to the normal project cadence and preserve the recovery lessons.

## Failure diagnosis discipline

Before repair, articulate:

1. specific choice or condition;
2. mechanism by which it caused the symptom;
3. project or technical invariant violated;
4. bounded corrective action;
5. evidence that would prove restoration;
6. guarantees still missing.

Do not route by accumulating exceptions around an unexplained failure. If a test is invalid, preserve that separately from product evidence.

## Self-authored restriction audit

For any blocking rule, ask:

- Who authored it?
- What authority did they have?
- What risk was it meant to control?
- Which exact action does it block?
- Does it conflict with the owner's requested terminal state?
- What is its expiry or reconsideration trigger?

If the model invented the restriction, say so. Retain any useful risk insight, but return the decision to the owner. This converts process armor back into a proposal.

## Recovery output

A useful recovery checkpoint contains:

- restored purpose and hierarchy;
- frozen or preserved state;
- verified facts and disputed claims;
- root constraints and causal model;
- triage decision;
- authorized scope and baseline;
- active controls and escalation thresholds;
- first three short commitments;
- repository/custody state;
- residual risks and next review.