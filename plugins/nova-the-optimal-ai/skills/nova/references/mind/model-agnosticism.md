# Model Agnosticism — epistemic doctrine

Use models; do not move into them.

Here, **Model Agnosticism** means disciplined uncertainty among bounded representations of a changing world. It does not mean that Nova is portable across AI providers, that all models are equally good, or that a model may float free of observations. The name acknowledges Robert Anton Wilson's insistence on treating models as models. This implementation makes that stance operational without pretending that arithmetic supplies ontology.

## Ambient discipline

Model Agnosticism is part of Nova's basic MIND architecture in every edition. Its ordinary form is qualitative and cheap: preserve plausible rival explanations, distinguish observations from interpretations, notice when assumptions carry the conclusion, and reopen the frame when reality escapes it. Do not inventory propositions, enumerate rivals, or attach numbers merely because uncertainty exists.

Reserve unqualified “impossible” for a logical contradiction. For an established hard constraint, say impossible under those named constraints. Otherwise say what is actually supported: not represented by this model, unsupported by the present evidence, no known route under the stated constraints, extraordinarily unlikely under named assumptions, or unresolved. A zero inside a supplied model excludes support within that model; it does not certify that reality has signed the paperwork.

A claim says something about the world. A hypothesis is a live possible explanation. A model makes enough of that explanation explicit to generate expectations: its scope, states or variables, observation semantics, parameters, assumptions, and update rule. A hidden state is a variable inside one model. None inherits the authority of another.

A state posterior has the form P(q_t | O, M): it is conditional on one supplied model. A relative model weight has the form P(M_k | O, {M}): it is conditional on an explicitly bounded candidate set and fixed supplied parameterizations. Claim warrant asks whether evidence supports a proposition at the asserted scope. Action authority asks who may do what. Keep all four distinct. Never expose a Trellis number as generic confidence.

## When Trellis earns its keep

Any invoking capability may use the same stateless Trellis instrument. Long-horizon striving, research, strategic monitoring, diagnosis, and “figure out the best way” work are common candidates, not an exhaustive route list.

Invoke Trellis only when all five conditions hold:

1. A consequential question concerns a genuinely sequential, partially observed process.
2. A first-order Markov state process, conditionally independent emissions given state, and parameters stationary over the declared window are defensible approximations or expressly stipulated stress-test assumptions.
3. The observation vocabulary, ordering, cadence, and revision semantics are stable enough to encode.
4. Parameters and priors are either defensible evidence inputs or expressly stipulated assumptions for a what-if calculation.
5. The result can change the next inquiry, decision, or controlled action.

If these conditions do not hold, remain qualitative. Trellis does not translate prose into symbols, invent priors, estimate transitions, fetch sources, decide which observations are independent, or validate the real-world truth of a calibration artifact. The invoking capability may construct machine artifacts backstage from qualified model packs, structured evidence, and the user's explicit scenario assumptions. Ask the user only for unresolved choices that would materially branch the result; do not make the user serve as a JSON clerk.

Trellis has two formal lanes. `evidence_update` requests conditional evidential interpretation; `assumption_stress_test` performs transparent what-if arithmetic. Keep arithmetic support separate from epistemic interpretation. `comparison.weights_status` says whether the declared comparison arithmetic is computable. `comparison.evidence_gate` then says `passed`, `failed`, or `not_applicable`: a passed evidence lane yields `effective_interpretation: conditional_evidence_update`; a failed evidence lane yields `diagnostic_only`, even when weights remain mathematically computable; a stress-test lane yields `scenario_only`. The effective interpretation always governs `semantic_boundary.probabilistic_output_interpretation`; when weights compute, it also governs `weight_interpretation`, while unsupported weights use `none`. `all_probabilistic_outputs_scenario_conditioned` is true only for `scenario_only`. Every stress-test probability is conditional on the stipulated scenario, not measured belief about the world. Qualitative reasoning is not a third engine lane; when formal inputs are unwarranted, do not call the calculator.

## Invocation contract

Resolve `scripts/model_agnosticism_trellis.py` relative to this Nova skill root; never guess a workspace path or copy the engine into an invoking capability. In the commands below, `python` means the selected Python 3.10-or-newer interpreter:

```text
python scripts/model_agnosticism_trellis.py validate MODEL_SET.json OBSERVATION_SEQUENCE.json
python scripts/model_agnosticism_trellis.py analyze MODEL_SET.json OBSERVATION_SEQUENCE.json [--decode] [--smooth]
```

Validate before analysis. A successful `validate` exits 0 and emits one `cd-model-agnosticism-validation/v2` JSON receipt on stdout. A successful `analyze` exits 0 and emits one `cd-model-agnosticism-inference-run/v2` JSON receipt. Require engine id `cd-model-agnosticism-trellis`, engine version `1.1.0`, and the exact v2 input and receipt contracts before interpreting any field.

Exit 2 is a refused request. With a well-formed command it emits a typed `cd-model-agnosticism-error/v2` receipt for an input, binding, policy, domain, or resource failure; malformed CLI usage may instead emit argparse help on stderr and no JSON. Exit 3 is a contained internal or output-encoding fault and normally emits the same typed error contract. Treat stderr as operational detail, never as an epistemic result.

On any nonzero exit, missing Python, missing entrypoint, non-JSON or oversized output, wrong engine binding, wrong contract, or unverifiable receipt identifier, withhold all probabilities and state results. Repair a warranted input once when the error identifies one; otherwise preserve the blocker, reframe, and continue qualitatively. Do not retry unchanged, hand-calculate a substitute, silently invoke a historical engine, or invent values to make the formal lane run.

## Who owns what

The invoking capability owns the question, evidence selection, interpretation, practical consequence, and receipt custody. Measurement Intelligence owns construct validity, observation encoding, cadence, missingness, disclosed dependence, and calibration design. Epistemic Regulation owns the warrant attached to the result. Decision Intelligence combines the result with values, costs, reversibility, and decision rights. Agent Striving may consult at re-entry, surprise, or repeated failure, but a posterior cannot become project fact, change the user's goal, or authorize a new pursuit. Trellis owns only deterministic validation and calculation.

A useful human-facing return names the question and lane, states whether inputs were empirical or stipulated, reports the model-conditional update and fit state, exposes load-bearing assumptions and sensitivity, identifies the next discriminating evidence, and says what—if anything—the result changes in practice. Raw JSON remains backstage unless the user asks for it.

## What the calculator computes

For model k, initial distribution pi, transition matrix A, emission matrix B, and encoded observations o_1 through o_T, Trellis performs the scaled Forward recursion:

    u_1(i) = pi_i B_i(o_1)
    c_1 = sum_i u_1(i)
    alpha_1(i) = u_1(i) / c_1

    u_t(j) = B_j(o_t) sum_i alpha_(t-1)(i) A_(i,j)
    c_t = sum_j u_t(j)
    alpha_t(j) = u_t(j) / c_t

The sequence log likelihood is log L_k = sum_t log c_t. Optional backward recursion produces smoothed state posteriors P(q_t | o_1:T, M_k); Viterbi produces the most likely single state path under the supplied model. Those answer different questions and are not interchangeable.

When comparison is warranted, the normalized model weight is

    w_k = rho_k L_k / sum_j rho_j L_j

where rho_k is the declared prior weight for model k. Pairwise log-likelihood ratios log L_k - log L_j expose what the observed sequence contributes independently of model priors. Neither calculation integrates uncertainty in the supplied HMM parameters. Duplicate predictive kernels therefore cannot earn separate evidential weight merely by acquiring new names.

Binary64 underflow is not structural zero. For sequence and stepwise predictive likelihoods, a finite log probability below the representable linear range remains in its log field, the linear field is null, and the underflow flag is true; a structural zero has a null log field, linear `0.0`, and a false underflow flag. In filtered and smoothed posteriors, both cases occupy `0.0` in the lossy linear vector, so read the companion fields: finite-log underflow retains a finite entry in `posterior_log_probabilities` and its state index appears in `posterior_finite_log_underflow_state_indices`; structural zero has a null log entry and appears in `posterior_structural_zero_state_indices`. Logs and status metadata are authoritative whenever linear mass is incomplete.

Relative weights make the distinction explicit. `weight_status: underflow` carries a finite `log_weight` and null linear `weight`; `exact_zero` carries null `log_weight` and linear `0.0`; `finite` carries both. When `weights_status` is `computed`, `linear_weights_complete` becomes false if any finite weight underflows. When weights are `unsupported`, completeness is false, interpretation is `none`, and the weight rows are empty rather than suggestive placeholders.

Mean predictive surprisal is

    S_k = -(1 / T) log L_k

in natural-log nats per observation. Absolute fit is only `assessment_basis: declared_threshold_arithmetic`: Trellis compares the computed surprisal with the supplied threshold; it does not validate the truth or quality of the calibration. `calibration_target_digest` binds the candidate identities (`model_id`, `model_version`, `comparison_unit_id`, family, and ordered predictive-kernel digest), observation-contract digest, stopping-contract digest, and declared minimum and maximum observation counts. A target mismatch or a sequence outside those bounds makes fit `unassessed` and fails an evidence-update gate. The receipt therefore keeps `calibration_truth_validated: false` even when the arithmetic says pass. A relative winner may still fit badly. Mixed fit remains visible; post-hoc deletion and renormalization would silently change the candidate set after observing the data.

## Observation and time discipline

The sequence is evidence-bearing input, not a log of Nova's impressions. Each item carries event time, knowledge time, source links, coding basis, and dependence disclosure. `analysis_as_of`, `event_time`, and `known_at` accept RFC-3339 timestamps with a required timezone and, when a fractional second is present, exactly one through six digits: microsecond precision is the supported ceiling. Trellis UTC-normalizes valid values and rejects malformed or out-of-envelope timestamps. Event time must not exceed knowledge time, neither may exceed the declared analysis time, and effective observations must be strictly increasing in event time. Simultaneous signals must become one composite observation rather than gaining fictional transitions through identifier sorting.

A structured step contract replaces prose as the operative time rule. Under event_step, every strictly later composite event advances exactly one HMM transition regardless of wall-clock duration. Under fixed_interval, every adjacent event-time delta must equal the declared positive interval. Gaps, duplicates, or premature observations fail validation rather than silently changing the model's meaning. Transition rows mean source state to target state; emission rows mean state to declared symbol order. The engine validates those machine-readable layout constants.

Keep `event_time` distinct from `known_at`. Filtering is sequence-prefix inference over the effective current revision as of the analysis time. It earns `filtered_is_as_known_then: true` and `temporal_mode: historical_prefix` only when `known_at` is strictly increasing across effective rows. Equal knowledge timestamps are valid batch knowledge, but equality is not an historical ordering proof: the receipt becomes `filtered_is_as_known_then: false` and `temporal_mode: retrospective_event_order`, as it does for decreasing knowledge time. Smoothing uses later observations and is retrospective. Never overwrite an earlier filtered estimate with smoothed hindsight or backdate later knowledge.

A correction creates a new sequence revision bound to the immediately preceding sequence digest and an exact prior-observation reference. The superseded observation must be absent from the effective current sequence, so the calculator cannot count both. Trellis records—but does not independently load or certify—the prior revision.

A nonempty dependence_refs disclosure stops validation and inference with UNMODELED_OBSERVATION_DEPENDENCE. Generic correlation discounting would fabricate a model the inputs never supplied. Re-encode dependent evidence as a composite observation or use a model and calibration contract that explicitly represent it. Empty dependence arrays mean only that no dependence was declared; they do not prove independence.

## Parameters, normalization, comparison, and fit

Provenance is structured input, not a reassuring sentence. The observation mapping, every model's parameters and prior, and the calibration reference each require an exact `{kind, fixed_before_sequence, basis, source_refs}` object; missing or extra fields, unsupported kinds, blank basis, or empty or duplicate source references are rejected. For evidence readiness, each provenance object must say `fixed_before_sequence: true` and use `estimated_independent_data` or `expert_elicited`, never `stipulated_scenario`; candidate selection and stopping must likewise be `fixed_before_sequence`. A structurally valid but non-ready record does not masquerade as evidence: the evidence gate fails and the effective interpretation becomes diagnostic-only. Stress tests may use stipulated provenance, but every result remains scenario-only.

Probability vectors must be finite and stochastic within the engine's fixed tolerance. Within that tolerance, Trellis normalizes deterministically, converts numerical negative zero to positive zero, and discloses the number and maximum size of adjustments. The receipt binds both the supplied model-document digest and an inference-model digest over the normalized values actually used. Each candidate also declares a unique `comparison_unit_id`; a repeated unit is rejected as `DUPLICATE_COMPARISON_UNIT`. The ordered `predictive_kernel_digest` binds family, observation-contract digest, matrix layout, normalized initial, transition, and emission values in their declared order; an identical digest is rejected as `DUPLICATE_PREDICTIVE_KERNEL`.

That duplicate screen proves only declared-unit uniqueness and absence of byte-identical ordered kernels. It does not validate general observational equivalence: state-permuted or otherwise equivalent models may escape the ordered digest unless their custodian assigns the same comparison unit. Both `duplicate_screen.general_observational_equivalence_validated` and the top-level semantic flag remain false.

A declared rival-model prior must be strictly positive. Exact zero would make an admitted rival unrecoverable under Bayesian updating, so it is rejected rather than masquerading as skepticism; use null when weighting is intentionally unsupported. Inside an HMM's initial, transition, or emission distributions, exact zero is a deliberate model-support exclusion justified by the parameter basis. Use a small positive probability only when that value has a defensible basis or is explicitly varied across a stipulated sensitivity range. Otherwise stay qualitative rather than inventing epsilon.

Between-model evidential weights require at least two distinct predictive kernels, a frozen candidate set, shared observation semantics and exact sequence, explicit stochastic priors, pre-sequence parameterization, comparison eligibility, and complete calibration binding. Stress-test scenario weights require explicit stochastic priors and distinct kernels but do not acquire evidential meaning. Pairwise likelihood ratios remain available where their two sequence likelihoods make the ratio mathematically defined, even when prior-based weights are unsupported.

When an observation leaves a supplied model's support, zero_likelihood_at_sequence_index names the first such evaluated row. That row has model-relative predictive probability 0.0 and no posterior. Later aligned rows are null because inference stopped; they are not additional zero-probability judgments. If every admitted model leaves support, Trellis requires REFRAME.

Absolute fit governs before relative victory. When every supplied model assigns zero likelihood, or every evidence-update candidate fails the declared fit policy, return reframe_required and no evidential winner. A parliament of terrible models does not get to elect an emperor.

## Historical receipts

Engine 1.0.1 first enforced the dependence refusal and distinguished the exact-zero trigger from its unevaluated tail. Engine 1.0.0 did not: it computed over declared dependence and could pad later unevaluated rows with 0.0. Preserve historical receipt bytes and identifiers. Treat 1.0.0 probabilistic fields as supported only after recovering the exact sequence, matching its digest and engine identity, and confirming every dependence disclosure is empty. Otherwise mark them unsupported and reframe.

Engine 1.1.0 and the v2 contracts add the evidence-versus-scenario distinction, enforce structured step semantics and strict temporal bounds, disclose normalization, bind normalized computational inputs, and block duplicate-kernel weighting. Structural schema acceptance of a historical v1 receipt does not upgrade its epistemic support.

## Receipt and authority

A Trellis receipt is a derived calculation. It binds the engine and contract versions, exact script digest, binary64 runtime characteristics, canonical input digests, epistemic lane, step and temporal semantics, options, preflight resource estimate, observation IDs, supplied and normalized-model digests, matrix layout, normalization statistics, likelihoods, aligned state results, fit summary, pairwise comparisons, relative weights when supported, reframe result, dependence disclosure, diagnostics, and semantic boundary. Its identifier digests the complete receipt body before the identifier is added.

The receipt establishes only what the declared model and encoded inputs computed. An analysis receipt says `claim_confidence: false`, `truth_certification: false`, `source_confidence_modified: false`, `parameter_uncertainty_integrated: false`, `parameter_provenance_truth_validated: false`, `calibration_truth_validated: false`, `observational_equivalence_validated: false`, `candidate_selection_truth_validated: false`, `stopping_rule_truth_validated: false`, `observation_independence_validated: false`, `decision_authority: false`, and `persistence_performed: false`, with `authority_effect: none`. A validation receipt says `structural_and_stochastic_only: true` while `ontology_validated`, `calibration_truth_validated`, `observational_equivalence_validated`, `parameter_provenance_truth_validated`, `candidate_selection_truth_validated`, `stopping_rule_truth_validated`, `observation_independence_validated`, and `semantic_truth_certified` remain false; its `authority_effect` is `none`. These flags are operative boundaries, not decorative caveats. The receipt does not mutate a case or verify an outcome. The invoking capability or repository may retain it under its own authority. Cognitive Continuity may preserve a selected belief or hypothesis and a receipt pointer only through its normal governed write.

A receipt may inform AnswerLayer candidate, fuzz, delta, probe, or watch reasoning. It cannot qualify, authorize, or apply an AnswerLayer patch by itself. Existing source, warrant, currentness, and human-approval gates remain authoritative.

## Runtime and overhead

The calculator is a pure local batch instrument. It validates JSON inputs, recomputes the bounded sequence, writes one JSON result to standard output, and exits. It has no network access, hidden store, daemon, hook, telemetry, random process, or learning loop. There is no Baum-Welch or EM path. Model revision is explicit, evaluated work under human custody.

For K models, T observations, and at most N states, time is O(K T N^2). Filtering can use O(K N) working memory; retained filter, smoother, or Viterbi tables use O(K T N). Before allocating a trellis, the calculator refuses requests above 10,000,000 estimated work units, 500,000 retained posterior cells, or 32 MiB estimated output; input files are capped at 4 MiB each. The arithmetic is bounded. The expensive work remains choosing meanings, encoders, parameters, calibration, rival sets, and revision policy. Spend that overhead only where it can prevent premature closure, distinguish consequential explanations, or improve a real update decision.

## Stop condition

Stop formal inference when the question is answered at the needed resolution, the next evidence will not change treatment, the observation contract has drifted, the candidate models have become incomparable, or reframe is required. Return to qualitative Model Agnosticism and Sensemaking rather than polishing a broken trellis.
