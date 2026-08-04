# An oracle makes wrong behavior observable

A test is evidence only when its observations discriminate the intended behavior from a plausible dangerous implementation.

Strong oracles usually combine:

- returned value or response contract;
- persistent post-state;
- emitted event or external effect;
- forbidden side effect;
- ordering or timing bound where material;
- invariants preserved across the operation.

Weak proxies include truthiness, “did not throw,” status code alone, snapshot bulk, mock call count without state, or implementation-private details. Strengthen them by naming the user- or system-visible consequence.

For each scenario, ask:

1. Which incorrect implementation should this catch?
2. What observation differs between correct and incorrect behavior?
3. Could a mock, fixture, or assertion make both look the same?
4. What must remain unchanged on denial or failure?

When expected behavior is disputed, preserve competing oracles and seek the domain authority; do not choose the easiest assertion.
