# Verification output contract

The canonical machine record is one JSON verification manifest conforming to [assets/schemas/verification-manifest.schema.json](assets/schemas/verification-manifest.schema.json). The canonical human handoff is the assembled Markdown report. Assemble them only after the working evidence reaches a stable cutoff; they are not intake paperwork, package receipts, or authority to run release-sealing tools.

Required state:

- bounded target, revision, included scope, exclusions, constraints, and safety boundary;
- facts, assumptions, and unresolved unknowns attached to the claims they affect;
- impact map and domain invariants;
- risk register with a disposition for every critical risk;
- scenario catalog with explicit oracles and risk links;
- test records whose statuses distinguish designed, unexecuted, passed, failed, and blocked;
- execution records with command, working directory, exit code or explicit non-execution, and raw evidence reference;
- classified findings and residual risks;
- independent reviewer disposition;
- exactly one release status.

`READY` requires all decision-critical checks to have executed and passed, no unresolved critical or high product defect, no critical risk without credible evidence, and reviewer acceptance. `READY_WITH_RESIDUAL_RISK` requires the same blocking conditions to be absent plus bounded, visible residual risk. Other states preserve why readiness has not been earned.

Keep the report at least as qualified as its manifest. Preserve assumptions, unresolved claims, reviewer findings/conditions, all failed or incomplete attempts and linked residual treatment. Record command versus observation, supplied versus directly observed source, target revision and environment. One consistent status follows the evidence; it never grants release authority. See references/core/evidence-records.md for the machine-readable contract.
