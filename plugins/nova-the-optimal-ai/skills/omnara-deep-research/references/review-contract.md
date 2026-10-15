# Review the actual inquiry, evidence and report

The existing campaign v1 files remain native. `semantic-review.json` records an actual reviewer judgment about the current content. It is optional while work is active and required for `phase: complete` / `status: complete`. Older `support`, `semantic_audit`, `evidence_status` and `disposition` fields remain historical source data. They are never silently upgraded into current review.

Run `python scripts/research_campaign.py review-subject <campaign-folder>` after the report, notes, ledgers, scope and audit prose are stable. The command only prints a SHA-256 subject and its file inventory. It makes no changes and issues no verdict. The reviewer must inspect the material before recording that digest.

The subject includes all campaign fields except administrative phase, status, counters, created_at, updated_at, resume_point and last_verified_artifact; every root native Markdown file; all immediate notes/draft Markdown; and source, claim and query ledgers. It excludes only the subject's containing semantic-review.json and deterministic citation-audit-structural.json. Unknown substantive campaign fields are included. External URLs, collected originals and unrelated nested corpora remain outside this native text boundary: disclose their custody, exact accessed version or capture location in a source note when material. A hash of a note does not authenticate its external source.

A review record has this shape. Values below are instructions, not a passing receipt:

```json
{
  "format": "omnara-semantic-review/v1",
  "subject_sha256": "copy the current digest only after actual review",
  "reviewer": "actual reviewer identity and in-process/independent role",
  "reviewed_at": "YYYY-MM-DD or zoned timestamp",
  "result": "needs-work",
  "rationale": "Explain scope, full report review, limitations and any material unresolved issue.",
  "claims": [
    {"claim_id": "C001", "treatment": "unresolved", "rationale": "Explain the exact evidence-to-claim inference and report wording."}
  ]
}
```

Use `supported`, `qualified`, `not-used` or `unresolved` for each recorded claim. Qualified means the report visibly narrows the statement to what the evidence earns; explain where. Not-used means the candidate claim does not support the final conclusion. Unresolved prevents a pass. Record every claim once, including rejected candidates, so convenient omissions cannot disappear. `result: pass` means the declared reviewer found the full report acceptable within the stated research boundary, not that software proved truth or that the owner approved publication.

Assemble before auditing. Run `python scripts/citation_audit.py <campaign-folder>` and then the campaign validator. The structural gate recomputes visible citation mechanics and source/claim links; it does not accept a hand-edited pass declaration. The semantic gate checks types, claim coverage, chronology and exact subject identity, never entailment or reviewer authenticity. A reviewer can lie; a hash cannot prevent that.

To resume an older completed campaign, preserve its old receipt, set phase to review and status to active, inspect current evidence, and perform the affected substantive review. Do not bulk reseal old work. Admin-only transitions from reviewed to complete do not stale the subject. Changed notes, scope, source records, draft sections, report or audit prose do.
