# Recover the next useful step

Preserve the campaign and exact error before resetting anything. [Validation](VALIDATION.md) explains what each command checks.

| Symptom | Recovery |
|---|---|
| Skill is not discoverable | Confirm complete import and fresh session; use [Installation](INSTALLATION.md) or [copy/paste fallback](../fallbacks/universal-copy-paste-workflow.md). |
| Open does not launch | Confirm Python3.10+; run `python workspace/open.py --serve --data-root "your folder"` from the package root to expose the error. |
| Campaign says needs repair in library | Open it, use Vault actions → Native files and repair malformed text. If the native directory itself is linked/unreadable, preserve the original and repair a regular-directory copy. |
| Save reports revision conflict | Download unsaved draft, reload saved vault, compare changes and reapply only what is still needed. Coordinate the other writer. |
| Save fails during writing | Ordinary write failure restores prior native bytes. If rollback is incomplete, the error gives the history snapshot; preserve your draft and restore those exact native files before further editing. |
| Complete campaign has stale review | Preserve the historical result. Set phase review and status active in a working copy. Review actual changed evidence/report; use [review contract](../references/review-contract.md). Do not bulk recompute verdicts. |
| Counter mismatch | Correct the underlying record first, then synchronize counts. Room Save computes them from ledgers. |
| Deeply-read note missing | Read the source and record its actual scope and limitations, or remove the unearned reading state. Padding a note proves nothing. |
| Excluded or duplicate source is cited | Preserve reading history; remove the final citation or retain a usable canonical source. Explain disposition and duplicate_of as applicable. |
| Visible bibliography entry missing | Include the cited ID, exact source title and locator under Sources, Bibliography or References. Hidden comments and fenced examples do not count. |
| Assembly refuses differing report | Compare report.md with ordered draft sections. Reconcile them, or intentionally use --replace; prior report is retained under .assembly-history. |
| Import refuses old completion | Preserve the original, set a working copy review/active and repair actual records; old labels are not current review. |

## Access or budget ends

Unavailable search leaves live web findings unexecuted; unavailable full text leaves deeply-read and entailment unresolved. Continue useful supplied-source work and use [degraded-capability guidance](../fallbacks/degraded-capability.md). A hard budget stops execution without proving unsearched things absent. Preserve question, achieved findings, coverage gaps and exact return point.

Existing permission carries forward. Ask for a genuinely new paid/private/authenticated route only when it can repair a named gap. A missing independent reviewer does not magically make author review independent; perform a useful in-process review when allowed, or deliver the draft with the exact unmet requirement.

## What a backup contains

Native text export contains root Markdown, campaign/review JSON, ledgers and immediate notes/drafts. Unsaved draft download is recovery JSON, not automatic merge/import. Complete-folder backup must also include your originals, media, nested corpora and local history. [Lifecycle](LIFECYCLE.md) explains updates and removal; [Support](../SUPPORT.md) explains a useful defect report.
