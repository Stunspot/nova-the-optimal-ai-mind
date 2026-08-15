# Validation status

This file describes the repository's evidence model. Exact remediation receipts are stored under `verification/remediation-2026-08-12/` and are bound to the final candidate fingerprint or commit recorded there.

## Deterministic checks

Run from the repository root:

```bash
python scripts/self_check.py
python -m unittest discover -s tests -v
python scripts/inspect_infographic_html.py docs/index.html
```

For a newly initialized test project, also run the initializer and `validate_loomfile.py`. For packaging, use a new output path outside the Loomfile, extract the resulting one-root ZIP, validate the extracted root, and inspect its release manifest.

## What these checks can establish

- required package resources exist and are regular files;
- frontmatter identity, manifest identity, declared hosts, and JSON parseability satisfy implemented rules;
- the initializer produces the required directory/state skeleton;
- the Loomfile validator enforces its implemented path, enum, hash, claim-linkage, and stage rules;
- the HTML inspector enforces its named static structure and risky-pattern rules;
- the packager rejects output inside the Loomfile, validates source and extracted archive state, preserves required empty directories, excludes symbolic links and named secret-like files, hashes the exact bytes written to every ZIP file payload, embeds the generated release manifest without mutating the Loomfile, refuses existing or competing output, removes partial temporary archives, preserves any destination after an ambiguous final-link interruption, and requires explicit inspection before reuse or removal.

## What remains separate

These checks do not by themselves establish:

- fresh-host installation, discovery, invocation, or health on Codex or Claude Code;
- rendered visual correctness, navigation behavior, responsive behavior, or live publication;
- keyboard, zoom/reflow, contrast, screen-reader, or formal accessibility conformance;
- sanitization, absence of secrets, security, privacy compliance, or dependency trust;
- factual correctness beyond the supplied source/claim records;
- professional, legal, medical, financial, or commercial fitness;
- user approval, export approval, publication, reach, or platform performance.

A check result is valid only for the exact bytes reviewed. Any post-review documentation, CSS, HTML, script, schema, or asset change invalidates the affected receipt and requires re-review.