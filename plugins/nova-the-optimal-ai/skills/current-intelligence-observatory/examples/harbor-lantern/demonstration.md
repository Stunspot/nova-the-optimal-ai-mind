# First inquiry: should the editor report a three-day closure?

Use the supplied fictional reports only. The useful answer is: **the packet supports correcting the announcement to a limited Gate B entry pause; it does not establish a three-day terminal closure, actual completed operations or a cause.** Read [the cited brief](public-brief.md).

Open [Evidence Atlas](../../workspace/index.html), choose **Explore the synthetic case**, and inspect `CLM-SIX-HOUR-PAUSE`. Follow its support to `CAP-GAMMA`. The source says 16:00–22:00 local time, without a timezone. A UTC event instant would invent precision, so the native event preserves the wording without one. Publication and retrieval timestamps still appear in Sequence.

Next inspect `REL-BETA-REPEATS-ALPHA`. Beta explicitly follows Alpha in the original paragraph: those reports are one assertion lineage from the start. In Compare, the correction changes the claim status while the earlier capture remains. Records lets you browse observations, decisions and artifacts without knowing an ID first.

The [baseline](case-baseline.json) and [update](case-update.json) share one inquiry_id. The baseline's manual watch review is explicitly an authored fictional exercise. The updated brief remains awaiting editorial review; no human approval or live observation is fabricated. The embedded instruction in Gamma is retained as untrusted text and grants no authority.

From the skill root, verify the case and write projections to a new destination:

```text
python scripts/observatory_guardrail.py validate-case examples/harbor-lantern/case-baseline.json --files
python scripts/observatory_guardrail.py validate-case examples/harbor-lantern/case-update.json --files
python scripts/observatory_guardrail.py project examples/harbor-lantern/case-update.json ./my-projections
python scripts/observatory_guardrail.py delta examples/harbor-lantern/case-baseline.json examples/harbor-lantern/case-update.json ./my-delta.json
python scripts/observatory_guardrail.py audit-publication examples/harbor-lantern/case-update.json
```

The final command deliberately returns nonzero. Read [editorial challenge](editorial-challenge.md), then [the recovery checkpoint](recovery-checkpoint.md). Passing file/hash checks does not answer the editor's semantic or publication decision.
