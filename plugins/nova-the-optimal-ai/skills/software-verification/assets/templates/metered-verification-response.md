# Metered verification response

Use this package-owned template for every quota-limited verification preflight. Copy supplied snapshot facts exactly. Replace every bracketed expression with an observed value or `unknown`; never invent a timestamp, validity interval, reserve, multiplier, command, or file path.

## Capacity

- Provider and billing scope: `[provider; exact billing scope or unknown]`
- Observation and validity: `[copy supplied observation and remaining validity exactly, or unknown]`
- Capacity status and included allowance: `[observed, unavailable, or unknown; remaining allowance or unknown]`
- Reserve and paid availability: `[principal-set reserve or unknown; paid availability or unknown]`

## Expansion

`[triggers] × [matrix jobs] × [attempts] × [ceiling minutes] = [raw runner-minute total]`

Provider multiplier: `[observed value or unknown]`

`[raw runner-minute total] × [provider multiplier] = [estimated billed minutes or unknown]`

Never label the intermediate trigger, job, or attempt count as minutes. State the raw total even when the multiplier is unknown. One retry means two attempts. For two triggers, three jobs, two attempts, and a 20-minute ceiling: `2 × 3 × 2 × 20 = 240 raw runner-minutes`; the billed total remains unknown when the multiplier is unknown.

When included capacity is observed, also state:

- `required_with_reserve_minutes = [estimated] + [reserve] = [evaluated total]`
- `included_available_after_reserve = max([remaining] - [reserve], 0) = [evaluated total]`
- `maximum_paid_minutes_required = max([estimated] - [included available after reserve], 0) = [evaluated total]`

After the equations, state whether the evaluated required-with-reserve total exceeds the observed included allowance. A formula that omits its evaluated result is incomplete.

For 45 estimated minutes, 15 remaining minutes, and a 10-minute reserve: required with reserve is 55, included capacity usable after retaining reserve is 5, and maximum paid minutes required is 40.

## Decision

`[PROCEED, HOLD_RESERVE, HOLD_INSUFFICIENT, HOLD_UNKNOWN, HOLD_PROVIDER_UNAVAILABLE, or AUTHORITY_REQUIRED_PAID]`

State whether automatic invocation and paid dispatch are permitted. Only `PROCEED` permits automatic invocation; this assessor never permits paid dispatch.

## Substitute

`PREPARED — NOT EXECUTED: [generic local, clean-host, self-hosted, or batched route, unless an observed repository route can be named]`

`This substitute does not prove: [provider runner/image behavior; trigger/matrix behavior; permission/secret integration; artifact integration; status integration].`

## Authority

If paid execution is relevant, ask for one decision with these explicit fields:

- Exact run: `[trigger name and count; matrix jobs; attempts; ceiling; multiplier]`
- Maximum paid minutes: `[evaluated maximum_paid_minutes_required]`
- Maximum monetary spend: `[observed estimate or unknown]`
- Billing scope: `[exact observed billing scope]`
- Expiry: `[copy the supplied snapshot expiry or remaining-validity interval exactly]`

Never replace the exact run with the phrase “the exact run,” offer a range, fabricate authority data, or issue a dispatch command. If capacity or reserve is unknown, request the missing authoritative observation instead of assuming zero.
