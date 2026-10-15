# Native campaign records

Campaign room and agent share ordinary files, not parallel evidence stores. [The room guide](CAMPAIGN-ROOM.md) explains actions; [the review contract](../references/review-contract.md) defines exact current-review identity.

| File | Purpose |
|---|---|
| campaign.json | Verbatim inquiry, title, phase/status, budgets, counters, routes, blockers and return point |
| research-brief.md | Audience, scope, decision, evidence burden and cutoff meaning |
| source-ledger.jsonl | Stable S001-style IDs, title, locator, recorded states and provenance |
| claim-ledger.jsonl | C001-style assertion, source_ids and bounded interpretation |
| query-ledger.jsonl | Unique ID, query, result_ids and actual retrieval context |
| notes/S001.md | What the source establishes, location, reading scope and limits |
| coverage-matrix.md / contradictions.md | Covered and missing questions; rival accounts |
| draft/*.md / report.md | Ordered authored sections and present answer |
| citation-audit.md | Substantive audit observations |
| citation-audit-structural.json | Deterministic current integrity result |
| semantic-review.json | Actual reviewer, claim treatment and content-bound subject |
| campaign-summary.md | Achieved outcome, limitations, counts and next event |

JSONL means one JSON object per nonblank line. Duplicate JSON keys are errors. Source IDs use S plus at least three digits; claims use C plus at least three digits. Titles and locators must be real text, not numbers masquerading as entries. Dates use YYYY-MM-DD or a full timestamp with valid timezone offset; unknown publication dates may be `unknown` or `undated`. Optional campaign `evidence_cutoff` is the knowledge cutoff for publication dates, not the retrieval or review date. Explain a different historical/currentness boundary in the brief rather than silently changing its meaning.

Source events accumulate: discovered → inspected → opened → deeply-read → cited. Opened means readable content was accessed. A note records the actual reading scope; its length cannot prove reading. Excluded, duplicate and inaccessible require a disposition reason. A later exclusion preserves previous reading events. A duplicate uses `duplicate_of` pointing to the canonical retained record. Excluded/duplicate/inaccessible records cannot remain cited.

A source example: `{"id":"S001","title":"Accountable source","url":"https://example.org/source","states":["discovered"],"disposition":"Candidate awaiting reading"}`. A provisional claim may have empty source_ids; that is not a supported conclusion. [The complete example](../examples/sea-level-comparison/report.md) shows real interpretation and a source excluded after reading.

Room saves synchronize counters from retained records. Direct agent edits must synchronize them too. Counts overlap by event; they are not mutually exclusive categories or a completion percentage.

## Completion and return

Valid sparse active work needs its inquiry, typed records and return point, not a quota of words. Complete requires phase and status both complete; actual brief, coverage, contradiction, summary and report content; freshly recomputed citation integrity; and a matching declared semantic review covering every claim's treatment. Unused candidates can be not-used. Qualified claims must be visibly limited in the report. Unresolved review prevents completion. A no-source result can complete a narrow inquiry only with honestly reviewed search/absence limits; it cannot prove absence in the world.

Legacy unbound judgments remain readable. Preserve an older completed copy, move the working copy to review/active and perform the affected review. The validator never manufactures new authorship or approval. [Troubleshooting](TROUBLESHOOTING.md) explains rejected saves and re-entry.
