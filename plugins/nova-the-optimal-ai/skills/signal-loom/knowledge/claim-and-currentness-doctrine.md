# Claim and currentness doctrine

## Claim statuses

- `sourced`: directly supported by a supplied source and locator.
- `inferred`: reasoned from sourced material but not directly stated.
- `illustrative`: invented and visibly labeled to demonstrate form or logic, never presented as observed fact.
- `missing`: required support was not supplied.
- `stale`: evidence exists but is too old for the intended current claim.
- `disputed`: supplied sources conflict or an authoritative challenge remains unresolved.

Do not use `inferred`, `illustrative`, `missing`, `stale`, or `disputed` claims as unqualified factual copy.

## Currentness classes

- `timeless`: the claim does not materially depend on a changing external state.
- `dated`: the claim is valid only with an explicit as-of date or period.
- `current-sensitive`: the claim purports to describe a current state and needs freshness evidence.

Currentness is about the claim, not the file's modification date. An old source can support a timeless claim; a recently copied file can contain stale facts.

## Required ledger fields

Each JSON Lines record should include:

```json
{"id":"C-001","text":"...","type":"fact","source_id":"S-001","locator":"page 4","as_of":"2026-07-01","currentness":"dated","status":"sourced","notes":""}
```

Use `null` only when the absence is real and explicit. `source_id` and `locator` may be null for `illustrative` or `missing` records, but the visible artifact must label or exclude them.

## Authority

The system can classify and recommend. Only the human can approve disputed resolution, authorize externally refreshed evidence, approve an artifact for export, or publish it. Record that authority rather than implying it.
