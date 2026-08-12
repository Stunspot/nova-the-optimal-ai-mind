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

These checks cover the forty-one unique skill roots, sixteen-Faculty boundary, two TestForge roles, excluded capabilities, plugin topology and versions, canonical Nova and Promptcraft bytes, MIND runtime/version synchronization, reminder cards and vectors, release exclusions, links, portable Claude ZIP shape, deterministic package construction, and integrated fingerprints.

A source/package pass means the tested tree has those properties. It does not mean a customer installed it, a host discovered it, a hook was trusted, a model used it, or the package works in every environment.

## Reminder evidence

The bundled public estate contains forty-one capability cards and 246 vectors for local `qwen3-embedding:0.6b` association at radius `0.33`. Isolated activation, SQLite integrity, foreign-key checks, representative semantic probes, and the prompt hook’s local path have been exercised.

The profile remains `unqualified`. Mechanical operation does not establish broad retrieval quality, hook trust on a customer machine, delivery before a provider turn, model attention, correct route selection, or successful specialist behavior.

## Installation evidence

`verify-install.ps1` can read the configured marketplace and enabled plugin versions, create a temporary read-only verification copy of the database, inspect its generation and integrity, and exercise semantic association without intentionally modifying the live store.

A PASS from that script establishes the observations written in its report for that machine and run. The user must still inspect the hook, start a fresh task, confirm discovery, and evaluate actual behavior.

## Host support evidence

- **Codex plugin source and deterministic packaging:** verified.
- **Codex installer/readback implementation:** present and mechanically testable; final public release publication and a clean customer installation remain separate observations.
- **Claude per-skill archives:** structurally verified; representative live upload and cross-skill behavior are not claimed here.
- **Generic hosts, ChatGPT web, Codex IDE extension, macOS/Linux integrated runtime:** not supported or independently verified by this release.

See [Host matrix](HOST-MATRIX.md) for the exact boundary.

## Documentation and presentation evidence

The final documentation set receives:

1. a Hesperos customer-journey authorship and review pass;
2. a separate accessibility review of structure, language, contrast, focus, resizing, reduced motion, alt text, and navigation;
3. a separate TestForge adversarial verification pass;
4. live HTTP and visual re-entry after GitHub Pages deployment.

Receipts identify the exact commit and documentation fingerprint. Any later content change invalidates those content-bound receipts and requires review again.

## What is not claimed

No verification establishes defect-freedom, universal model compliance, universal retrieval quality, legal/professional correctness, physical execution, credentialed access, hosted uptime, accessibility conformance across every assistive technology, or commercial support approval.
