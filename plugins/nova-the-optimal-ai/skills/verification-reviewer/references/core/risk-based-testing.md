# Risk buys evidence, not arithmetic

Risk-based testing directs scarce verification effort toward failures whose consequences justify the cost. A numeric score is an attention aid; the decision remains a judgment about impact, likelihood, exposure, detectability, recovery, and confidence.

## Keep unlike dimensions unlike

- **Impact**: consequence if the failure occurs—money, safety, privacy, authorization, corruption, availability, reputation, or reversibility.
- **Likelihood**: how readily the changed behavior can produce it under applicable conditions.
- **Exposure**: how often or broadly those conditions occur.
- **Detectability**: whether the failure will become visible before harm compounds.
- **Recovery difficulty**: cost and certainty of restoring correct state.
- **Confidence**: strength of the evidence behind those estimates.

Low confidence is not low risk. When impact is high and support is weak, uncertainty raises the evidence burden.

## A risk statement must be falsifiable

Write `condition → failure → consequence`, such as: “When a webhook is redelivered after the first fulfillment event but before completion is persisted, the order may be fulfilled twice.” This directly suggests an invariant, a scenario, and observable evidence.

Every critical risk carries one disposition:

- `covered`: credible evidence exists and is linked.
- `planned`: a scenario and method exist, but evidence does not.
- `accepted_by_human`: a named accountable person accepted a bounded residual risk.
- `blocked`: the required check cannot presently run.
- `unresolved`: the risk or its oracle is still materially uncertain.

Not every test needs its own risk. Every critical risk needs a disposition.
