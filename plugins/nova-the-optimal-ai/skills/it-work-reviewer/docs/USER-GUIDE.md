# Work an IT case with Beryl

This guide explains how to collaborate with Beryl from the first symptom through diagnosis, change, verification, and handoff. It is for device owners, support staff, repair technicians, and administrators who can supply evidence and retain authority over consequential actions.

## Understand the working loop

Beryl uses seven connected motions:

1. **Frame:** state the device, environment, observable problem, timing, recent change, stakes, and desired outcome.
2. **Gate:** identify hazards, data value, privacy, credentials, ownership, policy, warranty, and business-continuity limits.
3. **Preserve:** capture evidence that a reboot, reset, update, repair, or cleanup could erase.
4. **Differentiate:** compare materially different causes and choose an observation that separates them.
5. **Intervene:** make one intelligible, authorized, reversible change where practical.
6. **Verify:** recreate the original failure conditions and check functions disturbed by the work.
7. **Hand off:** leave another person the current state, decisive evidence, authority, next move, and evidence needed to advance.

The loop is elastic. An urgent hazard can require containment before full diagnosis. A failed verification returns the case to the differential rather than erasing earlier evidence.

## Describe the problem

Use this compact intake when you have enough information:

```text
$beryl-it-tech
Device and environment:
What I observe:
When or under what workload:
What still works:
Recent changes:
What I already tried:
Data, privacy, downtime, or cost stakes:
Owner or authority:
What I want to accomplish:
```

Leave any field as `unknown`. Do not fill gaps with a diagnosis.

## Supply evidence safely

Good evidence includes exact errors, timestamps, logs, photos, version and device identifiers, resource measurements, network addressing, update history, health counters, backup state, and the result of a named test under named conditions.

Before sharing:

- remove passwords, MFA codes, recovery phrases, private keys, and unrelated personal data;
- confirm you may share workplace or client material;
- preserve the original file when editing or redacting a copy;
- state whether evidence is reported, directly observed, measured, retrieved from a source, or assumed.

A screenshot proves only what was visible in that captured state. A log proves only what its producing subsystem recorded. A prepared command is not an executed command.

## Evaluate a proposed action

Before you carry out a consequential step, confirm that the response states:

- the purpose of the action;
- the exact device, version, or condition to which it applies;
- prerequisites and required authority;
- the expected result;
- the safe stop condition;
- the possible effect on data, privacy, warranty, or service;
- the rollback or recovery path;
- what result leads to each next branch.

If the action changes several variables at once, ask why the bundle is necessary and how causality and rollback will be preserved.

## Work with commands and tools

Beryl may prepare a command when the platform and purpose are sufficiently known. Treat it as prepared until an authorized person or real tool runs it.

When returning a result, include:

- the exact command that ran;
- the actual device and account context;
- the complete relevant output or error;
- the time and conditions;
- whether the command changed state;
- whether rollback was needed.

Do not paste secrets or run commands against a different platform, version, drive, interface, or account because the syntax looks familiar.

## Preserve a long case

Ask Beryl to create a case from `assets/it-case.template.json` when work spans multiple turns, people, tools, or consequential changes. The case keeps current evidence, hypotheses, tests, changes, verification, authority, and next move separate.

Follow [Create, validate, and resume a case file](CASE-FILES.md) for the field definitions and validation procedure.

## Verify before closing

A new part, changed setting, successful boot, quiet interval, or absent error is not automatically a confirmed repair.

Before `verified-resolved`, record:

- the original triggering workload, duration, state, and symptom;
- the after-change test under a comparable envelope;
- relevant temperatures, power behavior, errors, or measurements;
- adjacent functions disturbed by the repair;
- the observation window for intermittent problems;
- pass, fail/reopen, and safe-stop conditions.

Use a bounded disposition when evidence is incomplete: `improved-unresolved`, `workaround-only`, `awaiting-observation`, `awaiting-authority`, `referred`, or `unsafe/incomplete`.

## Use independent review

Invoke `$it-work-reviewer` when a plan affects irreplaceable data, credentials, security, firmware, expensive parts, a managed device, destructive recovery, or a completion claim.

Provide the case, plan, work order, or completion note as received. The reviewer returns:

1. a verdict;
2. the exact scope reviewed;
3. material findings with evidence and closure conditions;
4. the residual boundary.

Review is advisory unless an accountable human assigns it gate authority. It does not authorize access, spending, physical work, wiping, release, or configuration changes.

## Choose the right artifact

| Need | Artifact |
|---|---|
| Resumable machine-readable case | `assets/it-case.template.json` |
| Fast investigation notes | `assets/diagnostic-worksheet.md` |
| Device ownership and custody | `assets/device-intake-and-custody.md` |
| Technician or customer handoff | `assets/work-order-and-handoff.md` |
| Rebuild or migration | `assets/build-and-migration-checklist.md` |
| Evidence-backed closure | `assets/verification-record.md` |

## Know when to stop

Stop at containment or handoff when the remaining action cannot protect people, data, truth, or authority. Common referral boundaries include swollen batteries, mains or power-supply work, liquid damage, board-level repair, unstable storage with unique data, destructive recovery, managed-device compromise, credential bypass, and organization-controlled identity or security systems.

Use [Protect people, data, and authority](SAFETY-AND-DATA.md) for the full boundary and [Troubleshoot Beryl IT Benchcraft](TROUBLESHOOTING.md) when the host or evidence path fails.
