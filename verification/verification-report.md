# Verification report

## Decision

**READY_WITH_RESIDUAL_RISK** for the locally evidenced package only. This is a release-operator decision after reconciling the final TestForge review's documentary conditions; it is not a claim that TestForge certified release readiness, reran the package after reconciliation, or observed any external contest action.

The final complete-stage TestForge review, E-011, validly returned **`REVIEW_PASS_WITH_CONDITIONS`** for the package's own then-current **`INSUFFICIENT_EVIDENCE`** decision. It found that decision defensible and required an accurate current-review state, manifest-aligned Markdown traceability, and demo re-entry. The manifest and traceability conditions are now reconciled. The stale demo references were replaced with the current Mara Vey / Orison and final-review evidence; the 322-word, eight-scene script parsed through the production pipeline and its host doctor returned `READY`. Rendering, complete audiovisual viewing, upload, and the other external gates remain separate work.

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
| `live-core-probe-status.json`, six bound current analyses, and six `live-*-public-raw.json` receipts | Valid stable index for direct-negative, tour, Ludis character, MIND decision, Agentic orientation, and professional brief. Sanitized logs retain a SHA-256 binding to ignored local raw. | Six named clean-host executions only; not universal behavioral proof |
| `live-testforge-review-pre-fix-analysis.json`, `live-testforge-review-stage-gap-analysis.json`, `live-testforge-review-index-contradiction-analysis.json` | Each is a valid historical execution with `REVIEW_FAIL` / `INSUFFICIENT_EVIDENCE`; together they exposed incomplete staging, missing custody, and index orchestration flaws. | Preserved negative audit record; not a current product pass or plugin-defect finding |
| `live-testforge-review-analysis.json`, `live-testforge-review-public-raw.json` | E-011 executed against a privacy-clean 513-file staged tree with deterministic Git binding and returned `REVIEW_PASS_WITH_CONDITIONS` for the package's preceding `INSUFFICIENT_EVIDENCE` decision. | Evidence-quality review only. It does not certify release readiness or external completion. |
| `video-production-inputs.json` | Refreshed script, shot list, and Studio Case are hash-bound; 322 spoken words in eight timed scenes; production parser passed and pipeline doctor returned `READY`. | Production-input readiness only; no final render, viewing, upload, or submission claim. |

## Conditions and residual risks

The final review's current-review-state and traceability-ID conditions are addressed in `verification-manifest.json` and `traceability-matrix.md`. The final review was not rerun after that reconciliation, so the work is honestly a post-review documentary fix, not reviewer recertification. Demo re-entry is addressed at the canonical-input layer by `video-production-inputs.json`; the final MP4 and human viewing remain unobserved.

- The original six core live executions are content-hash-bound but not Git-revision-bound.
- Sanitized public receipts are SHA-256-bound derivatives of ignored local raw; an external reviewer cannot compare the private originals.
- The nested review host blocked independent reruns of helper scripts, Git state, and archive hashes.
- The six core prompts and the one TestForge prompt are narrow samples.
- Repository access, public video, feedback/provenance, rights, team acceptance, and Devpost submission remain human/external gates.

Current installation/discovery/cache checks are green within their named boundaries. Do not convert fresh-host installation, browser coverage, the seven named live scenarios, or local `READY_WITH_RESIDUAL_RISK` into universal specialist-behavior, public-repository, video, rights, or submission claims.
