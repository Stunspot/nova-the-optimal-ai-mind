# Hesperos documentation review

- Candidate commit: `f1126cd0fc8f0ed1a88fa05928a40b417d8c214b`
- Governed fingerprint: `e0449cdbf63f6c9d3c87cf60d60394f1ddab25593bef21e210d716c237f92b0b` (59 tracked files; verification evidence excluded)
- Fingerprint order: exact `governed-files.txt` order, maintained as case-insensitive path order
- Product version: `0.1.0`
- Review result: **HESPEROS_PASS**

## Reader and top task

The intended reader has supplied evidence and needs to decide whether Signal Loom fits, install it on Codex or Claude Code, verify each activation layer, complete a first Loomfile workflow, understand inputs and outputs, recover without destroying evidence, govern privacy and security, update or remove the skill, and find support.

## Source reconstruction and review method

The full customer corpus was assessed as one journey: `README.md`, `docs/CUSTOMER-GUIDE.md`, `docs/index.html`, `docs/404.html`, `docs/SITE-SOURCE.md`, `SECURITY.md`, `SUPPORT.md`, `CONTRIBUTING.md`, `VALIDATION.md`, `CHANGELOG.md`, `LICENSE.md`, `SKILL.md`, both fallback guides, and the product doctrine needed to verify claims. Exact per-file hashes preserved the earlier complete reading only for unchanged bytes. Every changed document was reread top to bottom. `scripts/package_loomfile.py`, `tests/test_init_loomfile.py`, `scripts/validate_loomfile.py`, `scripts/init_loomfile.py`, and `manifest.json` were read completely for the changed runtime and packaging claims.

The source uses PEP 604 union annotations; therefore Python `3.9+` was an unsupported documentation claim. README, customer guide, Pages, and `manifest.json` now consistently state Python 3.10+ for the deterministic helpers. No Python 3.9 execution claim remains.

## Customer journey result

The combined repository and Pages documentation now provides a viable path through:

- product, intended audience, problem, capabilities, and non-capabilities;
- Codex and Claude Code installation, discovery, invocation, and health verification;
- a realistic first brief, workflow examples, expected state, inputs, and outputs;
- Loomfile configuration, claim states, stage and authority rules;
- troubleshooting, safe stopping, evidence-preserving recovery, update, removal, and data cleanup;
- privacy, local storage, host-provider network boundaries, hostile-input boundaries, secrets limitations, and security reporting;
- known limitations, provenance, validation layers, support, contribution, licensing, and input/output rights boundaries.

README serves orientation and first success; the customer guide carries the full operational lifecycle; Pages supplies a polished task-first route with navigation and recovery; root policies provide durable reference.

## Review-driven repairs confirmed

The final packaging contract now matches executable behavior:

1. the requested ZIP must resolve outside the Loomfile before any packaging side effect;
2. required empty directories receive explicit ZIP entries and survive extraction;
3. exact file-entry bytes determine the embedded release-manifest hashes;
4. the completed archive is extracted and its Loomfile state revalidated before exposure;
5. a registered source changed after pre-validation is rejected as invalid archived state;
6. final publication uses a non-overwriting hard link; if linking creates the output and then raises, file-identity recovery removes only this operation's owned output;
7. the project-side manifest remains unchanged, competing output is preserved, failed artifacts are cleaned, and retry remains possible.

The former brochure, stale product/version wording, generic visual identity, generic 404, missing lifecycle/support paths, accessibility contrast defects, and weak packaging claims remain repaired. The three role-specific images remain byte-identical to their retained actual-pixel reviews and correctly wired.

## Verification

- Hesperos accessible-Markdown lint: nine authored documents pass.
- Package self-check: pass.
- Unit tests: ten pass, including all four exact independent-review counterexamples.
- Pages and custom 404 bounded HTML inspection: pass with zero warnings each.
- Fresh local document, asset, Pages-base, and same-page anchor check: 35 targets, zero failures.
- Runtime claim audit: source union syntax and all public declarations agree on Python 3.10+.
- Governed fingerprint: independently recomputed, 59 files, exact match.
- Exact visual hashes remain unchanged from actual-pixel review: README hero `7f8c710124a7d277def62b997276a2bfb5a39f540f353ab57d2b001708a6d878`; Pages hero `188d9101651244b17d82b8dd0fa16916b51dfd469cc5665ed8efae5134daeeb7`; social card `6446c77f285606f3468a22080fe8494e4de9989f9c1352d4de17e28413931fb2`.

## Post-review change and re-review

The independent accessibility review of the prior exact candidate found three broken canonical faculty table-of-contents fragments. Commit `f1126cd0fc8f0ed1a88fa05928a40b417d8c214b` changed only those three destinations. Hesperos rechecked the complete nine-link table of contents against its target headings using GitHub-compatible per-space fragment behavior: nine links, zero broken fragments. No product, procedure, runtime, visual, presentation, or customer-entry content changed. The prior receipt was invalidated; this receipt binds the repaired bytes.
## Claim boundary

HESPEROS_PASS establishes complete source-bounded documentation content for commit `f1126cd0fc8f0ed1a88fa05928a40b417d8c214b` and fingerprint `e0449cdbf63f6c9d3c87cf60d60394f1ddab25593bef21e210d716c237f92b0b` only.

It does not establish fresh-host installation, host discovery or invocation, rendered browser behavior, assistive-technology compatibility, security, formal accessibility conformance, publication, or live Pages correctness. GitHub-hosted Actions were not invoked. The current live Pages site remains pre-remediation and cannot substantiate these candidate bytes.

Any governed-content change invalidates this receipt.
