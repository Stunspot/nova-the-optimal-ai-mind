# Keep a usable native case

Use **Start a case** in the Studio for a short guided intake, or copy `assets/it-case.template.json` from this skill folder into an owner-controlled location. The template is an incomplete starting document; populate `case_id`, update time and a usable `next_move.action`. Do not turn unknowns into measurements to satisfy a checker.

The native record keeps device/complaint/custody, evidence, hypotheses, tests, changes, sources, verification and next move. Every member of the five record collections needs a nonempty unique `id`. Supplied ID references are arrays of nonempty strings; a missing referenced record remains visible for review. Additional owner fields are preserved. Arrays may be empty when nothing is known or performed.

Current evidence uses `kind` and `claim`; current tests use `action`, `status` and explicit boolean `performed`. Legacy `state`, `value` and `test` fields remain readable without being rewritten on import. A legacy `test-run` label without `performed=true` is unconfirmed execution, not a fabricated result. Conflicting aliases need human reconciliation.

From this **skill folder** (the folder containing SKILL.md), run:

```text
python -B scripts/validate_case_file.py path/to/case.json
python -B scripts/validate_case_file.py path/to/case.json --consistency --json
```

The first checks shape; the second additionally fails on the bounded declared-consistency findings. Correct the named field while retaining the evidence. Neither proves truth, authorization or physical repair. An incomplete case can be useful even while it has review findings.

For `verified-resolved`, record original-envelope retest and `results`; each check uses `outcome`, `observation`, `source` and `conditions`. Use `outcome: passed` only for a recorded passing check. Record adjacent checks in the same form or a specific `adjacent_not_applicable` explanation. Keep a usable `reopen_condition`. A stale verification must be reconciled explicitly. Old narrative results remain preserved and visible, but cannot receive a clean machine consistency finding until their actual basis is recorded.

Resume with `$beryl-it-tech Resume this case at its first unverified step; keep unknowns, falsified causes and authority limits intact.` A handoff should let the next actor identify the original symptom, decisive evidence, current risk, actual work, remaining uncertainty and one next action without rereading the entire conversation.
