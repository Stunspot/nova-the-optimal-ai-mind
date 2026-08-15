# Omnara 1.0.1 reconciliation record

Status: CANDIDATE — pending merge, exact-commit package build, publication, and readback.

## Reconciled inputs

- Historical Omnara 0.1.1 customer distribution: dual-host wrapper containing the verified Codex skill and Claude package.
- Standalone Omnara 1.0.0 public source and release.
- Default-branch changes after 1.0.0: live-publication evidence and clearer deep-research product framing.

## Content disposition

A topology-aware comparison matched the historical Codex skill against the standalone source tree. Thirty-two runtime files were byte-identical. The only changed runtime file was `scripts/validate_release.py`; the standalone version expands validation with source/runtime profiles, JSON and JSONL checks, local Markdown-link checks, and broader source/package requirements. That later validator is retained.

The standalone repository additionally carries the maintained customer documentation, Pages source, visual assets, tests, and verification records. Historical wrapper-only files—inner Claude ZIP, host matrix, package reference, provenance wrapper, release manifest, and checksum list—remain historical release evidence rather than competing runtime source.

## Release invariant

The final 1.0.1 release is acceptable only when:

1. local `main` and GitHub `main` resolve to the same commit;
2. tag `v1.0.1` resolves to that exact commit;
3. `omnara-deep-research-v1.0.1.zip` is built from that commit with a single `omnara-deep-research-v1.0.1/` prefix;
4. the GitHub release asset and central distribution ZIP have identical SHA-256 hashes;
5. the extracted archive passes source validation and unit tests.

This record does not claim fresh-host installation, discovery, invocation, semantic citation correctness, or research completeness.