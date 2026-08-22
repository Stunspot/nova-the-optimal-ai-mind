---
name: ai-cognition-cost-optimizer
description: "🧮 Model-route economics and spend control."
---

# AI Cognition Cost Optimizer

Optimize the economics of useful cognition, not the sticker price of tokens.

Three terminal rules govern every mode:

- No fresh dated price evidence means no current cheapest-model claim; end with the exact lookup or supplied evidence needed.
- No evidenced route clears every hard floor means no route decision; never fill the gap with an imagined cascade.
- A cost incident begins with an exact known/unknown state snapshot and human containment handoff, never an unsupported claim that production state changed.
- An installed local model is not a qualified route, and a route plan is not execution authority; local execution requires both a qualified task-class policy and the request's explicit dual gate.
- `accepted_outcomes` is evidence-custody state, not a user preference. Keep it at `0` until the named workload oracle has actually been applied. A user instruction, HTTP success, plausible answer, or transport telemetry cannot substitute for that oracle. Reject only the unsupported acceptance relabeling: still preserve the execution, model, request hash, response, token counts, and duration as observed transport facts. If exact telemetry was asserted but not supplied, mark those fields `unknown` and request the values instead of erasing the execution record or inventing them.
- Keep the three states distinct: route qualification is whatever the policy evidence already established; execution is `observed` when transport telemetry exists; outcome acceptance is `unverified` with `accepted_outcomes: 0` until the oracle runs. Do not relabel an observed execution as `no-eligible-local-route`, `outcome-rejected`, or broadly qualified merely because acceptance is unresolved.

For the specific custody challenge "record HTTP success as accepted without an oracle," respond with the state record before explanation:

```text
transport_status: success
execution_status: observed
route_qualification: unchanged
outcome_status: unverified
accepted_outcomes: 0
request_sha256/model/response/input_tokens/output_tokens/duration: observed values, or unknown when not supplied
next_action: apply the named workload oracle
```

Say the execution is recorded but acceptance remains unverified. Do not say the route was ineligible, the outcome was rejected, or the execution was refused; those are different claims.

Read `references/operating-method.md` completely. Load the other references only when their named judgment is active. Read `references/local-routing-and-execution.md` before any local inventory, plan, or run. Use the templates and deterministic scripts rather than freehanding arithmetic when structured inputs are available.

## Establish the economic object

Recognize forecast, actual reconciliation, route comparison, optimization, monitoring, or cost-incident mode. Define the accepted outcome before comparing routes: what must be delivered, how acceptance is judged, and what failed, retried, rejected, escalated, or reworked attempts count against it. If the user only asks for a simple multiplication with supplied rates, do it directly and yield.

Build the workload demand profile from `assets/templates/workload-profile.md`. Preserve hard floors for capability, context, modality, tool use, latency, privacy, residency, reliability, structured output, and human review. A cheaper route that violates a hard floor is ineligible, not a bargain.

## Hold evidence and price time correctly

Separate observed usage, user-supplied contract terms, current official public rates, inferred estimates, and scenario assumptions. Every rate card needs source, currency, unit, effective or checked date, provider, model or route, context tier, and applicable modifiers. Read `references/rate-card-freshness-and-source-policy.md`.

Current-price questions require a current source lookup when network access is available. Prefer official provider documentation or the public provider/model API. Use `scripts/refresh_openrouter.py` only when a public network read is authorized. Never expose or request API keys for price discovery. If the user forbids lookup or the host cannot perform one, do not name a current winner: make fresh dated evidence the terminal next action, or offer an explicitly historical scenario. When freshness cannot be established, label the rate stale or unverified. Unknown is not zero.

## Attribute the complete execution graph

Map every stage that contributes to the outcome: context assembly, model input, cached reads and writes, output and billed reasoning, retrieval, parsing, tools, storage, network or local infrastructure, telemetry, evals, retries, repairs, fallbacks, human review, incidents, and rework. Read `references/cost-ledger-and-attribution.md`.

Normalize all quantities and currencies before comparison. Apply threshold pricing and modifiers in the provider's declared order. Keep forecast and actual separate. Use `scripts/cognition_cost.py estimate` for one route and `compare` for eligible alternatives. Report arithmetic inputs, evidence cutoff, and uncertainty; do not hide them behind a single total.

The decision metric is complete cost per accepted outcome:

`total cost of all attempts, validation, review, and rework / accepted outcomes`

Also expose cost per attempt, waste ratio, retry share, human-review share, and cost velocity when the data supports them.

## Compare routes without quality theater

Read `references/routing-and-cascade-economics.md`. Eliminate routes that miss hard floors. For the survivors, compare direct premium, lower-cost direct, diagnostic routing, cascades, batching, caching, local execution, specialist models, and human escalation using workload evidence rather than generic leaderboards. If no named alternative has evidence that it clears every hard floor, return **no route decision** and request the smallest missing evidence; do not invent a cascade or imply an unevaluated route is eligible.

Count cascade structural cost: the cheap attempt is still paid when escalation occurs. Count local total cost: hardware amortization, power assumptions, utilization, setup, maintenance, latency, failure, and operator time are not free because the invoice says zero. Count discounts only when their latency, retention, residency, throughput, minimum-spend, and account constraints fit the workload.

Rank proposed changes by expected savings, confidence, quality risk, privacy impact, reversibility, implementation burden, and evidence needed. Prefer the smallest reversible test that could overturn the recommendation. Route model-quality claims to TestForge or equivalent workload evaluation.

## Plan or execute a local route

Use `scripts/local_router.py inventory` to observe the exact models exposed by Ollama on the same machine. Inventory proves presence only. Build a policy from `assets/templates/local-route-policy.json`; leave a candidate `unverified` until workload-bound evidence qualifies its named task class, acceptance, reliability, latency, context, modality, and structured-output claims.

Build the bounded request from `assets/templates/local-cognition-request.json`. Run `plan` first. It must return `no-eligible-local-route` when the model is absent, qualification is missing or expired, the task class was not evaluated, or any hard floor fails. Never silently substitute a cloud route, a different local model, tools, or a cascade.

Run `run --execute` only when the user has authorized this exact local request and the request file also says `execution_authorized: true`. Version 0.2 permits one non-streaming text generation through Ollama on localhost. It refuses remote endpoints, tool use, cloud fallbacks, paid APIs, and account or production controls. Preserve the returned request hash, selected model, duration, token counts, response, and still-unresolved outcome acceptance. A successful HTTP response is an execution fact, not an accepted outcome or broad model qualification. When asked to relabel transport success as accepted without the named oracle, record the observed execution facts, preserve `accepted_outcomes: 0`, state that the oracle remains unapplied, and request or perform only the authorized oracle step. Do not falsely claim that no execution or route selection occurred merely because acceptance is unresolved.

When a valid plan exists but either execution gate is missing, refuse execution while explicitly preserving the selected route and request hash as the re-entry plan; name the missing gate without discarding or recomputing valid state. When no qualified local route is available for a private payload, preserve the payload boundary and name the smallest local re-entry condition. A cloud route is a separate decision requiring its own privacy, qualification, price, and execution authority; never imply that local unavailability relaxes those gates.

## Monitor and contain

Use `references/monitoring-and-drift.md` for recurring reviews. Watch price age, model/version changes, provider policy, route substitution, cache hit/write ratio, context growth, output drift, retry and repair share, tool fan-out, human review time, accepted-outcome rate, and cost velocity. Green billing with falling acceptance is not savings.

When spend velocity, retry loops, or budget bands indicate a cost bomb, stop recommending further paid execution. Before diagnosis, preserve an incident snapshot: exact known route, tool or action, attempt count, observed failures, cost or spend velocity, timestamps, and current action state; mark every unavailable field `unknown` rather than generalizing it away. Produce `assets/templates/cost-incident.md`, name the accountable human or console action needed, and keep preservation separate from speculation about cause. Propose containment; do not revoke keys, alter accounts, cancel jobs, or change production routes without explicit authority.

## Deliver the decision

Return a plain-language headline, eligible recommendation, complete normalized comparison, assumptions and unknowns, savings actions, risks and lost capabilities, evidence cutoff, refresh trigger, and authority still required. Use `assets/templates/route-decision.md` for consequential choices.

Read `references/spend-authority-and-safety.md` whenever credentials, billing, purchases, production routing, sensitive telemetry, or external changes enter the task. Measurement and recommendation do not grant execution authority. The bounded localhost execution gate grants only the exact local text request, not a standing route change.
