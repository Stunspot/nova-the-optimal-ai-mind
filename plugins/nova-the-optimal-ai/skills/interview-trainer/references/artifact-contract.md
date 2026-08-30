# Interview preparation packet contract

| Artifact | Required contents |
| --- | --- |
| employer-role-brief.md | Role, employer, interview logistics, known format, central criteria, strongest evidence, material gaps, source dates |
| question-map.csv | Stable question IDs, family, criterion, probability, evidence IDs, priority, and practice status |
| evidence-register.csv | Stable evidence IDs, evidence summary, joined source IDs, direct or adjacent status, confirmation state, and notes |
| answer-bank.md | Question sections whose evidence IDs match the map, explicit support state, and user-confirmed facts rather than fabricated scripts |
| mock-session-record.md | Mode, question, actual response or accurate summary, follow-up, observable critique, and session state |
| critique-and-drills.md | Material strengths, weak spots, targeted drill, success cue, and rerun result |
| questions-to-ask.md | Role-specific candidate questions and already-answered exclusions |
| final-interview-brief.md | Compact logistics, thesis, priority prompts, gaps, questions, setup, and bounded readiness |
| source-register.md | Stable source IDs, supplied and retrieved sources, dates, custody, and use |

## Evidence chain

A high-priority question must join to its answer-bank section. The section's `Evidence IDs` must match the question map. Each `EVD-*` record must join to an existing `SRC-*` record before the answer can be labeled `supported`. Use `confirmation-needed` for unresolved facts and `honest-gap` when no supporting evidence exists.

## Practice truth

If the user does not practice, the preparation artifacts may be complete but `mock-session-record.md` and `critique-and-drills.md` must state `PRACTICE NOT OBSERVED`, and the final brief must say `practice unobserved`. A question may be labeled `practiced` or `needs-drill` only when its mock turn contains the user's actual response or an accurate nonempty summary.

The checker validates artifact presence, controlled ledgers, question-to-answer evidence agreement, evidence-to-source joins, and practice-state consistency. It does not judge source truth, answer quality, delivery, employer intent, legality, or outcome.
