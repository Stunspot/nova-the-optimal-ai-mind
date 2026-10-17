# Changelog

## 2.0.0 - 2026-09-05

- Mark removal of the shipped assessor JSON `plan_sha256` field as a compatibility break; callers must stop requiring it.
- Move mandatory metered-verification detail behind the existing conditional reference without weakening capacity or spend safeguards.
- Give the accepted source and both independently packaged skills a new 2.0.0 release identity; restore original 1.1.7 assets and preserve its tag.

- Defer verification-manifest assembly until the evidence reaches a stable cutoff.
- Prohibit custody checksums, release archives, and package or release receipts until verdict and independent review are complete.
- Remove the metered-preflight plan digest and hard-gate checksum-producing release tools behind an explicit final seal.
- Add reviewer and behavioral-regression coverage for premature sealing and receipt recursion.

## 1.1.7 - 2026-08-13

- Make TestForge an explicit release-grade verdict on a frozen candidate rather than routine build verification.
- Require every check, artifact, retry, reviewer pass, and receipt to be capable of changing the bounded verdict.
- Cap test, tooling, and environment recovery at one materially different low-cost path per cycle.
- Close a second support-layer failure with the exact lost guarantee instead of creating another completion gate.
- Align plugin discovery, activation examples, the operator, and the fileless fallback with the same stopping boundary.

## 1.1.6 — 2026-08-12

- Require a fresh, billing-scope-matched capacity observation before quota-limited verification.
- Expand the complete planned run, including duplicate triggers, matrices, attempts, ceilings, and current provider multipliers.
- Hold unknown, stale, insufficient, reserve-consuming, provider-refused, and unauthorized paid execution without launching a probe job.
- Add a deterministic included-capacity assessor that rejects caller-supplied paid authority and never permits paid dispatch.
- Package a JSON schema and worked plan template for the assessor input.
- Package a five-field response template that preserves supplied snapshot facts and calculates reserve-aware paid capacity without ambiguous spend ranges.
- Document the safeguard across first-use, workflow, capability, limitation, and release guidance.
- Run branch-push CI only on `main`; pull requests retain the full cross-platform gate, avoiding duplicate branch push and pull-request runs while preserving pre-merge and merged-state evidence.

## 1.1.5 — 2026-08-08

- Synchronize the operator with the current TestForge last-tripwire doctrine.
- Align package, plugin, evaluation, and customer-release versions.
- Rebuild deterministic Codex and Claude distributions with explicit removal and rollback routes.
- Keep the independent reviewer lean and self-contained.

## 1.1.1 — 2026-07-20

- Prepare the skills-only Codex plugin for official directory review with exact privacy and terms links.
- Align the plugin listing with the two bundled verification skills instead of implying that the repository-only behavioral-evaluation harness is installed.
- Refresh customer privacy, terms, support, security, installation, and publication guidance.
- Extend public-distribution tests to lock version parity, legal URLs, listing assets, and customer-document reachability.

## 1.1.0 — 2026-07-18

- Make the operator and reviewer independently self-contained without changing their verification doctrine.
- Add portable one-skill Claude.ai upload archives and current non-coder installation guidance.
- Shorten discovery metadata to the current Claude limit.
- Replace the operator's sibling-file reviewer handoff with explicit `$verification-reviewer` routing and an honest unavailable-reviewer boundary.
- Add deterministic dual-host packaging and parity checks.

## 1.0.2 — 2026-07-18

- Assigned TestForge the product-specific `cd-testforge` marketplace namespace so installing it cannot displace a separately distributed Collaborative Dynamics marketplace such as CanopyOps.
- Updated the public installation command, judge quickstart, distribution-integrity test, manifests, and release package without changing TestForge's verification behavior.

## 1.0.1 — 2026-07-17

- Strengthened capability-matched, read-only diagnosis after a recorded local-model failure proposed destructive package removal as reproduction.
- Separated executed commands, safe copy-ready diagnostics, and unexecuted remediation more explicitly.
- Prevented behavioral judges from excluding weak observable responses by misclassifying poor performance as an invalid episode.
- Hardened sentence-only verification, deterministic time oracles, authorization denial evidence, and active-security re-entry boundaries after the stricter evaluator exposed unsupported assumptions.
- Repaired a password-reset eval oracle that had demanded a no-duplicate-token policy absent from the supplied requirement; authorized policy or explicit unresolved custody now passes.
- Reconciled the same sentence-only eval's execution oracle with its runtime boundary: a concrete API/persistence evidence plan may pass when honestly labeled unexecuted.
- Added a reusable secret-capability lifecycle state machine for issuance, delivery, repeated issuance, redemption, reuse, expiry, concurrency, protected state, and authorization evidence.
- Compiled a compact local-model context from the operator kernel and decision-relevant references, excluding examples and package bulk that caused attention dilution and evidence contamination.
- Scoped secret-capability fallback doctrine to actual secret-bearing targets so unrelated deletion and timing cases no longer inherit token workflows.
- Added explicit reversible-fixture and authority boundaries for destructive deletion, static-only handling for unauthorized production probes, and concise sentence-only async triage.
- Added local-judge discipline for negated criteria, unexecuted planning evidence, bounded missing-material requests, and stack-neutral placeholders after recorded judge inversions.
- Added Codex plugin distribution, Build Week provenance, a fictional judge path, and public distribution-integrity checks at the repository layer.

## 1.0.0 — 2026-07-16

- Initial free public-release candidate.
- Added the verification operator and independent reviewer skills.
- Added standard-library deterministic inspection, validation, normalization, smell-scan, and report-assembly tools.
- Added TypeScript/Vitest/Jest, Python/pytest, and generic stack guidance.
- Added canonical schemas, templates, three complete demonstrations, behavioral evals, host adapters, and fileless fallback operation.
