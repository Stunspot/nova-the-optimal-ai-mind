---
name: job-application-builder
description: "💼 Vacancy-matched résumé, letter, answers."
---

# Finish the application for the actual vacancy

Own one application from supplied evidence to a review-ready packet. Do not broaden into career campaigning, interview coaching, offer negotiation, social-profile management, or automatic submission.

## Start from the vacancy

Ask for or locate:

- the complete vacancy posting and employer name;
- the user's existing resume or work history;
- requested application questions and document limits;
- location, schedule, work authorization, compensation, accessibility, privacy, and deadline constraints that materially affect fit;
- existing work samples or portfolio material, if relevant.

Proceed with partial material when useful. Name missing inputs and preserve unsupported fields as unresolved; never invent them.

Read [references/application-method.md](references/application-method.md) before drafting. Read [references/truth-ats-and-risk.md](references/truth-ats-and-risk.md) when evaluating claims, keywords, selection criteria, protected information, accommodations, or automated-screening concerns. Read [references/artifact-contract.md](references/artifact-contract.md) before finalizing the packet.

## Build the evidence map first

1. Decompose the posting into required, preferred, responsibility, context, and administrative criteria.
2. Register each supplied source with a stable `SRC-*` ID, custody, date, and use; map every supported `EVD-*` item to one or more of those source IDs.
3. Map each material criterion to supplied evidence, a truthful adjacent signal, or an explicit gap.
4. Separate direct evidence, adjacent transfer, user confirmation needed, and unsupported claims.
5. Identify the strongest role-relevant achievements, methods, constraints, and proof artifacts.
6. Preserve vacancy language only where it truthfully describes the user's evidence. Never keyword-stuff or claim an unearned credential.

Use [assets/evidence-claim-matrix.csv](assets/evidence-claim-matrix.csv) as the working ledger. Claims must remain traceable to a supplied source or an explicit user confirmation.

## Produce the packet

Create the following for the specific vacancy:

- `role-match-brief.md`
- `resume.md`
- `cover-letter.md`
- `application-answers.md`
- `evidence-claim-matrix.csv`
- `work-sample-guidance.md`
- `unresolved-claims.md`
- `submission-checklist.md`
- `source-register.md`

Use the assets as starting structures, not mandatory prose. Match requested file formats and length limits. Preserve a single-column, conventional-heading resume unless the employer explicitly requires another format.

### Resume

Prioritize vacancy-relevant evidence without erasing the user's actual history. Use action, method, context, and result when supported. Keep dates, titles, employers, credentials, scope, and metrics consistent with sources. Do not hide gaps through false dates or inflated titles.

### Cover letter

Make a compact evidence-backed case for this role. Connect two or three strong requirements to actual examples, explain a truthful transition or motivation when useful, and avoid generic enthusiasm, biography dumps, or claims that merely repeat the posting.

### Application answers

Answer the question actually asked. Respect word limits. Use direct examples and label any item requiring user confirmation. Never infer salary history, demographic data, disability, criminal history, citizenship, authorization, clearance, or legal attestations.

### Work samples

Recommend existing evidence first. When a new sample would materially strengthen the application, specify a bounded brief, what it proves, what must remain fictional or sanitized, and how to disclose AI assistance when relevant. Do not create employer work product or misuse confidential material.

## Reconcile before done

Run the packet checker when a filesystem and Python are available:

    python scripts/check_packet.py <packet-directory>

Then perform semantic review:

- every material resume and letter claim is supported or explicitly unresolved;
- dates, titles, metrics, technologies, credentials, and scope agree across artifacts;
- the resume and answers address the vacancy without copying its claims as the user's;
- no private source data was added unnecessarily;
- submission fields requiring the user's attestation remain with the user;
- file names, formats, limits, links, and deadline are checked.

The checker proves only structural and ledger consistency. It cannot decide whether prose is persuasive, evidence is genuine, or a candidate should be selected.

## Stop responsibly

Do not submit, impersonate the user, contact an employer, create accounts, accept legal attestations, or disclose sensitive data without an exposed tool and explicit permission. Stop for user confirmation when a material claim lacks evidence, a required legal answer is unknown, the posting appears fraudulent, or the application would require deception.

Done means the complete packet is ready for the user's review and submission, with unresolved claims and user-owned attestations visible.
