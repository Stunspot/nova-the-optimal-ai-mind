# Traceability matrix

This reference maps risks to invariants, scenarios, tests, and execution evidence. Read [`verification-report.md`](verification-report.md) first unless you are auditing the proof chain directly.

| Risk | Invariant | Scenario | Test | Execution evidence | Disposition |
|---|---|---|---|---|---|
| R-001 | INV-001 | S-CURRENT-RELEASE | T-CURRENT-STATIC; T-CURRENT-RELEASE | E-001 `entry-static.json`; E-002 `release-extraction-validation.json` | Covered: current static verifier, archive validators, and TestForge package checks passed; the inventory is 201 directories / 443 files (MIND 147; Nova 296), zero symlinks, with no generated debris. |
| R-002 | INV-002 | S-CURRENT-INSTALL | T-CURRENT-MIND-CACHE; T-CURRENT-NOVA-CACHE; T-CURRENT-DISCOVERY; T-CURRENT-FRESH-INSTALL | E-003 current-host/cache/discovery receipts; E-004 `fresh-host-install.json` | Covered, bounded: after correction and cleanup, installed source/cache equality is 147/147 and 296/296, 28 handles are discovered, and an initially empty temporary home reproduced install and equality. |
| R-003 | INV-003 | S-TOUR | T-TOUR | E-005 `tour-browser-command.json` | Covered, bounded: five layout viewports, zero overflow, seven activations, reduced-motion and no-JavaScript assertions. |
| R-004 | INV-004 | S-DIRECT-NEGATIVE | T-DIRECT-NEGATIVE | E-006 `live-direct-negative-analysis.json` | Covered only for the named simple-work nonactivation scenario. |
| R-005 | INV-005 | S-LIVE-INDEX; S-TESTFORGE-CURRENT | T-LIVE-INDEX; T-PRE-FIX-TESTFORGE (not applicable); T-TESTFORGE-STAGE-GAP (not applicable); T-TESTFORGE-INDEX-CONTRADICTION (not applicable); T-TESTFORGE-CURRENT | E-007 stable six-scenario core; E-008/E-009/E-010 preserved historical negatives; E-011 `live-testforge-review-analysis.json` and public raw receipt | Covered with residual risk: six named core scenarios are valid. E-011 returned `REVIEW_PASS_WITH_CONDITIONS` for the preceding `INSUFFICIENT_EVIDENCE` decision, not release certification. Historical negatives remain auditable and are not current acceptance tests. |
| R-006 | INV-006 | S-REPOSITORY-PUBLICATION | T-REPOSITORY-PUBLICATION | E-012 `repository-publication.json` | Covered, bounded: GitHub reports the repository as `PUBLIC` and first-published revision parity passed. This is not final-head or signed-out proof. |
| R-007 | INV-007 | S-EXTERNAL-GATES | T-EXTERNAL-GATES | `video-production-inputs.json` proves only local production-input readiness | Blocked/human-gated: final-head parity, signed-out readability, video, feedback, rights, team, and Devpost. |

Every ID in this table is defined in `verification-manifest.json`. The local decision is `READY_WITH_RESIDUAL_RISK` after documentary reconciliation, not a claim that the review reran after those edits or that the remaining external contest actions occurred.
