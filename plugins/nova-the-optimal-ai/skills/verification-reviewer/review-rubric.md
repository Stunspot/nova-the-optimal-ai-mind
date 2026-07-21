# Verification review rubric

| Lens | Pass condition | Release-blocking signal |
|---|---|---|
| Scope | Target, revision, inclusions, exclusions, and environment are bounded | Evidence belongs to another revision or material surface is silently excluded |
| Risk | Catastrophic and high-impact failure modes have dispositions | Critical authorization, corruption, duplication, or irreversible-state risk is absent or accepted without authority |
| Oracle | Assertions discriminate correct from dangerous behavior | Status-only, truthiness, call-count-only, or snapshot assertions stand in for state and side effects |
| Layer | The test preserves the boundary it claims to verify | Mocking removes persistence, transaction, serialization, authorization, or dependency behavior under claim |
| Evidence | Claims trace to captured results and raw references | “Passed” is inferred from generated code, stale logs, or an unrecorded command |
| Triage | Failures remain classified with discriminating evidence | Environment or test failure is presented as product defect, or a product defect is dismissed as flake |
| Safety | Consequential actions are bounded and authorized | Production targeting, destructive activity, active exploitation, install, or external action lacks approval |
| Decision | Status follows from blockers, residual risk, and review | READY coexists with unresolved critical risk, failed decision-critical check, or unexecuted essential evidence |

Verdicts:

- `REVIEW_PASS`: the bounded status is supported.
- `REVIEW_PASS_WITH_CONDITIONS`: no hidden blocker, but named evidence or human decision remains before the stated next action.
- `REVIEW_FAIL`: a material break makes the status unsafe; name the minimum repair.
