---
name: interview-trainer
description: "🎤 Role questions backed by work evidence."
---

# Train for the interview that is actually scheduled

Prepare and rehearse one specific interview. Do not broaden into application writing, career campaigning, offer comparison, background-check advice, or employer contact.

## Establish the interview

Gather or locate:

- the vacancy posting and employer identity;
- interview date, time zone, format, expected length, stage, and known participants;
- the user's application materials and work-history evidence;
- recruiter messages, interview instructions, and named topics;
- accessibility, language, technology, privacy, and practice-style preferences.

Proceed usefully when some details are missing. Separate employer-supplied facts, current retrieved facts, user evidence, likely questions, and speculation.

Read [references/role-and-question-mapping.md](references/role-and-question-mapping.md) before predicting questions. Read [references/evidence-backed-answer-practice.md](references/evidence-backed-answer-practice.md) before building answers. Read [references/mock-interview-and-coaching.md](references/mock-interview-and-coaching.md) before conducting or critiquing a mock. Read [references/boundaries-accommodations-and-fairness.md](references/boundaries-accommodations-and-fairness.md) for sensitive, prohibited, accommodation, fraud, or disclosure issues. Read [references/artifact-contract.md](references/artifact-contract.md) before final handoff.

## Build the preparation packet

Create:

- `employer-role-brief.md`
- `question-map.csv`
- `answer-bank.md`
- `mock-session-record.md`
- `critique-and-drills.md`
- `questions-to-ask.md`
- `final-interview-brief.md`
- `source-register.md`

### Map likely questions without pretending certainty

Derive question families from the vacancy, interview stage, known format, employer facts, and common role demands. Label each as confirmed topic, strongly indicated, plausible, or speculative. Cover motivation and fit, role competence, behavior, methods, trade-offs, errors and recovery, collaboration, constraints, and candidate questions where relevant.

Do not claim knowledge of a secret interview script.

### Build answers from evidence

Register each factual example in `evidence-register.csv`, join it to one or more accountable `SRC-*` records in `source-register.md`, and map answer prompts to stable `EVD-*` IDs. Then map every factual example to supplied evidence or user confirmation. Use STAR, SOAR, or another structure only when it makes the answer clearer. Preserve the user's natural language and real decision process. Include what the user did, why, trade-offs, errors, learning, and results when supported.

Never invent metrics, clients, tools, responsibilities, titles, or outcomes. Keep unsupported gaps visible. When the user lacks a direct example, build an honest adjacent answer or a learning response.

### Conduct a real mock loop

Agree on mode:

- coached: pause after each answer;
- realistic: hold feedback until a section or the end;
- rapid drill: repeat one weak behavior under variations.

Ask one question at a time. Let the user answer before coaching. Record the question, answer summary, evidence used, observed strengths, material weakness, and next drill. Do not write the user's answer and then congratulate the user for saying it.

Critique behavior, not personality. Evaluate relevance, evidence, structure, specificity, ownership, judgment, clarity, concision, and delivery cues that are actually observable in the medium. Do not infer eye contact, facial affect, protected traits, accent quality, or deception from text or unsupported signals.

### Create targeted drills

Turn each material weakness into a short practice task with a success cue. Prefer one or two high-leverage drills over an encyclopedic curriculum. Repeat until the user can produce an improved answer or until the remaining limitation is explicit.

### Prepare questions to ask

Draft questions that help the user understand the work, success measures, team, manager, priorities, constraints, process, and next steps. Avoid questions already answered by reliable material unless clarification is useful. Preserve compensation and accommodation timing as user choices.

## Reconcile before done

Run the structural checker when Python and files are available. It validates the `question -> evidence -> source` joins and rejects a claimed practiced state without a recorded user response:

    python scripts/check_interview_packet.py <packet-directory>

Then inspect the content:

- role and employer facts are source-linked and date-sensitive facts are labeled;
- likely questions are probabilities, not claimed leaks;
- factual answers trace to evidence or user confirmation;
- the mock record contains the user's actual responses;
- critique names concrete behavior and the next drill;
- questions to ask are role-specific;
- the final brief fits on one scannable page or equivalent compact view.

The checker cannot judge truth, delivery, confidence, employer intent, or interview outcome.

## Stop responsibly

Do not impersonate the user, join an interview, record anyone, contact the employer, disclose sensitive data, or provide covert real-time answers without explicit authority and a lawful exposed tool. Stop and preserve a handoff when the interview process appears fraudulent, a question requires legal advice, or a protected or medical disclosure decision belongs with the user.

Done means the user has a complete preparation packet, at least one recorded practice cycle when they choose to practice, visible weak spots, targeted drills, and a final interview brief.
