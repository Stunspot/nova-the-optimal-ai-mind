# Reality Ledger state and authority

`reality-ledger.json` is canonical. Briefs, reports, and exports are derived views.

## Objects

- baseline: the approved answer or operating state being maintained;
- sources: dated evidence with authority and access notes;
- candidates: unadmitted developments under examination;
- deltas: accepted answer-changing developments;
- rejections: candidates that failed the gate, with reasons and recheck conditions;
- fuzz: unresolved competing claims;
- patches: exact proposed mutations and their consequences;
- probes and traps: discriminating observations and stale-answer detectors;
- watch: thresholded future conditions;
- approvals: human decisions with scope and date;
- publication: external-release state.

## Status meanings

- `candidate`: recorded for examination; no answer-change authority.
- `accepted_delta`: evidence and mechanism warrant a patch proposal; baseline is unchanged.
- `rejected_noise`: presently excluded, with a recorded basis.
- `fuzz_unresolved`: conflict or uncertainty changes treatment and remains open.
- `patched`: an authorized patch has been applied to a new baseline version.
- `superseded`: retained history no longer current.
- `retired`: intentionally closed and no longer active.

## Authority gates

The model may extract, classify, recommend, draft, and run deterministic checks. Only an accountable human may:

- approve the original baseline;
- adopt a patch and create the next baseline version;
- accept material degraded operation;
- approve an external brief;
- authorize publication.

`machine_validated` means the record passed specified structural rules. `human_reviewed` means a named person examined it. `human_approved` means that person authorized the stated scope. `executed` records that an action occurred. `verified` records evidence that the intended result occurred. None implies another.

Never delete a prior approved baseline when applying a patch. Supersede it, preserve the change reason and evidence, and record which decisions operated under each version.
