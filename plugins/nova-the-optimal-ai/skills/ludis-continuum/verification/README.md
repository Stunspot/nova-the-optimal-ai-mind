# Verification records

This directory separates historical public-release evidence from the current local export-enhancement review.

## Current 1.1 local candidate

- `export-verification-manifest.json` traces consequential risks to scenarios, tests, local executions, independent reviews, and the final bounded decision.
- `export-python-tests-20260813.json` is the exact TestForge command receipt for the complete Python regression suite.
- `export-e2e-20260813.json` records the generated example's 14-step local build, verify, and exact-byte approval workflow.
- `export-static-checks-20260813.json` records package, skill, Python 3.10 grammar, product JSON, authored Markdown, HTML source, JavaScript, and repository-diff gates.
- `export-adversarial-review-20260813.json` records the independent software challenge.
- `export-architecture-review-20260813.json` records the independent architecture challenge.
- `export-documentation-review-20260813.json` records the final Hesperos customer-journey review.
- `export-accessibility-review-20260813.json` records the separate documentation accessibility review.

The dated candidate reviews and manifest bind to a content fingerprint covering the present product and documentation files. `verification/*.json` is excluded from that fingerprint so receipts do not recursively hash themselves. Any later product or documentation change invalidates the candidate review and requires a fresh fingerprint and affected review. The decision and its remaining risks belong to the current manifest, not to a historical receipt or a filename alone.

## Historical 1.0 evidence

The undated receipts, the `20260812-r2` receipts, and `live-verification.json` belong to the earlier public 1.0 release. They remain useful history but do not verify this changed local candidate. In particular, the older live receipt must not be read as evidence that the 1.1 export code, current Pages source, Alchemy profile, or Foundry adapter was published or exercised live.

A receipt reports only its named checks. It does not establish fresh-host installation, host discovery, live table quality, balance, rules accuracy, VTT compatibility, originality, rights clearance, representative-user accessibility, or semantic spoiler safety unless that observation is explicitly recorded.
