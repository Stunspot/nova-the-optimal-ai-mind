# Cost Ledger and Attribution

The accounting boundary is the complete execution graph. Attribute each cost to workload, route, stage, attempt, tenant or project where applicable, and outcome.

## Billable and economic components

- uncached input, cached read, cache write, output, billed reasoning, images/audio/video;
- fixed request fees, web/search/tool calls, retrieval, embeddings, reranking, parsing, storage, and data transfer;
- local hardware amortization, power, utilization, hosting, maintenance, and operator time;
- safety checks, telemetry, evals, retries, format repairs, fallbacks, abandoned generations, incidents, and human review;
- rework and remediation following an apparently successful but rejected output.

Unknown components remain `null` with a note. Do not silently omit them from comparisons; show a subtotal and the incomplete boundary.

## Core measures

- `cost_per_attempt = total_cost / attempts`
- `cost_per_accepted_outcome = total_cost / accepted_outcomes`
- `waste_ratio = failed_retry_rejected_unverified_cost / total_cost`
- `acceptance_rate = accepted_outcomes / attempts`
- `cost_velocity = cost / elapsed_time`
- `risk_adjusted_value = captured_value - serve - verify - expected_failure - adoption - operational_change`

Use provider-reported native token and generation cost when available. Preserve invoice or trace reconciliation differences rather than forcing agreement.
