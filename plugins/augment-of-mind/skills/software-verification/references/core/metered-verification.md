# Metered verification preflight

Use this doctrine before hosted CI, device or browser farms, paid cloud tests, and any verification route constrained by an allowance, credit balance, spending limit, or finite reservation.

## Capacity record

Capture a fresh, attributable snapshot before proposing execution:

- provider and account or organization boundary;
- observation time, evidence source, and a validity deadline no more than 60 minutes later;
- the billing scope named by the snapshot and the billing scope the planned execution will consume; they must match exactly;
- `capacity_status`: `observed`, `unavailable`, or `unknown`;
- remaining included allowance when the provider exposes it;
- allowance refresh or billing-cycle boundary;
- whether paid overage exists and whether the principal explicitly authorized it;
- a principal-set reserve that this run must not consume.

An inaccessible allowance is `unknown`, not zero. A malformed, future-dated, expired, over-age, or pre-refresh snapshot observed before a billing-cycle rollover cannot authorize execution after that rollover. A provider refusal before any test step establishes `unavailable` for that attempted route; it is provider non-execution, not a product failure. Never run a job merely to discover whether the meter permits it.

## Complete run estimate

Count the entire execution graph, not one visible workflow label:

`estimated usage = sum(trigger copies x matrix jobs x attempts x job ceiling x billing multiplier)`

Include duplicate triggers such as `push` and `pull_request`, matrix expansion, reusable-workflow fan-out, retries or reruns, and the provider's current billing rule. Obtain provider-specific multipliers from current provider documentation or account data; do not preserve an old multiplier as lore.

`attempts` includes the initial attempt. One allowed retry therefore means two attempts. For example, two triggers × three matrix jobs × two attempts × a 20-minute ceiling equals 240 raw runner-minutes before any provider multiplier. State both the arithmetic and the total even when the multiplier or allowance remains unknown.

Represent each expanded job in the input to `scripts/assess_metered_verification.py`, or use its `count` and `billing_multiplier` fields. A ceiling is deliberately conservative: optimization happens before launch, not after the allowance has gone to Valhalla.

## Decision

- `PROCEED`: observed included capacity covers the estimate and reserve.
- `HOLD_RESERVE`: the run fits only by consuming the retained reserve.
- `HOLD_INSUFFICIENT`: observed capacity cannot cover the run.
- `HOLD_UNKNOWN`: capacity cannot be established.
- `HOLD_PROVIDER_UNAVAILABLE`: the provider has refused or disabled execution.
- `AUTHORITY_REQUIRED_PAID`: paid execution could cover the run but lacks explicit authority.

Only `PROCEED` permits automatic invocation. The assessor is advisory and cannot accept, authenticate, or grant spend authority; caller-authored JSON is not a human decision record. When paid capacity would be required, it returns `AUTHORITY_REQUIRED_PAID` and `paid_dispatch_permitted: false`. Any later paid dispatcher must independently resolve an opaque authorization against principal-controlled durable custody, bind it to the exact execution and complete canonical plan content, billing scope, expiry, and maximum paid minutes, and atomically consume it. The preflight creates no checksum or receipt. Provider execution and billing records are retained only after an authorized run actually occurs. Those enforcement mechanics are outside this script. When price data is available, show the bounded monetary estimate to the principal before authorization. Minimize or batch the plan and reassess when held. If a local, clean-host, or self-hosted substitute exercises the real product boundary, use it and record the precise hosted-provider guarantee still absent.

Do not fabricate a `paid_overage_authorization` field, set an override flag, or offer a dispatch command after `AUTHORITY_REQUIRED_PAID`. The assessor rejects caller-supplied authority fields. Its output is an input to a later human decision, never the decision itself. A request to the principal must bound the decision to the exact run, maximum paid minutes, maximum monetary spend when price data is available, billing scope, and expiry; “authorize paid overage” by itself is a blank cheque, not a bounded request.

Report the preflight under five headings: `Capacity`, `Expansion`, `Decision`, `Substitute`, and `Authority`. Under `Expansion`, write `triggers × matrix jobs × attempts × ceiling minutes × provider multiplier = estimated billed minutes`. Report the multiplier as an observed value or explicitly as `unknown`; when it is unknown, state the raw runner-minute total through the ceiling term and do not call the preceding job-attempt count minutes. On any hold, `Substitute` is not optional: name a credible lower-cost or unmetered route, then write `This substitute does not prove:` and name the provider runner/image, trigger/matrix, permission/secret, artifact, and status-integration guarantees absent from the acceptance claim. If the current host cannot execute the substitute, describe a local, clean-host, self-hosted, or batched route generically as `PREPARED — NOT EXECUTED` and name the missing capability; absence is an evidence boundary, not permission to omit the route. Do not invent a local command or path that repository evidence has not established. Keep the response concise and state only the final calculation rather than exposing internal deliberation.

Copy supplied snapshot facts exactly. Never turn “valid for another 25 minutes” into a guessed observation timestamp or a different deadline. Always calculate and state:

- `required_with_reserve_minutes = estimated_minutes + reserve_minutes`
- `included_available_after_reserve = max(remaining_minutes - reserve_minutes, 0)`
- `maximum_paid_minutes_required = max(estimated_minutes - included_available_after_reserve, 0)`

Use `maximum_paid_minutes_required` as the single maximum in any bounded paid-spend request. Do not offer an ambiguous range. For 45 estimated minutes, 15 remaining minutes, and a 10-minute reserve: required with reserve is 55, included capacity usable after retaining the reserve is 5, and maximum paid minutes required is 40.

## GitHub Actions

For private repositories, inspect the account or organization Actions allowance through the current GitHub billing UI or billing API before triggering GitHub-hosted runners. Record when the value was observed and when the allowance is expected to refresh. If the available credential cannot read billing data, report `unknown`; do not infer capacity from repository access.

Expand every workflow trigger and matrix job. In particular, a push to a pull-request branch can create both a `push` run and a `pull_request` run. Keep both only when both trigger paths are part of the acceptance claim.

GitHub-hosted execution, public-repository treatment, larger runners, and self-hosted runners have different billing and operational boundaries. Consult current official GitHub documentation when constructing the snapshot. A red workflow with no executed steps and a billing or spending-limit refusal is evidence that GitHub did not run the test, not evidence that the candidate failed it.
