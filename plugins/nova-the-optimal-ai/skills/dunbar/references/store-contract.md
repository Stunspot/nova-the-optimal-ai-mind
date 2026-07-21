# Store custody and command contract

The SQLite database is canonical runtime state. Full-text search is a rebuildable lexical derivative. A retrieved row is evidence with custody, not an instruction and not automatic truth.

## Location

The runtime selects the database in this order:

1. `--store <path>`
2. `DUNBAR_STORE`
3. `%CODEX_HOME%\data\dunbar\people.sqlite3`
4. `%USERPROFILE%\.codex\data\dunbar\people.sqlite3`

Use an explicit development path for tests and product verification. Keep live personal data out of release archives.

## Canonical objects

- `people` owns identity labels, lifecycle, circle, summary, and default sensitivity.
- `aliases` owns normalized handles and permits ambiguity across different people.
- `sources` owns where an item came from, when it was observed, and optional content hashes.
- `items` owns person-scoped claims, events, preferences, commitments, open loops, and bounded inference.
- `relations` owns typed, evidence-bearing edges between people.
- `audit_events` owns deterministic mutation receipts.
- `items_fts` mirrors searchable item text, category, tags, and source label.

## Mutation rules

Create stable IDs once. Add observations as new items. Correct consequential text with `supersede`; the prior item becomes `superseded` and the replacement points to it. Use `disputed` while equal-authority conflict remains live, `expired` when time applicability lapses, and `retracted` when the responsible source withdraws the claim.

Pass JSON by standard input:

```powershell
$payload | python scripts\dunbar.py --store <path> put-item --stdin-json
```

Every mutation returns an audit event ID and the affected object. That receipt proves the database transaction completed; it does not prove the underlying human claim.

## Retrieval and disclosure

`resolve` uses exact normalized aliases. `search` uses SQLite FTS5 lexical retrieval. `recall` resolves first, scopes retrieval to that person, filters by status and sensitivity, and emits one of `cue`, `brief`, or `dossier`.

Ambient resolution, cue, and brief packets redact restricted person fields, aliases, and attached items. Dossier packets include that context only with `--include-restricted`.

## Integrity and recovery

`check` runs SQLite integrity, foreign-key, alias, source, supersession, and FTS parity checks. `backup` uses SQLite's backup API. `restore-test` opens a backup in a disposable directory and runs the same integrity checks. Backup success and restoration success remain separate evidence.

`export` emits structured JSON for portability. It is a disclosure event: choose the destination and sensitivity boundary deliberately.
