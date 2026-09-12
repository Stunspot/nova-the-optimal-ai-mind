# Challenge the evidence before seeing the proposed verdict

Use when confidence anchoring could materially weaken independent review. The operator may provide a first-pass packet with the candidate identity, scope, intended behavior, impact/risk map, tests, complete relevant raw evidence, exclusions and known limitations. Keep the proposed status, author self-score and previous reviewer praise in a separate second-pass section. This is optional evidence ordering within the existing review, not another mandatory review cycle.

Before reading the proposed status, reconstruct what was tested, what the evidence establishes and which consequential claims remain open. Then compare that assessment with the operator's recommendation and apply the normal rubric. Preserve factual failure history, repairs between candidate revisions, sampling decisions, missing results and methodological changes in the first pass. Hiding them would blind the reviewer to the defects it is meant to find.

Inspect a packet inventory and access primary artifacts for the decisive claims. A clean summary can omit the failed seed, stale run or unsupported exclusion. Record the limits if raw evidence is inaccessible. An operator-authored packet plus a fresh context reduces priming; it does not establish independent authorship of the evidence or different provider/model lineage.

Bind the returned review to the target, revision, environment and stable evidence cutoff under the existing non-sealing rules. Preserve the reviewer's original response. Distinguish an unavailable reviewer, an unparsed response, a substantive rejection and an accepted bounded claim. The coordinating author cannot manufacture the independent reviewer's verdict. If review infrastructure is absent, report the lost guarantee rather than treating same-context rewriting as independent approval.

Compare disagreements at the challenged claim and its evidence. Do not translate missing ratings into numbers or average away a blocker. If numerical calibration is requested, use only actual ratings with compatible scales and retain their reasons. A higher score establishes neither correctness nor release authority.

Lineage: independently adapted from [AutoResearch's blind-review coordinator](https://github.com/EvoMap/AutoResearch/blob/0fa9a9336fc84a6b069111adb03ca21fabb5394b/ar-runtime/.claude/agents/ar-blind-reviewer.md), retaining reduced evaluative priming and rejecting omission of validity-relevant history. No upstream prompt text is included.
