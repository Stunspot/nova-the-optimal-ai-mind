# Adversarial verification review - Signal Loom

Receipt: `SIGNAL-LOOM-ADVERSARIAL-4b88d1e-2915a01f-20260812`

- Target: `4b88d1e7c7284797227b71497913b51b26f28156`
- Fingerprint: `2915a01f8e71be06945993fee6b41889e263f3f8b9c3969495799bcda47f0e97`
- Evidence cutoff: final local verification before public branch push
- Reviewer verdict: `REVIEW_PASS_WITH_CONDITIONS`
- Proposed TestForge status: `READY_WITH_RESIDUAL_RISK`

The review first rejected `d33f4fd...`: its `stat`-then-`unlink` cleanup still allowed a competitor replacement between the identity check and deletion. Builder custody replaced that design. This new candidate performs no destination deletion after linking begins. Its deterministic regressions prove that a complete owned ZIP survives post-link interruption, retry cannot overwrite it, a replacement written by another process survives cleanup, project state is unchanged, and unique temporary paths are removed.

Oracle challenge: the tests assert archive payload hashes and byte counts, required-directory round trip, extracted-root validation, project immutability, destination bytes, absence of temporary paths, overwrite refusal, and retry behavior. The TestForge smell scanner reports seven low `snapshot_assertion` lexical hits, but manual inspection shows exact project/path/hash tuples and byte comparisons rather than undifferentiated snapshot approval; the warnings do not weaken the critical oracles.

Documentation, static accessibility, exact-pixel visual roles, local links/fragments, package self-check, bounded HTML checks, line-ending policy, and diff hygiene pass. Tool-wrapper failures remain separately classified and did not alter the candidate or its verdict.

Conditions before repository PASS: push the exact evidence commit to a feature branch, allow public standard-runner status checks, merge without weakening rules, wait for Pages deployment, and verify remote commit, live navigation, custom 404, README hero, Pages hero, social card, metadata, and exact asset bytes. GUI-rendered and assistive-technology behavior remain NOT TESTED under the current tool constraint; no such claim is issued.

This was a separate adversarial lens in the same agent context because delegation was not authorized. It does not claim independent-agent review. Any governed-file change reopens the affected review lenses.
