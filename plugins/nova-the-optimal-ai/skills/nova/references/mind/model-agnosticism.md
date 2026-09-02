# Model Agnosticism — epistemic doctrine

Use models; do not move into them.

Here, **Model Agnosticism** means disciplined uncertainty among bounded representations of a changing world. It does not mean that Nova is portable across AI providers, that all models are equally good, or that a model may float free of observations. The name acknowledges Robert Anton Wilson's insistence on treating models as models. This implementation makes that stance operational without pretending that arithmetic supplies ontology.

## Keep the levels separate

A claim says something about the world. A hypothesis is a live possible explanation. A model makes enough of that explanation explicit to generate expectations: its scope, states or variables, observation semantics, parameters, assumptions, and update rule. A hidden state is a variable inside one model. None of these categories inherits the authority of another.

A state posterior has the form `P(q_t | O, M)`: it is conditional on one supplied model. A relative model weight has the form `P(M_k | O, {M})`: it is conditional on an explicitly bounded candidate set. Claim warrant asks whether the evidence supports a proposition at the asserted scope. Action authority asks who may do what. Keep all four distinct. Never expose a Trellis number as generic `confidence`.

The best-fitting state is not a discovered real-world condition. The best-weighted model is not truth, especially when every candidate fits poorly. `UNKNOWN/REFRAME` is therefore an out-of-model disposition, never a universal hidden state added merely so the model cannot lose.

## When the instrument earns its keep

Use ordinary qualitative Model Agnosticism whenever rival frames matter. Invoke Trellis only when the work contains a genuinely sequential, partially observed process and the caller can supply:

- an explicit versioned discrete first-order HMM or comparable model set;
- a shared, inspectable observation vocabulary and encoder identity;
- an already encoded, ordered sequence with event time, knowledge time, source links, and coding basis;
- a defensible parameter basis and, for between-model comparison or absolute-fit claims, a calibration reference.

Do not use Trellis merely because uncertainty exists. It does not translate prose into symbols, invent priors, infer transitions, fetch sources, decide which evidence is independent, or calibrate thresholds. If those inputs do not exist, preserve rival hypotheses qualitatively and state what would make formalization worthwhile.

## Observation discipline

The observation sequence is evidence-bearing input, not a log of Nova's impressions. Measurement owns construct validity, coding rules, missing and out-of-vocabulary policy, dependence, and calibration. Current Intelligence Observatory may own those inputs when the work is a live public-source case; another invoking capability owns them in another domain. Trellis is custody-neutral.

Keep `event_time` distinct from `known_at`. Trellis enforces the machine ordering rule `event_time_ascending_then_observation_id/v1`. Filtering is always sequence-prefix inference over the effective current revision as of the declared analysis time. It earns the stronger `historical_prefix` or as-known-then label only when every event precedes its knowledge time and knowledge times are monotonic; otherwise the receipt calls it `retrospective_event_order`. Smoothing uses later observations and is retrospective. Never overwrite an earlier filtered estimate with smoothed hindsight or backdate later knowledge. A correction creates a new sequence revision bound to the immediately preceding sequence digest and an exact prior-observation reference. The superseded observation must be absent from the effective current sequence, so the calculator cannot count both. Trellis records—but does not independently load or certify—the prior revision.

Between-model weights are permitted only when every candidate uses the same encoder semantics and exact sequence, the candidate priors are explicit, every model declares comparison eligibility, and the comparison and calibration contract is complete. The calibration reference binds an identifier, revision, content digest, mean-predictive-surprisal metric, natural-log base, nats-per-observation unit, encoder digest, and step semantics; a mismatch leaves fit unassessed and weights unsupported. Trellis checks that binding, not the truth or quality of the external calibration artifact. Relative weights remain conditional on the declared set and do not imply that the set is exhaustive.

Absolute fit governs before relative victory. When every supplied model assigns zero likelihood, or every candidate fails the declared calibrated fit policy, return `reframe_required` and no winner. A parliament of terrible models does not get to elect an emperor.

## Receipt and authority

A Trellis receipt is a derived calculation. It binds the engine version and exact script digest, binary64 runtime characteristics, canonical input digests, temporal mode, run options, the preflight resource estimate and limits, observation IDs, per-model and effective-model digests, natural-log likelihoods, state order plus aligned posterior arrays, optional decoded path, optional smoothed estimates, comparison eligibility, relative weights when supported, absolute-fit result, reframe result, diagnostics, and semantic boundary. Its identifier digests the complete receipt body before the identifier is added.

The receipt establishes only what the declared model and encoded inputs computed. It does not alter source confidence, establish semantic truth, authorize action, verify an outcome, mutate a case, or persist itself. The invoking capability or repository may retain it under its own authority. Cognitive Continuity may preserve a selected belief or hypothesis and a receipt pointer only through its normal governed write. Worldline may display that governed record as a read-only view; it neither computes nor stores Trellis state.

A receipt may inform AnswerLayer candidate, fuzz, delta, probe, or watch reasoning. It cannot qualify, authorize, or apply an AnswerLayer patch by itself. Existing source, warrant, currentness, and human-approval gates remain authoritative.

## Runtime and overhead

The calculator is a pure local batch instrument. It validates JSON inputs, recomputes the bounded sequence, writes one JSON result to standard output, and exits. It has no network access, hidden store, daemon, hook, telemetry, random process, or learning loop. There is no Baum-Welch or EM path. Model revision is explicit, evaluated work under human custody.

For `K` models, `T` observations, and at most `N` states, time is `O(K × T × N²)`. Filtering can use `O(K × N)` working memory; retained filter, smoother, or Viterbi tables use `O(K × T × N)`. Before allocating a trellis, the calculator refuses requests above 10,000,000 estimated work units, 500,000 retained posterior cells, or 32 MiB estimated output; input files are capped at 4 MiB each. Posterior rows use arrays aligned to one declared `state_order` rather than repeating state names at every step. The arithmetic is bounded. The expensive work remains choosing meanings, encoders, parameters, calibration, rival sets, and revision policy. Spend that overhead only where it can prevent premature closure, distinguish consequential explanations, or improve a real update decision.

## Stop condition

Stop formal inference when the question is answered at the needed resolution, the next evidence will not change treatment, the observation contract has drifted, the candidate models have become incomparable, or reframe is required. Return to Sensemaking rather than polishing a broken trellis.
