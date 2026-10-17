# Preserve revisions and bind the next use

A digest can identify bytes; it cannot establish that an output used its inputs faithfully. Record the production basis during real creation or an evidenced reconciliation. Read the result against its originals and use the relevant format craft. Never clear a stale warning by capturing today's inputs against yesterday's unchanged output without doing that work.

## Declare the actual inputs

The v2 artifact register keeps the existing artifact fields and adds `input_artifact_ids`, `source_ids`, `ledger_item_ids` and `input_basis`. Declare only inputs actually used. `canonical_source_id` names the governing editable artifact of a derivative; other upstream artifacts belong in `input_artifact_ids`. Source and ledger IDs point into their existing registers. A produced derivative needs its canonical parent. Dependencies must be acyclic, and two current IDs cannot claim the same file. Planned unresolved parents remain warnings until production.

For example, a workbook may use `SRC-BUDGET` and `ITEM-TOTAL`; a briefing PDF derives from `ART-BRIEF` and also uses the workbook's `ART-BUDGET`. The capture includes transitive dependencies. An unrelated ledger correction leaves that family current. A change to its declared source, controlled value, relationship or upstream file invalidates the old basis.

After actual creation, capture the current binding into a new record:

```text
python scripts/capture_artifact_binding.py OFFICEFILE ART-BRIEF --record-kind produced --evidence "working/build-brief.py and review/content-readback.md" --output OFFICEFILE/review/brief-production-v1.json
```

Use `reconciled` only when an actual documented comparison establishes that an existing output remains faithful. Copy `input_basis` from the result into that artifact's register entry. Retain the production record. Its `sha256` and `input_basis_sha256` can identify the exact output in a later review; copying them does not perform that review. The helper never changes existing registers and refuses an existing output path.

## Use a review directly

The review wrapper uses `officecraft-review/v2`. An actual operator or independent review is a `officecraft-review-entry/v2` object. Copy that complete object into the corresponding `operator_review` or `independent_review` field. Preserve the previous wrapper in `history/` first. Do not convert prose into a passing record without the underlying review.

Each passing entry names `officefile_state`, `intended_use`, `reviewer_role`, actual `reviewed_at`, and `reviewed_artifacts`. Each artifact binding contains its `artifact_id`, exact output `sha256`, and production `input_basis_sha256`. Include `material_findings` and structured `conditions`, using empty arrays when none exist. The matched reviewer template and schema use this same entry format; no second invented disposition is needed.

A condition has `id`, `statement`, `artifact_ids`, the exact `intended_use`, and status `open`, `met` or `residual_accepted`. A met condition includes `resolution_evidence`. Residual acceptance includes the accountable `owner`, `authority_kind` (`user` or `accountable_owner`), exact `approved_use`, actual `accepted_at` and `rationale`. The user must supply that authority. Open material findings identify their `condition_id`; a finding requiring REVISE or BLOCKED cannot accompany a passing disposition.

PASS_WITH_CONDITIONS remains a useful, bounded review, including while a condition is open. It cannot support an approved claim for the affected use until that condition is met or its stated residual is explicitly accepted by the same accountable approval owner. PASS has no open or accepted-residual conditions. Approval records separately bind the artifact ID, output digest, input-basis digest, owner, authority kind, approved use and actual approval time. Review never supplies approval.

Treat current reviews as cumulative constraints on the same artifact, production basis, Officefile state and intended use. An operator PASS cannot cancel an independent open condition, and the reverse is equally true. REVISE or BLOCKED for that exact scope prevents a passing reviewed or approved claim; a differently scoped review keeps its own consequence. Preserve superseded entries in history when genuine new evidence replaces them. Approve the affected use only when all its current conditions are met or explicitly accepted by the same accountable owner, with no current rejecting verdict.

Native validation checks these relationships and declarations. It does not authenticate identities, condition evidence or subject truth. Keep actual observations and remaining visual, calculation, accessibility or delivery limits in the review and HANDOFF.md.

## Return without erasing the old result

Preserve the prior Officefile or affected output/review records before changing them. Reconcile the correction at the governing source or ledger. Set affected outputs to working and move superseded passing reviews to history; keep unaffected output bindings. Regenerate or genuinely reconcile each affected output, capture the new basis, inspect it, and review the exact new versions. An unchanged PDF digest cannot keep an old review current after its source changed.

For an older v1 Officefile:

```text
python scripts/migrate_officefile.py ORIGINAL NEW-COPY
```

The destination must be new and outside the original. The original files remain unchanged. The new copy retains the old registers, brief and review under `history/pre-v2`; current output files are preserved but become working, old review/approval is historical, and production basis remains unverified. Resolve relationships and perform real production or reconciliation before stronger claims. A failed copy leaves an `MIGRATION-INCOMPLETE.txt` marker; keep using the original. Never treat migration itself as a fresh review.