# What has been checked

This page separates constructed, packaged, installed, discoverable, invoked, healthy, published, and independently verified. Those states are not synonyms, however much release notes occasionally wish they were.

## Source and package verification

At the final documentation commit, maintainers run:

```powershell
python -m unittest discover -s tests -v
python -X utf8 .\tools\verify_package.py
python -X utf8 .\tools\build_release.py
python -X utf8 .\tools\verify_package.py --release
python -X utf8 .\plugins\augment-of-mind\scripts\build_release.py --output-dir <empty-path> --replace
```

The repository and embedded Continuity suites use deterministic tests for the forty-one unique skill roots, sixteen-Faculty boundary, two TestForge roles, product/plugin/Core/Continuity version contracts, workspace schema v2, all four Worldline views, Faultline Error Neighborhood and mutation controls, metered-capacity arithmetic and authority denial, linked design evidence, standalone MIND prerequisites, exclusions, canonical Nova and Promptcraft bytes, model-context delivery, reminder cards and vectors, links, portable Claude ZIP shape, deterministic package construction, and integrated fingerprints.

The final release gate requires the [source lock](../design/source-lock.json) to bind the frozen product version, imported component commits, selected paths, and exact tree digests. The package verifier recomputes imported trees instead of trusting the JSON record. During this local source freeze the lock and integrated fingerprint remain intentionally deferred; a package PASS is not claimed until both are regenerated from the final bytes and rechecked.

The permanent public workflow is configured to run the source suite, deterministic combined-package build, portable-release verification, and embedded standalone MIND build on Linux, Windows, and macOS. A configured workflow is not an executed workflow. Hosted-provider capacity, a successful run on the frozen commit, publication, and asset readback remain separate release evidence.

A source/package pass means the tested tree has those properties. It does not mean a customer installed it, a host discovered it, a hook was trusted, a model used it, or the package works in every environment.

## Reminder evidence

The bundled public estate contains forty-one capability cards and 246 vectors for local `qwen3-embedding:0.6b` association at radius `0.33`. Isolated activation, SQLite integrity, foreign-key checks, representative semantic probes, and the prompt hook’s local path have been exercised.

The profile remains `unqualified`. Mechanical operation does not establish broad retrieval quality, hook trust on a customer machine, delivery before a provider turn, model attention, correct route selection, or successful specialist behavior.

## Continuity, Worldline, and Faultline evidence

Local disposable-workspace tests exercise Cognitive Continuity 0.2.2/workspace schema v2, v1 read-only compatibility, immutable generations, expected-generation and idempotency controls, correction, forgetting, export, validation, and recovery. The migration regression also proves exact preservation of bounded oversized v1 content, generation-0 manifest/receipt provenance binding, ordinary v2 size enforcement, unchanged carry-forward, governed removal/restoration, and pre-intent denial of self-consistent forged provenance. Worldline tests exercise deterministic `resume`, `status`, `checkpoint`, and `inspect` views, generation-race retry, source/provenance selection, false-completion withholding, portable fallback, no-view behavior, absence of writes, highly matching global-operative exclusion, and explicit unrepresented-project degradation. Faultline tests exercise redacted occurrences, governed patterns, zero-to-three-card neighborhoods, expiry, scope and sensitivity filters, retry collapse, noncausal recurrence, human-authority gates, and typed v1 rejection.

Those observations are local source/runtime evidence. They do not establish packaged bytes, installation, fresh-task discovery, live `NOVA_CONTINUITY_HOME` selector resolution, migration of a customer workspace, external-system health, or correct model use. A Worldline view does not prove persistence or completion; a Faultline card does not prove cause, safety, repair, or authority.

## Installation evidence

`verify-install.ps1` can read the configured marketplace and enabled plugin versions, create a temporary read-only verification copy of the database, inspect its generation and integrity, and exercise semantic association without intentionally modifying the live store.

A PASS from that script establishes the observations written in its report for that machine and run. The user must still inspect the hook, start a fresh task, confirm discovery, and evaluate actual behavior. The script does not inspect, create, migrate, or validate a Cognitive Continuity workspace and does not establish Worldline or Faultline health.

## Host support evidence

- **Codex plugin source and deterministic packaging:** verified.
- **Codex installer/readback implementation:** present and mechanically testable; release publication and a clean customer installation remain separately evidenced observations.
- **Claude per-skill archives:** structurally verified; representative live upload and cross-skill behavior are not claimed here.
- **Generic hosts, ChatGPT web, Codex IDE extension, macOS/Linux integrated runtime:** not supported or independently verified by this release.

See [Host matrix](HOST-MATRIX.md) for the exact boundary.

## Documentation and presentation evidence

Before publication, the candidate documentation set requires:

1. a Hesperos customer-journey authorship and review pass;
2. a separate accessibility review of structure, language, contrast, focus, resizing, reduced motion, alt text, and navigation;
3. a separate TestForge adversarial verification pass;
4. live HTTP and visual re-entry after GitHub Pages deployment, recorded as release-specific post-publication evidence.

Receipts identify the reviewed candidate and documentation fingerprint. Any later customer-facing content change invalidates those content-bound receipts and requires review again.

## What is not claimed

No verification establishes defect-freedom, universal model compliance, universal retrieval quality, legal/professional correctness, physical execution, credentialed access, hosted uptime, accessibility conformance across every assistive technology, or commercial support approval.
