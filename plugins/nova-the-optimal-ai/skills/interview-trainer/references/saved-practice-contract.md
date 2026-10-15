# Saved practice format and native limits

[Artifact map](artifact-contract.md) · [Skill entry](../SKILL.md)

This format is for a maintained packet, not a prerequisite for a conversation. The trainer can organize the files for the user. The checker is read-only and uses only Python's standard library. It does not fetch sources, write practice records, make approvals or infer meaning from an ID match.

## Files and inspectable sources

The CSV headers in [assets](../assets/) are the reference templates. `source-register.csv` names sources, dates, custody and use; `source-evidence.csv` points to one retained UTF-8 copy per source ID with SHA-256, locator and exact excerpt. Use a labelled excerpt or dated self-report when a whole original cannot be retained, rather than claiming the full original was seen. `evidence-support.csv` names the exact evidence item, source, passage, basis (`source-excerpt` or `user-confirmation`) and why it supports that specific claim. A confirmed evidence item needs this inspectable support. Self-report is not independent authentication.

`criteria.csv` binds each `CRIT-001` style criterion to stated source IDs and priority. A hypothetical sparse role source is allowed when labelled. `question-map.csv` joins questions to criteria and evidence; probability labels are `confirmed-topic`, `confirmed-question`, `strongly-indicated`, `plausible` or `speculative`. Confirmed labels also need `confirmation_source_ids`; exact wording must occur in the retained instruction for `confirmed-question`.

Each supplied answer uses a unique `## Q-001` section and fields `Evidence IDs`, `Support state` and `Compact answer prompt`. Evidence IDs match its map row. States are `supported`, `confirmation-needed`, `honest-gap` or `proposed-method`. The last is a future approach, not past experience. Every supplied answer is checked, including lower-priority questions. Native checks do not establish that the cited passage semantically entails the claim.

## Preserve actual attempts

Copy [practice-record.template.json](../assets/practice-record.template.json) to `practice-record.json` only for the current working packet. Replace the identity and as-of timestamp; its empty attempts describe preparation, not practice. Timestamps use seconds and a known UTC offset, such as `2026-10-07T14:05:00-05:00`. Unknown `-00:00`, impossible calendar/offset components and future evidence beyond the packet cutoff fail. Source dates may be calendar dates or explicitly `unknown`.

An attempt has `attempt_id` (`ATT-001`), `question_id`, actual `question_asked`, original `response`, `origin`, `mode`, `medium`, `assistance`, `recorded_at`, `scope_sha256` and an `assessment`. Origins are `user-verbatim`, `user-confirmed-summary`, `assistant-demonstration` or `fictional`. Modes are `coached`, `realistic`, `rapid-drill`; media are `text`, `audio`, `video`, `in-person`; assistance is `none`, `cue-given` or `model-answer-shown`. These are declared records, not authenticated observations.

Assessment contains the precise `target`, an `observation` quoted from the response, `result` (`needs-drill` or `workable`) and a substantive `rationale`. A quote demonstrates where feedback came from, not whether its interpretation is correct. The actual reviewer must compare the question, response and intended performance.

The session state is `not-started`, `in-progress` or `ended`. Ended means the session stopped. Current question practice states are `planned`, `practiced`, `needs-drill`, `deferred` or `demonstrated`; the last labels illustrative material. Only the two user-origin kinds can support observed practice coverage.

## Scope and changed work

Use `python scripts/check_interview_packet.py <packet> --subject` to read current `scope_sha256` and `review_subject_sha256`. This command does not approve or create anything.

The scope hashes the interview ID, role brief, answer cues, criterion/evidence/source tables and retained source-copy bytes, plus all question fields except `practice_status`. It excludes the readable mock, critique, final brief and candidate questions so recording feedback does not itself erase an attempt's context. Assign the actual current scope when the attempt occurs. Do not renew historical attempt hashes to make old practice look current.

Changed preparation scope keeps prior attempts historical. Completed historical drills remain retained but contribute no current coverage. Set current question/coverage states honestly and practice the affected behavior when needed. A new label with the same question ID is not the same task.

## A drill must test the diagnosed behavior

Each drill has `drill_id`, `target`, `before_attempt`, `after_attempt` when performed, `intervention`, `success_cue`, `state` and a concrete `comparison`. States are `open`, `coached-improvement` or `transfer-demonstrated`. The original attempt must show `needs-drill` on that target; a completed rerun must assess that exact target on the same question/scope, later in time, with `workable` result. Equality of a target string is only a consistency check: review whether both tasks actually require that behavior.

Transfer additionally requires a different, uncued question variant and user-origin responses. Repeating an identical question or showing a model answer cannot establish this bounded transfer. Any recorded current material gap without a matching completed drill, including a later failed response, prevents a transfer claim for that question. Historical completion is retained without being relabelled current.

## Bounded summary and actual review

Readiness contains `claim`, `question_ids`, `remaining_gaps` and `next_action`. Claims are `preparation-only`, `observed-practice`, `bounded-transfer` or `fictional-demonstration`. Coverage must agree with current attempts/drills and origin. None means general employability, mastery of every criterion or likely hiring.

For a full current packet check, a person or model must actually inspect source-to-claim meaning, response provenance, target-to-drill alignment, confidential details, contradictions and the final brief. Retain that report, identify its author honestly, and only then fill [packet-review.template.json](../assets/packet-review.template.json) as `packet-review.json`. Its fields are `format: interview-packet-review/v1`, `scope: interview-preparation`, `result: consistent-with-stated-limits`, `reviewer`, `reviewed_at`, `subject_sha256`, `report_path`, `report_sha256`. A pending or failed review cannot qualify.

The review subject hashes all six readable packet documents, all required current CSV tables, their referenced source-copy bytes and `practice-record.json`. The review record/report are excluded to avoid a circular hash; the report's exact hash is checked separately. Source or prose changes stale the subject, including final-summary changes. The report's reviewed time must follow included current attempts and be within the packet's cutoff. A checksum binds an actual review; it cannot substitute for one or authenticate its author.

`python scripts/check_interview_packet.py <packet> --json` returns `CONSISTENT_REVIEWED_PACKET`, `DRAFT` or `BLOCKED` and scope-limited coverage. `--draft` permits incomplete/legacy work without qualification. Legacy CSV-formatted `source-register.md` and plain criteria can be retained while migrating; never delete raw responses or invent their provenance to satisfy the new format. Malformed input errors name the affected boundary and preserve the files.