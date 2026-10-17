# Shape an inquiry Omnara can investigate

A useful research request identifies the question, who will use the result, what decision it supports, and which boundaries change the answer. It does not need to prescribe every search query.

## Minimal focused inquiry

Use this for a bounded factual or comparative question:

```text
Use $omnara-deep-research.

Compare the current data-retention terms of Product A and Product B for a United States healthcare startup. Use official sources, note effective dates and plan differences, and return a concise comparison with unresolved points.
```

The important cues are the products, jurisdiction, audience, source expectation, freshness requirement, and output form.

## Decision brief

Use this when evidence must support a choice:

```text
Use $omnara-deep-research.

Investigate whether our ten-person nonprofit should replace shared passwords with a password manager this quarter.
Audience and decision use: the executive director and operations lead choosing a rollout plan.
Include: security benefit, administrative burden, account recovery, accessibility, training, cost, and credible objections.
Evidence cutoff: current through [date].
Deliverable: a recommendation, alternatives, implementation risks, evidence limits, and the observations that would change the recommendation.
```

## Contested or causal question

Use this when sources are likely to disagree:

```text
Use $omnara-deep-research.

Investigate the strongest explanations for [phenomenon] between [date] and [date]. Map competing accounts rather than averaging them. For each account, identify its strongest support, awkward evidence, incentives, scope limits, and the obtainable observation most likely to distinguish it from its nearest rival.
```

## Literature-centered inquiry

```text
Use $omnara-deep-research.

Review the research on [topic] for [population or system]. Prioritize systematic reviews, primary studies, registered reports, corrections, retractions, and current consensus statements. Preserve method, sample, measurement, geography, time window, and transfer limits. Separate established findings, disputed findings, and open questions.
```

## Product or software inquiry

```text
Use $omnara-deep-research.

Determine how [product or library] currently handles [behavior]. Prefer official documentation, release notes, repository code, tests, issues, and direct reproducible checks. Keep version and environment attached to every consequential claim. Distinguish declared behavior from observed behavior.
```

## Supplied-source audit

```text
Use $omnara-deep-research.

Audit the attached sources against this claim: [claim]. Do not browse unless needed to resolve a named gap. For each source, state what it establishes, what it does not establish, relevant scope and dates, and whether it supports, partially supports, contradicts, or cannot verify the claim.
```

## Expensive or access-gated research

Name authority boundaries before Omnara reaches them:

```text
Paid sources are not authorized. Authenticated browsing is allowed only for [named source] in my existing session. Do not upload private files or send messages. Stop and ask before any externally mutating action.
```

Omnara should use authorized free routes first and request a paid or private route only when it can name the coverage gap that route could repair.

## Requests to avoid

Avoid instructions that reward appearance over evidence:

- “Find exactly 500 sources.”
- “Prove my conclusion.”
- “Cite something after every sentence.”
- “Do not mention disagreement.”
- “Write 100 pages even if the evidence is thin.”

Replace them with a decision use, evidence burden, source ecology, disconfirming requirement, and stopping condition.
