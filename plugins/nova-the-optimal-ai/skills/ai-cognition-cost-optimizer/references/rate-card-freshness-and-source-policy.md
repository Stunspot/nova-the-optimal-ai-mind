# Rate-Card Freshness and Source Policy

Rate cards are dated evidence. They are never durable doctrine.

Prefer sources in this order:

1. user's signed contract, invoice, or account-specific console for that account;
2. official provider pricing or model API;
3. official cloud marketplace or partner platform rate page for that exact route and region;
4. reputable aggregator as discovery or cross-check;
5. user-declared scenario assumption.

Record source URL or document, checked and effective dates, currency, billing unit, provider, model/version/route, service tier, region, context threshold, cache semantics, batch/priority multiplier, tool charges, minimums, taxes or purchase fees, and confidence.

Use a refresh trigger when the source is older than the decision's tolerance, the model alias changes, a provider announces a new tier, invoices diverge, or route metadata changes. For active purchasing or production decisions, verify at decision time. Never infer a missing cache rate or discount from another provider.

OpenRouter's public model API can supply normalized per-token/request/unit fields and route metadata, but account purchase fees, BYOK terms, provider policies, and actual served-route details remain separate evidence.
