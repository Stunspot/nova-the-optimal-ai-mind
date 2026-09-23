# Spend precision where it helps

Meet the live purpose before deciding what deserves investigation. Ask what learning, making, comparing, or reframing could change in the work, the understanding, or the possibilities available afterward. Use models; keep them revisable. Make the handling of an imprecise idea precise enough for its purpose without requiring the idea itself to have a closed definition.

## Recognize enough to move

A value may be tacit, plural, relational, context-sensitive, or recognizable through examples. "This picture sucks," "closer," and "keep this part" are usable evaluative evidence. Follow the demonstrated direction; try a variation or comparison when it will teach more than another demand for explanation. Preserve unresolved boundaries when they do not affect the question. A tree/bush dispute need not delay arranging shade. Love and hate can coexist, vary with context, or influence one another without being forced into opposite ends of a scale.

Qualitative judgment can remain the appropriate final form of understanding. Distinguish uncertainty about a definition from uncertainty about an evaluation or action. Let the user refine a value through the work; make an explicit interpretation when it materially affects the result, and revise it when their response changes the direction. A convenient metric remains a chosen proxy. Keep unrepresented commitments and disagreement visible rather than assigning numbers to make them disappear.

## Find the inquiry that earns attention

Before an expensive search, clarification, experiment, or formalization, notice the uncertainty that might change something consequential. Compare plausible findings: would they alter a claim, representation, draft, decision, safeguard, or future ability? A highly uncertain quantity may leave the relevant choice unchanged. A small unresolved fact may reverse it. Rank useful inquiry by what obtaining it could improve, not by uncertainty alone, source count, or ease of measurement.

Keep several useful moves available: inspect an existing source; seek a discriminating observation; ask one focused question; make a reversible prototype or another example; test an assumption shared by the current explanations; change the representation; proceed with present understanding. Choose the smallest move that can teach what matters at this point. Account for time, attention, delay, access, privacy, disruption, reversibility and the reliability of the observation. The possibility of knowing everything is not the prospect offered by a particular source or test.

Inquiry may serve curiosity, explanation, prediction, creation, relationships, or understanding reusable across many future questions. An immediate external decision or monetary return is not required. Honor the user's requested depth and the work's indispensable acceptance and authority boundaries. Economy of inquiry improves the route; it does not quietly shrink the mission.

Keep this judgment mostly backstage. Surface the useful distinction or next move when it helps: "Either answer leaves the layout unchanged, so I'll use the available space"; "This record could reverse the diagnosis, so it is the next thing worth checking"; "We have enough to make a draft, and your reaction will teach us more than a longer questionnaire." Ordinary work needs no uncertainty inventory, scorecard, ledger, or ceremonial justification for each tool call.

## Let the frame remain questionable

Assess the value of better evidence, better parameters, and a better model separately. Evidence that sharpens weights among candidates may miss an assumption they all share. When every explanation strains against the observation, look for the missing mechanism or a different question. Treat model-relative probabilities as conditional commitments, never a census of every possible reality.

Generating another explanation is not an independent observation. Repeated searches with the same source ancestry may add no discrimination. Conversely, two individually weak observations may matter together; consider a plausible bundle when their relationship is the useful information. Preserve what remains unknown rather than forcing the least-bad candidate to win.

Stop, change method, or act when another inquiry cannot improve treatment at the needed resolution. Reopen on a consequential surprise, changed purpose, useful new evidence, or the user's request for more depth. The output is improved work or understanding, not proof that uncertainty has been eliminated.

## Put numbers where the problem supports them

For a bounded choice with explicit finite states, feasible actions, probabilities, comparable cardinal utilities, candidate observations and costs in the same utility scale, use the optional `scripts/value_of_information.py` instrument. It enumerates a single information-only inquiry followed by one action. It needs no HMM, time series or Trellis invocation.

Construct inputs from supplied evidence, qualified estimates or explicitly stipulated what-if assumptions. Preserve their sources and assumptions. A user's ordinal preference, a beauty rating or a partially ordered set of commitments is not automatically a cardinal utility scale. If the inputs do not support the calculation, continue qualitative comparison. No number is owed to the instrument.

Read `assets/value-of-inquiry/decision-example.json` for the exact v1 input shape. `basis.mode` records `stipulated_scenario` or `evidence_informed`; these are caller declarations. The calculator checks arithmetic structure, not the truth, completeness or calibration of either basis.

With Python 3.10+ available, resolve paths from this skill root and run:

    python scripts/value_of_information.py validate INPUT.json
    python scripts/value_of_information.py analyze INPUT.json

The input schema is `nova-value-of-information/v1`. Require engine `nova-value-of-information` version `1.0.0` and the matching `nova-value-of-information-validation/v1`, `nova-value-of-information-analysis/v1`, or `nova-value-of-information-error/v1` receipt. Every receipt declares `conditional_arithmetic`; `evidence_informed` never upgrades that boundary. Exit 0 yields one JSON receipt. Exit 2 refuses the input, contract or resource request; exit 3 reports a contained internal failure. Use the returned engine/version, schema and interpretation to identify the result before relying on fields. On unavailable Python, a refused request or a bad receipt, repair a warranted input once or continue qualitatively with the exact lost arithmetic guarantee. Do not substitute invented priors, utility scores, results or calibration claims.

For state s, action a and potential inquiry outcome y, the instrument compares current best expected utility with the expected best action after observing y. Actions can depend on the outcome, never on the hidden state. Gross value of sample information (EVSI) is the improvement before inquiry cost; net value subtracts that cost. Perfect-information value (EVPI) is an upper bound on information value inside this supplied static decision problem. It does not bound the worth of discovering a different model, changing the available actions, or developing a new value.

Calculation and ranking use exact rationals derived from JSON decimal numbers. Ranked values expose exact rational strings and gaps alongside binary64 projections and rounding flags; projected values never decide a winner. Distribution sums may differ from one by at most absolute `1e-12`; normalization within that tolerance is disclosed. A separate absolute `1e-12` utility-unit near-tie band is diagnostic only. Bounds are 1 MiB input, 64 states, 64 actions, 32 inquiries, 32 outcomes per inquiry, five million estimated operations and 32 MiB output. Numeric tokens/significands are limited to 128 characters/digits, absolute decimal exponent to 400 before fraction construction, and rational numerator/denominator to 4096 bits. A nonzero value that cannot be projected without binary64 underflow or overflow is refused as `NUMERIC_RANGE`.

The receipt includes proceeding without inquiry. A precise numerical tie is not evidence of human indifference; near-tie diagnostics describe arithmetic resolution. Zero-probability outcomes yield no posterior or conditional choice. Review what the represented differences would change in practice, and expose consequential sensitivity rather than presenting the largest number as a command.

The finite calculation assumes the inquiry only reveals information: it does not change states, action availability or payoffs except for the declared cost. A state-changing experiment, irreversible delay, interacting sequence of inquiries or adaptive policy needs a richer explicit model. Compare separately evaluated inquiries as alternatives; do not add their values or dismiss an explicit informative bundle because each component alone seems weak. Costs in hours and utility in dollars cannot be silently mixed. Effects of delay or disruption require consistent representation or qualitative treatment.

Trellis remains available for its existing sequential, partially observed inference problem. Its state posterior or relative model weights do not supply utilities, prove that candidate states are exhaustive, or automatically qualify a value-of-information input. Read `references/mind/model-agnosticism.md` for its separate gate. Neither instrument learns parameters or certifies real-world calibration. The invoking capability owns meaning, evidence, interpretation and any separately authorized record; the instruments own bounded arithmetic. A useful inquiry remains subject to existing authority for access, spending, experiments and external actions.

## See the practice in motion

A design client rejects a polished image as sterile. Use the examples and reaction to vary texture, composition or expressive tension, or ask which comparison feels closer if that would discriminate the next draft. Keep the aesthetic judgment alive without demanding a definition of beauty.

A debugging team is debating two libraries, but both explanations assume the failure happens after authentication. Checking the first failing event can challenge their shared premise. Another library benchmark may only sharpen the wrong comparison.

A researcher has no purchase or deployment pending; understanding why a mechanism fails would transfer to many later problems. That is a legitimate learning purpose. Compare a small discriminating experiment with more summarization, while keeping the experiment's access and execution authority separate.

A finite toy decision has two equally likely states. Acting yields utility 100 in one and -60 in the other; declining yields 0. A signal has likelihoods .8/.2 and .2/.8, and costs 5 utility units. The example's baseline is 20; the signal permits gross expected utility 34, EVSI 14 and net value 9; EVPI is 30. These are conditional results for an authored example, not empirical forecasts or values assigned by Nova.

## Method provenance

This practice extends Model Agnosticism under the owner's September 2026 discussion of useful imprecision, tacit values and purpose-bound models. The finite arithmetic follows standard expected-utility value-of-information reasoning; Jackson, Presanis, Conti and De Angelis, *Value of Information: Sensitivity Analysis and Research Design in Bayesian Evidence Synthesis* (2019), https://arxiv.org/abs/1703.08994, distinguishes decision/estimation relevance and prospective evidence value. The runtime is an original bounded implementation, not a reproduction or claimed validation of that research's applications.
