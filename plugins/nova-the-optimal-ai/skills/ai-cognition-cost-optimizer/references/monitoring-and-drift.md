# Monitoring and Drift

Monitor economic, behavioral, and policy state together:

- rate-card age and source changes;
- requested versus actually served provider/model/tier;
- model/version deprecation or silent alias movement;
- input, cached read/write, output, reasoning, retrieval, tool, and review quantities;
- cache hit ratio and write amortization;
- context and output growth;
- attempt, retry, repair, escalation, rejection, and acceptance rates;
- latency, queue, failure, and fallback behavior;
- cost per accepted outcome, waste ratio, and cost velocity;
- privacy, residency, retention, and account-policy changes.

Use workload-specific baselines. Alert on meaningful deltas, not universal magic thresholds. A falling cost paired with route downgrade or acceptance collapse is a behavioral incident. Capture metadata by default; never log credentials or raw sensitive payloads into a general cost ledger.
