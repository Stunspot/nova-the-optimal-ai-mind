# Retry policy and idempotency are separate contracts

A retry policy answers **when and how again**. Idempotency answers **whether again changes the outcome**. Green retry-counter tests establish neither duplicate safety nor crash recovery.

Map the commit points: request accepted, remote effect performed, local state persisted, event published, acknowledgement returned. Probe interruption between each pair. Re-deliver the same operation with the same and different idempotency keys; verify final state, effect count, result stability, and conflict behavior.

Timeouts need a total budget, per-attempt bounds, cancellation behavior, and observability. Backoff without a cap can extend latency beyond the caller's contract. Retrying non-transient failures can amplify harm.
