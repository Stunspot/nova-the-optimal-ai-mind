# Verification report

## Decision

**Status:** NOT_READY
**Target:** inclusive date-range filtering regression
**Revision:** synthetic-py-v1
**Reviewer:** REVIEW_PASS

### Basis

- high-severity regression test fails on the documented boundary

## Scope

### Included

- date-range inclusion behavior

### Excluded

- timezone conversion
- database query planning

## Critical invariants

- INV-001: a closed date interval includes records equal to start and end and excludes immediate neighbors

## Risk register

| ID | Severity | Disposition | Risk |
|---|---|---|---|
| R-001 | high | covered | start-boundary record -> strict comparison omits valid data -> incomplete report |

## Execution evidence

| ID | Status | Exit | Command | Raw evidence |
|---|---|---:|---|---|
| E-001 | failed | 1 | `python -m unittest expected.test_date_filter -v` | expected/execution-record.json |

## Findings

- F-001 [PRODUCT_DEFECT/high]: the implementation excludes the documented inclusive start boundary — open

## Residual risk

- RR-001: timezone-aware datetime behavior is outside this date-only fixture — add a separate timezone scenario if production accepts datetimes

## Authority still required

- maintainer approves production patch
