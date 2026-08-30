# Choose the smallest topology that earns itself

The admission question is not “can this be delegated?” It is “will this delegation improve the accepted result after all coordination costs?”

## Read the task graph

Represent each candidate slice by its required inputs, transformation, output, owner, read surfaces, write surfaces, evidence burden, and downstream consumer. An edge means one slice’s accepted output or state transition is required before another can begin.

Ready work has no unresolved incoming edge. A worker is useful only when its slice is coherent enough to complete independently and its result can be consumed without reconstructing its hidden process.

## Select by marginal value

| Topology | Use when | Characteristic failure |
|---|---|---|
| Direct | Small, sequential, shared-context-heavy, same-surface, or latency-sensitive work | Delegation overhead exceeds work |
| Enlist | One bounded, noisy, specialist, or independently checkable slice helps the root | Worker receives the whole mission and drifts |
| Assemble | Two or more independent ready slices improve speed, coverage, or challenge | Hidden dependencies or overlapping writes |
| Chain | Accepted output from one slice defines the next | Fake parallelism produces stale work |
| Competing hypotheses | Rival explanations can be tested independently without answer leakage | Agents converge from shared framing rather than evidence |
| Independent review | Consequence warrants fresh challenge of an existing artifact or evidence chain | Reviewer sees the intended answer and rubber-stamps it |
| Recover | Existing swarm state is stale, conflicting, failed, or interrupted | Repeating the same route without changed premise |

## Price the whole swarm

Estimate worker startup, context reconstruction, duplicated reads, model cost, tool contention, latency, messages, merge, verification, correction, and cleanup. Compare that complete cost with expected speed, recall, specialist depth, independence, output isolation, or uncertainty reduction.

More workers can increase wall-clock speed while worsening total cost and merge quality. Use the fewest workers that cover the independent ready frontier. Preserve one coordinator slot unless the live runtime explicitly supplies separate coordination capacity.

## Protect single-writer integrity

Assign one writer per file, record, database row set, external object, or other mutable surface at a time. Parallel agents may inspect the same evidence. They should not make overlapping edits unless the work is deliberately sequenced and the next writer begins from reconciled current state.

Sequence correctness-bearing changes before presentation changes. Technical, factual, schema, security, or policy correction should establish the accepted substrate; clarity, style, formatting, and polish follow from observed current bytes. When both perspectives can be formed independently, use comment-only review packets and one integration owner instead of multiple writers.

Partition by directory or module only when those boundaries match the actual change. A cross-cutting contract, shared schema, lockfile, generated index, or documentation manifest may create hidden overlap across apparently separate folders.

## Re-score at real changes

Reconsider topology after decisive evidence, a user correction, completion, failure, authority change, budget change, or newly exposed dependency. Do not continuously churn the team because another possible decomposition can be imagined.
