# Status and stakeholder communication

## Answer the governing question first

A project status is decision support. Lead with the conclusion in ordinary language:

1. **Done?** yes, no, or unknown under the named completion contract.
2. **Location?** exact Project -> Phase/Stage -> Milestone -> Workstream path.
3. **Outcome?** what is now true, supported by what evidence.
4. **Gap?** the smallest material remaining condition.
5. **Constraint?** why it remains and who can change it.
6. **Next?** one controlled move, owner, and decision time if relevant.

Do not lead with test counts, file lists, hashes, or a travel diary through the terminal. Those are evidence attachments.

## State vocabulary

Use qualified state phrases that cannot be mistaken for one another:

- constructed, not yet verified;
- verified locally, not checkpointed;
- locally checkpointed, remote behind;
- remote synchronized, not deployed;
- deployed, runtime health unobserved;
- operational under the tested scenario;
- accepted with named residual conditions;
- project complete under the stated contract;
- valuable outcome not yet measured.

If the user asks “is it finished?”, answer that before explaining the taxonomy. If the completion contract is missing, say what common interpretation you are using and identify the decision needed.

## Project-scale status brief

Use this compact shape for consequential updates:

```text
Project: <name>
Location: <phase > milestone > workstream>
Is it done: <yes/no/unknown, under which contract>
What exists: <outcome plus strongest evidence>
What remains: <material gap>
Authority edge: <who can act or decide>
Next move: <one action and owner>
```

Add risks, decisions, forecast, or technical details only when they affect steering.

## Translate for the audience

### Owner or sponsor

Focus on outcome, value, current location, confidence, cost/schedule exposure, material risk, and the decision required. Name consequences and options. Do not make the sponsor decode implementation vocabulary.

### Project lead

Focus on active commitments, dependencies, capacity, controls, change load, evidence, exceptions, and recovery options. Preserve exact identifiers.

### Delivery team

Focus on outcome, definition of done, near-term priority, blockers, interfaces, quality, and protected focus. Do not spray executive theater downward.

### Finance, audit, or governance

Focus on baseline, authority, traceability, evidence method, cost/forecast, accepted variance, and residual exposure. Do not imply assurance beyond inspected evidence.

### Technical or domain specialist

Focus on the specific interface, decision, constraint, evidence need, and downstream consequence. Let the specialist own domain truth.

## Decision requests

A useful escalation states:

- decision needed;
- deadline or trigger;
- available options;
- recommendation and rationale;
- impact of each option on outcome, time, cost, risk, quality, and benefits;
- default consequence if no decision arrives;
- evidence attached.

Escalation should travel before the project exhausts its options. “We have been blocked for six weeks” is a postmortem sentence, not a control.

## Avoid narrative failure

- Never invent a new roadmap vocabulary without mapping it to the established one.
- Never let the latest work package become the whole project in the report.
- Never call an agent-authored rule user policy without provenance.
- Never report green from activity metrics when integration or acceptance evidence is absent.
- Never hide remote divergence, uncommitted state, or unperformed external steps behind “done.”
- Never bury the user's question under a cathedral of technically accurate detail.

## Correction language

When wrong, say:

1. what was wrong;
2. what the correct project frame or state is;
3. why the error happened in control terms;
4. what artifact or rule changes;
5. what remains unaffected;
6. the restored next move.

Precision repairs trust faster than either groveling or process cosplay.