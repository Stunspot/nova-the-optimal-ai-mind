# Plan state, ownership and validation

Use the plan for the next bounded execution phase. Run Python against the packaged scripts/validate_swarm_plan.py and your plan file; --help shows the command contract. VALID means the declarations are internally consistent. The validator does not open evidence references, authenticate receipts, observe workers, or prove the mission succeeded.

## Keep three questions separate

Worker status answers what happened to the worker. Output acceptance answers whether the root accepted that worker's deliverable. Mission outcome answers whether the integrated result met the user's criteria. Disposing a worker never answers the other two.

The original v1 status reconciled already declares a returned output accepted after root reconciliation. That legacy meaning is preserved. For a worker later marked closed, retain an optional output record with state accepted and concrete root-observed evidence references. A closed worker without that record has no accepted output available to a dependent consumer. A rejected output stays rejected even though the worker can be disposed.

Optional worker output is an object containing state (pending, accepted, rejected) and evidence (an array of references). Accepted/rejected decisions require concrete references, not none or N/A. Output accepted while planned, dispatched or working is contradictory. An optional started boolean records known dispatch history; omit it when unknown. False means the worker never started, not that an interrupted action rolled back.

Cancelled or interrupted responsibilities can be disposed before their prerequisites exist. They need not fabricate accepted inputs merely to stop. If started is explicitly true, dependency readiness remains required. Terminal unknown start history is not a claim that the work ran correctly.

## Retain uncertain writes

Declare paths consistently relative to one named workspace, or consistently absolute. A directory reservation includes descendants. src/a and src/ab are distinct; src and src/a overlap. Windows case, separator and trailing-dot/space aliases are compared conservatively. Symlinks, hardlinks, drive mappings, relative-versus-absolute aliases and arbitrary external-object aliases are not resolved. The root must map those to one ownership namespace before dispatch.

Two dependent writers can reserve the same surface while the downstream writer is still planned. Before the downstream starts, the upstream's accepted output and authoritative write state must be reconciled.

For a stopped writer, optional write_readback contains state unknown or reconciled and evidence references. Reconciled requires concrete observed readback. A closed, failed, cancelled or interrupted writer with unknown writes retains its reservation. Only known never-started work or observed reconciled readback releases that reservation. Legacy reconciled status retains its original combined output/write reconciliation meaning.

For a closed prerequisite that wrote anything, both accepted output and reconciled write_readback are needed before its consumer starts. Never record readback from an interrupt acknowledgment alone.

## Respect capacity and authority

budgets.concurrency_limit caps worker statuses dispatched and working; it excludes the root and future planned workers. A returned worker no longer consumes this execution count. Some hosts retain agent slots after a turn returns; inspect those actual slots and root/nested-worker limits before another spawn. The plan cannot measure the host or enforce limits across other plans.

Identical normalized text cannot appear in both authority.allowed and authority.reserved. Every worker permission must be drawn from allowed. This is a consistency check on declared grants, not semantic proof that differently worded permissions are compatible or user-authorized.

## Close control without inflating the result

Plan status closed means all responsibilities have terminal dispositions and next_move is a closure or an explicit re-entry-only-if condition. It does not mean success. Legacy v1 plans without outcome remain readable and print mission outcome unverified.

The optional outcome object contains state (unverified, partial, accepted, cancelled), checks, and unresolved. Each check names one exact plan acceptance criterion, result (passed, failed, not-run), and evidence references. Observed pass/fail results require concrete references. Unknown criteria and duplicate checks are rejected.

Accepted requires closed control, exactly one passing check for every acceptance criterion, no unresolved issues, and no unknown writes. A partial closed mission with failed checks is valid and must be reported as partial. An accepted declaration is still a declaration: the root must inspect the actual evidence and report its real verification boundary.

## Resume from the first unearned condition

Keep the old plan and observed result. Update the actual premise, source, authority, output decision or readback that changed; do not make a failing plan green by deleting the failed check or inventing evidence. If the new work belongs to a different phase, start its own plan and link the accepted predecessor output. Use the existing return, merge-ledger and organization-transition templates only when they resolve a live ambiguity.

For a legacy plan, add only state you can support now. Do not backfill started, accepted output, reconciled readback or mission success from a historical closed label.
