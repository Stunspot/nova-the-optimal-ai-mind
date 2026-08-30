# Metered verification response

## Capacity

Provider and billing scope: GitHub Actions for the private `nova-the-optimal-ai-mind` repository; exact account billing scope and current included allowance were not observed in this cycle. The historical 2026-08-12 billing/spending refusal predates this candidate and is not a current capacity snapshot. Capacity is `unknown`. Remaining minutes, principal-set reserve, paid-overage availability, and spending authority are unknown. No workflow was dispatched.

Repository configuration does not establish the exact account billing scope, current included allowance, retained reserve, paid-overage state, or one authoritative multiplier for this mixed operating-system plan.

## Expansion

Candidate verification: `1 manual trigger × 3 matrix jobs × 1 attempt × 15 ceiling minutes = 45 raw runner-minutes`.

Line-ending policy: `1 manual trigger × 1 job × 1 attempt × 5 ceiling minutes = 5 raw runner-minutes`.

Pages deployment: `1 manual trigger × 1 job × 1 attempt × 10 ceiling minutes = 10 raw runner-minutes`.

Complete one-dispatch-each plan: `45 + 5 + 10 = 60 raw runner-minutes`.

Provider multiplier: `unknown` for the mixed Ubuntu, Windows, and macOS verification matrix plus the two Ubuntu jobs. Estimated billed minutes cannot be asserted from repository files. Because remaining allowance and reserve are also unknown, `required_with_reserve_minutes`, `included_available_after_reserve`, and `maximum_paid_minutes_required` cannot be evaluated without fabricating account facts.

The Pages job is additionally a publication action. Its billing treatment cannot create deployment authority.

## Decision

`HOLD_UNKNOWN`

Automatic invocation is not permitted. Paid dispatch is not permitted. All three workflows remain `workflow_dispatch`-only, time-bounded, and unrun. The canonical assessor was not invoked because its required exact billing scope, dated provider snapshot, refresh boundary, and numeric principal reserve are unavailable; fabricating those inputs would violate the preflight contract. The machine boundary is retained in `raw/metered-preflight.json`.

## Substitute

`EXECUTED LOCALLY OR PREPARED — NOT EXECUTED:` the repaired checkpoint has a fresh Windows regression run, deterministic temporary build exercise, rebuilt-package verification, documentation check, static-site check, and source-freeze check. A clean or self-hosted three-OS run is the credible unmetered next layer if suitable hosts become available.

`This substitute does not prove:` GitHub-hosted runner or image behavior; provider trigger and matrix expansion; permission, token, and secret integration; external action checkout behavior; artifact upload or retention; Pages deployment; or GitHub check/status integration.

## Authority

No authority request is made because the current allowance snapshot is missing and public redistribution is already blocked by component rights. Re-entry requires the observed account billing scope, remaining allowance, refresh boundary, principal-set reserve, paid-overage state, and—if paid execution is proposed—a separately authenticated human authorization bound to the exact workflow set, matrices, attempts, ceilings, maximum paid minutes, maximum spend, billing scope, and expiry. Pages deployment also requires explicit publication authority. Launching a workflow merely to discover capacity is prohibited.