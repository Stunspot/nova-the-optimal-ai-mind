# Adversarial checks

Use the smallest check that could overturn the claim:

- Substitute a dangerous implementation mentally: would the assertion still pass?
- Remove the mock: which claimed boundary disappears?
- Repeat, reorder, interrupt, or partially apply the operation: can state duplicate or diverge?
- Change tenant, role, ownership, or identifier: is denial verified without side effects?
- Move one value across each boundary: does the oracle specify the expected side?
- Compare command time, revision, path, and environment to the report: is the evidence current and applicable?
- Trace each critical risk to scenario, executable test or manual charter, execution record, and finding disposition.
- Treat a green suite as one source: what high-impact behavior was never asked to fail?
- Treat a red suite as ambiguous: what single check separates product, test, environment, flake, contract, and tooling causes?
- Ask whose authority the recommendation would exercise if followed.
