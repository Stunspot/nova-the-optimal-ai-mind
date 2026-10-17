# Authority and continuity

The owner-selected ledger checkpoint records the work. Keep the prior file and write a new checkpoint for meaningful changes. v2 separates ledger revision from baseline version: adding evidence or a review raises revision; changing baseline text, cutoff or decision context raises baseline version and appends the exact prior baseline. Use `validate NEW --previous OLD` to check retained history and ordered approvals. With one file alone, no tool can prove that undisclosed history was not removed.

## Use authority already given

Human authorization may already cover research, preparation, local adoption or delivery. Read its actual scope and carry it through. Record actor, time, scope and basis accurately; ask again only where required authority is missing or a reserved decision remains. Do not convert a name, an example, a status word, a hash or a tool result into consent. Native records store assertions; they are not signatures or an identity service.

Approval records are append-only decisions: approve or withdraw, bound to the starting baseline and complete patch content. The latest appended decision for that patch governs eligibility. Expiry, withdrawal, changed content or a different baseline invalidates its use. Retain earlier decisions and create a new patch ID after decided content changes. Source content is immutable across checkpoints except status; a corrected source gets a new ID. Retired evidence remains visible but cannot support current adoption.

`adopt` checks the current patch and writes a new checkpoint without replacing the input. It applies one exact unambiguous text span and records the prior baseline, evidence identity and approval assertion. An approved proposal is not already adopted. A brief is local preparation, not external distribution. Browser editing and downloads make neither change automatically. Publication fields are assertions whose existence does not prove a message or document was actually published.

Authority labels preserve what was claimed: model_generated, machine_validated, human_reviewed, human_approved, executed and verified. Explain their evidence; never promote one mechanically into the next.
