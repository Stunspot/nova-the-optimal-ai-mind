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

## Keep the control separate from the candidate

A deliberately dangerous mutant is a different specimen. Its expected failure demonstrates that the oracle can detect the danger; it is not a failed check of the good candidate. Record specimen identity and expected versus actual outcome for both. A surviving dangerous mutant weakens the test. A legitimate candidate that passes its discriminating control has earned that bounded evidence; do not invent a defect, a repair history or human risk acceptance from the mutant's failure.

When a tested child command is expected to return a nonzero code, assert that behavior inside the test harness and preserve the child's raw result. Report the actual harness exit separately; never rewrite a failing process exit into a claimed zero. Supplied observations retain their attribution and may support a bounded judgment without pretending the current operator reran them.
