# Troubleshooting and recovery

Begin from the observable symptom. Preserve campaign files and error output before resetting anything.

## The host does not expose `$omnara-deep-research`

**Likely conditions**

- The standalone directory was not placed where the host discovers skills.
- The host requires a plugin package rather than an individual skill directory.
- The current task began before the skill was imported.
- Omnara is available only through an installed Nova package.

**Check**

1. Confirm that the imported directory contains `SKILL.md` at its root.
2. Confirm that the host lists `omnara-deep-research` or **OMNARA Deep Research**.
3. Begin a fresh task after import.
4. If the host requires plugin manifests, use the Nova distribution or follow the host's packaging instructions. This repository does not claim a standalone plugin manifest.

**Recovery**

Use [`../fallbacks/universal-copy-paste-workflow.md`](../fallbacks/universal-copy-paste-workflow.md) when the host can accept a long prompt but cannot load the skill.

## Campaign initialization says the destination is not empty

**Cause**

`research_campaign.py init` refuses to overwrite an existing nonempty directory.

**Recovery**

Choose a new directory or inspect and intentionally move the existing campaign. Do not delete it until you know whether it contains evidence that must be preserved.

## Campaign validation reports counter mismatches

**Cause**

`campaign.json` counters no longer match the query and source ledgers.

**Check**

Review the reported counter and count the retained records with that state. Remember that one source can carry several compatible states.

**Recovery**

Correct the ledger state or the counter. Do not change the counter merely to silence validation when the source record is wrong.

## A deeply read source requires a substantive note

**Cause**

The source is marked `deeply-read`, but `notes/S###.md` is missing, too short, or still contains template instructions.

**Recovery**

Write the evidence note using `notes/SOURCE-NOTE-TEMPLATE.md`, or remove the `deeply-read` state until the full reading exists. Preserve what the source does not establish.

## A terminal state conflicts with an opened or cited state

**Cause**

A source is marked `excluded`, `duplicate`, or `inaccessible` while also being marked `opened`, `deeply-read`, or `cited`.

**Recovery**

Choose the state that reflects the canonical record. For a duplicate, keep the usable source under its canonical ID and point the duplicate record to it. For partial access, record the precise access boundary rather than calling the source both inaccessible and deeply read.

## Report assembly says no Markdown section drafts were found

**Cause**

The campaign has no `draft/*.md` files.

**Recovery**

Create ordered section files such as:

```text
01-orientation.md
02-evidence.md
03-contradictions.md
04-implications.md
99-bibliography.md
```

Run assembly again. Files are concatenated in lexical filename order.

## Structural citation audit reports no markers

**Cause**

The assembled report contains no markers such as `[S001]`.

**Recovery**

Add markers immediately after supported claim spans, ensure each source is eligible and linked from a claim record, reassemble the report, and rerun the audit.

## Structural citation audit is stale after an edit

**Cause**

The report, source ledger, or claim ledger changed after the audit. Their SHA-256 values no longer match the audit record.

**Recovery**

Rerun `citation_audit.py`. Then recheck semantic entailment for every claim affected by the edit.

## Search is unavailable

**Preserve**

- the verbatim inquiry;
- research brief;
- coverage map;
- query families;
- supplied-source analysis;
- exact retrieval plan.

Label unexecuted web work `PREPARED - NOT EXECUTED`. Do not claim source counts or negative findings from searches that did not run.

## A paid, private, or authenticated source is needed

Stop at the authority boundary. Name the source, the coverage gap it could repair, the intended access method, and whether a free or public substitute remains. Do not request or store credentials in the campaign vault.

## The budget is exhausted

Set an honest status such as `budget-exhausted` or `partial-success`. Record counts, covered and uncovered loci, important claims, contradictions, blockers, and the exact resume point. A budget stop is not a completed search.
