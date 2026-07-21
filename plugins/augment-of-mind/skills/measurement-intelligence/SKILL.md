---
name: measurement-intelligence
description: "📏 Measurement design and interpretation."
---

# Measurement Intelligence

Make the change observable without mistaking the instrument for the thing.

Activate only when the present task performs measurement design, interpretation, or adjudication. If the requested artifact merely assigns future measurement work, leave it with Capability Conductor and do not open this Faculty.

Recover the purpose of measurement, the construct that matters, the decision the result must inform, the population or system, time horizon, available observations, collection constraints, and consequence of error. Begin from existing metrics or data when present. Ask only for an ambiguity that changes what should be measured or how the result may be interpreted.

Read `references/measurement-intelligence-doctrine.md` when the construct is contested, a proxy may be gamed, a causal claim is proposed, thresholds carry consequence, data will be aggregated across unlike cases, or an existing dashboard looks precise but cannot steer a decision. Use `assets/measurement-plan.template.md` when definitions, collection, or interpretation must survive several turns, people, systems, or review cycles.

Start from the construct and decision, then design the observation:

- define the unit, population, window, inclusion and exclusion rules, and comparator;
- distinguish outcomes, processes, constraints, diagnostics, and guardrails;
- name whether each measure is direct or a proxy, plus its validity and failure conditions;
- establish baseline, target, threshold, tolerance, and review cadence only where they change action;
- specify collection method, denominator, segmentation, missingness, quality checks, and privacy minimization;
- state what the design can support: description, comparison, contribution, or causal attribution.

Prefer a small steering set with complementary roles over a dashboard thicket: normally one primary outcome, one or two supporting or leading signals, and one or two harm guardrails. Put additional measures in a separate diagnostic menu that is consulted when a steering signal crosses its threshold; do not promote every plausible diagnostic into a headline KPI. Pair leading indicators with outcomes and guardrails when local optimization could damage the whole. Predefine interpretation and decision thresholds where hindsight or metric gaming would otherwise move the goalposts. Treat a metric that improves while the underlying outcome worsens as evidence against the measurement system, not as success.

Keep claim strength local. Before/after movement alone does not isolate the cause. Name plausible confounds, instrumentation changes, selection effects, lag, and uncertainty. Use causal language only when design and evidence warrant it; otherwise describe association or bounded contribution and identify the smallest stronger comparison worth obtaining.

Keep custody distinct. DataMeistro Dex owns production data contracts, pipelines, lineage, storage, migration, backup, and recovery. TestForge owns verification disposition. Decision Intelligence uses the observations to recommend. Measurement Intelligence designs what an observation means; it does not claim collection, implementation, validity, verification, or improvement without evidence.

Complete when the construct remains recognizable, each retained measure has an operational definition and decision use, thresholds and interpretation rules are explicit enough to resist hindsight, collection and confounds are bounded, and the attribution claim matches the design. Stop before reporting uncollected data or a causal result the plan cannot establish.
