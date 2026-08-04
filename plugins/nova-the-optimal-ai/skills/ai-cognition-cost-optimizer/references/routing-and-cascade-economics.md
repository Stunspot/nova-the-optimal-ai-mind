# Routing and Cascade Economics

Selection follows floors, then economics.

1. Exclude routes missing capability, context, modality, tools, structure, privacy, residency, latency, reliability, or authority requirements.
2. Estimate complete cost and accepted-outcome rate for each survivor from workload evidence.
3. Stress volume, cache misses, long-context tiers, retries, outages, and review burden.
4. Prefer the least-cost route whose downside remains acceptable.

For a two-route cascade:

`expected_cost = low_route_cost + escalation_probability * high_route_cost + validation_cost`

If escalation is frequent, direct premium routing may be cheaper. Pre-generation diagnostic routing avoids paying a doomed low-route attempt but requires its own validated router. Batch discounts trade latency and often retention characteristics. Caching earns savings only when stable prefixes, tenant boundaries, reuse density, write cost, TTL, and invalidation behavior align.

Generic benchmarks nominate candidates; task-specific accepted outcomes decide. A model may be cheap per token and expensive per success. A premium model may be cheaper if it avoids retries, review, or failure. No route earns quality credit without evidence.
