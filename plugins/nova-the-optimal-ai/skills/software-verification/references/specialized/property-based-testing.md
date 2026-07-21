# Properties compress families of examples

Use property-based testing when a stable invariant spans many inputs and generators can produce valid, meaningful cases. The property—not random volume—is the evidence.

Define generator domain, validity constraints, shrinking expectations, seeds, and failure persistence. Avoid tautologies that reimplement the function or properties so weak every output passes.

Examples: round-trip stability, monotonicity, commutativity where intended, conservation, idempotence, partition agreement, and equivalence under semantics-preserving transformation.
