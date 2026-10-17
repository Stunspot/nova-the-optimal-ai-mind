# Native ledger operations

Use Python 3.10+ from the complete skill folder. The commands in this reference operate only on supplied local files. JSON input is bounded to 2 MB, UTF-8 with at most one leading BOM, no duplicate keys or nonfinite numbers, and at most 64 nested levels. Decimal literals retain precision. Every file-producing operation refuses an existing output and linked paths, including ancestor junctions. Choose a new filename in an existing ordinary directory. The initializer alone can create its destination directory.

## Start and resume

`python -B scripts/answerlayer.py init CASE --title "Decision title" --owner "Owner"` creates `CASE/reality-ledger.json` with a unique ID and real creation time. The answer cutoff is explicitly unknown. Fill the initial draft with actual wording, scope, decision use, owner and cutoff before treating it as an established checkpoint. Keep unknown values honest.

`python -B scripts/answerlayer.py validate FILE [--previous PRIOR]` checks structure, calendar/time values, references, evidence identities and supplied history. v1 is readable but cannot supply current bound approval. v2 is `answerlayer/reality-ledger/v2`, product 0.3.0. Unknown extension fields survive; known fields must match the declared schema. The standard-library checker implements this product's fixed schema vocabulary plus semantic checks; it is not a general JSON Schema engine.

When a real checkpoint changes, raise `revision`. A changed baseline text, cutoff or context requires the next baseline version and the exact old baseline appended to `baseline_history`. Keep the original file. With `--previous`, prior IDs, source contents, decided patch contents and approval/history prefixes are protected. Without it, the checker cannot detect omitted undisclosed history.

## Record a traceable proposal

A source records its title/locator, publication date, authority, access status/time, optional originating source ID and precise claim-location-relation-scope support. A source is evidence supplied to the checker, not evidence fetched by it. Retain source content under its ID; corrections get a new ID. Retirement is a status change.

A patch supplies `before`, `after`, mechanism, counterfactual, scope, recheck, source IDs, source hashes, candidate IDs, starting baseline version/hash and resulting answer cutoff. The starting span must match once for adoption. The source hashes bind each referenced source's full content except status. A new source or changed patch requires a new decision; status labels do not grant it.

Use `python -B scripts/answerlayer.py approval-basis FILE PATCH_ID` to get the exact patch and baseline hashes. Record only real authorization in an appended approval object: `id`, `object_id`, action `approve` or `withdraw`, actor, time, scope, authorization_basis, base_sha256, patch_sha256 and nullable expires_at. `patch-adoption` covers a local patch application and local brief; `local-brief` covers only preparation. Existing user authority may supply the basis. The tool authenticates neither the actor nor consent. The latest appended decision for a patch governs; withdrawal, expiry or changed binding blocks it. Prior decisions cannot be reordered when comparing checkpoints.

`python -B scripts/answerlayer.py adopt FILE PATCH_ID NEW.json` writes one exact local application to a new checkpoint. It requires current dated baseline/result cutoffs, eligible supplied source support, current binding and adoption scope. It retains the prior answer and records the adopted patch ID. No other canonical file or external system changes.

`python -B scripts/answerlayer.py brief FILE NEW.md [--patch PATCH_ID]` prepares a local brief. Without `--patch`, it includes eligible patches and reports excluded IDs with reasons; an explicitly requested ineligible patch refuses the entire output. Local preparation is not publication. Publication fields record assertions only; this toolkit has no send/publish command.

## Other bounded helpers

| Goal | Command after `python -B scripts/answerlayer.py` | Meaning |
| --- | --- | --- |
| Candidate fields | `qualify CANDIDATE.json` | Typed field checks; no factual proof |
| Text difference | `compare BEFORE.txt AFTER.txt` | Exact supplied text comparison |
| Source inventory | `citations FILE NEW.json` | Source/support records plus input hash |
| Overlap review | `conflicts FILE` | Shared conflict keys are overlap; retained fuzz is shown separately |
| Review date | `recheck 2026-09-01 30` | Chosen interval in days, not measured decay |
| Threshold | `watch 12 gte 10` | Decimal comparison of supplied observations |
| Missing observation | `watch unknown gte 10` | Unknown result and null triggered state |
| Legacy migration | `migrate OLD.json NEW.json` | Preserving v1-to-v2 copy; no invented history/approval |
| Package basics | `self-check` | Required files and blank template only |

The old helper filenames remain compatibility entrypoints for these operations. Results are JSON: exit0 indicates the requested check/operation completed, exit1 indicates a negative validation/qualification result, and exit2 indicates refusal or a command/input error. Read the result and its boundary; success does not imply factual truth, authenticated consent, field effectiveness or external delivery.

## Date and time profile

Calendar dates use YYYY-MM-DD; explicitly allowed unknown/not_applicable values are retained where the schema permits. Decision/access timestamps accept date-only at UTC midnight, or YYYY-MM-DDTHH:MM:SS with optional 1–6 fractional digits and Z or a known ±HH:MM offset. Offset hours must be 00–23 and minutes 00–59; -00:00, leap seconds, impossible calendar dates and values outside the representable UTC range are refused. Approval ordering follows the appended array; dates may tie, and later entries resolve a tie. Record a full timestamp where within-day timing matters. A chosen review interval is 1–365000 integer days and must stay within the calendar range.

## Recovery and snapshots

`python -B scripts/answerlayer.py snapshot CASE NEW.zip` captures the entire ordinary source tree, including any snapshots directory and empty directories, with a manifest and per-file hashes. Output must be outside that tree and absent. Bounds are 4096 entries, 64 MiB per file, 256 MiB total and 180 characters per relative path. Linked/reparse/special files, Windows-reserved names, nonportable characters and case/Unicode-normalization collisions are refused. A staged ZIP is read back before exclusive publication; changed source content before publication refuses the operation. Quiesce live writers first: this is not a database-consistent backup.

Failed writes remove the operation's own staging file and leave prior inputs/outputs intact. Exclusive publication requires filesystem hard-link support; unsupported or denied operations fail rather than overwrite. If cleanup itself fails, retain the `.answerlayer-*` staging file as incomplete evidence and retry with a new output only after inspecting the error. Restore a snapshot to a new ordinary empty directory, verify its manifest against the extracted files and validate the selected ledger; never extract over live state. The source remains your recovery copy.
