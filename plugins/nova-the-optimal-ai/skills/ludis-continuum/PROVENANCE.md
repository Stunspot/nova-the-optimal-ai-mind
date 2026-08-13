# Provenance, validation, and evidence status

This file separates what Ludis Continuum contains from what has actually been exercised. Presence is not behavior. A passing local check is not a fresh-host result, a live VTT import, or a public release.

## Provenance

This standalone repository preserves the curated Ludis Continuum skill from the public Nova + MIND OpenAI Build Week release and extends it with governed campaign-ledger and offline export tooling. Private development history, private campaign material, and worked campaign worlds are excluded.

- Source candidate edition: `1.1.0`
- Canonical campaign-ledger format: `cd-ludis-campaign-ledger/v2`
- Legacy ledger handling: read-only recognition plus explicit migration from `0.1.0`; legacy approval evidence grants no current authority
- Neutral pack format: `cd-ludis-pack/v1`
- Narrow target profiles: Alchemy character JSON and Foundry VTT generation 14, authored against build 14.365
- Import-observation format: `cd-ludis-import-observation/v1`
- License: MIT
- Bundled Python runtime dependencies: Python 3.10 or later, standard library only
- Creative corpus: 32 compact instrument cores listed in `knowledge/instruments/manifest.json`

The generated example map and token were created specifically for this repository with OpenAI image generation. Exact hashes, alternative text, rights status, credit, and provenance are stored in `examples/tonight-pack/campaign/campaign-ledger.json`. They are raster artwork, not programmed SVG substitutes.

The instrument manifest describes its corpus as semantically rewritten derivative material with legacy source retained only for provenance. It does not by itself prove originality or rights clearance; publication review remains human work.

## Current local evidence

| Claim | Status | Evidence boundary |
|---|---|---|
| Standalone package constructed | Verified locally | Required source, doctrine, fallbacks, schemas, tools, host metadata, examples, and generated assets are present in the reviewed local candidate. |
| Curated package self-check | Verified locally | `python -B scripts/self_check.py` passes for all 32 instrument cores and the required export assets and schemas. |
| Ledger v2, migration, and authority guards | Verified locally | Tests cover identity, unknown-value preservation, legacy-authority quarantine, transitive player visibility, guarded promotion, Windows final-boundary replacement, POSIX displaced-generation comparison and recovery, competing writers, source drift, and write/replace faults. |
| Frozen campaign capture | Verified locally | Tests cover root confinement, symlink and reparse rejection, declared digests, per-file capture checks, and an end-of-capture recheck of the ledger and every declared asset. |
| Neutral Ludis Packs | Verified locally | Tests and the generated example cover deterministic ZIPs, canonical member names, unique asset paths, manifests, previews, player filtering, immutable candidates, complete write-set reservation, and unchanged final bytes. |
| Alchemy character JSON | Statically verified locally | The conservative adapter validates mapped native structures, requires an explicit `systemKey`, emits individual and bulk files, and reports losses. No current Alchemy account import was observed. |
| Foundry v14.365 offline module | Statically verified locally | Tests cover exact trusted importer bytes, strict manifest/member allowlists, campaign-scoped identity, exact-revision resume, changed-import conflicts, audience ownership, core document mappings, Level backgrounds, safe assets, and JavaScript syntax. No running Foundry import was observed. |
| Import-observation receipt | Verified locally | Tests bind one unauthenticated local observation to exact bundle and optional evidence bytes, require a timezone, refuse overwrite, and fix product-compatibility promotion to false. |
| Generated example workflow | Verified locally | GM and player neutral packs, Alchemy JSON, and GM/player Foundry modules build and verify. Generic and Foundry player finals preserve the reviewed candidate SHA-256 exactly. |
| Documentation and Pages source | Reviewed locally | Root journeys and six static Pages routes cover setup, operation, exports, approvals, target imports, recovery, and evidence limits. Live deployed Pages were not changed or rechecked. |
| Fresh-host installation and host discovery | Not independently verified | Source shape and manual instructions exist; no fresh Codex or Claude host receipt is inferred from this checkout. |
| Live Alchemy or Foundry compatibility | Not verified | Static conformance does not establish platform recognition, database acceptance, rendering, grid alignment, player visibility, or repeat-run behavior. |
| Live-table quality, balance, rules accuracy, accessibility, originality, or semantic spoiler safety | Not independently verified | These require representative people, authoritative rules or platform access, and campaign-specific review. |

## Evidence custody

The 2026-08-12 receipts under `verification/` describe the earlier 1.0 public release and remain historical evidence. They do not apply to this changed 1.1 local candidate.

The current enhancement review uses `verification/export-verification-manifest.json` plus dated adversarial, documentation, and accessibility receipts. Those records bind to a content fingerprint of the final present files while excluding `verification/*.json` to avoid a receipt hashing itself. Any product or documentation change after fingerprinting invalidates the current receipts and requires a fresh review.

No GitHub-hosted Actions were invoked for this candidate. GitHub publication, a release tag, deployed Pages, marketplace installation, and live VTT imports are outside this local evidence cycle.

## Interpreting a local PASS

A local PASS means the named source, tests, example commands, and static reviews succeeded against one exact candidate. It does not widen the product claims beyond the evidence table. In particular, “statically validated” never means “the current service imported it,” and an unauthenticated local approval or observation is evidence of an operator assertion, not verified identity.
