# Example: competing hypotheses without consensus theater

**User:** “Our scheduled reports sometimes arrive twice. Use agents to find the cause, but do not change production.”

The root binds the acceptance condition as a supported causal diagnosis plus the smallest safe verification move. It keeps production read-only and notices that the failure could arise from scheduling, queue redelivery, or downstream idempotency. These explanations can be inspected independently against the same evidence without editing shared state.

The root admits three bounded workers:

- one traces scheduler creation and duplicate trigger evidence;
- one traces delivery retries, acknowledgments, and queue semantics;
- one inspects downstream deduplication and idempotency boundaries.

Each packet names the same incident window, relevant log and configuration locations, read-only authority, expected source locations, and a return contract. It does not reveal which explanation the root prefers. The root keeps the cross-cutting event-identity map and waits only after that map is ready.

Two workers return compatible evidence that the scheduler emitted one job and the queue redelivered after an acknowledgment timeout. The third reports that the downstream sender lacks an idempotency key. The root inspects the cited logs and code paths, then distinguishes cause from amplification: redelivery explains the second attempt; missing idempotency permits the duplicate customer-visible effect.

The result is not “all three agents agree.” It is a reconciled causal chain, source locations, explicit unknowns about the timeout’s infrastructure cause, and a prepared non-production test that can discriminate whether corrected acknowledgment timing alone prevents duplication. Production remains unchanged because no packet or user authority permitted a write.

The invariant is portable: independent workers test separable explanations; the root owns the common evidence model, distinguishes reports from observations, and integrates causes that operate at different layers rather than forcing one winner.
