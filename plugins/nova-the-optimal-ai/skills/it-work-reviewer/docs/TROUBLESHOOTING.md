# Troubleshoot Beryl IT Benchcraft

Choose the heading that matches the observable problem. Preserve error wording, host version, release version, and the action that produced the problem before reinstalling, resetting, or rewriting a case.

## The skill name is not recognized

1. Confirm that you started a new task after installation.
2. Confirm that the host registered `skills/beryl-it-tech`, not only its `SKILL.md` file.
3. Confirm that the complete release tree remains available around the skill.
4. Restart the host if it caches skill discovery.
5. Retry this exact input:

   ```text
   $beryl-it-tech Help me frame a test case. Do not diagnose anything yet.
   ```

If the host still does not recognize the name, record the host and version, installation method, installed path or package identity, and exact error. Use [the universal workflow](../fallbacks/universal-copy-paste-workflow.md) until the host’s real skill-installation contract is known.

## Beryl gives generic troubleshooting advice

Supply one observable failure envelope instead of a diagnosis label:

```text
Device and operating system:
Exact symptom or error:
When it happens:
What remains working:
Recent change:
What was already tried:
```

Ask Beryl to name the live mechanisms, the evidence each predicts, and the smallest test that separates the leading two. If it still gives a reset bundle, stop and invoke `$it-work-reviewer` on the proposed plan.

## Beryl invents a symptom or action

Correct the record explicitly:

```text
That state was not reported or observed. Mark it unknown, restore the original facts, and rebuild the next decision without it.
```

If a response says a command ran, a part was replaced, or a result passed without evidence, treat the claim as unsupported. Preserve the response and use `$it-work-reviewer` before continuing.

## The proposed step feels unsafe or too destructive

Do not perform it. Ask for the purpose, prerequisites, expected result, safe stop condition, data and privacy effect, rollback, and a lower-risk discriminating alternative.

For heat, swelling, smoke, liquid, mains exposure, unstable unique storage, credential bypass, or a managed-device incident, use [Protect people, data, and authority](SAFETY-AND-DATA.md) and transfer custody where required.

## The host cannot run a command or inspect a file

Ask Beryl to continue in plan-ready mode:

```text
Prepare the exact observation or command for an authorized operator. State its purpose, prerequisites, stop condition, rollback, expected branches, and the guarantee lost because you cannot execute or inspect it.
```

Return the actual output later. Do not allow a prepared command to become an execution claim.

## A current vendor procedure is unavailable

Do not accept an exact firmware file, driver, compatibility promise, warranty statement, security procedure, or model-specific instruction from memory alone.

Ask Beryl to prepare a source request containing the manufacturer, exact model, hardware revision, current firmware or software version, installed component where relevant, reason for the change, and the current primary-vendor document needed. Resume after that source is supplied or retrieved.

## A case file fails validation

Run:

```text
python scripts/validate_case_file.py path/to/case.json
```

Use the reported failure:

| Failure | Recovery |
|---|---|
| Missing required keys | Restore the named fields from `assets/it-case.template.json` |
| Invalid status | Use a controlled status from `schemas/it-case.schema.json` |
| Evidence, hypotheses, tests, changes, or sources is not an array | Restore JSON array brackets, even when the array is empty |
| Invalid verification disposition | Use a controlled disposition listed in [the case-file reference](CASE-FILES.md#use-status-and-disposition-correctly) |
| `next_move.action` is empty | State the next safe action or referral |
| JSON parse error | Fix the named syntax position without discarding case content |

Validation proves structure, not truth. Reconcile the repaired file with the last trusted case state.

## The symptom is gone, but verification is incomplete

Do not mark the case fixed from quiet time alone. Record the change as applied and the observation as limited evidence. Recreate the original workload, duration, state, and trigger when safe; observe relevant errors, temperatures, power behavior, and adjacent functions; define pass, fail/reopen, and safe-stop conditions.

Use `awaiting-observation` or another bounded disposition until the evidence earns closure.

## Prepare an escalation

Include:

- device and owner or authority;
- exact symptom, timing, and trigger;
- important data, backup, encryption, and privacy state;
- hazards and safe stopping state;
- decisive evidence and source versions;
- tests and changes actually performed;
- live hypotheses and what would separate them;
- rollback state;
- requested decision or qualified custodian.

Use `assets/work-order-and-handoff.md` for a structured transfer.
