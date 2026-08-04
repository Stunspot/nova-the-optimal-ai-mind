# Create, validate, and resume a case file

Use a Beryl case file when diagnosis spans several turns, people, tools, or consequential changes. The JSON file preserves current state so the next actor can continue without reconstructing the case from chat history.

## Before you begin

- Use a copy of `assets/it-case.template.json`.
- Store the case where its owner controls access.
- Redact passwords, MFA codes, recovery phrases, private keys, and unnecessary personal data.
- Keep the case with the device or organization it describes; do not mix unrelated devices in one file.

## Create the case

1. Copy `assets/it-case.template.json` to a working location.
2. Give it a stable identifier such as `IT-20260718-001.json`.
3. Replace the template placeholders with facts you know.
4. Leave unknown facts as `unknown`, `not-recorded`, or `not-examined` instead of guessing.
5. Populate `next_move.action`. The validator requires a usable next action.

## Understand the top-level fields

| Field | What it preserves |
|---|---|
| `case_id` | Stable identity for the episode of work |
| `updated_at` | Time of the latest reconciled state |
| `status` | Current evidence or action state |
| `device` | Ownership, identity, platform, and environment |
| `complaint` | Desired outcome, observable symptom, trigger, affected and working functions, changes, and stakes |
| `custody` | Hazards, data, backup, encryption, privacy, authority, and referral limits |
| `evidence` | Reported, observed, measured, or retrieved records |
| `hypotheses` | Materially different causal explanations and their predictions |
| `tests` | Planned or executed discriminating checks |
| `changes` | Authorized, applied, and rollback-relevant interventions |
| `sources` | Vendor or other authority with version and applicability |
| `verification` | Original-envelope result, adjacent checks, disposition, and reopen condition |
| `next_move` | Action, owner, required authority, and evidence needed to advance |

The schema allows additional fields, but preserve the required fields and controlled values in `schemas/it-case.schema.json`.

## Use status and disposition correctly

`status` records the present evidence or action state, such as `reported`, `measured`, `test-planned`, `test-run`, `supported`, `falsified`, `confirmed`, `change-authorized`, `change-applied`, `verification-passed`, `verification-failed`, `deferred`, or `referred`.

`verification.disposition` records how far the case can close:

- `verified-resolved`: the original failure envelope and affected neighbors passed;
- `improved-unresolved`: behavior improved, but cause or closure remains incomplete;
- `workaround-only`: service is restored around the fault;
- `awaiting-observation`: more time, recurrence, or workload evidence is needed;
- `awaiting-authority`: an accountable decision is missing;
- `referred`: another custodian owns the next step;
- `unsafe/incomplete`: the case stopped at a safety or evidence boundary.

Do not use `verified-resolved` merely because a part was replaced, a command completed, or the symptom has not yet returned.

## Validate the file

From the release root, run:

```text
python scripts/validate_case_file.py path/to/case.json
```

- Expected result for a valid file: `PASS` followed by the case path.
- If the result begins with `FAIL`, correct the named missing key, invalid state, incorrect array type, verification disposition, or empty next action. Do not delete evidence to make validation pass.

The validator checks required structure and controlled states. It does not prove that case facts are true, a test ran, a change was authorized, or a repair worked.

## Resume the case

Start a new task with:

```text
$beryl-it-tech Resume this case at its first unverified edge. Preserve falsified hypotheses, authority limits, and planned-but-unrun tests.
```

Attach or paste the case file. Beryl should identify the present disposition, decisive evidence, live hypotheses, next move, and evidence required to advance. It should not restart intake or describe a planned test as completed.

## Confirm a usable handoff

A case is ready to transfer when another technician can identify:

- the exact device and owner;
- the observable complaint and stakes;
- current hazards and data custody;
- evidence already preserved;
- hypotheses strengthened or falsified;
- tests and changes that actually occurred;
- rollback state;
- verification disposition;
- next actor, authority, action, and advancement evidence.

See the worked cases under `examples/` for demonstrations of state motion, not diagnoses to copy.
