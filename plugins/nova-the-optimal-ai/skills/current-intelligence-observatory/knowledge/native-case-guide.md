# Native case operations

Work from the skill folder: `codex/current-intelligence-observatory` in the customer ZIP, or `source/current-intelligence-observatory` in the repository. Python3.10+ is required for these helpers. The browser Atlas needs no Python.

## First durable case

Ask the assistant to retain a case from your actual question and supplied sources. It uses [the template](../assets/observatory-case.template.json), infers ordinary framing, and marks unavailable evidence. You do not need to fill every optional collection. Keep a copy of source artifacts beside the case, with relative paths. An inaccessible source can be recorded with `preservation_status: unavailable` and a specific `failure`; never invent its hash or contents.

The checks below use the wholly fictional worked case. Run output commands into **new** destinations outside the distributed examples:

```text
python scripts/observatory_guardrail.py validate-case examples/harbor-lantern/case-update.json --files
python scripts/observatory_guardrail.py project examples/harbor-lantern/case-update.json ./my-projections
python scripts/observatory_guardrail.py delta examples/harbor-lantern/case-baseline.json examples/harbor-lantern/case-update.json ./my-delta.json
```

Existing destinations are refused. Choose a new revision name; do not delete original evidence to satisfy a command. `validate-case` without `--files` checks declared structure only. With `--files`, preserved captures, hashed artifacts and declared review evidence are read under the case directory and compared with their hashes. UTF-8 support excerpts are checked for exact occurrence, not semantic entailment.

## Capture and support

```text
python scripts/observatory_guardrail.py capture-receipt ./case/captures/notice.txt --source-id SRC-NOTICE --capture-id CAP-NOTICE --url https://example.test/notice --retrieved-at 2026-10-07T10:00:00Z --case-root ./case --output ./case/notice-receipt.json
```

This hashes existing bytes. It does not retrieve the URL or certify the source. `artifact_path` is relative to `--case-root`; without that flag it is relative to the capture's parent. Add the receipt to the native case only after matching its source and scope.

A claim can retain `support` entries with `capture_id`, `relation` (`supports`, `refutes`, `context`, `reports`), `locator`, `excerpt` and `rationale`. Link the claim to its capture or observation through typed `_ids` or heterogeneous `provenance_ids`. A quote's presence is not enough: read its qualifications and explain why it supports the exact claim, strength, date and population.

## Time and comparisons

Known instants use `YYYY-MM-DDTHH:MM:SSZ` or an explicit numeric offset, with optional fractional seconds. Invalid offset components and `-00:00` are rejected because the latter does not establish known UTC. Preserve unknown source clocks as `event_time_text` and `event_timezone`, leaving event instants absent. The helper does not implement every possible ISO8601 representation or leap-second notation.

`evidence_as_of` is an optional known instant. Recorded retrieval/observation/first-seen/last-seen times cannot exceed it. Future scheduled event times may. Two case revisions share `inquiry_id`; otherwise native delta requires the same `case_id`. Delta v2 separates changed fields, currentness changes, new representation, disappearance and explicit status transitions. It does not infer importance or make a deleted record false. Old v1 delta files remain historical outputs.

## Review bindings

Do the actual review before recording a pass. `review-subject CASE.json` only prints a digest; it performs no review. The subject is canonical sorted JSON of every root field **except** `checks`, `phase`, `posture` and `history`. It includes claims, support, source/capture hashes, scope, question, watch, artifacts and next action. Changing any substantive field changes the digest. Moving a genuinely reviewed case between administrative postures does not.

A ready check names `check_type`, `status: passed`, exact `subject_sha256`, `reviewer`, `method`, `rationale`, `reviewed_at` and nonempty `evidence_files` containing relative `path` and `sha256`. Its declared review cannot predate source retrieval. Any unresolved/nonpassing check of a required type blocks readiness; resolve it explicitly rather than hiding it behind another pass. Historical review belongs in retained prior revisions/history, not a fabricated replacement.

For `watch-ready`, the watch names its baseline, owner, cadence, nonempty triggers, meaningful `change_threshold` and `resume_action`; `watch-specification` and `baseline-integrity` reviews cover that subject. This does not activate a scheduler.

For `publication-ready`, `publication_artifact_id` selects an artifact of type `publication-package` with a relative path and SHA256. All four required checks—provenance, citation-integrity, redaction and editorial-challenge—also name that `artifact_id`. Keep the review evidence separate from the case to avoid a self-hashing receipt. Run:

```text
python scripts/observatory_guardrail.py audit-publication ./case/case-reviewed.json
```

That command verifies local files and requires publication-ready posture. A successful result establishes the declared binding and local byte integrity only. It cannot authenticate the reviewer, infer semantic truth or grant external publication authority. The supplied Harbor Lantern update deliberately fails publication audit because editorial approval remains pending.

## Return and recovery

Keep the previous case and original captures. Reopen the exact case JSON, inspect `next_action`, and check changed source/deliverable bytes before relying on an old ready label. If you lack scripts, disclose unverified mechanical checks and use [the copy-paste route](../fallbacks/universal-copy-paste-workflow.md). If import or validation fails, fix the named field in a new revision; do not relabel an incomplete investigation ready.
