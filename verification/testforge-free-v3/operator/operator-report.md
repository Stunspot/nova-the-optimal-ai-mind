# Verification report

## Decision

**Status:** READY_WITH_RESIDUAL_RISK
**Target:** Nova the Optimal AI Free 3.0.0 local static qualification candidate
**Revision:** 20beac84346465b7fe082c4c169b7d03be57880e
**Reviewer:** REVIEW_PASS_WITH_CONDITIONS

### Basis

- Independent TestForge review returned REVIEW_PASS_WITH_CONDITIONS with zero open blockers at the bounded local-static layer.
- All 36 operator tests passed, including 14 adversarial custody cases; the reviewer independently reran 10 product-contract and all 14 adversarial tests.
- The exact qualification package passes inventory, rights-custody, source-lock/map, checksum, host-tree, payload-tree, archive, documentation, and lifecycle oracles.
- Independent Hesperos review passed with five explicit documentation evidence conditions and zero open documentation defects.
- Fresh-host, hosted-provider/cross-platform, direct visual/accessibility, specialist-efficacy, and publication layers remain residual boundaries and are not claimed complete.
- This decision is bound to the exact qualification hashes reviewed; any later build with different bytes requires reverification and rebinding.

## Scope

### Included

- one-plugin, 25-root, 16-core topology
- source-map and source-lock custody
- MIT plus CC BY-ND 4.0 split-rights packet
- standalone rights envelopes and component notices
- deterministic Codex and Claude-compatible packages
- checksum, tree, archive, source-map, source-lock, and persona integrity
- optional Nova estate behavior
- customer documentation and static site
- manual workflow governance
- bounded local-static release-candidate decision

### Excluded

- publication or distribution
- fresh-host installation, discovery, restart, invocation, and rollback
- GitHub-hosted or three-operating-system execution
- direct pixel-level visual approval
- accessibility conformance
- outcome efficacy across every specialist

## Critical invariants

- INV-001: Exactly one Nova plugin exposes 25 visible roots and 16 nested MIND cores.
- INV-002: Imports, persona, notices, source map, and rights hashes match the immutable source lock.
- INV-003: Every physical package file except SHA256SUMS appears exactly once in sorted checksums with a lowercase digest and safe path.
- INV-004: Codex and Claude payloads, standalone folders, and standalone ZIPs match locked source payloads.
- INV-005: Every detached skill retains nova-free-rights and applicable component notices.
- INV-006: Builds are deterministic and state is built_from_frozen_source, never self-approved or published.
- INV-007: Optional state is external to .codex, explicit, atomic, and governed by four selectors.
- INV-008: Docs distinguish license permission, build state, publication, and live behavior.
- INV-009: GitHub workflows are manual and time-bounded; unknown capacity causes HOLD_UNKNOWN and no dispatch.

## Risk register

| ID | Severity | Disposition | Risk |
|---|---|---|---|
| R-001 | critical | covered | Topology or source-custody drift exposes a different product than the reviewed Nova Free composition. |
| R-002 | critical | covered | Split-license, portable rights-envelope, or component-notice omission creates an incomplete public distribution. |
| R-003 | critical | covered | Omitted, duplicate, traversal, or synchronized payload tampering passes a superficial checksum oracle. |
| R-004 | high | covered | Nondeterministic construction or Codex/Claude payload drift delivers unreviewed bytes. |
| R-005 | high | covered | State fallback, implicit initialization, or partial estate writes violate custody and recovery. |
| R-006 | high | covered | Documentation, site, or package drift breaks installation, rights, upgrade, support, or recovery journeys. |
| R-007 | high | covered | Source movement after qualification invalidates the evidence binding. |
| R-008 | critical | covered | Builder or metadata prematurely claims independent review, sealing, or publication. |
| R-009 | high | covered | An automatic or unbounded hosted workflow spends capacity or publishes without authority. |
| R-010 | high | covered | Local static evidence is overclaimed as live-host, hosted-provider, visual, accessibility, efficacy, or publication evidence. |
| R-011 | medium | blocked | Fresh-host installation or invocation fails despite a valid static package. |
| R-012 | medium | blocked | GitHub-hosted three-operating-system behavior differs from local Windows evidence. |
| R-013 | medium | blocked | Rendered pages contain visual or accessibility defects not detected by static checks. |
| R-014 | medium | planned | One or more specialist skills underperform representative real-world tasks. |

## Execution evidence

| ID | Status | Exit | Command | Raw evidence |
|---|---|---:|---|---|
| E-001 | passed | 0 | `python -B -X utf8 -m unittest discover -s tests -v` | verification/testforge-free-v3/operator/raw/full-unittest.json |
| E-002 | passed | 0 | `python -B -X utf8 tools/verify_package.py dist/qualification/nova-the-optimal-ai-free-3.0.0` | verification/testforge-free-v3/operator/raw/package-verifier.json |
| E-003 | passed | 0 | `python -B -X utf8 tools/check_documentation.py` | verification/testforge-free-v3/operator/raw/documentation-check.json |
| E-004 | passed | 0 | `python -B -X utf8 docs/check_site.py` | verification/testforge-free-v3/operator/raw/site-check.json |
| E-005 | passed | 0 | `git diff --exit-code 20beac84346465b7fe082c4c169b7d03be57880e -- . :(exclude)verification` | verification/testforge-free-v3/operator/raw/source-checkpoint-diff.json |
| E-006 | passed | 0 | `git diff --check 20beac84346465b7fe082c4c169b7d03be57880e -- . :(exclude)verification` | verification/testforge-free-v3/operator/raw/source-diff-check.json |
| E-007 | not_run | None | `NOT RUN: clean-host install, discovery, restart, invocation, and rollback` | not_available |
| E-008 | not_run | None | `NOT RUN: GitHub Actions verify-package or line-ending-policy workflow_dispatch` | verification/testforge-free-v3/operator/raw/metered-preflight.json |
| E-009 | not_run | None | `NOT RUN: direct pixel, keyboard, screen-reader, zoom, and representative-device review` | verification/hesperos-free-v3/visual-review.json |

## Findings

- F-001 [INSUFFICIENT_EVIDENCE/medium]: Fresh-host installation and invocation behavior are unobserved. — blocked
- F-002 [ENVIRONMENT_FAILURE/medium]: GitHub-hosted and three-operating-system evidence is absent because capacity, reserve, billing scope, and dispatch authority were not established. — blocked
- F-003 [ENVIRONMENT_FAILURE/medium]: Fresh render files exist, but direct pixel and assistive-technology review were blocked or unavailable. — blocked
- F-004 [INSUFFICIENT_EVIDENCE/medium]: Static qualification does not establish outcome efficacy across all 25 visible roots. — open
- F-005 [INSUFFICIENT_EVIDENCE/informational]: The candidate is licensed for authentic redistribution but has not been published. — open

## Residual risk

- RR-001: Host-specific installation, discovery, restart, invocation, and rollback failures may remain. — Keep the decision local/static; require disposable-host acceptance for a live-host claim.
- RR-002: GitHub runner, matrix, permissions, artifacts, statuses, and cross-platform behavior remain unproved. — Maintain HOLD_UNKNOWN and zero hosted dispatch until current capacity and authority are observed.
- RR-003: Pixel-level defects and keyboard, screen-reader, zoom, or device issues may remain. — Preserve captured-not-inspected wording and avoid accessibility-conformance claims.
- RR-004: Real-world efficacy across all specialist skills is unproved. — Limit the claim to composition, custody, packaging, state, and customer-surface behavior.
- RR-005: Public availability, downloadable bytes, and published links are unobserved. — Do not call the product published; require separate authority and post-publication observation.

## Authority still required

- Separate authority before any GitHub-hosted, paid, publication, push, tag, release, deployment, distribution, or announcement action.
- Fresh evidence before any live-host, cross-platform, visual-approval, accessibility-conformance, all-specialist-efficacy, or published-availability claim.
