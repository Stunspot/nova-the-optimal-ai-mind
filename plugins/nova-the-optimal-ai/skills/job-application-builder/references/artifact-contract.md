# Current private packet and native commands

Version 0.2 supports `job-application-packet/v2`. The normal case contains `case.json`, `source-register.csv`, `evidence-claim-matrix.csv`, selected applicant documents, and retained sources. Additional private notes are allowed. Only the selected root files `resume.md|txt`, `cover-letter.md|txt`, `application-answers.md|txt` and `work-sample-guidance.md|txt` can be exported. The native tools do not create Word/PDF. Legacy nine-file packets remain read-only checkable as `legacy_unreviewed`; see the customer migration guide before adopting current review records.

From this skill directory, start a new private case:

```text
python scripts/new_packet.py --output /path/to/new-case --case-id coordinator-1 --candidate-id candidate --employer "Employer name" --role "Coordinator" --artifact resume
python scripts/check_packet.py /path/to/new-case --json
```

Use a real writable path; on Windows a quoted `..\my-private-application` relative path is suitable. Creation refuses existing destinations. An initial draft intentionally has unknown instructions and no invented evidence. Add only requested artifacts with repeated `--artifact` options, or edit the case when requirements change.

## Case fields

`case_id` and `candidate_id` are stable private references; `revision` is a positive integer. `purpose` is `real` or `practice`. A practice case never becomes a real handoff. `vacancy` retains employer/title, source IDs, `coverage` (`complete`, `partial`, `unknown`) and a deadline record. `deadline.status` is `known`, `unknown` or `not-stated`; preserve `wording`. A known `instant` needs an actual date, seconds and `Z` or a numeric offset such as `2026-10-07T17:00:00-05:00`. Do not infer that instant from an ambiguous date or a daylight-saving transition. Unknown/not-stated uses JSON `null`. `--as-of` supplies the same timestamp profile for reproducible checking; otherwise the current clock is used.

Each `artifacts` entry selects an `id` and its matching root `path`, `allowed` (`true`, `false`, `null`), `required_format` (`markdown`, `text`, `pdf`, `docx`, `unknown`), and optional integer `max_words`/`max_characters` or `null`. A forbidden/unknown artifact is a draft decision to resolve, not a silently exported final letter. Non-native requested formats remain a separate conversion task and prevent native handoff readiness.

Each `questions` entry preserves `id`, original `text`, registered vacancy `source_id`, exact `answer`, limits or `null`, `requires_user_confirmation` and `confirmation_source` or `null`. Use empty answer text for unknown input. The exact answer must occur in the selected answers file. Limits count non-whitespace runs as words and Unicode code points as characters; include spaces/punctuation for character counts. These conventions are not a promise that a portal counts identically. A sensitive/attestation answer needs a current user-statement source for this candidate.

`checks` name the material eligibility, instruction and privacy conditions. Each has unique `id`, `kind`, original `requirement`, `state` (`met`, `unmet`, `unknown`, `not-applicable`), Boolean `blocking`, `basis` for met/not-applicable, and `next_action` for unresolved/unmet. A preferred gap can be non-blocking; do not relabel a required exclusion as optional merely to clear the checker. Completeness is a declared semantic judgment, not inferred by the parser.

`submission.state` is `not-submitted`, `outcome-unknown` or `observed-submitted`. The last needs `authority_reference`, `receipt_reference` and aware `observed_at`. Those are accountable declarations, not authenticated proof. An unknown outcome requires checking the prior attempt before retrying; the scripts do not submit anything.

## Source and claim records

The CSV header templates are in assets/source-register.csv and assets/evidence-claim-matrix-v2.csv. Use a CSV-aware editor: quoted commas and multiline notes are supported; duplicate headers and wrong row widths are rejected. Inputs are UTF-8 (an initial BOM is accepted), each text file at most 2 MiB. JSON rejects duplicate decoded keys, NaN/Infinity and overflowing non-finite floats. Linked/reparse roots or files are not accepted. Originals are never edited by checking.

Sources keep stable `SRC-*`, type/title, locator, source/retrieval dates, custody, use, notes, origin, subject, state and optional hash. `origin`: `user-record`, `user-statement`, `employer`, `third-party`, `fictional`, `unknown`. `use`: `vacancy`, `candidate-evidence`, `context`, `sample`. `state`: `current`, `conflicted`, `unverified`. Candidate evidence `subject` must equal the case candidate ID. A `file:sources/history.md` locator reads only a contained regular file and requires its lowercase SHA-256. Other locators are retained references; the checker does not fetch or authenticate them. Do not write sensitive source contents into a URL field.

Matrix fields preserve criterion identity/text/type/importance, EVD ID, source IDs separated by semicolons, strength (`direct`, `adjacent`, `self-report`, `none`), exact proposed claim, support, selected destinations, confirmation and risk note. Supported states are `documented`, `user-confirmed`, `reasonable-paraphrase`; these require candidate evidence, nonempty exact fragment/destinations and resolved confirmation. A user-confirmed claim needs a user-statement source. `confirmation-needed`/`unsupported` keeps no final destination and requires a useful gap/next-action note. Required/administrative gaps keep the packet draft; preferred/context gaps are visible warnings. Exact-fragment matching cannot detect all paraphrased unsupported prose: review semantically.

## Review, correction and export

`ok:true` means records are internally checkable, not that the application is complete. `draft` lists unresolved work. `ready-for-review` has no declared mechanical/material blockers. After actual semantic/privacy review, record who did it and why:

```text
python scripts/check_packet.py /path/to/case --record-review --actor agent --reviewer "Reviewer identity" --basis "Compared all selected prose with retained sources and posting; checked privacy and unresolved constraints" --json
```

Use `--actor user` only for an actual user review, never to manufacture approval. Timestamped files in `reviews/` bind the content snapshot; their declarations are not authenticated signatures. A changed source, case field or selected draft invalidates a previous snapshot review. Preserve originals, increment revision and reconcile the correction before recording a new review. Old reviews remain. No approval is required solely to save a draft.

```text
python scripts/check_packet.py /path/to/case --export /path/to/new-handoff --json
```

Normal export needs a real, currently reviewed packet with no material blockers and not-submitted state. `--draft` explicitly creates a labeled working copy, including practice output, without claiming readiness. Export copies only selected text files and EXPORT-README.json into a new folder outside the case; existing destinations are refused. Keep the entire private case separately for recovery. File integrity and exact fragments do not prove truth, full coverage, legal eligibility, document rendering, ATS behavior or hiring results.
