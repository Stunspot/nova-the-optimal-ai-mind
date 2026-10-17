# Demonstration: green unit shape, red release reality

Load when a changed service coordinates authorization, persistence, and an external side effect yet existing tests exercise only the normal return path.

The existing Vitest case looks reassuring: it observes `cancelled` and one provider call. TestForge does not add random edge cases. It maps the commit points and notices that the provider call occurs before durable local state. The decisive cue is not “there is a retry”; it is **an external effect can succeed while the caller observes failure**.

That cue changes the manifest:

- `R-001` becomes critical because retry can duplicate a billing-side effect.
- `INV-001` names one logical cancellation → at most one remote cancellation and one event.
- `S-RETRY-001` interrupts between remote commit and local persistence, then redelivers.
- The oracle includes final local state, remote effect count, and event count; provider call count alone was not the contract.

The Vitest artifact is repository-shaped but remains `unexecuted` because dependencies are not installed. Static ordering evidence supports an open critical finding, while absent execution remains attached to that test. The result is `NOT_READY`, not `BLOCKED_BY_ENVIRONMENT`: the environment blocks confirmation, but the inspected code already exposes a release-blocking duplicate window.

The transferable behavior is to find the real commit boundary, give the failure an invariant, and keep code evidence separate from execution evidence.
