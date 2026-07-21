# Release status is a consequence, not a sentiment

Issue one status for one bounded target and revision.

- `READY`: all decision-critical checks executed and passed; no unresolved critical/high product defect; every critical risk has credible evidence; reviewer passed; required human authority is present for the stated release context.
- `READY_WITH_RESIDUAL_RISK`: the READY blockers are absent, but bounded non-blocking uncertainty or accepted residual risk remains visible with owner and follow-up.
- `NOT_READY`: an unresolved critical/high product defect, failed decision-critical check, unsafe condition, or missing required remediation blocks release.
- `INSUFFICIENT_EVIDENCE`: correctness cannot be assessed because intent, scope, oracle, or applicable evidence is materially missing.
- `BLOCKED_BY_ENVIRONMENT`: the required verification is known, but environment/tooling/access prevents execution; do not imply product failure.

Precedence is asymmetric: a blocking defect overrides broad green evidence. `BLOCKED_BY_ENVIRONMENT` describes execution capability; `INSUFFICIENT_EVIDENCE` describes epistemic support. Human acceptance can bound residual risk but cannot rewrite a failed check as passed.

The report should let a skeptical reader reproduce the reasoning: target and revision, scope, commands and results, risk dispositions, findings, exclusions, residual risks, reviewer disposition, and authority still required.
