# Application packet contract

The packet is complete only when these artifacts agree.

| Artifact | Required contents |
| --- | --- |
| role-match-brief.md | Vacancy identity, deadline, constraints, selection thesis, required and preferred criteria, strongest evidence, material gaps |
| resume.md | Vacancy-matched truthful resume with conventional headings and consistent chronology |
| cover-letter.md | Specific evidence-backed letter within any stated limit |
| application-answers.md | Every supplied question, limit, answer, evidence IDs, and unresolved or attestation flags |
| evidence-claim-matrix.csv | Criterion-to-evidence-to-claim ledger with stable IDs and support status |
| work-sample-guidance.md | Existing and proposed samples, proof purpose, confidentiality and disclosure boundaries |
| unresolved-claims.md | Missing facts, contradictions, user decisions, and claims excluded from final prose |
| submission-checklist.md | Formats, names, links, limits, attestations, deadline, user review, and external submission status |
| source-register.md | Supplied and retrieved sources with identity, date, custody, and use |

## Completion rules

- Every substantive claim maps through `criterion -> EVD-* -> SRC-* -> proposed claim -> destination` or is ordinary non-factual connective prose.
- A reused evidence ID retains the same source-register IDs and evidence strength across criteria.
- Confirmation-needed claims are absent from final prose until confirmation is recorded.
- Every unsupported matrix row is absent from final prose.
- Every confirmation-needed row appears in unresolved-claims.md.
- Dates, titles, employers, credentials, metrics, and tool claims do not conflict.
- Vacancy instructions and word or file limits are represented in the checklist.
- Submission and legal attestations remain incomplete until performed by the user or through an explicitly authorized tool.

## Degraded completion

When the posting, work history, or application questions are incomplete, produce the useful subset and mark the packet NOT READY TO SUBMIT. List exactly what unlocks completion. Never fill missing facts with plausible defaults.

## Checker boundary

The checker validates file presence, matrix headers and statuses, stable IDs, unresolved confirmation rows, and checklist state. It does not validate truth, writing quality, legal compliance, or employer behavior.
