# Decision: Model Agnosticism is ambient discipline plus an earned callable instrument

Status: accepted
Date: 2026-09-04
Scope: Nova and MIND in every edition

## Decision

Model Agnosticism is part of Nova's basic cognitive architecture. It is not a separate product, hidden background process, universal proposition extractor, or numerical coating over ordinary work.

Its ambient behavior is qualitative: treat models as bounded instruments, preserve viable rivals, separate observation from interpretation and authority, and reopen the frame when evidence escapes the supplied models. Ordinary conversation does not incur a proposition inventory, mandatory rival enumeration, or fabricated probabilities. Unqualified “impossible” is reserved for logical contradiction; hard-constraint impossibility is explicitly scoped to the named constraints, and model-relative exclusion is described as such.

Trellis is one stateless, capability-neutral, deterministic HMM instrument. Any capability may invoke it when all of the following are true: the consequential question concerns a sequential partially observed process; a first-order Markov state process, conditionally independent emissions, and parameters stationary over the declared window are defensible approximations or explicit stress-test assumptions; observation and step semantics are explicit; model parameters are defensible evidence inputs or expressly declared scenario assumptions; and the result can alter a decision, inquiry, or controlled action. The invoking capability constructs the machine inputs backstage and retains question, evidence, interpretation, and receipt custody. The user is not made into a JSON clerk.

Trellis has two formal lanes. evidence_update supports conditional evidential comparison only under stronger predeclared candidate, parameter, prior, observation, and calibration gates. assumption_stress_test performs transparent what-if arithmetic and labels every probabilistic output scenario-only and conditional on the stipulated assumptions. Neither lane turns model output into truth, generic confidence, persistence, permission, or decision authority.

Measurement Intelligence governs constructs, observation encoding, cadence, missingness, disclosed dependence, and calibration. Epistemic Regulation governs claim warrant and interpretation. Decision Intelligence combines the result with values, costs, reversibility, and authority. Agent Striving may consult Model Agnosticism at re-entry, surprise, or repeated failure, but cannot turn a posterior into project fact or silently change the user's goal. Other capabilities use the same contract rather than receiving duplicated local variants.

## Accepted v2 disclosure contract

Time is explicit and deliberately conservative. `analysis_as_of`, `event_time`, and `known_at` use timezone-bearing RFC-3339 with optional one-to-six-digit fractional seconds, matching the runtime's microsecond ceiling. Event order is strict. Historical-prefix interpretation additionally requires `known_at` to increase strictly; equal knowledge timestamps represent a batch and force retrospective event-order interpretation rather than quietly asserting an as-known-then sequence.

Finite-log underflow remains different from structural zero. A posterior component may display linear `0.0` while retaining a finite entry in `posterior_log_probabilities` and its index in `posterior_finite_log_underflow_state_indices`; structural zero carries a null log value and its index in `posterior_structural_zero_state_indices`. A relative weight with finite-log underflow has `weight_status: underflow`, finite `log_weight`, null linear weight, and makes `linear_weights_complete` false. Structural zero has `weight_status: exact_zero`, null log weight, and linear `0.0`. Logs and explicit statuses govern interpretation; display zeros do not get to counterfeit impossibility.

Evidence semantics are a second gate over valid arithmetic. `evidence_gate: passed` yields `effective_interpretation: conditional_evidence_update`; a failed evidence lane yields `diagnostic_only` even if comparison weights compute; an assumption stress test makes the gate not applicable and yields `scenario_only`. Observation-mapping, parameter, prior, and calibration provenance must be exact structured records. Evidence use further requires non-stipulated provenance fixed before the sequence, plus candidate selection and stopping fixed before the sequence; otherwise the result is diagnostic rather than evidential.

Calibrated fit remains declared-threshold arithmetic, not an empirical blessing conferred by JSON. `calibration_target_digest` binds the sorted candidate identities and ordered predictive kernels, observation and stopping contracts, and minimum and maximum observation counts. A target mismatch or sequence outside those bounds leaves fit unassessed and fails the evidence gate. Calibration truth remains explicitly unvalidated.

Every model has one unique `comparison_unit_id`; repeated units are rejected as `DUPLICATE_COMPARISON_UNIT`. Byte-identical ordered predictive kernels are rejected as `DUPLICATE_PREDICTIVE_KERNEL`. This catches declared duplicates, not every mathematically equivalent parameterization: the ordered-kernel screen is not invariant to state permutation, and `general_observational_equivalence_validated` remains false. Custodians must identify known equivalents with the same comparison unit so validation rejects them; that declaration still does not prove general equivalence.

Analysis receipts keep claim confidence, truth certification, source-confidence mutation, integrated parameter uncertainty, provenance truth, calibration truth, observational equivalence, candidate-selection truth, stopping-rule truth, observation independence, decision authority, and persistence explicitly false; authority effect remains none. Validation receipts establish structural and stochastic conformance only, leaving ontology, semantic truth, calibration truth, equivalence, provenance truth, selection truth, stopping truth, and independence false.

## Consequences

There is no daemon, hook, learned extractor, automatic numerical invocation, shared hidden state, or per-capability Trellis copy. If defensible numbers or stable sequential semantics do not exist, Nova stays qualitative.

The deterministic engine validates explicit versioned artifacts, exposes its numerical assumptions and normalization, refuses declared evidence dependence it cannot model, distinguishes evidence from scenarios, and requires reframing when the bounded model parliament cannot responsibly answer. Its output remains a derived receipt under the invoking capability's custody.

This decision supersedes any reading of the earlier Faculty examples as an exhaustive routing list or of a supplied-model zero as a claim that reality itself forbids an event.
