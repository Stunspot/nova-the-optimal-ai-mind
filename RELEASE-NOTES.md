# Nova + MIND Free release notes

## 2.0.7

The installer now completes a disposable MIND estate and live semantic-association preflight before adding the marketplace, installing either plugin, or committing the customer database. A missing Ollama service or embedding model therefore fails before consequential installation state is created.

Plugin steps are idempotent and the verified database moves into place only at the final commit point, making interrupted or partially completed plugin work safe to resume. This combined release carries MIND 2.1.5; its reminder cards, embeddings, and model-context contract are unchanged from 2.1.4.

The release builder now has a non-mutating help path, refuses to overwrite existing outputs without explicit replacement, rejects uncommitted tracked source, and records the source revision and source-material digest in both the customer manifest and build receipt.

Installer and verifier Python calls suppress bytecode generation so customer execution does not add cache artifacts to the unpacked release.

The root installer and readback verifier now resolve the customer archive's codex/ marketplace layout as well as the maintainer source layout. This closes a source-only verification gap that made the previous 2.0.7 candidate fail before preflight when run from its own ZIP.

## 2.0.6 — public-experience release

Nova + MIND Free 2.0.6 packages Nova plugin 2.0.1 with MIND plugin 2.1.4. The Arm’s Reach model-facing preface no longer encourages capability-catalog exploration; it asks the model to assess vector-near reminders in context and integrate only relevant praxis already available through the assembled host context.

The package retains forty-one unique skill handles, sixteen MIND Faculties, Capability Promotion, and both TestForge roles. The public reminder estate contains forty-one cards and 246 vectors and remains explicitly `unqualified` pending broader behavioral qualification.

This documentation remediation adds a complete customer journey, multi-page GitHub Pages site, repository-correct support and security routes, explicit installation/readback semantics, lifecycle cleanup, and three distinct role-specific presentation assets. Final documentation, accessibility, adversarial, publication, and live-reentry evidence is recorded under `verification/`.

## 2.0.5 — hook-owned association

Association moved fully into the trusted pre-prompt hook. Nova and MIND no longer ask the model to locate, invoke, or retry an association adapter. Empty or failed delivery makes no claim about capability availability, relevance, or fit.

## 2.0.4 — last previously published GitHub release

The GitHub release previously available before 2.0.6 bundled Nova 2.0.1 with MIND 2.1.2. It introduced the forty-one-skill product shape and per-skill Claude archives. Do not infer current source behavior from that older artifact after 2.0.6 publication.

## Version layers

- Product release: Nova + MIND Free 2.0.6
- Nova plugin: 2.0.1
- MIND plugin: 2.1.4
- MIND Core: 0.2.x

These layers version different components and are intentionally not numerically identical.

## Evidence boundary

Deterministic build and verification can establish package topology, canonical bytes, version synchronization, release exclusions, reminder assets, links, archive shape, and fingerprints. It does not establish fresh-host success, hook trust, pre-turn delivery, model attention, Claude parity, universal behavior, publication, or defect-freedom. Read [What has been checked](docs/VERIFICATION.md).
