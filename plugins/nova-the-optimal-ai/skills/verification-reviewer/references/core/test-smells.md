# Test smells are credibility warnings

Smells do not prove a test is wrong; they identify places where the evidence claim may exceed the test.

- **Assertion poverty**: no assertion, truthiness, status-only, or “does not throw.”
- **Mock-boundary erasure**: the dependency whose semantics matter is replaced with the test's own assumption.
- **Snapshot overreach**: a large snapshot obscures the few consequential observations.
- **Temporal guessing**: fixed sleeps stand in for a state or event condition.
- **Shared mutable state**: order-dependent setup, reused database records, global clock, or leaked environment.
- **Exception swallowing**: broad catch or expected-failure logic turns unexpected faults green.
- **Branch mimicry**: the test restates implementation conditionals instead of asserting behavior.
- **Fixture fantasy**: data cannot occur under production constraints or omits material fields.
- **Flake laundering**: retries hide nondeterminism rather than diagnosing it.
- **Coverage theater**: line percentage is used as a substitute for risk and oracle coverage.

Repair the evidence claim or the test. Do not automatically delete, skip, broaden tolerances, or update snapshots to obtain green.
