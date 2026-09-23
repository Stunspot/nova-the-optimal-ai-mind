# Value of inquiry within Model Agnosticism

Case: MA-INQUIRY-20260923. Revision: 1. Status: accepted for implementation after independent architecture PASS; implementation authorized by the owner in this task.

## Purpose and accepted delta

Nova spends attention where learning, trying, comparing, or reframing can improve the user's work, understanding, or future capability. She proceeds with useful ambiguity when finer distinctions do not repay their cost. Qualitative values and tacit recognition are complete forms of usable judgment, not failed numerical inputs. Precision belongs to handling commitments, relationships, evidence and revisions at the resolution the purpose earns.

The owner's examples govern the design: the tree/bush boundary can remain open when irrelevant; "this picture sucks" can guide revision without a theory of beauty; love and hate can have modeled relationships without exhaustive definitions or a forced bipolar scale. Models are purpose-bound, provisional instruments. Their utility includes understanding, prediction, creation, relationship and reusable learning, not merely immediate monetary action.

This improves the existing cross-cutting Model Agnosticism responsibility. It adds no Faculty, skill, router, daemon, persistence store or new retail product. The customer's financial diligence project is outside scope. Trellis 1.1.0 and its v2 HMM inference contracts remain unchanged. The legacy standalone MIND distribution stays retired and Arm's Reach stays parked.

## Architecture and praxis

| Intent | Responsibility and owner | Observable outcome |
|---|---|---|
| I1 Purpose before precision | Ambient Model Agnosticism in Prime/Field/entrypoint | Nova accepts a useful fuzzy distinction and acts when defining it would not change the work. |
| I2 Tacit evaluative knowledge | Model cognition with the user's examples and reactions | Aesthetic or relational feedback leads to an appropriate variation/comparison or focused question, without invented scores or an exhaustive rubric. |
| I3 Consequential inquiry | Model cognition and invoking capability | A candidate question is connected to possible findings and what they could change; obtainable evidence, time, attention, privacy, delay and reversibility shape priority. |
| I4 Open model boundaries | Model Agnosticism plus Sensemaking | A shared blind spot can trigger a new representation, counterexample or inquiry rather than more efficient confirmation of the current candidates. |
| I5 Exact optional arithmetic | Separate stateless Python standard-library instrument | Finite discrete expected utility and value-of-information arithmetic is reproducible, conditional and bounded. |
| I6 No authority or state leakage | Existing host and invoking capability | Inquiry evaluation cannot authorize collection, spend, external actions or storage; no hidden continuing loop. |
| I7 Earned stopping | Model cognition | Nova acts, prototypes, compares, investigates, reframes, asks, or stops at the level useful now; no routine uncertainty inventory. |

Resident prompt: compact performance seed beside existing Model Agnosticism. Deeper craft: references/mind/value-of-inquiry.md, reached when inquiry/precision competes for effort or explicit formal comparison is useful. Situated examples teach continuation rather than require a report form. Exact engine: scripts/value_of_information.py, called only through the reference; no import or automatic conversion from Trellis. Machine example: assets/value-of-inquiry/decision-example.json. Meaningful numerical and behavioral tests remain development/evaluation material.

Existing Measurement, Decision, Aesthetic and Epistemic Regulation responsibilities compose as needed; their Cores need no rewrite. The invoking capability owns evidence and any authorized artifact. No new durable record is required for ordinary judgment.

## Instrument contract

Versioned input `nova-value-of-information/v1` describes a bounded one-step, finite, static decision. Exact top-level fields: schema, purpose, utility_unit, basis, states, actions, inquiries. `basis` has mode (`stipulated_scenario` or `evidence_informed`), assumptions (nonempty strings) and source_refs (nonempty strings). Labels declare basis; the engine never validates provenance or empirical calibration.

States have unique id and probability. Actions have unique id and utilities mapping every state id to finite cardinal utility on the declared common scale, where higher is preferred. Inquiries have unique id, nonnegative cost in the same scale, and outcomes; each outcome has unique id and likelihoods mapping every state id to P(outcome|state). For each inquiry/state, outcome likelihoods sum to one. Unknown or missing keys, duplicate JSON keys/ids, booleans as numbers, nonfinite values, negative probabilities, invalid distributions, empty/oversized inputs and inconsistent state mappings are refusals. Bounds: 1 MiB input, 64 states, 64 actions, 32 inquiries, 32 outcomes/inquiry, 5 million estimated state-action-outcome operations. Probabilities use a declared tight tolerance; normalize only inside tolerance and disclose it. Reject finite-value arithmetic that overflows.

Calculate current expected utilities and all maximizing actions, expected utility with perfect state information, EVPI, outcome probabilities, posterior-conditioned maximizing actions, gross expected utility after each inquiry, EVSI, net value after cost, and all maximizing options including proceed-without-inquiry. Zero-probability outcomes have no conditional action or posterior, not invented certainty. Preserve ties explicitly; near ties receive a disclosed numerical tolerance, not a human-indifference claim. Finite enumerated inputs can represent parameter/model states if supplied, but cannot certify model completeness, causal effects or independent evidence.

The calculator assumes one inquiry then one terminal action; observations reveal information and do not themselves change state or the action set. Timing, irreversible experimental effects, interacting inquiries, adaptive policies, distribution fitting, utility elicitation and portfolio/financial valuation are outside this arithmetic. It must not naively add the value of overlapping inquiries. Inquiry costs do not model delay or other effects unless already represented consistently in the supplied utilities. Declining to scalarize plural values routes back to qualitative judgment.

CLI: `python scripts/value_of_information.py validate INPUT.json` then `... analyze INPUT.json`. Exit 0 emits JSON; exit 2 emits a typed refusal for input/contract/resource failures; exit 3 emits a contained internal failure. Stdout contains one JSON object. No network, dependencies beyond standard library, subprocesses, persistence or execution of inquiry. Output binds engine/version and input digest, states conditional arithmetic interpretation, and keeps provenance_validated, calibration_validated, model_completeness_validated, utility_endorsed, action_authorized and persistence_performed false. Mode evidence_informed is a caller declaration, not earned certification.

## Alternatives and decision

A sentence-only reminder is narrower but does not reliably teach tacit recognition, inquiry selection, model revision or formal use. A universal quantified inquiry controller is broader but would manufacture precision, mandate overhead and constrain open values. Extending Trellis would mix HMM inference with a distinct decision problem and silently widen its assumptions. Select a compact ambient seed, progressively loaded craft, situated examples and one optional exact finite calculator. This delivers the discussed general capability while leaving empirical modeling and judgment with the LLM and relevant domain owner.

## Acceptance and evidence plan

Q1: Tree/shrub ambiguity irrelevant to requested shade or composition -> proceed without botanical clarification.
Q2: "This picture sucks; less sterile" -> use comparison/variation and concrete perceptual direction, without forcing beauty metrics or demanding justification.
Q3: Love/hate relationship -> allow coexistence/context and explicit chosen relations; preserve undefined concept boundaries without forcing a single axis.
Q4: An uncertain but decision-invariant variable vs a small obtainable decision-changing fact -> prioritize the latter and explain relevance briefly.
Q5: No immediate external decision but reusable scientific understanding -> recognize legitimate inquiry value without inventing money.
Q6: Every candidate shares a failing assumption -> reopen frame; no forced winner or narrow optimization of a broken model set.
Q7: Exact finite fixture: states good/bad .5/.5, invest [100,-60], decline [0,0], probe outcomes + [.8,.2], - [.2,.8], cost 5 -> baseline 20, gross 34, EVSI 14, EVPI 30, net 9. Outcome policy uses observed signal only.
Q8: Uninformative, perfect and zero-probability signals; exact and near ties; high cost; malformed distributions, NaN/Infinity, booleans, duplicate keys, missing states and oversized inputs -> correct arithmetic or typed refusal, never a fabricated probability.
Q9: Missing Python or unsupported plural utilities -> useful qualitative continuation; no calculator prerequisite for ordinary work.
Q10: Apparent completion -> stop when further inquiry would not change treatment; preserve explicit user requests for depth and hard acceptance/authority boundaries.

Independent architecture review precedes implementation freeze. Independent code review and bounded held-out model continuations challenge the candidate. Numerical tests establish conditional arithmetic; model continuations establish only the observed prompt episodes, not population reliability or fresh-host discovery. Existing package, product and line-ending checks cover the changed distribution contract. Trellis regressions establish unchanged arithmetic behavior where run.

## Delivery, compatibility and rollback

Canonical owner is the active Nova Free embedded MIND source; Emergent receives a newly frozen and qualified dependency through its existing pipeline. Update existing maps/contracts, customer explanations and release sidecars to describe the achieved capability, then packages, governed shelf/catalog and applicable installed copies. Preserve product versions for this owner-authorized current-surface update unless a governing contract requires otherwise; do not invent a public announcement or new channel. Retain immutable historical dependency/evidence records and preserve preexisting user edits. Snapshot replaced shelf/install bytes before replacement. Repository updates are authorized; private hosted Actions remain on hold until the account-capacity gate is satisfied, so use credible local evidence and avoid triggering workflows by accident.

No permission is added by this design; the user's instruction to plan and effectuate changes supplies implementation and routine current-surface authority. Revisit this architecture if multi-step inquiry, automatic data collection, non-scalar optimization or a learned calibration service is later requested.

## Implementation refinement — exact arithmetic

The finite engine uses exact rationals from JSON decimal lexemes; exact ranking precedes binary64 projection and includes rational value/gap strings. Numeric tokens/significands are bounded to 128 characters/digits, decimal exponent magnitude to 400 before Fraction construction, rational numerator/denominator to 4096 bits, and output to 32 MiB. Projection overflow or nonzero underflow is a typed refusal. Distribution normalization tolerance and diagnostic near-tie band are each absolute 1e-12 in their respective probability/utility units; near ties never change maximizers or imply human indifference. These are bounded refinements of I5/Q8, not a broader decision scope.
