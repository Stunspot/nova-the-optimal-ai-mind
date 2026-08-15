# Contributing

Contributions that strengthen source custody, documentation, accessibility, deterministic checks, portability, or honest evidence boundaries are welcome.

## Before editing

- Open or reference an issue for consequential behavior changes.
- Preserve the distinction among constructed, packaged, installed, discoverable, invoked, healthy, approved, and published.
- Do not add telemetry, remote runtime dependencies, automatic publication, invented sample evidence, or silent execution of supplied HTML.
- Do not rewrite frozen historical archives to make current documentation agree with them.
- Never commit credentials, private sources, proprietary Loomfiles, or generated archives containing them.

## Verify a change

Run from the repository root:

```bash
python scripts/self_check.py
python -m unittest discover -s tests -v
python scripts/inspect_infographic_html.py docs/index.html
```

For documentation or visual changes, also:

- read every changed customer-facing document completely;
- open and inspect every changed image at actual pixels;
- exercise all local links and navigation;
- perform a separate documentation accessibility review;
- perform an adversarial review of claims and evidence boundaries;
- bind review evidence to the exact candidate commit or documentation fingerprint.

Static checks do not replace rendered browser, keyboard, zoom/reflow, screen-reader, security, or fresh-host testing. State what was not tested.

## Pull requests

Keep the change coherent and avoid unrelated formatting churn. Explain the user problem, material changes, exact commands and results, unproved evidence layers, and any migration or rollback considerations. By contributing, you agree that your contribution is licensed under the repository's [MIT License](LICENSE.md).