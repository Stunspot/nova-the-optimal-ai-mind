# Verification report

This report states the current evidence decision and its limits. It is not the install path. To try the product, use [`../START-HERE.md`](../START-HERE.md); to inspect evidence in order, use [`../docs/JUDGE-GUIDE.md`](../docs/JUDGE-GUIDE.md).

## Decision

**READY_WITH_RESIDUAL_RISK** for the locally evidenced package only. This is a release-operator decision after reconciling the final TestForge review's documentary conditions; it is not a claim that TestForge certified release readiness, reran the package after reconciliation, or observed any external contest action.

The final complete-stage TestForge review, E-011, validly returned **`REVIEW_PASS_WITH_CONDITIONS`** for the package's own then-current **`INSUFFICIENT_EVIDENCE`** decision. It found that decision defensible and required an accurate current-review state, manifest-aligned Markdown traceability, and demo re-entry. The manifest and traceability conditions are now reconciled. The stale demo references were replaced with the current Mara Vey / Orison and final-review evidence; the 322-word, eight-scene script parsed through the production pipeline, and the final 2:52 local MP4 subsequently passed 27/27 automated checks plus three independent quality gates. stunspot completed the full watch, and the exact final filename is publicly playable on YouTube. Devpost and its remaining authorized attestations remain separate work.

## Current evidence

| Receipt | Result | Bounded claim |
|---|---|---|
| `entry-static.json` | Passed: 28 skill handles, no errors/warnings | Current entry static integrity |
| `shipping-directory-inventory.json` | 201 directories, 443 files (MIND 147; Nova 296), zero symlinks | Complete shipping-tree inventory |
| `release-extraction-validation.json` | Both archives passed official plugin validators, all 28 official skill validators, and TestForge; hashes matched | Deterministic release payload validity |
| `current-host-install.json`, `installed-cache-mind.json`, `installed-cache-nova.json` | Current refresh valid; exact 147/147 and 296/296 source/cache equality | Current host registration and installed payload fidelity after the preferred-name correction and debris cleanup; model behavior separate |
| `installed-discovery.json` | Both real Codex selectors installed and enabled at 1.0.0; cache present; 16 + 12 = 28 discovered SKILL.md directories | Current host registration and discovery only |
| `fresh-host-install.json` | Initially empty temporary CODEX_HOME: both selectors enabled at 1.0.0, 16 + 12 handles, exact 147 + 296 source/cache equality | Current clean-host install path; no authentication or model call |
| `tour-browser-command.json` | Passed five layout viewports with zero overflow; seven total activations (3 pointer, 2 keyboard, 2 touch); reduced-motion and no-JavaScript assertions passed | Bounded browser tour coverage |
| `documentation-review.md` | Full Hesperos pass across 270 Markdown files, 20 principal documents, 28 skill entrypoints, 28 picker cards, and the separately audited 158-module Nova prompt surface; 55 local links resolve | Complete product-documentation review within its stated accessibility and external-action boundary |
| `live-core-probe-status.json`, six bound current analyses, and six `live-*-public-raw.json` receipts | Valid stable index for direct-negative, tour, Ludis character, MIND decision, Agentic orientation, and professional brief. Sanitized logs retain a SHA-256 binding to ignored local raw. | Six named clean-host executions only; not universal behavioral proof |
| `live-testforge-review-pre-fix-analysis.json`, `live-testforge-review-stage-gap-analysis.json`, `live-testforge-review-index-contradiction-analysis.json` | Each is a valid historical execution with `REVIEW_FAIL` / `INSUFFICIENT_EVIDENCE`; together they exposed incomplete staging, missing custody, and index orchestration flaws. | Preserved negative audit record; not a current product pass or plugin-defect finding |
| `live-testforge-review-analysis.json`, `live-testforge-review-public-raw.json` | E-011 executed against a privacy-clean 513-file staged tree with deterministic Git binding and returned `REVIEW_PASS_WITH_CONDITIONS` for the package's preceding `INSUFFICIENT_EVIDENCE` decision. | Evidence-quality review only. It does not certify release readiness or external completion. |
| `video-production-inputs.json` | Refreshed script, shot list, and Studio Case are hash-bound; 322 spoken words in eight timed scenes; production parser passed and pipeline doctor returned `READY`. | Production-input readiness only; no final render, viewing, upload, or submission claim. |
| `video-render-verification.json` | Hash-bound 172.066667-second 1080p MP4 and matching 43-cue SRT; 27/27 automated checks and mechanical, audio/caption, and visual/privacy gates passed; stunspot confirmed the complete watch | Local render and complete-viewing evidence; public availability is recorded separately. |
| `youtube-publication-verification.json` | Exact final filename is public at `https://youtu.be/1cqEFrP6FZw`; anonymous playability exposes 1080p and audio formats; opening, midpoint, and final-card watch checks passed; stunspot confirmed the complete watch | Public video and bounded playback evidence; Devpost submission remains unobserved. |
| `repository-publication.json` | GitHub reports `Stunspot/nova-the-optimal-ai-mind` as `PUBLIC` on `main`; the first published remote revision matched local commit `57857ae…`. | Initial publication metadata and first-push parity only; later judge-facing content is covered by the separate final-content receipt. |
| `repository-final-content-verification.json` | Judge-facing content commit `8e0f1f8…` matched local `HEAD` and `origin/main`; anonymous repository and raw-README requests returned HTTP 200 with the exact public-video link present; both release ZIP hashes matched. | Final judge-facing content and release readback; no Devpost, rights, or team claim. |

## Conditions and residual risks

The final review's current-review-state and traceability-ID conditions are addressed in `verification-manifest.json` and `traceability-matrix.md`. The final review was not rerun after that reconciliation, so the work is honestly a post-review documentary fix, not reviewer recertification. Demo re-entry is addressed at the canonical-input, local-render, human-viewing, and public-playback layers by the two video receipts.

- The original six core live executions are content-hash-bound but not Git-revision-bound.
- Sanitized public receipts are SHA-256-bound derivatives of ignored local raw; an external reviewer cannot compare the private originals.
- The nested review host blocked independent reruns of helper scripts, Git state, and archive hashes.
- The six core prompts and the one TestForge prompt are narrow samples.
- Live Devpost feedback/provenance entry, rights, team acceptance, and Devpost submission remain human/external gates.

Current installation/discovery/cache checks and the public video are green within their named boundaries. Do not convert fresh-host installation, browser coverage, the seven named live scenarios, or local `READY_WITH_RESIDUAL_RISK` into universal specialist-behavior, rights, Devpost entry, or submission claims.
