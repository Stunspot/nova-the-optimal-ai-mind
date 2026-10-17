# Races violate invariants across valid local steps

Look for read-check-write sequences, uniqueness assumptions, shared counters, caches, queue consumers, lock ordering, and state transitions whose correctness depends on interleaving.

State the invariant first, then construct two or more operations that can cross the vulnerable window. Synchronize on observable barriers or test hooks rather than sleeps. Assert final state, effect multiplicity, conflict response, and recovery.

A nondeterministic reproduction is evidence of a race but a poor regression test. Once localized, build a deterministic interleaving or property that fails reliably.

## A user operation outlives its first event

For interactive work, trace the operation from request to final commit or invalidation. Identify its target record, the draft/revision it was allowed to replace, and the current generation of the workspace. The vulnerable interval may include file reading, hashing, validation or an asynchronous confirmation after the apparent loading step. Cancellation or navigation can invalidate the request even when the underlying work cannot be stopped.

A pending read can also cross a successful write: hold an older refresh snapshot, complete a current mutation, then release the read. Verify that the visible catalog and authoritative saved state remain consistent with the newer commit, or that the interface honestly identifies a stale view and recovers. Protecting storage alone does not establish a correct current display.

Bind the invariant to user work: a late result cannot silently discard newer edits, insert an old editor's text into another record, or resurrect a cancelled operation. Observe both visible state and the stored/exported result when persistence is claimed. A title, successful return, spinner or clean console alone cannot establish this invariant.

Hold a real asynchronous boundary with a deferred response, promise gate or supported test hook; observe that the request reached it. While held, perform the conflicting action through the actual interface. Release the boundary and observe completion before asserting preserved work and effect count. When several awaits can still separate permission from mutation, select the last consequential one or justify why the earlier barrier covers them. Retain the action order and states at request, conflict and commit so the failure is reproducible without sleeps.

Judge the chosen interaction contract. A serialized interface must keep every conflicting route unavailable for the full operation, visibly explain the wait, and restore interaction on success, cancellation and failure. Probe real pointer/keyboard paths; calling a handler directly cannot prove inert UI. An editable interface must retain the new work or obtain permission against the current draft immediately before replacement. If a confirmation itself yields, test edits and identity changes during that interval too. Generation fencing and record binding must prevent stale completion from mutating a successor; aborting a transport is only one possible implementation.

Pair each consequential rejection with useful work: a valid replacement commits once, cancellation preserves the draft, and retrying the same selected file works after cancel or failure. Where navigation leaves an editor alive, try applying its old draft after the target changes. Preserve or explicitly resolve that draft under its original identity; never count application to the new record as recovery. Test only the interleavings the candidate's contract exposes, not every possible permutation.

Use [the pending-replacement worked example](../../examples/pending-replacement/walkthrough.md) when the seam or oracle is unclear. Its synthetic trace teaches test construction, not proof that another product or a model passed. If only a reducer or mocked callback was exercised, limit the verdict to that layer and name the missing interface evidence.
