# Get an answer you can inspect

Begin with your actual question. “Use $omnara-deep-research. Does [claim] hold for [setting/time], and what evidence would change the answer?” Include the intended decision and supplied material. The agent should begin useful work, preserve your question and identify the consequential uncertainty. You do not need to operate every ledger yourself.

## Open or return to the room

Extract the complete package. With Python 3.10+, double-click **Open.cmd** on Windows; on macOS/Linux run `python3 workspace/open.py`. [Installation](docs/INSTALLATION.md) gives the skill and fallback routes. The launcher opens the matching local service. Research lives separately, by default under `Documents/OMNARA Campaigns`; reopen through the launcher after reboot rather than bookmarking a temporary port.

The OMNARA wordmark opens your investigation library. **New investigation** takes a title and the question exactly as asked. **Import a native vault** copies an existing valid campaign without changing the original. **Environment** selects Tracework, Survey Folio or Proof Cabinet. [Campaign room](docs/CAMPAIGN-ROOM.md) explains reading, comparison, editing and recovery.

For an inspectable example, read [the local/global sea-level report](examples/sea-level-comparison/report.md). Copy `examples/sea-level-comparison` into a writable research location before importing or editing it. It contains actual bounded primary-source research, not invented station data.

## Advance the inquiry

Use **Next-pass handoff** to give the saved campaign path and next step to your research agent. The room itself does not search. The agent records sources, reads the important subset, tests competing explanations and writes the report. **Evidence atlas** follows claims to sources; **Reading room** opens notes and comparisons; **Open questions** keeps missing evidence visible; **Synthesis** reads the current answer and its bibliography.

A connection is only a recorded citation. The current-review line tells you whether the saved native content has a matching declared semantic review. Legacy labels such as supported are retained as recorded history. Edits invalidate current review; they cannot inherit a verdict about different evidence.

## Save and finish

**Save vault** validates native records and retains prior files. If another writer changed the campaign, download the unsaved draft before reloading. A rejected edit remains in your browser. [Recovery](docs/TROUBLESHOOTING.md) explains damaged records, failed saves and historical completed campaigns.

The agent assembles before auditing:

```text
python scripts/assemble_report.py <campaign-folder>
python scripts/citation_audit.py <campaign-folder>
python scripts/research_campaign.py review-subject <campaign-folder>
```

Assembly refuses to replace a differing report until you inspect it and explicitly use `--replace`; that retains prior report bytes. The subject command does not issue a review. Follow [the review contract](references/review-contract.md), then set phase and status to complete together and validate:

```text
python scripts/research_campaign.py validate <campaign-folder>
```

Your result should answer the question, name important limits, expose readable sources and say what would reopen it. A useful no-evidence answer is possible; it must distinguish “not established here” from “does not exist.” Source quotas and page estimates are not completion criteria.

Use **Export native text ZIP** for the saved native text and **Next-pass handoff** for continuation. Neither includes external corpora or media. [Lifecycle](docs/LIFECYCLE.md) explains complete-folder backup and updates. All commands run from the folder containing SKILL.md; use `python3` if that is your interpreter name.
