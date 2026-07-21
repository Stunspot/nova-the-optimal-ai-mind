# Races violate invariants across valid local steps

Look for read-check-write sequences, uniqueness assumptions, shared counters, caches, queue consumers, lock ordering, and state transitions whose correctness depends on interleaving.

State the invariant first, then construct two or more operations that can cross the vulnerable window. Synchronize on observable barriers or test hooks rather than sleeps. Assert final state, effect multiplicity, conflict response, and recovery.

A nondeterministic reproduction is evidence of a race but a poor regression test. Once localized, build a deterministic interleaving or property that fails reliably.
