# Governance, forecast, and capacity

Load this for governance design, planning, baseline decisions, status, exceptions, or recovery.

## Proportionate governance

Match control intensity to consequence, uncertainty, reversibility, coordination load, regulation, and decision latency. Define sponsor and accountable owner, delegated decisions, reserved decisions, tolerances, cadence, gates, evidence, and escalation. Remove any control that has no decision function.

## Forecast discipline

A usable forecast states:

- the completion unit and unit of measure;
- lower and upper bounds;
- confidence and the evidence basis;
- baseline and current variance;
- assumptions, dependencies, and uncertainty drivers;
- the next update event.

When no estimate exists, use `null` for both bounds and `unknown` confidence. A one-sided estimate may retain its known bound while the other remains `null`; state that limitation in the basis. Keep the reason and next update concrete. Zero is a real estimate, never a placeholder for missing evidence. Unknown forecasts warn without blocking otherwise authorized work.

A target date is not a forecast. A forecast is not a promise. A baseline is not immutable truth. When confidence is low, narrow uncertainty by resolving integration, dependency, capacity, or acceptance risk—not by deleting the range.

## Capacity and flow

Observe demand, available capacity, WIP, queue age, blocked work, handoffs, rework, and the current bottleneck. Limit WIP at the governing constraint. Starting more work can reduce throughput when attention, review, environments, specialists, or decisions are scarce.

For every material commitment, state:

- who or what capacity is required;
- what is already committed;
- what will be displaced;
- the WIP limit and any exception authority;
- the queue and bottleneck;
- the next action that improves flow.

Utilization is not the objective. Optimize reliable value flow and recovery options.
