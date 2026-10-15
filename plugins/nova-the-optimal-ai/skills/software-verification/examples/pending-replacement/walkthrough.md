# The draft written while replacement was waiting

The submitted claim is: "A reader may replace an open packet without silently losing unsaved work, and can cancel or retry the same file." The packet is fictional, with record A open and record B selected for import. This worked example is a test-design seed. Its expected results are oracles, not a claim that a submitted product or a model has executed them.

## Find the consequential boundary

At request start, A has no draft. The interface reads B, then validates it. While validation is unresolved, the reader types "Keep this observation" into A. A guard evaluated before reading B saw a clean document. The important question is what the later commit does with the newly dirty A.

State the invariant before selecting a seam: without permission covering the current draft, completion must preserve that draft under A's identity. B must never acquire A's unapplied editor text. Cancellation must invalidate the eventual completion. A successful authorized replacement must still work exactly once.

Use a local deferred response or a supported test hook at the final asynchronous boundary before replacement. The harness waits for a request-reached signal rather than a timer. Keep the normal button, input events and completion path in use. If the seam bypasses parsing, persistence or confirmation, say so and inspect whether that omitted stage can itself yield before mutation. Test the later boundary when it can.

```javascript
// Stack-neutral harness sketch; adapt the seam to the candidate.
const gate = deferredResponseForTheActualReadOrValidation();
await clickReplaceWith(fictionalPacketB);
await gate.requestReached;
await typeIntoCurrentDraft('Keep this observation');
gate.release(validPacketB);
await observeOperationSettled();
assertDraftPreservedUnderAOrCurrentDiscardPermissionRecorded();
assertNoDraftFromAWasAppliedToB();
```

An interface that serializes operations has a different legitimate intermediate observation: the real edit and conflicting navigation are unavailable while the request is held. Verify that through browser pointer/keyboard input and visible pending feedback. Then prove controls return after success, cancel and failure. Artificially setting a disabled flag in the test or invoking only the protected handler does not test that claim.

An editable interface accepts the text. At completion it must preserve it, explicitly resolve the conflict, or ask permission covering that current draft. Rejecting that permission leaves A and its work intact. Accepting it permits the stated replacement. If confirmation is asynchronous, hold that step too: another edit or record switch must invalidate the stale choice or obtain a fresh one.

## Cross the invalidation, then inspect the result

| Interleaving | Decisive observation | Matched useful control |
|---|---|---|
| A becomes dirty while B waits | A's newer text survives unless current discard permission covers it | Accept a current discard choice; B commits once |
| Cancel B, then release its deferred result | A and its draft stay unchanged after late completion | Select B again, including the same file; import succeeds |
| Open C while B waits | B's old completion cannot overwrite C or its work | A valid current request for C succeeds |
| Keep A's editor open, then replace the packet | Its old draft cannot apply to B | Reopen/apply a draft that actually belongs to B |
| Old refresh snapshot returns after a successful save | The visible catalog retains the newer committed result, or explicitly reports staleness and recovers | A fresh refresh displays current saved state |
| Read or validation fails | Existing work remains and controls recover | Retry the same file with valid data |

Capture the actual action order, target identities, draft text/revisions, current request, visible busy/editability state, completion status and stored/exported state. A final screenshot can show B while missing the erased draft. A no-exception log can pass every failure above. For an allegedly serialized UI, check a representative conflicting control outside the import button and the last pending stage before it becomes interactive again.

The reviewer should be able to substitute "checks dirty only at invocation", "cancel closes only the dialog", "old editor writes to the current record", or "unlocks before validation finishes" and see the corresponding assertion fail. Pair the failure with the successful control so refusing every import cannot pass. One example is not a complete interaction inventory: derive the candidate's actual operations and use the smallest interleaving that can overturn its claim.

A reproduced loss supports NOT_READY for that frozen candidate and returns it to builder custody. An unexecuted sketch supports a coverage gap, not an observed defect. A passing synthetic fixture proves the teaching oracle discriminates its mutations; product behavior, browser wiring and model adherence require their own evidence.
