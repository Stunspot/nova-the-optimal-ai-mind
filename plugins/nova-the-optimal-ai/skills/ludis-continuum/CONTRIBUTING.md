# Contributing

Contributions are welcome when they preserve Ludis Continuum's core contract: player agency, creator voice, explicit authority, provenance, privacy, and the difference between generated confidence and accepted canon.

## Before proposing a change

1. Open or search an issue describing the user problem.
2. State whether the change affects product behavior, an instrument, documentation, schema, tool behavior, or presentation.
3. Identify any compatibility, privacy, rights, accessibility, or migration consequence.
4. Use synthetic fixtures; do not contribute private campaigns or licensed source text.

## Local checks

```powershell
python -B scripts/self_check.py
python -B scripts/validate_ledger.py assets/campaign.template/campaign-ledger.json
```

For tool changes, add or document a focused positive and negative probe. For documentation changes, exercise every changed link and read the resulting customer journey from install through removal. For image changes, inspect the actual pixels at native size and likely crop; dimensions and filenames are not visual evidence.

## Instrument changes

An instrument should own one coherent creative transformation, remain setting-free, preserve user canon, distinguish player-facing and GM-only layers where relevant, and avoid inventing authoritative mechanics. Update the manifest intentionally and explain provenance.

## Export adapter changes

Keep target mapping pure and deterministic: projection and frozen asset bytes go in; a path-to-bytes bundle and explicit loss report come out. Add positive, blocking, malformed-input, determinism, and no-input-mutation probes. Never infer game mechanics, relax player visibility, add network credentials, or promote a local import observation into a product compatibility claim. Target a named official format/version and link the authority used.
## Documentation and Pages

A content change invalidates prior review receipts. Run a fresh Hesperos documentation review, accessibility review, and adversarial verification against the final candidate. Do not edit old receipts to make them fit new bytes.

## Pull requests

Keep a pull request coherent and exclude unrelated files. Describe:

- the defect and customer consequence;
- the change;
- evidence actually observed;
- claims deliberately not made;
- migration or cleanup needs;
- final content fingerprint or commit used for review.

By contributing, you agree that your contribution is provided under the repository's [MIT License](LICENSE.md) and that you have the right to submit it.