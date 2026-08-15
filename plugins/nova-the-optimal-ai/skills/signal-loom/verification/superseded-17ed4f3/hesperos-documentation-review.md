# Hesperos documentation review

- Candidate commit: `17ed4f30975081b4a020dd8e28e6a35eb0edda1d`
- Governed fingerprint: `bc6ca8a21832c6bb3428e5649a0be27feffacc1a34d746510604a194ca2b7ab1` (59 tracked files; verification evidence excluded)
- Product version: `0.1.0`
- Review result: **HESPEROS_PASS**

## Reader and task

The reader has supplied evidence and needs to decide whether Signal Loom fits, install it on Codex or Claude Code, verify each activation layer, complete a first Loomfile workflow, understand inputs and outputs, recover from failures, govern privacy and security, update or remove the skill, and find support.

## Source reconstruction

Every current customer-facing document was read completely. After the final redesign, `README.md`, `docs/CUSTOMER-GUIDE.md`, `docs/index.html`, `VALIDATION.md`, and `CHANGELOG.md` were reread top to bottom. The final packager and all seven tests were read completely. Every new integrity/recovery claim was traced to directly executed behavior.

The packager now treats the completed ZIP as the only committed artifact. It hashes the exact stream written to each archive payload, writes the generated manifest inside that ZIP, leaves the Loomfile's project-side manifest record unchanged, creates the final name without overwrite through a same-directory hard link, and removes final/temporary artifacts on failed or interrupted commit. The documentation distinguishes the project-side record from the archive-embedded generated manifest and discloses the filesystem requirement.

## Customer journey result

The combined README and Pages journey covers product, audience, problem, capabilities, limits, both declared hosts, verification, first value, realistic workflows, expected state and outputs, configuration, troubleshooting, recovery, update, removal, data cleanup, privacy, storage, network behavior, security, limitations, provenance, validation, support, contribution, licensing, and terms boundaries.

The former brochure, stale version label, generic particle-wave visual, generic 404, and missing lifecycle/support paths remain repaired. Three separate role-specific visuals remain correctly wired and byte-identical to the inspected assets.

## Review-driven repairs

Accessibility repairs remain intact: light-surface link/focus contrast, 12px install-label contrast, and narrow-screen reflow.

TestForge exposed four package-integrity failures across successive candidates: existing-output mutation, interrupted-write mutation/partial output, precomputed hashes diverging from concurrently changed payloads, and an after-replacement interruption splitting project/archive state. After two failures on the two-artifact premise, packaging was redesigned as a single-artifact commit. Seven regression tests now cover archive payload/manifest identity, unchanged project state, existing output, competing output, mid-write failure, concurrent source mutation, post-link interruption, cleanup, and retry.

## Verification

- Hesperos Markdown lint: eight authored docs pass.
- Package self-check: pass.
- Unit tests: seven pass.
- Pages and 404 bounded HTML inspection: pass, zero warnings each.
- Local document, asset, site-root, and same-page anchor targets resolve.
- Exact visual hashes remain unchanged from actual-pixel review; roles remain distinct and the social card visibly contains `SIGNAL LOOM` and `Evidence-to-visual story production`.

## Claim boundary

HESPEROS_PASS establishes complete source-bounded documentation content for this exact commit and fingerprint. It does not establish fresh-host host activation, rendered browser behavior, assistive-technology compatibility, security, formal accessibility conformance, publication, or live Pages correctness. Those remain separate gates.

Any governed-content change invalidates this receipt.