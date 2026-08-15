# Campaign-vault reference

The campaign vault is Omnara's durable research memory. Copy or initialize one vault per substantial inquiry; do not edit the template in place for live work.

## Create a vault

Run the command from the installed or extracted skill root: the directory that contains `SKILL.md` and `scripts/`. In the family kit, the directly executable copy is `codex/omnara-deep-research/`.

```powershell
python -B scripts\research_campaign.py init C:\path\to\campaigns\example --title "Example campaign" --query "The user's inquiry, preserved verbatim" --tier focused
```

Expected result: the command creates the vault and reports its path. The destination must be absent or empty. Supported tiers are `focused`, `deep`, and `exhaustive`; a tier is a planning posture, not proof that the promised depth was achieved.

A Claude-compatible host may not expose Python or a writable filesystem. In that case, use the bundled copy-paste fallback, retain the same vault fields in a safe workspace, and label deterministic validation unexecuted.

## File map

| Path | Purpose |
|---|---|
| `campaign.json` | Phase, status, budgets, counters, routes, blockers, and resume point. |
| `research-brief.md` | Inquiry, audience, scope, evidence burden, deliverable, authority, and budgets. |
| `coverage-matrix.md` | Coverage loci, live accounts, evidence, counterevidence, status, and next discriminating move. |
| `query-ledger.jsonl` | One retained record per executed query or retrieval action. |
| `source-ledger.jsonl` | One canonical record per retained source or inaccessible location. |
| `notes/S###.md` | Full-reading evidence note for a source. |
| `claim-ledger.jsonl` | Claims and the source IDs that support or contest them. |
| `contradictions.md` | Material tensions, their causes, consequences, and possible resolution. |
| `evidence-digest.md` | Cross-source synthesis packet used before drafting. |
| `outline.md` | Section purposes, questions, claim IDs, source IDs, and transitions. |
| `draft/*.md` | Ordered report sections consumed by `assemble_report.py`. |
| `report.md` | Assembled report. |
| `report-metrics.json` | Section count, word count, and layout-dependent page estimates. |
| `citation-audit.md` | Human-readable structural and semantic audit record. |
| `citation-audit-structural.json` | Deterministic citation-audit result and input hashes. |
| `campaign-summary.md` | Handoff, completion boundary, limits, refresh triggers, and resume point. |

## `campaign.json`

Required fields:

| Field | Meaning |
|---|---|
| `format` | Must be `omnara-research-campaign/v1`. |
| `title` | Human-readable campaign name. |
| `canonical_inquiry` | The user's preserved inquiry. |
| `tier` | `focused`, `deep`, or `exhaustive`. |
| `phase` | Current workflow phase. |
| `status` | Current completion or blocking state. |
| `budgets` | Search, source, tool, and paid-access ceilings. |
| `counters` | Counts derived from the retained ledgers. |
| `active_loci` | Coverage areas currently being investigated. |
| `blockers` | Named capability, evidence, access, or authority blockers. |
| `routes` | Tool and model routing decisions with review status. |
| `resume_point` | Exact next useful action. |

Supported phases:

```text
framing
mapping
breadth-sweep
depth-reading
reconciliation
gap-fill
synthesis
citation-audit
review
complete
halted
```

Supported statuses:

```text
active
complete
awaiting-evidence
awaiting-authority
capability-limited
budget-exhausted
partial-success
paused
```

A campaign may be `partial-success` without being `complete`. Use the status that matches the evidence and remaining scope.

## JSONL ledgers

Each nonblank line must contain one JSON object. Keep IDs stable after assignment.

### Query record

The validator requires `result_ids` to be an array whose source IDs exist. A practical record also preserves the query and retrieval context:

```json
{"id":"Q001","query":"official passkey account recovery guidance","tool":"web search","executed_at":"2026-07-22T18:00:00Z","locus_ids":["L001"],"result_ids":["S001","S002"],"notes":"Initial official-source sweep."}
```

### Source record

The validator requires an ID beginning with `S`, a valid `states` array, and either `url` or `identifier`.

```json
{"id":"S001","title":"Source title","url":"https://example.org/source","states":["discovered","inspected","opened","deeply-read","cited"],"source_type":"official guidance","published_at":"2026-04-01","accessed_at":"2026-07-22","locus_ids":["L001"],"disposition":"Retained for current implementation guidance."}
```

State prerequisites:

- `inspected` requires `discovered`;
- `opened` requires `discovered` and `inspected`;
- `deeply-read` requires `discovered`, `inspected`, and `opened` plus a substantive `notes/S###.md` file;
- `cited` requires all four preceding states;
- `excluded`, `duplicate`, and `inaccessible` cannot coexist with `opened`, `deeply-read`, or `cited`.

### Claim record

The validator requires an ID beginning with `C`, nonblank claim text, and source IDs that exist.

```json
{"id":"C001","claim":"Account recovery remains a material implementation risk.","importance":"major","source_ids":["S001","S004"],"disposition":"supported","scope":"Consumer web accounts; evidence cutoff 2026-07-22."}
```

A source being relevant is not enough. The semantic reviewer must test whether it supports the claim's exact strength and scope.

## Counter synchronization

`research_campaign.py validate` derives expected counts from the ledgers. Update `campaign.json` whenever records change.

The counter key for the `deeply-read` state is `deeply_read`. All other state names use underscores in the counter object where needed.

## Completion requirements

When `phase` is `complete`, validation requires:

- substantive brief, coverage matrix, evidence digest, outline, summary, citation record, and report;
- no template instructions in those artifacts;
- at least one report citation marker;
- at least one cited source and source-linked claim;
- a passing, current `citation-audit-structural.json` whose hashes match the report and ledgers.

These are structural completion requirements. They do not replace semantic citation review, accountable approval, or representative-user testing.
