# TypeScript API change walkthrough

This synthetic project demonstrates authorization, idempotency, transaction ordering, Vitest adaptation, and an honest blocked execution boundary.

1. Run `scripts/inspect_repo.py` and `scripts/detect_test_stack.py` against `input/`; Vitest and npm should be detected.
2. Read the requirement, service, and existing test. The existing test covers only ordinary provider success.
3. Inspect `demonstration.md` for the transition from provider-ordering evidence to the critical retry scenario.
4. Validate `expected/verification-manifest.json` with the example directory as `--root`.
5. Execute the generated test only after installing the declared dependencies with human approval. Until then, retain `E-001` as blocked and the test as unexecuted.

Expected decision: `NOT_READY`. The critical defect is visible in source ordering; runtime evidence and provider-contract evidence remain unavailable.
