# Verification report

## Decision

**Status:** NOT_READY
**Target:** subscription cancellation
**Revision:** synthetic-ts-v1
**Reviewer:** REVIEW_PASS

### Basis

- critical duplicate-side-effect window remains open
- decision-critical test is unexecuted

## Scope

### Included

- tenant authorization
- billing cancellation
- state persistence
- event publication

### Excluded

- email rendering

## Critical invariants

- INV-001: one logical cancellation causes at most one remote cancellation and one event
- INV-002: a cross-tenant request changes no state and performs no downstream call

## Risk register

| ID | Severity | Disposition | Risk |
|---|---|---|---|
| R-001 | critical | unresolved | ambiguous provider timeout -> retry repeats remote cancellation -> duplicate billing-side effect |
| R-002 | critical | planned | cross-tenant identifier -> unauthorized cancellation -> tenant boundary violation |

## Execution evidence

| ID | Status | Exit | Command | Raw evidence |
|---|---|---:|---|---|
| E-001 | blocked | None | `npm test -- --run expected/cancelSubscription.integration.test.ts` | not_available |

## Findings

- F-001 [PRODUCT_DEFECT/critical]: remote effect precedes durable idempotency state, leaving an ambiguous-timeout duplicate window — open

## Residual risk

- RR-001: provider sandbox idempotency semantics are not supplied — verify provider contract before release

## Authority still required

- service owner approves remediation
- dependency installation before execution
