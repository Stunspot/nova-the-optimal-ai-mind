# Release status is a consequence, not a sentiment

Issue one status for one bounded target and revision.

- `READY`: all decision-critical checks executed and passed; no unresolved critical/high product defect; every critical risk has credible evidence; reviewer passed; evidence and review are bound to the submitted candidate. This is a technical verdict, not authority to release.
- `READY_WITH_RESIDUAL_RISK`: the READY blockers are absent, but bounded non-blocking uncertainty or accepted residual risk remains visible with owner and follow-up. It never waives an unexecuted decision-critical check or open blocking review condition.
- `NOT_READY`: an unresolved critical/high product defect, failed decision-critical check, unsafe condition, or missing required remediation blocks release.
- `INSUFFICIENT_EVIDENCE`: correctness cannot be assessed because intent, scope, oracle, or applicable evidence is materially missing.
- `BLOCKED_BY_ENVIRONMENT`: the required verification is known, but environment/tooling/access prevents execution; do not imply product failure.

Precedence is asymmetric: a blocking defect overrides broad green evidence. `BLOCKED_BY_ENVIRONMENT` describes execution capability; `INSUFFICIENT_EVIDENCE` describes epistemic support. Human acceptance can bound residual risk but cannot rewrite a failed check as passed.

The report should let a skeptical reader reproduce the reasoning: target and revision, scope, commands and results, risk dispositions, findings, exclusions, residual risks, reviewer disposition, and authority still required.

If the stated claim itself includes an authorized release action, unresolved authority prevents that claim. Otherwise list outstanding release authority separately from the bounded technical verdict. Retain one properly classified support-failure correction with its original evidence; do not confuse that history with an unresolved product defect. See [Evidence records](evidence-records.md).

Before handing off, reconcile the single stated status against the actual findings. A supplied observation of a promised core function failing supports a bounded NOT_READY even when the current host cannot rerun it; retain attribution and uncertainty about cause, not uncertainty about the observed contract failure. Do not open with one status and close with another. Out-of-scope work is an exclusion, not automatically residual risk in the included claim. A legitimate control that passed must not inherit its deliberately broken mutant's failure. State a fraction with its original denominator; if numeric rates matter, calculate them rather than improvising prose.
