# Metered verification response

## Capacity

Provider and billing scope: GitHub Actions for the private `nova-the-optimal-ai-mind` repository; the exact account billing scope and current included allowance were not observed in this cycle. A prior 2026-08-12 operator observation recorded private-repository jobs being refused before any test step because of the account billing or spending limit. That historical refusal is provider non-execution, not a current capacity snapshot. Capacity is therefore `unknown`; the expected 2026-09-01 monthly boundary has not yet been crossed and verified. Remaining minutes, a principal-set reserve, paid-overage availability, and any spending authorization are all unknown. No workflow was dispatched.

Current GitHub documentation says private-repository standard hosted runners consume the repository owner's allowance and that allowance resets at the start of the billing cycle. It also publishes operating-system-specific paid rates rather than one safe aggregate multiplier for this mixed-OS matrix: https://docs.github.com/en/billing/concepts/product-billing/github-actions

## Expansion

Candidate verification workflow: `1 manual trigger × 3 matrix jobs × 1 attempt × 15 ceiling minutes = 45 raw runner-minutes`.

Provider multiplier: `unknown` for the mixed `ubuntu-latest`, `windows-latest`, and `macos-latest` matrix. Estimated billed minutes against the account allowance cannot be asserted from the repository alone.

Pages workflow: `1 manual trigger × 1 job × 1 attempt × 10 ceiling minutes = 10 raw runner-minutes`. It is a publication action, not a substitute verification run, and publication authority is absent regardless of GitHub's current Pages billing treatment.

Because remaining allowance and reserve are unknown, `required_with_reserve_minutes`, `included_available_after_reserve`, and `maximum_paid_minutes_required` cannot be evaluated without inventing account facts.

## Decision

`HOLD_UNKNOWN`

Automatic invocation is not permitted. Paid dispatch is not permitted. The manual workflows remain dormant.

## Substitute

`EXECUTED LOCALLY OR PREPARED — NOT EXECUTED:` use the repository's local Python regression suite, deterministic temporary build, package verifier, documentation checker, static-site checker, and retained browser renders on the current Windows host. After the source is frozen, a clean local or self-hosted three-OS run is the credible unmetered next layer if those hosts are available.

`This substitute does not prove:` GitHub-hosted runner and image behavior; the provider's manual trigger and matrix expansion; permission, token, and secret integration; artifact upload or retention integration; Pages deployment; or GitHub check/status integration.

## Authority

No authority request is made in this cycle because a fresh authoritative capacity snapshot is missing and public distribution is already blocked by component rights. Re-entry requires an observed account billing scope, remaining allowance, refresh boundary, principal-set reserve, paid-overage state, and—only if paid execution is proposed—a separately authenticated human authorization bound to the exact workflow, matrix, attempts, ceilings, maximum paid minutes, maximum spend, billing scope, and expiry. Running a workflow merely to discover capacity is prohibited.