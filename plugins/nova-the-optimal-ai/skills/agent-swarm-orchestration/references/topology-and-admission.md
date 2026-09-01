# Compile the next horizon into the lightest capable execution regime

The organization workbench decides what kinds of contribution and interaction the task needs. The execution kernel decides how the next ready work runs safely. Do not force organization semantics into the dependency graph.

## Read the dependency graph

Represent each candidate slice by its accepted inputs, transformation, output, owner, consumer, read surfaces, write surfaces, evidence burden, and return condition. An execution edge means one slice's accepted output or state transition is required before another begins.

Ready work has no unresolved incoming edge. A worker is useful only when its slice can complete coherently and its return can be consumed without reconstructing hidden process. Cognitive challenge or visibility does not create an execution dependency unless the downstream transformation truly requires the exposed return.

## Use the literal regimes

| Execution regime | Use when | Characteristic failure |
|---|---|---|
| Direct | Root work is small, sequential, tightly coupled, latency-sensitive, or shared-context-heavy | delegation overhead exceeds work |
| Enlist | One bounded specialist, noisy, contained, or independently checkable contribution helps root work | worker receives the whole mission and drifts |
| Assemble | At least two independent ready slices improve speed, coverage, search, challenge, resilience, or isolation | hidden dependencies, duplicated work without purpose, or overlapping writes |
| Chain | One accepted return defines another stage's exact input | fake parallelism creates stale downstream work |
| Recover | Existing work is failed, stale, conflicting, contaminated, interrupted, or based on a wrong premise | identical retry without a changed premise |

Competing hypotheses, independent review, boardroom, anthill, platoon, general staff, and other patterns are organization or interaction recipes. They compile into one or more of these regimes; they are not additional regime labels.

## Select by whole marginal value

Estimate startup, context reconstruction, duplicated reads, tool contention, latency, messages, exposure risk, rounds, merge, verification, correction, and cleanup. Compare the complete cost with expected speed, recall, evidence access, specialist depth, independence, resilience, output isolation, uncertainty reduction, or error detection.

Prefer the least cumbersome organization that is sufficient for acceptance. This is not always the fewest agents. Purposeful redundancy, independent confirmation, broad exploration, incubation, or containment can justify more members when their causal reason, budget, resolver, and release signals are explicit.

Preserve coordination capacity. On a constrained host, the root may keep a slot and perform one slice locally. On a host with separate coordination capacity, another arrangement may be safe. Inspect the live contract.

## Protect single-writer integrity

Assign one writer per file, record, database row set, external object, or other mutable surface at a time. Parallel members may inspect the same evidence. They do not make overlapping edits unless work is deliberately sequenced and the next writer begins from reconciled current state.

Sequence correctness-bearing changes before presentation changes. Technical, factual, schema, security, or policy correction establishes the accepted substrate; clarity, style, formatting, and polish follow from observed current bytes. Independent perspectives can return comment-only recommendations to one integration owner.

Partition by directory or module only when those boundaries match the actual change. Shared schemas, locks, generated indexes, manifests, decision records, or external objects can couple apparently separate folders.

## Re-score at meaningful events

Reconsider the execution regime and organization after decisive evidence, accepted dependency, verifier failure, user correction, contribution completion, stall, authority change, budget change, contamination, newly exposed dependency, or supported acceptance. Do not churn the team continuously, and do not preserve a topology after its causal job disappears.
