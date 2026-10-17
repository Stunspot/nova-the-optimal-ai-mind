# Verification report

## Decision

**Status:** NOT_READY
**Target:** escaped-delimiter configuration parser
**Revision:** synthetic-parser-v1
**Reviewer:** REVIEW_PASS

### Basis

- high-severity escaped-delimiter contract fails reproducibly

## Scope

### Included

- pair separation
- escaped semicolon handling
- backslash preservation

### Excluded

- Unicode normalization
- resource exhaustion

## Critical invariants

- INV-001: only unescaped semicolons separate pairs
- INV-002: escape processing preserves the intended literal value

## Risk register

| ID | Severity | Disposition | Risk |
|---|---|---|---|
| R-001 | high | covered | escaped delimiter -> premature lexical split -> malformed or incorrect configuration |

## Execution evidence

| ID | Status | Exit | Command | Raw evidence |
|---|---|---:|---|---|
| E-001 | failed | 1 | `python -m unittest expected.test_parser -v` | expected/execution-record.json |

## Findings

- F-001 [PRODUCT_DEFECT/high]: lexical splitting occurs before escape recognition and breaks escaped delimiter values — open

## Residual risk

- RR-001: complete consecutive-backslash and malformed-input grammar is unspecified — obtain grammar authority and add properties before broad release

## Authority still required

- parser owner confirms full escape grammar before generalized fix
